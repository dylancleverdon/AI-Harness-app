"""Thin client for the LM Studio local server (OpenAI-compatible + /api/v0 REST)."""
import shutil
import subprocess

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


def unload_all():
    """Unload every model using the `lms` CLI that ships with LM Studio."""
    lms = shutil.which("lms") or str(__import__("pathlib").Path("~/.lmstudio/bin/lms").expanduser())
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
