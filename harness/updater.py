"""Self-update via git: the install is a git checkout, so updating is a fast-forward pull."""
import hashlib
import os
import subprocess
import sys
import threading
import time

from .config import DATA_DIR, ROOT


def _git(*args, timeout=60):
    r = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout + r.stderr).strip()


def version():
    code, out = _git("log", "-1", "--format=%h %cs")
    return out if code == 0 else "unknown"


def check():
    """Fetch and report how far behind the upstream branch we are."""
    try:
        if _git("rev-parse", "--git-dir")[0] != 0:
            return {"available": False, "error": "not a git checkout"}
        code, out = _git("fetch", "--quiet", timeout=20)
        if code != 0:
            return {"available": False, "error": f"fetch failed: {out[:200]}"}
        code, behind = _git("rev-list", "--count", "HEAD..@{u}")
        if code != 0:
            return {"available": False, "error": "no upstream branch to track"}
        n = int(behind)
        changes = _git("log", "--format=%s", "HEAD..@{u}")[1].splitlines() if n else []
        return {"available": n > 0, "behind": n, "changes": changes[:15], "error": None}
    except Exception as e:
        return {"available": False, "error": str(e)}


def apply():
    """Pull the latest code (local edits are auto-stashed). Caller restarts afterwards."""
    code, out = _git("pull", "--rebase", "--autostash", timeout=120)
    return {"ok": code == 0, "log": out[-1500:], "version": version()}


def ensure_deps():
    """Reinstall requirements.txt when it changed since last start (e.g. after an update)."""
    req = ROOT / "requirements.txt"
    marker = DATA_DIR / ".requirements.sha"
    digest = hashlib.sha256(req.read_bytes()).hexdigest()
    try:
        if marker.read_text() == digest:
            return
    except OSError:
        pass
    print("Installing updated dependencies...")
    r = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", str(req)])
    if r.returncode == 0:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        marker.write_text(digest)


def restart_soon():
    def go():
        time.sleep(0.6)
        os.execv(sys.executable, [sys.executable, "-m", "harness"])
    threading.Thread(target=go, daemon=True).start()
