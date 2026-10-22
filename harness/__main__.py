import argparse
import os
import subprocess
import sys
import webbrowser

import uvicorn

from . import updater
from .config import PORT, ensure_dirs


def _sysctl(name):
    try:
        return subprocess.run(["sysctl", "-n", name], capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def native_restart_argv():
    """On an Apple Silicon Mac, an app whose program is a script (like AI Harness.app)
    is started under Rosetta, as Intel, and so is everything it starts: the compiler
    then builds Intel code. If this Python can run natively, the command to start it
    again that way; else None. Tried once (AIHARNESS_NATIVE_TRIED)."""
    if sys.platform != "darwin" or os.environ.get("AIHARNESS_NATIVE_TRIED"):
        return None
    if _sysctl("sysctl.proc_translated") != "1" or _sysctl("hw.optional.arm64") != "1":
        return None
    try:          # does this Python have Apple Silicon code? Run it that way once to see
        ok = subprocess.run(["/usr/bin/arch", "-arm64", sys.executable, "-c", "pass"],
                            capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.SubprocessError):
        ok = False
    if not ok:
        return None
    return ["/usr/bin/arch", "-arm64", sys.executable, "-m", "harness", *sys.argv[1:]]


def main():
    argv = native_restart_argv()
    if argv:
        print("AI Harness was started under Rosetta (as Intel): starting again natively (Apple Silicon)",
              flush=True)
        os.environ["AIHARNESS_NATIVE_TRIED"] = "1"
        os.execv(argv[0], argv)
    ap = argparse.ArgumentParser(prog="harness")
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--open", action="store_true", help="open the UI in your browser")
    args = ap.parse_args()
    ensure_dirs()
    updater.ensure_deps()
    if args.open:
        webbrowser.open(f"http://127.0.0.1:{args.port}")
    from .config import settings
    from . import remote
    # remote access (Settings > Remote access): listen on the network too; the
    # server itself still only answers this Mac and signed-in Tailscale devices
    host = "0.0.0.0" if settings.get("remote_access") and remote.has_password() else "127.0.0.1"
    if host != "127.0.0.1":
        import os
        os.environ["AIHARNESS_REMOTE"] = "1"
    uvicorn.run("harness.server:app", host=host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
