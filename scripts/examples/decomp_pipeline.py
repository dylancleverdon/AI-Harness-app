#!/usr/bin/env python3
"""
decomp_pipeline.py - from a Ghidra project to readable C++ that compiles and links,
in one resumable local pipeline. (pseudo_to_cpp.py and DECOMP_FIXER.py, combined.)

Stages, in order:
  export    Ghidra's function list and pseudocode -> ghidra/ghidra_export.json
            (HTTP/MCP plugin, analyzeHeadless, or a script you run in Ghidra's GUI).
            The headless/GUI export also records Ghidra's data types and function
            signatures, for later use.
  rewrite   a local model rewrites each function as clean C++ and names the ones
            Ghidra only had a placeholder for -> rewrite/rewritten.cpp
  split     libclang splits that file into build/shared.h, globals.cpp and one file
            per function; de-ghidra cleanup; header gate; compile every function
  fix       dependency-ordered repair of the functions that don't compile:
            deterministic fixes, then the model, then quarantine
  recover   quarantined functions are rebuilt from their Ghidra pseudocode
  link      build the whole program, stub what's missing, report what's left
  improve   rounds of checks and small fixes, worst functions first (see below)
  organize  modules + classes, a final privacy check, then PROJ/final/: the code as a
            normal C++ project that builds on its own

The improve stage: the model never writes a whole function again. Each check finds
one small problem; a rule fixes it, or the model plans one edit and rewrites only the
few lines involved (or just picks a name). A change is kept only if the function still
compiles, still makes the calls Ghidra's version makes, and — for functions that only
compute from their arguments — still returns the same as Ghidra's version on thousands
of inputs. Each function has a notes file (build/improve/notes/) with its goal and what
was tried, which the model reads on its next task; every version is kept in
build/improve/history/. Rejected tasks are parked until a different model is loaded.
Checks: privacy (identifying strings/comments, blocklisted words in names), Ghidra
helpers (CONCAT/ZEXT/SUB), divide-by-multiply, stack-protector code, pointer arithmetic
that is a struct member, casts that change nothing, hand-written strlen/memcpy-style
functions, clang-tidy clean-ups, compiler warnings, decompiler names (param_1, uVar3),
calls with the wrong arguments, behaviour against Ghidra's version (missing calls,
side-by-side tests, sanitizers), goto. Across files: duplicate functions, structs with
the same layout, field / global / function names, repeated magic numbers.

Usage:
  python3 decomp_pipeline.py --workdir PROJ                    everything, or carry on
  python3 decomp_pipeline.py --workdir PROJ --to rewrite       stop after the rewrite
  python3 decomp_pipeline.py --workdir PROJ --from fix         e.g. after loading a
                                                               bigger model
  python3 decomp_pipeline.py --workdir PROJ --project ~/G/App.gpr --ghidra-home ~/ghidra_11.3
                                                               export headless first

Running the same command again carries on where it stopped, in any stage. Ctrl+C
pauses. Each stage skips work that's already done.

Models: always whatever model is loaded in LM Studio, checked again at the start of
each stage, so you can swap models between stages (--pause-between-stages waits for
you at each stage that uses the model). Tasks the loaded model couldn't do are tried
again when a different model is loaded. --backend ollama uses Ollama instead.

Redoing work never deletes anything:
  --redo rewrite    rewrite every function again (--functions A B for just those).
                    Each new rewrite REPLACES the old one in place as it finishes;
                    until then the old one stays in rewritten.cpp.
  --redo-suspect    the same, for the functions flagged for a second look
  --redo export     fetch every function's pseudocode from Ghidra again, replacing
                    entries in place. Functions whose pseudocode changed are then
                    rewritten again automatically.
  --redo split      rebuild the build folder from the current rewrite: function files
  --redo fix        are overwritten with fresh copies (the model's earlier fixes are
                    replaced), then compiled and fixed again
  --redo recover    give the quarantined functions another recovery pass
  --redo link       relink from scratch (placeholders regenerated)
  --redo improve    try every parked improve task again
  Before a redo replaces anything, the current files are copied to
  PROJ/snapshots/<time>-<what>/ (--no-snapshot to skip). Nothing is ever removed from
  snapshots/; delete old ones yourself when you no longer need them.
  Functions whose upstream code changed (rewritten again) are refreshed in the build
  automatically; functions that didn't change keep the fixes they already have.

Folder layout (--workdir PROJ):
  REPORT.md, report.json   summary of every stage (the numbers to compare runs by)
  pipeline_state.json      which stages finished, with which model
  pipeline.log             one line per stage event
  ghidra/                  ghidra_export.json, callgraph.json, pseudocode/
  rewrite/                 rewritten.cpp, names.txt, function_index.json, progress.json
  build/                   shared.h, globals.cpp, funcs/, quarantine/, stubs.cpp,
                           manifest.json, worklist.log and the *_report.txt files
  build/improve/           notes/ and history/ per function, state.json
  final/                   the finished project (the previous one goes to snapshots/)
  privacy_blocklist.txt    words that identify the original program (yours to edit)
  privacy_report.txt       what the final privacy check found
  snapshots/               copies taken before a redo replaced anything

Carrying on from the old scripts (files are copied, never moved):
  --adopt-rewrite DIR   a pseudo_to_cpp.py output folder (--out)
  --adopt-build DIR     a DECOMP_FIXER.py --workdir

Needs: LM Studio (or Ollama) with a model loaded; clang++ or g++; pip install libclang;
for the export, Ghidra with the MCP plugin, or a Ghidra install for --project.
"""

from __future__ import annotations

import argparse
import atexit
import contextlib
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, as_completed, wait
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

PIPELINE_VERSION = "2026-10-18.1"
STAGES = ["export", "rewrite", "split", "fix", "recover", "link", "improve", "organize"]
MODEL_STAGES = {"rewrite": "rewrite", "fix": "fix"}   # stage -> which model it uses


# ============================================================================
# Pipeline plumbing: folders, log, state, lock, snapshots
# ============================================================================

class Paths:
    def __init__(self, root: Path):
        self.root = root
        self.ghidra = root / "ghidra"
        self.rewrite = root / "rewrite"
        self.build = root / "build"
        self.snapshots = root / "snapshots"
        self.state = root / "pipeline_state.json"
        self.report_md = root / "REPORT.md"
        self.report_json = root / "report.json"
        self.log = root / "pipeline.log"
        self.lock = root / ".pipeline.lock"
        self.export = self.ghidra / "ghidra_export.json"
        self.callgraph = self.ghidra / "callgraph.json"
        self.pseudocode = self.ghidra / "pseudocode"
        self.rewritten = self.rewrite / "rewritten.cpp"
        self.rewritten_dir = self.rewrite / ".rewritten"
        self.progress = self.rewrite / "progress.json"
        self.index = self.rewrite / "function_index.json"
        self.names = self.rewrite / "names.txt"
        self.manifest = self.build / "manifest.json"
        self.no_snapshot = False

    def make(self):
        for d in (self.root, self.ghidra, self.pseudocode, self.rewrite,
                  self.rewritten_dir, self.build):
            d.mkdir(parents=True, exist_ok=True)


# The progress bar on screen now (one at a time), and the stage it belongs to,
# e.g. "[3/6 split]". Every stage's long loop shows one; log lines scroll above it.
BAR: dict = {"p": None, "stage": ""}

STAGE_INFO = {
    "export": "getting every function's pseudocode from Ghidra (once — after that "
              "Ghidra can be closed)",
    "rewrite": "the model rewrites each function as readable C++, gives placeholder "
               "names real ones, and strips identifying strings",
    "split": "libclang splits the rewrite into shared.h + one file per function, "
             "repairs the header, then compiles every function on its own",
    "fix": "functions that don't compile are repaired, callees first: quick "
           "deterministic fixes, then the model; what can't be fixed is quarantined",
    "recover": "quarantined functions are rebuilt from their Ghidra pseudocode",
    "link": "the whole program is compiled and linked; anything still missing gets "
            "a placeholder and is listed in link_report.txt",
    "improve": "checks find small problems, worst functions first; each is fixed by a "
               "rule or one small planned edit, and kept only if it still compiles and "
               "behaves like Ghidra's version",
    "organize": "the improved code is arranged into modules and classes, checked for "
                "anything identifying, and written to final/ as a project that builds",
}


def say(text: str) -> None:
    """Print a line — above the live progress bar when one is showing."""
    p = BAR["p"]
    if p is not None and not p.stop_flag.is_set():
        p.log(text)
    else:
        print(text, flush=True)


_BAR_TL = threading.local()       # the bar item this thread is working on


def phase(text: str) -> None:
    """Tell the bar what this thread's item is doing now."""
    p = BAR["p"]
    if p is not None:
        with p.lock:
            key = getattr(_BAR_TL, "key", None)
            if key in p.active:
                p.active[key][1] = text
            else:
                for v in p.active.values():
                    v[1] = text


def plog(P: Paths, msg: str) -> None:
    """A pipeline-level line: printed and appended to pipeline.log."""
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    say(line)
    try:
        with open(P.log, "a") as f:
            f.write(line + "\n")
    except OSError:
        pass


def write_atomic(path: Path, text: str) -> None:
    """Write via a temporary file, so an interrupted write never leaves half a file."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text)
    tmp.replace(path)


def set_aside(path: Path, why: str) -> Path:
    """Keep an unreadable file under a new name instead of overwriting it."""
    dest = path.with_name(f"{path.name}.unreadable-{time.strftime('%Y%m%d-%H%M%S')}")
    path.replace(dest)
    print(f"WARNING: {path.name} couldn't be read ({why}); kept it as {dest.name} "
          f"and started a new one.", flush=True)
    return dest


def load_pstate(P: Paths) -> dict:
    try:
        st = json.loads(P.state.read_text())
    except Exception:
        st = {}
    st.setdefault("stages", {})
    return st


def mark_stage(P: Paths, stage: str, **info) -> None:
    st = load_pstate(P)
    entry = st["stages"].get(stage, {})
    entry.update(info, at=time.strftime("%Y-%m-%d %H:%M:%S"))
    st["stages"][stage] = entry
    st["version"] = PIPELINE_VERSION
    write_atomic(P.state, json.dumps(st, indent=2))


def snapshot(P: Paths, reason: str, items: list[Path]) -> Optional[Path]:
    """Copy files/folders into snapshots/<time>-<reason>/ before they get replaced."""
    if P.no_snapshot:
        return None
    items = [p for p in items if p.exists()]
    if not items:
        return None
    dest = P.snapshots / f"{time.strftime('%Y%m%d-%H%M%S')}-{reason}"
    n = 1
    while dest.exists():
        n += 1
        dest = P.snapshots / f"{time.strftime('%Y%m%d-%H%M%S')}-{reason}-{n}"
    for p in items:
        target = dest / p.relative_to(P.root)
        target.parent.mkdir(parents=True, exist_ok=True)
        if p.is_dir():
            shutil.copytree(p, target)
        else:
            shutil.copy2(p, target)
    plog(P, f"  snapshot of the current files before '{reason}': {dest}")
    return dest


def acquire_lock(P: Paths, force: bool) -> None:
    """One run per project folder at a time."""
    if P.lock.exists():
        alive = False
        try:
            pid = int(P.lock.read_text().split()[0])
            if pid != os.getpid():
                os.kill(pid, 0)
                alive = True
        except PermissionError:
            alive = True
        except (ProcessLookupError, ValueError, IndexError, OSError):
            alive = False
        if alive and not force:
            sys.exit(f"Another run is working in {P.root} (process {pid}). Stop it first, "
                     f"or pass --force if that's wrong.")
    P.lock.write_text(f"{os.getpid()} {time.time():.0f}\n")

    def release():
        try:
            if P.lock.read_text().split()[0] == str(os.getpid()):
                P.lock.unlink()
        except Exception:
            pass
    atexit.register(release)


# ============================================================================
# Model client (LM Studio or Ollama), shared by every stage
# ============================================================================

class ModelGate:
    """Limits how many requests go to the model at once. The limit can change while
    running (--auto-parallel)."""

    def __init__(self, limit):
        self.limit, self.active, self.peak = max(1, limit), 0, 0
        self.cv = threading.Condition()

    def acquire(self):
        with self.cv:
            while self.active >= self.limit:
                self.cv.wait()
            self.active += 1
            self.peak = max(self.peak, self.active)

    def release(self):
        with self.cv:
            self.active -= 1
            self.cv.notify_all()

    def set_limit(self, n):
        with self.cv:
            self.limit = max(1, n)
            self.peak = self.active
            self.cv.notify_all()


GATE = {"gate": None, "tuner": None}


class ModelError(Exception):
    pass


# Set when the run is being stopped (Ctrl+C, or the app's Stop button = SIGTERM).
# Stopping also kills the compilers, so a compile that "fails" now means nothing:
# workers stop before they change any file (StopRun) instead of acting on it.
STOPPING = threading.Event()


class StopRun(Exception):
    pass


def _on_sigterm(signum, frame):
    STOPPING.set()
    raise KeyboardInterrupt                   # same clean stop as Ctrl+C


class ServerSaid(Exception):
    """The model server answered this request with an error message."""


# What the model is doing right now, for the progress bar and the stall warning:
# requests waiting for an answer, answers received, when anything last arrived
# (thinking counts), and answers that were only thinking with no actual reply.
MODEL_ACTIVITY = {"waiting": 0, "answered": 0, "last": 0.0, "thinking_only": 0,
                  "busy": 0.0, "busy_since": 0.0}
_ACT_LOCK = threading.Lock()
_TL = threading.local()          # per-thread count of model calls (per function)


def _model_started():
    with _ACT_LOCK:
        if MODEL_ACTIVITY["waiting"] == 0:
            MODEL_ACTIVITY["busy_since"] = time.time()
        MODEL_ACTIVITY["waiting"] += 1


def _model_finished():
    with _ACT_LOCK:
        MODEL_ACTIVITY["waiting"] -= 1
        if MODEL_ACTIVITY["waiting"] == 0:
            MODEL_ACTIVITY["busy"] += time.time() - MODEL_ACTIVITY["busy_since"]


def model_busy_seconds() -> float:
    """Total time at least one request was with the model (so far)."""
    with _ACT_LOCK:
        extra = time.time() - MODEL_ACTIVITY["busy_since"] if MODEL_ACTIVITY["waiting"] else 0
        return MODEL_ACTIVITY["busy"] + extra


class ModelUse:
    """How busy the model was during one stage: "model busy 93%"."""

    def __init__(self):
        self.t0, self.b0 = time.time(), model_busy_seconds()

    def share(self) -> Optional[float]:
        el = time.time() - self.t0
        return (model_busy_seconds() - self.b0) / el if el > 1 else None

    def text(self) -> str:
        s = self.share()
        return f"model busy {s * 100:.0f}%" if s is not None else "model busy —"


def calls_on_this_thread() -> int:
    return getattr(_TL, "calls", 0)


def last_reply() -> dict:
    """How this thread's last model reply ended (finish reason, thinking, size)."""
    return getattr(_TL, "last", {}) or {}


TOO_LONG = re.compile(r"context|too (?:long|large|many tokens)|exceed|n_ctx|max.*tokens", re.I)


def why_no_code(reply: str) -> str:
    info = last_reply()
    thought = info.get("thought", 0)
    if info.get("error"):
        if TOO_LONG.search(info["error"]):
            return "cut off: the prompt is too long for the model's context"
        return f"server error: {info['error'][:120]}"
    if info.get("finish") == "length":
        return ("cut off at the token limit while thinking" if thought > info.get("chars", 0)
                else "cut off at the token limit")
    if not (reply or "").strip():
        return "only thinking, no answer" if thought else "empty reply"
    return "no code block in the reply"


class ModelClient:
    """Talks to LM Studio's local server (OpenAI-style) or Ollama. Requests are
    streamed, so a long answer never trips a timeout while it's still arriving."""

    def __init__(self, backend: str, api: Optional[str] = None):
        self.kind = backend
        if backend == "lmstudio":
            base = (api or os.environ.get("OPENAI_BASE_URL") or "http://localhost:1234/v1")
            base = base.rstrip("/")
            if not base.endswith("/v1"):
                base += "/v1"
        else:
            base = (api or os.environ.get("OLLAMA_HOST") or "http://localhost:11434")
            if not base.startswith("http"):
                base = "http://" + base
            base = base.rstrip("/")
        self.base = base + "/"
        self.calls = 0

    @property
    def name(self) -> str:
        return "LM Studio" if self.kind == "lmstudio" else "Ollama"

    def _get(self, url: str, timeout=20):
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.load(r)

    def models(self) -> Optional[list[str]]:
        """Usable models, the loaded ones first. None if the server isn't reachable."""
        try:
            if self.kind == "lmstudio":
                root = self.base[:-len("v1/")]
                try:   # LM Studio's own API says which models are actually loaded
                    data = self._get(root + "api/v0/models").get("data", [])
                    loaded = [m["id"] for m in data if m.get("state") == "loaded"
                              and m.get("type") != "embeddings"]
                    if loaded:
                        return loaded
                except Exception:
                    pass
                ids = [m["id"] for m in self._get(self.base + "models").get("data", [])]
                return [i for i in ids if "embed" not in i.lower()]
            running = []
            try:
                running = [m["name"] for m in self._get(self.base + "api/ps").get("models", [])]
            except Exception:
                pass
            tags = [m["name"] for m in self._get(self.base + "api/tags").get("models", [])]
            return running + [t for t in tags if t not in running]
        except Exception:
            return None

    def loaded_context(self, model: str) -> Optional[int]:
        """The context length LM Studio loaded this model with, if it says."""
        if self.kind != "lmstudio":
            return None
        try:
            for m in self._get(self.base[:-len("v1/")] + "api/v0/models").get("data", []):
                if m.get("id") == model:
                    for k in ("loaded_context_length", "context_length"):
                        if isinstance(m.get(k), int):
                            return m[k]
        except Exception:
            pass
        return None

    def resolve(self, wanted: Optional[str]) -> str:
        """The model to use: the one asked for if it's there, else the loaded one."""
        ids = self.models()
        if ids is None:
            raise ModelError(f"{self.name} isn't reachable at {self.base}. "
                             + ("In LM Studio, open the Developer tab, load a model and "
                                "switch the server on." if self.kind == "lmstudio" else
                                "Is the Ollama app running?"))
        if not ids:
            raise ModelError(f"{self.name} is running but has no model loaded. Load one, "
                             f"then run this again.")
        if not wanted:
            return ids[0]
        if wanted in ids:
            return wanted
        close = [i for i in ids if wanted.lower().replace(":", "-") in i.lower()]
        if close:
            return close[0]
        print(f"  model '{wanted}' isn't loaded in {self.name}; using '{ids[0]}' "
              f"(available: {', '.join(ids[:6])})", flush=True)
        return ids[0]

    def chat(self, model, messages, max_out=None, temperature=0.2, ctx=None,
             timeout=1800, fatal=True) -> Optional[str]:
        """The model's reply with any <think> block removed. On failure: exit with
        advice (fatal=True) or return None."""
        gate, tuner = GATE["gate"], GATE["tuner"]
        if gate:
            gate.acquire()
        sent = time.time()
        self.calls += 1
        _TL.calls = calls_on_this_thread() + 1
        _model_started()
        MODEL_ACTIVITY["last"] = time.time()
        try:
            if self.kind == "lmstudio":
                body = {"model": model, "messages": messages, "stream": True,
                        "temperature": temperature, "repeat_penalty": 1.1}
                if max_out:
                    body["max_tokens"] = max_out
                url = self.base + "chat/completions"
            else:
                opts = {"temperature": temperature, "repeat_penalty": 1.1}
                if ctx:
                    opts["num_ctx"] = ctx
                if max_out:
                    opts["num_predict"] = max_out   # stops a model stuck repeating itself
                body = {"model": model, "messages": messages, "stream": True,
                        "think": False, "options": opts}
                url = self.base + "api/chat"
            req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
            text, first_word, thought, finish = _read_stream(req, self.kind, timeout)
        except (urllib.error.HTTPError, ServerSaid) as e:
            # the server is there but turned this request down (often: the prompt is
            # longer than the model's context). Not a reason to stop the whole run.
            detail = (e.read().decode(errors="replace") if isinstance(e, urllib.error.HTTPError)
                      else str(e))
            try:
                detail = json.loads(detail).get("error", detail)
                if isinstance(detail, dict):
                    detail = detail.get("message", str(detail))
            except Exception:
                pass
            detail = " ".join(str(detail).split())[:300]
            _TL.last = {"error": detail, "finish": "error", "thought": 0, "chars": 0,
                        "max_out": max_out, "raw": ""}
            if MODEL_ACTIVITY.setdefault("errors", 0) < 3 or "context" in detail.lower():
                say(f"  !! {self.name} turned a request down: {detail}")
            MODEL_ACTIVITY["errors"] += 1
            return "" if fatal else None
        except Exception as e:
            if fatal:
                sys.exit(f"\nCould not reach {self.name} at {self.base} ({e}). Check the "
                         f"server is on and the model is loaded.")
            return None
        finally:
            _model_finished()
            if gate:
                gate.release()
        MODEL_ACTIVITY["answered"] += 1
        if tuner:
            tuner.record(sent, sum(len(m["content"]) for m in messages), first_word, len(text))
        out = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
        inline = len(text) - len(out)
        if "<think>" in out:                  # thinking that never finished (cut off)
            i = out.index("<think>")
            inline += len(out) - i
            out = out[:i]
        out = out.strip()
        thought += inline
        _TL.last = {"finish": finish, "thought": thought, "chars": len(out),
                    "max_out": max_out, "raw": text}
        if not out and thought:
            MODEL_ACTIVITY["thinking_only"] += 1
            if MODEL_ACTIVITY["thinking_only"] in (1, 10, 100):
                say(f"  !! the model spent its whole answer thinking ({thought} characters) "
                    f"and wrote no reply. Turn thinking off for this model in LM Studio, "
                    f"or give it more room (--ctx).")
        return out

    def ping(self, model) -> float:
        """A tiny request, to prove the model really answers. Seconds it took."""
        t0 = time.time()
        reply = self.chat(model, [{"role": "user", "content": "Reply with the word OK."}],
                          max_out=200, temperature=0, timeout=600, fatal=False)
        if reply is None:
            raise ModelError(f"{self.name} lists '{model}' but didn't answer a test "
                             f"request. Check the model is loaded and the server is on.")
        return time.time() - t0


def _read_stream(req, kind, timeout=1800):
    """Reads a streamed reply. Returns (text, seconds until the first word, characters
    of separate thinking, why it ended: "stop" / "length" / ...). Thinking (LM
    Studio's reasoning_content) is not part of the reply, but it shows the model
    is working."""
    t0, first, parts, thought, finish = time.time(), None, [], 0, None
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        for raw in resp:
            line = raw.decode(errors="replace").strip()
            if not line:
                continue
            if kind == "lmstudio":
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                j = json.loads(data)
                if j.get("error"):                # LM Studio refused / failed this one
                    e = j["error"]
                    raise ServerSaid(e.get("message") if isinstance(e, dict) else str(e))
                ch = (j.get("choices") or [{}])[0]
                finish = ch.get("finish_reason") or finish
                d = ch.get("delta") or ch.get("message") or {}
                piece = d.get("content") or ""
                think = d.get("reasoning_content") or d.get("reasoning") or ""
                if think:
                    thought += len(think)
                    if first is None:
                        first = time.time() - t0
            else:
                j = json.loads(line)
                if j.get("error"):
                    raise RuntimeError(j["error"])
                piece = (j.get("message") or {}).get("content") or ""
                think = (j.get("message") or {}).get("thinking") or ""
                thought += len(think)
                finish = j.get("done_reason") or finish
            MODEL_ACTIVITY["last"] = time.time()
            if piece:
                if first is None:
                    first = time.time() - t0
                parts.append(piece)
            if kind == "ollama" and j.get("done"):
                break
    return "".join(parts), (first if first is not None else time.time() - t0), thought, finish


CLIENT: dict = {"c": None}


def work_pool(workers: int, items: list, fn, every=0, checkpoint=None) -> None:
    """fn(item) for every item, on `workers` threads, handed out in order. While
    one item waits for the model, the others compile, test and prepare their own
    request, so the model's next job is ready the moment it finishes one (the
    model gate still limits how many requests it gets at once)."""
    pool = ThreadPoolExecutor(max_workers=max(1, workers))
    futs = [pool.submit(fn, it) for it in items]
    last = time.time()
    try:
        for k, fu in enumerate(as_completed(futs), 1):
            try:
                fu.result()
            except StopRun:
                raise KeyboardInterrupt
            # save every `every` items, and at least every 30 seconds
            if checkpoint and ((every and k % every == 0) or time.time() - last > 30):
                checkpoint()
                last = time.time()
    except BaseException:
        pool.shutdown(wait=False, cancel_futures=True)
        raise
    pool.shutdown(wait=True)


def ask_model(model, messages, ctx, max_out=None, temperature=0.2):
    """The rewrite stage's model call (exits with advice if the server is gone).
    The answer may use all the room the context leaves (see answer_room)."""
    room = answer_room(ctx, sum(len(m["content"]) for m in messages))
    return CLIENT["c"].chat(model, messages, max(max_out or 0, room), temperature, ctx)


# ============================================================================
# Compiler
# ============================================================================

COMPILER = {"cmd": None, "clang": True}


def find_compiler(choice):
    """Path of the C++ compiler to use (auto: clang++, else g++), or None."""
    if choice == "none":
        return None
    for name in (["clang++", "g++"] if choice == "auto" else [choice]):
        path = shutil.which(name) or (name if os.path.isfile(name) else None)
        if path:
            try:
                ver = subprocess.run([path, "--version"], capture_output=True, text=True,
                                     timeout=30).stdout
            except Exception:
                continue
            COMPILER["cmd"], COMPILER["clang"] = path, "clang" in ver.lower()
            return path
    return None


# ============================================================================
# Stage: export (Ghidra)
# ============================================================================

# ---------------------------------------------------------------- Ghidra

def ghidra_request(base, path, params=None):
    """Returns the reply text (also for error replies), or None if nothing answered."""
    url = base.rstrip("/") + "/" + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=180) as r:
            return r.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        try:
            return e.read().decode(errors="replace")
        except Exception:
            return None
    except Exception:
        return None


def _json(text):
    try:
        return json.loads(text) if text and text.lstrip().startswith("{") else None
    except Exception:
        return None


def _items(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in ("items", "functions", "results", "data"):
            if isinstance(data.get(k), list):
                return data[k]
    return []


def _longest_code(obj):
    if isinstance(obj, str):
        return obj if "{" in obj and len(obj) > 10 else ""
    best = ""
    vals = obj.values() if isinstance(obj, dict) else obj if isinstance(obj, list) else []
    for v in vals:
        c = _longest_code(v)
        if len(c) > len(best):
            best = c
    return best


FUNC_LINE = re.compile(r"^\s*(.+?)\s+(?:at|@)\s+(?:(\w+):)?(?:0x)?([0-9a-fA-F]+)\s*$")


class Ghidra:
    """Talks to either kind of Ghidra MCP plugin: the original one (plain text replies,
    /list_functions, /decompile_function) or JSON ones ({"success": ..., "data": ...})."""

    def __init__(self, base):
        self.base = base
        self.style = None
        self.decomp = None          # the JSON plugin's pseudocode command, once found
        self.notice = None          # a one-off message for the person running this
        self.probe_lock = threading.Lock()

    def functions(self):
        """[(name, address)] in program order, or exit with advice."""
        found = self._json_list() or self._text_list()
        if not found:
            sys.exit(
                f"Couldn't get the list of functions from Ghidra at {self.base}\n"
                "- Open the program in Ghidra's CodeBrowser and let the analysis finish.\n"
                "- Make sure the MCP plugin is ticked under File > Configure > Developer.\n"
                "- If its port isn't 8080, add --ghidra http://127.0.0.1:PORT/\n"
                f"Test it with:  curl \"{self.base.rstrip('/')}/functions\"")
        return sorted(set(found), key=lambda f: f[1])

    def _json_list(self):
        found, seen, offset, page, paging, last = [], set(), 0, 1, "offset", None
        for _ in range(100000):
            params = ({"offset": offset, "limit": 1000} if paging == "offset"
                      else {"page": page, "page_size": 1000, "limit": 1000})
            j = _json(ghidra_request(self.base, "functions", params))
            if not j or not j.get("success"):
                break
            last = j.get("data")
            batch, new = _items(last), 0
            for it in batch:
                if not isinstance(it, dict) or it.get("external") or it.get("is_external") \
                        or it.get("isExternal"):
                    continue
                name = it.get("name") or it.get("function") or ""
                a = str(it.get("address") or it.get("entry") or it.get("entry_point") or "")
                m = re.search(r"(?:0x)?([0-9a-fA-F]+)$", a)
                if name and m and not a.upper().startswith("EXTERNAL") \
                        and int(m.group(1), 16) not in seen:
                    seen.add(int(m.group(1), 16))
                    found.append((name, int(m.group(1), 16)))
                    new += 1
            if not batch:
                break
            if not new:
                if paging == "offset" and page == 1:
                    paging, page = "page", 2          # it ignored "offset"; try pages
                    continue
                break
            offset += len(batch)
            page += 1
            total = last.get("total") if isinstance(last, dict) else None
            if (isinstance(total, int) and len(found) >= total) or \
                    (isinstance(last, dict) and last.get("has_more") is False):
                break
        if found:
            self.style = "json"
            total = last.get("total") if isinstance(last, dict) else None
            if isinstance(total, int) and len(found) < total:
                print(f"WARNING: Ghidra says it has {total} functions but only "
                      f"{len(found)} could be listed. Only those will be rewritten.")
        return found

    def _text_list(self):
        text = ghidra_request(self.base, "list_functions")
        if not text or _json(text) is not None:
            return []
        found = []
        for line in text.splitlines():
            m = FUNC_LINE.match(line)
            if m and (m.group(2) or "").upper() != "EXTERNAL":
                found.append((m.group(1).strip(), int(m.group(3), 16)))
        if found:
            self.style = "text"
        return found

    def pseudocode(self, name, addr):
        if self.style == "json":
            return self._json_decompile(addr)
        text = ghidra_request(self.base, "decompile_function", {"address": hex(addr)})
        if text and "{" in text and _json(text) is None:
            return text.strip()
        return None

    def _json_decompile(self, addr):
        a = f"{addr:x}"

        def call(path, params):
            path = path.replace("{A}", a).replace("{0xA}", "0x" + a)
            params = {k: v.replace("{A}", a).replace("{0xA}", "0x" + a)
                      for k, v in params.items()}
            return _longest_code(_json(ghidra_request(self.base, path, params)) or {}) or None

        if self.decomp:
            return call(*self.decomp)
        with self.probe_lock:                 # only one thread works out the command
            if self.decomp:
                return call(*self.decomp)
            return self._probe(addr, a, call)

    def _probe(self, addr, a, call):
        tries = []
        for A in ("{A}", "{0xA}"):
            for key in ("address", "addr"):
                for path in ("decompile", "decompile_function", "function/decompile",
                             "functions/decompile", "decompiler", "decomp"):
                    tries.append((path, {key: A}))
            tries += [(f"functions/{A}/decompile", {}), (f"decompile/{A}", {}),
                      (f"function/{A}/decompile", {}), (f"functions/{A}", {"decompile": "true"})]
        for path, params in tries:
            code = call(path, params)
            if code:
                self.decomp = (path, params)
                self.notice = (f"(Your Ghidra plugin gives pseudocode at "
                               f"/{path.replace('{A}', '…').replace('{0xA}', '…')})")
                return code
        sys.exit("Your Ghidra plugin listed the functions, but none of the usual commands "
                 "for pseudocode worked. Send a screenshot of this to whoever is helping you:\n"
                 f"  curl \"{self.base.rstrip('/')}/decompile?address={a}\"")


# ---------------------------------------------------------------- Ghidra cache
# Everything this pipeline needs from Ghidra is written once to ghidra_export.json:
# the function list and each function's pseudocode (version 2 exports from the
# headless/GUI script also carry "signatures" {addr: prototype} and "datatypes",
# Ghidra's structs/unions/enums/typedefs). After that the pipeline reads the file
# and Ghidra can be closed. The recover stage reads the same file to rebuild
# quarantined functions straight from their pseudocode.

EXPORT_VERSION = 1      # what the HTTP plugin path writes (no types/signatures)


class GhidraCache:
    """Drop-in stand-in for Ghidra that serves functions() and pseudocode() from
    ghidra_export.json. A live Ghidra is used only to build the file (first run
    or --refresh-ghidra) and to fill the rare gap the export is missing."""

    def __init__(self, export_path: Path, live: "Ghidra | None"):
        self.path = export_path
        self.live = live
        self.notice = None
        self.style = getattr(live, "style", None)
        self._lock = threading.Lock()
        self._dirty = 0
        self._last_save = 0.0
        self.refresh: set = set()       # keys to fetch again even though cached
        self.data = {"version": EXPORT_VERSION, "ghidra": getattr(live, "base", None),
                     "functions": [], "pseudocode": {}}
        if export_path.exists():
            try:
                loaded = json.loads(export_path.read_text())
                if loaded.get("functions"):
                    self.data = loaded
                    self.data.setdefault("pseudocode", {})
            except Exception as e:
                set_aside(export_path, str(e))     # keep it rather than overwrite it

    # -- read interface (same shape as Ghidra) --------------------------------

    def functions(self):
        if self.data.get("functions"):
            return [(f["name"], int(f["addr"], 16) if isinstance(f["addr"], str)
                     else f["addr"]) for f in self.data["functions"]]
        if not self.live:
            sys.exit(f"No {self.path.name} and Ghidra isn't reachable. Open the program "
                     f"in Ghidra (with the MCP plugin) once so the export can be built, "
                     f"or point --out at the folder that has {self.path.name}.")
        funcs = self.live.functions()
        self.style = self.live.style
        self.data["functions"] = [{"name": n, "addr": f"{a:x}"} for n, a in funcs]
        self._save(force=True)
        return funcs

    def pseudocode(self, name, addr):
        key = f"{addr:x}"
        with self._lock:
            hit = self.data["pseudocode"].get(key)
            again = key in self.refresh
        if hit is not None and not (again and self.live):
            return hit or None
        if not self.live:
            return None
        code = self.live.pseudocode(name, addr)
        if getattr(self.live, "notice", None):
            self.notice = self.live.notice
            self.live.notice = None
        with self._lock:
            if code or not hit:          # a failed re-fetch keeps what was there
                self.data["pseudocode"][key] = code or ""
            self.refresh.discard(key)
            self._dirty += 1
        self._save()
        return code or hit or None

    # -- building the export --------------------------------------------------

    def _save(self, force=False):
        with self._lock:
            now = time.time()
            if not force and (self._dirty < 50 and now - self._last_save < 20):
                return
            tmp = self.path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(self.data))
            tmp.replace(self.path)
            self._dirty, self._last_save = 0, now

    def have_pseudocode(self, addr) -> bool:
        return bool(self.data["pseudocode"].get(f"{addr:x}"))

    def build_full_export(self, parallel=4, progress_print=print, refresh=False):
        """Fetch pseudocode for every function so the file is complete and Ghidra
        can be closed. Resumable: skips functions already in the cache. refresh:
        fetch every function again, replacing each entry as its new one arrives
        (the old entry stays until then, so stopping halfway loses nothing)."""
        if refresh and self.live:
            funcs = self.live.functions()           # the list may have changed too
            self.style = self.live.style
            with self._lock:
                self.data["functions"] = [{"name": n, "addr": f"{a:x}"} for n, a in funcs]
                self.refresh = {f"{a:x}" for _, a in funcs}
            self._save(force=True)
        elif refresh:
            progress_print("--redo export: Ghidra isn't reachable, so nothing was "
                           "fetched again; using the existing export.")
            return
        funcs = self.functions()
        missing = [(n, a) for n, a in funcs if not self.have_pseudocode(a)
                   or f"{a:x}" in self.refresh]
        if not missing:
            progress_print(f"Ghidra export already complete "
                           f"({len(funcs)} functions in {self.path.name}).")
            return
        if not self.live:
            progress_print(f"{len(missing)} function(s) missing from {self.path.name} "
                           f"and Ghidra isn't reachable — continuing with what's cached.")
            return
        progress_print(f"{'Refreshing' if refresh else 'Building'} {self.path.name}: fetching pseudocode for "
                       f"{len(missing)} function(s) from Ghidra (one-time; after this "
                       f"you can close Ghidra)...")
        prog = Progress(len(missing), 0, title="fetching pseudocode from Ghidra")

        def fetch(item):
            n, a = item
            prog.begin(a, n)
            self.pseudocode(n, a)
            prog.end(a)

        try:
            with ThreadPoolExecutor(max_workers=max(1, parallel)) as pool:
                list(pool.map(fetch, missing))
        finally:
            prog.close()
            self._save(force=True)
        got = sum(1 for _, a in funcs if self.have_pseudocode(a))
        progress_print(f"Export complete: {got}/{len(funcs)} functions have pseudocode "
                       f"in {self.path.name}. Ghidra is no longer needed for this program.")

    def write_callgraph(self, path: Path, name_for: "dict[str,str] | None" = None):
        """Call graph derived from the pseudocode, in the JSON edge format the fix
        stage reads (--callgraph) for exact dependency ordering.
        Keyed by final function names when name_for maps a Ghidra name to one."""
        funcs = self.functions()
        by_addr_name = {f"{a:x}": n for n, a in funcs}
        known = set(by_addr_name.values())
        name_for = name_for or {}

        def final(ghidra_name):
            return name_for.get(ghidra_name, ghidra_name)

        graph = {}
        call_re = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(")
        for n, a in funcs:
            code = self.data["pseudocode"].get(f"{a:x}") or ""
            callees = set()
            for m in call_re.findall(strip_comments(code)):
                if m in known and m != n:
                    callees.add(final(m))
            if callees:
                graph[final(n)] = sorted(callees)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(graph, indent=0))
        tmp.replace(path)
        return len(graph)



# ---------------------------------------------------------------- headless export
# The decompiler API only runs inside Ghidra's JVM, so "headless export" means
# launching Ghidra's analyzeHeadless with the embedded GhidraScript below. It
# writes the same ghidra_export.json (merging with any existing one), far faster
# than the one-at-a-time HTTP/MCP export. --emit-ghidra-script writes the script
# out for running by hand from Ghidra's GUI Script Manager instead.

GHIDRA_EXPORT_SCRIPT = r"""
// Ghidra export for decomp_pipeline.py (Java GhidraScript — runs natively on
// Ghidra 11/12, no Jython or PyGhidra needed). Decompiles every function and
// writes ghidra_export.json (format version 2: the function list, pseudocode,
// each function's signature and the program's data types). It MERGES with an
// existing export: functions that already have pseudocode are kept and skipped,
// so it resumes prior progress and is itself resumable (checkpoints every 500
// functions). With the second argument "refresh" every function is decompiled
// again, each entry replaced in place as its new version arrives.
//
// Run it headless (launched automatically by decomp_pipeline.py --project) or
// from the GUI Script Manager. Script arguments: OUTPUT FOLDER [refresh]; if no
// folder is given, DEFAULT_OUT below is used.
//
// @category Decomp
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.decompiler.DecompiledFunction;
import ghidra.program.model.data.Composite;
import ghidra.program.model.data.DataType;
import ghidra.program.model.data.DataTypeComponent;
import ghidra.program.model.data.DataTypeManager;
import ghidra.program.model.data.Structure;
import ghidra.program.model.data.TypeDef;
import ghidra.program.model.data.Union;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class GhidraExport extends GhidraScript {

    static final String DEFAULT_OUT = "";
    static final int DECOMP_TIMEOUT = 60;   // seconds per function
    static final int SAVE_EVERY = 500;

    @Override
    public void run() throws Exception {
        String[] a = getScriptArgs();
        String outDir = (a.length >= 1 && a[0].trim().length() > 0) ? a[0].trim() : DEFAULT_OUT;
        boolean refresh = a.length >= 2 && a[1].trim().equalsIgnoreCase("refresh");
        if (outDir.length() == 0) {
            outDir = askDirectory("Folder for ghidra_export.json", "Export here").getPath();
        }
        File dir = new File(outDir);
        if (!dir.exists()) dir.mkdirs();
        File out = new File(dir, "ghidra_export.json");

        LinkedHashMap<String, String> pseudo = new LinkedHashMap<String, String>();
        int had = loadExisting(out, pseudo);
        println("Export -> " + out.getPath());
        println("Already have pseudocode for " + had + " function(s); "
                + (refresh ? "each will be replaced by a fresh decompile." : "they will be skipped."));

        DecompInterface decomp = new DecompInterface();
        if (!decomp.openProgram(currentProgram)) {
            println("ERROR: could not open the decompiler for this program.");
            return;
        }
        FunctionManager fm = currentProgram.getFunctionManager();
        int total = fm.getFunctionCount();
        println("Program has " + total + " function(s). Decompiling the missing ones...");

        List<String[]> funcs = new ArrayList<String[]>();
        LinkedHashMap<String, String> sigs = new LinkedHashMap<String, String>();
        int done = 0, newly = 0;
        long t0 = System.currentTimeMillis();
        for (Function func : fm.getFunctions(true)) {
            if (monitor.isCancelled()) break;
            if (func.isExternal()) continue;
            long off = func.getEntryPoint().getOffset();
            String addr = Long.toHexString(off);
            funcs.add(new String[] { func.getName(), addr });
            try {
                sigs.put(addr, func.getPrototypeString(false, false));
            } catch (Exception e) {
                // no signature for this one; the pseudocode still has its header
            }
            done++;
            String have = pseudo.get(addr);
            if (!refresh && have != null && have.length() > 0) continue;   // resume: skip done
            String code = "";
            try {
                DecompileResults res = decomp.decompileFunction(func, DECOMP_TIMEOUT, monitor);
                if (res != null && res.decompileCompleted()) {
                    DecompiledFunction d = res.getDecompiledFunction();
                    if (d != null && d.getC() != null) code = d.getC();
                }
            } catch (Exception e) {
                println("  ! " + func.getName() + " @ " + addr + " failed: " + e);
            }
            if (code.length() > 0 || have == null) pseudo.put(addr, code);   // keep old on failure
            newly++;
            if (newly % SAVE_EVERY == 0) {
                write(out, pseudo, funcs, sigs, null);
                double rate = newly / Math.max((System.currentTimeMillis() - t0) / 1000.0, 0.001);
                println(String.format("  %d/%d  (+%d new, %.1f/s)", done, total, newly, rate));
            }
        }
        String types = "[]";
        try {
            types = dataTypesJson(currentProgram.getDataTypeManager());
        } catch (Exception e) {
            println("  (could not export data types: " + e + ")");
        }
        write(out, pseudo, funcs, sigs, types);
        int got = 0;
        for (String v : pseudo.values()) if (v != null && v.length() > 0) got++;
        println("Done. " + got + "/" + total + " functions have pseudocode in " + out.getPath());
        println("Ghidra is no longer needed for this program.");
    }

    // Minimal, dependency-free read of our own export: pull "<hex>":"<escaped>"
    // entries out of the "pseudocode" object so a rerun resumes. Tolerant of a
    // missing/short file (returns 0).
    private int loadExisting(File out, Map<String, String> pseudo) {
        if (!out.exists()) return 0;
        StringBuilder sb = new StringBuilder();
        try {
            BufferedReader r = new BufferedReader(
                new InputStreamReader(new FileInputStream(out), StandardCharsets.UTF_8));
            char[] buf = new char[1 << 16];
            int n;
            while ((n = r.read(buf)) > 0) sb.append(buf, 0, n);
            r.close();
        } catch (Exception e) {
            return 0;
        }
        String s = sb.toString();
        int p = s.indexOf("\"pseudocode\":{");
        if (p < 0) return 0;
        p = s.indexOf('{', p);
        if (p < 0) return 0;
        int i = p + 1, len = s.length(), had = 0;
        while (i < len) {
            while (i < len && s.charAt(i) != '"' && s.charAt(i) != '}') i++;
            if (i >= len || s.charAt(i) == '}') break;
            StringBuilder key = new StringBuilder();
            i = readString(s, i, key);
            while (i < len && s.charAt(i) != ':') i++;
            i++;
            while (i < len && Character.isWhitespace(s.charAt(i))) i++;
            StringBuilder val = new StringBuilder();
            if (i < len && s.charAt(i) == '"') i = readString(s, i, val);
            if (key.length() > 0) {
                pseudo.put(key.toString(), val.toString());
                if (val.length() > 0) had++;
            }
            while (i < len && s.charAt(i) != ',' && s.charAt(i) != '}') i++;
            if (i < len && s.charAt(i) == '}') break;
            i++;
        }
        return had;
    }

    // read a JSON string starting at s[i]=='"', append decoded chars to sb,
    // return index just past the closing quote.
    private int readString(String s, int i, StringBuilder sb) {
        i++;  // skip opening quote
        int len = s.length();
        while (i < len) {
            char c = s.charAt(i++);
            if (c == '"') break;
            if (c == '\\' && i < len) {
                char e = s.charAt(i++);
                switch (e) {
                    case 'n': sb.append('\n'); break;
                    case 'r': sb.append('\r'); break;
                    case 't': sb.append('\t'); break;
                    case 'b': sb.append('\b'); break;
                    case 'f': sb.append('\f'); break;
                    case 'u':
                        if (i + 4 <= len) {
                            sb.append((char) Integer.parseInt(s.substring(i, i + 4), 16));
                            i += 4;
                        }
                        break;
                    default: sb.append(e);
                }
            } else {
                sb.append(c);
            }
        }
        return i;
    }

    // Ghidra's own structs, unions, enums and typedefs, as a JSON array.
    private String dataTypesJson(DataTypeManager dtm) {
        StringBuilder b = new StringBuilder("[");
        boolean first = true;
        Iterator<DataType> it = dtm.getAllDataTypes();
        while (it.hasNext()) {
            DataType dt = it.next();
            String kind;
            StringBuilder body = new StringBuilder();
            if (dt instanceof Composite) {
                kind = (dt instanceof Union) ? "union" : "struct";
                Composite c = (Composite) dt;
                DataTypeComponent[] comps = (dt instanceof Structure)
                    ? ((Structure) dt).getDefinedComponents() : c.getComponents();
                body.append(",\"fields\":[");
                for (int i = 0; i < comps.length; i++) {
                    DataTypeComponent f = comps[i];
                    if (i > 0) body.append(",");
                    String fname = f.getFieldName();
                    if (fname == null) fname = "field_0x" + Integer.toHexString(f.getOffset());
                    body.append("{\"off\":").append(f.getOffset())
                        .append(",\"size\":").append(f.getLength())
                        .append(",\"name\":\"").append(esc(fname))
                        .append("\",\"type\":\"").append(esc(f.getDataType().getDisplayName()))
                        .append("\"}");
                }
                body.append("]");
            } else if (dt instanceof ghidra.program.model.data.Enum) {
                kind = "enum";
                ghidra.program.model.data.Enum en = (ghidra.program.model.data.Enum) dt;
                body.append(",\"values\":{");
                String[] names = en.getNames();
                for (int i = 0; i < names.length; i++) {
                    if (i > 0) body.append(",");
                    body.append("\"").append(esc(names[i])).append("\":")
                        .append(en.getValue(names[i]));
                }
                body.append("}");
            } else if (dt instanceof TypeDef) {
                kind = "typedef";
                body.append(",\"type\":\"")
                    .append(esc(((TypeDef) dt).getDataType().getDisplayName())).append("\"");
            } else {
                continue;
            }
            if (!first) b.append(",");
            first = false;
            b.append("{\"kind\":\"").append(kind)
             .append("\",\"name\":\"").append(esc(dt.getName()))
             .append("\",\"path\":\"").append(esc(dt.getCategoryPath().getPath()))
             .append("\",\"size\":").append(dt.getLength())
             .append(body).append("}");
        }
        return b.append("]").toString();
    }

    private void write(File out, Map<String, String> pseudo, List<String[]> funcs,
                       Map<String, String> sigs, String types) throws Exception {
        File tmp = new File(out.getParentFile(), out.getName() + ".tmp");
        Writer w = new BufferedWriter(
            new OutputStreamWriter(new FileOutputStream(tmp), StandardCharsets.UTF_8));
        w.write("{\"version\":2,\"ghidra\":\"headless-java\",\"program\":\""
                + esc(currentProgram.getName()) + "\",\"functions\":[");
        boolean first = true;
        for (String[] fn : funcs) {
            if (!first) w.write(",");
            first = false;
            w.write("{\"name\":\"" + esc(fn[0]) + "\",\"addr\":\"" + fn[1] + "\"}");
        }
        w.write("],\"pseudocode\":{");
        first = true;
        for (Map.Entry<String, String> e : pseudo.entrySet()) {
            if (!first) w.write(",");
            first = false;
            w.write("\"" + e.getKey() + "\":\"" + esc(e.getValue()) + "\"");
        }
        w.write("},\"signatures\":{");
        first = true;
        for (Map.Entry<String, String> e : sigs.entrySet()) {
            if (!first) w.write(",");
            first = false;
            w.write("\"" + e.getKey() + "\":\"" + esc(e.getValue()) + "\"");
        }
        w.write("}");
        if (types != null) w.write(",\"datatypes\":" + types);
        w.write("}");
        w.close();
        Files.move(tmp.toPath(), out.toPath(),
            StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
    }

    private String esc(String s) {
        if (s == null) return "";
        StringBuilder b = new StringBuilder(s.length() + 16);
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            switch (c) {
                case '"': b.append("\\\""); break;
                case '\\': b.append("\\\\"); break;
                case '\n': b.append("\\n"); break;
                case '\r': b.append("\\r"); break;
                case '\t': b.append("\\t"); break;
                case '\b': b.append("\\b"); break;
                case '\f': b.append("\\f"); break;
                default:
                    if (c < 0x20) b.append(String.format("\\u%04x", (int) c));
                    else b.append(c);
            }
        }
        return b.toString();
    }
}
"""


def find_analyze_headless(ghidra_home):
    import glob
    names = ["analyzeHeadless.bat", "analyzeHeadless"] if os.name == "nt" else ["analyzeHeadless"]
    roots = []
    if ghidra_home:
        roots.append(ghidra_home)
    if os.environ.get("GHIDRA_INSTALL_DIR"):
        roots.append(os.environ["GHIDRA_INSTALL_DIR"])
    roots += ["/opt/homebrew/Caskroom/ghidra", "/Applications", os.path.expanduser("~"),
              "/opt", "/usr/share"]
    for root in roots:
        for nm in names:
            direct = os.path.join(root, "support", nm)
            if os.path.isfile(direct):
                return direct
            hits = glob.glob(os.path.join(root, "**", "support", nm), recursive=True)
            if hits:
                return hits[0]
    return None


def _project_dir_name(project):
    """Ghidra wants <projectDir> <projectName> (name without extension). Accept
    the .gpr file, the .rep data folder, a project dir, or a bare name."""
    p = Path(project).expanduser()
    # a Ghidra project is <name>.gpr + <name>.rep; both identify project <name>
    if p.suffix in (".gpr", ".rep"):
        return str(p.parent), p.stem
    if p.is_dir():
        gprs = list(p.glob("*.gpr"))
        if len(gprs) == 1:
            return str(p), gprs[0].stem        # a folder containing one project
        return str(p.parent), p.name
    return str(p.parent), p.name


def run_headless_export(P: Paths, args, refresh=False):
    """Launch Ghidra analyzeHeadless with the embedded export script. Returns True
    on success. Resumes automatically (the script merges with any existing
    ghidra_export.json); refresh decompiles everything again, in place."""
    ah = find_analyze_headless(args.ghidra_home)
    if not ah:
        sys.exit("Couldn't find Ghidra's analyzeHeadless. Pass --ghidra-home "
                 "/path/to/ghidra_<version> (the folder that contains support/).")
    if not args.project:
        sys.exit("The headless export needs --project /path/to/YourProject.gpr "
                 "(or the project folder).")
    proj_dir, proj_name = _project_dir_name(args.project)
    script_dir = P.ghidra / ".script"
    script_dir.mkdir(parents=True, exist_ok=True)
    (script_dir / "GhidraExport.java").write_text(GHIDRA_EXPORT_SCRIPT)
    # -readOnly: we only decompile and write an external JSON, never modify the
    # program, so headless shouldn't check out or save anything.
    cmd = [ah, proj_dir, proj_name, "-noanalysis", "-readOnly",
           "-scriptPath", str(script_dir),
           "-postScript", "GhidraExport.java", str(P.ghidra)] + (["refresh"] if refresh else [])
    if args.program:
        cmd[3:3] = ["-process", args.program]
    else:
        cmd[3:3] = ["-process"]        # every program in the project
    print("Launching Ghidra headless export:\n  " + " ".join(cmd) + "\n", flush=True)
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True)
    except Exception as e:
        sys.exit("Couldn't launch analyzeHeadless (%s)" % e)
    print("  (Ghidra is starting its JVM and opening the project — this is silent "
          "for a minute or so before the export begins)", flush=True)
    for line in proc.stdout:
        line = line.rstrip()
        if line:                       # stream everything so it's visibly working
            print("  " + line, flush=True)
    code = proc.wait()
    export_path = P.export
    if not export_path.exists():
        sys.exit("Ghidra headless export produced no %s (exit %d). Check the project/"
                 "program names and --ghidra-home, and the output above." % (export_path, code))
    return True


# ============================================================================
# Stage: rewrite (pseudocode -> readable C++)
# ============================================================================

# Names a model writes when it hasn't really chosen one
BAD_NAME = re.compile(r"(?i)^(the|some|my|a|new)?_?(function|func|method)(_?name)?\d*$|"
                      r"^(the|some|my)[A-Z_]\w*$|^placeholder\w*$|^fun_?[0-9a-f]+$|"
                      r"^unknown\w*$|^name\d*$|"
                      r"^applyLowpassFilter\w*$|^yourName\w*$|^theName\w*$")   # copied examples
PLACEHOLDER = re.compile(r"^(?:thunk_)?(?:FUN|SUB|LAB)_[0-9a-fA-F]+$")
CHARS_PER_TOKEN = 3.2      # rough size of a "token" (what the model's limit is counted in)
GHIDRA_HELPERS = re.compile(r"^(CONCAT\d+|SUB\d+|ZEXT\d+|SEXT\d+|CARRY\d*|SCARRY\d*|SBORROW\d*|"
                            r"NEON_\w+|POPCOUNT|LZCOUNT|SQRT|ROUND|TRUNC|ABS|"
                            r"_?_?(malloc|free|calloc|realloc|memcpy|memmove|memset|strlen|fwrite|"
                            r"printf|fprintf|sin|cos|sqrt|exp|log|pow|sincos_stret))$")

SYSTEM_PROMPT = """You turn Ghidra decompiler pseudocode into clean, readable C++.

You get ONE function. Rewrite it as the C++ a person would plausibly have written:
- Keep the behaviour exactly the same: same conditions, loops, calculations, calls and
  return values. Don't add features, error handling or logging that isn't there.
- Replace decompiler artifacts with normal C++: undefined4/undefined8 become real types
  (int, float, uint64_t, pointers, bool); CONCAT/SUB/ZEXT become ordinary expressions;
  things like *(float *)(param_1 + 0x18) become members of a struct or class you define,
  with sensible names (add the struct definition above the function).
- Give the parameters and local variables meaningful names.
- If the function has a placeholder name (like FUN_100003a20), give it a meaningful
  name in lowerCamelCase that says what it does. Otherwise keep its name.
- Calls to other functions: use the names you are given. Declare them (no body) if
  you need to.
- Write ONLY this one function. Never write bodies for other functions, not even
  small helpers: declare them instead.
- Ghidra helper notation is not real code: CONCAT44(a, b), SUB84(x, 0), ZEXT48(x),
  NEON_xxx(...) and the like describe bit or vector operations. Turn them into plain
  C++ (shifts, casts, ordinary float maths, or a simple loop over 4 floats); never
  declare or define functions with those names.
- _malloc, _free, _memcpy, _fwrite, ___sincos_stret etc. are standard library calls:
  use malloc, free, memcpy, fwrite, sinf/cosf.
- DAT_xxx / PTR_xxx are global variables: give them meaningful names if you can tell
  what they are.
- Rewrite, don't transcribe: replace uVar3/iVar7/param_1/local_28/DAT_xxx with names
  describing what they hold, and replace goto/labels with if/else or loops where
  possible. No decompiler-style names may be left in your code.
- No raw addresses or offsets: never leave hex addresses (like 0x100003a20) in names
  or values, and turn pointer-plus-offset access into struct members. Only keep casts
  the types really need.
- Remove names and strings that identify the original program: replace or drop product
  names, company names, copyright notices, version strings, file paths and URLs. String
  literals from the pseudocode should not appear unchanged in your code unless they are
  format specifiers, single characters, or standard C strings like "rb" or "\\n".
- Your code is compiled on its own, so it must compile as standard C++17: include the
  headers you use, define the structs and globals it uses, and declare (no body) the
  other functions it calls.
- Never add printing, logging, messages or text strings that aren't in the pseudocode.
{comments}
- Do not use #if, #ifdef, #define, #pragma or platform headers (windows.h and the like).
Reply with ONE ```cpp code block, then one final line: NAME: followed by the name you
chose for this function (a name that describes what THIS function does)."""

NO_COMMENTS = "- Do not write any comments in the code."
WITH_COMMENTS = "- Add short comments where the purpose of a step isn't obvious."


class AutoParallel:
    """Finds a good number of requests to run at once.

    The model app works on a set number of requests at a time and queues the rest. A
    queued request is easy to spot: its first word arrives far later than the size of
    its prompt explains. So:
      - a request that sat in the queue  -> one fewer at a time
      - no queueing for `every` seconds  -> one more at a time (if all slots were busy)
      - one more made the model slower overall -> step back and wait a while"""

    def __init__(self, gate, max_parallel, every, log):
        self.gate, self.maxp, self.every, self.log = gate, max_parallel, every, log
        self.lock = threading.Lock()
        self.rates = []                    # prompt characters per second until 1st word
        self.n = 0
        self.changed_at = time.time()
        self.queued = 0                    # queued requests since the last change
        self.chars = 0                     # characters written since the last change
        self.last_step, self.speed_before_up, self.hold_until = None, None, 0.0
        self.fails = {}                    # limit -> times it turned out too many
        self.stop = threading.Event()
        threading.Thread(target=self._run, daemon=True).start()

    def record(self, sent_at, prompt_chars, first_word, out_chars):
        with self.lock:
            self.n += 1
            rate = prompt_chars / max(first_word, 0.05)
            typical = sorted(self.rates)[int(len(self.rates) * 0.8)] \
                if len(self.rates) >= 5 else None
            self.rates = (self.rates + [rate])[-40:]
            if sent_at < self.changed_at:
                return                          # sent under the previous setting
            self.chars += out_chars
            if typical is None or self.n <= 3:  # first ones include loading the model
                return
            if first_word > 2.5 * prompt_chars / typical + 1.5:
                self.queued += 1
                if self.gate.limit > 1 and \
                        time.time() - self.changed_at >= min(30, self.every / 2):
                    self._too_many(self.gate.limit, "requests were waiting in the model's queue")

    def _too_many(self, limit, why):
        """`limit` at once was too many: step back, and wait before trying it again,
        longer each time it fails (15 min, 30, 1 hour at most, with --auto-every 5)."""
        k = self.fails[limit] = self.fails.get(limit, 0) + 1
        wait_for = min(3 * self.every * 2 ** (k - 1), max(3600, 3 * self.every))
        self.last_step, self.speed_before_up = "down", None
        self.hold_until = time.time() + wait_for
        self._set(limit - 1, f"{why}; trying {limit} again in {fmt_duration(wait_for)}")

    def _set(self, n, why):
        old = self.gate.limit
        self.gate.set_limit(n)
        self.changed_at, self.queued, self.chars = time.time(), 0, 0
        if n != old:
            self.log(f"  parallel {old} -> {n} ({why})")

    def _run(self):
        while not self.stop.wait(5):
            with self.lock:
                now = time.time()
                elapsed = now - self.changed_at
                if elapsed < self.every:
                    continue
                speed = self.chars / elapsed
                limit = self.gate.limit
                if self.last_step == "up" and self.speed_before_up \
                        and speed < 0.9 * self.speed_before_up:
                    self._too_many(limit, "one more at a time made it slower")
                elif self.queued == 0 and self.gate.peak >= limit and limit < self.maxp \
                        and now >= self.hold_until:
                    self.last_step, self.speed_before_up = "up", speed
                    self._set(limit + 1, f"no queue for {fmt_duration(elapsed)}")
                else:
                    self.last_step, self.speed_before_up = None, None
                    self._set(limit, "")        # start a fresh measuring window


def _func_name(item):
    head = item.split("{", 1)[0]
    m = re.search(r"([A-Za-z_~][\w:~]*)\s*\([^()]*(\([^()]*\)[^()]*)*\)\s*(const\s*)?"
                  r"(noexcept\s*)?(override\s*)?$", head.strip())
    return m.group(1).split("::")[-1] if m else None


def _is_statement(line):
    """True for a line that is code from inside a function, not a declaration."""
    if re.match(r"(if|for|while|do|switch|return|goto|break|continue|else)\b", line) or \
            re.match(r"\w+:\s*$", line) or line.startswith(("*", "(", "++", "--")):
        return True
    flat = line
    while re.search(r"\([^()]*\)", flat):           # ignore '=' inside (...), e.g. default args
        flat = re.sub(r"\([^()]*\)", "", flat)
    m = re.search(r"(?<![=!<>+\-*/%&|^])([-+*/%&|^]|<<|>>)?=(?!=)", flat)
    if not m:
        return False
    lhs = flat[:m.start()].strip()
    # a declaration has a type and a name ("float gain = 1"); a statement assigns to
    # an existing variable or memory ("x = ...", "p->f = ...", "*(int *)(p + 4) = ...")
    return bool(re.search(r"->|\.|\(|\+", lhs)) or bool(m.group(1)) or \
        re.fullmatch(r"[A-Za-z_]\w*(\[[^\]]*\])?", lhs) is not None


def brace_balance(text):
    """Opening minus closing braces, ignoring string and character literals."""
    n, i, L = 0, 0, len(text)
    while i < L:
        ch = text[i]
        if ch in "\"'":
            j = i + 1
            while j < L and text[j] != ch and text[j] != "\n":
                j += 2 if text[j] == "\\" else 1
            i = j + 1
            continue
        n += 1 if ch == "{" else -1 if ch == "}" else 0
        i += 1
    return n


def invented_strings(code, pseudo):
    """Text strings in the rewrite that aren't anywhere in Ghidra's pseudocode: almost
    always printing or messages the model made up."""
    lit = re.compile(r'"((?:[^"\\\n]|\\.)*)"')
    have = set(lit.findall(pseudo))
    body = "\n".join(l for l in code.splitlines() if not l.lstrip().startswith("#"))
    return [x for x in lit.findall(body) if x.strip() and x not in have]


# Strings short enough or generic enough to keep (format specifiers, modes, single chars)
_GENERIC_STR = re.compile(
    r"^[\s%\-+#0-9.*lhLqjzt]*[diouxXeEfFgGaAcspn%]\s*$"   # printf format
    r"|^\\[nrt0\\]$"                                         # escaped char
    r"|^.{0,2}$"                                             # 1-2 chars (rb, w, \n, etc.)
)


def surviving_strings(code, pseudo):
    """String literals from the pseudocode that survived into the rewrite unchanged.
    These may identify the original program (product names, paths, versions, etc.)."""
    lit = re.compile(r'"((?:[^"\\\n]|\\.)*)"')
    orig = set(lit.findall(pseudo))
    body = "\n".join(l for l in code.splitlines() if not l.lstrip().startswith("#"))
    found = set(lit.findall(body))
    return sorted(s for s in orig & found if not _GENERIC_STR.match(s))


_FORMAT_STR = re.compile(r'%[-+#0-9.*lhLqjzt]*[diouxXeEfFgGaAcspn]')
_IDENTIFYING = re.compile(r'[A-Za-z]{4,}|[/\\][A-Za-z0-9._]|\b\d+\.\d+\b')


def strip_identifying(code):
    """Blank string literals that look like they identify the original program
    (product names, paths, version numbers), while keeping generic ones: short
    strings, modes like "rb", and printf format strings (even with escapes)."""
    lit = re.compile(r'"((?:[^"\\\n]|\\.)*)"')

    def repl(m):
        s = m.group(1)
        if _GENERIC_STR.match(s) or _FORMAT_STR.search(s):
            return m.group(0)                     # generic or a format string: keep
        return '""' if _IDENTIFYING.search(s) else m.group(0)

    return lit.sub(repl, code)


def faithful_from_pseudo(shown):
    """A faithful, deterministic C++ version of a function straight from its
    Ghidra pseudocode: type cleanup, no identifying strings, no model. Used only
    when the model couldn't produce a compiling rewrite — the honest raw version
    is better for the downstream fixer (which has the ghidra intrinsics) to
    recover than a half-broken model attempt."""
    return strip_identifying(tidy_tiny(shown))


# Ghidra's names for parameters, locals and globals. FUN_ isn't here: calls to functions
# that haven't been rewritten yet keep it until they get their own name.
LEFTOVER_NAMES = re.compile(r"\b(param_\d+|local_[0-9a-fA-F]+|[a-z]{1,3}Var\d+|"
                            r"(?:DAT|PTR|LAB)_[0-9a-fA-F]+|in_\w+|extraout_\w+|unaff_\w+)\b")
# An address inside a macOS program (they start at 0x100000000)
RAW_ADDRESS = re.compile(r"\b0x0*1000[0-9a-fA-F]{5}\b")


def leftover_names(code):
    return sorted(set(LEFTOVER_NAMES.findall(strip_comments(code))))


def suspect_reasons(code, pseudo, name, check_names=True):
    why = []
    if invented_strings(code, pseudo or ""):
        why.append("invented text/printing")
    if name and BAD_NAME.match(name):
        why.append("no real name")
    if brace_balance(code) != 0:
        why.append("cut off")
    if check_names and leftover_names(code):
        why.append("decompiler names left")
    if check_names and RAW_ADDRESS.search(strip_comments(code)):
        why.append("raw addresses left")
    if check_names and surviving_strings(code, pseudo or ""):
        why.append("identifying strings left")
    return why



# ---------------------------------------------------------------- standalone compile check

PRELUDE = ("#include <cstdint>\n#include <cstddef>\n#include <cstdlib>\n#include <cstring>\n"
           "#include <cmath>\n#include <cstdio>\n")


def compile_errors(code):
    """None if the code compiles on its own (syntax and types, no linking), else the
    compiler's error messages. Line numbers match the code as given."""
    limit = "-ferror-limit=10" if COMPILER["clang"] else "-fmax-errors=10"
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "function.cpp")
        with open(src, "w") as f:
            f.write(PRELUDE + '#line 1 "function.cpp"\n' + code + "\n")
        try:
            r = subprocess.run([COMPILER["cmd"], "-std=c++17", "-fsyntax-only", "-w", limit,
                                "-x", "c++", src], capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            return "the compiler gave up (took over 2 minutes)"
    if r.returncode == 0:
        return None
    err = (r.stderr or r.stdout).replace(src, "function.cpp").strip()
    if len(err) > 3000:
        err = err[:3000].rsplit("\n", 1)[0] + "\n..."
    return err or "the compiler failed without saying why"


def n_errors(err):
    return len(re.findall(r"\berror\b", err)) if err else 0


# ---------------------------------------------------------------- incremental fix
# Instead of regenerating a whole function when it won't compile (a small model
# drifts and guts it), fix it the way a person would: understand the goal once,
# then for each compile error read the exact line the compiler flags, diagnose
# it, plan the minimal change, and edit JUST that line. Recompile and repeat. A
# no-progress guard stops the loop as soon as an edit stops moving the error.

FIX_GOAL_SYS = ("In 1-2 sentences, state what this function does: its inputs, what "
                "it computes, and what it returns. Describe behaviour only; output no code.")
FIX_DIAG_SYS = ("A C++ compiler reported an error on one line of a function. In ONE "
                "sentence say what is wrong with that line (syntax or types). Do not "
                "propose a fix yet and output no code.")
FIX_PLAN_SYS = ("Choose the smallest change that fixes a C++ compile error WITHOUT "
                "changing what the code does. Given the goal, the diagnosis and the "
                "failing line, say in ONE sentence what the corrected line should be. "
                "Output no code.")
FIX_EDIT_SYS = ("Output the corrected replacement for the given line(s) of C++ and "
                "nothing else. Change as little as possible; keep the same behaviour; do "
                "not rename the function; do not add or remove braces that would "
                "unbalance the surrounding code. Return ONLY the replacement line(s) in "
                "one ```cpp code block.")


def _first_err_line(err):
    m = re.search(r'function\.cpp:(\d+):(\d+):\s*(?:fatal\s+)?error:\s*(.*)', err)
    return (int(m.group(1)), int(m.group(2)), m.group(3).strip()) if m else None


def _edit_span(lines, ln):
    """0-based [lo, hi) to edit for an error on 1-based line `ln`: that line plus
    any continuation lines until its brackets balance (a multi-line statement)."""
    lo = ln - 1
    if lo < 0 or lo >= len(lines):
        return None
    hi = ln
    while hi < min(len(lines), lo + 5):
        seg = "\n".join(lines[lo:hi])
        if seg.count("{") == seg.count("}") and seg.count("(") >= seg.count(")"):
            break
        hi += 1
    return lo, hi


def incremental_fix(args, code, pseudo, name, prog, key):
    """Drive a standalone function to compile by minimal, line-anchored edits.
    Returns (code, compiled_bool, n_edits). Makes no model call when the code
    already compiles."""
    goal = None
    seen = {}
    edits = 0
    max_iters = max(4, args.compile_retries * 3)
    for _ in range(max_iters):
        errors = compile_errors(code)
        if errors is None:
            return code, True, edits
        loc = _first_err_line(errors)
        if not loc:
            break
        ln, col, emsg = loc
        lines = code.split("\n")
        span = _edit_span(lines, ln)
        if not span:
            break
        lo, hi = span
        target = "\n".join(lines[lo:hi])
        sig = (ln, emsg[:60])
        seen[sig] = seen.get(sig, 0) + 1
        if seen[sig] >= 2:          # this exact error survived an edit -> stop
            break
        if args.fix_steps == "chain":
            if goal is None:
                goal = ask_model(args.model_in_use, [{"role": "system", "content": FIX_GOAL_SYS},
                    {"role": "user", "content": f"Function {name}:\n```c\n{pseudo[:6000]}\n```"}],
                    args.ctx, 160)
            diagnosis = ask_model(args.model_in_use, [{"role": "system", "content": FIX_DIAG_SYS},
                {"role": "user", "content": f"Error: {emsg}\nLine {ln}: {target}"}],
                args.ctx, 120)
            plan = ask_model(args.model_in_use, [{"role": "system", "content": FIX_PLAN_SYS},
                {"role": "user", "content": f"Goal: {goal}\nDiagnosis: {diagnosis}\n"
                 f"Failing line {ln}: {target}\nCompiler error: {emsg}"}], args.ctx, 120)
            user = (f"Function goal: {goal}\nPlan: {plan}\nCompiler error: {emsg}\n\n"
                    f"Replace ONLY these line(s):\n```cpp\n{target}\n```")
        else:
            user = (f"Compiler error: {emsg}\n\nReplace ONLY these line(s):\n"
                    f"```cpp\n{target}\n```")
        prog.set_phase(key, f"fixing line {ln} (edit {edits + 1})")
        reply = ask_model(args.model_in_use, [{"role": "system", "content": FIX_EDIT_SYS},
                          {"role": "user", "content": user}], args.ctx,
                          min(600, max(200, (hi - lo) * 48)))
        new, _ = parse_reply(reply)
        if new is None:
            new = reply.strip()
        new = "\n".join(l for l in new.split("\n")
                        if not l.lstrip().startswith("#include")).strip()
        if not new or new.strip() == target.strip():
            break
        if (new.count("{") - new.count("}")) != (target.count("{") - target.count("}")):
            break                   # would unbalance the braces
        indent = re.match(r"[ \t]*", lines[lo]).group(0)
        nl = new.split("\n")
        if indent and nl and not nl[0][:1].isspace():
            nl = [indent + x if x.strip() else x for x in nl]
        lines[lo:hi] = nl
        code = "\n".join(lines)
        edits += 1
    return code, compile_errors(code) is None, edits


def keep_one_function(code, wanted):
    """Keep only what belongs in this function's rewrite: #includes, types, declarations,
    and ONE function body (the one named `wanted`, else the longest). Extra function
    bodies the model invented, Ghidra helper functions and stray statements are dropped.
    Returns (code, found_the_function)."""
    items = split_items(code)
    bodies = [it for it in items if it.rstrip().endswith("}") and _func_name(it)
              and not re.match(r"\s*(template\s*<[^>]*>\s*)?(struct|class|union|enum|namespace)\b",
                               it)]
    target = next((b for b in bodies if _func_name(b) in wanted), None)
    if target is None and bodies:
        target = max(bodies, key=len)
    kept = []
    for it in items:
        first = it.split("\n", 1)[0].strip()
        if it in bodies and it is not target:
            continue                                     # another function's body
        name = _func_name(it.rstrip(";")) if it.rstrip().endswith(";") else None
        if name and GHIDRA_HELPERS.match(name):
            continue                                     # e.g. a CONCAT44 declaration
        if it is not target and not it.rstrip().endswith((";", "}")) \
                and not first.startswith("#"):
            continue                                     # unfinished fragment
        if it is not target and _is_statement(first):
            continue                                     # a loose statement or label
        kept.append(it)
    # A reply that was cut off: close its braces so it can't swallow what follows
    out = "\n\n".join(kept)
    missing = brace_balance(out)
    if missing > 0:
        out = out.rstrip() + "\n" + "}" * missing
    return out, target is not None


def parse_reply(reply):
    blocks = re.findall(r"```[\w+\-]*[ \t]*\n(.*?)```", reply, flags=re.S)
    code = max(blocks, key=len).strip() if blocks else None
    if code is None:
        # the closing ``` is missing (often a reply that ran out of room right at the
        # end): keep the code if the function in it is complete
        m = re.search(r"```[\w+\-]*[ \t]*\n(.*)$", reply, flags=re.S)
        if m:
            tail = re.split(r"^\s*NAME:", m.group(1), flags=re.M)[0].strip()
            if "{" in tail and tail.rstrip().endswith("}") and brace_balance(tail) == 0:
                code = tail
    m = re.search(r"^\s*NAME:\s*`?([A-Za-z_][\w:~]*)`?\s*$", reply, flags=re.M)
    return code, (m.group(1) if m else None)


# ---------------------------------------------------------------- tiny functions
# Getters, setters, one-line wrappers and the like gain almost nothing from the model,
# so with --tiny they are copied over from Ghidra with its types tidied up.

GHIDRA_TYPES = [
    (r"\bundefined8\b", "uint64_t"), (r"\bundefined4\b", "uint32_t"),
    (r"\bundefined2\b", "uint16_t"), (r"\bundefined1\b", "uint8_t"),
    (r"\bundefined\s*\*", "void *"), (r"\bundefined\b", "uint8_t"),
    (r"\bulonglong\b", "uint64_t"), (r"\blonglong\b", "int64_t"),
    (r"\bulong\b", "uint64_t"), (r"\buint\b", "uint32_t"), (r"\bushort\b", "uint16_t"),
    (r"\buchar\b", "uint8_t"), (r"\bbyte\b", "uint8_t"), (r"\bsbyte\b", "int8_t"),
    (r"\bcode\s*\*", "void *"), (r"\b__(thiscall|cdecl|stdcall|fastcall)\b\s*", ""),
]
DECL_LINE = re.compile(r"^[\w\s\*&:<>]+?[\s\*&]\**\w+(\s*\[\w*\])*\s*;$")


def body_statements(pseudo):
    """The statements inside a function's outermost { }, without declarations/comments."""
    code = strip_comments(pseudo)
    if "{" not in code or "}" not in code:
        return None
    body = code[code.index("{") + 1:code.rindex("}")]
    out = []
    for line in body.splitlines():
        t = line.strip()
        if not t or (DECL_LINE.match(t) and "=" not in t and "(" not in t
                     and not re.match(r"(return|goto|break|continue|delete|throw)\b", t)):
            continue
        out.append(t)
    return out


def is_tiny(pseudo, limit):
    stmts = body_statements(pseudo)
    if stmts is None or len(stmts) > limit:
        return False
    return not any(re.match(r"(if|else|for|while|do|switch|case|goto)\b", t)
                   or re.match(r"\w+:$", t) or t.startswith(("{", "}")) for t in stmts)


def tidy_types(code):
    for rx, rep_ in GHIDRA_TYPES:
        code = re.sub(rx, rep_, code)
    return code


def tidy_tiny(pseudo):
    code = strip_comments(pseudo)
    for rx, rep_ in GHIDRA_TYPES:
        code = re.sub(rx, rep_, code)
    code = re.sub(r"\)\s*\n\s*\{", ") {", code, count=1)    # "f(...)\n\n{" -> "f(...) {"
    return "#include <cstdint>\n\n" + code.strip()


# ---------------------------------------------------------------- big functions
# A function too big for the model is cut into pieces at sensible places (between
# statements, preferring the outermost level), each piece is rewritten on its own, and
# the pieces are joined back together in order inside one function.

PIECE_PROMPT = """You turn part of a Ghidra decompiler function into clean, readable C++.
The function is too long to rewrite in one go, so you get one piece of it at a time.
The pieces are joined back together afterwards, in order.
- Rewrite ONLY the lines of this piece, in the same order, as C++ statements.
  No function header, no #include, no new struct or function definitions.
- The piece may start or end in the middle of a block. Every { or } in it that doesn't
  have its partner inside the piece must stay exactly where it is, so the pieces still
  fit together.
- Keep variable names exactly as they are: other pieces use them too.
- Keep the behaviour exactly the same. Keep goto and LAB_ labels as they are (they can
  jump between pieces).
- Ghidra helper notation is not real code: CONCAT44(a, b), SUB84(x, 0), ZEXT48(x),
  NEON_xxx(...) describe bit or vector operations. Write them as plain C++.
- _malloc, _free, _memcpy, ___sincos_stret etc. are standard library calls: use malloc,
  free, memcpy, sinf/cosf. Turn undefined4/undefined8 into real types.
- Never add printing, logging, messages or text strings that aren't in the piece.
{comments}
Reply with ONE ```cpp code block containing just the rewritten lines."""


def split_function(pseudo):
    """(header, declaration lines, body lines) of a function, or None."""
    code = strip_comments(pseudo)
    i, j = code.find("{"), code.rfind("}")
    if i < 0 or j <= i:
        return None
    header = " ".join(code[:i].split())
    lines = code[i + 1:j].strip("\n").split("\n")
    decls = []
    for l in lines:
        t = l.strip()
        if not t:
            if decls:
                break
            continue
        if DECL_LINE.match(t) and "=" not in t and "(" not in t:
            decls.append(l)
        else:
            break
    return header, decls, lines


def chunk_lines(lines, max_chars):
    """Cut lines into pieces of at most max_chars, choosing cut points between
    statements and as close to the outermost level as possible."""
    depth_after, d = [], 0
    for l in lines:
        d = max(0, d + brace_balance(l))
        depth_after.append(d)
    pieces, start, n = [], 0, len(lines)
    while start < n:
        size, end = 0, start
        while end < n and (end == start or size + len(lines[end]) + 1 <= max_chars):
            size += len(lines[end]) + 1
            end += 1
        if end >= n:
            pieces.append(lines[start:])
            break
        best, best_key = end - 1, None
        for c in range(start + (end - start) // 2, end):
            t = lines[c].strip()
            if t and not t.endswith((";", "{", "}")) and not re.match(r"\w+:$", t):
                continue                                  # mid-statement: don't cut here
            key = (depth_after[c], -c)
            if best_key is None or key < best_key:
                best, best_key = c, key
        pieces.append(lines[start:best + 1])
        start = best + 1
    return ["\n".join(p) for p in pieces]


def clean_piece(code, original, names):
    """The model's rewrite of a piece if it still fits the jigsaw, else None."""
    lines = [l for l in code.split("\n") if not re.match(r"\s*#\s*(include|import)\b", l)]
    while lines and not lines[0].strip():
        lines.pop(0)
    # Unwrap a function header the model added around the piece
    if lines and lines[0].strip() not in original:
        first = lines[0].strip()
        hdr = re.match(r"[\w\s\*&:<>,]*\b(\w+)\s*\([^;]*\)\s*(const\s*)?\{?$", first)
        if hdr and not re.match(r"(if|for|while|switch|do|else|return)\b", first) and \
                (hdr.group(1) in names or first.endswith("{") or
                 (len(lines) > 1 and lines[1].strip() == "{")):
            lines.pop(0)
            if not first.endswith("{") and lines and lines[0].strip() == "{":
                lines.pop(0)
            body = "\n".join(lines).rstrip()
            if body.endswith("}") and brace_balance(body) == brace_balance(original) - 1:
                body = body[:body.rfind("}")].rstrip()
            lines = body.split("\n")
    out = "\n".join(lines).strip("\n")
    if not out.strip() or brace_balance(out) != brace_balance(original):
        return None
    return out


# ---------------------------------------------------------------- tidying the output

def strip_comments(code):
    """Remove // and /* */ comments, leaving string and character literals alone."""
    MARK, out, i, n = "\x00", [], 0, len(code)
    while i < n:
        two = code[i:i + 2]
        if two == "//":
            j = code.find("\n", i)
            i = n if j < 0 else j
            out.append(MARK)
            continue
        if two == "/*":
            j = code.find("*/", i + 2)
            i = n if j < 0 else j + 2
            out.append(MARK)
            continue
        m = re.match(r'(?:u8|u|U|L)?R"([^(\s"\\]{0,16})\(', code[i:])
        if m and (i == 0 or not (code[i - 1].isalnum() or code[i - 1] == "_")):
            end = code.find(")" + m.group(1) + '"', i + m.end())
            j = n if end < 0 else end + len(m.group(1)) + 2
            out.append(code[i:j])
            i = j
            continue
        if code[i] in "\"'":
            q, j = code[i], i + 1
            while j < n and code[j] != q and code[j] != "\n":
                j += 2 if code[j] == "\\" else 1
            j = min(j + 1, n)
            out.append(code[i:j])
            i = j
            continue
        out.append(code[i])
        i += 1
    lines = []
    for line in "".join(out).split("\n"):
        if MARK in line and not line.replace(MARK, "").strip():
            continue
        line = re.sub(r"^([ \t]*)\x00[ \t]*", r"\1", line)
        line = re.sub(r"(\S)[ \t]*\x00[ \t]*(?=\S)", r"\1 ", line)
        lines.append(line.replace(MARK, "").rstrip())
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip("\n")


IMPORT_RE = re.compile(r"^\s*#\s*(include|import)\b")


def _depth_change(line):
    d, i, n = 0, 0, len(line)
    while i < n:
        ch = line[i]
        if ch in "\"'":
            j = i + 1
            while j < n and line[j] != ch:
                j += 2 if line[j] == "\\" else 1
            i = j + 1
            continue
        d += 1 if ch in "{([" else -1 if ch in "})]" else 0
        i += 1
    return d


def split_items(code):
    """Top-level pieces of a file: an #include, a declaration, a struct, a function."""
    items, cur, depth = [], [], 0
    for line in code.split("\n"):
        s = line.strip()
        if not cur and not s:
            continue
        cur.append(line)
        depth = max(0, depth + _depth_change(line))
        last = next((l.strip() for l in reversed(cur) if l.strip()), "")
        if depth == 0 and ((not s and not last.endswith(")")) or s.startswith("#")
                           or s.endswith((";", "}"))):
            items.append("\n".join(cur).rstrip())
            cur = []
    if cur:
        items.append("\n".join(cur).rstrip())
    return [it for it in items if it.strip()]


def combine(codes):
    """One file from many: each #include once at the top, type definitions and
    declarations once (before the functions), functions in program order."""
    includes, types, decls, funcs, seen = [], [], [], [], set()
    for code in codes:
        for item in split_items(code):
            first = item.split("\n", 1)[0].strip()
            norm = re.sub(r"\s+", " ", item).strip()
            if IMPORT_RE.match(first):
                if norm not in seen:
                    seen.add(norm)
                    includes.append(first)
                continue
            if first.startswith("#"):                     # other preprocessor lines
                funcs.append(item)
                continue
            if norm in seen:
                continue
            seen.add(norm)
            if re.match(r"(typedef|enum|using)\b", first) or \
                    re.match(r"(template\s*<[^>]*>\s*)?(struct|class|union)\s+[\w:]+\s*(final\s*)?"
                             r"(:[^{;]*)?(\{|$)", first) and not item.rstrip().endswith("}"):
                types.append(item)                        # struct/class definitions, typedefs
            elif norm.endswith(";") and "{" not in norm:
                decls.append(item)                        # forward declarations, prototypes
            else:
                funcs.append(item)
    parts = ["\n".join(includes)] if includes else []
    if types:
        parts.append("\n\n".join(types))
    if decls:
        parts.append("\n".join(decls))
    parts += funcs
    return "\n\n".join(parts).strip() + "\n"


# ---------------------------------------------------------------- bookkeeping

def load_progress(P: Paths):
    if not P.progress.exists():
        return {}
    try:
        return json.loads(P.progress.read_text())
    except Exception as e:
        set_aside(P.progress, str(e))     # keep it rather than overwrite it
        return {}


def save_progress(P: Paths, progress):
    write_atomic(P.progress, json.dumps(progress, indent=0))


def apply_names(text, names):
    """Swap Ghidra's placeholder names for the new ones (whole words only)."""
    if not names:
        return text
    rx = re.compile(r"\b(" + "|".join(re.escape(k) for k in
                                       sorted(names, key=len, reverse=True)) + r")\b")
    return rx.sub(lambda m: names[m.group(1)], text)


def mark_function(code, ghidra_name, addr_hex):
    """Tag the function body with a one-line marker carrying its Ghidra address,
    so the recover stage can map a function in the combined file back to its
    pseudocode. The marker rides on the body item through combine()."""
    items = split_items(code)
    for idx, it in enumerate(items):
        if it.rstrip().endswith("}") and _func_name(it) and not re.match(
                r"\s*(template\s*<[^>]*>\s*)?(struct|class|union|enum|namespace)\b", it):
            items[idx] = f"//@ghidra {addr_hex} {ghidra_name}\n{it}"
            break
    return "\n\n".join(items)


STD_HEADERS = set("""cstdint cstddef cstdlib cstring cstdio cmath climits cfloat cctype
cwchar cassert cerrno ctime cstdarg csetjmp csignal clocale string vector map set list
deque array memory functional algorithm utility iostream ostream istream sstream fstream
iomanip stdexcept exception new typeinfo locale mutex atomic thread chrono tuple
unordered_map unordered_set queue stack bitset limits numeric iterator type_traits
initializer_list optional variant cinttypes stdint.h stddef.h stdlib.h string.h stdio.h
math.h limits.h float.h ctype.h wchar.h assert.h errno.h time.h stdarg.h stdbool.h
pthread.h""".split())
PREPROC = re.compile(r"^\s*#\s*(if|ifdef|ifndef|elif|else|endif|define|undef|pragma|error|"
                     r"warning|line|import)\b")


def clean_for_monolith(code: str) -> str:
    """A function's rewrite as it goes into rewritten.cpp. Everything goes into ONE
    file, so one function's #ifdef _WIN32 without its #endif, or an extra '}',
    would hide every function after it from the split. Preprocessor lines and
    includes other than the standard library's are dropped; extra closing braces
    at the end are removed."""
    out = []
    for line in code.split("\n"):
        if PREPROC.match(line):
            continue
        m = re.match(r'\s*#\s*include\s*[<"]([^>"]+)[>"]', line)
        if m and m.group(1) not in STD_HEADERS:
            continue
        out.append(line)
    code = "\n".join(out)
    while brace_balance(code) < 0:
        i = code.rstrip().rfind("}")
        if i < 0:
            break
        code = code[:i] + code[i + 1:]
    if brace_balance(code) > 0:
        code = code.rstrip() + "\n" + "}" * brace_balance(code)
    return code


def write_outputs(P: Paths, progress, order, keep_comments):
    """rewritten.cpp from every finished function (including ones waiting to be
    rewritten again: their current version stays until the new one replaces it)."""
    names = {e["ghidra"]: e["name"] for e in progress.get("functions", {}).values()
             if e.get("name") and e["name"] != e["ghidra"]}
    codes, index = [], {}
    for key in order:
        e = progress.get("functions", {}).get(key)
        if e and e.get("status") == "done":
            f = P.rewritten_dir / f"{key}.cpp"
            if f.exists():
                code = f.read_text()
                code, _ = keep_one_function(code if keep_comments else strip_comments(code),
                                            {e.get("name"), e.get("ghidra")})
                code = clean_for_monolith(code)
                # apply names FIRST, then add the marker, so the marker's literal
                # Ghidra name/address are never rewritten by apply_names
                code = mark_function(apply_names(code, names), e["ghidra"], key)
                codes.append(code)
                final = e.get("name") or e["ghidra"]
                index[final] = {"ghidra": e["ghidra"], "addr": key,
                                "status": e.get("status"),
                                "pieces": e.get("pieces"), "tiny": e.get("tiny", False)}
    if codes:
        write_atomic(P.rewritten, combine(codes))
    # sidecar map (final name -> Ghidra address), a fallback for the fixer when a
    # function in the combined file has no inline marker
    write_atomic(P.index, json.dumps(index, indent=0))
    write_atomic(P.names, "".join(
        f"{e['ghidra']}  ->  {e['name']}\n" for k in order
        if (e := progress.get("functions", {}).get(k)) and e.get("name")))


def unique_name(name, taken):
    base, n = name, 2
    while name in taken:
        name = f"{base}{n}"
        n += 1
    return name


# ---------------------------------------------------------------- progress display

def fmt_duration(secs):
    secs = int(secs)
    if secs < 60:
        return f"{secs}s"
    m, h = secs // 60, secs // 3600
    if h == 0:
        return f"{m}m"
    if h < 48:
        return f"{h}h {m % 60:02d}m"
    return f"{h // 24}d {h % 24}h"


def fmt_clock(secs):
    when = datetime.now() + timedelta(seconds=secs)
    clock = when.strftime("%I:%M %p").lstrip("0")
    if when.date() == datetime.now().date():
        return clock
    if when.date() == (datetime.now() + timedelta(days=1)).date():
        return "tomorrow " + clock
    return when.strftime("%a ") + clock


class Progress:
    """A progress bar that stays at the bottom of the window while finished functions
    scroll past above it, with a time estimate and timers for the functions in progress.
    Speed and time left are averaged over the whole session."""
    SPIN = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self, total, already=0, title=""):
        self.total, self.done = total, already
        self.title = title                    # what this bar is counting
        self.finished_at = []                 # when each function finished, this run
        self.started = time.time()
        self.active = {}                      # key -> [label, phase, started]
        self.extra = None                     # optional callable: more text for the bar
        # live (redrawn in place) in a terminal and in the AI Harness console, which
        # shows a carriage-return line as one pinned, updating line
        self.live = sys.stdout.isatty() or bool(os.environ.get("AIHARNESS_RUN_ID"))
        self.lock = threading.RLock()
        self.stop_flag = threading.Event()
        self.thread = None
        self.every = max(10, total // 40)     # without a live bar: print it this often
        if BAR["p"] is not None:
            BAR["p"].close()
        BAR["p"] = self
        if self.live:
            self.thread = threading.Thread(target=self._spin, daemon=True)
            self.thread.start()

    def rate(self):
        """Functions finished per second, averaged over the whole session (since this
        command was started)."""
        n = len(self.finished_at)
        elapsed = time.time() - self.started
        if n < 2 or elapsed <= 0:
            return None
        return n / elapsed

    def estimate(self):
        r = self.rate()
        if not r:
            return "estimating time left..."
        secs = (self.total - self.done) / r
        per = 60 * r
        speed = f"{per:.1f}/min" if per >= 1 else f"{fmt_duration(1 / r)} each"
        return f"{speed}, about {fmt_duration(secs)} left, done around {fmt_clock(secs)}"

    def bar_line(self, spin=""):
        frac = self.done / self.total if self.total else 1.0
        width = 22
        full = int(frac * width)
        bar = "█" * full + "░" * (width - full)
        running = fmt_duration(time.time() - self.started)
        head = " ".join(x for x in (BAR["stage"], self.title) if x)
        line = (f"{spin} {head + ': ' if head else ''}{self.done}/{self.total} {bar} "
                f"{frac * 100:4.1f}%")
        if self.active:      # what's being worked on matters most, so it comes first
            label, phase, t0 = min(self.active.values(), key=lambda v: v[2])
            line += f" | now: {label}{' — ' + phase if phase else ''} {int(time.time() - t0)}s"
            if len(self.active) > 1:
                line += f" (+{len(self.active) - 1} more)"
        if self.extra:
            line += f" | {self.extra()}"
        line += f" | {self.estimate()} | running {running}"
        cols = shutil.get_terminal_size((160, 20)).columns
        return line[:max(20, cols - 1)]

    def _draw(self, spin=""):
        sys.stdout.write("\r\x1b[K" + self.bar_line(spin))
        sys.stdout.flush()

    def _spin(self):
        i = 0
        while not self.stop_flag.wait(0.25):
            with self.lock:
                self._draw(self.SPIN[i % len(self.SPIN)])
            i += 1

    def log(self, text):
        """Print a line above the bar."""
        with self.lock:
            if self.live:
                sys.stdout.write("\r\x1b[K" + text + "\n")
                self._draw(" ")
            else:
                print(text, flush=True)

    def begin(self, key, label):
        with self.lock:
            self.active[key] = [label, "", time.time()]
        _BAR_TL.key = key

    def set_phase(self, key, phase):
        with self.lock:
            if key in self.active:
                self.active[key][1] = phase

    def end(self, key, text=None):
        with self.lock:
            t0 = self.active.pop(key, [None, None, time.time()])[2]
            self.done += 1
            self.finished_at.append(time.time())
            if text:
                self.log(text.replace("{secs}", fmt_duration(time.time() - t0)))
            if not self.live and (self.done % self.every == 0 or self.done == self.total):
                print(self.bar_line(), flush=True)

    def close(self):
        if BAR["p"] is self:
            BAR["p"] = None
        if self.stop_flag.is_set():
            return
        self.stop_flag.set()
        if self.thread:
            self.thread.join(timeout=1)
        if self.live:
            with self.lock:
                sys.stdout.write("\r\x1b[K" + self.bar_line(" ") + "\n")
                sys.stdout.flush()

# ---------------------------------------------------------------- export stage

def export_info(P: Paths) -> dict:
    try:
        data = json.loads(P.export.read_text())
    except Exception:
        return {}
    pc = data.get("pseudocode") or {}
    return {"functions": len(data.get("functions") or []),
            "with_pseudocode": sum(1 for v in pc.values() if v),
            "export_version": data.get("version"),
            "source": data.get("ghidra"),
            "datatypes": len(data.get("datatypes") or []),
            "signatures": len(data.get("signatures") or {})}


def open_ghidra(P: Paths, args, live_ok=True) -> GhidraCache:
    """The export, with a live Ghidra plugin behind it to fill any gap (unless the
    export came from headless, where the plugin usually isn't running)."""
    live = Ghidra(args.ghidra) if live_ok and not (args.headless_export or args.project) \
        else None
    return GhidraCache(P.export, live)


def run_export(P: Paths, args, redo: set) -> dict:
    refresh = "export" in redo
    headless = bool(args.headless_export or args.project)
    if refresh:
        snapshot(P, "redo-export", [P.export])
    if headless and (refresh or not P.export.exists() or args.export_complete):
        plog(P, "  exporting with Ghidra headless (analyzeHeadless)"
                + (" — every function again, replacing entries in place" if refresh else ""))
        run_headless_export(P, args, refresh)
        ghidra = GhidraCache(P.export, None)
    else:
        ghidra = open_ghidra(P, args)
        if not P.export.exists() or refresh or args.export_complete:
            ghidra.build_full_export(
                parallel=args.export_parallel or max(8, args.parallel), refresh=refresh,
                progress_print=lambda m: plog(P, "  " + m))
        else:
            plog(P, f"  using the existing {P.export.name} (Ghidra not needed)")
    names_known = {e["ghidra"]: e["name"]
                   for e in load_progress(P).get("functions", {}).values()
                   if e.get("name") and e["name"] != e["ghidra"]}
    try:
        n_edges = ghidra.write_callgraph(P.callgraph, names_known)
        plog(P, f"  callgraph.json: {n_edges} functions with internal calls")
    except Exception as e:
        plog(P, f"  (could not write callgraph.json: {e})")
    info = export_info(P)
    plog(P, f"  export: {info.get('with_pseudocode', 0)}/{info.get('functions', 0)} functions "
            f"have pseudocode"
            + (f", {info['datatypes']} data types, {info['signatures']} signatures"
               if info.get("datatypes") or info.get("signatures") else ""))
    return info


# ---------------------------------------------------------------- rewrite stage

MIN_PIECE_CHARS = 600    # smallest piece a cut-off function is split into


def answer_room(ctx: int, prompt_chars: int) -> int:
    """Tokens the answer may use: everything the prompt leaves (a thinking model
    needs room to think before it writes the code)."""
    return max(300, int(ctx - prompt_chars / CHARS_PER_TOKEN - 200))


def prompt_chars(ctx: int) -> int:
    """How much text a prompt with a SHORT answer (a goal, a line number, names)
    may carry."""
    return max(4000, int((ctx - 1500) * CHARS_PER_TOKEN))


def recovery_chars(ctx: int) -> int:
    """The recover stage's budget (pseudocode + the original function): bigger
    functions are patched a few lines at a time instead of rewritten whole. Same
    rule as the pieces: the prompt and an answer of the same size must fit."""
    return 2 * piece_chars(ctx, 2500)


def piece_chars(ctx: int, overhead_chars: int) -> int:
    """How big a piece may be so its prompt and its answer (about 1.5x the piece,
    plus room to think) both fit in the context. The same rule for every split;
    after a cut-off the recorded smaller size is used instead."""
    budget = (ctx - overhead_chars / CHARS_PER_TOKEN - 300) / 2.5
    return max(MIN_PIECE_CHARS * 2, int(budget * CHARS_PER_TOKEN))


def _pseudo_sha(code: Optional[str]) -> str:
    return hashlib.sha1((code or "").encode()).hexdigest()[:16]


def run_rewrite(P: Paths, args, redo: set, client: ModelClient) -> dict:
    """Rewrite every function that isn't done yet. Returns a summary; summary["stop"]
    is True when the run should stop here (--max reached, or nothing to build)."""
    ghidra = open_ghidra(P, args)
    funcs = ghidra.functions()
    selected = funcs
    if args.functions:
        wanted = {w.lower().removeprefix("0x") for w in args.functions}
        selected = [f for f in funcs if f[0].lower() in wanted or f"{f[1]:x}" in wanted]
        plog(P, f"  working on {len(selected)} of {len(funcs)} functions (--functions)")
    sel_keys = {f"{a:x}" for _, a in selected}

    progress = load_progress(P)
    done = progress.setdefault("functions", {})
    # every function stays in the output, in program order, whatever is selected
    order = [f"{a:x}" for _, a in funcs]

    # entries an older pseudo_to_cpp marked "redo" still have their code: keep it
    # in the output until the new rewrite replaces it
    for key, e in done.items():
        if e.get("status") == "redo" and e.get("name") and not e.get("retry_reason") \
                and (P.rewritten_dir / f"{key}.cpp").exists():
            e["status"], e["stale"] = "done", True

    # Functions skipped last time (the model returned no code, Ghidra had no
    # pseudocode) are marked redo, so every run tries them again.
    retry: dict[str, int] = {}
    for e in done.values():
        if e.get("status") == "skipped":
            e["status"] = "redo"
            e["retry_reason"] = e.get("reason") or "skipped"
            e["retries"] = e.get("retries", 0) + 1
        if e.get("status") == "redo" and e.get("retry_reason"):
            retry[e["retry_reason"]] = retry.get(e["retry_reason"], 0) + 1
    if retry:
        plog(P, f"  {sum(retry.values())} function(s) skipped last time are marked redo and "
                f"will be tried again ({', '.join(f'{n} {r}' for r, n in retry.items())})")

    marked = 0
    if "rewrite" in redo:
        snapshot(P, "redo-rewrite", [P.progress, P.rewritten, P.rewritten_dir, P.names,
                                     P.index])
        progress["redo_gen"] = progress.get("redo_gen", 0) + 1
        for key in sel_keys:
            e = done.get(key)
            if e and e.get("status") == "done":
                e["stale"] = True
                marked += 1
            elif e:
                e["status"] = "todo"
        plog(P, f"  --redo rewrite: {marked} function(s) will be rewritten again; each "
                f"replaces its old version as it finishes")

    # pseudocode that changed since a function was rewritten (e.g. --redo export
    # after renaming things in Ghidra) -> rewrite that function again
    changed = 0
    for n, a in funcs:
        key = f"{a:x}"
        e = done.get(key)
        if not e or e.get("status") != "done":
            continue
        sha = _pseudo_sha(ghidra.data["pseudocode"].get(key))
        if e.get("pseudo_sha") is None:
            e["pseudo_sha"] = sha
        elif e["pseudo_sha"] != sha and not e.get("stale"):
            e["stale"] = True
            changed += 1
    if changed:
        plog(P, f"  {changed} function(s) have new pseudocode since they were rewritten — "
                f"rewriting them again")

    taken = {e["name"] for e in done.values() if e.get("name")} | \
            {n for n, _ in funcs if not PLACEHOLDER.match(n)}
    if args.redo_suspect:
        n_sus = 0
        for n, a in selected:
            e = done.get(f"{a:x}")
            if not e or e.get("status") != "done" or e.get("tiny"):
                continue
            if "suspect" not in e:              # done by an earlier version: check it now
                f = P.rewritten_dir / f"{a:x}.cpp"
                pf = P.pseudocode / (re.sub(r"[^\w.-]", "_", n) + ".c")
                code = f.read_text(errors="replace") if f.exists() else ""
                pseudo = pf.read_text(errors="replace") if pf.exists() else ""
                why = suspect_reasons(code, pseudo, e.get("name"),
                                      check_names=not e.get("pieces"))
                if PLACEHOLDER.match(n) and e.get("name") in (None, n):
                    why.append("no real name")
                e["suspect"] = sorted(set(why))
            if e["suspect"] and not e.get("stale"):
                e["stale"] = True
                n_sus += 1
        if n_sus:
            snapshot(P, "redo-suspect", [P.progress, P.rewritten, P.rewritten_dir])
        plog(P, f"  {n_sus} function(s) flagged for a second look will be rewritten again "
                f"(their current version stays until then)")
    save_progress(P, progress)

    todo = [(n, a) for n, a in selected
            if done.get(f"{a:x}", {}).get("status") not in ("done", "skipped")
            or done.get(f"{a:x}", {}).get("stale")]
    if len(todo) < len(selected):
        plog(P, f"  {len(selected) - len(todo)} already done, {len(todo)} to go")
    if not todo:
        write_outputs(P, progress, order, args.comments)
        return _rewrite_summary(progress, order, stop=False)

    model = client.resolve(None)             # whatever is loaded in LM Studio
    args.model_in_use = model
    plog(P, f"  checking that '{model}' really answers ...")
    took = client.ping(model)
    plog(P, f"  {client.name} model '{model}' answered a test request in {took:.1f}s")
    loaded = client.loaded_context(model)
    if loaded and loaded < args.ctx:
        plog(P, f"  !! LM Studio loaded '{model}' with {loaded} tokens of context, but --ctx "
                f"is {args.ctx}: bigger functions will be cut off. Load it with at least "
                f"{args.ctx}, or run with --ctx {loaded}.")
    elif loaded:
        plog(P, f"  LM Studio context: {loaded} tokens (--ctx {args.ctx})"
                + (f"; with --parallel {args.parallel}, check LM Studio isn't splitting it "
                   f"between requests (`lms ps`)" if args.parallel > 1 else ""))
    plog(P, f"  rewriting with {client.name} model '{model}'"
            + (f", compile check with {COMPILER['cmd']}" if COMPILER["cmd"] else
               " (compile check off: the build stages compile against shared.h)"))
    print("Working through functions in program order. Press Ctrl+C to pause; run the "
          "same command to resume.\n", flush=True)

    system = SYSTEM_PROMPT.replace("{comments}",
                                   WITH_COMMENTS if args.comments else NO_COMMENTS)
    t_start, last_write = time.time(), time.time()
    prog = Progress(len(selected), len(selected) - len(todo), title="rewriting functions")
    GATE["gate"] = ModelGate(args.parallel)
    GATE["tuner"] = None
    answered0 = MODEL_ACTIVITY["answered"]
    use = ModelUse()

    def bar_extra():
        # proof of life: is a request with the model right now, and how many came back
        m = (f"model: {'working on ' + str(MODEL_ACTIVITY['waiting']) if MODEL_ACTIVITY['waiting'] else 'idle'}"
             f", {MODEL_ACTIVITY['answered'] - answered0} answers, {use.text()[6:]}")
        return m + (f" | parallel {GATE['gate'].limit}" if args.auto_parallel else "")
    prog.extra = bar_extra
    if args.auto_parallel:
        GATE["tuner"] = AutoParallel(GATE["gate"], args.max_parallel,
                                     args.auto_every * 60, prog.log)
        prog.log(f"  parallel starts at {args.parallel}; adjusting every "
                 f"{args.auto_every} min (max {args.max_parallel})")
    state = threading.RLock()          # guards progress/names when several run at once
    stopping = threading.Event()
    counts = {"done": 0}
    how: dict[str, int] = {}             # how each function was finished this run
    redo_gen = str(progress.get("redo_gen", 0))

    def finish(key, entry, text, kind=None):
        n_calls = calls_on_this_thread()
        if kind is None:
            kind = ("rewritten by the model" if entry.get("status") == "done"
                    else entry.get("reason") or entry["status"])
        if entry.get("status") == "done" and not entry.get("pieces") and not entry.get("tiny"):
            text += f"  · {n_calls} model call{'s' if n_calls != 1 else ''}"
        with state:
            how[kind] = how.get(kind, 0) + 1
            old = done.get(key) or {}
            if entry["status"] != "done" and old.get("status") == "done":
                # a redo that came back empty-handed: keep the previous rewrite, and
                # leave it marked so the next run tries again
                old["redo_failed"] = entry.get("reason") or entry["status"]
                entry = old
                text += "  (kept the previous version; tried again next run)"
            elif entry["status"] == "skipped" and old.get("retries"):
                entry["retries"] = old["retries"]
            done[key] = entry
            dirty[0] = True                   # saved by the main loop (every ~2s)
            if entry["status"] == "done":
                counts["done"] += 1
        prog.end(key, text)

    def work(gname, addr):
        key = f"{addr:x}"
        if stopping.is_set():
            return
        _TL.calls = 0
        prog.begin(key, gname)
        prog.set_phase(key, "getting pseudocode from Ghidra" if ghidra.live and
                       not ghidra.have_pseudocode(addr) else "reading pseudocode")
        pseudo = ghidra.pseudocode(gname, addr)
        if ghidra.notice:
            prog.log(ghidra.notice)
            ghidra.notice = None
        if not pseudo:
            return finish(key, {"ghidra": gname, "status": "skipped",
                                "reason": "no pseudocode from Ghidra"},
                          f"  {gname}: no pseudocode from Ghidra, skipped (tried again "
                          f"next run)")
        safe = re.sub(r"[^\w.-]", "_", gname)
        (P.pseudocode / f"{safe}.c").write_text(pseudo + "\n")
        psha = _pseudo_sha(pseudo)

        # Names already chosen for other functions, swapped in so the model sees them
        with state:
            names = {e["ghidra"]: e["name"] for e in done.values()
                     if e.get("name") and e["name"] != e["ghidra"]}
        shown = apply_names(pseudo, names)
        if args.tiny and is_tiny(shown, args.tiny):
            (P.rewritten_dir / f"{key}.cpp").write_text(tidy_tiny(shown) + "\n")
            return finish(key, {"ghidra": gname, "name": gname, "status": "done",
                                "tiny": True, "pseudo_sha": psha},
                          f"  {gname}: small, copied without the model (--tiny)",
                          kind="copied without the model (--tiny)")
        in_tokens = int((len(shown) + len(system)) / CHARS_PER_TOKEN) + 200
        room = args.ctx - in_tokens
        split_chars = (done.get(key) or {}).get("split_chars")
        if split_chars and not args.no_split:
            # an earlier answer was cut off at the token limit: do it in pieces
            return work_in_pieces(gname, key, shown, names, psha, split_chars)
        if room < 1500:
            if not args.no_split:
                return work_in_pieces(gname, key, shown, names, psha)
            # Too big to fit: cutting it off produces garbage, so leave it for a later
            # run with a larger --ctx
            return finish(key, {"ghidra": gname, "status": "too big"},
                          f"  {gname}: too big for --ctx {args.ctx} (needs about "
                          f"{in_tokens * 2 // 1000 + 1}k), left for later")
        max_out = answer_room(args.ctx, len(shown) + len(system) + 640)
        called = sorted({n for n in names.values()
                         if re.search(rf"\b{re.escape(n)}\s*\(", shown)})
        msg = (f"Function: {gname}"
               + (" (placeholder name: choose a meaningful one)" if PLACEHOLDER.match(gname)
                  else " (keep this name)")
               + (f"\nOther functions it calls were already given these names: "
                  f"{', '.join(called)}" if called else "")
               + f"\n\nGhidra pseudocode:\n```c\n{shown}\n```")
        prog.set_phase(key, f"model writing C++ ({len(shown.splitlines())} lines of "
                            f"pseudocode)")
        reply = ask_model(args.model_in_use, [{"role": "system", "content": system},
                                              {"role": "user", "content": msg}],
                          args.ctx, max_out)
        code, new_name = parse_reply(reply)
        no_code_why = []
        if code is None:
            no_code_why.append(why_no_code(reply))
            raws = [last_reply().get("raw", reply)]
            if no_code_why[-1].startswith("cut off") and not args.no_split:
                # too long to answer in one go: do it again now, in pieces of half
                # the size (pieces that are still cut off are split further)
                prog.set_phase(key, "cut off at the token limit — splitting it")
                return work_in_pieces(gname, key, shown, names, psha,
                                      max(MIN_PIECE_CHARS, len(shown) // 2),
                                      cut_whole=len(shown))
            if not args.no_retry:
                # once more, with all the room left, and without thinking if thinking
                # is what used it up (/no_think switches it off for Qwen3-style models)
                thinking = "thinking" in no_code_why[-1] or last_reply().get("thought", 0) > 0
                prog.set_phase(key, "no code in the reply — asking once more")
                reply = ask_model(args.model_in_use, [
                    {"role": "system", "content": system},
                    {"role": "user", "content": msg + "\n\nReply with the code first: ONE "
                     "```cpp code block with the whole function, then the NAME: line. Keep "
                     "any explanation out." + (" /no_think" if thinking else "")}],
                    args.ctx, max_out)
                code, new_name = parse_reply(reply)
                if code is None:
                    no_code_why.append(why_no_code(reply))
                    raws.append(last_reply().get("raw", reply))
                    if no_code_why[-1].startswith("cut off") and not args.no_split:
                        prog.set_phase(key, "cut off at the token limit — splitting it")
                        return work_in_pieces(gname, key, shown, names, psha,
                                              max(MIN_PIECE_CHARS, len(shown) // 2),
                                              cut_whole=len(shown))
            if code is None:
                d = P.rewrite / "no_code"
                d.mkdir(exist_ok=True)
                (d / f"{key}.txt").write_text(
                    f"{gname}: no usable code. Why: {'; then '.join(no_code_why)}\n"
                    f"prompt ~{in_tokens} tokens, answer room {max_out} tokens (--ctx "
                    f"{args.ctx}); how the last reply ended: "
                    f"{last_reply().get('finish')}"
                    + (f"; server said: {last_reply()['error']}" if last_reply().get("error") else "")
                    + "\n" + "".join(f"\n===== reply {i + 1} =====\n{r}\n"
                                              for i, r in enumerate(raws)))
        ok = False
        if code:
            code, ok = keep_one_function(code, {new_name, gname})

        def problems(c):
            return (len(invented_strings(c, shown)) + len(leftover_names(c))
                    + len(surviving_strings(c, shown)))

        if (not ok or (code and problems(code))) and args.retry_quality \
                and not args.no_retry:
            prog.set_phase(key, "retrying")
            left = leftover_names(code) if code else []
            surv = surviving_strings(code, shown) if code else []
            reply = ask_model(args.model_in_use, [
                {"role": "system", "content": system},
                {"role": "user", "content": msg},
                {"role": "user", "content": "Write ONLY this one function, complete, in one "
                                            "```cpp code block, then NAME: <the name you chose>. Don't add "
                                            "printing or text that isn't in the pseudocode."
                 + (f" Give these decompiler names descriptive names: {', '.join(left[:20])}."
                    if left else "")
                 + (f" Remove these identifying strings (they belong to the original program): "
                    f"{', '.join(repr(s) for s in surv[:10])}."
                    if surv else "")}],
                args.ctx, max_out, temperature=0.4)
            code2, new_name2 = parse_reply(reply)
            if code2:
                code2, ok2 = keep_one_function(code2, {new_name2, gname})
                better = ok2 and (not ok or problems(code2) < problems(code))
                if better or not code:
                    code, new_name, ok = code2, new_name2 or new_name, ok2
        if not code:
            why = no_code_why[-1] if no_code_why else "no code block in the reply"
            entry = {"ghidra": gname, "status": "skipped",
                     "reason": f"model returned no code ({why})"}
            then = "tried again next run"
            if why.startswith("cut off") and not args.no_split:
                # too long to answer in one go: next run splits it into pieces of half
                # its size (and halves again if a piece is still cut off)
                entry["split_chars"] = max(MIN_PIECE_CHARS, len(shown) // 2)
                then = "marked as big — split into pieces next run"
            return finish(key, entry,
                          f"  {gname}: no code from the model — {why}; skipped, {then} "
                          f"(reply saved in rewrite/no_code/{key}.txt)")

        # Compile it; if that fails, repair it incrementally (minimal edits to the
        # failing lines) rather than regenerating the whole function.
        compiled, fixes = None, 0
        if COMPILER["cmd"]:
            prog.set_phase(key, "compiling")
            if args.fix_mode == "edit":
                code, compiled, fixes = incremental_fix(
                    args, code, shown, new_name or gname, prog, key)
            else:
                errors = compile_errors(code)
                while errors and fixes < args.compile_retries:
                    fix = (f"That didn't compile. The compiler said:\n```\n{errors}\n```\n"
                           "Fix it so it compiles as standard C++17 on its own, with the "
                           "same behaviour: include the headers you need, define the structs "
                           "and globals you use, and declare (no body) other functions. Reply "
                           "with the whole function again in one ```cpp code block, then "
                           "NAME: <the name>.")
                    prior = f"```cpp\n{code}\n```\nNAME: {new_name or gname}"
                    need = in_tokens + (len(prior) + len(fix)) / CHARS_PER_TOKEN
                    if need + 500 > args.ctx:
                        break
                    fixes += 1
                    prog.set_phase(key, f"fixing compile errors ({fixes}/{args.compile_retries})")
                    reply = ask_model(args.model_in_use, [
                        {"role": "system", "content": system},
                        {"role": "user", "content": msg},
                        {"role": "assistant", "content": prior},
                        {"role": "user", "content": fix}],
                        args.ctx, max(1500, min(max_out, int(args.ctx - need - 200))))
                    code2, new_name2 = parse_reply(reply)
                    if not code2:
                        continue
                    code2, ok2 = keep_one_function(code2, {new_name2, new_name, gname})
                    if not ok2:
                        continue
                    errors2 = compile_errors(code2)
                    if errors2 is None or n_errors(errors2) <= n_errors(errors):
                        code, errors = code2, errors2
                        new_name = new_name2 or new_name
                compiled = errors is None

        # Faithful fallback: the model couldn't make it compile. Emit the
        # deterministic pseudocode-derived version (type-cleaned, identifying
        # strings removed) instead of a broken rewrite — it's more faithful to
        # the binary and the fixer's recovery (which has the ghidra intrinsics)
        # can compile it. Flagged so you can review these.
        faithful = False
        if compiled is False and COMPILER["cmd"]:
            fb = faithful_from_pseudo(shown)
            if fb and keep_one_function(fb, {gname})[1]:
                code = fb
                new_name = gname          # the faithful version keeps the Ghidra name
                faithful = True

        with state:
            prev_name = done.get(key, {}).get("name")
            if not PLACEHOLDER.match(gname):
                name = gname                              # Ghidra already had a real name
            elif prev_name and prev_name != gname:
                name = prev_name      # rewritten again: keep the name its callers use
            elif new_name and new_name != gname and not PLACEHOLDER.match(new_name) \
                    and not BAD_NAME.match(new_name):
                name = unique_name(new_name, taken - {done.get(key, {}).get("name")})
                taken.add(name)
            else:
                name = gname
        # Make the code use the chosen name. This also covers the case where the
        # model's name was REJECTED (name == gname): the body was written with
        # new_name (e.g. "theFunctionName"), so it must be swapped back to gname,
        # or every rejected function ends up defining the same duplicate name.
        if new_name and new_name != name and new_name != gname:
            code = re.sub(rf"\b{re.escape(new_name)}\b", name, code)
        if name != gname:
            code = re.sub(rf"\b{re.escape(gname)}\b", name, code)
        (P.rewritten_dir / f"{key}.cpp").write_text(code + "\n")
        entry = {"ghidra": gname, "name": name, "status": "done", "pseudo_sha": psha}
        if new_name and new_name not in (name, gname) and name == prev_name:
            entry["suggested_name"] = new_name
        if compiled is not None:
            entry["compiled"] = compiled
        why = suspect_reasons(code, shown, name if name != gname else None)
        if PLACEHOLDER.match(gname) and name == gname:
            why.append("no real name")      # the model's name was unusable
        if faithful:
            entry["faithful"] = True
            why.append("faithful fallback (model couldn't compile a clean rewrite)")
        if compiled is False:
            why.append("doesn't compile")
        if why:
            entry["suspect"] = sorted(set(why))
        note = ("compiles" if compiled and not fixes else
                f"compiles after {fixes} fix{'es' if fixes > 1 else ''}" if compiled else "")
        finish(key, entry, f"  {gname} -> {name}  ({{secs}}{', ' + note if note else ''})"
               + (f"  [check: {', '.join(entry['suspect'])}]" if why else ""))

    piece_system = PIECE_PROMPT.replace("{comments}",
                                        WITH_COMMENTS if args.comments else NO_COMMENTS)

    def work_in_pieces(gname, key, shown, names, psha, split_chars=None, cut_whole=None):
        parts = split_function(shown)
        if not parts:
            return finish(key, {"ghidra": gname, "status": "too big"},
                          f"  {gname}: too big, and couldn't be split, left for later")
        header, decls, lines = parts
        decl_text = "\n".join(d.strip() for d in decls)
        if len(decl_text) > 2000:
            decl_text = decl_text[:2000].rsplit("\n", 1)[0] + "\n..."
        overhead = len(piece_system) + len(header) + len(decl_text) + 900
        max_chars = piece_chars(args.ctx, overhead)
        if split_chars:                       # cut off before: start at the size recorded
            max_chars = min(max_chars, split_chars)
        pieces = chunk_lines(lines, max_chars)
        n = len(pieces)
        pdir = P.rewritten_dir / f"{key}.parts"
        pdir.mkdir(exist_ok=True)
        # pieces saved by an interrupted attempt are reused, unless they belong to an
        # earlier round than this --redo (then they're overwritten one by one)
        gen_file = pdir / "gen.txt"
        reuse = not gen_file.exists() or gen_file.read_text().strip() == redo_gen
        gen_file.write_text(redo_gen)
        placeholder = PLACEHOLDER.match(gname)
        state_ = {"done": 0, "fallback": 0, "name": None, "reused": 0,
                  "cut": [], "stuck": 0}      # sizes that were cut off; cut-offs at the smallest size
        lock_ = threading.Lock()
        prog.set_phase(key, f"big: 0/{n} parts")

        def try_piece(piece, label, prev_tail, ask_name):
            """One piece, one answer (plus one more for a badly formatted answer).
            (code or None, chosen name, whether the answer was cut off)."""
            ctx_text = ""
            if prev_tail:
                ctx_text = (f"Its local variables:\n```c\n{decl_text}\n```\n"
                            f"The piece before this one ends with:\n```c\n{prev_tail}\n```\n")
            msg = (f"Function: {gname}, piece {label}\n"
                   f"Function header: {header}\n{ctx_text}\n"
                   f"Piece {label} to rewrite:\n```c\n{piece}\n```"
                   + ("\n\nAfter the code block, also write one line NAME: followed by "
                      "a meaningful lowerCamelCase name for the whole function, "
                      "judging from this first piece." if ask_name else ""))
            max_out = answer_room(args.ctx, len(piece_system) + len(msg))
            reply = ask_model(args.model_in_use,
                              [{"role": "system", "content": piece_system},
                               {"role": "user", "content": msg}], args.ctx, max_out)
            code, new_name = parse_reply(reply)
            got = clean_piece(code or "", piece, set(names.values()) | {gname})
            if got is None and why_no_code(reply).startswith("cut off"):
                return None, new_name, True   # same size again would fail the same way
            if got is None and not args.no_retry:
                reply = ask_model(args.model_in_use, [
                    {"role": "system", "content": piece_system},
                    {"role": "user", "content": msg + "\n\nRewrite ONLY these lines, "
                     "keeping every unmatched { and } where it is. No function header."}],
                    args.ctx, max_out, temperature=0.4)
                code, new_name2 = parse_reply(reply)
                got = clean_piece(code or "", piece, set(names.values()) | {gname})
                new_name = new_name or new_name2
                return got, new_name, got is None and why_no_code(reply).startswith("cut off")
            return got, new_name, False

        def do_piece(piece, label, prev_tail, ask_name, depth=0):
            """A piece; if the answer is cut off at the token limit, split the piece in
            half and do the halves (and so on, down to the smallest size)."""
            got, name, cut = try_piece(piece, label, prev_tail, ask_name)
            if got is not None or not cut:
                return got, name
            with lock_:
                state_["cut"].append(len(piece))
            subs = chunk_lines(piece.split("\n"), max(MIN_PIECE_CHARS, len(piece) // 2)) \
                if len(piece) > MIN_PIECE_CHARS and depth < 5 else [piece]
            if len(subs) < 2:
                with lock_:
                    state_["stuck"] += 1      # can't split any further
                return None, name
            prog.set_phase(key, f"piece {label} was cut off — splitting it in {len(subs)}")
            outs, tail = [], prev_tail
            for j, sp in enumerate(subs):
                g2, n2 = do_piece(sp, f"{label}.{j + 1}", tail, ask_name and j == 0, depth + 1)
                outs.append(g2 if g2 is not None
                            else "// [left as Ghidra wrote it]\n" + tidy_types(sp))
                name = name or n2
                tail = "\n".join(sp.split("\n")[-8:])
            return "\n".join(outs), name

        def one(i):
            piece = pieces[i]
            h = hashlib.sha1(piece.encode()).hexdigest()[:10]
            f = pdir / f"{i:04d}-{h}.cpp"
            if f.exists() and reuse:            # done in an earlier session
                got = f.read_text()
                with lock_:
                    state_["reused"] += 1
                if i == 0 and (pdir / "name.txt").exists():
                    state_["name"] = (pdir / "name.txt").read_text().strip() or None
            else:
                prev_tail = "\n".join(pieces[i - 1].split("\n")[-8:]) if i > 0 else ""
                ask_name = i == 0 and placeholder
                got, new_name = do_piece(piece, f"{i + 1} of {n}", prev_tail, ask_name)
                if got is None:                 # doesn't fit: keep Ghidra's version
                    got = "// [left as Ghidra wrote it]\n" + tidy_types(piece)
                pdir.mkdir(parents=True, exist_ok=True)
                if ask_name and new_name:
                    state_["name"] = new_name
                    (pdir / "name.txt").write_text(new_name)
                f.write_text(got)
            with lock_:
                state_["done"] += 1
                if "// [left as Ghidra wrote it]" in got:
                    state_["fallback"] += 1
                prog.set_phase(key, f"big: {state_['done']}/{n} parts")
            return got

        # The pieces don't depend on each other, so several can be written at once;
        # the model limit still applies to all of them together.
        with ThreadPoolExecutor(max_workers=min(n, max(1, GATE["gate"].limit))) as pp:
            results = list(pp.map(one, range(n)))

        new_name = state_["name"]
        with state:
            prev_name = done.get(key, {}).get("name")
            if not placeholder:
                name = gname
            elif prev_name and prev_name != gname:
                name = prev_name      # rewritten again: keep the name its callers use
            elif new_name and not PLACEHOLDER.match(new_name) and not BAD_NAME.match(new_name):
                name = unique_name(new_name, taken - {done.get(key, {}).get("name")})
                taken.add(name)
            else:
                name = gname
        head = tidy_types(header)
        if name != gname:
            head = re.sub(rf"\b{re.escape(gname)}\b", name, head)
        body = "\n".join(r.replace("// [left as Ghidra wrote it]\n", "") for r in results)
        code = f"{head} {{\n{body}\n}}"
        # Drive the REASSEMBLED big function to compile with the same line-anchored
        # edit loop used for normal functions. This is what makes it size-proof:
        # the fix step only ever sends the ONE failing line to the model, never the
        # whole function, so --ctx is never a constraint during repair.
        compiled, fixes = None, 0
        if COMPILER["cmd"] and args.fix_mode == "edit":
            prog.set_phase(key, "compiling (big)")
            code, compiled, fixes = incremental_fix(args, code, shown, name, prog, key)
        # faithful fallback (same as normal functions): if the reassembled big
        # function still won't compile, emit the deterministic pseudocode version
        faithful = False
        if compiled is False and COMPILER["cmd"]:
            fb = faithful_from_pseudo(shown)
            if fb:
                if name != gname:
                    fb = re.sub(rf"\b{re.escape(gname)}\b", name, fb)
                code = fb
                faithful = True
        (P.rewritten_dir / f"{key}.cpp").write_text(code + "\n")
        shutil.rmtree(pdir, ignore_errors=True)    # scratch pieces, now joined above
        entry = {"ghidra": gname, "name": name, "status": "done", "pieces": n,
                 "pseudo_sha": psha}
        if split_chars:
            entry["split_chars"] = split_chars
        if cut_whole:
            state_["cut"].append(cut_whole)      # the whole function was cut off first
        if state_["cut"]:
            # what happened, so the next run starts below the smallest size that was
            # cut off instead of trying a size that already failed
            entry["cut_off_sizes"] = sorted(set(state_["cut"]), reverse=True)
            entry["split_chars"] = max(MIN_PIECE_CHARS, min(state_["cut"]) // 2)
            if state_["stuck"]:
                entry["cut_off_at_smallest"] = state_["stuck"]
        if compiled is not None:
            entry["compiled"] = compiled
        # the pieces keep Ghidra's variable names on purpose, so don't flag those
        why = suspect_reasons(code, shown, name if name != gname else None, check_names=False)
        if placeholder and name == gname:
            why.append("no real name")
        if faithful:
            entry["faithful"] = True
            why.append("faithful fallback (model couldn't compile a clean rewrite)")
        if compiled is False:
            why.append("doesn't compile")
        if state_["fallback"]:
            why.append(f"{state_['fallback']} of {n} parts left as Ghidra wrote them")
        if why:
            entry["suspect"] = sorted(set(why))
        note = ("compiles" if compiled and not fixes else
                f"compiles after {fixes} fix{'es' if fixes != 1 else ''}" if compiled else
                "not compiling" if compiled is False else "")
        finish(key, entry, f"  {gname} -> {name}  (big: {n} parts"
               + (f", {state_['reused']} saved from an earlier session" if state_["reused"]
                  else "")
               + (f", {note}" if note else "") + ", {secs})"
               + (f"  [check: {', '.join(entry['suspect'])}]" if why else ""))

    # Keep functions in progress, handed out in program order: --parallel with the
    # model, plus a few more being prepared (pseudocode, prompt) so a request is
    # always waiting the moment the model finishes one.
    pending, it = set(), iter(todo)
    warned = [0.0]
    dirty = [False]
    last_save = [time.time()]
    out_every = [30.0]

    def save_now():
        with state:
            if dirty[0]:
                save_progress(P, progress)
                dirty[0] = False
        last_save[0] = time.time()

    def outputs_now():
        # from a copy, so finishing functions never wait for this (it reads every
        # function and can take a while on a big program)
        with state:
            snap = {"functions": {k: dict(v) for k, v in done.items()}}
        t0 = time.time()
        write_outputs(P, snap, order, args.comments)
        out_every[0] = max(30.0, 10 * (time.time() - t0))
    reached_max = False
    try:
        workers = (args.max_parallel + 4) if args.auto_parallel else args.parallel + 2
        # (not a "with" block: leaving one waits for every function in progress to
        # finish, which made Ctrl+C slow to pause)
        pool = ThreadPoolExecutor(max_workers=workers)
        while True:
            # with --auto-parallel, a few extra functions are kept ready (pseudocode
            # fetched) so the model never waits on Ghidra
            target = GATE["gate"].limit + 4 if args.auto_parallel else args.parallel + 2
            while len(pending) < target and not stopping.is_set():
                if args.max and counts["done"] + len(pending) >= args.max:
                    break                             # --max: no more than asked for
                nxt = next(it, None)
                if nxt is None:
                    break
                pending.add(pool.submit(work, *nxt))
            if not pending:
                break
            finished, pending = wait(pending, timeout=5, return_when=FIRST_COMPLETED)
            for f in finished:
                f.result()                            # surface any error
            quiet = time.time() - MODEL_ACTIVITY["last"]
            if MODEL_ACTIVITY["waiting"] and quiet > 180 and time.time() - warned[0] > 600:
                warned[0] = time.time()
                prog.log(f"  !! no word from the model for {fmt_duration(quiet)} although "
                         f"{MODEL_ACTIVITY['waiting']} request(s) are waiting. Check LM "
                         f"Studio's server log: the model may have been unloaded or be stuck "
                         f"(a huge prompt can also take this long).")
            if dirty[0] and time.time() - last_save[0] > 2:
                save_now()
            if time.time() - last_write > out_every[0]:
                outputs_now()
                last_write = time.time()
            if args.max and counts["done"] >= args.max and not stopping.is_set():
                stopping.set()                        # let the ones running finish
                reached_max = True
        pool.shutdown(wait=True)
    except KeyboardInterrupt:
        stopping.set()
        STOPPING.set()
        prog.close()
        save_now()
        try:
            error_summary(P)
        except Exception:
            pass
        with state:
            write_outputs(P, progress, order, args.comments)
        try:
            write_report(P)
        except Exception:
            pass
        print("\nPaused. Run the same command to carry on from here.")
        os._exit(0)                       # don't wait for replies still being written
    prog.close()
    save_now()
    if GATE["tuner"]:
        GATE["tuner"].stop.set()
    write_outputs(P, progress, order, args.comments)
    try:
        ghidra.write_callgraph(P.callgraph, {e["ghidra"]: e["name"] for e in done.values()
                                             if e.get("name") and e["name"] != e["ghidra"]})
    except Exception:
        pass
    mins = (time.time() - t_start) / 60
    plog(P, f"  this run: {counts['done']} function(s) done in {fmt_duration(mins * 60)}, "
            f"{MODEL_ACTIVITY['answered'] - answered0} model answers"
            + (": " + ", ".join(f"{n} {k}" for k, n in how.items()) if how else ""))
    if reached_max:
        plog(P, f"  reached --max {args.max}; stopping here. Run the same command to continue.")
    return _rewrite_summary(progress, order, stop=reached_max, model=model)


def _rewrite_summary(progress, order, stop=False, model=None) -> dict:
    fs = progress.get("functions", {})
    es = [fs[k] for k in order if k in fs]
    done = [e for e in es if e.get("status") == "done"]
    reasons: dict[str, int] = {}
    for e in done:
        for r in e.get("suspect") or []:
            r = re.sub(r"^\d+ of \d+ parts", "some parts", r)
            reasons[r] = reasons.get(r, 0) + 1
    out = {"functions": len(order), "done": len(done),
           "stale": sum(1 for e in done if e.get("stale")),
           "skipped": sum(1 for e in es if e.get("status") in ("skipped", "redo")),
           "too_big": sum(1 for e in es if e.get("status") == "too big"),
           "not_started": len(order) - len(es),
           "renamed": sum(1 for e in done if e.get("name") and e["name"] != e.get("ghidra")),
           "tiny": sum(1 for e in done if e.get("tiny")),
           "in_pieces": sum(1 for e in done if e.get("pieces")),
           "faithful": sum(1 for e in done if e.get("faithful")),
           "suspect": sum(1 for e in done if e.get("suspect")),
           "suspect_reasons": dict(sorted(reasons.items(), key=lambda t: -t[1])),
           "stop": stop}
    if model:
        out["model"] = model
    return out



# ============================================================================
# Stages: split / fix / recover / link  (the build)
# ============================================================================
# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------

@dataclass
class Config:
    input_file: Path
    workdir: Path
    cxx: str = "clang++"
    std: str = "c++17"
    # the shared model client, the model asked for (None: the loaded one), and the
    # one actually used once model_check() has run
    client: Optional[ModelClient] = None
    wanted_model: Optional[str] = None
    fix_model_used: Optional[str] = None
    model_temperature: float = 0.1
    model_max_tokens: int = 2048
    model_timeout_s: int = 180
    # fixer loop
    max_model_attempts: int = 3
    # libclang dylib path override (macOS Homebrew LLVM often needs this)
    libclang_path: Optional[str] = None
    # extra include dirs / compile flags for the real build
    extra_flags: list[str] = field(default_factory=list)
    # optional Ghidra call-graph export (json / csv / graphml). When set, used
    # for dependency ordering instead of the regex heuristic.
    callgraph_path: Optional[Path] = None
    # keep going even if the header gate / preflight says everything will fail
    force: bool = False
    # link step: stub every undefined symbol that has a prototype, not only
    # quarantined functions and Ghidra FUN_/DAT_ names
    stub_all: bool = False
    # pseudocode recovery: the export and the rewrite's name -> address index.
    # model_ctx_chars: prompt budget before a function is repaired by error-window
    # patching instead of a full rewrite.
    export_path: Optional[Path] = None
    index_path: Optional[Path] = None
    model_ctx_chars: int = 24000
    retry_quarantined: bool = False   # revive manifest quarantines for another pass
    no_pseudo: bool = False           # skip the pseudocode recovery stage
    # where files about to be replaced are copied first (None: don't)
    snapshot_dir: object = field(default_factory=lambda: (lambda: None))
    workers: int = 1                  # functions worked on at once (CPU side)
    ctx: int = 16384                  # the model's context (--ctx), for answer room

    @property
    def funcs_dir(self) -> Path: return self.workdir / "funcs"
    @property
    def shared_h(self) -> Path: return self.workdir / "shared.h"
    @property
    def intrins_h(self) -> Path: return self.workdir / "ghidra_intrins.h"
    @property
    def globals_cpp(self) -> Path: return self.workdir / "globals.cpp"
    @property
    def manifest_path(self) -> Path: return self.workdir / "manifest.json"
    @property
    def cache_path(self) -> Path: return self.workdir / "fix_cache.json"
    @property
    def quarantine_dir(self) -> Path: return self.workdir / "quarantine"
    @property
    def log_path(self) -> Path: return self.workdir / "worklist.log"


# ----------------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------------

def log(cfg: Config, msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    say(line)
    with open(cfg.log_path, "a") as f:
        f.write(line + "\n")
        f.flush()
        os.fsync(f.fileno())


# ----------------------------------------------------------------------------
# Stage 0 — intrinsics header
# ----------------------------------------------------------------------------

GHIDRA_INTRINS_H = r"""#pragma once
// ghidra_intrins.h — typedefs + helpers to make Ghidra pseudocode-ish C++ compile.
#include <cstdint>
#include <cstring>

// --- Ghidra "undefined" width typedefs ---
typedef uint8_t   undefined;
typedef uint8_t   undefined1;
typedef uint16_t  undefined2;
typedef uint32_t  undefined4;
typedef uint64_t  undefined8;
typedef uint8_t   byte;
typedef uint16_t  word;
typedef uint32_t  dword;
typedef uint64_t  qword;
typedef unsigned int   uint;
typedef unsigned short ushort;
typedef unsigned char  uchar;
typedef unsigned long  ulong;
typedef long long          longlong;
typedef unsigned long long ulonglong;
typedef signed char        sbyte;

// --- CONCAT / SUB / ZEXT / SEXT family (common Ghidra pseudo-intrinsics) ---
// CONCATxy: concatenate an x-byte high part and a y-byte low part.
static inline uint16_t CONCAT11(uint8_t  h, uint8_t  l){ return (uint16_t(h)<<8)  | l; }
static inline uint32_t CONCAT22(uint16_t h, uint16_t l){ return (uint32_t(h)<<16) | l; }
static inline uint32_t CONCAT13(uint8_t  h, uint32_t l){ return (uint32_t(h)<<24) | (l & 0x00FFFFFFu); }
static inline uint32_t CONCAT31(uint32_t h, uint8_t  l){ return (uint32_t(h)<<8)  | l; }
static inline uint64_t CONCAT44(uint32_t h, uint32_t l){ return (uint64_t(h)<<32) | l; }
static inline uint64_t CONCAT17(uint8_t  h, uint64_t l){ return (uint64_t(h)<<56) | (l & 0x00FFFFFFFFFFFFFFull); }
static inline uint64_t CONCAT71(uint64_t h, uint8_t  l){ return (uint64_t(h)<<8)  | l; }

// SUBxy(value, byteOffset-ish): extract y low bytes after shifting. Ghidra's SUB
// means "take y bytes of an x-byte value". We approximate with masking helpers;
// the de-ghidra text pass rewrites the common SUBxy(v,0) forms to plain casts,
// so these are a safety net for the rarer offsets.
template<typename T> static inline uint8_t  SUB_u8 (T v){ return  (uint8_t)v;  }
template<typename T> static inline uint16_t SUB_u16(T v){ return (uint16_t)v; }
template<typename T> static inline uint32_t SUB_u32(T v){ return (uint32_t)v; }

static inline uint32_t ZEXT14(uint8_t  v){ return v; }
static inline uint32_t ZEXT24(uint16_t v){ return v; }
static inline uint64_t ZEXT18(uint8_t  v){ return v; }
static inline uint64_t ZEXT48(uint32_t v){ return v; }
static inline int32_t  SEXT14(int8_t   v){ return v; }
static inline int32_t  SEXT24(int16_t  v){ return v; }
static inline int64_t  SEXT48(int32_t  v){ return v; }
"""

# Standard headers the decompiled C++ leans on (std::string, ostream, exceptions,
# pthread types...). Included both when libclang parses the monolith and at the
# top of shared.h, so these types resolve instead of being dropped as unknown.
STD_INCLUDES = [
    "<cstdint>", "<cstddef>", "<cstring>", "<cstdlib>", "<cstdio>", "<cmath>",
    "<string>", "<vector>", "<map>", "<set>", "<list>", "<deque>", "<memory>",
    "<functional>", "<algorithm>", "<utility>", "<iostream>", "<ostream>",
    "<istream>", "<sstream>", "<fstream>", "<stdexcept>", "<exception>", "<new>",
    "<typeinfo>", "<locale>", "<mutex>", "<atomic>", "<pthread.h>",
]


def write_intrinsics(cfg: Config) -> None:
    cfg.intrins_h.write_text(GHIDRA_INTRINS_H)


# ----------------------------------------------------------------------------
# Stage 1 — Splitter (libclang two-pass)
# ----------------------------------------------------------------------------
#
# shared.h is now REBUILT from libclang's typed view of every declaration
# (struct fields, enum constants, typedef targets, globals, prototypes) instead
# of slicing raw source text. Every declaration is written as one "unit":
#
#     //@unit 42 record applyLowpassFilter6432
#     struct applyLowpassFilter6432 {
#         undefined8 field_0x0;
#         float coeff;
#     };
#
# The markers let the header repair step switch off a WHOLE declaration with
# #if 0 / #endif (or drop one single-line field inside a struct). It never
# comments out a lone line like `struct X {` or `};`, which is what used to
# leave a struct unclosed and swallow every prototype after it.

@dataclass
class FuncRecord:
    name: str            # spelling
    mangled: str         # mangled name -> filename key
    file: str            # relative path under funcs/
    start: int           # byte offset in monolith
    end: int             # byte offset in monolith
    compiles: bool = False
    quarantined: bool = False
    deps: list[str] = field(default_factory=list)   # mangled names of internal callees
    attempts: int = 0
    last_error: str = ""
    ghidra_addr: str = ""   # address from the //@ghidra marker, to find pseudocode
    rederived: bool = False # rebuilt from pseudocode by the recovery stage
    recovery: str = ""      # how it was recovered (rewrite / window-patch / faithful)
    recovery_tried: bool = False  # pseudocode recovery attempted and failed
    src_sha: str = ""       # hash of the function's code in the rewrite, at split time:
                            # tells a resume whether the rewrite changed this function
    recovery_model: str = ""  # the model the last recovery attempt used
    duplicate_of: str = ""  # merged into this identical function by the improve stage


def _load_libclang(cfg: Config):
    import clang.cindex as cx
    if cx.Config.loaded:          # already set up earlier in this process
        return cx
    if cfg.libclang_path:
        cx.Config.set_library_file(cfg.libclang_path)
    else:
        # best-effort autodiscovery for common macOS/Linux locations
        for cand in (
            "/Library/Developer/CommandLineTools/usr/lib/libclang.dylib",
            "/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/lib/libclang.dylib",
            "/opt/homebrew/opt/llvm/lib/libclang.dylib",
            "/usr/local/opt/llvm/lib/libclang.dylib",
            "/usr/lib/llvm-18/lib/libclang.so.1",
            "/usr/lib/x86_64-linux-gnu/libclang-18.so.1",
        ):
            if os.path.exists(cand):
                cx.Config.set_library_file(cand)
                break
    return cx


def _libclang_args(cfg: Config) -> list[str]:
    """Args for libclang. Same std/include/extra flags as the real compile, and
    on macOS the SDK sysroot — without it libclang often can't find <cstdint>
    and silently turns every uint32_t etc. into `int`."""
    args = [f"-std={cfg.std}", f"-I{cfg.workdir}", "-x", "c++", *cfg.extra_flags]
    if sys.platform == "darwin" and not any(a.startswith("-isysroot") for a in args):
        try:
            sdk = subprocess.run(["xcrun", "--show-sdk-path"], capture_output=True,
                                 text=True, timeout=20).stdout.strip()
            if sdk:
                args += ["-isysroot", sdk]
        except Exception:
            pass
    return args


ANON_MARKERS = ("(unnamed", "(anonymous", "(lambda")
RECORD_KIND_NAMES = {"STRUCT_DECL", "CLASS_DECL", "UNION_DECL"}


def _is_anon_text(s: str) -> bool:
    return any(m in s for m in ANON_MARKERS)


def _anon(c) -> bool:
    return (not c.spelling) or _is_anon_text(c.spelling)


def _cmt(s: str) -> str:
    """Make arbitrary text safe inside a /* */ comment, on one line."""
    s = re.sub(r"\s+", " ", s).strip().replace("*/", "* /")
    return s[:140] + ("..." if len(s) > 140 else "")


class _ErrIndex:
    """Byte offsets of libclang ERROR diagnostics in the monolith, so a
    declaration whose text contains an error can be detected. libclang does NOT
    mark these types invalid — an unknown type name is silently reported as
    `int` — so this is the only reliable signal."""
    def __init__(self, tu, path: str):
        import bisect
        self._bisect = bisect
        items = sorted(
            (d.location.offset, d.spelling) for d in tu.diagnostics
            if d.severity >= 3 and d.location.file is not None
            and d.location.file.name == path)
        self.offs = [o for o, _ in items]
        self.msgs = [m for _, m in items]

    def within(self, c, ignore: Optional[re.Pattern] = None) -> bool:
        s, e = c.extent.start.offset, c.extent.end.offset
        i = self._bisect.bisect_left(self.offs, s)
        while i < len(self.offs) and self.offs[i] <= e:
            if ignore is None or not ignore.search(self.msgs[i]):
                return True
            i += 1
        return False


# errors that only say "this name is already defined" — expected for duplicate
# definitions, which get renamed instead of skipped
_DUP_DEF_ERR = re.compile(r"differ only in their return type|^redefinition of")


def _declarator(t, inner: str) -> str:
    """Build a C++ declaration of `inner` with type `t`, from libclang's type
    tree, so arrays and function pointers come out right:
    int[4] + 'x' -> 'int x[4]',  void(*)(int) + 'cb' -> 'void (*cb)(int)'."""
    k = t.kind.name
    if k in ("POINTER", "LVALUEREFERENCE", "RVALUEREFERENCE"):
        sym = {"POINTER": "*", "LVALUEREFERENCE": "&", "RVALUEREFERENCE": "&&"}[k]
        pointee = t.get_pointee()
        q = "const " if (k == "POINTER" and t.is_const_qualified()) else ""
        new = f"{sym}{q}{inner}"
        if pointee.kind.name in ("FUNCTIONPROTO", "FUNCTIONNOPROTO",
                                 "CONSTANTARRAY", "INCOMPLETEARRAY"):
            new = f"({new})"
        return _declarator(pointee, new)
    if k == "CONSTANTARRAY":
        return _declarator(t.element_type, f"{inner}[{t.element_count}]")
    if k == "INCOMPLETEARRAY":
        return _declarator(t.element_type, f"{inner}[]")
    if k in ("FUNCTIONPROTO", "FUNCTIONNOPROTO"):
        params = [a.spelling for a in t.argument_types()] if k == "FUNCTIONPROTO" else []
        if k == "FUNCTIONPROTO" and t.is_function_variadic():
            params.append("...")
        return _declarator(t.get_result(), f"{inner}({', '.join(params)})")
    base = t.spelling or "int"
    return f"{base} {inner}".strip() if inner else base


def _needs(t, by_value: bool, out: set, depth: int = 0) -> None:
    """Collect USRs of declarations that must appear BEFORE something using
    type `t`. Typedef names always (the name must exist); records only when
    used by value (pointers are covered by the forward-declaration block)."""
    if depth > 25:
        return
    k = t.kind.name
    try:
        if k == "TYPEDEF":
            u = t.get_declaration().get_usr()
            if u:
                out.add(u)
            if by_value:
                _needs(t.get_canonical(), True, out, depth + 1)
        elif k == "ELABORATED":
            _needs(t.get_named_type(), by_value, out, depth + 1)
        elif k == "RECORD":
            if by_value:
                u = t.get_declaration().get_usr()
                if u:
                    out.add(u)
        elif k in ("POINTER", "LVALUEREFERENCE", "RVALUEREFERENCE"):
            _needs(t.get_pointee(), False, out, depth + 1)
        elif k in ("CONSTANTARRAY", "INCOMPLETEARRAY"):
            _needs(t.element_type, by_value, out, depth + 1)
        elif k == "FUNCTIONPROTO":
            _needs(t.get_result(), False, out, depth + 1)
            for a in t.argument_types():
                _needs(a, False, out, depth + 1)
    except Exception:
        pass


@dataclass
class _Unit:
    kind: str               # fwd | record | enum | typedef | global | proto
    label: str
    lines: list[str]
    order: int
    provides: set = field(default_factory=set)
    needs: set = field(default_factory=set)


class _SplitStats:
    def __init__(self):
        self.notes: list[str] = []
        self.unresolved_fields = 0
        self.skipped: dict[str, int] = {}

    def skip(self, kind: str, what: str, why: str):
        self.skipped[kind] = self.skipped.get(kind, 0) + 1
        self.notes.append(f"skipped {kind} {what}: {why}")


def _enum_line(c, name: Optional[str]) -> str:
    under = c.enum_type.spelling or "int"
    try:
        scoped = c.is_scoped_enum()
    except Exception:
        scoped = False
    items = [f"{e.spelling} = {e.enum_value}" for e in c.get_children()
             if e.kind.name == "ENUM_CONSTANT_DECL"]
    head = "enum class" if scoped else "enum"
    nm = f" {name}" if name else ""
    return f"{head}{nm} : {under} {{ {', '.join(items)} }};"


def _method_line(m, err: "_ErrIndex", owner: str) -> Optional[str]:
    k = m.kind.name
    try:
        if k == "CONSTRUCTOR":
            params = ", ".join(a.spelling for a in m.type.argument_types())
            return f"{owner}({params});"
        if k == "DESTRUCTOR":
            v = "virtual " if m.is_virtual_method() else ""
            return f"{v}~{owner}();"
        # CXX_METHOD
        pre = ("static " if m.is_static_method() else "") + \
              ("virtual " if m.is_virtual_method() else "")
        post = (" const" if m.is_const_method() else "") + \
               (" = 0" if m.is_pure_virtual_method() else "")
        return f"{pre}{_declarator(m.type, m.spelling)}{post};"
    except Exception:
        return None


def _record_members(c, err: "_ErrIndex", stats: _SplitStats, needs: set,
                    provides: set) -> list[str]:
    """One string per member, each COMPLETE on a single line (nested records are
    written inline on one line). That guarantees any single interior line of a
    struct can be dropped without unbalancing braces."""
    owner = c.spelling
    out: list[str] = []
    children = list(c.get_children())

    # anonymous records that a field uses as its type (`struct { .. } inner;`)
    field_anon_decls = []
    for f in children:
        if f.kind.name == "FIELD_DECL":
            t = f.type
            while t.kind.name in ("CONSTANTARRAY", "INCOMPLETEARRAY"):
                t = t.element_type
            d = t.get_canonical().get_declaration()
            if d.kind.name in RECORD_KIND_NAMES and _anon(d):
                field_anon_decls.append(d)

    for m in children:
        k = m.kind.name
        if k == "FIELD_DECL":
            if err.within(m):
                stats.unresolved_fields += 1
                out.append(f"/* [unresolved field: unknown type] "
                           f"{_cmt(_raw(m))} */")
                continue
            name = m.spelling or ""
            d = _declarator(m.type, name)
            if _is_anon_text(d):
                # field of an anonymous record type -> write the record inline
                t, dims = m.type, ""
                while t.kind.name == "CONSTANTARRAY":
                    dims += f"[{t.element_count}]"
                    t = t.element_type
                rd = t.get_canonical().get_declaration()
                if rd.kind.name in RECORD_KIND_NAMES and _anon(rd):
                    out.append(f"{_record_inline(rd, err, stats, needs, provides)} {name}{dims};")
                else:
                    sz = m.type.get_size()
                    if sz and sz > 0:
                        out.append(f"uint8_t {name}[{sz}]; /* opaque: anonymous type */")
                    else:
                        out.append(f"/* [dropped field with anonymous type] {_cmt(_raw(m))} */")
                continue
            try:
                if m.is_bitfield():
                    d += f" : {m.get_bitfield_width()}"
            except Exception:
                pass
            _needs(m.type, True, needs)
            out.append(d + ";")
        elif k in RECORD_KIND_NAMES:
            if any(m == fd for fd in field_anon_decls):
                continue  # written inline with its field
            if not m.is_definition():
                if not _anon(m):
                    kw = "union" if k == "UNION_DECL" else "struct"
                    out.append(f"{kw} {m.spelling};")
                continue
            out.append(_record_inline(m, err, stats, needs, provides) + ";")
        elif k == "ENUM_DECL":
            if m.is_definition():
                out.append(_enum_line(m, None if _anon(m) else m.spelling))
        elif k in ("TYPEDEF_DECL", "TYPE_ALIAS_DECL"):
            if err.within(m):
                out.append(f"/* [unresolved typedef] {_cmt(_raw(m))} */")
                continue
            d = _declarator(m.underlying_typedef_type, m.spelling)
            if not _is_anon_text(d):
                _needs(m.underlying_typedef_type, False, needs)
                out.append(f"typedef {d};")
        elif k in ("CXX_METHOD", "CONSTRUCTOR", "DESTRUCTOR"):
            if err.within(m):
                out.append(f"/* [unresolved method] {_cmt(m.displayname)} */")
                continue
            line = _method_line(m, err, owner)
            if line and not _is_anon_text(line):
                _needs(m.type, False, needs)
                out.append(line)
        elif k == "VAR_DECL":  # static data member
            if not err.within(m):
                d = _declarator(m.type, m.spelling)
                if not _is_anon_text(d):
                    out.append(f"static {d};")
        elif k == "CXX_ACCESS_SPEC_DECL":
            try:
                out.append(m.access_specifier.name.lower() + ":")
            except Exception:
                pass
        # base specifiers handled by the caller; anything else is ignored
    return out


def _record_inline(c, err, stats, needs, provides) -> str:
    kw = "union" if c.kind.name == "UNION_DECL" else "struct"
    try:
        u = c.get_usr()
        if u:
            provides.add(u)
    except Exception:
        pass
    nm = "" if _anon(c) else f" {c.spelling}"
    members = _record_members(c, err, stats, needs, provides)
    return f"{kw}{nm} {{ {' '.join(members)} }}"


def _record_bases(c, err, needs) -> str:
    bases = []
    for b in c.get_children():
        if b.kind.name == "CXX_BASE_SPECIFIER" and not err.within(b):
            try:
                acc = b.access_specifier.name.lower()
                acc = acc if acc in ("public", "protected", "private") else "public"
            except Exception:
                acc = "public"
            bases.append(f"{acc} {b.type.spelling}")
            _needs(b.type, True, needs)
    return (" : " + ", ".join(bases)) if bases else ""


def _record_unit(c, err, stats, order: int, typedef_name: Optional[str] = None) -> _Unit:
    """Multi-line struct: header line, one member per line, closing line."""
    kw = "union" if c.kind.name == "UNION_DECL" else "struct"
    needs: set = set()
    provides: set = set()
    try:
        provides.add(c.get_usr())
    except Exception:
        pass
    members = _record_members(c, err, stats, needs, provides)
    bases = _record_bases(c, err, needs)
    if typedef_name:   # typedef of an anonymous struct
        lines = [f"typedef {kw}{bases} {{"] + ["    " + m for m in members] + [f"}} {typedef_name};"]
        label = typedef_name
    else:
        lines = [f"{kw} {c.spelling}{bases} {{"] + ["    " + m for m in members] + ["};"]
        label = c.spelling
    return _Unit("record", label, lines, order, provides, needs - provides)


_RAW_BYTES: bytes = b""


def _raw(c) -> str:
    return _RAW_BYTES[c.extent.start.offset:c.extent.end.offset].decode("utf-8", "replace")


def _top_level(tu, path: str):
    """Top-level cursors from the monolith itself, descending into extern "C"
    blocks (which the old splitter skipped entirely)."""
    for c in tu.cursor.get_children():
        if c.location.file is None or c.location.file.name != path:
            continue
        if c.kind.name == "LINKAGE_SPEC":
            for k in c.get_children():
                yield k
        else:
            yield c


def _order_units(units: list[_Unit]) -> list[_Unit]:
    """Source order, but anything a unit needs (a struct used by value, a
    typedef name) is moved ahead of it. Cycles fall back to source order."""
    by_usr: dict[str, _Unit] = {}
    for u in units:
        for p in u.provides:
            by_usr.setdefault(p, u)
    out: list[_Unit] = []
    done: set[int] = set()
    active: set[int] = set()

    def visit(u: _Unit):
        if id(u) in done or id(u) in active:
            return
        active.add(id(u))
        for n in sorted(u.needs):
            dep = by_usr.get(n)
            if dep is not None and dep is not u:
                visit(dep)
        active.discard(id(u))
        done.add(id(u))
        out.append(u)

    for u in sorted(units, key=lambda x: x.order):
        visit(u)
    return out


def _strip_leading_static(body: str, name: str) -> str:
    """Each function now lives in its own .cpp, so a `static` function would be
    invisible to its callers in other files. Drop `static` before the name."""
    i = body.find(name)
    if i <= 0:
        return body
    head = re.sub(r"\bstatic\b\s*", "", body[:i], count=1)
    return head + body[i:]


def write_shared_header(cfg: Config, fwd: list[_Unit], types: list[_Unit],
                        globs: list[_Unit], protos: list[_Unit]) -> None:
    out = ['#pragma once'] + [f"#include {h}" for h in STD_INCLUDES] + \
          ['#include "ghidra_intrins.h"', '']
    uid = 0

    def emit(section: str, units: list[_Unit]):
        nonlocal uid
        out.append(f"// ==== {section} ====")
        for u in units:
            uid += 1
            out.append(f"//@unit {uid} {u.kind} {u.label}")
            out.extend(u.lines)
        out.append("")

    emit("forward declarations", fwd)
    emit("type definitions", types)
    emit("extern globals", globs)
    emit("function prototypes", protos)
    cfg.shared_h.write_text("\n".join(out) + "\n")


def split_monolith(cfg: Config, tu_dir: Optional[Path] = None) -> dict[str, FuncRecord]:
    """tu_dir: where to write the per-function files (default funcs/). Resume
    writes them to a scratch folder and then decides file by file what to keep."""
    global _RAW_BYTES
    cx = _load_libclang(cfg)
    raw = cfg.input_file.read_bytes()

    # prepend the intrinsics include so libclang resolves the ghidra types
    # (we parse a version that includes the header, but slice from the ORIGINAL
    #  raw bytes — so offsets must account for the prefix).
    prefix = ("".join(f"#include {h}\n" for h in STD_INCLUDES)
              + '#include "ghidra_intrins.h"\n').encode()

    # A missing #include "x.h" is a FATAL error, and after a fatal error clang
    # stops reporting every later error — so unknown types further down would
    # silently become `int`. Neutralize missing project includes by turning
    # `#include` into `//nclude` (same byte length, so all offsets stay valid).
    search_dirs = [cfg.input_file.parent, cfg.workdir] + [
        Path(f[2:]) for f in cfg.extra_flags if f.startswith("-I") and len(f) > 2]
    neutralized = []

    def _fix_inc(m: re.Match) -> bytes:
        inc = m.group(2).decode("utf-8", "replace")
        if any((d / inc).exists() for d in search_dirs):
            return m.group(0)
        neutralized.append(inc)
        return m.group(1) + b"//nclude" + m.group(0)[len(m.group(1)) + len(b"#include"):]

    def _fix_sys_inc(m: re.Match) -> bytes:
        # <windows.h> and other non-standard system headers (not on this machine)
        inc = m.group(2).decode("utf-8", "replace")
        if inc in STD_HEADERS:
            return m.group(0)
        neutralized.append(inc)
        return m.group(1) + b"//nclude" + m.group(0)[len(m.group(1)) + len(b"#include"):]

    parse_raw = re.sub(rb'(?m)^([ \t]*)#include[ \t]*"([^"\n]+)"', _fix_inc, raw)
    parse_raw = re.sub(rb'(?m)^([ \t]*)#include[ \t]*<([^>\n]+)>', _fix_sys_inc, parse_raw)
    assert len(parse_raw) == len(raw)
    if neutralized:
        log(cfg, f"  ignored {len(neutralized)} #include line(s) for files that don't "
                 f"exist (e.g. {', '.join(neutralized[:3])}) — they'd stop libclang "
                 f"from reporting any later errors")
    parse_bytes = prefix + parse_raw
    prefix_len = len(prefix)
    _RAW_BYTES = parse_bytes

    parse_path = str(cfg.workdir / "_parse_monolith.cpp")
    Path(parse_path).write_bytes(parse_bytes)

    args = _libclang_args(cfg)
    idx = cx.Index.create()
    stats = _SplitStats()

    # ---- Pass 1: declarations only (bodies skipped -> robust to broken funcs) ----
    opts1 = (cx.TranslationUnit.PARSE_INCOMPLETE
             | cx.TranslationUnit.PARSE_SKIP_FUNCTION_BODIES)
    tu1 = idx.parse(parse_path, args=args, options=opts1)
    err = _ErrIndex(tu1, parse_path)

    # Show what libclang itself couldn't understand — this is where silent
    # `int` substitutions come from.
    parse_errs = [d for d in tu1.diagnostics if d.severity >= 3]
    if parse_errs:
        lines = []
        for d in parse_errs:
            loc = d.location
            fname = Path(loc.file.name).name if loc.file else "?"
            lines.append(f"{fname}:{loc.line}: {d.spelling}")
        (cfg.workdir / "libclang_parse_errors.txt").write_text("\n".join(lines) + "\n")
        log(cfg, f"  libclang reported {len(parse_errs)} error(s) in the declarations "
                 f"(saved to libclang_parse_errors.txt), e.g.:")
        for ln in lines[:5]:
            log(cfg, f"    {ln[:180]}")
        # Only a missing SYSTEM header (#include <...>) means uint32_t etc. are
        # broken. A missing project header (#include "DAT_x.h") is just a stray
        # include in the monolith.
        src_lines = parse_bytes.decode("utf-8", "replace").splitlines()
        sys_missing = []
        for d in parse_errs:
            if "file not found" not in d.spelling:
                continue
            ln = d.location.line
            text = src_lines[ln - 1] if d.location.file and 0 < ln <= len(src_lines) else ""
            if "<" in text or d.location.file is None or d.location.file.name != parse_path:
                sys_missing.append(d.spelling)
        if sys_missing:
            log(cfg, "  !! libclang can't find a system header. Types like uint32_t "
                     "will be wrong. Point --libclang at Xcode's libclang.dylib or add "
                     "--flag=-isysroot --flag=\"$(xcrun --show-sdk-path)\"")

    fwd: list[_Unit] = []
    types: list[_Unit] = []
    globs: list[_Unit] = []
    protos: list[_Unit] = []
    seen_fwd: set[str] = set()
    seen_type: set[str] = set()
    seen_proto: set[str] = set()
    seen_global: set[str] = set()
    namespaces = 0
    order = 0
    def_counts: dict[tuple, int] = {}
    renames: dict[int, str] = {}   # parse offset of a definition -> new name

    for c in _top_level(tu1, parse_path):
        order += 1
        k = c.kind.name

        if k == "NAMESPACE":
            namespaces += 1
            continue

        if k in RECORD_KIND_NAMES:
            if _anon(c):
                continue  # emitted through its typedef / variable instead
            kw = "union" if k == "UNION_DECL" else "struct"
            if c.spelling not in seen_fwd:
                seen_fwd.add(c.spelling)
                fwd.append(_Unit("fwd", c.spelling, [f"{kw} {c.spelling};"], order))
            if not c.is_definition():
                continue
            key = "R:" + c.spelling
            if key in seen_type:
                stats.notes.append(f"duplicate struct {c.spelling}: kept first definition")
                continue
            seen_type.add(key)
            types.append(_record_unit(c, err, stats, order))

        elif k == "ENUM_DECL":
            if not c.is_definition():
                continue
            name = None if _anon(c) else c.spelling
            key = "E:" + (name or f"anon{order}")
            if key in seen_type:
                continue
            seen_type.add(key)
            u = _Unit("enum", name or "<anon enum>", [_enum_line(c, name)], order)
            try:
                u.provides.add(c.get_usr())
            except Exception:
                pass
            if name:
                try:
                    scoped = "enum class" if c.is_scoped_enum() else "enum"
                except Exception:
                    scoped = "enum"
                fwd.append(_Unit("fwd", name,
                                 [f"{scoped} {name} : {c.enum_type.spelling or 'int'};"], order))
            types.append(u)

        elif k in ("TYPEDEF_DECL", "TYPE_ALIAS_DECL"):
            name = c.spelling
            key = "T:" + name
            if key in seen_type:
                continue
            if err.within(c):
                stats.skip("typedef", name, "libclang could not resolve its type")
                continue
            under = c.underlying_typedef_type
            target = under
            while target.kind.name == "ELABORATED":
                target = target.get_named_type()
            tdecl = target.get_declaration()
            if (tdecl.kind.name in RECORD_KIND_NAMES and _anon(tdecl)
                    and tdecl.is_definition()):
                # typedef struct { ... } Name;  (older libclang leaves it unnamed)
                seen_type.add(key)
                u = _record_unit(tdecl, err, stats, order, typedef_name=name)
                try:
                    u.provides.add(c.get_usr())
                except Exception:
                    pass
                types.append(u)
                continue
            d = _declarator(under, name)
            if _is_anon_text(d):
                stats.skip("typedef", name, "refers to an anonymous type")
                continue
            seen_type.add(key)
            u = _Unit("typedef", name, [f"typedef {d};"], order)
            try:
                u.provides.add(c.get_usr())
            except Exception:
                pass
            _needs(under, False, u.needs)
            types.append(u)

        elif k == "FUNCTION_DECL":
            # pass 1 skips bodies, so libclang's is_definition() is always False
            # here; a definition is a declaration whose text ends in its body.
            is_def = (c.is_definition()
                      or _RAW_BYTES[c.extent.end.offset:c.extent.end.offset + 400]
                      .lstrip()[:1] in (b"{", b":"))
            if err.within(c, ignore=_DUP_DEF_ERR if is_def else None):
                stats.skip("prototype", c.spelling,
                           "its signature uses a type libclang could not resolve")
                continue
            fname_out = c.spelling
            if is_def:
                # The rewrite reused names (theFunctionName x30...). Two
                # definitions with the same name AND same parameters can't both
                # exist in C++ ("differ only in return type" / duplicate symbol),
                # so later copies get a unique name. Different parameter lists
                # are legal overloads and are left alone.
                try:
                    params = tuple(a.spelling for a in c.type.argument_types())
                except Exception:
                    params = ()
                dkey = (c.spelling, params)
                n = def_counts.get(dkey, 0)
                def_counts[dkey] = n + 1
                if n:
                    fname_out = f"{c.spelling}__dup{n}"
                    renames[c.extent.start.offset] = fname_out
                    stats.notes.append(f"renamed duplicate definition {c.spelling}"
                                       f"({', '.join(params)}) -> {fname_out}")
            proto = _declarator(c.type, fname_out) + ";"
            try:
                if c.lexical_parent is not None and c.lexical_parent.kind.name == "LINKAGE_SPEC":
                    proto = 'extern "C" ' + proto
            except Exception:
                pass
            if _is_anon_text(proto):
                stats.skip("prototype", c.spelling, "uses an anonymous type")
                continue
            pkey = re.sub(r"\s+", " ", proto)
            if pkey in seen_proto:
                continue
            seen_proto.add(pkey)
            protos.append(_Unit("proto", fname_out, [proto], order))

        elif k == "CXX_METHOD":
            # out-of-line `Foo::bar` definitions: declared inside struct Foo already
            continue

        elif k == "VAR_DECL":
            gname = c.spelling
            if not gname:
                continue
            if err.within(c):
                stats.skip("global", gname, "its type could not be resolved")
                continue
            decl = "extern " + _declarator(c.type, gname) + ";"
            if _is_anon_text(decl):
                stats.skip("global", gname, "has an anonymous type")
                continue
            gkey = re.sub(r"\s+", " ", decl)
            if gkey in seen_global:
                continue
            seen_global.add(gkey)
            globs.append(_Unit("global", gname, [decl], order))

    types = _order_units(types)
    write_shared_header(cfg, fwd, types, globs, protos)

    # ---- Pass 2: with bodies, to get exact function spans ----
    opts2 = cx.TranslationUnit.PARSE_INCOMPLETE
    tu2 = idx.parse(parse_path, args=args, options=opts2)

    records: dict[str, FuncRecord] = {}
    spans: list[tuple[int, int, str, str]] = []  # (start,end,name,mangled) in raw coords
    name_counts: dict[str, int] = {}

    for c in _top_level(tu2, parse_path):
        if c.kind.name not in ("FUNCTION_DECL", "CXX_METHOD") or not c.is_definition():
            continue
        s = c.extent.start.offset - prefix_len
        e = c.extent.end.offset - prefix_len
        if s < 0 or e <= s or e > len(raw):
            continue  # defensive: parse artifact, skip
        name = c.spelling or f"anon_{s}"
        mangled = c.mangled_name or name
        new = renames.get(c.extent.start.offset)
        if new:
            mangled = f"{mangled}__{new[len(name):].lstrip('_')}"
            name = new
        # disambiguate colliding mangled names (duplicate statics, etc.)
        if mangled in name_counts:
            name_counts[mangled] += 1
            mangled = f"{mangled}__{name_counts[mangled]}"
        else:
            name_counts[mangled] = 0
        spans.append((s, e, name, mangled))

    # ---- Reconciliation guard: spans must be sane & non-overlapping ----
    spans.sort(key=lambda t: t[0])
    clean_spans: list[tuple[int, int, str, str]] = []
    last_end = -1
    overlaps = 0
    for (s, e, name, mangled) in spans:
        if s < last_end:
            overlaps += 1
            log(cfg, f"  ! overlap: {name} ({s}:{e}) starts before previous end {last_end} — quarantining span")
            continue
        clean_spans.append((s, e, name, mangled))
        last_end = e

    if overlaps:
        log(cfg, f"  reconciliation: {overlaps} overlapping span(s) dropped to manual bucket")

    # ---- Emit per-function TUs ----
    tu_dir = tu_dir or cfg.funcs_dir
    tu_dir.mkdir(parents=True, exist_ok=True)
    include_line = '#include "shared.h"\n\n'
    # positions of every //@ghidra <addr> marker, to tag each function with the
    # address its pseudocode lives under (written by the rewrite stage)
    markers = [(m.start(), m.group(1)) for m in
               re.finditer(rb"//@ghidra\s+([0-9a-fA-F]+)\b", raw)]
    marker_offs = [p for p, _ in markers]
    import bisect
    prev_end = 0
    for (s, e, name, mangled) in clean_spans:
        body = raw[s:e].decode("utf-8", "replace")
        m_dup = re.match(r"^(.*)__dup\d+$", name)
        if m_dup:   # rename the definition itself to match its new prototype
            body = re.sub(rf"\b{re.escape(m_dup.group(1))}\b(?=\s*\()", name, body, count=1)
        body = _strip_leading_static(body, name)
        safe = re.sub(r"[^A-Za-z0-9_]", "_", mangled)[:120]
        fname = f"{safe}.cpp"
        (tu_dir / fname).write_text(include_line + body + "\n")
        i = bisect.bisect_left(marker_offs, s) - 1   # nearest marker before this func
        # only this function's own marker counts: it must sit between the previous
        # function and this one, not be a leftover from an unmarked gap
        addr = markers[i][1].decode() if i >= 0 and marker_offs[i] >= prev_end else ""
        prev_end = e
        records[mangled] = FuncRecord(
            name=name, mangled=mangled, file=f"funcs/{fname}",
            start=s, end=e, ghidra_addr=addr,
            src_sha=hashlib.sha1(raw[s:e]).hexdigest()[:16],
        )

    # ---- globals.cpp (file-scope definitions) ----
    glob_lines = [include_line, "// ==== global definitions ===="]
    gnames = seen_global_names(globs)
    gid = 0
    for c in _top_level(tu2, parse_path):
        if c.kind.name == "VAR_DECL" and c.is_definition() and c.spelling in gnames:
            s = c.extent.start.offset - prefix_len
            e = c.extent.end.offset - prefix_len
            if 0 <= s < e <= len(raw):
                text = raw[s:e].decode("utf-8", "replace").rstrip()
                text = _strip_leading_static(text, c.spelling)
                if not text.endswith(";"):
                    text += ";"
                gid += 1
                glob_lines.append(f"//@unit {gid} global {c.spelling}")
                glob_lines.append(text)
    cfg.globals_cpp.write_text("\n".join(glob_lines) + "\n")

    # ---- did we find every function? (each one in the rewrite has a //@ghidra marker)
    lost_note = []
    if len(markers) > 20 and len(records) < 0.9 * len(markers):
        last = max((e for _, e, _, _ in clean_spans), default=0)
        after = [p for p in marker_offs if p > last]
        first_lost = after[0] if after else None
        text = raw.decode("utf-8", "replace")
        line_no = text.count("\n", 0, first_lost) + 1 if first_lost is not None else 0
        log(cfg, f"  !! the split found {len(records)} functions, but the rewrite has "
                 f"{len(markers)}. libclang loses track of the file around line {line_no} "
                 f"of {cfg.input_file.name}: everything after that is missing from the build. "
                 f"The code just before it is in split_report.txt.")
        if first_lost is not None:
            start = text.rfind("\n", 0, max(0, text.rfind("//@ghidra", 0, first_lost) - 1))
            lost_note = ["", f"== where the split lost track (line {line_no}) — the code before it:",
                         text[max(0, start - 3000):first_lost]]

    # ---- report ----
    rep = [f"unresolved struct fields (unknown type, left as comments): {stats.unresolved_fields}"]
    for kind, n in sorted(stats.skipped.items()):
        rep.append(f"skipped {kind}s: {n}")
    rep.append("")
    rep += stats.notes
    rep += lost_note
    (cfg.workdir / "split_report.txt").write_text("\n".join(rep) + "\n")

    n_types = sum(1 for u in types)
    log(cfg, f"  split -> {len(records)} function TUs, {n_types} types "
             f"(+{len(fwd)} forward decls), {len(protos)} prototypes, {len(globs)} globals")
    if stats.unresolved_fields or stats.skipped:
        sk = ", ".join(f"{n} {k}s" for k, n in sorted(stats.skipped.items())) or "nothing"
        log(cfg, f"  {stats.unresolved_fields} struct field(s) with unknown types left as "
                 f"comments; skipped {sk} — details in split_report.txt")
    if renames:
        log(cfg, f"  renamed {len(renames)} duplicate function definition(s) to unique "
                 f"names (e.g. theFunctionName__dup1) — listed in split_report.txt")
    if namespaces:
        log(cfg, f"  note: {namespaces} top-level namespace block(s) were not split "
                 f"(functions inside namespaces are not handled yet)")
    return records


def seen_global_names(globs: list[_Unit]) -> set[str]:
    return {u.label for u in globs}

# ----------------------------------------------------------------------------
# Stage 2 — Per-TU de-ghidra text cleanup (safe transforms)
# ----------------------------------------------------------------------------

DEGHIDRA_SUBS: list[tuple[str, str]] = [
    # calling-convention junk
    (r"\b__fastcall\b", ""),
    (r"\b__cdecl\b", ""),
    (r"\b__thiscall\b", ""),
    (r"\b__stdcall\b", ""),
    # SUBxy(v,0) -> cast to the low width (the common, safe case)
    (r"\bSUB84\s*\(([^,]+),\s*0\s*\)", r"(uint32_t)(\1)"),
    (r"\bSUB84\s*\(([^,]+),\s*4\s*\)", r"(uint32_t)((\1)>>32)"),
    (r"\bSUB164\s*\(([^,]+),\s*0\s*\)", r"(uint32_t)(\1)"),
    (r"\bSUB41\s*\(([^,]+),\s*0\s*\)", r"(uint8_t)(\1)"),
    (r"\bSUB42\s*\(([^,]+),\s*0\s*\)", r"(uint16_t)(\1)"),
    (r"\bSUB21\s*\(([^,]+),\s*0\s*\)", r"(uint8_t)(\1)"),
]

# phantom register/unaffected variables Ghidra emits with no real definition
PHANTOM_VAR_RE = re.compile(r"\b((?:unaff_|in_|extraout_|unique0x)[A-Za-z0-9_]+)\b")


def deghidra_text(src: str) -> str:
    out = src
    for pat, repl in DEGHIDRA_SUBS:
        out = re.sub(pat, repl, out)
    # declare phantom vars locally as 0-initialized so the TU at least compiles;
    # these get flagged for review (they indicate incomplete lifting).
    phantoms = sorted(set(PHANTOM_VAR_RE.findall(out)))
    if phantoms:
        decls = "".join(f"    uint64_t {p} = 0; // TODO: phantom var (incomplete lift)\n"
                        for p in phantoms)
        # insert after the first '{' of the function body
        idx = out.find("{")
        if idx != -1:
            out = out[:idx+1] + "\n" + decls + out[idx+1:]
    return out


def apply_deghidra_pass(cfg: Config, records: dict[str, FuncRecord]) -> None:
    changed = 0
    for rec in records.values():
        p = cfg.workdir / rec.file
        src = p.read_text()
        new = deghidra_text(src)
        if new != src:
            p.write_text(new)
            changed += 1
    log(cfg, f"  de-ghidra text pass touched {changed} TU(s)")


# ----------------------------------------------------------------------------
# Stage 3 — Isolated compile sweep + diagnostics
# ----------------------------------------------------------------------------

# Position-independent code: default on macOS; on Linux it has to be passed,
# and the PCH is only accepted when every compile uses the same setting.
PIC_FLAGS: list[str] = [] if sys.platform == "darwin" else ["-fPIC"]


def _pch_path(cfg: Config) -> Path:
    return cfg.workdir / "shared.h.pch"


def build_pch(cfg: Config) -> bool:
    """Precompile shared.h once. With the standard-library includes, parsing the
    header is ~85% of each function's compile time; the PCH skips that."""
    cmd = [cfg.cxx, f"-std={cfg.std}", f"-I{cfg.workdir}", "-w", *PIC_FLAGS,
           "-x", "c++-header", *cfg.extra_flags, str(cfg.shared_h),
           "-o", str(_pch_path(cfg))]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        _pch_path(cfg).unlink(missing_ok=True)
        log(cfg, "  (precompiled header failed to build — compiling without it, slower)")
        return False
    return True


class RWLock:
    """Many readers or one writer. Compiles read shared.h (and its precompiled
    header) at the same time; a header repair waits for them and has it alone.
    A thread holding the write lock may also read."""

    def __init__(self):
        self._cv = threading.Condition()
        self._readers = 0
        self._writer = None
        self._depth = 0
        self._waiting = 0

    @contextlib.contextmanager
    def read(self):
        me = threading.get_ident()
        with self._cv:
            mine = self._writer == me
            if not mine:
                while self._writer is not None or self._waiting:
                    self._cv.wait()
                self._readers += 1
        try:
            yield
        finally:
            if not mine:
                with self._cv:
                    self._readers -= 1
                    self._cv.notify_all()

    @contextlib.contextmanager
    def write(self):
        me = threading.get_ident()
        with self._cv:
            if self._writer == me:
                self._depth += 1
            else:
                self._waiting += 1
                while self._writer is not None or self._readers:
                    self._cv.wait()
                self._waiting -= 1
                self._writer, self._depth = me, 1
        try:
            yield
        finally:
            with self._cv:
                self._depth -= 1
                if not self._depth:
                    self._writer = None
                    self._cv.notify_all()


HEADER_LOCK = RWLock()


def _pch_flags(cfg: Config, rebuild=True) -> list[str]:
    """Use the PCH only if it's at least as new as shared.h (the header can be
    repaired mid-run); rebuild it once if it's stale (rebuild=False: just say
    whether it can be used)."""
    pch = _pch_path(cfg)

    def fresh():
        return pch.exists() and pch.stat().st_mtime >= cfg.shared_h.stat().st_mtime
    try:
        if not fresh():
            if not rebuild:
                return []
            with HEADER_LOCK.write():
                if not fresh() and not build_pch(cfg):
                    return []
        return ["-include-pch", str(pch)]
    except OSError:
        return []


def compile_tu(cfg: Config, rel_path: str) -> tuple[bool, str, list[dict]]:
    """Compile one TU with -fsyntax-only. Returns (ok, raw_stderr, diags).
    (The old version passed -fdiagnostics-format=json, which is a GCC-only flag:
    clang rejects it, so EVERY function was reported as failing.)"""
    src = cfg.workdir / rel_path
    if STOPPING.is_set():
        raise StopRun
    _pch_flags(cfg)                       # brings the PCH up to date first, if needed
    with HEADER_LOCK.read():
        cmd = [cfg.cxx, f"-std={cfg.std}", f"-I{cfg.workdir}",
               "-fsyntax-only", "-w", "-ferror-limit=20", *PIC_FLAGS,
               *_pch_flags(cfg, rebuild=False), *cfg.extra_flags, str(src)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
    if STOPPING.is_set():
        raise StopRun                     # the compiler was probably killed by the stop
    return proc.returncode == 0, proc.stderr, []


def _compile_header_human(cfg: Config, header_rel: str) -> tuple[bool, str]:
    """Compile a header alone with human-format diagnostics (regex-parseable)."""
    src = cfg.workdir / header_rel
    # -ferror-limit=0: report every error in one pass. -w: errors only.
    lang = ["-x", "c++-header"] if header_rel.endswith(".h") else [*_pch_flags(cfg)]
    cmd = [cfg.cxx, f"-std={cfg.std}", f"-I{cfg.workdir}",
           "-fsyntax-only", "-ferror-limit=0", "-w", *PIC_FLAGS, *lang,
           *cfg.extra_flags, str(src)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode == 0, proc.stderr


DIAG_RE = re.compile(r"^(?P<file>.+?):(?P<line>\d+):(?P<col>\d+):\s*"
                     r"(?P<sev>fatal error|error|warning|note):\s*(?P<msg>.*)$")
UNIT_RE = re.compile(r"^//@unit (\d+) (\w+) ?(.*)$")


def _parse_units(lines: list[str]) -> list[dict]:
    """Find the //@unit blocks in shared.h. Each unit's content runs from the
    line after its marker up to the next marker / section line."""
    units = []
    i, n = 0, len(lines)
    while i < n:
        m = UNIT_RE.match(lines[i])
        if not m:
            i += 1
            continue
        j = i + 1
        while j < n and not UNIT_RE.match(lines[j]) and not lines[j].startswith("// ===="):
            j += 1
        end = j
        while end > i + 1 and not lines[end - 1].strip():
            end -= 1
        units.append({"uid": m.group(1), "kind": m.group(2), "label": m.group(3),
                      "start": i, "end": end})   # content = lines[start+1:end]
        i = j
    return units


def _unit_at(units: list[dict], idx: int) -> Optional[dict]:
    lo, hi = 0, len(units) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        u = units[mid]
        if idx < u["start"]:
            hi = mid - 1
        elif idx >= u["end"]:
            lo = mid + 1
        else:
            return u if idx > u["start"] else None
    return None


def repair_header(cfg: Config, header_rel: str, max_iter: int = 60) -> bool:
    with HEADER_LOCK.write():                 # no compile reads it halfway through
        return _repair_header(cfg, header_rel, max_iter)


def _repair_header(cfg: Config, header_rel: str, max_iter: int = 60) -> bool:
    """Make shared.h compile by switching off broken DECLARATIONS, never by
    commenting out arbitrary lines.

      - error on a single field line inside a struct  -> drop just that field
      - any other error inside a declaration          -> wrap the whole
                                                          declaration in #if 0
      - "to match this '{'" pointing into a decl       -> whole declaration

    Disabled structs stay usable through pointers because every struct also
    has a `struct X;` in the forward-declaration block. Everything removed is
    listed in header_repair_report.txt. Returns True once the header compiles."""
    hpath = cfg.workdir / header_rel
    hname = Path(header_rel).name
    report_path = cfg.workdir / ("header_repair_report.txt" if hname.endswith(".h")
                                 else f"{Path(hname).stem}_repair_report.txt")
    report: list[str] = []
    dropped_fields = 0
    disabled_units = 0
    last_err = ""

    for _ in range(max_iter):
        ok, err = _compile_header_human(cfg, header_rel)
        last_err = err
        if ok:
            if report:
                report_path.write_text("\n".join(report) + "\n")
                log(cfg, f"  {hname}: repaired — disabled {disabled_units} "
                         f"declaration(s), dropped {dropped_fields} struct field(s) "
                         f"(list in {report_path.name})")
            return True

        lines = hpath.read_text().splitlines()
        units = _parse_units(lines)
        field_drops: dict[int, str] = {}
        unit_disables: dict[str, tuple[dict, str]] = {}
        foreign: list[str] = []

        for raw_ln in err.splitlines():
            m = DIAG_RE.match(raw_ln.strip())
            if not m:
                continue
            sev, msg = m.group("sev"), m.group("msg")
            is_brace_note = sev == "note" and "to match this" in msg
            if "error" not in sev and not is_brace_note:
                continue
            if Path(m.group("file")).name != hname:
                if "error" in sev:
                    foreign.append(raw_ln.strip())
                continue
            idx = int(m.group("line")) - 1
            u = _unit_at(units, idx)
            if u is None:
                if "error" in sev:
                    foreign.append(raw_ln.strip())
                continue
            first, last = u["start"] + 1, u["end"] - 1
            interior = (u["kind"] == "record" and first < idx < last
                        and not is_brace_note
                        and not lines[idx].lstrip().startswith(("//", "/*", "#")))
            if interior:
                field_drops.setdefault(idx, msg)
            else:
                unit_disables.setdefault(u["uid"], (u, msg))

        if not field_drops and not unit_disables:
            break   # nothing we can attribute to a declaration -> can't repair

        for idx, msg in field_drops.items():
            u = _unit_at(units, idx)
            if u and u["uid"] in unit_disables:
                continue
            report.append(f"dropped field in {u['label'] if u else '?'}: "
                          f"{lines[idx].strip()}   <- {msg}")
            lines[idx] = f"    // [dropped: {msg[:80]}] {lines[idx].strip()}"
            dropped_fields += 1

        for u, msg in sorted(unit_disables.values(), key=lambda t: -t[0]["start"]):
            s, e = u["start"], u["end"]
            if s + 1 < len(lines) and lines[s + 1].startswith("#if 0"):
                continue
            report.append(f"disabled {u['kind']} {u['label']}   <- {msg}")
            lines.insert(e, "#endif")
            lines.insert(s + 1, f"#if 0 // [disabled: {msg[:100]}]")
            disabled_units += 1

        hpath.write_text("\n".join(lines) + "\n")

    if report:
        report_path.write_text("\n".join(report) + "\n")
    (cfg.workdir / "header_errors.txt").write_text(last_err)
    log(cfg, f"  header {hname}: could not be made to compile.")
    shown = 0
    for ln in last_err.splitlines():
        if "error" in ln:
            log(cfg, f"    | {ln[:200]}")
            shown += 1
            if shown >= 8:
                break
    log(cfg, f"  (full compiler output saved to header_errors.txt)")
    return False


def validate_headers(cfg: Config) -> bool:
    """Gate: both generated headers must compile before the per-TU sweep, or
    every function fails identically."""
    ok_intr, err = _compile_header_human(cfg, "ghidra_intrins.h")
    if not ok_intr:
        (cfg.workdir / "header_errors.txt").write_text(err)
        log(cfg, "  ghidra_intrins.h itself does not compile — this is the script's "
                 "own header, so it's a toolchain/flag problem. First lines:")
        for ln in err.strip().splitlines()[:6]:
            log(cfg, f"    | {ln[:200]}")
        return False
    if not repair_header(cfg, "shared.h"):
        return False
    with HEADER_LOCK.write():
        build_pch(cfg)
    # globals.cpp: definitions whose extern was disabled, duplicates, unknown
    # types... switch those off too so the final link isn't blocked by them.
    if not repair_header(cfg, "globals.cpp"):
        log(cfg, "  (globals.cpp still has errors — the link step will report them)")
    return True


def header_implicated(stderr: str) -> bool:
    """True if a TU's failure originates in a shared header rather than its own
    body — including an unclosed '{' in the header that clang only notices at
    the end of the function file."""
    return bool(re.search(
        r"(shared\.h|ghidra_intrins\.h):\d+:\d+:\s*(?:(?:fatal\s+)?error|note: to match this)",
        stderr))


def preflight_diagnose(cfg: Config, records: dict[str, FuncRecord]) -> bool:
    """Compile the first handful of TUs with full (human) diagnostics. If they
    ALL fail, the cause is systemic (shared header / missing include / bad flag),
    and rewriting 5063 bodies would be hours of wasted work that can't fix it.
    Surface the real error loudly and save it so it's not guesswork.
    Returns True if the failure looks systemic."""
    sample = list(records.values())[:20]
    if not sample:
        return False
    first_fail_err = None
    n_fail = 0
    for rec in sample:
        src = cfg.workdir / rec.file
        # -w so the sample shows ERRORS, not the wall of harmless warnings
        cmd = [cfg.cxx, f"-std={cfg.std}", f"-I{cfg.workdir}",
               "-fsyntax-only", "-w", "-ferror-limit=5", *PIC_FLAGS, *_pch_flags(cfg),
               *cfg.extra_flags, str(src)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            n_fail += 1
            if first_fail_err is None:
                first_fail_err = (rec, proc.stderr)
    if n_fail == len(sample) and first_fail_err:
        rec, err = first_fail_err
        (cfg.workdir / "first_error.txt").write_text(err)
        log(cfg, "  " + "!"*58)
        log(cfg, f"  SYSTEMIC FAILURE: all {len(sample)} sampled TUs fail.")
        log(cfg, "  This is a shared cause (header / include / flag), NOT per-function.")
        log(cfg, "  The fixer loop canNOT fix this by rewriting bodies. Real error below:")
        log(cfg, "  " + "-"*58)
        for ln in err.strip().splitlines()[:18]:
            log(cfg, "  | " + ln[:200])
        log(cfg, "  " + "-"*58)
        log(cfg, f"  (full text saved to {cfg.workdir/'first_error.txt'})")
        log(cfg, "  " + "!"*58)
        return True
    elif n_fail:
        log(cfg, f"  preflight: {n_fail}/{len(sample)} sampled TUs fail — looks "
                 f"per-function, proceeding to full sweep + fixer")
    else:
        log(cfg, "  preflight: sampled TUs compile — proceeding")
    return False


def compile_sweep(cfg: Config, records: dict[str, FuncRecord]) -> None:
    from concurrent.futures import ThreadPoolExecutor
    ok_n = 0
    total = len(records)
    t0 = time.time()
    _pch_flags(cfg)   # build the PCH once before the workers start
    workers = max(1, (os.cpu_count() or 2) - 1)
    log(cfg, f"  compiling with {workers} parallel worker(s)")
    recs = list(records.values())
    prog = Progress(total, 0, title="compiling each function on its own")
    prog.extra = lambda: f"{ok_n} pass"
    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = pool.map(lambda r: compile_tu(cfg, r.file), recs)
            paired = zip(recs, results)
            for i, (rec, (ok, err, _)) in enumerate(paired, 1):
                _sweep_record(rec, ok, err)
                if ok:
                    ok_n += 1
                prog.end(rec.mangled)
    finally:
        prog.close()
    log(cfg, f"  isolated compile: {ok_n}/{len(records)} TUs pass, "
             f"{len(records)-ok_n} need repair ({time.time() - t0:.0f}s)")


def _sweep_record(rec: FuncRecord, ok: bool, err: str) -> None:
    rec.compiles = ok
    if not ok:
        rec.last_error = err[-4000:]


# ----------------------------------------------------------------------------
# Dependency ordering
# ----------------------------------------------------------------------------

def import_callgraph(cfg: Config) -> Optional[dict[str, list[str]]]:
    """Load a Ghidra-exported call graph as {caller_name: [callee_names]}.

    Accepts three formats, chosen by extension / sniffed content:
      .json     -> {"caller": ["callee", ...], ...}
      .csv/.tsv -> edge list, one 'caller,callee' (or caller<TAB>callee) per line
      .graphml  -> Ghidra graph export; node id->label map + <edge source target>
    Names are function spellings as they appear in Ghidra (e.g. FUN_00401abc),
    which match the 'name' we stored per record.
    """
    p = cfg.callgraph_path
    if not p or not p.exists():
        return None
    text = p.read_text()
    ext = p.suffix.lower()
    graph: dict[str, list[str]] = {}

    try:
        if ext == ".json" or text.lstrip().startswith("{"):
            data = json.loads(text)
            for caller, callees in data.items():
                graph.setdefault(caller, [])
                for c in (callees or []):
                    if c and c != caller:
                        graph[caller].append(c)

        elif ext in (".csv", ".tsv") or ("," in text and "<" not in text[:200]):
            sep = "\t" if ext == ".tsv" else ","
            for line in text.splitlines():
                line = line.strip()
                if not line or line.lower().startswith(("caller", "source", "#")):
                    continue
                parts = [x.strip() for x in line.split(sep)]
                if len(parts) >= 2 and parts[0] and parts[1]:
                    caller, callee = parts[0], parts[1]
                    if callee != caller:
                        graph.setdefault(caller, []).append(callee)

        elif ext == ".graphml" or "<graphml" in text[:500].lower():
            # Minimal GraphML parse: node id -> label, then edges by id.
            import xml.etree.ElementTree as ET
            root = ET.fromstring(text)
            ns = {"g": "http://graphml.graphdrawing.org/xmlns"}
            # Map any node id to a human label if a <data> holds one, else the id.
            id_to_name: dict[str, str] = {}
            for node in root.iter():
                if node.tag.endswith("node"):
                    nid = node.get("id", "")
                    label = nid
                    for d in node:
                        if d.tag.endswith("data") and (d.text or "").strip():
                            label = d.text.strip()
                            break
                    id_to_name[nid] = label
            for edge in root.iter():
                if edge.tag.endswith("edge"):
                    s = id_to_name.get(edge.get("source", ""), edge.get("source", ""))
                    t = id_to_name.get(edge.get("target", ""), edge.get("target", ""))
                    if s and t and s != t:
                        graph.setdefault(s, []).append(t)
        else:
            log(cfg, f"  callgraph: unrecognized format for {p.name}, ignoring")
            return None
    except Exception as e:
        log(cfg, f"  callgraph: failed to parse {p.name} ({e}); falling back to heuristic")
        return None

    # de-dup callee lists
    for k in graph:
        graph[k] = sorted(set(graph[k]))
    edges = sum(len(v) for v in graph.values())
    log(cfg, f"  callgraph imported: {len(graph)} callers, {edges} edges from {p.name}")
    return graph


def build_dep_order(cfg: Config, records: dict[str, FuncRecord]) -> list[str]:
    """Dependency order, leaves first. Uses an imported Ghidra call graph when
    available (exact), otherwise a regex heuristic over source text.
    Returns mangled names leaves-first. Cycles are broken arbitrarily."""
    name_to_mangled: dict[str, str] = {}
    for m, r in records.items():
        name_to_mangled.setdefault(r.name, m)

    imported = import_callgraph(cfg)

    if imported is not None:
        matched = 0
        unmatched_names: set[str] = set()
        for m, r in records.items():
            callees = imported.get(r.name)
            if callees is None:
                # no entry for this function in the export -> fall back to regex
                # for just this function so ordering still has signal.
                src = (cfg.workdir / r.file).read_text()
                calls = set(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", src))
                r.deps = [name_to_mangled[c] for c in calls
                          if c in name_to_mangled and name_to_mangled[c] != m]
                continue
            deps = []
            for c in callees:
                cm = name_to_mangled.get(c)
                if cm and cm != m:
                    deps.append(cm)
                elif c not in name_to_mangled:
                    unmatched_names.add(c)
            r.deps = deps
            matched += 1
        if unmatched_names:
            log(cfg, f"  callgraph: {len(unmatched_names)} callee name(s) not in our "
                     f"TU set (external/library calls) — ignored for ordering")
        log(cfg, f"  callgraph: exact deps for {matched}/{len(records)} functions")
    else:
        for m, r in records.items():
            src = (cfg.workdir / r.file).read_text()
            calls = set(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", src))
            r.deps = [name_to_mangled[c] for c in calls
                      if c in name_to_mangled and name_to_mangled[c] != m]

    # topological sort (leaves first), tolerant of cycles
    visited: set[str] = set()
    order: list[str] = []
    temp: set[str] = set()

    def visit(m: str):
        if m in visited or m in temp:
            return
        temp.add(m)
        for d in records[m].deps:
            if d in records:
                visit(d)
        temp.discard(m)
        visited.add(m)
        order.append(m)

    for m in records:
        visit(m)
    return order


# ----------------------------------------------------------------------------
# Context slicing for the model
# ----------------------------------------------------------------------------

ERR_SYMBOL_RE = re.compile(r"'([A-Za-z_][A-Za-z0-9_:<>~ ]*)'")

def extract_error_symbols(stderr: str) -> list[str]:
    syms = []
    for m in ERR_SYMBOL_RE.findall(stderr):
        s = m.strip()
        if s and s not in syms:
            syms.append(s)
    return syms[:20]


def gather_declarations(cfg: Config, symbols: list[str], limit=4000) -> str:
    """What shared.h says about the names an error mentions: the WHOLE definition of
    a struct / enum / typedef (so the model can see which fields really exist), the
    prototype of a function, the extern of a global — or that it was switched off
    by the header repair, or isn't declared anywhere."""
    lines = cfg.shared_h.read_text().splitlines()
    units = _parse_units(lines)
    by_label: dict[str, list[dict]] = {}
    for u in units:
        by_label.setdefault(u["label"], []).append(u)
    out: list[str] = []
    seen: set[str] = set()
    for sym in symbols:
        for part in re.split(r"::|[<>,\s*&]+", sym):
            base = part.strip()
            if not base or base in seen or base in CPP_KEYWORDS:
                continue
            seen.add(base)
            us = [u for u in by_label.get(base, []) if u["kind"] != "fwd"]
            if us:
                for u in us:
                    body = lines[u["start"] + 1:u["end"]]
                    if body and body[0].startswith("#if 0"):
                        why = body[0].split("[", 1)[-1].rstrip("]")
                        out.append(f"// {base}: switched off in shared.h (it didn't compile: "
                                   f"{why[:120]}) — it can't be used")
                    else:
                        out.append("\n".join(body))
            elif any(re.search(rf"\b{re.escape(base)}\b", l) for l in lines
                     if l.strip().endswith(";")):
                out += [l.strip() for l in lines if re.search(rf"\b{re.escape(base)}\b", l)
                        and l.strip().endswith(";")][:3]
            elif re.match(r"^[A-Z_a-z]\w*$", base) and len(base) > 2:
                out.append(f"// {base}: not declared anywhere in the program")
    text = "\n".join(dict.fromkeys(out))       # no repeats, order kept
    return text[:limit].rsplit("\n", 1)[0] if len(text) > limit else text


# ----------------------------------------------------------------------------
# Deterministic / templated repair (no model)
# ----------------------------------------------------------------------------

def templated_fix(cfg: Config, rel_path: str, stderr: str) -> bool:
    """Apply mechanical fixes for common diagnostics. Returns True if it changed."""
    src_path = cfg.workdir / rel_path
    src = src_path.read_text()
    orig = src

    # implicit function declaration -> the prototype is in shared.h already;
    # usually means a spelling/namespace issue. Skip (model handles).
    # missing ';' before '}' style — clang usually recovers; skip.

    # "use of undeclared identifier 'X'": a Ghidra local (uVar1, local_28,
    # unaff_x...) the rewrite used but never declared -> declare it at the top
    # of the function. Names used as calls are functions, not variables, and
    # are left for the model. (The old check skipped any variable that was
    # assigned somewhere, i.e. most of them.)
    body_open = src.find("{")
    for m in sorted(set(re.findall(
            r"use of undeclared identifier '([A-Za-z_][A-Za-z0-9_]*)'", stderr))):
        if re.search(rf"\b{re.escape(m)}\s*\(", src):
            continue
        if body_open != -1 and not re.search(rf"\b(uint64_t|auto)\s+{re.escape(m)}\b", src):
            decl = f"\n    uint64_t {m} = 0; // auto-declared (undeclared in the rewrite)\n"
            src = src[:body_open + 1] + decl + src[body_open + 1:]

    if src != orig:
        src_path.write_text(src)
        return True
    return False


# ----------------------------------------------------------------------------
# LM Studio slice repair
# ----------------------------------------------------------------------------

MODEL_STATS = {"calls": 0, "no_answer": 0, "rejected": 0}   # the fix stage's small edits


def model_check(cfg: Config) -> bool:
    """Is the model server up, and which model does this stage use? Checked at the
    start of each stage, so a model swapped in between stages is picked up.
    Without this, a stopped server made every model call fail silently and the
    fixer quarantined thousands of functions."""
    if cfg.client is None:
        return False
    try:
        cfg.fix_model_used = cfg.client.resolve(cfg.wanted_model)
    except ModelError as e:
        log(cfg, f"  {e}")
        return False
    log(cfg, f"  {cfg.client.name} OK — using the loaded model {cfg.fix_model_used}")
    return True


def _fix_chat(cfg: Config, system: str, user: str, max_tokens: int) -> Optional[str]:
    """One fix/recover request. None when there's no usable answer (the caller
    then moves on: quarantine, or the next strategy)."""
    if cfg.fix_model_used is None and not model_check(cfg):
        cfg.fix_model_used = ""            # don't ask again for every function
    if not cfg.fix_model_used:
        return None
    return cfg.client.chat(cfg.fix_model_used,
                           [{"role": "system", "content": system},
                            {"role": "user", "content": user}],
                           max_out=max(max_tokens, answer_room(cfg.ctx, len(system) + len(user))),
                           temperature=cfg.model_temperature,
                           timeout=cfg.model_timeout_s, fatal=False)


def _accept_model_fix(name: str, original: str, fixed: str) -> Optional[str]:
    """Reject 'fixes' that make the compile error go away by deleting the
    problem: dropping/renaming the function or gutting most of its body. For
    vulnerability work a function that compiles but lost its logic is worse
    than one that is quarantined and flagged."""
    if name and not re.search(rf"\b{re.escape(name.split('::')[-1])}\s*\(", fixed):
        return f"model output no longer defines {name}"
    if "{" not in fixed or fixed.count("{") != fixed.count("}"):
        return "model output is not a complete function"
    orig_len = len(re.sub(r"\s+", "", original))
    new_len = len(re.sub(r"\s+", "", fixed))
    if orig_len > 300 and new_len < 0.4 * orig_len:
        return f"model output is {new_len * 100 // max(orig_len, 1)}% of the original size (gutted)"
    return None


# ----------------------------------------------------------------------------
# Fix cache
# ----------------------------------------------------------------------------

def load_cache(cfg: Config) -> dict:
    if cfg.cache_path.exists():
        return json.loads(cfg.cache_path.read_text())
    return {}

def save_cache(cfg: Config, cache: dict) -> None:
    for _ in range(20):                       # other workers may be adding to it
        try:
            text = json.dumps(dict(cache), indent=0)
            break
        except RuntimeError:
            time.sleep(0.02)
    else:
        return
    write_atomic(cfg.cache_path, text)

def cache_key(src: str, err: str) -> str:
    h = hashlib.sha256()
    h.update(src.encode()); h.update(b"||"); h.update(err[-1000:].encode())
    return h.hexdigest()[:24]


# ----------------------------------------------------------------------------
# Stage 4 — Fixer loop
# ----------------------------------------------------------------------------

def quarantine(cfg: Config, rec: FuncRecord, original: Optional[str] = None) -> None:
    """original: the code before any fix attempts (kept, rather than whatever the
    attempts left behind), so the recover stage starts from the real thing."""
    if STOPPING.is_set():
        raise StopRun                         # not because the run is being stopped
    cfg.quarantine_dir.mkdir(parents=True, exist_ok=True)
    src = cfg.workdir / rec.file
    dst = cfg.quarantine_dir / Path(rec.file).name
    if original is not None:
        dst.write_text(original)
    else:
        shutil.copy(src, dst)
    # replace the TU with a compilable stub so the build can progress
    stub = (f'#include "shared.h"\n\n'
            f'// QUARANTINED: {rec.name} — could not be repaired automatically.\n'
            f'// Original saved at quarantine/{Path(rec.file).name}\n')
    src.write_text(stub)
    rec.quarantined = True
    log(cfg, f"  QUARANTINE {rec.name}: {_first_error(rec.last_error, rec.file)[1][:160] if rec.last_error else '?'}")


_FIXCTX: dict = {}
_FIX_TL = threading.local()       # this thread's last plan (fix stage)


def _first_error(err: str, rel: str) -> tuple[int, str]:
    name = Path(rel).name
    for l in err.splitlines():
        m = DIAG_RE.match(l.strip())
        if m and "error" in m.group("sev") and Path(m.group("file")).name == name:
            return int(m.group("line")), m.group("msg")
    return 0, (next((l for l in err.splitlines() if "error" in l), "") or err[:200]).strip()


def compile_fix_edit(cfg: Config, rec: FuncRecord, src: str, err: str) -> Optional[str]:
    """Plan and make one small edit to the lines with the first compile error."""
    line, msg = _first_error(err, rec.file)
    _FIX_TL.plan = ""
    if not line:
        return None
    if not cfg.fix_model_used and not model_check(cfg):
        return None
    ctx = _FIXCTX.get("ctx")
    if ctx is None or ctx.cfg is not cfg:
        ctx = ImproveCtx(cfg, {rec.mangled: rec})
        _FIXCTX["ctx"] = ctx
    ctx.model = cfg.fix_model_used
    decls = gather_declarations(cfg, extract_error_symbols(err))
    new = ctx.line_edit(rec, src, line, f"The compiler says: {msg}. Fix it without changing "
                        f"what the code does; don't rename the function.",
                        context=(f"Declarations the program already has (use them, don't "
                                 f"redefine them):\n{decls}" if decls else ""))
    _FIX_TL.plan = ctx.last_plan
    MODEL_STATS["calls"] += 1
    if new is None:
        MODEL_STATS["no_answer"] += 1
    return new


def repair_tu(cfg: Config, rec: FuncRecord, cache: dict) -> bool:
    """Drive one TU to compile. Returns True if it compiles, False if quarantined."""
    rel = rec.file
    header_fix_tries = 0
    original = (cfg.workdir / rel).read_text()
    for attempt in range(cfg.max_model_attempts + 1):
        phase("compiling")
        ok, err, _ = compile_tu(cfg, rel)
        if ok:
            rec.compiles = True
            return True
        rec.last_error = err[-4000:]

        # 0) if this failure comes from a shared header, fix the HEADER, not the
        #    body — otherwise we rewrite a fine function that can never pass.
        if header_implicated(err) and header_fix_tries < 2:
            header_fix_tries += 1
            log(cfg, f"      {rec.name}: failure originates in a shared header — "
                     f"repairing header, not the function")
            phase("repairing shared.h")
            repair_header(cfg, "shared.h")
            continue

        # 1) templated / deterministic
        phase("quick deterministic fixes")
        if templated_fix(cfg, rel, err):
            continue

        # 2) cache
        src = (cfg.workdir / rel).read_text()
        key = cache_key(src, err)
        if key in cache:
            (cfg.workdir / rel).write_text(cache[key])
            ok2, _, _ = compile_tu(cfg, rel)
            if ok2:
                rec.compiles = True
                return True

        # 3) the model: ONE small edit to the line the compiler flags (planned
        #    first, with the notes from earlier tries), never a whole new function
        if attempt >= cfg.max_model_attempts:
            break
        phase(f"small edit by the model ({attempt + 1}/{cfg.max_model_attempts})")
        new_text = compile_fix_edit(cfg, rec, src, err)
        rec.attempts += 1
        if new_text:
            (cfg.workdir / rel).write_text(new_text)
            phase("compiling the model's edit")
            try:
                ok3, err3, _ = compile_tu(cfg, rel)
            except StopRun:
                (cfg.workdir / rel).write_text(src)
                raise
            write_note(cfg, rel, f"[compile] {_first_error(err, rel)[1][:120]} — plan: "
                                 f"{getattr(_FIX_TL, 'plan', '')[:160]} — "
                                 + ("compiles now." if ok3 else
                                    "still fails: " + _first_error(err3, rel)[1][:100]))
            if ok3:
                cache[key] = (cfg.workdir / rel).read_text()
                save_cache(cfg, cache)
                rec.compiles = True
                return True
            # keep the edit only if it got somewhere: fewer errors, or the error it
            # was for is gone without adding more. Otherwise undo it, so the next
            # try starts from the same code instead of from a broken edit.
            before, after = _first_error(err, rel), _first_error(err3, rel)
            if n_errors(err3) < n_errors(err) or (after != before and n_errors(err3) <= n_errors(err)):
                rec.last_error = err3[-4000:]
            else:
                (cfg.workdir / rel).write_text(src)
                write_note(cfg, rel, "[compile] that edit didn't help — undone.")

    quarantine(cfg, rec, original)
    return False


def error_kinds(cfg: Config, records: dict) -> list[tuple[int, str, list[str]]]:
    """Why functions are quarantined, grouped: (how many, kind of error, examples).
    Names in quotes are replaced by X so the same kind of error groups together."""
    kinds: dict[str, list[str]] = {}
    for r in records.values():
        if r.quarantined and r.last_error:
            msg = _first_error(r.last_error, r.file)[1]
            msg = re.sub(r"'[^']*'", "'X'", msg)
            msg = re.sub(r"\b\d+\b", "N", msg)[:120]
            kinds.setdefault(msg, []).append(r.name)
    return sorted(((len(v), k, v[:3]) for k, v in kinds.items()), reverse=True)


def error_summary(P: "Paths", records: Optional[dict] = None, cfg: Optional[Config] = None,
                  limit=15) -> None:
    """Every kind of error so far, grouped, into the log: printed when the run is
    stopped and when it finishes. Fast (no compiling), so it fits in the few seconds
    the Stop button allows."""
    out = ["", "━━━━ errors so far ━━━━"]
    try:
        fns = load_progress(P).get("functions", {})
    except Exception:
        fns = {}
    rw: dict[str, list[str]] = {}
    for e in fns.values():
        if e.get("status") in ("skipped", "redo", "too big") or e.get("redo_failed"):
            why = e.get("reason") or e.get("retry_reason") or e.get("redo_failed") or e["status"]
            rw.setdefault(why, []).append(e.get("name") or e.get("ghidra", "?"))
    if rw:
        out.append(f"rewrite — {sum(map(len, rw.values()))} function(s) without a usable "
                   f"rewrite (tried again next run):")
        for why, names in sorted(rw.items(), key=lambda kv: -len(kv[1]))[:limit]:
            out.append(f"  {len(names):6d} × {why}   e.g. {', '.join(names[:3])}")
    if records is None and P.manifest.exists():
        try:
            cfg = cfg or Config(input_file=P.rewritten, workdir=P.build)
            records = load_manifest(cfg)
        except Exception:
            records = None
    if records:
        cfg = cfg or Config(input_file=P.rewritten, workdir=P.build)
        kinds = error_kinds(cfg, records)
        failing = [r for r in records.values() if not r.compiles and not r.quarantined]
        if kinds:
            out.append(f"build — {sum(n for n, _, _ in kinds)} function(s) quarantined, by "
                       f"first compile error:")
            out += [f"  {n:6d} × {k}   e.g. {', '.join(ex)}" for n, k, ex in kinds[:limit]]
            if len(kinds) > limit:
                out.append(f"  ... and {len(kinds) - limit} more kinds (build/fix_report.txt)")
        if failing:
            out.append(f"build — {len(failing)} function(s) not compiling yet (not tried, or "
                       f"stopped before they were)")
    if MODEL_ACTIVITY.get("errors"):
        out.append(f"model — LM Studio turned down {MODEL_ACTIVITY['errors']} request(s) this run")
    if MODEL_ACTIVITY.get("thinking_only"):
        out.append(f"model — {MODEL_ACTIVITY['thinking_only']} answer(s) were only thinking")
    if len(out) == 2:
        out.append("  none")
    for line in out:
        plog(P, line)


def write_fix_report(cfg: Config, records: dict) -> None:
    kinds = error_kinds(cfg, records)
    total = sum(n for n, _, _ in kinds)
    lines = [f"why {total} function(s) are quarantined (first compile error, grouped):", ""]
    lines += [f"{n:6d}  {k}\n        e.g. {', '.join(ex)}" for n, k, ex in kinds]
    (cfg.workdir / "fix_report.txt").write_text("\n".join(lines) + "\n")
    if kinds:
        log(cfg, f"  why functions are quarantined (most common first; all in fix_report.txt):")
        for n, k, ex in kinds[:8]:
            log(cfg, f"    {n:5d} × {k}  (e.g. {ex[0]})")


def fixer_loop(cfg: Config, records: dict[str, FuncRecord], order: list[str]) -> None:
    cache = load_cache(cfg)
    failing = [m for m in order if m in records and not records[m].compiles
               and not records[m].quarantined]
    total = len(failing)
    log(cfg, f"  fixer loop over {total} failing TU(s), dependency-ordered")
    fixed = [0]
    use = ModelUse()
    prog = Progress(total, 0, title="repairing functions (callees first)")
    prog.extra = lambda: f"{fixed[0]} fixed | {use.text()}"

    def one(item):
        i, m = item
        rec = records[m]
        t1 = time.time()
        prog.begin(m, rec.name)
        try:
            ok = repair_tu(cfg, rec, cache)
        finally:
            prog.end(m)
        if ok:
            fixed[0] += 1
        log(cfg, f"    [{i}/{total}] {rec.name} -> "
                 f"{'fixed' if ok else 'quarantined'} ({fmt_duration(time.time() - t1)})")

    def checkpoint():
        # this loop can run for hours; save so a rerun picks up from here
        save_manifest(cfg, records)
        save_cache(cfg, cache)
    try:
        work_pool(cfg.workers, list(enumerate(failing, 1)), one, 25, checkpoint)
    finally:
        prog.close()
    save_cache(cfg, cache)
    if MODEL_STATS["calls"]:
        log(cfg, f"  model: {MODEL_STATS['calls']} small edit(s) asked for, "
                 f"{MODEL_STATS['no_answer']} without a usable edit")
    done = sum(1 for r in records.values() if r.compiles)
    q = sum(1 for r in records.values() if r.quarantined)
    log(cfg, f"  fixer loop done: {done} compiling, {q} quarantined")
    write_fix_report(cfg, records)


# ----------------------------------------------------------------------------
# Stage 5 — Link pass
# ----------------------------------------------------------------------------

GHIDRA_AUTONAME_RE = re.compile(r"^(FUN_|DAT_|PTR_|thunk_|LAB_|SUB_|switchD_|caseD_|s_|u_)")


def _demangle_all(cfg: Config, syms: list[str]) -> dict[str, str]:
    """Raw linker symbol -> readable name. macOS adds a leading underscore to
    every symbol; C++ ones are then demangled with c++filt."""
    out: dict[str, str] = {}
    to_dm: list[str] = []
    for s in syms:
        t = s
        if sys.platform == "darwin" and t.startswith("_") and not t.startswith("_Z") \
                and "(" not in t:
            t = t[1:]
        out[s] = t
        if t.startswith("_Z"):
            to_dm.append(t)
    if to_dm:
        try:
            pr = subprocess.run(["c++filt"], input="\n".join(to_dm), capture_output=True,
                                text=True, timeout=60)
            dm = pr.stdout.splitlines()
            if len(dm) == len(to_dm):
                table = dict(zip(to_dm, dm))
                for s, t in out.items():
                    if t in table:
                        out[s] = table[t]
        except Exception:
            pass
    return out


def _parse_link_errors(err: str) -> tuple[list[str], list[tuple[str, str]]]:
    """Returns (undefined symbols, [(duplicate symbol, text block)]) for
    macOS ld64/ld-prime, GNU ld and lld output."""
    undefined: list[str] = []
    for pat in (r'^\s*"(.+?)", referenced from:',            # macOS
                r"undefined reference to [`'](.+?)'",          # GNU ld
                r"undefined symbol: (.+?)\s*$"):               # lld
        for m in re.finditer(pat, err, re.M):
            sym = m.group(1).strip()
            if sym and sym not in undefined:
                undefined.append(sym)
    dups: list[tuple[str, str]] = []
    for pat in (r"duplicate symbol '(.+?)' in:",                # macOS
                r"multiple definition of [`'](.+?)'",           # GNU ld
                r"duplicate symbol: (.+?)\s*$"):                # lld
        for m in re.finditer(pat, err, re.M):
            dups.append((m.group(1).strip(), err[max(0, m.start() - 300): m.end() + 600]))
    return undefined, dups


def _enabled_header_lines(cfg: Config) -> list[tuple[str, str, str]]:
    """(kind, label, line) for every declaration still enabled in shared.h."""
    lines = cfg.shared_h.read_text().splitlines()
    out = []
    for u in _parse_units(lines):
        body = lines[u["start"] + 1:u["end"]]
        if not body or body[0].startswith("#if 0"):
            continue
        if u["kind"] in ("proto", "global") and len(body) == 1:
            out.append((u["kind"], u["label"], body[0].strip()))
    return out


def _stub_for(kind: str, line: str, name: str) -> Optional[str]:
    """Turn a prototype / extern line from shared.h into a placeholder
    definition that returns / holds a zero value."""
    if kind == "global":
        if not line.startswith("extern ") or line.startswith('extern "C"'):
            return None
        return line[len("extern "):].rstrip(";").rstrip() + "{};"
    decl = line.rstrip(";").rstrip()
    head = decl[:decl.find(name + "(")] if (name + "(") in decl else ""
    if re.search(r"&\s*$", head):
        return None            # returns a reference: no safe placeholder
    if re.match(r'^(extern "C"\s+)?void\s+$', head):
        return decl + " {}"
    return decl + " { return {}; }"


# ----------------------------------------------------------------------------
# Stage 4b — recover quarantined functions from their Ghidra pseudocode
# ----------------------------------------------------------------------------
#
# A quarantined function compiled on its own in pseudo_to_cpp.py (against invented
# declarations) but not against the shared header. Instead of leaving it stubbed,
# go back to the SOURCE — Ghidra's pseudocode — and rewrite it to compile against
# shared.h, with a real compile check. Three strategies, in order:
#   (a) full rewrite from pseudocode + the shared.h declarations it needs
#   (b) error-window patching (for functions too big for one prompt): fix only
#       the lines around each compile error, a window at a time
#   (c) faithful fallback: make Ghidra's own pseudocode compile (ugly but true)
# A function that comes through is marked rederived, not silently "fixed".

PSEUDO_SYSTEM = (
    "You rewrite ONE function from a decompiler's pseudocode into C++ that compiles "
    "as part of an existing program. The program already defines its types, globals "
    "and the other functions — their declarations are given to you, and you MUST use "
    "them instead of redefining them. Rules: keep the behaviour exactly as in the "
    "pseudocode (same conditions, loops, arithmetic, calls, return values); do not "
    "invent logging, printing or error handling; keep the function's name and "
    "signature EXACTLY as in the provided prototype; do not add #include lines or "
    "redefine any provided type/global/function; turn Ghidra artifacts (undefined4, "
    "CONCAT/SUB/ZEXT, param_1, local_28, uVarN, DAT_x) into ordinary C++. Reply with "
    "ONLY the one function as a single ```cpp code block."
)

_PSEUDO_CACHE: dict = {}


def _load_pseudocode(cfg: Config) -> tuple[dict, dict]:
    """(address -> pseudocode, final-name -> {ghidra,addr}). Loaded once."""
    key = str(cfg.workdir)
    if key in _PSEUDO_CACHE:
        return _PSEUDO_CACHE[key]
    export, index = {}, {}
    try:
        data = json.loads(Path(cfg.export_path).read_text())
        export = data.get("pseudocode", {}) or {}
    except Exception:
        export = {}
    try:
        index = json.loads(Path(cfg.index_path).read_text()) or {}
    except Exception:
        index = {}
    _PSEUDO_CACHE[key] = (export, index)
    return export, index


def _pseudo_for(rec: FuncRecord, export: dict, index: dict) -> Optional[str]:
    addr = rec.ghidra_addr
    if not addr:
        base = re.sub(r"__dup\d+$", "", rec.name)
        addr = (index.get(rec.name) or index.get(base) or {}).get("addr", "")
    code = export.get(addr) if addr else None
    return code or None


def _proto_for(cfg: Config, name: str) -> Optional[str]:
    base = re.sub(r"__dup\d+$", "", name)
    for _, label, line in _enabled_header_lines(cfg):
        if label in (name, base):
            return line
    return None


def _idents(text: str) -> list[str]:
    seen, out = set(), []
    for m in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text):
        if m not in seen:
            seen.add(m)
            out.append(m)
    return out


def _decls_for(cfg: Config, text: str, extra: str = "") -> str:
    syms = _idents(text)[:80] + extract_error_symbols(extra)
    return gather_declarations(cfg, syms)


def _post_chat(cfg: Config, system: str, user: str, max_tokens: int) -> Optional[str]:
    content = _fix_chat(cfg, system, user, max_tokens)
    if content is None:
        return None
    m =re.search(r"```(?:cpp|c\+\+|c)?\s*(.*?)```", content, re.DOTALL)
    code = m.group(1) if m else content
    code = "\n".join(l for l in code.splitlines()
                     if not l.lstrip().startswith("#include")).strip()
    return code or None


def _write_and_compile(cfg: Config, rec: FuncRecord, body: str) -> tuple[bool, str]:
    (cfg.workdir / rec.file).write_text('#include "shared.h"\n\n' + body + "\n")
    ok, err, _ = compile_tu(cfg, rec.file)
    return ok, err


def _rename_defined_func(src: str, newname: str) -> str:
    i = src.find("{")
    if i < 0:
        return src
    head = src[:i]
    m = re.search(r"([A-Za-z_]\w*)\s*\(", head)
    if not m:
        return src
    return head[:m.start(1)] + newname + head[m.end(1):] + src[i:]


def _recover_full_rewrite(cfg: Config, rec: FuncRecord, pseudo: str,
                          proto: str, orig_body: str) -> Optional[str]:
    decls = _decls_for(cfg, pseudo)
    user = (f"// Target prototype (keep this name and signature):\n{proto}\n\n"
            f"// Declarations already provided by the program (use, do not redefine):\n"
            f"{decls}\n\n// Ghidra pseudocode of the function to rewrite:\n{pseudo}")
    for attempt in range(cfg.max_model_attempts):
        fixed = _post_chat(cfg, PSEUDO_SYSTEM, user, cfg.model_max_tokens)
        if not fixed:
            return None
        # compare against the decompiled body (not the verbose pseudocode) so a
        # legitimately concise rewrite isn't mistaken for a gutted one
        why = _accept_model_fix(rec.name, orig_body or pseudo, fixed)
        if why:
            return None
        ok, err = _write_and_compile(cfg, rec, fixed)
        if ok:
            return fixed
        user = (f"// That did not compile. Compiler errors:\n{err[-1800:]}\n\n"
                f"// Target prototype:\n{proto}\n\n// Declarations:\n{decls}\n\n"
                f"// Pseudocode:\n{pseudo}")
    return None


def _recover_window_patch(cfg: Config, rec: FuncRecord, pseudo: str,
                          rounds: int = 6) -> bool:
    """For functions too big for one prompt: fix the lines around the first
    compile error, recompile, repeat. The whole file stays on disk between rounds."""
    pseudo_slice = pseudo[:cfg.model_ctx_chars // 2]
    for _ in range(rounds):
        ok, err, _ = compile_tu(cfg, rec.file)
        if ok:
            return True
        mm = re.search(rf"{re.escape(Path(rec.file).name)}:(\d+):", err)
        if not mm:
            return False
        ln = int(mm.group(1))
        lines = (cfg.workdir / rec.file).read_text().splitlines()
        lo, hi = max(0, ln - 16), min(len(lines), ln + 15)
        window = "\n".join(lines[lo:hi])
        user = (f"// Part of a decompiled function that fails to compile against the "
                f"program's shared header.\n// Compiler errors:\n{err[-1200:]}\n\n"
                f"// The function's Ghidra pseudocode (reference):\n{pseudo_slice}\n\n"
                f"// Fix ONLY these lines (return the same lines, corrected, nothing "
                f"else):\n```cpp\n{window}\n```")
        fixed = _post_chat(cfg, FIX_EDIT_SYS, user,
                           min(cfg.model_max_tokens, max(400, (hi - lo) * 24)))
        if not fixed or fixed.count("{") - fixed.count("}") != \
                window.count("{") - window.count("}"):
            return False   # would unbalance the braces: give up on this strategy
        lines[lo:hi] = fixed.splitlines()
        (cfg.workdir / rec.file).write_text("\n".join(lines) + "\n")
    ok, _, _ = compile_tu(cfg, rec.file)
    return ok


def _recover_faithful(cfg: Config, rec: FuncRecord, pseudo: str) -> bool:
    """Last resort: make Ghidra's own pseudocode compile against shared.h, with
    its name fixed to match the prototype. Ugly but faithful to the binary."""
    body = deghidra_text(_rename_defined_func(pseudo, re.sub(r"__dup\d+$", "", rec.name)))
    ok, _ = _write_and_compile(cfg, rec, body)
    return ok


def recover_one(cfg: Config, rec: FuncRecord, export: dict, index: dict) -> bool:
    pseudo = _pseudo_for(rec, export, index)
    if not pseudo:
        return False
    proto = _proto_for(cfg, rec.name)
    saved = (cfg.workdir / rec.file).read_text()   # current stub, to restore on failure
    # the original decompiled body (saved at quarantine time), used both as the
    # starting point for window patching and as the size reference for guards
    orig = cfg.quarantine_dir / Path(rec.file).name
    orig_text = orig.read_text() if orig.exists() else saved
    orig_body = re.sub(r'^\s*#include\s+"shared.h"\s*', "", orig_text, count=1).strip()

    big = len(pseudo) + len(orig_text) > cfg.model_ctx_chars
    rec.recovery_model = cfg.fix_model_used or ""
    # Small steps first; the improve stage then improves whatever comes through.
    # (a) error-window patching: start from the original decompiled body, which is
    # closer to correct than the stub, and fix only the lines around each error
    (cfg.workdir / rec.file).write_text(orig_text)
    phase("patching the lines around each error")
    if _recover_window_patch(cfg, rec, pseudo):
        body = (cfg.workdir / rec.file).read_text()
        body = re.sub(r'^\s*#include\s+"shared.h"\s*', "", body, count=1).strip()
        if not _accept_model_fix(rec.name, orig_body, body):
            rec.recovery = "window-patch"
            return _finish_recovery(cfg, rec)

    # (b) faithful: Ghidra's own pseudocode, made to compile (no model)
    phase("faithful fallback (Ghidra's own pseudocode)")
    if _recover_faithful(cfg, rec, pseudo):
        rec.recovery = "faithful-pseudocode"
        return _finish_recovery(cfg, rec)

    # (c) last resort: the model writes the function again from the pseudocode
    if proto and not big:
        phase("rewriting from pseudocode against shared.h (last resort)")
        fixed = _recover_full_rewrite(cfg, rec, pseudo, proto, orig_body)
        if fixed is not None:
            rec.recovery = "rewrite"
            return _finish_recovery(cfg, rec)

    (cfg.workdir / rec.file).write_text(saved)   # restore the stub; stays quarantined
    rec.recovery_tried = True
    return False


def _finish_recovery(cfg: Config, rec: FuncRecord) -> bool:
    rec.compiles = True
    rec.quarantined = False
    rec.rederived = True
    return True


def pseudocode_recovery(cfg: Config, records: dict[str, FuncRecord]) -> None:
    if cfg.no_pseudo:
        return
    export, index = _load_pseudocode(cfg)
    if not export:
        log(cfg, f"  pseudocode recovery: no pseudocode in {cfg.export_path} — skipping")
        return
    model_check(cfg)
    current = cfg.fix_model_used or ""
    targets = [m for m, r in records.items() if r.quarantined
               and (cfg.retry_quarantined or not r.recovery_tried
                    or (current and r.recovery_model != current))]
    if not targets:
        already = sum(1 for r in records.values() if r.quarantined and r.recovery_tried)
        if already:
            log(cfg, f"  pseudocode recovery: {already} quarantined function(s) already "
                     f"tried and skipped — use --retry-quarantined to try again "
                     f"(e.g. after loading a bigger model)")
        return
    have = sum(1 for m in targets if _pseudo_for(records[m], export, index))
    log(cfg, f"  pseudocode recovery: {len(targets)} quarantined, {have} have "
             f"pseudocode to rebuild from")
    if not have:
        return
    if not current:
        cfg.fix_model_used = ""
        log(cfg, "  (model not available — only the faithful fallback will run)")
    t0 = time.time()
    counts = {"fixed": 0, "faithful": 0}
    use = ModelUse()
    prog = Progress(len(targets), 0, title="rebuilding quarantined functions")
    prog.extra = lambda: f"{counts['fixed']} re-derived | {use.text()}"

    def one(item):
        i, m = item
        rec = records[m]
        if not _pseudo_for(rec, export, index):
            prog.end(m)
            return
        prog.begin(m, rec.name)
        try:
            ok = recover_one(cfg, rec, export, index)
        finally:
            prog.end(m)
        if ok:
            counts["fixed"] += 1
            if rec.recovery == "faithful-pseudocode":
                counts["faithful"] += 1
            log(cfg, f"    [{i}/{len(targets)}] {rec.name} -> re-derived ({rec.recovery})")
        else:
            log(cfg, f"    [{i}/{len(targets)}] {rec.name} -> still quarantined")
    try:
        work_pool(cfg.workers, list(enumerate(targets, 1)), one, 20,
                  lambda: save_manifest(cfg, records))
    finally:
        prog.close()
    fixed_n, faithful_n = counts["fixed"], counts["faithful"]
    save_manifest(cfg, records)
    log(cfg, f"  pseudocode recovery: {fixed_n} re-derived "
             f"({faithful_n} as faithful pseudocode — review these), "
             f"{len(targets) - fixed_n} still quarantined. Took {time.time()-t0:.0f}s")
    rederived = [r.name for r in records.values() if r.rederived]
    if rederived:
        (cfg.workdir / "rederived.txt").write_text("\n".join(sorted(rederived)) + "\n")


def link_pass(cfg: Config, records: dict[str, FuncRecord]) -> bool:
    """Compile every TU to an object (parallel, incremental, with the PCH) and
    link a shared library. Problems are handled deterministically:

      - a TU that no longer compiles      -> fixer (model) or quarantine
      - globals.cpp / stubs.cpp errors     -> disable the broken definition
      - undefined function/global that this
        program owns (quarantined, or a
        Ghidra FUN_/DAT_ name) with a
        prototype in shared.h               -> placeholder in stubs.cpp
      - duplicate symbol                    -> keep the first, quarantine the rest
      - anything else (system frameworks)   -> reported in link_report.txt

    The model is never asked to fix "symbol not found": that can't be fixed by
    editing the caller, and the old loop quarantined innocent callers."""
    from concurrent.futures import ThreadPoolExecutor
    cache = load_cache(cfg)
    obj_dir = cfg.workdir / "obj"
    obj_dir.mkdir(exist_ok=True)
    stubs_cpp = cfg.workdir / "stubs.cpp"
    stubs: dict[str, str] = {}          # name -> stub definition
    report: list[str] = []
    if sys.platform == "darwin":
        out = cfg.workdir / "program.dylib"
        lib_flags = ["-dynamiclib"]
    else:
        out = cfg.workdir / "program.so"
        lib_flags = ["-shared", "-Wl,--no-undefined"]
    stem_to_rec = {Path(r.file).stem: m for m, r in records.items()}
    quarantined_names = lambda: {r.name for r in records.values() if r.quarantined}

    def write_stubs():
        body = ['#include "shared.h"', "", "// ==== placeholder definitions ====",
                "// Functions/globals that are referenced but have no recovered",
                "// definition. Each returns / holds zero. Review before trusting",
                "// any behaviour that depends on them."]
        for i, (nm, text) in enumerate(sorted(stubs.items()), 1):
            body += [f"//@unit {i} stub {nm}", text]
        stubs_cpp.write_text("\n".join(body) + "\n")

    # start from no placeholders: an earlier run's stubs could stand in for functions
    # that now compile (duplicate symbols); the rounds below add back what's needed
    write_stubs()

    def _obj(src: Path) -> tuple[Path, Path, str]:
        o = obj_dir / (src.stem + ".o")
        if o.exists() and o.stat().st_mtime >= max(src.stat().st_mtime,
                                                   cfg.shared_h.stat().st_mtime):
            return src, o, ""
        pch = _pch_flags(cfg)
        cmd = [cfg.cxx, f"-std={cfg.std}", f"-I{cfg.workdir}", "-w", "-c",
               *PIC_FLAGS, *pch, *cfg.extra_flags, str(src), "-o", str(o)]
        pr = subprocess.run(cmd, capture_output=True, text=True)
        if pr.returncode != 0 and pch:   # PCH/flag mismatch -> retry without
            pr = subprocess.run([x for x in cmd if x not in pch],
                                capture_output=True, text=True)
        if pr.returncode != 0:
            o.unlink(missing_ok=True)
        return src, o, ("" if pr.returncode == 0 else pr.stderr)

    workers = max(1, (os.cpu_count() or 2) - 1)
    err = ""
    for round_no in range(1, 16):
        _pch_flags(cfg)   # make sure the PCH is current before workers start
        sources = [cfg.workdir / r.file for r in records.values()] + [cfg.globals_cpp]
        if stubs_cpp.exists():
            sources.append(stubs_cpp)
        prog = Progress(len(sources), 0, title=f"round {round_no}: compiling objects")
        try:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                built = []
                for b in pool.map(_obj, sources):
                    built.append(b)
                    prog.end(b[0].name)
        finally:
            prog.close()
        failed = [(src, e) for src, o, e in built if e]

        if failed:
            log(cfg, f"  link round {round_no}: {len(failed)} file(s) failed to compile")
            for src, e in failed:
                if src in (cfg.globals_cpp, stubs_cpp):
                    rel = src.name
                    if not repair_header(cfg, rel):
                        (cfg.workdir / "link_errors.txt").write_text(e)
                        log(cfg, f"  {rel} can't be repaired — see link_errors.txt")
                        return False
                    if src == stubs_cpp:   # forget stubs that were switched off
                        txt = stubs_cpp.read_text().splitlines()
                        for u in _parse_units(txt):
                            if txt[u["start"] + 1].startswith("#if 0"):
                                stubs.pop(u["label"], None)
                                report.append(f"stub for {u['label']} did not compile — removed")
                        write_stubs()
                    continue
                m = stem_to_rec.get(src.stem)
                if m is None:
                    continue
                rec = records[m]
                rec.compiles = False
                rec.last_error = e[-4000:]
                if not repair_tu(cfg, rec, cache):
                    report.append(f"quarantined {rec.name}: stopped compiling at link time")
            continue

        objs = [str(o) for _, o, _ in built]
        log(cfg, f"  link round {round_no}: linking {len(objs)} objects ...")
        cmd = [cfg.cxx, *lib_flags, *PIC_FLAGS, *cfg.extra_flags, *objs, "-o", str(out)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            if stubs:
                log(cfg, f"  {len(stubs)} placeholder definition(s) in stubs.cpp "
                         f"(listed in link_report.txt)")
            (cfg.workdir / "link_report.txt").write_text("\n".join(report) + "\n")
            log(cfg, f"  LINK OK (round {round_no}) -> {out}")
            return True

        err = proc.stderr
        undefined, dups = _parse_link_errors(err)
        changed = False

        # --- duplicate symbols: keep the first definition, quarantine the rest
        for sym, block in dups:
            stems = sorted({Path(p).stem for p in re.findall(r"[^\s'`\"():]+\.o\b", block)}
                           & set(stem_to_rec))
            for stem in stems[1:]:
                rec = records[stem_to_rec[stem]]
                if not rec.quarantined:
                    rec.last_error = f"duplicate symbol {sym}"
                    quarantine(cfg, rec)
                    report.append(f"quarantined {rec.name}: duplicate definition of {sym} "
                                  f"(kept {records[stem_to_rec[stems[0]]].name})")
                    changed = True

        # --- undefined symbols: stub the ones this program owns
        names = _demangle_all(cfg, undefined)
        header = _enabled_header_lines(cfg)
        external: list[str] = []
        qnames = quarantined_names()
        for raw_sym in undefined:
            readable = names.get(raw_sym, raw_sym)
            if "::" in readable.split("(")[0]:
                external.append(readable)       # class method / namespaced: not stubbed
                continue
            base = readable.split("(")[0].strip()
            owned = base in qnames or bool(GHIDRA_AUTONAME_RE.match(base)) or cfg.stub_all
            if not owned or base in stubs:
                external.append(readable)
                continue
            cands = [(k, l) for k, lbl, l in header if lbl == base]
            if "(" in readable and len(cands) > 1:   # pick the matching overload
                want = re.sub(r"\s+", "", readable[readable.find("("):])
                exact = [(k, l) for k, l in cands
                         if re.sub(r"\s+", "", l[l.find(base + "(") + len(base):]
                                   ).rstrip(";").startswith(want)]
                cands = exact or cands[:1]
            stub = _stub_for(cands[0][0], cands[0][1], base) if cands else None
            if stub:
                stubs[base] = stub
                why = "quarantined" if base in qnames else "never defined"
                report.append(f"stubbed {readable} ({why})")
                changed = True
            else:
                external.append(readable)
        if changed:
            write_stubs()
            log(cfg, f"  link round {round_no}: {len(undefined)} undefined, {len(dups)} "
                     f"duplicate symbol(s) — stubbed/quarantined, relinking")
            continue

        # nothing left we can fix automatically
        (cfg.workdir / "link_errors.txt").write_text(err)
        report.append("")
        report.append(f"unresolved external symbols ({len(external)}):")
        report += [f"  {x}" for x in external]
        (cfg.workdir / "link_report.txt").write_text("\n".join(report) + "\n")
        if external:
            log(cfg, f"  link: {len(external)} undefined symbol(s) come from outside this "
                     f"code (system frameworks / libraries), e.g. {', '.join(external[:4])}")
            if sys.platform == "darwin":
                log(cfg, "  -> add the frameworks with --flag=-framework --flag=<Name>, or "
                         "let the dylib resolve them at load time with "
                         "--flag=-Wl,-undefined,dynamic_lookup")
            else:
                log(cfg, "  -> add the libraries with --flag=-l<name>")
            log(cfg, "     (or --stub-all-missing to stub anything that has a prototype)")
        else:
            log(cfg, "  link errors not handled automatically — see link_errors.txt")
        return False
    (cfg.workdir / "link_errors.txt").write_text(err)
    log(cfg, "  link pass hit round cap — see link_errors.txt")
    return False


# ----------------------------------------------------------------------------
# Manifest I/O
# ----------------------------------------------------------------------------

def save_manifest(cfg: Config, records: dict[str, FuncRecord]) -> None:
    data = {m: asdict(r) for m, r in records.items()}
    tmp = cfg.manifest_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(cfg.manifest_path)      # never leave a half-written manifest


def load_manifest(cfg: Config) -> dict[str, FuncRecord]:
    data = json.loads(cfg.manifest_path.read_text())
    known = set(FuncRecord.__dataclass_fields__)
    return {m: FuncRecord(**{k: v for k, v in r.items() if k in known})
            for m, r in data.items()}


# ----------------------------------------------------------------------------
# Run state + resume check
# ----------------------------------------------------------------------------
#
# build/build_state.json records which version of this script produced the split
# and which build steps finished. Every run checks that against what's on disk,
# so a build started with an OLDER version (or from an older rewrite) is updated
# in place: the header and globals are rebuilt, function files nobody touched are
# refreshed, functions the rewrite changed get the new code, files the model
# already fixed are kept, and old quarantines are retried.

SCRIPT_VERSION = "2026-10-18.1"   # bump when the split / header format changes


def _state_path(cfg: Config) -> Path:
    return cfg.workdir / "build_state.json"


def load_state(cfg: Config) -> dict:
    try:
        return json.loads(_state_path(cfg).read_text())
    except Exception:
        return {}


def save_state(cfg: Config, **updates) -> None:
    st = load_state(cfg)
    st.update(updates)
    st["version"] = SCRIPT_VERSION
    _state_path(cfg).write_text(json.dumps(st, indent=2))


def _input_sha(cfg: Config) -> str:
    return hashlib.sha256(cfg.input_file.read_bytes()).hexdigest()[:16]


def _untouched_variants(raw_body: str, name: str) -> set[str]:
    """Every way an earlier version of this script could have written a
    function's file before any fixing happened."""
    inc = '#include "shared.h"\n\n'
    bodies = {raw_body, _strip_leading_static(raw_body, name)}
    out = set()
    for b in bodies:
        t = inc + b + "\n"
        out.add(t)
        out.add(deghidra_text(t))
    return {re.sub(r"\s+", " ", v).strip() for v in out}


def reconcile_resume(cfg: Config, old: dict[str, FuncRecord]) -> dict[str, FuncRecord]:
    """Re-split the monolith with the current logic and merge it with the
    previous run's work, function by function."""
    raw = cfg.input_file.read_bytes()
    fresh_dir = cfg.workdir / "_fresh_funcs"
    if fresh_dir.exists():
        shutil.rmtree(fresh_dir)
    new = split_monolith(cfg, tu_dir=fresh_dir)

    old_by_start = {r.start: r for r in old.values()}
    counts = {"refreshed": 0, "kept": 0, "retry": 0, "new": 0, "changed": 0}
    to_deghidra: list[FuncRecord] = []
    cfg.funcs_dir.mkdir(parents=True, exist_ok=True)
    # read every old file first: a function's file can be renamed onto another's
    old_text: dict[str, Optional[str]] = {}
    for r in old.values():
        p = cfg.workdir / r.file
        old_text[r.file] = p.read_text() if p.exists() else None
    written: set[Path] = set()
    renamed_from: set[Path] = set()

    def keep_copy(rel_file: str, text: Optional[str]) -> None:
        """A fixed function file is about to be replaced: copy it to the snapshot."""
        d = cfg.snapshot_dir()
        if d is None or not text:
            return
        dest = d / "build" / rel_file
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text)

    for m, rec in new.items():
        fresh_text = (fresh_dir / Path(rec.file).name).read_text()
        target = cfg.workdir / rec.file
        written.add(target)
        # the same function in the old run: by its (mangled) name, else by position
        prev = old.get(m)
        if prev is None:
            prev = old_by_start.get(rec.start)
            if prev is not None and not (prev.name == rec.name
                                         or rec.name.startswith(prev.name + "__dup")):
                # same position but a different function: the input file was edited
                # since the old run, so its offsets no longer line up — don't carry
                # another function's code over
                prev = None
        if prev is None:
            target.write_text(fresh_text)
            to_deghidra.append(rec)
            counts["new"] += 1
            continue
        prev_path = cfg.workdir / prev.file
        if prev_path != target:
            renamed_from.add(prev_path)
        cur = old_text.get(prev.file)
        raw_body = raw[rec.start:rec.end].decode("utf-8", "replace")
        if prev.src_sha and prev.src_sha != rec.src_sha:
            # the rewrite changed this function (e.g. it was rewritten again):
            # take the new code; earlier fixes were for code that's gone
            if cur and "// QUARANTINED:" not in cur:
                keep_copy(prev.file, cur)
            target.write_text(fresh_text)
            to_deghidra.append(rec)
            counts["changed"] += 1
        elif prev.quarantined or cur is None or "// QUARANTINED:" in (cur or ""):
            # old quarantines happened against a broken/incomplete header:
            # restore the original code and let the fixer try again
            target.write_text(fresh_text)
            to_deghidra.append(rec)
            counts["retry"] += 1
        elif re.sub(r"\s+", " ", cur).strip() in _untouched_variants(raw_body, prev.name):
            target.write_text(fresh_text)      # nothing done to it yet: use new split
            to_deghidra.append(rec)
            counts["refreshed"] += 1
        else:
            # the fixer / model already changed this file: keep that work,
            # applying any rename the new split gave this function
            if rec.name != prev.name and rec.name.startswith(prev.name + "__dup"):
                cur = re.sub(rf"\b{re.escape(prev.name)}\b(?=\s*\()", rec.name, cur, count=1)
            target.write_text(cur)
            rec.attempts = prev.attempts
            rec.rederived, rec.recovery = prev.rederived, prev.recovery
            counts["kept"] += 1
    shutil.rmtree(fresh_dir)                   # this function's own scratch copies
    # files whose function moved to a new file name: their content was carried over
    # above. Moved out of funcs/ (not deleted), unless another function now uses it.
    leftovers = [p for p in renamed_from if p not in written and p.exists()
                 and p.parent == cfg.funcs_dir]
    if leftovers:
        dest = (cfg.snapshot_dir() or cfg.workdir / "funcs_unused") / "build" / "funcs_renamed"
        dest.mkdir(parents=True, exist_ok=True)
        for p in leftovers:
            shutil.move(str(p), str(dest / p.name))

    for rec in to_deghidra:
        p = cfg.workdir / rec.file
        p.write_text(deghidra_text(p.read_text()))

    log(cfg, f"    functions: {counts['changed']} changed in the rewrite (new code taken), "
             f"{counts['kept']} already fixed by the model (kept), "
             f"{counts['refreshed']} untouched (refreshed with the new split), "
             f"{counts['retry']} previously quarantined (restored for another try), "
             f"{counts['new']} not in the old run")
    if counts["changed"] and cfg.snapshot_dir() is not None:
        log(cfg, f"    (the replaced versions are in {cfg.snapshot_dir()})")
    return new


def _header_is_current(cfg: Config) -> bool:
    try:
        txt = cfg.shared_h.read_text()
    except OSError:
        return False
    return "//@unit " in txt and "#include <string>" in txt


# ----------------------------------------------------------------------------
# Orchestrator
# ----------------------------------------------------------------------------

def _gate_header(cfg: Config, records: dict[str, FuncRecord]) -> None:
    if not validate_headers(cfg):
        save_manifest(cfg, records)
        if not cfg.force:
            log(cfg, "STOPPED: shared.h does not compile, so every function would "
                     "fail and the model would rewrite thousands of fine functions "
                     "for nothing. See header_errors.txt. (--force to continue anyway)")
            sys.exit(2)
        log(cfg, "  --force: continuing despite broken header")
    save_state(cfg, header_ok=True)


def _sweep_all(cfg: Config, records: dict[str, FuncRecord]) -> None:
    log(cfg, f"  » preflight diagnose (surface any systemic cause before "
             f"spending model time on {len(records)} functions)")
    if preflight_diagnose(cfg, records):
        save_manifest(cfg, records)
        if not cfg.force:
            log(cfg, "STOPPED: every sampled function fails for a shared reason "
                     "(see first_error.txt). Fix that first. (--force to continue anyway)")
            sys.exit(2)
    log(cfg, "  » isolated compile sweep")
    live = {m: r for m, r in records.items() if not r.quarantined}
    compile_sweep(cfg, live)
    save_manifest(cfg, records)
    save_state(cfg, sweep_done=True)


# ============================================================================
# Small-edit machinery (used by the fix, improve and organize stages)
# ============================================================================
#
# The model never rewrites a whole function here. Every change is one small,
# checked step: a check finds one problem; a rule, or the model, makes one small
# edit (a few lines, or a name); the change is kept only if the function still
# compiles and still behaves like Ghidra's version. Each function has a notes
# file (its goal, what was tried, what happened) that the model reads on its
# next task, and every version of every function is kept in improve/history/.

CPP_KEYWORDS = set("""alignas alignof and asm auto bool break case catch char char16_t
char32_t class const constexpr const_cast continue decltype default delete do double
dynamic_cast else enum explicit export extern false float for friend goto if inline int
long mutable namespace new noexcept not nullptr operator or private protected public
register reinterpret_cast return short signed sizeof static static_assert static_cast
struct switch template this thread_local throw true try typedef typeid typename union
unsigned using virtual void volatile wchar_t while xor""".split())

_TOK = re.compile(r"""
    (?P<comment>//[^\n]*|/\*.*?\*/)
  | (?P<string>(?:u8|u|U|L)?"(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*')
  | (?P<number>0[xX][0-9a-fA-F]+[uUlL]*|(?:\d+\.\d*|\.\d+)(?:[eE][-+]?\d+)?[fFlL]?
               |\d+(?:[eE][-+]?\d+)?[uUlLfF]*)
  | (?P<ident>[A-Za-z_]\w*)
  | (?P<punct>->|::|<<|>>|\S)
""", re.S | re.X)

INCLUDE_LINE = '#include "shared.h"'


def tokens(text: str) -> list[tuple[str, str, int, int]]:
    """(kind, text, start, end) for every token; whitespace is skipped."""
    return [(m.lastgroup, m.group(), m.start(), m.end()) for m in _TOK.finditer(text)]


def is_ident(s: str) -> bool:
    return bool(s) and re.fullmatch(r"[A-Za-z_]\w*", s) is not None and s not in CPP_KEYWORDS


def ident_set(text: str) -> set[str]:
    return {t for k, t, _, _ in tokens(text) if k == "ident"}


def rename_idents(text: str, mapping: dict[str, str], skip_members=True) -> tuple[str, int]:
    """Rename identifier tokens (never inside strings or comments). skip_members:
    leave `x.name` / `p->name` alone (those are struct fields, not variables)."""
    toks = tokens(text)
    out, last, n = [], 0, 0
    for i, (k, t, s, e) in enumerate(toks):
        if k != "ident" or t not in mapping:
            continue
        if skip_members and i and toks[i - 1][1] in (".", "->"):
            continue
        out += [text[last:s], mapping[t]]
        last, n = e, n + 1
    out.append(text[last:])
    return "".join(out), n


def alpha_equivalent(old: str, new: str, mapping: dict[str, str]) -> bool:
    """True if `new` is `old` with only these identifiers renamed (token for token)."""
    a = [(k, t) for k, t, _, _ in tokens(old) if k != "comment"]
    b = [(k, t) for k, t, _, _ in tokens(new) if k != "comment"]
    if len(a) != len(b):
        return False
    for (ka, ta), (kb, tb) in zip(a, b):
        if ka != kb:
            return False
        if ta != tb and not (ka == "ident" and mapping.get(ta) == tb):
            return False
    return True


def matching_close(text: str, i: int) -> int:
    """Index of the bracket closing the one at text[i], or -1."""
    pairs = {"(": ")", "[": "]", "{": "}"}
    stack: list[str] = []
    for m in _TOK.finditer(text, i):
        if m.lastgroup != "punct":
            continue
        c = m.group()
        if c in pairs:
            stack.append(pairs[c])
        elif c in (")", "]", "}"):
            if not stack or stack.pop() != c:
                return -1
            if not stack:
                return m.start()
    return -1


def split_args(s: str) -> list[str]:
    """Top-level comma-separated parts of an argument / parameter list."""
    if not s.strip():
        return []
    parts, depth, last = [], 0, 0
    for m in _TOK.finditer(s):
        if m.lastgroup != "punct":
            continue
        c = m.group()
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == "," and depth == 0:
            parts.append(s[last:m.start()])
            last = m.end()
    parts.append(s[last:])
    return [p.strip() for p in parts]


def replace_calls(text: str, want, fn, limit=500) -> tuple[str, int]:
    """Replace calls `name(args)` where want(name) is true with fn(name, args) (a
    string, or None to leave that call). Innermost / last calls first."""
    n = 0
    skip: set[int] = set()
    for _ in range(limit):
        toks = tokens(text)
        cands = [(s, toks[i + 1][2], t) for i, (k, t, s, e) in enumerate(toks)
                 if k == "ident" and i + 1 < len(toks) and toks[i + 1][1] == "("
                 and want(t) and s not in skip
                 and not (i and toks[i - 1][1] in (".", "->"))]
        done = False
        for s, op, name in reversed(cands):
            close = matching_close(text, op)
            if close < 0:
                skip.add(s)
                continue
            rep = fn(name, split_args(text[op + 1:close]))
            if rep is None:
                skip.add(s)
                continue
            text = text[:s] + rep + text[close + 1:]
            n += 1
            done = True
            break
        if not done:
            break
    return text, n


def tu_split(text: str) -> tuple[str, str]:
    """(header, rest) of a one-function file: the text before the body's first '{'
    (after the include line), and everything from that '{' on."""
    body = text.split("\n", 1)[1] if text.startswith(INCLUDE_LINE) else text
    i = body.find("{")
    return (body[:i], body[i:]) if i >= 0 else (body, "")


def parse_header(header: str):
    """(return type, name, [(type, param name)]) from `ret name(params)`, or None."""
    h = " ".join(strip_comments(header).split())
    h = re.sub(r'^extern\s+"C"\s+', "", h)
    m = re.match(r"(.*?)\b([A-Za-z_~][\w:]*)\s*\((.*)\)\s*(const\s*)?$", h)
    if not m:
        return None
    params = []
    for p in split_args(m.group(3)):
        if p in ("", "void"):
            continue
        pm = re.match(r"(.*?)([A-Za-z_]\w*)\s*(\[[^\]]*\])?$", p)
        if pm and pm.group(1).strip() and pm.group(2) not in CPP_KEYWORDS:
            params.append((pm.group(1).strip() + (pm.group(3) or ""), pm.group(2)))
        else:
            params.append((p, ""))
    return m.group(1).strip(), m.group(2), params


def numbered(lines: list[str], lo: int, hi: int, mark=None) -> str:
    """Lines lo..hi-1 (0-based) with 1-based numbers; marked ones get '>>'."""
    out = []
    for i in range(max(0, lo), min(len(lines), hi)):
        tag = ">>" if mark and mark[0] <= i < mark[1] else "  "
        out.append(f"{tag}{i + 1:4d} | {lines[i]}")
    return "\n".join(out)


def text_sha(text: str) -> str:
    return hashlib.sha1(text.encode()).hexdigest()[:16]


# ---------------------------------------------------------------- notes, history, state

class ImproveState:
    """build/improve/state.json: per-function findings and parked tasks, the list
    of header-level changes to replay after a re-split, names chosen so far."""

    def __init__(self, cfg: "Config"):
        self.dir = cfg.workdir / "improve"
        (self.dir / "history").mkdir(parents=True, exist_ok=True)
        (self.dir / "notes").mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "state.json"
        self._lock = threading.Lock()
        self.data = {"funcs": {}, "overlay": [], "rounds": [], "global": {}}
        if self.path.exists():
            try:
                self.data.update(json.loads(self.path.read_text()))
            except Exception as e:
                set_aside(self.path, str(e))

    def f(self, m: str) -> dict:
        return self.data["funcs"].setdefault(m, {"findings": [], "parked": {}, "cache": {},
                                                 "changes": 0})

    def g(self, key: str, default):
        return self.data["global"].setdefault(key, default)

    def save(self):
        with self._lock:
            for _ in range(20):               # workers may be adding to it right now
                try:
                    text = json.dumps(self.data, indent=1)
                    break
                except RuntimeError:
                    time.sleep(0.02)
            else:
                return
            write_atomic(self.path, text)


def _note_file(cfg: "Config", rel: str) -> Path:
    return cfg.workdir / "improve" / "notes" / (Path(rel).stem + ".md")


def read_notes(cfg: "Config", rel: str, last=5) -> tuple[str, list[str]]:
    """(goal, the last few notes) for a function."""
    p = _note_file(cfg, rel)
    if not p.exists():
        return "", []
    lines = p.read_text(errors="replace").splitlines()
    goal = next((l[6:] for l in lines if l.startswith("goal: ")), "")
    notes = [l[2:] for l in lines if l.startswith("- ")]
    return goal, notes[-last:]


def write_note(cfg: "Config", rel: str, text: str = "", goal: str = "") -> None:
    p = _note_file(cfg, rel)
    p.parent.mkdir(parents=True, exist_ok=True)
    old = p.read_text(errors="replace") if p.exists() else f"# {Path(rel).stem}\n"
    if goal and "\ngoal: " not in old:
        old = old.rstrip("\n") + f"\ngoal: {' '.join(goal.split())}\n"
    if text:
        old = old.rstrip("\n") + f"\n- {time.strftime('%m-%d %H:%M')} {' '.join(text.split())}\n"
    p.write_text(old)


def record_version(cfg: "Config", rel: str, old: Optional[str], new: str, tag: str) -> None:
    """Keep every version: the first time, the original too. Never deleted."""
    d = cfg.workdir / "improve" / "history" / Path(rel).name
    d.mkdir(parents=True, exist_ok=True)
    n = len(list(d.iterdir()))
    suffix = Path(rel).suffix or ".txt"
    if n == 0 and old is not None:
        (d / f"0000-original{suffix}").write_text(old)
        n = 1
    safe = re.sub(r"[^\w.-]", "_", tag)[:40]
    (d / f"{n:04d}-{safe}{suffix}").write_text(new)


class Txn:
    """A change touching several files: kept together or undone together."""

    def __init__(self, cfg: "Config"):
        self.cfg = cfg
        self.old: dict[Path, Optional[str]] = {}

    def write(self, path: Path, text: str) -> None:
        if path not in self.old:
            self.old[path] = path.read_text() if path.exists() else None
        path.write_text(text)

    def rollback(self) -> None:
        for p, t in self.old.items():
            if t is not None:
                p.write_text(t)

    def commit(self, tag: str) -> None:
        for p, t in self.old.items():
            if p.exists():
                record_version(self.cfg, str(p.relative_to(self.cfg.workdir)), t,
                               p.read_text(), tag)

# ---------------------------------------------------------------- shared.h edits

def _max_uid(lines: list[str]) -> int:
    return max([int(m.group(1)) for l in lines if (m := UNIT_RE.match(l))] or [0])


def disable_units(text: str, label: str, why: str, kinds=None) -> tuple[str, int]:
    """Switch off shared.h declarations with this label (#if 0), like the header
    repair does. Returns (text, how many)."""
    lines = text.split("\n")
    n = 0
    for u in sorted(_parse_units(lines), key=lambda u: -u["start"]):
        if u["label"] != label or (kinds and u["kind"] not in kinds):
            continue
        s, e = u["start"], u["end"]
        if s + 1 < len(lines) and lines[s + 1].startswith("#if 0"):
            continue
        lines.insert(e, "#endif")
        lines.insert(s + 1, f"#if 0 // [{why}]")
        n += 1
    return "\n".join(lines), n


def add_const_unit(text: str, name: str, spelling: str) -> str:
    if re.search(rf"\bconstexpr auto {re.escape(name)}\b", text):
        return text
    lines = text.split("\n")
    uid = _max_uid(lines) + 1
    unit = [f"//@unit {uid} const {name}", f"constexpr auto {name} = {spelling};"]
    if "// ==== named constants ====" in lines:
        i = lines.index("// ==== named constants ====") + 1
    else:
        i = next((k for k, l in enumerate(lines) if l.startswith("// ==== forward")), len(lines))
        lines[i:i] = ["// ==== named constants ====", ""]
        i += 1
    lines[i:i] = unit
    return "\n".join(lines)


def strip_disabled(text: str) -> str:
    """shared.h without the #if 0 ... #endif blocks the repairs switched off."""
    out, skip = [], 0
    for l in text.split("\n"):
        if l.startswith("#if 0"):
            skip += 1
            continue
        if skip and l.startswith("#endif"):
            skip -= 1
            continue
        if not skip:
            out.append(l)
    return "\n".join(out)


_LAYOUTS: dict = {}


def struct_layouts(cfg: "Config") -> dict:
    """{struct name: {"size", "fields": [(byte offset, name, type, size)], "label"}}
    for the structs defined (and switched on) in shared.h, from libclang."""
    try:
        key = (str(cfg.shared_h), cfg.shared_h.stat().st_mtime_ns)
    except OSError:
        return {}
    if _LAYOUTS.get("key") == key:
        return _LAYOUTS["data"]
    out: dict = {}
    try:
        cx = _load_libclang(cfg)
        tu = cx.Index.create().parse(str(cfg.shared_h),
                                     args=_libclang_args(cfg) + ["-x", "c++-header", "-w"])
        for c in tu.cursor.get_children():
            if c.location.file is None or c.location.file.name != str(cfg.shared_h):
                continue
            rec, name = None, None
            if c.kind.name in RECORD_KIND_NAMES and c.is_definition() and not _anon(c):
                rec, name = c, c.spelling
            elif c.kind.name == "TYPEDEF_DECL":
                d = c.underlying_typedef_type.get_canonical().get_declaration()
                if d.kind.name in RECORD_KIND_NAMES and _anon(d) and d.is_definition():
                    rec, name = d, c.spelling
            if rec is None or name in out:
                continue
            fields = []
            for f in rec.get_children():
                if f.kind.name == "FIELD_DECL":
                    off = f.get_field_offsetof()
                    fields.append((off // 8 if off >= 0 else -1, f.spelling,
                                   f.type.get_canonical().spelling, f.type.get_size()))
            out[name] = {"size": rec.type.get_size(), "fields": fields,
                         "union": rec.kind.name == "UNION_DECL"}
    except Exception:
        out = {}
    _LAYOUTS.update(key=key, data=out)
    return out


# ---------------------------------------------------------------- behaviour signature

_SIG_SKIP = re.compile(r"^(CONCAT\d+|SUB\d+|ZEXT\d+|SEXT\d+|CARRY\d*|SCARRY\d*|SBORROW\d*|"
                       r"NEON_\w+|u?int\d+_t|size_t|undefined\d*|u?long|u?char|u?short|uint|"
                       r"byte|sbyte|longlong|ulonglong|code|word|dword|qword|"
                       r"_*stack_chk_\w*|__security_\w+|_mcount)$")


def call_counts(code: str, own: set[str], rename: Optional[dict] = None) -> dict[str, int]:
    """How often each function is called (library names without leading _)."""
    toks = tokens(code)
    out: dict[str, int] = {}
    for i, (k, t, s, e) in enumerate(toks):
        if k != "ident" or i + 1 >= len(toks) or toks[i + 1][1] != "(":
            continue
        if t in CPP_KEYWORDS or t in own or _SIG_SKIP.match(t):
            continue
        if i and toks[i - 1][1] in (".", "->"):
            continue
        if i and toks[i - 1][1] == ")" and False:
            continue
        name = (rename or {}).get(t, t).lstrip("_")
        out[name] = out.get(name, 0) + 1
    return out


def missing_calls(pseudo_calls: dict, code_calls: dict) -> dict[str, tuple[int, int]]:
    return {n: (c, code_calls.get(n, 0)) for n, c in pseudo_calls.items()
            if code_calls.get(n, 0) < c}


# ---------------------------------------------------------------- side-by-side tests

_SCALARS = {
    "int": "i32", "int32_t": "i32", "signed int": "i32", "signed": "i32",
    "uint": "u32", "unsigned int": "u32", "unsigned": "u32", "uint32_t": "u32",
    "undefined4": "u32", "dword": "u32",
    "short": "i16", "int16_t": "i16", "ushort": "u16", "unsigned short": "u16",
    "uint16_t": "u16", "undefined2": "u16", "word": "u16",
    "char": "i8", "signed char": "i8", "int8_t": "i8", "sbyte": "i8",
    "uchar": "u8", "unsigned char": "u8", "uint8_t": "u8", "byte": "u8",
    "undefined1": "u8", "undefined": "u8", "bool": "b",
    "long": "i64", "long long": "i64", "longlong": "i64", "int64_t": "i64",
    "ulong": "u64", "unsigned long": "u64", "unsigned long long": "u64",
    "ulonglong": "u64", "uint64_t": "u64", "undefined8": "u64", "size_t": "u64",
    "qword": "u64", "float": "f32", "double": "f64",
}


def scalar_kind(t: str) -> Optional[str]:
    return _SCALARS.get(" ".join(t.replace("const", " ").split()))


_SAN: dict = {}


def sanitizer_flags(cfg: "Config") -> list[str]:
    """-fsanitize flags this compiler can build and run, or [] if none work."""
    if "flags" in _SAN:
        return _SAN["flags"]
    _SAN["flags"] = []
    d = cfg.workdir / "improve" / "tmp"
    d.mkdir(parents=True, exist_ok=True)
    src = d / "san_probe.cpp"
    src.write_text("int main(){return 0;}\n")
    for flags in (["-fsanitize=address,undefined"], ["-fsanitize=undefined"]):
        try:
            r = subprocess.run([cfg.cxx, *flags, str(src), "-o", str(d / "san_probe")],
                               capture_output=True, text=True, timeout=120)
            if r.returncode == 0 and subprocess.run([str(d / "san_probe")],
                                                    timeout=30).returncode == 0:
                _SAN["flags"] = flags
                break
        except Exception:
            pass
    return _SAN["flags"]


_GEN_CPP = r"""
namespace dp_test {
uint64_t s = 88172645463325252ull;
uint64_t rnd() { s ^= s << 13; s ^= s >> 7; s ^= s << 17; return s; }
const uint64_t EDGE[] = {0, 1, ~0ull, 2, 3, 10, 100, 0x7f, 0x80, 0xff, 0x100, 0x7fff,
                         0x8000, 0xffff, 0x7fffffffull, 0x80000000ull, 0xffffffffull,
                         0x7fffffffffffffffull, 0x8000000000000000ull, 0xfffffffeull};
const double FEDGE[] = {0.0, -0.0, 1.0, -1.0, 0.5, -2.5, 100.0, 1e10, -1e-10, 3.14159};
const int NE = sizeof(EDGE) / sizeof(EDGE[0]), NF = sizeof(FEDGE) / sizeof(FEDGE[0]);
uint64_t ival(int i, int j) { return i < 400 ? EDGE[(i * 7 + j * 13 + i / NE) % NE] : rnd(); }
double fval(int i, int j) {
    return i < 400 ? FEDGE[(i * 7 + j * 3 + i / NF) % NF]
                   : ((double)(rnd() % 2000000) / 1000.0 - 1000.0);
}
template <class T> bool same(T a, T b) { return a == b; }
bool same(double a, double b) {
    return a == b || (a != a && b != b) || std::fabs(a - b) <= 1e-6 * std::fmax(1.0, std::fabs(b));
}
bool same(float a, float b) { return same((double)a, (double)b); }
}
"""


def _gen_expr(kind: str, j: int) -> str:
    if kind in ("f32", "f64"):
        return f"dp_test::fval(i, {j})"
    if kind == "b":
        return f"(dp_test::ival(i, {j}) & 1)"
    return f"dp_test::ival(i, {j})"


def _print_expr(kind: str, v: str) -> tuple[str, str]:
    if kind in ("f32", "f64"):
        return "%g", f"(double)({v})"
    return "%lld", f"(long long)({v})"


def run_harness(cfg: "Config", tag: str, code: str, timeout=30) -> tuple[str, str]:
    """Compile and run a test program. ('ok'|'fail'|'nobuild'|'timeout'|'ub', output)."""
    d = cfg.workdir / "improve" / "tmp"
    d.mkdir(parents=True, exist_ok=True)
    src, exe = d / f"{tag}.cpp", d / f"{tag}.bin"
    src.write_text(code)
    san = sanitizer_flags(cfg)
    cmd = [cfg.cxx, f"-std={cfg.std}", "-O1", "-w", f"-I{cfg.workdir}", *san,
           *[f for f in cfg.extra_flags if f.startswith(("-I", "-D", "-isysroot"))],
           str(src), "-o", str(exe)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return "nobuild", "compile timed out"
    if r.returncode != 0:
        return "nobuild", r.stderr[-2000:]
    env = {**os.environ, "UBSAN_OPTIONS": "print_stacktrace=0",
           "ASAN_OPTIONS": "detect_leaks=0"}
    try:
        r = subprocess.run([str(exe)], capture_output=True, text=True, timeout=timeout,
                           env=env)
    except subprocess.TimeoutExpired:
        return "timeout", ""
    out = (r.stdout + r.stderr)[-3000:]
    if "current.cpp:" in out and ("runtime error" in out or "AddressSanitizer" in out):
        return "ub", out
    return ("ok" if r.returncode == 0 else "fail"), out


def pure_pseudo(pseudo: str) -> bool:
    """Ghidra's version only computes from its arguments: no calls, globals,
    pointers or memory."""
    body = strip_comments(pseudo)
    i = body.find("{")
    if i < 0:
        return False
    inner = body[i:]
    if re.search(r"\b(DAT|PTR|_DAT|s_|u_)\w*|->|\[|&|\*\s*\(|\*\s*[A-Za-z_]", inner):
        return False
    return not call_counts(inner, set())


def difftest(cfg: "Config", rec: "FuncRecord", text: str, pseudo: Optional[str]) -> dict:
    """Run this function and Ghidra's own version side by side on many inputs.
    {"status": pass | fail | ub | untestable, "detail": ...}"""
    if not pseudo or not pure_pseudo(pseudo):
        return {"status": "untestable", "detail": "not a pure function"}
    ph = parse_header(pseudo[:pseudo.find("{")])
    ch = parse_header(tu_split(text)[0])
    if not ph or not ch or len(ph[2]) != len(ch[2]):
        return {"status": "untestable", "detail": "signatures don't line up"}
    pk = [scalar_kind(t) for t, _ in ph[2]]
    ck = [scalar_kind(t) for t, _ in ch[2]]
    rk, crk = scalar_kind(ph[0]), scalar_kind(ch[0])
    if None in pk or None in ck or not rk or not crk:
        return {"status": "untestable", "detail": "not scalar"}
    lines = text.split("\n")
    if lines and lines[0].startswith(INCLUDE_LINE):
        lines[0] = "// " + lines[0]
    args = [f"a{j}" for j in range(len(pk))]
    decl = "".join(f"        auto a{j} = {_gen_expr(k, j)};\n" for j, k in enumerate(pk))
    fmt, vals = [], []
    for a, k in zip(args, pk):
        f_, v = _print_expr(k, a)
        fmt.append(f_)
        vals.append(v)
    gf, gv = _print_expr(crk, "got")
    wf, wv = _print_expr(rk, "want")
    ref = deghidra_text(pseudo)
    code = (f'{INCLUDE_LINE}\n#include <cmath>\n#include <cstdio>\n{_GEN_CPP}\n'
            f'#line 1 "current.cpp"\n' + "\n".join(lines) + "\n"
            f'#line 1 "ghidra.cpp"\nnamespace ghidra_ref {{\n{ref}\n}}\n'
            f'#line 1 "harness.cpp"\nint main() {{\n    for (int i = 0; i < 3000; i++) {{\n'
            f"{decl}"
            f"        auto got = ::{ch[1]}({', '.join(f'({t}){a}' for (t, _), a in zip(ch[2], args))});\n"
            f"        auto want = ghidra_ref::{ph[1]}({', '.join(f'({t}){a}' for (t, _), a in zip(ph[2], args))});\n"
            f"        if (!dp_test::same(got, (decltype(got))want)) {{\n"
            f'            std::printf("MISMATCH args({", ".join(fmt)}) got {gf} want {wf}\\n", '
            f"{', '.join(vals + [gv, wv])});\n            return 3;\n        }}\n    }}\n"
            f"    return 0;\n}}\n")
    status, out = run_harness(cfg, "diff_" + Path(rec.file).stem, code)
    if status == "ok":
        return {"status": "pass", "detail": ""}
    if status == "fail" and "MISMATCH" in out:
        return {"status": "fail", "detail": out[out.find("MISMATCH"):].split("\n")[0]}
    if status == "ub":
        m = re.search(r"current\.cpp:(\d+):\d+: runtime error: ([^\n]*)", out)
        return {"status": "ub", "detail": m.group(0) if m else out[:300],
                "line": int(m.group(1)) if m else 0}
    return {"status": "untestable", "detail": status}


# Hand-written copies of standard functions, found by behaviour: the function is
# run against the real one on many inputs and replaced only if it always agrees.
_STD_TESTS = {
    "strlen": ("P", "for (int t = 0; t < 2000; t++) { int n = rnd() % 64; char b[80];"
                    " for (int k = 0; k < 80; k++) b[k] = (char)(1 + rnd() % 250); b[n] = 0;"
                    " auto got = CALL(b); if ((unsigned long long)got != (unsigned long long)strlen(b)) return 3; }",
               "return (RET)strlen((const char *)A0);"),
    "strcmp": ("PP", "for (int t = 0; t < 3000; t++) { char x[8], y[8]; int n = rnd() % 7, m = rnd() % 7;"
                     " for (int k = 0; k < 8; k++) { x[k] = 'a' + rnd() % 2; y[k] = 'a' + rnd() % 2; }"
                     " x[n] = 0; y[m] = 0; auto got = CALL(x, y);"
                     " if ((long long)got != (long long)strcmp(x, y)) return 3; }",
               "return (RET)strcmp((const char *)A0, (const char *)A1);"),
    "memcmp": ("PPN", "for (int t = 0; t < 3000; t++) { unsigned char x[8], y[8]; size_t n = rnd() % 9;"
                      " for (int k = 0; k < 8; k++) { x[k] = 'a' + rnd() % 2; y[k] = 'a' + rnd() % 2; }"
                      " auto got = CALL(x, y, n);"
                      " if ((long long)got != (long long)memcmp(x, y, n)) return 3; }",
               "return (RET)memcmp((const void *)A0, (const void *)A1, (size_t)A2);"),
    "memset": ("PNN", "for (int t = 0; t < 2000; t++) { unsigned char x[64], y[64];"
                      " for (int k = 0; k < 64; k++) x[k] = y[k] = (unsigned char)rnd();"
                      " size_t n = rnd() % 40; int v = (int)(rnd() % 600);"
                      " RETCHK(CALL(x, v, n), x); memset(y, v, n); if (memcmp(x, y, 64)) return 3; }",
               "memset((void *)A0, (int)A1, (size_t)A2);"),
    "memmove": ("PPN", "for (int t = 0; t < 3000; t++) { unsigned char x[128], y[128];"
                       " for (int k = 0; k < 128; k++) x[k] = y[k] = (unsigned char)rnd();"
                       " size_t n = rnd() % 48, d = rnd() % 64, s = rnd() % 64;"
                       " RETCHK(CALL(x + d, x + s, n), x + d); memmove(y + d, y + s, n);"
                       " if (memcmp(x, y, 128)) return 3; }",
                "memmove((void *)A0, (const void *)A1, (size_t)A2);"),
    "strcpy": ("PP", "for (int t = 0; t < 2000; t++) { char s[40], x[64], y[64]; int n = rnd() % 32;"
                     " for (int k = 0; k < 40; k++) s[k] = (char)(1 + rnd() % 250); s[n] = 0;"
                     " for (int k = 0; k < 64; k++) x[k] = y[k] = (char)rnd();"
                     " RETCHK(CALL(x, s), x); strcpy(y, s); if (memcmp(x, y, 64)) return 3; }",
               "strcpy((char *)A0, (const char *)A1);"),
}


def _shape(params) -> str:
    out = ""
    for t, _ in params:
        if "*" in t or "[" in t:
            out += "P"
        elif scalar_kind(t) and scalar_kind(t)[0] in "iu":
            out += "N"
        else:
            return "?"
    return out


def stdlib_match(cfg: "Config", rec: "FuncRecord", text: str) -> Optional[tuple[str, str]]:
    """(standard function, new body line) if this function behaves exactly like one."""
    h = parse_header(tu_split(text)[0])
    if not h or not all(n for _, n in h[2]):
        return None
    ret, name, params = h
    shape = _shape(params)
    void_ret = ret.strip() == "void"
    ptr_ret = "*" in ret
    lines = text.split("\n")
    if lines and lines[0].startswith(INCLUDE_LINE):
        lines[0] = "// " + lines[0]
    for std, (want, test, body) in _STD_TESTS.items():
        if shape != want:
            continue
        returns_value = std in ("strlen", "strcmp", "memcmp")
        if returns_value and (void_ret or ptr_ret):
            continue
        if not returns_value and not (void_ret or ptr_ret):
            continue
        call = f"[&](auto... a) {{ return ::{name}(a...); }}"
        t = test.replace("CALL(", "dp_call(")
        t = t.replace("RETCHK(", "dp_ret(")
        code = (f"{INCLUDE_LINE}\n#include <cstring>\n#include <cstdint>\n"
                f"namespace {{ uint64_t s_ = 88172645463325252ull;\n"
                f"uint64_t rnd() {{ s_ ^= s_ << 13; s_ ^= s_ >> 7; s_ ^= s_ << 17; return s_; }} }}\n"
                f'#line 1 "current.cpp"\n' + "\n".join(lines) + "\n"
                f'#line 1 "harness.cpp"\n'
                f"template <class... A> auto dp_call(A... A_) {{ "
                f"auto t_ = std::make_tuple(A_...); (void)t_; return {call}("
                + ", ".join(f"({pt})std::get<{j}>(t_)" for j, (pt, _) in enumerate(params))
                + f"); }}\n"
                + ("template <class R, class D> bool dp_ret_ok(R r, D d) { return (void *)r == (void *)d; }\n"
                   if ptr_ret else "")
                + "int main() {\n"
                + ("#define dp_ret(EXPR, DEST) do { if (!dp_ret_ok((EXPR), (DEST))) return 4; } while (0)\n"
                   if ptr_ret else "#define dp_ret(EXPR, DEST) do { EXPR; } while (0)\n")
                + f"    {t}\n    return 0;\n}}\n")
        code = code.replace("#include <cstdint>\n", "#include <cstdint>\n#include <tuple>\n", 1)
        status, _ = run_harness(cfg, f"std_{std}_" + Path(rec.file).stem, code)
        if status == "ok":
            b = body
            for j, (_, pn) in enumerate(params):
                b = b.replace(f"A{j}", pn)
            b = b.replace("(RET)", f"({ret})")
            if ptr_ret:
                b += f" return ({ret}){params[0][1]};"
            return std, b
    return None

# ---------------------------------------------------------------- the model's small tasks

PLAN_SYS = ("You plan ONE small edit to a C++ function. You get the function's goal, "
            "notes from earlier attempts, the task, and the lines to change (marked >>). "
            "In ONE sentence say exactly what to change on those lines. Do not repeat an "
            "approach the notes say failed. Output no code.")
LOCATE_SYS = ("You find the line in a C++ function where a problem is. Reply with ONLY "
              "the line number, then one short sentence saying why.")
NAMES_SYS = ("You choose names for things in C++ code that was decompiled. Reply with "
             "ONLY lines of the form: old -> new. One line per item, nothing else. Names "
             "say what the thing is or does; never use product, company or person names.")
NAME_STYLE = {"variable": "lowerCamelCase", "field": "lowerCamelCase",
              "global": "lowerCamelCase", "function": "lowerCamelCase, starting with a verb",
              "constant": "SCREAMING_SNAKE_CASE (or NONE if it isn't a meaningful constant)",
              "module": "short snake_case (one or two words)"}


class ImproveCtx:
    def __init__(self, cfg: "Config", records: dict, P: Optional["Paths"] = None,
                 checks: Optional[set] = None):
        self.cfg, self.records, self.P = cfg, records, P
        self.state = ImproveState(cfg)
        self.export, self.index = _load_pseudocode(cfg)
        self.ghidra_to_final = {v.get("ghidra"): k for k, v in self.index.items()}
        self.model = cfg.fix_model_used or None
        self.checks = checks
        self.blocklist = load_blocklist(P) if P else []
        self._tl = threading.local()
        self._count_lock = threading.Lock()
        self.last_plan = ""
        self._arity = None
        self.stats: dict[str, dict[str, int]] = {}

    @property
    def last_plan(self) -> str:
        return getattr(self._tl, "plan", "")

    @last_plan.setter
    def last_plan(self, v: str) -> None:
        self._tl.plan = v

    # -- bookkeeping
    def count(self, check: str, what: str, n=1):
        with self._count_lock:
            d = self.stats.setdefault(check, {})
            d[what] = d.get(what, 0) + n

    def text(self, rec) -> str:
        return (self.cfg.workdir / rec.file).read_text()

    def pseudo(self, rec) -> Optional[str]:
        return _pseudo_for(rec, self.export, self.index)

    def pseudo_calls(self, rec) -> Optional[dict]:
        p = self.pseudo(rec)
        if not p:
            return None
        i = p.find("{")
        return call_counts(p[i:] if i >= 0 else p, {rec.name}, self.ghidra_to_final)

    def code_calls(self, rec, text) -> dict:
        _, body = tu_split(text)
        return call_counts(body, {rec.name, re.sub(r"__dup\d+$", "", rec.name)})

    def compiling(self):
        return [(m, r) for m, r in self.records.items()
                if r.compiles and not r.quarantined and not getattr(r, "duplicate_of", "")]

    # -- the model
    def ask(self, system: str, user: str, max_out=300) -> Optional[str]:
        if not self.model:
            return None
        # every task gets the room the context leaves: a thinking model capped at a
        # few hundred tokens is cut off before it writes anything, every time
        max_out = max(max_out, answer_room(self.cfg.ctx, len(system) + len(user)))
        return self.cfg.client.chat(self.model, [{"role": "system", "content": system},
                                                 {"role": "user", "content": user}],
                                    max_out=max_out, temperature=0.2,
                                    timeout=self.cfg.model_timeout_s, fatal=False)

    def goal(self, rec, text) -> str:
        g, _ = read_notes(self.cfg, rec.file)
        if g or not self.model:
            return g
        _, body = tu_split(text)
        cap = min(6000, prompt_chars(self.cfg.ctx) - 500)
        g = self.ask(FIX_GOAL_SYS, f"Function {rec.name}:\n```cpp\n{body[:cap]}\n```", 160) or ""
        g = " ".join(g.split())[:400]
        if g:
            write_note(self.cfg, rec.file, goal=g)
        return g

    def line_edit(self, rec, text: str, line_no: int, task: str, span=None,
                  context: str = "") -> Optional[str]:
        """Plan one small edit, then rewrite only the lines it covers (1-based)."""
        lines = text.split("\n")
        if span is None:
            span = _edit_span(lines, line_no)
        if not span:
            return None
        lo, hi = span
        window = "\n".join(lines[lo:hi])
        goal = self.goal(rec, text)
        _, notes = read_notes(self.cfg, rec.file)
        shown = numbered(lines, lo - 3, hi + 3, (lo, hi))
        info = (f"Function goal: {goal or '(unknown)'}\n"
                + (f"Notes from earlier attempts:\n" + "\n".join(f"- {n}" for n in notes) + "\n"
                   if notes else "")
                + f"Task: {task}\n" + (f"{context}\n" if context else ""))
        plan = self.ask(PLAN_SYS, info + f"\nLines:\n{shown}", 160) or ""
        self.last_plan = " ".join(plan.split())[:300]
        reply = self.ask(FIX_EDIT_SYS, info + f"Plan: {self.last_plan}\n\n"
                         f"Replace ONLY these line(s):\n```cpp\n{window}\n```",
                         min(900, max(200, (hi - lo) * 60)))
        if not reply:
            return None
        new, _ = parse_reply(reply)
        if new is None:
            new = reply.strip()
        new = "\n".join(l for l in new.split("\n")
                        if not l.lstrip().startswith("#include")).rstrip()
        if not new.strip() or new.strip() == window.strip():
            return None
        if brace_balance(new) != brace_balance(window):
            return None
        indent = re.match(r"[ \t]*", lines[lo]).group(0)
        nl = new.split("\n")
        if indent and nl and not nl[0][:1].isspace():
            nl = [indent + x if x.strip() else x for x in nl]
        lines[lo:hi] = nl
        return "\n".join(lines)

    def locate(self, rec, text: str, issue: str, context: str = "") -> Optional[int]:
        lines = text.split("\n")
        # as much of the function as fits the context (it reads, it doesn't write)
        budget, hi = prompt_chars(self.cfg.ctx) - len(issue) - len(context) - 300, 0
        while hi < len(lines) and budget - len(lines[hi]) - 9 > 0:
            budget -= len(lines[hi]) + 9
            hi += 1
        shown = numbered(lines, 0, max(1, hi))
        reply = self.ask(LOCATE_SYS, f"Problem: {issue}\n{context}\n\nFunction:\n{shown}", 80)
        m = re.search(r"\d+", reply or "")
        if m and 2 <= int(m.group()) <= len(lines):
            return int(m.group())
        return None

    def names(self, kind: str, items: list[tuple[str, list[str]]], extra="") -> dict:
        """Ask for names: items = [(current name, [lines where it's used])]."""
        if not items or not self.model:
            return {}
        body = "\n".join(f"- {old}\n" + "\n".join(f"    {u.strip()[:160]}" for u in uses[:4])
                         for old, uses in items)
        reply = self.ask(NAMES_SYS, f"Name these {kind}s. Style: {NAME_STYLE[kind]}.\n"
                         f"{extra}\n{body}", 40 + 30 * len(items)) or ""
        out = {}
        want = {o for o, _ in items}
        for line in reply.splitlines():
            m = re.match(r"\s*[-*]?\s*`?([\w:]+)`?\s*(?:->|=>|:)\s*`?([A-Za-z_]\w*)`?", line)
            if m and m.group(1) in want and m.group(2).upper() != "NONE":
                out[m.group(1)] = m.group(2)
        return out


# ---------------------------------------------------------------- the gate

def gate_change(ctx: ImproveCtx, rec, old: str, new: str, behaviour=True,
                allow_shrink=False) -> tuple[bool, str]:
    """Write `new`; keep it only if it compiles and still behaves like before.
    On failure the old text is back on disk."""
    path = ctx.cfg.workdir / rec.file
    if new == old:
        return False, "no change"
    if not allow_shrink and len(re.sub(r"\s+", "", new)) < 0.5 * len(re.sub(r"\s+", "", old)) \
            and len(old) > 300:
        return False, "removes too much of the function"
    path.write_text(new)
    try:
        ok, err, _ = compile_tu(ctx.cfg, rec.file)
    except StopRun:
        path.write_text(old)                  # never leave an unchecked change behind
        raise
    why = ""
    if not ok:
        first = next((l for l in err.splitlines() if "error" in l), err[:200])
        why = "doesn't compile: " + first.split("error:", 1)[-1].strip()[:160]
    elif behaviour:
        pc = ctx.pseudo_calls(rec)
        if pc:
            before = sum(c - h for c, h in missing_calls(pc, ctx.code_calls(rec, old)).values())
            after = sum(c - h for c, h in missing_calls(pc, ctx.code_calls(rec, new)).values())
            if after > before:
                why = "drops a call Ghidra's version makes"
        if not why:
            t_old = cached_difftest(ctx, rec, old)
            if t_old["status"] == "pass":
                t_new = cached_difftest(ctx, rec, new)
                if t_new["status"] != "pass":
                    why = "behaves differently from Ghidra's version: " + t_new.get("detail", "")
    if why:
        path.write_text(old)
        return False, why
    return True, ""


def cached_difftest(ctx: ImproveCtx, rec, text: str) -> dict:
    cache = ctx.state.g("difftest", {})
    key = f"{rec.mangled}:{text_sha(text)}"
    if key not in cache:
        cache[key] = difftest(ctx.cfg, rec, text, ctx.pseudo(rec))
    return cache[key]


# ---------------------------------------------------------------- per-function checks
#
# Each check: detect(ctx, rec, text) -> findings; fix(ctx, rec, text, finding) ->
# new text or None. "model": the fix needs the model; "behaviour": the fix is
# gated on behaving like Ghidra's version (renames / pure rewrites are too).

def _finding(check, line, msg, weight, key="", **data):
    return {"check": check, "line": line, "msg": msg, "weight": weight,
            "key": f"{check}:{key or msg}", "data": data}


def _line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


# -- leftover decompiler names (param_1, local_28, uVar3 ...)
LOCAL_LEFTOVER = re.compile(r"^(param_\d+|local_[0-9a-fA-F]+|[a-z]{1,3}Var\d+|in_\w+|"
                            r"extraout_\w+|unaff_\w+|stack0x\w+|auStack_\w+|abStack_\w+)$")


def detect_names(ctx, rec, text):
    _, body = tu_split(text)
    left = sorted({t for k, t, _, _ in tokens(body) if k == "ident" and LOCAL_LEFTOVER.match(t)})
    return [_finding("names", 0, f"decompiler names left: {', '.join(left[:12])}",
                     1 + len(left) * 0.5, key="names", names=left)] if left else []


def fix_names(ctx, rec, text, f):
    lines = text.split("\n")
    items = []
    for n in f["data"]["names"][:12]:
        uses = [l for l in lines if re.search(rf"\b{re.escape(n)}\b", l)]
        items.append((n, uses))
    goal = ctx.goal(rec, text)
    mapping = ctx.names("variable", items, f"They're local variables / parameters of a "
                                           f"function whose goal is: {goal}")
    taken = ident_set(text) | header_idents(ctx.cfg)
    clean, used = {}, set()
    for old, new in mapping.items():
        if is_ident(new) and new not in taken and new not in used and not LOCAL_LEFTOVER.match(new):
            clean[old] = new
            used.add(new)
    if not clean:
        return None
    new_text, _ = rename_idents(text, clean)
    if not alpha_equivalent(text, new_text, clean):
        return None
    ctx.last_plan = "rename " + ", ".join(f"{a}->{b}" for a, b in clean.items())
    return new_text


_HDR_IDENTS: dict = {}


def header_idents(cfg) -> set:
    try:
        key = cfg.shared_h.stat().st_mtime_ns
    except OSError:
        return set()
    if _HDR_IDENTS.get("key") != key:
        _HDR_IDENTS.update(key=key, ids=ident_set(cfg.shared_h.read_text()))
    return _HDR_IDENTS["ids"]


# -- Ghidra helper notation left in the code (CONCAT44, ZEXT48, SUB84 ...)
HELPER_CALL = re.compile(r"^(CONCAT|ZEXT|SEXT|SUB)(\d)(\d)$")


def _helper_rewrite(name, args):
    m = HELPER_CALL.match(name)
    if not m:
        return None
    kind, a, b = m.group(1), int(m.group(2)), int(m.group(3))
    sizes = {1, 2, 4, 8}
    if kind == "ZEXT" and len(args) == 1 and a in sizes and b in sizes:
        return f"((uint{8 * b}_t)(uint{8 * a}_t)({args[0]}))"
    if kind == "SEXT" and len(args) == 1 and a in sizes and b in sizes:
        return f"((int{8 * b}_t)(int{8 * a}_t)({args[0]}))"
    if kind == "CONCAT" and len(args) == 2 and (a + b) in (2, 4, 8) and a in sizes and b in sizes:
        t = f"uint{8 * (a + b)}_t"
        return (f"(({t})(({t})(uint{8 * a}_t)({args[0]}) << {8 * b}) | "
                f"({t})(uint{8 * b}_t)({args[1]}))")
    if kind == "SUB" and len(args) == 2 and a in sizes and b in sizes:
        try:
            off = int(args[1], 0)
        except ValueError:
            return None
        return f"((uint{8 * b}_t)((uint{8 * a}_t)({args[0]}) >> {8 * off}))"
    return None


def detect_helpers(ctx, rec, text):
    _, body = tu_split(text)
    found = sorted({t for k, t, _, _ in tokens(body) if k == "ident" and HELPER_CALL.match(t)})
    return [_finding("helpers", 0, f"Ghidra helper notation left: {', '.join(found)}", 2,
                     key="helpers")] if found else []


def fix_helpers(ctx, rec, text, f):
    head, body = tu_split(text)
    new_body, n = replace_calls(body, lambda t: bool(HELPER_CALL.match(t)), _helper_rewrite)
    return text.replace(body, new_body, 1) if n else None


# -- divide-by-multiplying: (uint64_t)x * 0xaaaaaaab >> 0x21  ->  x / 3
MAGIC_DIV = re.compile(r"\(\s*\(\s*(?:uint64_t|ulong|ulonglong|unsigned long(?: long)?)\s*\)\s*"
                       r"([A-Za-z_]\w*)\s*\*\s*(0x[0-9a-fA-F]+|\d+)(?:[uUlL]*)\s*\)\s*>>\s*"
                       r"(0x[0-9a-fA-F]+|\d+)")


def _divisor(mult: int, shift: int) -> Optional[int]:
    import random
    if not (0 < mult < 2 ** 33 and 32 <= shift < 64):
        return None
    d = round(2 ** shift / mult)
    if d < 2:
        return None
    rng = random.Random(mult ^ shift)
    xs = [0, 1, d - 1, d, d + 1, 2 ** 32 - 1, 2 ** 31, 2 ** 31 - 1] + \
         [rng.randrange(2 ** 32) for _ in range(20000)] + \
         [k * d + o for k in (rng.randrange(2 ** 32 // d) for _ in range(2000)) for o in (-1, 0, 1)]
    for x in xs:
        if 0 <= x < 2 ** 32 and (x * mult) >> shift != x // d:
            return None
    return d


def _unsigned32_vars(text: str) -> set:
    return set(re.findall(r"\b(?:uint32_t|uint|unsigned int|unsigned|undefined4|dword)\s+"
                          r"\**\s*([A-Za-z_]\w*)", text))


def detect_magic_div(ctx, rec, text):
    u32 = _unsigned32_vars(text)
    out = []
    for m in MAGIC_DIV.finditer(text):
        if m.group(1) in u32 and _divisor(int(m.group(2), 0), int(m.group(3), 0)):
            out.append(_finding("magic_div", _line_of(text, m.start()),
                                "division written as multiply-and-shift", 2,
                                key=m.group(0)))
    return out


def fix_magic_div(ctx, rec, text, f):
    u32 = _unsigned32_vars(text)

    def rep(m):
        d = _divisor(int(m.group(2), 0), int(m.group(3), 0))
        return f"((uint64_t)({m.group(1)}) / {d})" if d and m.group(1) in u32 else m.group(0)
    new = MAGIC_DIV.sub(rep, text)
    return new if new != text else None


# -- stack protector / compiler-inserted code
STACK_GUARD = re.compile(r"__?stack_chk_guard|___stack_chk_guard|__security_cookie")
STACK_FAIL = re.compile(r"\b_*stack_chk_fail\s*\(|\b__security_check_cookie\s*\(|\b_mcount\s*\(")


def detect_stack(ctx, rec, text):
    return [_finding("stack_guard", 0, "compiler-inserted stack protector code", 2,
                     key="stack")] if STACK_GUARD.search(text) or STACK_FAIL.search(text) else []


def fix_stack(ctx, rec, text, f):
    lines = text.split("\n")
    guard_vars = set()
    for l in lines:
        m = re.match(r"\s*([A-Za-z_]\w*)\s*=.*(?:stack_chk_guard|security_cookie)", l)
        if m:
            guard_vars.add(m.group(1))
    out, i = [], 0
    while i < len(lines):
        l = lines[i]
        s = l.strip()
        if STACK_GUARD.search(l) and re.match(r"[\w\s\*]*=.*;\s*$", s):
            i += 1
            continue                                  # local = guard;
        if re.match(r"(if|else\s+if)\s*\(", s) and (
                any(re.search(rf"\b{re.escape(v)}\b", s) for v in guard_vars)
                or STACK_GUARD.search(s)):
            j, depth = i, 0                           # the whole if-block
            block = []
            while j < len(lines):
                block.append(lines[j])
                depth += brace_balance(lines[j])
                if depth <= 0 and ("{" in "".join(block) or lines[j].rstrip().endswith(";")):
                    break
                j += 1
            if STACK_FAIL.search("\n".join(block)):
                i = j + 1
                continue
        if STACK_FAIL.search(l) and re.match(r"_*\w+\s*\([^;]*\)\s*;\s*$", s):
            i += 1
            continue
        if any(re.match(rf"(?:[\w\s\*]+\s)?\**{re.escape(v)}\s*;\s*$", s) for v in guard_vars):
            i += 1
            continue                                  # its declaration
        out.append(l)
        i += 1
    new = "\n".join(out)
    return new if new != text else None


# -- compiler warnings
WARN_FLAGS_CLANG = ["-Wall", "-Wextra", "-Wno-unused-parameter", "-Wno-sign-compare",
                    "-Wno-missing-field-initializers", "-Wconditional-uninitialized",
                    "-Wshorten-64-to-32", "-Wno-unused-function"]
WARN_FLAGS_GCC = ["-Wall", "-Wextra", "-Wno-unused-parameter", "-Wno-sign-compare",
                  "-Wno-missing-field-initializers", "-Wno-unused-function"]


def detect_warnings(ctx, rec, text):
    cfg = ctx.cfg
    flags = WARN_FLAGS_CLANG if "clang" in Path(cfg.cxx).name else WARN_FLAGS_GCC
    _pch_flags(cfg)
    with HEADER_LOCK.read():
        cmd = [cfg.cxx, f"-std={cfg.std}", f"-I{cfg.workdir}", "-fsyntax-only", *flags,
               *PIC_FLAGS, *_pch_flags(cfg, rebuild=False), *cfg.extra_flags,
               str(cfg.workdir / rec.file)]
        r = subprocess.run(cmd, capture_output=True, text=True)
    out = []
    name = Path(rec.file).name
    for l in r.stderr.splitlines():
        m = DIAG_RE.match(l.strip())
        if m and m.group("sev") == "warning" and Path(m.group("file")).name == name:
            msg = re.sub(r"\s*\[-W[\w-]+\]$", "", m.group("msg"))
            line = int(m.group("line"))
            src = text.split("\n")[line - 1].strip() if line <= text.count("\n") + 1 else ""
            out.append(_finding("warnings", line, f"warning: {msg}", 2, key=msg + "|" + src))
    return out


def fix_warnings(ctx, rec, text, f):
    lines = text.split("\n")
    ln = f["line"]
    m = re.match(r"warning: unused variable '(\w+)'", f["msg"])
    if m and 0 < ln <= len(lines):
        s = lines[ln - 1].strip()
        if re.fullmatch(rf"[\w\s\*:<>,]+\b{re.escape(m.group(1))}\s*(=\s*[^;()]*)?;", s):
            del lines[ln - 1]                         # nothing else on the line
            ctx.last_plan = f"remove the unused variable {m.group(1)}"
            return "\n".join(lines)
    return ctx.line_edit(rec, text, ln, f"The compiler warns: {f['msg'][9:]}. Fix the "
                                        f"cause without changing what the code does.")


# -- casts that change nothing (from libclang's types)
def _noop_casts(ctx, rec, text) -> list[tuple[int, int]]:
    if not re.search(r"\(\s*[\w\s\*:]+\)\s*[\w(]", text):
        return []
    cfg = ctx.cfg
    try:
        cx = _load_libclang(cfg)
        path = str(cfg.workdir / rec.file)
        tu = cx.Index.create().parse(path, args=_libclang_args(cfg) + ["-w"])
    except Exception:
        return []
    spans = []
    for c in tu.cursor.walk_preorder():
        if c.kind.name != "CSTYLE_CAST_EXPR" or c.location.file is None \
                or c.location.file.name != path:
            continue
        kids = [k for k in c.get_children() if k.kind.is_expression()]
        if not kids:
            continue
        k = kids[-1]
        if c.type.get_canonical().spelling != k.type.get_canonical().spelling:
            continue
        if c.type.kind.name in ("VOID", "TYPEDEF") and c.type.spelling != k.type.spelling:
            continue
        s, e = c.extent.start.offset, k.extent.start.offset
        if 0 <= s < e and re.fullmatch(r"\(\s*[^()]*\)\s*", text[s:e]):
            spans.append((s, e))
    return spans


def detect_casts(ctx, rec, text):
    spans = _noop_casts(ctx, rec, text)
    return [_finding("casts", _line_of(text, spans[0][0]),
                     f"{len(spans)} cast(s) that change nothing", 0.5 * len(spans),
                     key="casts")] if spans else []


def fix_casts(ctx, rec, text, f):
    spans = _noop_casts(ctx, rec, text)
    for s, e in sorted(spans, reverse=True):
        text = text[:s] + text[e:]
    return text if spans else None


# -- pointer arithmetic that is really a struct member
PTR_ARITH = re.compile(r"\*\s*\(\s*(?P<ty>[\w\s]+?)\s*\*\s*\)\s*\(\s*\(\s*(?:char|uchar|byte|"
                       r"uint8_t|int8_t|long|ulong|longlong|ulonglong|uint64_t|int64_t|"
                       r"intptr_t|uintptr_t|size_t|undefined)\s*\**\s*\)\s*(?P<var>[A-Za-z_]\w*)"
                       r"\s*\+\s*(?P<off>0x[0-9a-fA-F]+|\d+)\s*\)")


def _var_struct(text: str, var: str) -> Optional[str]:
    m = re.search(rf"\b(?:struct\s+)?([A-Za-z_]\w*)\s*\*\s*{re.escape(var)}\b", text)
    return m.group(1) if m else None


def _member_for(ctx, text, m) -> Optional[str]:
    s = _var_struct(text, m.group("var"))
    lay = struct_layouts(ctx.cfg).get(s or "")
    if not lay or lay.get("union"):
        return None
    off = int(m.group("off"), 0)
    ty = " ".join(m.group("ty").split())
    for foff, fname, ftype, fsize in lay["fields"]:
        if foff == off and (ftype == ty or scalar_kind(ftype) == scalar_kind(ty) != None):
            return f"{m.group('var')}->{fname}"
    return None


def detect_ptr_arith(ctx, rec, text):
    out = []
    for m in PTR_ARITH.finditer(text):
        known = _member_for(ctx, text, m) is not None
        out.append(_finding("ptr_arith", _line_of(text, m.start()),
                            "pointer arithmetic for a struct member" + ("" if known else
                            " (no matching field yet)"), 1.5 if known else 0.5,
                            key=m.group(0), known=known))
    return out


def fix_ptr_arith(ctx, rec, text, f):
    if not f["data"].get("known"):
        return None

    def rep(m):
        return _member_for(ctx, text, m) or m.group(0)
    new = PTR_ARITH.sub(rep, text)
    return new if new != text else None


# -- goto
def detect_goto(ctx, rec, text):
    out = []
    lines = text.split("\n")
    for i, l in enumerate(lines):
        m = re.search(r"\bgoto\s+(\w+)\s*;", l)
        if m:
            lab = next((j for j, x in enumerate(lines) if re.match(rf"\s*{m.group(1)}\s*:", x)), None)
            out.append(_finding("goto", i + 1, f"goto {m.group(1)}", 1.5,
                                key=f"{m.group(1)}|{l.strip()}", label=lab))
    return out


def fix_goto(ctx, rec, text, f):
    lab = f["data"].get("label")
    if lab is None:
        return None
    lo, hi = sorted((f["line"] - 1, lab))
    lines = text.split("\n")
    while lo > 0 and brace_balance("\n".join(lines[lo:hi + 1])) < 0:
        lo -= 1
    while hi + 1 < len(lines) and brace_balance("\n".join(lines[lo:hi + 1])) > 0:
        hi += 1
    if hi - lo > 30:
        return None
    return ctx.line_edit(rec, text, f["line"], f"Replace '{f['msg']};' and its label with "
                         f"structured code (if/else, a loop, break or continue). Keep exactly "
                         f"the same behaviour.", span=(lo, hi + 1))


# -- behaviour against Ghidra's version
def detect_behaviour(ctx, rec, text):
    out = []
    pc = ctx.pseudo_calls(rec)
    if pc:
        miss = missing_calls(pc, ctx.code_calls(rec, text))
        if miss:
            desc = ", ".join(f"{n} ({c}x in Ghidra's version, {h}x here)" for n, (c, h) in miss.items())
            out.append(_finding("calls", 0, f"calls missing compared with Ghidra's version: {desc}",
                                3, key="calls:" + ",".join(sorted(miss)), missing=sorted(miss)))
    t = cached_difftest(ctx, rec, text)
    if t["status"] == "fail":
        out.append(_finding("difftest", 0, f"behaves differently from Ghidra's version: "
                                           f"{t['detail']}", 5, key="difftest"))
    elif t["status"] == "ub":
        out.append(_finding("sanitizer", t.get("line", 0),
                            f"undefined behaviour: {t['detail']}", 4, key=t["detail"]))
    return out


def fix_behaviour(ctx, rec, text, f):
    if f["check"] == "calls":
        p = ctx.pseudo(rec) or ""
        name = f["data"]["missing"][0]
        ctxt = "\n".join(l for l in p.split("\n") if name in l)[:600]
        task = (f"Ghidra's version of this function calls {name} here:\n{ctxt}\n"
                f"This version doesn't (or calls it fewer times). Add the missing call back.")
        line = ctx.locate(rec, text, task)
        return ctx.line_edit(rec, text, line, task) if line else None
    line = f["line"] or ctx.locate(rec, text, f["msg"])
    if not line:
        return None
    return ctx.line_edit(rec, text, line, f"{f['msg']}. Fix this line so the function "
                                          f"behaves exactly like Ghidra's version.",
                         context="Ghidra's version:\n" + (ctx.pseudo(rec) or "")[:1500])


# -- hand-written copies of standard library functions
def detect_stdlib(ctx, rec, text):
    cache = ctx.state.g("stdlib", {})
    key = f"{rec.mangled}:{text_sha(text)}"
    if key not in cache:
        r = stdlib_match(ctx.cfg, rec, text)
        cache[key] = list(r) if r else None
    r = cache[key]
    if not r or re.search(rf"\b{r[0]}\s*\(", tu_split(text)[1]) and \
            len(tu_split(text)[1]) < 200:
        return []
    return [_finding("stdlib", 0, f"does exactly what {r[0]} does", 3, key=r[0],
                     std=r[0], body=r[1])]


def fix_stdlib(ctx, rec, text, f):
    head, body = tu_split(text)
    new = text[:len(text) - len(body)] + "{\n    " + f["data"]["body"] + "\n}\n"
    ctx.last_plan = f"replace the body with a call to {f['data']['std']}"
    return new


# -- privacy: strings and comments that identify the original program
PRIVACY_STR = re.compile(r"[/\\][A-Za-z0-9._-]+[/\\]|https?://|www\.|@[\w-]+\.\w|\b\d+\.\d+\.\d+|"
                         r"(?i:copyright|\(c\)|©|\b(?:inc|ltd|llc|gmbh|corp|corporation)\b)")


def privacy_hits(text: str, terms: list[str]) -> list[tuple[str, str, int]]:
    """(kind, token text, position) for strings/comments/identifiers that identify."""
    out = []
    low_terms = [t.lower() for t in terms]
    for k, t, s, e in tokens(text):
        if k == "string" and len(t) > 3 and not _FORMAT_STR.search(t):
            if PRIVACY_STR.search(t[1:-1]) or any(x in t.lower() for x in low_terms):
                out.append(("string", t, s))
        elif k == "comment" and (PRIVACY_STR.search(t) or any(x in t.lower() for x in low_terms)):
            out.append(("comment", t, s))
        elif k == "ident" and any(x in t.lower() for x in low_terms):
            out.append(("ident", t, s))
    return out


def detect_privacy(ctx, rec, text):
    hits = [h for h in privacy_hits(text, ctx.blocklist) if h[0] != "ident"]
    return [_finding("privacy", _line_of(text, hits[0][2]),
                     f"{len(hits)} string(s)/comment(s) that may identify the original program",
                     6, key="privacy")] if hits else []


def scrub_privacy(text: str, terms: list[str]) -> str:
    for kind, t, s in sorted(privacy_hits(text, terms), key=lambda h: -h[2]):
        if kind == "string":
            q = t[-1]
            pre = t[:t.index(q)]
            text = text[:s] + pre + q + q + text[s + len(t):]
        elif kind == "comment":
            text = text[:s] + ("" if t.startswith("//") else "/* */") + text[s + len(t):]
    return text


def fix_privacy(ctx, rec, text, f):
    new = scrub_privacy(text, ctx.blocklist)
    ctx.last_plan = "blank identifying strings and remove identifying comments"
    return new if new != text else None


# -- clang-tidy's automatic fixes
TIDY_CHECKS = ("-*,modernize-use-nullptr,modernize-use-bool-literals,"
               "readability-braces-around-statements,readability-redundant-control-flow,"
               "readability-simplify-boolean-expr,readability-else-after-return")


def _tidy_result(ctx, rec, text) -> Optional[str]:
    exe = shutil.which("clang-tidy")
    if not exe:
        return None
    cache = ctx.state.g("tidy", {})
    key = f"{rec.mangled}:{text_sha(text)}"
    if key in cache:
        return cache[key]
    d = ctx.cfg.workdir / "improve" / "tmp"
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / ("tidy_" + Path(rec.file).name)
    tmp.write_text(text)
    try:
        subprocess.run([exe, str(tmp), f"--checks={TIDY_CHECKS}", "--fix", "--quiet", "--",
                        f"-std={ctx.cfg.std}", f"-I{ctx.cfg.workdir}", "-w", "-x", "c++",
                        *ctx.cfg.extra_flags], capture_output=True, text=True, timeout=300)
        new = tmp.read_text()
    except Exception:
        new = text
    cache[key] = new if new != text else None
    return cache[key]


def detect_tidy(ctx, rec, text):
    return [_finding("tidy", 0, "clang-tidy has automatic clean-ups", 1, key="tidy")] \
        if _tidy_result(ctx, rec, text) else []


def fix_tidy(ctx, rec, text, f):
    return _tidy_result(ctx, rec, text)


# -- calls that use a prototype nobody defines (wrong number of arguments)
def _arity_table(ctx) -> dict:
    defined: dict[str, set] = {}
    for r in ctx.records.values():
        if r.quarantined:
            continue
        try:
            h = parse_header(tu_split((ctx.cfg.workdir / r.file).read_text())[0])
        except OSError:
            continue
        if h:
            defined.setdefault(re.sub(r"__dup\d+$", "", r.name), set()).add(len(h[2]))
    protos: dict[str, list[tuple[int, str]]] = {}
    for kind, label, line in _enabled_header_lines(ctx.cfg):
        if kind == "proto":
            h = parse_header(line.rstrip(";"))
            if h:
                protos.setdefault(label, []).append((len(h[2]), line))
    return {"defined": defined, "protos": protos}


def detect_signatures(ctx, rec, text):
    tab = ctx._arity or _arity_table(ctx)
    ctx._arity = tab
    out = []
    _, body = tu_split(text)
    base = len(text) - len(body)
    for i, (k, t, s, e) in enumerate(toks := tokens(body)):
        if k != "ident" or t not in tab["defined"] or i + 1 >= len(toks) or toks[i + 1][1] != "(":
            continue
        close = matching_close(body, toks[i + 1][2])
        n = len(split_args(body[toks[i + 1][2] + 1:close])) if close > 0 else -1
        if n >= 0 and n not in tab["defined"][t]:
            good = next((l for a, l in tab["protos"].get(t, []) if a in tab["defined"][t]), "")
            out.append(_finding("signatures", _line_of(text, base + s),
                                f"calls {t} with {n} argument(s), but it's defined as: {good}",
                                3, key=f"{t}:{n}:{body[s:close + 1][:80]}"))
    return out


def fix_signatures(ctx, rec, text, f):
    return ctx.line_edit(rec, text, f["line"], f"This line {f['msg']}. Change the call so "
                         f"it matches that definition and does the same thing.")


CHECKS = [
    # name, detect, fix, needs the model, gate on behaviour, expensive (cached)
    ("privacy", detect_privacy, fix_privacy, False, False, False),
    ("helpers", detect_helpers, fix_helpers, False, True, False),
    ("magic_div", detect_magic_div, fix_magic_div, False, True, False),
    ("stack_guard", detect_stack, fix_stack, False, False, False),
    ("ptr_arith", detect_ptr_arith, fix_ptr_arith, False, True, False),
    ("casts", detect_casts, fix_casts, False, True, True),
    ("stdlib", detect_stdlib, fix_stdlib, False, False, True),
    ("tidy", detect_tidy, fix_tidy, False, True, True),
    ("warnings", detect_warnings, fix_warnings, True, True, True),
    ("names", detect_names, fix_names, True, True, False),
    ("signatures", detect_signatures, fix_signatures, True, True, False),
    ("behaviour", detect_behaviour, fix_behaviour, True, True, True),
    ("goto", detect_goto, fix_goto, True, True, False),
]
CHECK_NAMES = [c[0] for c in CHECKS] + ["duplicates", "structs", "fields", "globals",
                                        "constants", "functions", "privacy_names", "format"]
_CHECK = {c[0]: c for c in CHECKS}
_CHECK_OF = {"calls": "behaviour", "difftest": "behaviour", "sanitizer": "behaviour"}


def quick_score(ctx: ImproveCtx, rec) -> float:
    """The cheap checks only (no compiling or tests): to decide what to look at first."""
    try:
        text = ctx.text(rec)
    except OSError:
        return 0.0
    total = 0.0
    for name, detect, _, _, _, expensive in CHECKS:
        if expensive or name in ("signatures",) or (ctx.checks and name not in ctx.checks):
            continue
        try:
            total += sum(f["weight"] for f in detect(ctx, rec, text))
        except Exception:
            pass
    return total + 0.01                       # never 0: everything gets checked once


def detect_all(ctx: ImproveCtx, m: str, rec) -> list[dict]:
    text = ctx.text(rec)
    sha = text_sha(text)
    fs = ctx.state.f(m)
    cache = fs.setdefault("cache", {})
    out = []
    for name, detect, _, _, _, expensive in CHECKS:
        if ctx.checks and name not in ctx.checks:
            continue
        if expensive and cache.get(name, {}).get("sha") == sha:
            out += cache[name]["findings"]
            continue
        phase(f"check: {name}")
        try:
            found = detect(ctx, rec, text)
        except Exception as e:
            found = []
            ctx.count(name, f"check failed ({type(e).__name__})")
        if expensive:
            cache[name] = {"sha": sha, "findings": found}
        out += found
    fs["findings"] = out
    fs["score"] = round(sum(f["weight"] for f in out), 2)
    fs["sha"] = sha
    return out


def attempt_fix(ctx: ImproveCtx, m: str, rec, f: dict, round_log: list) -> bool:
    name = _CHECK_OF.get(f["check"], f["check"])
    _, _, fix, needs_model, behaviour, _ = _CHECK[name]
    fs = ctx.state.f(m)
    parked = fs["parked"].get(f["key"])
    if parked and (not ctx.model or ctx.model in parked.get("models", [])):
        return False
    if needs_model and not ctx.model:
        return False
    text = ctx.text(rec)
    ctx.last_plan = ""
    phase(f"{f['check']}: {f['msg'][:60]}")
    try:
        new = fix(ctx, rec, text, f)
    except Exception as e:
        new = None
        ctx.last_plan = f"fix failed ({type(e).__name__}: {e})"[:200]
    ok, why = (False, "no usable edit") if not new else gate_change(
        ctx, rec, text, new, behaviour=behaviour, allow_shrink=name in ("stdlib", "stack_guard"))
    plan = f" plan: {ctx.last_plan.rstrip('.')}." if ctx.last_plan else ""
    if ok:
        record_version(ctx.cfg, rec.file, text, new, f["check"])
        round_log.append({"files": {rec.file: text}, "what": f"{rec.name}: {f['check']}"})
        fs["changes"] = fs.get("changes", 0) + 1
        fs["parked"].pop(f["key"], None)
        write_note(ctx.cfg, rec.file, f"[{f['check']}] {f['msg'][:140]} —{plan} kept.")
        ctx.count(f["check"], "kept")
        return True
    p = fs["parked"].setdefault(f["key"], {"tries": 0, "models": []})
    p["tries"] += 1
    if needs_model and p["tries"] >= 2 and ctx.model and ctx.model not in p["models"]:
        p["models"].append(ctx.model)        # parked until a different model is loaded
    elif not needs_model:
        p["models"].append(ctx.model or "-")
    write_note(ctx.cfg, rec.file, f"[{f['check']}] {f['msg'][:140]} —{plan} rejected: {why}.")
    ctx.count(f["check"], "rejected")
    return False

# ---------------------------------------------------------------- changes across files

GENERIC_FIELD = re.compile(r"^(field\d*_0x[0-9a-fA-F]+|field_?\d+|unk\w*|_?unknown\w*|"
                           r"f_?[0-9a-fA-F]{1,4}|undefined\w*|member_?\d+)$")
GENERIC_STRUCT = re.compile(r"^(astruct\w*|struct_?\w*\d\w*|Struct\d+\w*|anon\w*|S\d+|"
                            r"_?struct\d+\w*)$", re.I)
GLOBAL_LEFTOVER = re.compile(r"^(DAT|PTR|_DAT|g_DAT|BYTE|WORD|DWORD|QWORD)_[0-9a-fA-F]+$")
PLACEHOLDER_FN = re.compile(r"^(?:thunk_)?(?:FUN|SUB|LAB)_[0-9a-fA-F]+(?:__dup\d+)?$")


def load_blocklist(P: "Paths") -> list[str]:
    """Words that identify the original program (privacy_blocklist.txt, yours to
    edit; started with the program's name from the Ghidra export)."""
    f = P.root / "privacy_blocklist.txt"
    if not f.exists():
        prog = ""
        try:
            prog = json.loads(P.export.read_text()).get("program") or ""
        except Exception:
            pass
        stem = re.sub(r"\.(exe|dll|dylib|so|app|bin)$", "", prog, flags=re.I)
        parts = [w for w in re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+", stem) if len(w) >= 4]
        f.write_text(
            "# Words that identify the original program: product, company and people's\n"
            "# names. One per line; case doesn't matter. The improve stage removes strings\n"
            "# and comments containing them and renames identifiers that contain them;\n"
            "# the organize stage won't write the final code while any are left.\n"
            + (f"# The program's name, from the Ghidra export:\n{stem}\n" if len(stem) >= 3 else "")
            + ("# Parts of it (remove the # to use one):\n" + "".join(f"# {w}\n" for w in parts)
               if len(parts) > 1 else ""))
    terms = []
    for line in f.read_text(errors="replace").splitlines():
        t = line.strip()
        if t and not t.startswith("#") and len(t) >= 3:
            terms.append(t)
    return terms


def _all_files(ctx) -> list[Path]:
    cfg = ctx.cfg
    files = [cfg.shared_h, cfg.globals_cpp]
    files += [cfg.workdir / r.file for r in ctx.records.values()]
    return [p for p in files if p.exists()]


def _gate_files(ctx, paths: list[Path]) -> tuple[bool, str]:
    cfg = ctx.cfg
    if cfg.shared_h in paths:
        ok, err = _compile_header_human(cfg, "shared.h")
        if not ok:
            return False, "shared.h: " + next((l for l in err.splitlines() if "error" in l), "")[:200]
    for p in paths:
        if p.suffix != ".cpp":
            continue
        rel = str(p.relative_to(cfg.workdir))
        rec = next((r for r in ctx.records.values() if r.file == rel), None)
        if rec is not None and (rec.quarantined or not rec.compiles):
            continue
        ok, err, _ = compile_tu(cfg, rel)
        if not ok:
            return False, f"{p.name}: " + next((l for l in err.splitlines() if "error" in l), "")[:200]
    return True, ""


def global_change(ctx, edits: dict[Path, str], tag: str, round_log: list,
                  ops: Optional[list] = None) -> tuple[bool, str]:
    """Apply edits to several files; keep them only if everything still compiles."""
    with HEADER_LOCK.write():
        return _global_change(ctx, edits, tag, round_log, ops)


def _global_change(ctx, edits, tag, round_log, ops):
    txn = Txn(ctx.cfg)
    for p, t in edits.items():
        if t != p.read_text():
            txn.write(p, t)
    if not txn.old:
        return False, "no change"
    try:
        ok, why = _gate_files(ctx, list(txn.old))
    except StopRun:
        txn.rollback()
        raise
    if not ok:
        txn.rollback()
        return False, why
    txn.commit(tag)
    idx = []
    for op in ops or []:
        ctx.state.data["overlay"].append(op)
        idx.append(len(ctx.state.data["overlay"]) - 1)
    round_log.append({"files": {str(p.relative_to(ctx.cfg.workdir)): t for p, t in txn.old.items()},
                      "what": tag, "overlay": idx})
    ctx._arity = None
    return True, ""


def global_rename(ctx, mapping: dict[str, str], tag: str, round_log: list,
                  skip_members=True) -> tuple[bool, str]:
    edits = {}
    for p in _all_files(ctx):
        t = p.read_text()
        if any(o in t for o in mapping):
            new, n = rename_idents(t, mapping, skip_members)
            if n:
                edits[p] = new
    ok, why = global_change(ctx, edits, tag, round_log,
                            [{"op": "rename", "old": o, "new": n, "skip_members": skip_members}
                             for o, n in mapping.items()])
    if ok:
        for r in ctx.records.values():
            if r.name in mapping:
                r.name = mapping[r.name]
    return ok, why


def _usage_lines(ctx, name: str, limit=4) -> list[str]:
    out = []
    rx = re.compile(rf"\b{re.escape(name)}\b")
    for r in ctx.records.values():
        if len(out) >= limit:
            break
        p = ctx.cfg.workdir / r.file
        t = p.read_text() if p.exists() else ""
        if name in t:
            out += [l for l in t.split("\n")[1:] if rx.search(l)][:2]
    return out[:limit]


def _taken_names(ctx) -> set:
    names = set(header_idents(ctx.cfg)) | {r.name for r in ctx.records.values()}
    return names


def ask_all(ctx, items: list, fn) -> list:
    """fn(item) for each item at the same time (questions for the model), answers in
    the same order. The model gate decides how many it gets at once."""
    if not items:
        return []
    out = [None] * len(items)

    def run(k):
        out[k] = fn(items[k])
    work_pool(max(2, ctx.cfg.workers), list(range(len(items))), run)
    return out


def pass_duplicates(ctx, round_log):
    """Functions with identical code: an unused copy (foo__dup1) is switched off,
    a used one becomes a one-line call to the first."""
    groups: dict[str, list] = {}
    for m, r in ctx.compiling():
        t = ctx.text(r)
        head, body = tu_split(t)
        h = parse_header(head)
        if not h or len(body) < 40:
            continue
        norm = re.sub(r"\s+", " ", strip_comments(rename_idents(head + body, {r.name: "@"})[0]))
        groups.setdefault(norm, []).append((m, r, h))
    n = 0
    for members in groups.values():
        if len(members) < 2:
            continue
        members.sort(key=lambda x: ("__dup" in x[1].name, len(x[1].name), x[1].name))
        km, keep, kh = members[0]
        for m, r, h in members[1:]:
            used = any(r.name in ctx.text(o) for o in ctx.records.values() if o is not r) \
                or r.name in ctx.cfg.globals_cpp.read_text()
            path = ctx.cfg.workdir / r.file
            if not used and r.name.startswith(keep.name + "__dup"):
                hdr, _ = disable_units(ctx.cfg.shared_h.read_text(), r.name,
                                       f"identical to {keep.name}", kinds={"proto"})
                ok, _ = global_change(ctx, {ctx.cfg.shared_h: hdr, path: f"{INCLUDE_LINE}\n\n"
                                            f"// {r.name}: identical to {keep.name}, merged "
                                            f"(earlier versions in improve/history/)\n"},
                                      f"merged into {keep.name}", round_log)
                if ok:
                    r.duplicate_of = keep.name
                    n += 1
            elif all(pn for _, pn in h[2]):
                call = f"{keep.name}({', '.join(pn for _, pn in h[2])})"
                body = f"{{\n    {'return ' if h[0].strip() != 'void' else ''}{call};\n}}\n"
                head, _ = tu_split(ctx.text(r))
                ok, _ = global_change(ctx, {path: f"{INCLUDE_LINE}\n\n{head.strip()} {body}"},
                                      f"calls identical {keep.name}", round_log)
                n += ok
    if n:
        log(ctx.cfg, f"    duplicates: {n} identical function(s) merged or turned into a call")
    ctx.count("duplicates", "kept", n)


def pass_structs(ctx, round_log):
    """Structs with the same layout (same field types at the same offsets, same or
    placeholder field names) become one type."""
    lay = struct_layouts(ctx.cfg)
    by: dict = {}
    for name, l in lay.items():
        if l["union"] or len(l["fields"]) < 2 or any(o < 0 for o, *_ in l["fields"]):
            continue
        key = (l["size"], tuple((o, t, s) for o, _, t, s in l["fields"]))
        by.setdefault(key, []).append(name)
    n = 0
    for names in by.values():
        if len(names) < 2:
            continue
        uses = {nm: sum(nm in ctx.text(r) for r in ctx.records.values()) for nm in names}
        names.sort(key=lambda nm: (bool(GENERIC_STRUCT.match(nm)), -uses[nm], nm))
        keep = names[0]
        kf = [f for _, f, _, _ in lay[keep]["fields"]]
        for other in names[1:]:
            of = [f for _, f, _, _ in lay[other]["fields"]]
            if any(a != b and not (GENERIC_FIELD.match(a) or GENERIC_FIELD.match(b))
                   for a, b in zip(kf, of)):
                continue                       # same shape, different meaning: leave
            hdr, k = disable_units(ctx.cfg.shared_h.read_text(), other, f"same as {keep}",
                                   kinds={"record", "fwd", "typedef"})
            edits = {ctx.cfg.shared_h: hdr}
            for p in _all_files(ctx):
                t = edits.get(p, p.read_text())
                if other in t:
                    edits[p] = rename_idents(t, {other: keep})[0]
            ok, why = global_change(ctx, edits, f"struct {other} -> {keep}", round_log,
                                    [{"op": "disable_unit", "label": other, "why": f"same as {keep}",
                                      "kinds": ["record", "fwd", "typedef"]},
                                     {"op": "rename", "old": other, "new": keep}])
            n += ok
    if n:
        log(ctx.cfg, f"    structs: {n} duplicate struct type(s) merged")
    ctx.count("structs", "kept", n)


def member_refs(cfg, path: Path, struct: str, fields: set) -> list[tuple[int, str]]:
    """Where this struct's fields are used in a file (libclang, so a field with the
    same name in another struct is left alone)."""
    try:
        cx = _load_libclang(cfg)
        tu = cx.Index.create().parse(str(path), args=_libclang_args(cfg) + ["-w"])
    except Exception:
        return []
    text = path.read_text()
    out = []
    for c in tu.cursor.walk_preorder():
        if c.kind.name not in ("MEMBER_REF_EXPR", "MEMBER_REF") or c.location.file is None \
                or c.location.file.name != str(path):
            continue
        ref = c.referenced
        if ref is None or ref.kind.name != "FIELD_DECL" or ref.spelling not in fields:
            continue
        par = ref.semantic_parent
        if (par.spelling or "") != struct and par.type.spelling != struct:
            continue
        off = c.location.offset
        k = text.find(ref.spelling, off)
        if k >= 0 and k - off < 200:
            out.append((k, ref.spelling))
    return sorted(set(out))


def rename_fields(ctx_cfg, text_by_path: dict, struct: str, mapping: dict) -> dict:
    """New texts for a field rename: in the struct's own declaration in shared.h,
    and at every use of that struct's fields."""
    cfg = ctx_cfg
    out = {}
    hdr = text_by_path.get(cfg.shared_h, cfg.shared_h.read_text())
    lines = hdr.split("\n")
    for u in _parse_units(lines):
        if u["kind"] == "record" and u["label"] == struct:
            seg = "\n".join(lines[u["start"] + 1:u["end"]])
            lines[u["start"] + 1:u["end"]] = rename_idents(seg, mapping, skip_members=False)[0].split("\n")
    out[cfg.shared_h] = "\n".join(lines)
    for p, t in text_by_path.items():
        if p == cfg.shared_h or not any(o in t for o in mapping):
            continue
        refs = member_refs(cfg, p, struct, set(mapping))
        for k, old in sorted(refs, reverse=True):
            if t[k:k + len(old)] == old:
                t = t[:k] + mapping[old] + t[k + len(old):]
        if refs:
            out[p] = t
    return out


def pass_fields(ctx, round_log, limit=6):
    """Placeholder field names (field_0x18) get names from how they're used."""
    if not ctx.model:
        return
    lay = struct_layouts(ctx.cfg)
    done = ctx.state.g("fields_tried", [])
    todo = [(st, l) for st, l in lay.items() if st not in done
            and any(GENERIC_FIELD.match(f) for _, f, _, _ in l["fields"])][:limit]
    phase(f"naming the fields of {len(todo)} struct(s)")

    def ask(item):
        struct, l = item
        generic = [f for _, f, _, _ in l["fields"] if GENERIC_FIELD.match(f)]
        files = [p for p in _all_files(ctx) if p.suffix == ".cpp" and any(g in p.read_text() for g in generic)]
        uses: dict[str, list[str]] = {g: [] for g in generic}
        for p in files[:30]:
            t = p.read_text()
            for k, fld in member_refs(ctx.cfg, p, struct, set(generic)):
                if len(uses[fld]) < 4:
                    uses[fld].append(t[t.rfind("\n", 0, k) + 1:t.find("\n", k)])
        types = {f: ty for _, f, ty, _ in l["fields"]}
        items = [(g, [f"(type {types[g]})"] + uses[g]) for g in generic[:10]]
        return files, ctx.names("field", items, f"They're fields of struct {struct}.")
    answers = ask_all(ctx, todo, ask)
    n = 0
    for (struct, l), (files, mapping) in zip(todo, answers):
        done.append(struct)
        existing = {f for _, f, _, _ in l["fields"]}
        clean = {o: v for o, v in mapping.items()
                 if is_ident(v) and v not in existing and not GENERIC_FIELD.match(v)}
        if len(set(clean.values())) != len(clean) or not clean:
            continue
        texts = {p: p.read_text() for p in files}
        edits = rename_fields(ctx.cfg, texts, struct, clean)
        ok, why = global_change(ctx, edits, f"fields of {struct}", round_log,
                                [{"op": "field_rename", "struct": struct, "old": o, "new": v}
                                 for o, v in clean.items()])
        n += ok
        ctx.count("fields", "kept" if ok else "rejected")
    if n:
        log(ctx.cfg, f"    fields: named the fields of {n} struct(s)")


def pass_globals(ctx, round_log, limit=24):
    if not ctx.model:
        return
    tried = set(ctx.state.g("globals_tried", []))
    cands = [label for kind, label, _ in _enabled_header_lines(ctx.cfg)
             if kind == "global" and GLOBAL_LEFTOVER.match(label) and label not in tried][:limit]
    taken = _taken_names(ctx)
    n = 0
    batches = [cands[i:i + 8] for i in range(0, len(cands), 8)]
    phase(f"naming {len(cands)} global variable(s)")
    answers = ask_all(ctx, batches, lambda batch: ctx.names(
        "global", [(g, _usage_lines(ctx, g)) for g in batch],
        "They're global variables of the program."))
    for batch, mapping in zip(batches, answers):
        ctx.state.data["global"]["globals_tried"] = sorted(tried | set(batch))
        tried |= set(batch)
        clean = {o: v for o, v in mapping.items() if is_ident(v) and v not in taken
                 and not GLOBAL_LEFTOVER.match(v)}
        if len(set(clean.values())) == len(clean) and clean:
            ok, _ = global_rename(ctx, clean, "global names", round_log)
            n += len(clean) if ok else 0
            taken |= set(clean.values())
    if n:
        log(ctx.cfg, f"    globals: named {n} global variable(s)")
    ctx.count("globals", "kept", n)


def pass_constants(ctx, round_log, limit=10):
    """A number used in 3+ functions gets a name in shared.h."""
    if not ctx.model:
        return
    seen: dict[str, set] = {}
    lines_for: dict[str, list[str]] = {}
    for m, r in ctx.compiling():
        t = ctx.text(r)
        for k, tok, s, e in tokens(tu_split(t)[1]):
            if k != "number" or "." in tok:
                continue
            try:
                v = int(re.sub(r"[uUlL]+$", "", tok), 0)
            except ValueError:
                continue
            if v < 256 or (v & (v - 1)) == 0 or (v & (v + 1)) == 0 or RAW_ADDRESS.match(tok):
                continue
            seen.setdefault(tok, set()).add(r.file)
            if len(lines_for.setdefault(tok, [])) < 4:
                ln = next((l for l in t.split("\n") if tok in l), "")
                lines_for[tok].append(ln)
    tried = set(ctx.state.g("constants_tried", []))
    cands = [tok for tok, fs in sorted(seen.items(), key=lambda kv: -len(kv[1]))
             if len(fs) >= 3 and tok not in tried][:limit]
    if not cands:
        return
    ctx.state.data["global"]["constants_tried"] = sorted(tried | set(cands))
    phase(f"naming {len(cands)} repeated number(s)")
    mapping = ctx.names("constant", [(c, lines_for[c]) for c in cands],
                        "These numbers appear in several functions.")
    taken = _taken_names(ctx)
    n = 0
    for tok, name in mapping.items():
        if not re.fullmatch(r"[A-Z][A-Z0-9_]+", name) or name in taken:
            continue
        hdr = add_const_unit(ctx.cfg.shared_h.read_text(), name, tok)
        edits = {ctx.cfg.shared_h: hdr}
        for rel in seen[tok]:
            p = ctx.cfg.workdir / rel
            t = p.read_text()
            head_len = len(t) - len(tu_split(t)[1])
            out, last = [], 0
            for k, tk, s, e in tokens(t):
                if k == "number" and tk == tok and s >= head_len:
                    out += [t[last:s], name]
                    last = e
            edits[p] = "".join(out) + t[last:]
        ok, _ = global_change(ctx, edits, f"constant {name}", round_log,
                              [{"op": "add_const", "name": name, "spelling": tok,
                                "files": sorted(seen[tok])}])
        n += ok
        taken.add(name)
    if n:
        log(ctx.cfg, f"    constants: named {n} repeated number(s)")
    ctx.count("constants", "kept", n)


def pass_functions(ctx, round_log, limit=20):
    """Functions still without a real name (FUN_..., a poor name, or a name the
    rewrite suggested changing) are named from their goal and their calls."""
    if not ctx.model:
        return
    sugg = {}
    if ctx.P and ctx.P.progress.exists():
        try:
            for e in json.loads(ctx.P.progress.read_text()).get("functions", {}).values():
                if e.get("suggested_name") and e.get("name"):
                    sugg[e["name"]] = e["suggested_name"]
        except Exception:
            pass
    tried = set(ctx.state.g("functions_tried", []))
    callers: dict[str, list[str]] = {}
    for m, r in ctx.records.items():
        for d in r.deps:
            if d in ctx.records:
                callers.setdefault(ctx.records[d].name, []).append(r.name)
    cands = [(m, r) for m, r in ctx.compiling()
             if (PLACEHOLDER_FN.match(r.name) or BAD_NAME.match(r.name) or r.name in sugg)
             and r.name not in tried][:limit]
    taken = _taken_names(ctx)
    n = 0
    phase(f"naming {len(cands)} function(s)")

    def ask(item):
        m, r = item
        t = ctx.text(r)
        goal = ctx.goal(r, t)
        callees = [ctx.records[d].name for d in r.deps if d in ctx.records][:8]
        info = [f"goal: {goal or '(unknown)'}", f"calls: {', '.join(callees) or 'nothing'}",
                f"called by: {', '.join(callers.get(r.name, [])[:8]) or 'nothing'}"]
        if r.name in sugg:
            info.append(f"another suggestion was: {sugg[r.name]} (keep the current name if it's better)")
        return ctx.names("function", [(r.name, info)]).get(r.name)
    answers = ask_all(ctx, cands, ask)        # the questions go out together
    for (m, r), new in zip(cands, answers):
        tried.add(r.name)
        ctx.state.data["global"]["functions_tried"] = sorted(tried)
        if not new or new == r.name or not is_ident(new) or new in taken or not new[0].islower() \
                or PLACEHOLDER_FN.match(new) or BAD_NAME.match(new):
            continue
        ok, why = global_rename(ctx, {r.name: new}, f"rename {r.name} -> {new}", round_log)
        if ok:
            taken.add(new)
            n += 1
            write_note(ctx.cfg, r.file, f"[functions] renamed to {new}.")
    if n:
        log(ctx.cfg, f"    functions: named {n} function(s)")
    ctx.count("functions", "kept", n)


def _privacy_rename(name: str, terms: list[str], taken: set) -> str:
    new = name
    for t in sorted(terms, key=len, reverse=True):
        def rep(m):
            s = m.group(0)
            return "APP" if s.isupper() else "App" if s[0].isupper() else "app"
        new = re.sub(re.escape(t), rep, new, flags=re.I)
    if not is_ident(new) or new == name:
        new = "renamed_" + text_sha(name)[:6]
    base, k = new, 2
    while new in taken:
        new, k = f"{base}{k}", k + 1
    return new


def pass_privacy_names(ctx, round_log):
    """Identifiers that contain a blocklisted word are renamed everywhere; strings
    and comments in shared.h / globals.cpp are cleaned like the functions'."""
    if not ctx.blocklist:
        return
    hits = set()
    for p in _all_files(ctx):
        hits |= {t for kind, t, _ in privacy_hits(p.read_text(), ctx.blocklist) if kind == "ident"}
    taken = _taken_names(ctx)
    mapping = {}
    for h in sorted(hits):
        mapping[h] = _privacy_rename(h, ctx.blocklist, taken | set(mapping.values()))
    if mapping:
        ok, why = global_rename(ctx, mapping, "privacy renames", round_log, skip_members=False)
        log(ctx.cfg, f"    privacy: renamed {len(mapping)} identifier(s) containing a "
                     f"blocklisted word" + ("" if ok else f" — undone: {why}"))
        ctx.count("privacy_names", "kept" if ok else "rejected", len(mapping))
    edits = {}
    for p in (ctx.cfg.shared_h, ctx.cfg.globals_cpp):
        if p.exists():
            t = p.read_text()
            new = scrub_privacy(t, ctx.blocklist)
            if new != t:
                edits[p] = new
    if edits:
        global_change(ctx, edits, "privacy strings", round_log)


GLOBAL_PASSES = [("privacy_names", pass_privacy_names), ("duplicates", pass_duplicates),
                 ("structs", pass_structs), ("fields", pass_fields), ("globals", pass_globals),
                 ("constants", pass_constants), ("functions", pass_functions)]


def replay_overlay(cfg: "Config", records: dict) -> None:
    """After a (re-)split: re-apply the header-level changes the improve stage made
    (renames, merged structs, named constants, field names), so files coming fresh
    from the rewrite match the improved shared.h."""
    st_path = cfg.workdir / "improve" / "state.json"
    if not st_path.exists():
        return
    try:
        ops = [o for o in json.loads(st_path.read_text()).get("overlay", [])
               if not o.get("reverted")]
    except Exception:
        return
    if not ops:
        return
    files = [cfg.shared_h, cfg.globals_cpp] + [cfg.workdir / r.file for r in records.values()]
    texts = {p: p.read_text() for p in files if p.exists()}
    for op in ops:
        if op["op"] == "rename":
            mp = {op["old"]: op["new"]}
            for p, t in texts.items():
                if op["old"] in t:
                    texts[p] = rename_idents(t, mp, op.get("skip_members", True))[0]
            for r in records.values():
                if r.name == op["old"]:
                    r.name = op["new"]
        elif op["op"] == "disable_unit":
            texts[cfg.shared_h] = disable_units(texts[cfg.shared_h], op["label"], op["why"],
                                                set(op.get("kinds") or []) or None)[0]
        elif op["op"] == "add_const":
            texts[cfg.shared_h] = add_const_unit(texts[cfg.shared_h], op["name"], op["spelling"])
            for rel in op.get("files", []):
                p = cfg.workdir / rel
                if p in texts:
                    t = texts[p]
                    out, last = [], 0
                    for k, tk, s, e in tokens(t):
                        if k == "number" and tk == op["spelling"]:
                            out += [t[last:s], op["name"]]
                            last = e
                    texts[p] = "".join(out) + t[last:]
        elif op["op"] == "field_rename":
            for p, t in texts.items():
                p.write_text(t)
            texts.update(rename_fields(cfg, dict(texts), op["struct"], {op["old"]: op["new"]}))
    changed = 0
    for p, t in texts.items():
        if p.read_text() != t:
            p.write_text(t)
            changed += 1
    if changed:
        log(cfg, f"  re-applied {len(ops)} improve-stage change(s) to {changed} file(s) "
                 f"after the split")


def format_code(text: str) -> Optional[str]:
    exe = shutil.which("clang-format")
    if not exe:
        return None
    try:
        r = subprocess.run([exe, "--style={BasedOnStyle: LLVM, IndentWidth: 4, "
                                 "ColumnLimit: 100, AllowShortFunctionsOnASingleLine: None}",
                            "--assume-filename=x.cpp"], input=text, capture_output=True,
                           text=True, timeout=60)
        return r.stdout if r.returncode == 0 and r.stdout.strip() else None
    except Exception:
        return None


# ---------------------------------------------------------------- the improve stage

def _revert(ctx, change: dict, why: str) -> None:
    for rel, old in change["files"].items():
        p = ctx.cfg.workdir / rel
        if old is None or not p.exists():
            continue
        cur = p.read_text()
        p.write_text(old)
        record_version(ctx.cfg, rel, cur, old, "reverted")
        if rel.startswith("funcs/"):
            write_note(ctx.cfg, rel, f"[{change['what']}] undone: {why}.")
    for i in change.get("overlay", []):
        ctx.state.data["overlay"][i]["reverted"] = True


def run_improve(P: "Paths", cfg: "Config", records: dict, args) -> dict:
    model_check(cfg)
    checks = set(args.improve_checks.split(",")) if args.improve_checks else None
    ctx = ImproveCtx(cfg, records, P, checks)
    if "improve" in (args.redo or []):
        n = 0
        for fs in ctx.state.data["funcs"].values():
            n += len(fs.get("parked", {}))
            fs["parked"] = {}
        for k in ("fields_tried", "globals_tried", "constants_tried", "functions_tried"):
            ctx.state.data["global"].pop(k, None)
        log(cfg, f"  --redo improve: {n} parked task(s) will be tried again")
    if not ctx.model:
        log(cfg, "  no model available — only the fixes that don't need it will run")
    if not ctx.export:
        log(cfg, "  (no Ghidra export: the checks against Ghidra's version are off)")
    if not sanitizer_flags(cfg):
        log(cfg, "  (sanitizers aren't available with this compiler — tests run without them)")
    for tool in ("clang-tidy", "clang-format"):
        if not shutil.which(tool):
            log(cfg, f"  ({tool} not found — its clean-ups are skipped)")
    build_dep_order(cfg, records)
    deadline = time.time() + args.improve_minutes * 60 if args.improve_minutes else None
    link_ok_before = bool(load_state(cfg).get("link_ok"))
    first_score = None
    kept_total = 0
    for rnd in range(1, args.improve_rounds + 1):
        round_log: list = []
        log(cfg, f"  » round {rnd}: changes across the code (names, duplicates, types, "
                 f"constants, privacy)")
        for name, fn in GLOBAL_PASSES:
            if checks and name not in checks:
                continue
            try:
                fn(ctx, round_log)
            except Exception as e:
                log(cfg, f"    ({name} pass failed: {type(e).__name__}: {e})")
            ctx.state.save()
        funcs = ctx.compiling()
        # Worst first, by what's known: last round's score, else a quick look with
        # the cheap checks. Then checking and fixing run as one pipeline over
        # --workers functions at once, so while the model works on one function
        # the others are being compiled and tested and have their request ready.
        order = {}
        for m, r in funcs:
            sc = ctx.state.f(m).get("score")
            order[m] = sc if sc is not None else quick_score(ctx, r)
        def needs_look(m, r):
            fs = ctx.state.f(m)
            return fs.get("score") is None or fs["score"] > 0 or fs.get("sha") != text_sha(ctx.text(r))
        queue = sorted((x for x in funcs if needs_look(*x)), key=lambda x: -order[x[0]])
        start_scores: dict[str, float] = {}
        kept = [0]
        use = ModelUse()
        prog = Progress(len(queue), 0, title=f"round {rnd}: checking and fixing, worst first")
        prog.extra = lambda: f"{kept[0]} kept | {use.text()}"

        def one(item):
            m, r = item
            if deadline and time.time() > deadline:
                return
            prog.begin(m, r.name)
            try:
                detect_all(ctx, m, r)
                start_scores[m] = ctx.state.f(m)["score"]
                tried: set = set()
                for _ in range(args.improve_per_function):
                    fl = [f for f in ctx.state.f(m)["findings"] if f["key"] not in tried]
                    fl.sort(key=lambda f: (_CHECK[_CHECK_OF.get(f["check"], f["check"])][3],
                                           -f["weight"]))
                    progressed = False
                    for f in fl:
                        tried.add(f["key"])
                        if attempt_fix(ctx, m, r, f, round_log):
                            kept[0] += 1
                            detect_all(ctx, m, r)
                            progressed = True
                            break
                    if not progressed:
                        break
            finally:
                prog.end(m)
        try:
            work_pool(cfg.workers, queue, one, 20, ctx.state.save)
        finally:
            prog.close()
            ctx.state.save()
        score = round(sum(start_scores.values()) +
                      sum(ctx.state.f(m)["score"] or 0 for m, _ in funcs if m not in start_scores), 1)
        if first_score is None:
            first_score = score
        log(cfg, f"  » round {rnd}: checked {len(start_scores)} function(s) (score {score} at the "
                 f"start; lower is better), {kept[0]} small fix(es) kept, {use.text()}")
        # tidy layout of everything changed this round
        if shutil.which("clang-format"):
            for rel in sorted({f for c in round_log for f in c["files"] if f.startswith("funcs/")}):
                p = cfg.workdir / rel
                t = p.read_text()
                new = format_code(t)
                if new and new != t and new.startswith(INCLUDE_LINE):
                    p.write_text(new)
                    if compile_tu(cfg, rel)[0]:
                        record_version(cfg, rel, t, new, "format")
                    else:
                        p.write_text(t)
        if round_log:
            log(cfg, f"  » round {rnd}: {len(round_log)} change(s) kept — linking to check "
                     f"the whole program")
            ok = link_pass(cfg, records)
            if not ok and link_ok_before:
                for change in reversed(list(round_log)):
                    _revert(ctx, change, "the program stopped linking")
                    round_log.remove(change)
                    if link_pass(cfg, records):
                        ok = True
                        break
                log(cfg, f"    link: undid the change(s) that stopped the program linking")
            link_ok_before = link_ok_before or ok
            save_state(cfg, link_ok=ok)
        kept_total += len(round_log)
        ctx.state.data["rounds"].append({"at": time.strftime("%Y-%m-%d %H:%M:%S"),
                                         "changes": len(round_log), "score": score,
                                         "model": ctx.model or ""})
        ctx.state.save()
        save_manifest(cfg, records)
        if not round_log or (deadline and time.time() > deadline):
            break
    funcs = ctx.compiling()
    for m, r in funcs:
        if ctx.state.f(m).get("score") is None:
            detect_all(ctx, m, r)
    final_score = round(sum(ctx.state.f(m)["score"] or 0 for m, _ in funcs), 1)
    open_by: dict[str, int] = {}
    for m, _ in funcs:
        for f in ctx.state.f(m)["findings"]:
            open_by[f["check"]] = open_by.get(f["check"], 0) + 1
    summary = {"rounds": len(ctx.state.data["rounds"]), "kept": kept_total,
               "score_before": first_score, "score_after": final_score,
               "open": dict(sorted(open_by.items(), key=lambda kv: -kv[1])),
               "by_check": ctx.stats, "model": ctx.model or ""}
    ctx.state.data["global"]["last_summary"] = summary
    ctx.state.save()
    rep = [f"improve stage — {time.strftime('%Y-%m-%d %H:%M:%S')}, model: {ctx.model or 'none'}",
           f"score: {first_score} -> {final_score} (lower is better), {kept_total} change(s) kept",
           "", "by check (kept / rejected):"]
    rep += [f"  {c}: {d.get('kept', 0)} kept, {d.get('rejected', 0)} rejected"
            for c, d in sorted(ctx.stats.items())]
    rep += ["", "still open:"] + [f"  {c}: {n}" for c, n in open_by.items()]
    (cfg.workdir / "improve_report.txt").write_text("\n".join(rep) + "\n")
    log(cfg, f"  improve: score {first_score} -> {final_score}, {kept_total} change(s) kept "
             f"(details in build/improve_report.txt, notes in build/improve/notes/)")
    return summary

# ---------------------------------------------------------------- the organize stage
#
# Writes PROJ/final/: the improved code arranged as a normal C++ project, with
# modules (folders of related functions) and classes (structs whose functions
# become their methods). The build/ folder is never changed by this stage; the
# previous final/ is moved to snapshots/ first.

def _cluster(nodes: list[str], adj: dict, max_size=40) -> list[list[str]]:
    label = {n: i for i, n in enumerate(nodes)}
    for _ in range(20):
        changed = False
        sizes: dict[int, int] = {}
        for v in label.values():
            sizes[v] = sizes.get(v, 0) + 1
        for n in nodes:
            score: dict[int, float] = {}
            for nb, w in adj.get(n, {}).items():
                score[label[nb]] = score.get(label[nb], 0) + w
            if not score:
                continue
            best = max(score, key=lambda l: (score[l], -l))
            if best != label[n] and sizes.get(best, 0) < max_size \
                    and score[best] > score.get(label[n], 0):
                sizes[label[n]] -= 1
                sizes[best] = sizes.get(best, 0) + 1
                label[n] = best
                changed = True
        if not changed:
            break
    groups: dict[int, list[str]] = {}
    for n in nodes:
        groups.setdefault(label[n], []).append(n)
    big = [g for g in groups.values() if len(g) >= 3]
    small = [n for g in groups.values() if len(g) < 3 for n in g]
    for n in small:                    # a lone function joins the group it talks to most
        best, bw = None, 0.0
        for g in big:
            w = sum(adj.get(n, {}).get(x, 0) for x in g)
            if w > bw and len(g) < max_size:
                best, bw = g, w
        if best is not None:
            best.append(n)
        else:
            if not big or len(big[-1]) >= max_size or not big[-1][0].startswith("\0misc"):
                big.append(["\0misc"])
            big[-1].append(n)
    return [[n for n in g if not n.startswith("\0")] for g in big if any(not n.startswith("\0") for n in g)]


def _module_names(ctx, groups: list[list[str]], recs: dict) -> list[str]:
    cache = ctx.state.g("modules", {})
    names, used = [], set()
    ask = []
    for i, g in enumerate(groups):
        key = text_sha(",".join(sorted(recs[m].name for m in g)))
        if key in cache:
            names.append(cache[key])
        else:
            names.append(None)
            ask.append((i, key))
    if ask and ctx.model:
        for j in range(0, len(ask), 6):
            batch = ask[j:j + 6]
            got = ctx.names("module", [(f"group{i + 1}", [", ".join(recs[m].name for m in groups[i][:15])])
                                       for i, _ in batch],
                            "Each group is a set of related functions (listed by name).")
            for i, key in batch:
                v = got.get(f"group{i + 1}")
                if v:
                    v = re.sub(r"[^a-z0-9]+", "_", v.lower()).strip("_")[:40]
                    if v:
                        cache[key] = v
                        names[i] = v
    out = []
    for i, n in enumerate(names):
        n = n or f"module_{i + 1}"
        base, k = n, 2
        while n in used or n in ("program", "types", "other", "globals", "stubs"):
            n, k = f"{base}_{k}", k + 1
        used.add(n)
        out.append(n)
    return out


def _plan_methods(ctx, funcs: dict, texts: dict, lay: dict, header: str) -> dict:
    """{struct: [mangled...]}: functions whose first parameter is a pointer to a
    struct, at least two per struct, that can become its methods."""
    record_units = {u["label"] for u in _parse_units(header.split("\n")) if u["kind"] == "record"}
    all_text = "\n".join(texts.values())
    toks = tokens(all_text)
    as_value = {t for i, (k, t, _, _) in enumerate(toks)
                if k == "ident" and (i + 1 >= len(toks) or toks[i + 1][1] != "(")}
    plan: dict[str, list[str]] = {}
    for m, r in funcs.items():
        head, body = tu_split(texts[m])
        if 'extern "C"' in head:
            continue
        h = parse_header(head)
        if not h or not h[2]:
            continue
        t0, p0 = h[2][0]
        mt = re.fullmatch(r"(?:struct\s+)?([A-Za-z_]\w*)\s*\*", " ".join(t0.split()))
        if not mt or not p0 or mt.group(1) not in lay or mt.group(1) not in record_units:
            continue
        s = mt.group(1)
        if re.search(rf"\b{p0}\s*(=[^=]|\+\+|--|\+=|-=)|(\+\+|--)\s*{p0}\b|&\s*{p0}\b", body):
            continue                              # the pointer itself is changed / taken
        if any(f == r.name for _, f, _, _ in lay[s]["fields"]):
            continue
        if r.name in as_value:
            continue                              # used as a function pointer somewhere
        plan.setdefault(s, []).append(m)
    return {s: ms for s, ms in plan.items() if len(ms) >= 2}


def _write_final(ctx, out: Path, funcs: dict, texts: dict, modules: list, mod_names: list,
                 methods: dict) -> None:
    cfg = ctx.cfg
    (out / "include").mkdir(parents=True, exist_ok=True)
    (out / "src").mkdir(parents=True, exist_ok=True)
    header = strip_disabled(cfg.shared_h.read_text())
    lines = header.split("\n")
    units = _parse_units(lines)
    proto_of = {}
    for u in units:
        if u["kind"] == "proto":
            proto_of.setdefault(u["label"], []).extend(lines[u["start"] + 1:u["end"]])
    method_of = {funcs[m].name: s for s, ms in methods.items() for m in ms}
    # struct definitions get their method declarations
    decls: dict[str, list[str]] = {}
    for s, ms in methods.items():
        for m in ms:
            h = parse_header(tu_split(texts[m])[0])
            decls.setdefault(s, []).append(
                f"    {h[0]} {h[1]}({', '.join(f'{t} {n}'.strip() for t, n in h[2][1:])});")
    keep = []
    i = 0
    by_start = {u["start"]: u for u in units}
    while i < len(lines):
        u = by_start.get(i)
        if u and u["kind"] == "proto":
            i = u["end"]
            continue
        if u and u["kind"] == "record" and u["label"] in decls:
            body = lines[u["start"]:u["end"]]
            keep += body[:-1] + decls[u["label"]] + body[-1:]
            i = u["end"]
            continue
        l = lines[i]
        if l.startswith("// ==== function prototypes"):
            i += 1
            continue
        keep.append(l)
        i += 1
    types_h = "\n".join(l for l in keep if not l.startswith("//@unit "))
    (out / "include" / "types.h").write_text(types_h.rstrip() + "\n")
    (out / "include" / "ghidra_intrins.h").write_text(cfg.intrins_h.read_text())
    used_protos = set()
    for name, ms in zip(mod_names, modules):
        protos = []
        for m in ms:
            nm = funcs[m].name
            if nm in method_of:
                continue
            protos += proto_of.get(nm, [])
            used_protos.add(nm)
        (out / "include" / f"{name}.h").write_text(
            "#pragma once\n#include \"types.h\"\n\n" + "\n".join(protos) + "\n")
    other = [l for nm, ls in proto_of.items() if nm not in used_protos and nm not in method_of
             for l in ls]
    (out / "include" / "other.h").write_text(
        "#pragma once\n#include \"types.h\"\n\n// declared but defined elsewhere (or a "
        "placeholder in stubs.cpp)\n" + "\n".join(other) + "\n")
    (out / "include" / "program.h").write_text(
        "#pragma once\n#include \"types.h\"\n" + "".join(f'#include "{n}.h"\n' for n in mod_names)
        + '#include "other.h"\n')

    def convert_calls(t: str) -> str:
        if not method_of:
            return t

        def rep(name, args):
            if not args:
                return None
            a = args[0]
            obj = a if re.fullmatch(r"[\w.]+(?:->[\w.]+)*", a) else f"({a})"
            return f"{obj}->{name}({', '.join(args[1:])})"
        return replace_calls(t, lambda n: n in method_of, rep)[0]

    for name, ms in zip(mod_names, modules):
        parts = []
        for m in ms:
            r = funcs[m]
            head, body = tu_split(texts[m])
            if r.name in method_of:
                h = parse_header(head)
                s = method_of[r.name]
                body = rename_idents(body, {h[2][0][1]: "this"})[0]
                head = f"{h[0]} {s}::{h[1]}({', '.join(f'{t} {n}'.strip() for t, n in h[2][1:])}) "
            parts.append(convert_calls(head.strip() + " " + body.strip()))
        src = '#include "program.h"\n\n' + "\n\n".join(parts) + "\n"
        (out / "src" / f"{name}.cpp").write_text(src)
    for extra in ("globals.cpp", "stubs.cpp"):
        p = cfg.workdir / extra
        if p.exists():
            t = p.read_text().replace(INCLUDE_LINE, '#include "program.h"', 1)
            (out / "src" / extra).write_text(convert_calls(t))
    if shutil.which("clang-format"):
        for p in list((out / "src").glob("*.cpp")) + list((out / "include").glob("*.h")):
            if p.name == "ghidra_intrins.h":
                continue
            new = format_code(p.read_text())
            if new:
                p.write_text(new)
    (out / "CMakeLists.txt").write_text(
        "cmake_minimum_required(VERSION 3.16)\nproject(program CXX)\n"
        f"set(CMAKE_CXX_STANDARD {re.sub(r'[^0-9]', '', cfg.std) or '17'})\n"
        "file(GLOB SOURCES src/*.cpp)\nadd_library(program SHARED ${SOURCES})\n"
        "target_include_directories(program PRIVATE include)\n")
    readme = ["# Program", "", "Generated by decomp_pipeline.py (organize stage).", "",
              "## Modules", ""]
    for name, ms in zip(mod_names, modules):
        readme.append(f"- **{name}** ({len(ms)}): " + ", ".join(funcs[m].name for m in ms[:20])
                      + (" …" if len(ms) > 20 else ""))
    if methods:
        readme += ["", "## Classes", ""]
        for s, ms in methods.items():
            readme.append(f"- **{s}**: " + ", ".join(funcs[m].name for m in ms))
    (out / "README.md").write_text("\n".join(readme) + "\n")


def _build_final(cfg: "Config", out: Path) -> tuple[bool, bool, str]:
    """(everything compiles, it links, first error)."""
    obj = out / ".build"
    obj.mkdir(exist_ok=True)
    objs = []
    for src in sorted((out / "src").glob("*.cpp")):
        o = obj / (src.stem + ".o")
        r = subprocess.run([cfg.cxx, f"-std={cfg.std}", f"-I{out / 'include'}", "-w", "-c",
                            *PIC_FLAGS, *cfg.extra_flags, str(src), "-o", str(o)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            return False, False, f"{src.name}: " + next((l for l in r.stderr.splitlines()
                                                        if "error" in l), r.stderr[:200])
        objs.append(str(o))
    lib = ["-dynamiclib"] if sys.platform == "darwin" else ["-shared", "-Wl,--no-undefined"]
    r = subprocess.run([cfg.cxx, *lib, *PIC_FLAGS, *cfg.extra_flags, *objs, "-o",
                        str(obj / ("program.dylib" if sys.platform == "darwin" else "program.so"))],
                       capture_output=True, text=True)
    return True, r.returncode == 0, "" if r.returncode == 0 else r.stderr[:300]


def run_organize(P: "Paths", cfg: "Config", records: dict, args) -> dict:
    model_check(cfg)
    ctx = ImproveCtx(cfg, records, P)
    build_dep_order(cfg, records)
    funcs = {m: r for m, r in records.items()
             if r.compiles and not r.quarantined and not getattr(r, "duplicate_of", "")}
    texts = {m: (cfg.workdir / r.file).read_text() for m, r in funcs.items()}
    lay = struct_layouts(cfg)
    # modules: functions that call each other or use the same structs belong together
    adj: dict[str, dict[str, float]] = {}

    def link(a, b, w):
        if a != b:
            adj.setdefault(a, {})[b] = adj.get(a, {}).get(b, 0) + w
            adj.setdefault(b, {})[a] = adj.get(b, {}).get(a, 0) + w
    uses: dict[str, list[str]] = {}
    for m, r in funcs.items():
        for d in r.deps:
            if d in funcs:
                link(m, d, 1.0)
        for s in ident_set(texts[m]) & set(lay):
            uses.setdefault(s, []).append(m)
    for s, ms in uses.items():
        if len(ms) <= 12:
            for i, a in enumerate(ms):
                for b in ms[i + 1:]:
                    link(a, b, 0.5)
    phase("grouping functions into modules")
    modules = _cluster(sorted(funcs), adj)
    mod_names = _module_names(ctx, modules, funcs)
    ctx.state.save()                              # module names are asked for once
    methods = _plan_methods(ctx, funcs, texts, lay, cfg.shared_h.read_text())
    link_ok_before = bool(load_state(cfg).get("link_ok"))
    tmp = P.root / "final.new"
    result = {"modules": len(modules), "classes": 0, "built": False, "linked": False}
    for attempt in ("with classes", "without classes"):
        if attempt == "without classes":
            if not methods:
                break
            methods = {}
        if tmp.exists():
            shutil.rmtree(tmp)                    # our own half-written output
        _write_final(ctx, tmp, funcs, texts, modules, mod_names, methods)
        built, linked, err = _build_final(cfg, tmp)
        log(cfg, f"  final code {attempt}: {'compiles' if built else 'does not compile'}"
                 + (f", {'links' if linked else 'does not link'}" if built else f" ({err})"))
        if built and (linked or not link_ok_before):
            result.update(classes=len(methods), built=True, linked=linked)
            break
    if not result["built"]:
        log(cfg, f"  the final code doesn't build, so final/ was NOT updated — what was "
                 f"written is in {tmp} for a look")
        result["written"] = False
        return result
    hits = []
    terms = ctx.blocklist
    for p in sorted(tmp.rglob("*")):
        if p.is_file() and p.suffix in (".h", ".cpp", ".md", ".txt") and p.name != "ghidra_intrins.h":
            t = p.read_text(errors="replace")
            for kind, tok, s in privacy_hits(t, terms):
                hits.append(f"{p.relative_to(tmp)}:{_line_of(t, s)}: {kind} {tok[:80]}")
            for m in RAW_ADDRESS.finditer(t):
                hits.append(f"{p.relative_to(tmp)}:{_line_of(t, m.start())}: raw address {m.group()}")
    report = P.root / "privacy_report.txt"
    report.write_text(("Nothing found that identifies the original program.\n" if not hits else
                       "Possible identifying text in the final code:\n" + "\n".join(hits) + "\n"))
    result["privacy_hits"] = len(hits)
    if hits and not args.allow_privacy_findings:
        log(cfg, f"  privacy check: {len(hits)} possible identifying item(s) — final/ NOT "
                 f"updated (see privacy_report.txt; run improve again, add words to "
                 f"privacy_blocklist.txt, or --allow-privacy-findings)")
        result["written"] = False
        return result
    final = P.root / "final"
    if final.exists():
        dest = (P.snapshots / f"{time.strftime('%Y%m%d-%H%M%S')}-final")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(final), str(dest))
        log(cfg, f"  previous final/ moved to {dest}")
    shutil.move(str(tmp), str(final))
    result["written"] = True
    log(cfg, f"  final code written to {final}: {len(modules)} module(s), "
             f"{result['classes']} class(es)")
    return result


# ----------------------------------------------------------------------------
# Build stages (split / fix / recover / link)
# ----------------------------------------------------------------------------

def _set_aside_unused(cfg: Config, records: dict[str, FuncRecord]) -> None:
    """Function files left over from an earlier split that no function uses any
    more: moved out of funcs/ (into the snapshot, or funcs_unused/), never deleted."""
    used = {Path(r.file).name for r in records.values()}
    extra = [p for p in cfg.funcs_dir.glob("*.cpp") if p.name not in used]
    if not extra:
        return
    dest = (cfg.snapshot_dir() or cfg.workdir / "funcs_unused") / "build" / "funcs_unused"
    dest.mkdir(parents=True, exist_ok=True)
    for p in extra:
        shutil.move(str(p), str(dest / p.name))
    log(cfg, f"  moved {len(extra)} function file(s) no longer in the split to {dest}")


def build_split(cfg: Config, redo_split: bool) -> dict[str, FuncRecord]:
    """Stage 'split': split + de-ghidra + header gate + compile sweep, or carry on
    from (and update) an earlier build."""
    cfg.workdir.mkdir(parents=True, exist_ok=True)
    log(cfg, f"build {SCRIPT_VERSION} on {cfg.input_file}")
    write_intrinsics(cfg)

    if cfg.manifest_path.exists() and not redo_split:
        # ---------------- resume: check what's done, redo what's stale -------
        records = load_manifest(cfg)
        state = load_state(cfg)
        sha = _input_sha(cfg)
        log(cfg, f"Resume check ({len(records)} functions in manifest):")
        same_version = state.get("version") == SCRIPT_VERSION
        same_input = state.get("input_sha") in (None, sha)
        if not same_input:
            log(cfg, "  the rewrite changed since the last build — updating the split "
                     "(functions whose code changed get the new code; the others keep "
                     "their fixes)")
        files_missing = [r for r in records.values() if not (cfg.workdir / r.file).exists()]

        if not (same_version and same_input and _header_is_current(cfg)) or files_missing:
            why = ("made by an older version of this script" if not same_version
                   else "out of date" if same_input and not files_missing
                   else f"{len(files_missing)} function file(s) missing" if files_missing
                   else "input changed")
            log(cfg, f"  [redo] split + header: {why} — rebuilding shared.h/globals.cpp "
                     f"and merging with the work already done")
            records = reconcile_resume(cfg, records)
            _set_aside_unused(cfg, records)
            replay_overlay(cfg, records)
            save_manifest(cfg, records)
            save_state(cfg, input_sha=sha, split_done=True, header_ok=False,
                       sweep_done=False)
            state = load_state(cfg)
        else:
            log(cfg, "  [ok]   split + header are current")

        if not state.get("header_ok") or not _compile_header_human(cfg, "shared.h")[0]:
            log(cfg, "  [redo] header check")
            log(cfg, "  » validate/repair shared headers")
            _gate_header(cfg, records)
        else:
            log(cfg, "  [ok]   header compiles")
            _pch_flags(cfg)

        if not state.get("sweep_done"):
            log(cfg, "  [redo] compile status")
            _sweep_all(cfg, records)
        else:
            log(cfg, "  [ok]   compile sweep done")
    else:
        # ---------------- fresh split (first time, or --redo split/fix) -------
        # function files are overwritten in place; anything the earlier build had
        # was copied to a snapshot first (see run_pipeline)
        log(cfg, "  » split (parsing the whole file with libclang — "
                 "this can take a minute on a large monolith with no output; not stalled)")
        records = split_monolith(cfg)
        _set_aside_unused(cfg, records)
        save_state(cfg, input_sha=_input_sha(cfg), split_done=True,
                   header_ok=False, sweep_done=False)
        log(cfg, "  » de-ghidra text pass")
        apply_deghidra_pass(cfg, records)
        replay_overlay(cfg, records)
        save_manifest(cfg, records)
        log(cfg, "  » validate/repair shared headers (gate — a broken "
                 "header fails every TU identically)")
        _gate_header(cfg, records)
        _sweep_all(cfg, records)

    done = sum(1 for r in records.values() if r.compiles)
    quar = sum(1 for r in records.values() if r.quarantined)
    todo = sum(1 for r in records.values() if not r.compiles and not r.quarantined)
    log(cfg, f"  status: {done} compile, {todo} still to fix, {quar} quarantined")
    return records


def build_fix(cfg: Config, records: dict[str, FuncRecord]) -> None:
    n_failing = sum(1 for r in records.values() if not r.compiles and not r.quarantined)
    if not n_failing:
        log(cfg, "  nothing to fix")
        return
    if not model_check(cfg):
        save_manifest(cfg, records)
        if not cfg.force:
            log(cfg, f"STOPPED: {n_failing} function(s) need the model but it isn't "
                     f"available. Start the server, load a model and run the same command "
                     f"again (no re-split needed), or add --force to quarantine whatever "
                     f"the deterministic fixes can't handle.")
            sys.exit(2)
        log(cfg, "  --force: continuing without the model")
    log(cfg, "  » dependency order + fixer loop")
    order = build_dep_order(cfg, records)
    fixer_loop(cfg, records, order)
    save_manifest(cfg, records)


def build_recover(cfg: Config, records: dict[str, FuncRecord]) -> None:
    pseudocode_recovery(cfg, records)
    save_manifest(cfg, records)


def build_link(cfg: Config, records: dict[str, FuncRecord]) -> bool:
    linked = link_pass(cfg, records)
    save_manifest(cfg, records)
    save_state(cfg, link_ok=linked)
    return linked


def build_summary(cfg: Config, records: dict[str, FuncRecord]) -> dict:
    out = {"functions": len(records),
           "compile": sum(1 for r in records.values() if r.compiles),
           "quarantined": sum(1 for r in records.values() if r.quarantined),
           "fixed_by_model": sum(1 for r in records.values()
                                 if r.compiles and r.attempts and not r.rederived),
           "rederived": sum(1 for r in records.values() if r.rederived)}
    by: dict[str, int] = {}
    for r in records.values():
        if r.rederived:
            by[r.recovery or "?"] = by.get(r.recovery or "?", 0) + 1
    out["rederived_by"] = by
    return out


# ----------------------------------------------------------------------------
# Adopting runs of the old scripts
# ----------------------------------------------------------------------------

def _copy_missing(src: Path, dst: Path, counts: dict) -> None:
    """Copy src (file or folder) to dst without replacing anything already there."""
    if src.is_dir():
        for p in src.rglob("*"):
            if p.is_file():
                _copy_missing(p, dst / p.relative_to(src), counts)
        return
    if dst.exists():
        counts["kept"] += 1
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    counts["copied"] += 1


def adopt_rewrite(P: Paths, old: Path) -> None:
    """A pseudo_to_cpp.py --out folder -> ghidra/ + rewrite/ (copies)."""
    if not old.is_dir():
        sys.exit(f"--adopt-rewrite: {old} is not a folder")
    counts = {"copied": 0, "kept": 0}
    for name in ("ghidra_export.json", "callgraph.json"):
        if (old / name).exists():
            _copy_missing(old / name, P.ghidra / name, counts)
    if (old / "pseudocode").is_dir():
        _copy_missing(old / "pseudocode", P.pseudocode, counts)
    for name in ("progress.json", "names.txt", "function_index.json"):
        if (old / name).exists():
            _copy_missing(old / name, P.rewrite / name, counts)
    if (old / ".rewritten").is_dir():
        _copy_missing(old / ".rewritten", P.rewritten_dir, counts)
    if (old / "rewritten code.cpp").exists():
        _copy_missing(old / "rewritten code.cpp", P.rewritten, counts)
    if not (P.progress.exists() or P.export.exists()):
        sys.exit(f"--adopt-rewrite: {old} has no progress.json or ghidra_export.json — is "
                 f"it a pseudo_to_cpp.py output folder?")
    plog(P, f"adopted {old}: {counts['copied']} file(s) copied, {counts['kept']} already "
            f"here and left alone")


def adopt_build(P: Paths, old: Path) -> None:
    """A DECOMP_FIXER.py --workdir -> build/ (copies)."""
    if not (old / "manifest.json").exists():
        sys.exit(f"--adopt-build: {old} has no manifest.json — is it a DECOMP_FIXER.py "
                 f"--workdir?")
    counts = {"copied": 0, "kept": 0}
    for p in old.iterdir():
        if p.name in ("pipeline_state.json", "_fresh_funcs", "_parse_monolith.cpp"):
            continue
        _copy_missing(p, P.build / p.name, counts)
    if (old / "pipeline_state.json").exists():
        _copy_missing(old / "pipeline_state.json", P.build / "build_state.json", counts)
    plog(P, f"adopted {old}: {counts['copied']} file(s) copied, {counts['kept']} already "
            f"here and left alone")


# ----------------------------------------------------------------------------
# Report
# ----------------------------------------------------------------------------

def _link_details(P: Paths) -> dict:
    out = {"stubs": 0, "unresolved": 0}
    rep = P.build / "link_report.txt"
    if rep.exists():
        txt = rep.read_text(errors="replace")
        out["stubs"] = len(re.findall(r"^stubbed ", txt, re.M))
        m = re.search(r"unresolved external symbols \((\d+)\)", txt)
        out["unresolved"] = int(m.group(1)) if m else 0
    return out


def write_report(P: Paths) -> dict:
    st = load_pstate(P)
    data: dict = {"generated": time.strftime("%Y-%m-%d %H:%M:%S"),
                  "pipeline_version": PIPELINE_VERSION, "workdir": str(P.root)}
    data["export"] = export_info(P)
    progress = load_progress(P)
    order = list(progress.get("functions", {}).keys())
    try:
        order = [f["addr"] if isinstance(f["addr"], str) else f"{f['addr']:x}"
                 for f in json.loads(P.export.read_text()).get("functions", [])]
    except Exception:
        pass
    data["rewrite"] = _rewrite_summary(progress, order) if progress.get("functions") else {}
    data["rewrite"].pop("stop", None)
    bstate = {}
    if P.manifest.exists():
        try:
            cfg = Config(input_file=P.rewritten, workdir=P.build)
            data["build"] = build_summary(cfg, load_manifest(cfg))
            bstate = load_state(cfg)
        except Exception:
            data["build"] = {}
    else:
        data["build"] = {}
    data["link"] = {"ok": bstate.get("link_ok"), **_link_details(P)} if bstate else {}
    try:
        data["improve"] = json.loads((P.build / "improve" / "state.json").read_text()) \
            .get("global", {}).get("last_summary", {})
    except Exception:
        data["improve"] = {}
    org = load_pstate(P).get("stages", {}).get("organize", {})
    pr = P.root / "privacy_report.txt"
    data["organize"] = {"note": org.get("note"), "written": bool(org.get("done")),
                        "privacy_hits": (len(pr.read_text().splitlines()) - 1
                                         if pr.exists() and not pr.read_text().startswith("Nothing")
                                         else 0) if pr.exists() else None}
    data["stages"] = st.get("stages", {})
    write_atomic(P.report_json, json.dumps(data, indent=2))

    def row(label, val):
        return f"| {label} | {val if val not in (None, '') else '—'} |"

    ex, rw, bd, lk = data["export"], data["rewrite"], data["build"], data["link"]
    md = ["# Decomp pipeline report", "",
          f"`{P.root}` · generated {data['generated']} · pipeline {PIPELINE_VERSION}", "",
          "## Stages", "", "| Stage | Last finished | Model | Notes |",
          "|---|---|---|---|"]
    for s in STAGES:
        e = data["stages"].get(s, {})
        md.append(f"| {s} | {e.get('at', '—') if e.get('done') else ('stopped' if e else '—')}"
                  f" | {e.get('model', '') or ''} | {e.get('note', '') or ''} |")
    md += ["", "## Export", "", "| | |", "|---|---|",
           row("Functions", ex.get("functions")),
           row("With pseudocode", ex.get("with_pseudocode")),
           row("Data types / signatures", f"{ex.get('datatypes', 0)} / {ex.get('signatures', 0)}"
               if ex else None),
           "", "## Rewrite", "", "| | |", "|---|---|",
           row("Rewritten", f"{rw.get('done')}/{rw.get('functions')}" if rw else None),
           row("Waiting to be rewritten again", rw.get("stale")),
           row("Renamed from placeholders", rw.get("renamed")),
           row("Skipped, tried again next run / too big / not started",
               f"{rw.get('skipped')} / {rw.get('too_big')} / {rw.get('not_started')}" if rw else None),
           row("Copied without the model (--tiny)", rw.get("tiny")),
           row("Done in pieces", rw.get("in_pieces")),
           row("Faithful fallbacks", rw.get("faithful")),
           row("Flagged for a second look", rw.get("suspect"))]
    for r, n in (rw.get("suspect_reasons") or {}).items():
        md.append(row(f"&nbsp;&nbsp;{r}", n))
    md += ["", "## Build", "", "| | |", "|---|---|",
           row("Functions in the build", bd.get("functions")),
           row("Compile", bd.get("compile")),
           row("Fixed by the model", bd.get("fixed_by_model")),
           row("Re-derived from pseudocode", bd.get("rederived")),
           row("Quarantined", bd.get("quarantined"))]
    for r, n in (bd.get("rederived_by") or {}).items():
        md.append(row(f"&nbsp;&nbsp;re-derived: {r}", n))
    im, og = data.get("improve") or {}, data.get("organize") or {}
    md += ["", "## Improve", "", "| | |", "|---|---|",
           row("Score (lower is better)", f"{im.get('score_before')} → {im.get('score_after')}"
               if im else None),
           row("Small changes kept", im.get("kept")),
           row("Rounds run (all time)", im.get("rounds"))]
    for c, d in sorted((im.get("by_check") or {}).items()):
        md.append(row(f"&nbsp;&nbsp;{c}", f"{d.get('kept', 0)} kept, {d.get('rejected', 0)} rejected"))
    for c, n in (im.get("open") or {}).items():
        md.append(row(f"&nbsp;&nbsp;still open: {c}", n))
    md += ["", "## Organize", "", "| | |", "|---|---|",
           row("Final code (final/)", og.get("note") if og else None),
           row("Privacy findings", og.get("privacy_hits"))]
    md += ["", "## Link", "", "| | |", "|---|---|",
           row("Linked", {True: "yes", False: "no"}.get(lk.get("ok"))),
           row("Placeholder definitions (stubs.cpp)", lk.get("stubs")),
           row("Unresolved external symbols", lk.get("unresolved")),
           "", "## Where to look", "",
           "- `build/quarantine/` originals of functions that couldn't be fixed",
           "- `build/rederived.txt` functions rebuilt from pseudocode (review the "
           "faithful-pseudocode ones first)",
           "- `build/link_report.txt` placeholders and unresolved symbols",
           "- `build/split_report.txt`, `build/header_repair_report.txt` what the split "
           "renamed or switched off",
           "- `rewrite/progress.json` per-function flags (`suspect`)",
           "- `build/improve/notes/` what was tried on each function, and why it was kept or not",
           "- `build/improve/history/` every version of every function",
           "- `build/improve_report.txt`, `privacy_report.txt`, `final/README.md`", ""]
    write_atomic(P.report_md, "\n".join(md))
    return data


# ----------------------------------------------------------------------------
# Orchestrator
# ----------------------------------------------------------------------------

def _pause_for_model(P: Paths, client: ModelClient, stage: str) -> None:
    current = client.models()
    plog(P, f"  next: '{stage}' uses the model. Loaded in {client.name} now: "
            f"{', '.join(current[:3]) if current else 'nothing / not reachable'}")
    print(f"Load the model you want for '{stage}' in {client.name}, then press Enter "
          f"(Ctrl+C to stop here; the same command resumes).", flush=True)
    try:
        input()
    except (EOFError, OSError):
        print("(no input available — carrying on)", flush=True)


def _check_inputs(P: Paths, first: str) -> None:
    i = STAGES.index(first)
    if i > STAGES.index("export") and not P.export.exists():
        sys.exit(f"--from {first}: there's no {P.export} yet. Run the export first "
                 f"(drop --from), or --adopt-rewrite an old pseudo_to_cpp folder.")
    if i > STAGES.index("rewrite") and not P.rewritten.exists():
        sys.exit(f"--from {first}: there's no {P.rewritten} yet. Run the rewrite first.")
    if i > STAGES.index("split") and not P.manifest.exists():
        sys.exit(f"--from {first}: there's no build yet ({P.manifest}). Run from split.")


def make_build_config(P: Paths, args, client: ModelClient, cxx: str) -> Config:
    snap: dict = {"dir": None}

    def snapshot_dir():
        if P.no_snapshot:
            return None
        if snap["dir"] is None:
            snap["dir"] = P.snapshots / f"{time.strftime('%Y%m%d-%H%M%S')}-build-update"
        return snap["dir"]

    cfg = Config(
        input_file=P.rewritten, workdir=P.build, cxx=cxx, std=args.std,
        libclang_path=args.libclang, max_model_attempts=args.fix_attempts,
        extra_flags=args.extra_flags,
        callgraph_path=args.callgraph or (P.callgraph if P.callgraph.exists() else None),
        force=args.force, stub_all=args.stub_all, export_path=P.export,
        index_path=P.index, no_pseudo=args.no_pseudo,
        retry_quarantined=args.retry_quarantined,
        model_ctx_chars=args.model_ctx_chars or recovery_chars(args.ctx),
        workers=args.workers, model_timeout_s=1800, ctx=args.ctx)
    cfg.client = client
    cfg.wanted_model = None                   # always the model loaded in LM Studio
    cfg.snapshot_dir = snapshot_dir
    return cfg


def run_pipeline(args) -> int:
    STOPPING.clear()
    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGTERM, _on_sigterm)
    P = Paths(args.workdir.expanduser().resolve())
    P.no_snapshot = args.no_snapshot
    P.make()
    acquire_lock(P, args.force)

    redo = set(args.redo or [])
    if args.refresh_ghidra:
        redo.add("export")
    if args.retry_quarantined or "recover" in redo:
        args.retry_quarantined = True
    first = args.from_stage or "export"
    last = args.to_stage or ("export" if args.export_only else "organize")
    if STAGES.index(first) > STAGES.index(last):
        sys.exit(f"--from {first} comes after --to {last}")
    # a redo of an earlier stage starts the run there
    for r in redo:
        if STAGES.index(r) < STAGES.index(first):
            first = r
    args.export_complete = args.export_only or last == "export"

    if args.adopt_rewrite:
        adopt_rewrite(P, args.adopt_rewrite.expanduser())
    if args.adopt_build:
        adopt_build(P, args.adopt_build.expanduser())
    _check_inputs(P, first)

    client = ModelClient(args.backend, args.api)
    CLIENT["c"] = client
    GATE["gate"] = ModelGate(args.parallel)
    cxx = find_compiler(args.cxx)
    if not cxx and STAGES.index(last) >= STAGES.index("split"):
        sys.exit(f"No C++ compiler found ({args.cxx}). On a Mac: xcode-select --install; "
                 f"or pass --cxx /path/to/clang++")
    if not args.rewrite_compile_check:
        COMPILER["cmd"] = None

    run_stages = STAGES[STAGES.index(first):STAGES.index(last) + 1]
    plog(P, f"decomp_pipeline {PIPELINE_VERSION}: {P.root} — stages "
            f"{run_stages[0]} → {run_stages[-1]}"
            + (f" (redo: {', '.join(sorted(redo))})" if redo else ""))
    cfg = make_build_config(P, args, client, cxx or "clang++")
    plog(P, f"  --ctx {args.ctx}: pieces up to {piece_chars(args.ctx, 3000)} characters, recover "
            f"stage up to {cfg.model_ctx_chars}"
            + (" (set by --model-ctx-chars)" if args.model_ctx_chars else ""))
    records = None
    ran_something = False
    try:
        for stage in run_stages:
            if args.pause_between_stages and ran_something and stage in MODEL_STAGES:
                _pause_for_model(P, client, stage)
            n = STAGES.index(stage) + 1
            BAR["stage"] = f"[{n}/{len(STAGES)} {stage}]"
            plog(P, f"━━━━ Stage {n}/{len(STAGES)} · {stage} ━━━━ {STAGE_INFO[stage]}")
            t0 = time.time()
            use = ModelUse()
            calls0 = client.calls
            mark_stage(P, stage, done=False, started=time.strftime("%Y-%m-%d %H:%M:%S"))
            info: dict = {}
            if stage == "export":
                ei = run_export(P, args, redo)
                info = {"note": f"{ei.get('with_pseudocode', 0)}/{ei.get('functions', 0)} "
                                f"with pseudocode"}
            elif stage == "rewrite":
                try:
                    s = run_rewrite(P, args, redo, client)
                except ModelError as e:
                    plog(P, f"STOPPED: {e}")
                    return 2
                info = {"model": s.get("model", ""),
                        "note": f"{s['done']}/{s['functions']} rewritten"}
                if s["stop"]:
                    mark_stage(P, stage, done=False, **info)
                    break
                if not s["done"]:
                    plog(P, "  nothing has been rewritten yet, so there's nothing to build")
                    mark_stage(P, stage, done=False, **info)
                    break
            elif stage == "split":
                redo_split = bool({"split", "fix"} & redo)
                if redo_split and P.manifest.exists():
                    snapshot(P, "redo-build", [P.build / "funcs", P.build / "quarantine",
                                               P.manifest, P.build / "shared.h",
                                               P.build / "globals.cpp", P.build / "stubs.cpp"])
                records = build_split(cfg, redo_split)
                info = {"note": f"{sum(1 for r in records.values() if r.compiles)}/"
                                f"{len(records)} compile after the sweep"}
            elif stage in ("fix", "recover", "link", "improve", "organize"):
                if records is None:
                    records = load_manifest(cfg)
                if stage == "improve":
                    s = run_improve(P, cfg, records, args)
                    info = {"model": s.get("model", ""),
                            "note": f"score {s['score_before']} → {s['score_after']}, "
                                    f"{s['kept']} change(s)"}
                elif stage == "organize":
                    s = run_organize(P, cfg, records, args)
                    info = {"model": cfg.fix_model_used or "",
                            "note": (f"{s['modules']} modules, {s['classes']} classes"
                                     if s.get("written") else "final/ not updated")}
                    if not s.get("written"):
                        mark_stage(P, stage, done=False, **info)
                        ran_something = True
                        continue
                elif stage == "fix":
                    build_fix(cfg, records)
                    info = {"model": cfg.fix_model_used or ""}
                elif stage == "recover":
                    build_recover(cfg, records)
                    info = {"model": cfg.fix_model_used or ""}
                else:
                    ok = build_link(cfg, records)
                    info = {"note": "linked" if ok else "incomplete"}
            ran_something = True
            if client.calls > calls0:
                share = use.share()
                plog(P, f"  {stage}: {client.calls - calls0} model request(s); the model was "
                        f"busy {share * 100:.0f}% of the stage's {fmt_duration(time.time() - t0)}"
                        if share is not None else "")
                info["model_busy"] = round(share * 100) if share is not None else None
            mark_stage(P, stage, done=True, seconds=round(time.time() - t0), **info)
    except KeyboardInterrupt:
        STOPPING.set()
        if BAR["p"] is not None:
            BAR["p"].close()
        if records is not None:
            save_manifest(cfg, records)
        try:
            error_summary(P, records, cfg)
        except Exception:
            pass
        plog(P, "Paused. Run the same command to carry on from here.")
        write_report(P)
        sys.stdout.flush()
        if threading.active_count() > 1 and "pytest" not in sys.modules:
            os._exit(130)                 # don't wait for replies still being written
        return 130
    except SystemExit:
        if records is not None:
            save_manifest(cfg, records)
        write_report(P)
        raise
    data = write_report(P)
    error_summary(P, records, cfg)
    bd, lk = data.get("build") or {}, data.get("link") or {}
    plog(P, "=" * 60)
    if bd:
        plog(P, f"SUMMARY: {bd['compile']}/{bd['functions']} functions compile, "
                f"{bd['quarantined']} quarantined, {bd['rederived']} re-derived, "
                f"link={'OK' if lk.get('ok') else 'INCOMPLETE' if lk else 'not run'}")
    plog(P, f"Report: {P.report_md}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    # (stage choices are written out, not STAGES, so the AI Harness Run settings
    # form can read them and show a dropdown)
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_argument_group("pipeline")
    g.add_argument("--workdir", type=Path, default=Path("./decomp_project"),
                   help="project folder for everything this pipeline writes")
    g.add_argument("--from", dest="from_stage", choices=["export", "rewrite", "split", "fix", "recover", "link", "improve",
                            "organize"], default=None,
                   help="start at this stage (earlier stages must have run)")
    g.add_argument("--to", dest="to_stage", choices=["export", "rewrite", "split", "fix", "recover", "link", "improve",
                            "organize"], default=None,
                   help="stop after this stage")
    g.add_argument("--redo", action="append", nargs="?", const="rewrite", choices=["export", "rewrite", "split", "fix", "recover", "link", "improve",
                            "organize"],
                   help="do a stage's work again, replacing results in place (never "
                        "deletes; snapshots first). Bare --redo means --redo rewrite. "
                        "Repeatable")
    g.add_argument("--redo-suspect", action="store_true",
                   help="rewrite again only the functions flagged for a second look")
    g.add_argument("--no-snapshot", action="store_true",
                   help="don't copy current files to snapshots/ before a redo replaces them")
    g.add_argument("--pause-between-stages", action="store_true",
                   help="wait for Enter before each stage that uses the model, so you can "
                        "load a different model in LM Studio")
    g.add_argument("--force", action="store_true",
                   help="continue past a failed header gate / systemic preflight / missing "
                        "model, and ignore another run's lock")
    g.add_argument("--adopt-rewrite", type=Path, default=None, metavar="DIR",
                   help="copy in an old pseudo_to_cpp.py output folder (--out)")
    g.add_argument("--adopt-build", type=Path, default=None, metavar="DIR",
                   help="copy in an old DECOMP_FIXER.py --workdir")

    g = ap.add_argument_group("model")
    g.add_argument("--backend", choices=["lmstudio", "ollama"], default="lmstudio")
    g.add_argument("--api", default=None,
                   help="server address if it isn't the usual one "
                        "(default: $OPENAI_BASE_URL or http://localhost:1234/v1)")

    g = ap.add_argument_group("export (Ghidra)")
    g.add_argument("--ghidra", default="http://127.0.0.1:8080/",
                   help="Ghidra MCP/HTTP plugin address")
    g.add_argument("--headless-export", action="store_true",
                   help="export with analyzeHeadless instead of the plugin (needs --project)")
    g.add_argument("--ghidra-home", default=None,
                   help="Ghidra install folder (the one with support/analyzeHeadless); "
                        "default $GHIDRA_INSTALL_DIR or autodiscovery")
    g.add_argument("--project", default=None,
                   help="Ghidra project (.gpr or its folder); implies --headless-export")
    g.add_argument("--program", default=None,
                   help="program inside the project (default: every program)")
    g.add_argument("--export-parallel", type=int, default=0,
                   help="parallel requests to the plugin while exporting (default max(8, --parallel))")
    g.add_argument("--export-only", action="store_true",
                   help="complete the export and stop (same as --to export)")
    g.add_argument("--emit-ghidra-script", nargs="?", const="", default=None, metavar="PATH",
                   help="write the GhidraScript for Ghidra's Script Manager (default "
                        "<workdir>/ghidra/GhidraExport.java) and exit")
    g.add_argument("--refresh-ghidra", action="store_true", help=argparse.SUPPRESS)

    g = ap.add_argument_group("rewrite")
    g.add_argument("--ctx", type=int, default=16384,
                   help="how much text the model can take in at once (tokens)")
    g.add_argument("--max", type=int, default=None, help="stop after N functions")
    g.add_argument("--functions", nargs="+", help="only these functions (names or addresses)")
    g.add_argument("--comments", action="store_true", help="let the model keep comments")
    g.add_argument("--parallel", type=int, default=1,
                   help="requests the model works on at once, in every stage (match LM "
                        "Studio's parallel setting)")
    g.add_argument("--workers", type=int, default=min(8, max(2, (os.cpu_count() or 2) - 1)),
                   help="functions prepared at once in the fix / recover / improve stages: "
                        "while one waits for the model the others compile and test, so the "
                        "model always has its next request ready")
    g.add_argument("--auto-parallel", action="store_true",
                   help="adjust --parallel by watching the model's queue")
    g.add_argument("--max-parallel", type=int, default=16)
    g.add_argument("--auto-every", type=float, default=5, help="minutes between steps up")
    g.add_argument("--no-retry", action="store_true",
                   help="don't ask a second time when a reply is unusable")
    g.add_argument("--retry-quality", action="store_true",
                   help="also retry replies that still have decompiler names or strings")
    g.add_argument("--tiny", type=int, default=0,
                   help="copy functions with at most N simple statements without the model")
    g.add_argument("--no-split", action="store_true",
                   help="leave functions too big for --ctx for later instead of splitting")
    g.add_argument("--rewrite-compile-check", action="store_true",
                   help="compile each rewrite on its own and fix it there too (off by "
                        "default: the build compiles against the real shared.h)")
    g.add_argument("--rewrite-retries", dest="compile_retries", type=int, default=3,
                   help="fix attempts per function for --rewrite-compile-check")
    g.add_argument("--fix-mode", choices=["edit", "rewrite"], default="edit",
                   help="how --rewrite-compile-check repairs: edit the failing lines, or "
                        "regenerate the whole function")
    g.add_argument("--fix-steps", choices=["chain", "single"], default="chain",
                   help="chain: goal/diagnose/plan/edit; single: just the edit")

    g = ap.add_argument_group("build (split / fix / recover / link)")
    g.add_argument("--cxx", default="auto", help="C++ compiler: auto (clang++, else g++), "
                                                 "a name or a path")
    g.add_argument("--std", default="c++17")
    g.add_argument("--libclang", default=None, help="path to libclang .dylib/.so")
    g.add_argument("--callgraph", type=Path, default=None,
                   help="call graph for dependency order (default ghidra/callgraph.json)")
    g.add_argument("--fix-attempts", type=int, default=6,
                   help="small edits the model may try per function that doesn't compile")
    g.add_argument("--flag", action="append", default=[], dest="extra_flags",
                   help="extra compile flag (repeatable), e.g. --flag -I/path")
    g.add_argument("--stub-all-missing", action="store_true", dest="stub_all",
                   help="at link time, stub EVERY undefined symbol that has a prototype")
    g.add_argument("--no-pseudo", action="store_true",
                   help="skip rebuilding quarantined functions from pseudocode")
    g.add_argument("--retry-quarantined", action="store_true",
                   help="retry recovery on functions already tried (same as --redo recover)")
    g.add_argument("--model-ctx-chars", type=int, default=None,
                   help="recover stage's prompt budget in characters; bigger functions are "
                        "patched a few lines at a time instead of rewritten (default: worked "
                        "out from --ctx)")
    g.add_argument("--resume", action="store_true", help=argparse.SUPPRESS)  # always on now

    g = ap.add_argument_group("improve / organize")
    g.add_argument("--improve-rounds", type=int, default=3,
                   help="rounds of checks and small fixes (a round with nothing to fix ends "
                        "the stage early)")
    g.add_argument("--improve-minutes", type=float, default=0,
                   help="stop improving after this many minutes (0: no limit)")
    g.add_argument("--improve-per-function", type=int, default=6,
                   help="most small fixes per function per round (spreads the work)")
    g.add_argument("--improve-checks", default=None,
                   help="only these checks, comma-separated: " + ", ".join(CHECK_NAMES))
    g.add_argument("--allow-privacy-findings", action="store_true",
                   help="write final/ even if the privacy check still finds something")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    args.parallel = max(1, args.parallel)
    args.compile_retries = max(0, args.compile_retries)
    if args.auto_parallel:
        args.max_parallel = max(args.parallel, args.max_parallel)
    args.model_in_use = None
    if args.improve_checks:
        bad = set(args.improve_checks.split(",")) - set(CHECK_NAMES)
        if bad:
            sys.exit(f"--improve-checks: unknown check(s) {', '.join(sorted(bad))}; "
                     f"choose from {', '.join(CHECK_NAMES)}")
    # fresh module state (matters when called more than once in one process)
    GATE["gate"] = GATE["tuner"] = None
    MODEL_STATS.update(calls=0, no_answer=0, rejected=0)
    MODEL_ACTIVITY.update(errors=0, thinking_only=0)
    _PSEUDO_CACHE.clear()

    if args.emit_ghidra_script is not None:
        P = Paths(args.workdir.expanduser().resolve())
        P.make()
        dest = Path(args.emit_ghidra_script) if args.emit_ghidra_script \
            else P.ghidra / "GhidraExport.java"
        dest.write_text(GHIDRA_EXPORT_SCRIPT.replace(
            'static final String DEFAULT_OUT = "";',
            'static final String DEFAULT_OUT = "%s";' % str(P.ghidra).replace("\\", "\\\\")))
        print(f"Wrote {dest}. In Ghidra: Window > Script Manager > add this folder, then run "
              f"GhidraExport.java with your program open. It writes {P.export} (resuming "
              f"any existing one). Then run this pipeline without --emit-ghidra-script.")
        return 0
    return run_pipeline(args)


if __name__ == "__main__":
    sys.exit(main())
