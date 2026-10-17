import asyncio
import json
import subprocess
import sys
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import ai_edit, lmstudio, memory, updater
from .config import DATA_DIR, SCRIPTS_DIR, settings
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
            "settings": settings.get(), "scripts_dir": str(SCRIPTS_DIR), "update": _update}


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
    pkg = body.get("package", "")
    if not pkg or pkg.startswith("-") or " " in pkg:
        raise HTTPException(400, "bad package name")
    r = subprocess.run([sys.executable, "-m", "pip", "install", pkg], capture_output=True, text=True)
    return {"ok": r.returncode == 0, "log": (r.stdout + r.stderr)[-1500:]}


# ---- AI edit ----------------------------------------------------------------
@app.post("/api/ai-edit")
def ai_edit_run(body: dict = Body(...)):
    """Streams progress events (SSE); the final 'done' event carries the edited text and a diff."""
    def gen():
        level = lambda: (monitor.latest or {}).get("level", "green")
        for ev in ai_edit.edit_stream(body.get("name", "script.py"), body.get("content", ""),
                                      body.get("instruction", ""), body.get("model") or None, level):
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
@app.post("/api/runs")
def start_run(body: dict = Body(...)):
    try:
        run = runs.start(body["script"], body.get("args", ""))
    except FileNotFoundError:
        raise HTTPException(404, "script not found")
    return run.summary()


@app.get("/api/runs")
def list_runs():
    return runs.history()


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    d = runs.load(run_id)
    if not d:
        raise HTTPException(404)
    return d


@app.post("/api/runs/{run_id}/stop")
def stop_run(run_id: str):
    return {"ok": runs.stop(run_id)}


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
        while True:
            with run.lock:
                new = run.lines[i:]
            for line in new:
                yield f"data: {json.dumps(line)}\n\n"
            i += len(new)
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
                       "active": [{"id": r.id, "script": r.script,
                                   "rss_mb": r.mem[-1]["rss_mb"] if r.mem else 0,
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


app.mount("/static", StaticFiles(directory=STATIC), name="static")
