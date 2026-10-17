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
    "keep_awake": True,  # macOS: stop the Mac sleeping while a script runs (caffeinate)
    "python": "",  # interpreter for scripts; empty = harness venv
    "auto_update": True,
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


def ensure_dirs():
    """Create the data dirs and seed example scripts on first run."""
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    examples = ROOT / "scripts" / "examples"
    if examples.is_dir() and not any(SCRIPTS_DIR.glob("*.py")):
        for f in examples.glob("*.py"):
            (SCRIPTS_DIR / f.name).write_text(f.read_text())
