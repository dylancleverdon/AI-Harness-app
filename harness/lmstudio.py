"""Thin client for the LM Studio local server (OpenAI-compatible + /api/v0 REST)."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import httpx

from .config import settings


def base_url():
    return settings.get("lmstudio_url").rstrip("/")


def status():
    """Returns {ok, error, models:[{id, loaded, type, size...}]}."""
    base = base_url()
    try:
        # /api/v0/models includes load state; fall back to the plain OpenAI listing.
        r = httpx.get(f"{base}/api/v0/models", timeout=2.5)
        if r.status_code == 200:
            models = [
                {"id": m["id"], "loaded": m.get("state") == "loaded", "type": m.get("type", ""),
                 "arch": m.get("arch", ""), "quant": m.get("quantization", ""),
                 "ctx": m.get("loaded_context_length") or m.get("max_context_length")}
                for m in r.json().get("data", [])
            ]
            return {"ok": True, "error": None, "models": models}
        r = httpx.get(f"{base}/v1/models", timeout=2.5)
        r.raise_for_status()
        return {"ok": True, "error": None,
                "models": [{"id": m["id"], "loaded": True, "type": "", "arch": "", "quant": "", "ctx": None}
                           for m in r.json().get("data", [])]}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}", "models": []}


def loaded_model():
    for m in status()["models"]:
        if m["loaded"] and m["type"] != "embeddings":
            return m["id"]
    return ""


def find_lms():
    """The `lms` command-line tool that ships with LM Studio (PATH first, then its default install folder)."""
    import os
    extra = os.pathsep.join(["/opt/homebrew/bin", "/usr/local/bin", str(Path.home() / ".lmstudio" / "bin")])
    return shutil.which("lms", path=os.environ.get("PATH", "") + os.pathsep + extra)


def _model_from_json(it):
    key = it.get("modelKey") or it.get("indexedModelIdentifier") or it.get("path") or it.get("id")
    if not key:
        return None
    q = it.get("quantization")
    q = q.get("name") if isinstance(q, dict) else q
    size = it.get("sizeBytes")
    return {"id": key, "name": it.get("displayName") or key, "type": it.get("type") or "llm",
            "params": it.get("paramsString") or "", "quant": q or "", "arch": it.get("architecture") or "",
            "format": it.get("format") or "", "size_gb": round(size / 1e9, 1) if isinstance(size, (int, float)) else None,
            "ctx": it.get("maxContextLength")}


def parse_lms_ls(text):
    """Models from `lms ls --json` (a list, or {"models": [...]}); falls back to the plain table."""
    try:
        data = json.loads(text)
        items = data if isinstance(data, list) else (data.get("models") or data.get("data") or [])
        return [m for m in (_model_from_json(i) for i in items if isinstance(i, dict)) if m]
    except ValueError:
        pass
    out, section = [], None
    for line in text.splitlines():
        s = line.strip()
        if re.match(r"^(LLM|EMBEDDING)s?\b", s, re.I):
            section = "embeddings" if s.upper().startswith("EMBEDDING") else "llm"
        elif section and s and not s.lower().startswith("you have") and not s.startswith(("-", "=")):
            cols = s.split()
            out.append({"id": cols[0], "name": cols[0], "type": section, "params": cols[1] if len(cols) > 3 else "",
                        "quant": "", "arch": cols[2] if len(cols) > 3 else "", "format": "",
                        "size_gb": None, "ctx": None})
    return out


def downloaded_models():
    """Every model downloaded in LM Studio, with which are loaded now. Works with the server off (uses `lms ls`);
    falls back to the server's model list. Returns {models, source, error}."""
    models, source, error = [], "none", ""
    lms = find_lms()
    if lms:
        for args in (["ls", "--json"], ["ls"]):
            try:
                r = subprocess.run([lms, *args], capture_output=True, text=True, timeout=25)
                models = parse_lms_ls(r.stdout) if r.returncode == 0 else []
            except (OSError, subprocess.SubprocessError) as e:
                error = str(e)
                models = []
            if models:
                source = "lms"
                break
    live = status()
    loaded = {m["id"] for m in live["models"] if m["loaded"]}
    if not models and live["ok"]:  # no lms: at least list what the running server knows about
        models = [{"id": m["id"], "name": m["id"], "type": m["type"] or "llm", "params": "", "quant": m["quant"] or "",
                   "arch": m["arch"] or "", "format": "", "size_gb": None, "ctx": m["ctx"]} for m in live["models"]]
        source = "server"
    if not models:
        error = error or ("LM Studio's `lms` tool wasn't found and the server isn't running. Open LM Studio once, or "
                          "run  ~/.lmstudio/bin/lms bootstrap")
    for m in models:
        m["loaded"] = m["id"] in loaded
    models.sort(key=lambda m: (not m["loaded"], m["type"] != "llm", m["id"].lower()))
    return {"models": models, "source": source, "error": error if not models else ""}


def unload_all():
    """Unload every model using the `lms` CLI that ships with LM Studio."""
    lms = find_lms() or str(Path("~/.lmstudio/bin/lms").expanduser())
    try:
        out = subprocess.run([lms, "unload", "--all"], capture_output=True, text=True, timeout=30)
        return out.returncode == 0, (out.stdout + out.stderr).strip()
    except (OSError, subprocess.SubprocessError) as e:
        return False, str(e)


async def chat_stream(payload):
    """Yields raw SSE lines from LM Studio's chat completions endpoint."""
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("POST", f"{base_url()}/v1/chat/completions",
                                 json={**payload, "stream": True}) as r:
            if r.status_code != 200:
                yield 'data: {"error": "%s"}\n\n' % (await r.aread()).decode()[:300].replace('"', "'")
                return
            async for line in r.aiter_lines():
                if line:
                    yield line + "\n\n"
