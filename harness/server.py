import asyncio
import json
import re
import subprocess
import sys
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import ai_edit, lmstudio, memory, params, updater
from .config import DATA_DIR, SCRIPTS_DIR, script_python, settings
from .runner import RunManager, report_markdown

STATIC = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(_app):
    monitor.start()
    if settings.get("auto_update"):
        threading.Thread(target=lambda: _update.update(updater.check()), daemon=True).start()
    yield


app = FastAPI(title="AI Harness", lifespan=lifespan)
runs = RunManager()
monitor = memory.Monitor(on_tick=runs.on_tick)
VERSION = updater.version()
_update = {"available": False}


def _script_path(name):
    p = (SCRIPTS_DIR / name).resolve()
    if SCRIPTS_DIR.resolve() not in p.parents or p.suffix != ".py":
        raise HTTPException(400, "script must be a .py file inside the scripts folder")
    return p


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-store"})


@app.get("/api/ping")
def ping():
    return {"ok": True}


@app.get("/api/status")
def status():
    return {"version": VERSION, "lmstudio": lmstudio.status(), "memory": monitor.latest,
            "settings": settings.get(), "scripts_dir": str(SCRIPTS_DIR), "update": _update,
            "python": script_python(), "term_cwd": str(runs.term_cwd),
            "sensor_tools": monitor.sensors.tools()}


@app.get("/api/settings")
def get_settings():
    return settings.get()


@app.put("/api/settings")
def put_settings(patch: dict = Body(...)):
    return settings.update(patch)


# ---- scripts --------------------------------------------------------------
@app.get("/api/scripts")
def list_scripts():
    return sorted(str(p.relative_to(SCRIPTS_DIR)) for p in SCRIPTS_DIR.rglob("*.py")
                  if "__pycache__" not in p.parts)


@app.get("/api/scripts/{name:path}")
def read_script(name: str):
    p = _script_path(name)
    if not p.is_file():
        raise HTTPException(404)
    return {"name": name, "content": p.read_text()}


@app.put("/api/scripts/{name:path}")
def write_script(name: str, body: dict = Body(...)):
    p = _script_path(name)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body.get("content", ""))
    return {"ok": True}


@app.delete("/api/scripts/{name:path}")
def delete_script(name: str):
    _script_path(name).unlink(missing_ok=True)
    return {"ok": True}


@app.post("/api/pip")
def pip_install(body: dict = Body(...)):
    """Install into the interpreter scripts actually run with. Accepts one or several space-separated packages."""
    pkgs = str(body.get("package", "")).split()
    if not pkgs or not all(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._\-\[\],<>=!~]*", p) for p in pkgs):
        raise HTTPException(400, "bad package name")
    py = script_python()
    try:
        r = subprocess.run([py, "-m", "pip", "install", *pkgs], capture_output=True, text=True, timeout=900)
    except (OSError, subprocess.SubprocessError) as e:
        return {"ok": False, "python": py, "log": f"Could not run pip with {py}: {e}"}
    return {"ok": r.returncode == 0, "python": py, "log": (r.stdout + r.stderr)[-2000:]}


# ---- AI edit ----------------------------------------------------------------
@app.post("/api/ai-edit")
def ai_edit_run(body: dict = Body(...)):
    """Streams progress events (SSE); the final 'done' event carries the edited text and a diff."""
    def gen():
        level = lambda: (monitor.latest or {}).get("level", "green")
        for ev in ai_edit.edit_stream(body.get("name", "script.py"), body.get("content", ""),
                                      body.get("instruction", ""), body.get("model") or None,
                                      "rewrite" if body.get("mode") == "rewrite" else "edit", level):
            if ev.get("type") == "done" and ev.get("review"):  # keep a copy of the review on disk
                d = DATA_DIR / "ai-edit-reviews"
                d.mkdir(parents=True, exist_ok=True)
                f = d / f"{Path(body.get('name', 'script')).stem}-{time.strftime('%Y%m%d-%H%M%S')}.md"
                f.write_text(ev["review"])
                ev["review_path"] = str(f)
            yield f"data: {json.dumps(ev)}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/api/ai-edit/apply")
def ai_edit_apply(body: dict = Body(...)):
    """Writes the edited script, first saving a timestamped backup of the old version."""
    p = _script_path(body["name"])
    backup = ""
    if p.is_file():
        d = DATA_DIR / "backups"
        d.mkdir(parents=True, exist_ok=True)
        b = d / f"{p.stem}.{time.strftime('%Y%m%d-%H%M%S')}.py"
        b.write_text(p.read_text())
        backup = str(b)
    p.write_text(body["content"])
    return {"ok": True, "backup": backup}


# ---- runs -----------------------------------------------------------------
@app.get("/api/script-settings/{name:path}")
def script_settings(name: str):
    """Options discovered in the script (argparse) plus the values used last time."""
    p = _script_path(name)
    if not p.is_file():
        raise HTTPException(404)
    return {"params": params.parse_params(p.read_text()), **params.get_saved(name)}


@app.put("/api/script-settings/{name:path}")
def save_script_settings(name: str, body: dict = Body(...)):
    _script_path(name)
    return params.save(name, body)


@app.post("/api/runs")
def start_run(body: dict = Body(...)):
    name = body["script"]
    p = _script_path(name)
    if not p.is_file():
        raise HTTPException(404, "script not found")
    src = p.read_text()
    plist = params.parse_params(src)
    saved = params.get_saved(name)
    values = body.get("values", saved["values"])
    if "values" in body or "extra" in body or "env" in body:  # remember what was used for next time
        params.save(name, {"values": values, "extra": body.get("extra", saved["extra"]),
                           "env": body.get("env", saved["env"])})
    extra = body.get("extra", body.get("args", saved["extra"]))
    env = params.parse_env(body.get("env", saved["env"]))
    run = runs.start(name, extra, params.build_argv(plist, values), env,
                     params.watch_dirs(plist, values, src, SCRIPTS_DIR))
    return run.summary()


@app.post("/api/pick")
def pick_path(body: dict = Body(...)):
    """Open the native macOS file/folder chooser and return the chosen absolute path ('' if cancelled)."""
    kind = "folder" if body.get("kind") == "folder" else "file"
    if sys.platform != "darwin":
        raise HTTPException(501, "The file picker only works on macOS - type the path instead.")
    start = Path(body.get("start") or "~").expanduser()
    while not start.is_dir() and start != start.parent:
        start = start.parent
    script = ('tell application "System Events"\nactivate\n'
              f'set p to POSIX path of (choose {kind} with prompt "Choose a {kind} for this script" '
              f'default location (POSIX file "{start}"))\nend tell\nreturn p')
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=600)
    return {"path": r.stdout.strip().rstrip("/") if r.returncode == 0 and kind == "folder" else r.stdout.strip()}


@app.post("/api/display-sleep")
def display_sleep():
    """Turn the screen off right now (`pmset displaysleepnow`, no admin rights needed). The Mac itself keeps
    running; if Keep awake is on it stays awake. Moving the mouse or pressing a key wakes the screen."""
    if sys.platform != "darwin":
        raise HTTPException(501, "Turning the screen off only works on macOS.")
    r = subprocess.run(["pmset", "displaysleepnow"], capture_output=True, text=True, timeout=10)
    if r.returncode != 0:
        raise HTTPException(500, (r.stderr or r.stdout or "pmset failed").strip())
    return {"ok": True}


@app.post("/api/reveal")
def reveal(body: dict = Body(...)):
    """Show a file a run produced in Finder (macOS) - only files listed on a run are allowed."""
    d = runs.load(body.get("run", ""))
    path = body.get("path", "")
    if not d or path not in [f["path"] for f in d.get("files", [])]:
        raise HTTPException(403, "not a file from this run")
    if sys.platform == "darwin":
        subprocess.Popen(["open", "-R", path])
    return {"ok": sys.platform == "darwin"}


@app.get("/api/run-file")
def run_file(run: str, path: str):
    """Preview (first 200 KB) of a text file a run produced."""
    d = runs.load(run)
    if not d or path not in [f["path"] for f in d.get("files", [])]:
        raise HTTPException(403, "not a file from this run")
    with open(path, "rb") as f:
        data = f.read(200_000)
    return PlainTextResponse(data.decode("utf-8", errors="replace"))


@app.get("/api/runs")
def list_runs():
    return runs.history()


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    d = runs.load(run_id)
    if not d:
        raise HTTPException(404)
    return d


@app.post("/api/runs/{run_id}/input")
def run_input(run_id: str, body: dict = Body(...)):
    """Type into a running script's stdin (answers input() prompts). eof=true closes stdin (Ctrl-D)."""
    ok = runs.send_input(run_id, str(body.get("text", "")), bool(body.get("eof")))
    if not ok:
        raise HTTPException(409, "that run isn't running (or its input is closed)")
    return {"ok": True}


@app.post("/api/terminal")
def terminal(body: dict = Body(...)):
    """Console prompt: run a shell command in the terminal's folder (`cd` changes it)."""
    cmd = str(body.get("command", "")).strip()
    if not cmd:
        raise HTTPException(400, "empty command")
    if cmd == "cd" or cmd.startswith("cd "):
        ok, msg = runs.change_dir(cmd[3:].strip().strip("\"'") if cmd != "cd" else "")
        return {"cd": ok, "message": msg, "cwd": str(runs.term_cwd)}
    return {"run": runs.start_command(cmd).summary(), "cwd": str(runs.term_cwd)}


@app.post("/api/runs/{run_id}/stop")
def stop_run(run_id: str):
    return {"ok": runs.stop(run_id)}


@app.post("/api/runs/{run_id}/send-report")
def send_report(run_id: str):
    run = runs.runs.get(run_id)
    if run is None:
        d = runs.load(run_id)
        if not d:
            raise HTTPException(404, "no such run")
        from . import reports
        path = reports.find_report(d.get("output", ""))
        if not path:
            raise HTTPException(404, "this run didn't write a diagnostics report")
        return reports.send(path)
    res = runs._send_report(run, force=True)
    if res is None:
        raise HTTPException(404, "this run didn't write a diagnostics report")
    return res


@app.get("/api/runs/{run_id}/report", response_class=PlainTextResponse)
def run_report(run_id: str):
    d = runs.load(run_id)
    if not d:
        raise HTTPException(404)
    return report_markdown(d, VERSION, lmstudio.status(), monitor.latest or monitor.sample())


@app.get("/api/runs/{run_id}/stream")
async def run_stream(run_id: str):
    """Server-sent events: new output lines as they appear, then a final 'done' event."""
    run = runs.runs.get(run_id)
    if not run:
        raise HTTPException(404, "run not live")

    async def gen():
        i = 0
        last_live = None
        while True:
            with run.lock:
                new = run.lines[i:]
            for line in new:
                yield f"data: {json.dumps(line)}\n\n"
            i += len(new)
            live = run.live.get("err") or run.live.get("out") or ""
            if live != last_live and run.status == "running":
                last_live = live
                yield f"event: live\ndata: {json.dumps({'x': live})}\n\n"
            if run.status != "running" and not new:
                yield f"event: done\ndata: {json.dumps(run.summary())}\n\n"
                return
            await asyncio.sleep(0.15)

    return StreamingResponse(gen(), media_type="text/event-stream")


# ---- live telemetry -------------------------------------------------------
@app.get("/api/stream")
async def telemetry():
    async def gen():
        while True:
            payload = {"memory": monitor.latest, "events": runs.events[-5:],
                       "awake": runs.awake(),
                       "active": [{"id": r.id, "script": r.script, "started": r.started,
                                   "elapsed": round(time.time() - r.started),
                                   "rss_mb": r.mem[-1]["rss_mb"] if r.mem else 0, "cpu_pct": r.cpu_now,
                                   "peak_cpu": r.peak_cpu_pct,
                                   "peak_mb": r.peak_rss_mb} for r in runs.active()]}
            yield f"data: {json.dumps(payload)}\n\n"
            await asyncio.sleep(1)
    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/api/memory/history")
def memory_history():
    return list(monitor.history)


@app.get("/api/events")
def events():
    return runs.events


# ---- models / chat --------------------------------------------------------
@app.get("/api/models/downloaded")
def models_downloaded():
    """Downloaded LM Studio models (for the model dropdowns in Run settings)."""
    return lmstudio.downloaded_models()


@app.post("/api/models/unload")
def unload():
    ok, out = lmstudio.unload_all()
    return {"ok": ok, "log": out}


@app.post("/api/chat")
async def chat(body: dict = Body(...)):
    return StreamingResponse(lmstudio.chat_stream(body), media_type="text/event-stream")


# ---- updates --------------------------------------------------------------
@app.get("/api/update/check")
def update_check():
    _update.clear()
    _update.update(updater.check())
    return _update


@app.post("/api/update/apply")
def update_apply():
    res = updater.apply()
    if res["ok"]:
        _update.clear()
        _update["available"] = False
    return res


@app.post("/api/restart")
def restart(force: bool = False):
    if runs.active() and not force:
        raise HTTPException(409, "scripts are running; stop them first or force")
    updater.restart_soon()
    return {"ok": True}


@app.middleware("http")
async def local_only(request, call_next):
    """The server can run code, so refuse anything that isn't this app talking to itself: a Host check
    (blocks DNS rebinding) and a custom header on writes (a web page on another site can't set it)."""
    host = (request.headers.get("host") or "").split(":")[0]
    if host not in ("127.0.0.1", "localhost", "testserver"):
        return PlainTextResponse("forbidden host", status_code=403)
    if request.method in ("POST", "PUT", "DELETE"):
        # Browsers always attach Origin to cross-site writes and pages can't forge it, so a local Origin proves
        # the request came from this app (this also keeps an older, cached copy of the page working).
        origin = (request.headers.get("origin") or "").split("://")[-1].split(":")[0]
        if request.headers.get("x-harness") != "1" and origin not in ("127.0.0.1", "localhost"):
            return PlainTextResponse("Blocked: this request didn't come from the AI Harness page. "
                                     "Reload the page (Cmd+Shift+R) and try again.", status_code=403)
    response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache"  # always revalidate, so updates show up immediately
    return response


app.mount("/static", StaticFiles(directory=STATIC), name="static")
