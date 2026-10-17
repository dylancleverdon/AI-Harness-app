"""Runs scripts as subprocesses, streams output, samples memory, writes reports."""
import codecs
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

from . import diagnose, lmstudio, memory
from .config import RUNS_DIR, SCRIPTS_DIR, settings


SUMMARY_KEYS = ("id", "script", "args", "started", "ended", "status", "exit_code",
                "kill_reason", "peak_rss_mb", "duration")


ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b[@-Z\\-_]")


def clean(text):
    return ANSI.sub("", text)


SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv"}


def snapshot(dirs, cap=20000):
    snap = {}
    for d in dirs:
        for root, dirnames, files in os.walk(d):
            dirnames[:] = [x for x in dirnames if x not in SKIP_DIRS and not x.startswith(".")]
            for f in files:
                if f.endswith(".pyc") or f.startswith(".") or len(snap) >= cap:
                    continue
                fp = os.path.join(root, f)
                try:
                    st = os.stat(fp)
                    snap[fp] = (st.st_mtime, st.st_size)
                except OSError:
                    pass
    return snap


def diff_snapshots(before, after):
    out = [{"path": p, "status": "new" if p not in before else "modified", "size": v[1]}
           for p, v in after.items() if before.get(p) != v]
    return sorted(out, key=lambda f: f["path"])[:200]


class Run:
    def __init__(self, script, args):
        self.id = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
        self.script = script
        self.args = args
        self.started = time.time()
        self.ended = None
        self.status = "running"  # running | ok | failed | stopped | killed
        self.exit_code = None
        self.kill_reason = ""
        self.lines = []  # {t, s: out|err|sys, x}
        self.mem = []  # {t, rss_mb, avail_pct, level}
        self.peak_rss_mb = 0
        self.proc = None
        self.live = {}  # stream -> in-place line (progress bar) shown pinned at the bottom
        self.files = []
        self.watch = []
        self.before = {}
        self.lock = threading.Lock()

    def add(self, stream, text):
        with self.lock:
            self.lines.append({"t": round(time.time() - self.started, 2), "s": stream, "x": text})

    def output(self):
        return "\n".join(l["x"] for l in self.lines if l["s"] != "sys")

    def summary(self):
        return {"id": self.id, "script": self.script, "args": self.args, "started": self.started,
                "ended": self.ended, "status": self.status, "exit_code": self.exit_code,
                "kill_reason": self.kill_reason, "peak_rss_mb": self.peak_rss_mb,
                "duration": round((self.ended or time.time()) - self.started, 1)}

    def detail(self):
        d = self.summary()
        d["output"] = self.output()
        d["traceback"] = diagnose.extract_traceback(d["output"])
        d["hints"] = diagnose.diagnose(d)
        d["files"] = self.files
        return d


class RunManager:
    def __init__(self):
        self.runs = {}
        self.events = []  # guard / system events shown in the UI
        self._trip_count = 0

    # ---- lifecycle -------------------------------------------------------
    def start(self, script, args="", argv=None, extra_env=None, watch=None):
        path = (SCRIPTS_DIR / script).resolve()
        if SCRIPTS_DIR.resolve() not in path.parents or not path.is_file():
            raise FileNotFoundError(script)
        cfg = settings.get()
        run = Run(script, args)
        base = lmstudio.base_url()
        env = {**os.environ, "PYTHONUNBUFFERED": "1", "LMSTUDIO_BASE_URL": base,
               "OPENAI_BASE_URL": base + "/v1", "OPENAI_API_KEY": "lm-studio",
               "AIHARNESS_RUN_ID": run.id, "AIHARNESS_MODEL": lmstudio.loaded_model(), **(extra_env or {})}
        py = cfg["python"] or sys.executable
        import shlex
        cmd = [py, "-u", str(path)] + (argv or []) + (shlex.split(args) if args else [])
        run.args = " ".join(shlex.quote(a) for a in cmd[3:])
        run.watch = watch or [SCRIPTS_DIR]
        run.before = snapshot(run.watch)
        try:
            run.proc = subprocess.Popen(cmd, cwd=SCRIPTS_DIR, env=env, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, bufsize=0,
                                        start_new_session=True)
        except OSError as e:
            run.add("sys", f"Could not start: {e}")
            run.status, run.ended = "failed", time.time()
            self._finalize(run)
            self.runs[run.id] = run
            return run
        self.runs[run.id] = run
        run.add("sys", f"$ {' '.join(cmd)}")
        run.pumps = []
        for stream, pipe in (("out", run.proc.stdout), ("err", run.proc.stderr)):
            t = threading.Thread(target=self._pump, args=(run, stream, pipe), daemon=True)
            t.start()
            run.pumps.append(t)
        threading.Thread(target=self._wait, args=(run,), daemon=True).start()
        return run

    def _pump(self, run, stream, pipe):
        """Reads raw output. '\\n' commits a line; a bare '\\r' means the line is being redrawn in place
        (progress bars), so it's shown as a live line instead of piling up as new lines."""
        dec = codecs.getincrementaldecoder("utf-8")("replace")
        cur = last = ""
        fd = pipe.fileno()

        def live():
            run.live[stream] = clean(cur).strip("\r") or clean(last)

        while True:
            try:
                chunk = os.read(fd, 65536)
            except OSError:
                break
            if not chunk:
                break
            for tok in re.split(r"(\r\n|\n|\r)", dec.decode(chunk)):
                if tok in ("\n", "\r\n"):
                    run.add(stream, clean(cur) if cur.strip() else clean(last) if last.strip() else "")
                    cur = last = ""
                    run.live[stream] = ""
                elif tok == "\r":
                    if cur.strip():
                        last, cur = cur, ""
                elif tok:
                    cur += tok
                    live()
            live()
        tail = clean(cur) if cur.strip() else clean(last)
        if tail.strip():
            run.add(stream, tail)
        run.live[stream] = ""

    def _wait(self, run):
        code = run.proc.wait()
        for t in getattr(run, "pumps", []):
            t.join(timeout=3)  # let output drain (a stray grandchild holding the pipe can't block us)
        run.exit_code, run.ended = code, time.time()
        if run.kill_reason:
            final = "killed" if run.kill_reason.startswith("memory guard") else "stopped"
        else:
            final = "ok" if code == 0 else "failed"
        try:
            run.files = diff_snapshots(run.before, snapshot(run.watch))
        except Exception:
            run.files = []
        run.before = {}
        run.add("sys", f"[exited with code {code} after {run.summary()['duration']}s]")
        if run.files:
            run.add("sys", f"[{len(run.files)} file(s) created or changed - see the list below]")
        run.status = final  # last, so anything seeing a finished run also sees its files and output
        self._finalize(run)

    def stop(self, run_id, reason="stopped by user"):
        run = self.runs.get(run_id)
        if not run or run.status != "running" or not run.proc:
            return False
        run.kill_reason = run.kill_reason or reason
        run.add("sys", f"[{reason}] sending SIGTERM")

        def kill():
            try:
                os.killpg(run.proc.pid, signal.SIGTERM)
                run.proc.wait(timeout=4)
            except subprocess.TimeoutExpired:
                run.add("sys", "[still running, sending SIGKILL]")
                os.killpg(run.proc.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
        threading.Thread(target=kill, daemon=True).start()
        return True

    def active(self):
        return [r for r in self.runs.values() if r.status == "running"]

    # ---- monitor hook ----------------------------------------------------
    def on_tick(self, snap):
        cfg = settings.get()
        now = time.time()
        for run in self.active():
            rss = memory.tree_rss(run.proc.pid) / 1024**2
            run.peak_rss_mb = max(run.peak_rss_mb, round(rss))
            run.mem.append({"t": round(now - run.started, 1), "rss_mb": round(rss),
                            "avail_pct": snap["available_pct"], "level": snap["level"]})
            limit = cfg["max_runtime_sec"]
            if limit and now - run.started > limit:
                self.stop(run.id, f"max runtime of {limit}s reached")
        trip = memory.LEVELS.index(cfg["guard_trip_level"])
        if cfg["guard_enabled"] and self.active() and memory.LEVELS.index(snap["level"]) >= trip:
            self._trip_count += 1
        else:
            self._trip_count = 0
        if self._trip_count >= 2:  # sustained for 2 samples, ignores one-off spikes
            self._trip_count = 0
            self._trip(snap, cfg)

    def _trip(self, snap, cfg):
        reason = (f"memory guard: {snap['level']} ({snap['available_pct']}% available, "
                  f"{snap['available_gb']} GB free, swap {snap['swap_used_gb']} GB)")
        names = []
        for run in self.active():
            self.stop(run.id, reason)
            names.append(run.script)
        msg = f"Memory hit {snap['level'].upper()}: stopped {', '.join(names)}"
        if cfg["unload_models_on_trip"]:
            ok, out = lmstudio.unload_all()
            msg += " and unloaded LM Studio models" if ok else f" (model unload failed: {out})"
        self.events.append({"t": time.time(), "level": snap["level"], "msg": msg})
        self.events[:] = self.events[-50:]
        if sys.platform == "darwin":
            subprocess.Popen(["osascript", "-e",
                              f'display notification "{msg}" with title "AI Harness memory guard"'])

    # ---- persistence -----------------------------------------------------
    def _finalize(self, run):
        d = run.detail()
        d["lines"], d["mem"] = run.lines, run.mem
        try:
            folder = RUNS_DIR / run.id
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "run.json").write_text(json.dumps(d))
        except OSError as e:
            print("could not save run:", e, file=sys.stderr)

    def history(self, limit=100):
        items = {r.id: r.summary() for r in self.runs.values()}
        for f in sorted(RUNS_DIR.glob("*/run.json"), reverse=True)[:limit]:
            if f.parent.name not in items:
                try:
                    d = json.loads(f.read_text())
                    items[d["id"]] = {k: d[k] for k in SUMMARY_KEYS if k in d}
                except (OSError, ValueError, KeyError):
                    pass
        return sorted(items.values(), key=lambda s: s["started"], reverse=True)[:limit]

    def load(self, run_id):
        """Full detail (+lines, mem) for a live or saved run, or None."""
        run = self.runs.get(run_id)
        if run:  # in memory (running, or just finished and not yet flushed to disk)
            d = run.detail()
            d["lines"], d["mem"] = list(run.lines), list(run.mem)
            return d
        f = RUNS_DIR / Path(run_id).name / "run.json"
        try:
            return json.loads(f.read_text())
        except (OSError, ValueError):
            return None


def report_markdown(d, app_version, lm, mem_snap):
    """A paste-ready bug report for a run."""
    tb = d.get("traceback")
    src = ""
    try:
        src = (SCRIPTS_DIR / d["script"]).read_text()
    except OSError:
        pass
    lines = [f"# Run report: {d['script']}", "",
             f"- Status: **{d['status']}** (exit code {d['exit_code']})",
             f"- Duration: {d['duration']}s, peak script memory {d['peak_rss_mb']} MB",
             f"- Run id: `{d['id']}`  |  AI Harness {app_version}",
             f"- LM Studio: {'online' if lm['ok'] else 'OFFLINE - ' + str(lm['error'])}; loaded models: "
             f"{', '.join(m['id'] for m in lm['models'] if m['loaded']) or 'none'}",
             f"- Memory now: {mem_snap['level']} ({mem_snap['available_pct']}% available of "
             f"{mem_snap['total_gb']} GB, swap {mem_snap['swap_used_gb']} GB)"]
    if d.get("kill_reason"):
        lines.append(f"- Stop reason: {d['kill_reason']}")
    if d.get("hints"):
        lines += ["", "## Diagnosis"] + [f"- **{h['title']}**: {h['detail']}" for h in d["hints"]]
    if tb:
        lines += ["", "## Traceback", "```", tb["text"], "```"]
    out = d.get("output", "")
    tail = "\n".join(out.splitlines()[-80:])
    lines += ["", "## Output (last 80 lines)", "```", tail, "```"]
    if d.get("files"):
        lines += ["", "## Files created/changed"] + [f"- {f['status']}: {f['path']} ({f['size']} bytes)" for f in d["files"][:40]]
    if d.get("mem"):
        step = max(1, len(d["mem"]) // 12)
        lines += ["", "## Memory timeline", "| t (s) | script MB | system avail % | level |", "|---|---|---|---|"]
        lines += [f"| {m['t']} | {m['rss_mb']} | {m['avail_pct']} | {m['level']} |" for m in d["mem"][::step]]
    if src:
        lines += ["", "## Script", "```python", src, "```"]
    return "\n".join(lines)
