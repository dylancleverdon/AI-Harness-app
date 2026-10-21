import argparse
import webbrowser

import uvicorn

from . import updater
from .config import PORT, ensure_dirs


def main():
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
