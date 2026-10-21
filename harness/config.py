import json
import os
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("AIHARNESS_HOME", "~/AIHarness")).expanduser()
SCRIPTS_DIR = DATA_DIR / "scripts"
RUNS_DIR = DATA_DIR / "runs"
SETTINGS_FILE = DATA_DIR / "settings.json"
PORT = int(os.environ.get("AIHARNESS_PORT", "8765"))

DEFAULTS = {
    "lmstudio_url": "http://localhost:1234",
    "guard_enabled": True,
    "guard_trip_level": "orange",  # yellow | orange | red
    "yellow_below_pct": 30,  # available memory %, below this = yellow
    "orange_below_pct": 15,
    "red_below_pct": 8,
    "unload_models_on_trip": False,
    "use_pty": True,  # run scripts in a pseudo-terminal so they behave exactly like in Terminal (isatty, spinners)
    "thermal_guard": "off",  # off | serious | critical: stop scripts when the Mac reports this thermal state
    "keep_awake": True,  # macOS: stop the Mac sleeping while a script runs (caffeinate)
    "python": "",  # interpreter for scripts; empty = harness venv
    "auto_update": True,
    "auto_send_reports": True,  # send a script's diagnostics report (DIAGNOSTICS: line) when it ends
    "github_token": "",  # for sending reports, if git on this Mac can't push to GitHub
}


class Settings:
    def __init__(self):
        self._lock = threading.Lock()
        self._data = dict(DEFAULTS)
        try:
            saved = json.loads(SETTINGS_FILE.read_text())
            self._data.update({k: v for k, v in saved.items() if k in DEFAULTS})
        except (OSError, ValueError):
            pass

    def get(self, key=None):
        with self._lock:
            return dict(self._data) if key is None else self._data[key]

    def update(self, patch):
        with self._lock:
            for k, v in patch.items():
                if k in DEFAULTS and isinstance(v, type(DEFAULTS[k])):
                    self._data[k] = v
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            SETTINGS_FILE.write_text(json.dumps(self._data, indent=2))
            return dict(self._data)


settings = Settings()


def script_python():
    """The interpreter scripts run with (Settings > Python), else the app's own private virtualenv."""
    import sys
    return settings.get("python").strip() or sys.executable


def _sha(text):
    import hashlib
    return hashlib.sha256(text.encode()).hexdigest()


def ensure_dirs():
    """Create the data dirs and keep the example scripts current."""
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    sync_examples()


def sync_examples():
    """Copy the example scripts into the scripts folder, and bring the copies up to
    date when an update changes an example. Your own edits stay until the example
    itself changes; then the edited copy is backed up to backups/ before it's
    replaced, so an update never loses anything. Returns the names updated."""
    import time
    examples = ROOT / "scripts" / "examples"
    if not examples.is_dir():
        return []
    state_file = DATA_DIR / ".examples.json"
    try:
        state = json.loads(state_file.read_text())
    except (OSError, ValueError):
        state = {}
    first_run = not any(SCRIPTS_DIR.glob("*.py"))
    updated = []
    for f in sorted(examples.glob("*.py")):
        new = f.read_text()
        dest = SCRIPTS_DIR / f.name
        seen = state.get(f.name) if isinstance(state.get(f.name), dict) else None
        if not dest.exists():
            if first_run or seen:
                dest.write_text(new)          # a first run, or one we installed before
                state[f.name] = {"example": _sha(new), "copy": _sha(new)}
            continue
        cur = dest.read_text(errors="replace")
        if cur == new:
            state[f.name] = {"example": _sha(new), "copy": _sha(new)}
            continue
        if seen and seen.get("example") == _sha(new):
            continue                          # the example hasn't changed: keep your edits
        if not seen or seen.get("copy") != _sha(cur):     # edited here: keep a copy
            backup = DATA_DIR / "backups"
            backup.mkdir(parents=True, exist_ok=True)
            (backup / f"{dest.stem}-{time.strftime('%Y%m%d-%H%M%S')}.py").write_text(cur)
        dest.write_text(new)
        state[f.name] = {"example": _sha(new), "copy": _sha(new)}
        updated.append(f.name)
    try:
        state_file.write_text(json.dumps(state, indent=1))
    except OSError:
        pass
    return updated
