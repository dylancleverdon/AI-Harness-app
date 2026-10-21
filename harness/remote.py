"""Remote access from your phone (or another computer) over Tailscale.

Off by default. When it's on (Settings > Remote access, then restart), the
server also listens on the network, but only answers:
- this Mac itself (as before), and
- devices on your Tailscale network (100.64.0.0/10, fd7a:115c:a1e0::/48), after
  they sign in with the password set on this Mac.
Anything else (other devices on your Wi-Fi, the internet) is refused. Turning
remote access on and setting the password can only be done on this Mac.
"""
import hashlib
import hmac
import ipaddress
import json
import os
import secrets
import shutil
import subprocess
import threading
import time

from .config import DATA_DIR, settings

SESSIONS_FILE = DATA_DIR / ".remote_sessions.json"
COOKIE = "harness_session"
SESSION_DAYS = 30
TAILNET = [ipaddress.ip_network("100.64.0.0/10"), ipaddress.ip_network("fd7a:115c:a1e0::/48")]
_lock = threading.Lock()
_fails: dict = {}                 # client ip -> [count, first failure time]


def is_local(ip: str) -> bool:
    try:
        return ipaddress.ip_address(ip).is_loopback
    except ValueError:
        return ip in ("testclient", "testserver")


def is_tailnet(ip: str) -> bool:
    try:
        a = ipaddress.ip_address(ip)
    except ValueError:
        return False
    if a.version == 6 and a.ipv4_mapped:
        a = a.ipv4_mapped
    return any(a in n for n in TAILNET)


def _hash(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000).hex()


def set_password(password: str) -> None:
    salt = secrets.token_bytes(16)
    settings.update({"remote_password": f"{salt.hex()}${_hash(password, salt)}"})
    with _lock:                                   # a new password signs every device out
        _save({})


def has_password() -> bool:
    return "$" in settings.get("remote_password")


def check_password(password: str) -> bool:
    stored = settings.get("remote_password")
    if "$" not in stored:
        return False
    salt, want = stored.split("$", 1)
    return hmac.compare_digest(_hash(password, bytes.fromhex(salt)), want)


def _load() -> dict:
    try:
        return json.loads(SESSIONS_FILE.read_text())
    except (OSError, ValueError):
        return {}


def _save(data: dict) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        SESSIONS_FILE.write_text(json.dumps(data))
        os.chmod(SESSIONS_FILE, 0o600)
    except OSError:
        pass


def login(ip: str, password: str):
    """A session token if the password is right. Too many wrong tries from one
    device lock it out for 15 minutes."""
    now = time.time()
    with _lock:
        n, since = _fails.get(ip, [0, now])
        if now - since > 900:
            n, since = 0, now
        if n >= 10:
            return None
    if not check_password(password):
        with _lock:
            _fails[ip] = [n + 1, since]
        return None
    token = secrets.token_urlsafe(32)
    with _lock:
        _fails.pop(ip, None)
        data = {k: v for k, v in _load().items() if v > now}
        data[hashlib.sha256(token.encode()).hexdigest()] = now + SESSION_DAYS * 86400
        _save(data)
    return token


def valid_session(token) -> bool:
    if not token:
        return False
    with _lock:
        exp = _load().get(hashlib.sha256(token.encode()).hexdigest())
    return bool(exp and exp > time.time())


def logout_all() -> None:
    with _lock:
        _save({})


def _tailscale_cli():
    for p in (shutil.which("tailscale"), "/Applications/Tailscale.app/Contents/MacOS/Tailscale",
              "/usr/local/bin/tailscale", "/opt/homebrew/bin/tailscale"):
        if p and os.path.exists(p):
            return p
    return None


def tailscale_info() -> dict:
    """This Mac's Tailscale address and name, if Tailscale is installed and up."""
    cli = _tailscale_cli()
    if not cli:
        return {"installed": False}
    try:
        out = subprocess.run([cli, "status", "--json"], capture_output=True, text=True,
                             timeout=8).stdout
        st = json.loads(out)
        me = st.get("Self") or {}
        ips = [i for i in (me.get("TailscaleIPs") or []) if ":" not in i]
        return {"installed": True, "running": st.get("BackendState") == "Running",
                "ip": ips[0] if ips else None,
                "name": (me.get("DNSName") or "").rstrip(".") or None}
    except Exception as e:
        return {"installed": True, "running": False, "error": str(e)[:200]}
