"""Memory sampling, level classification (green/yellow/orange/red) and per-process tracking."""
import subprocess
import sys
import threading
import time
from collections import deque

import psutil

from .config import settings

LEVELS = ["green", "yellow", "orange", "red"]
GB = 1024**3


def _mac_pressure():
    """macOS kernel memory pressure: 1 normal, 2 warn, 4 critical. None elsewhere."""
    if sys.platform != "darwin":
        return None
    try:
        out = subprocess.run(
            ["sysctl", "-n", "kern.memorystatus_vm_pressure_level"],
            capture_output=True, text=True, timeout=2,
        ).stdout.strip()
        return int(out)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def classify(avail_pct, pressure, cfg):
    idx = 0
    if avail_pct < cfg["yellow_below_pct"]:
        idx = 1
    if avail_pct < cfg["orange_below_pct"]:
        idx = 2
    if avail_pct < cfg["red_below_pct"]:
        idx = 3
    if pressure == 2:
        idx = max(idx, 1)
    elif pressure == 4:
        idx = 3
    return LEVELS[idx]


def tree_rss(pid):
    """Total RSS in bytes of a process and all its children."""
    try:
        p = psutil.Process(pid)
        procs = [p] + p.children(recursive=True)
    except psutil.Error:
        return 0
    total = 0
    for q in procs:
        try:
            total += q.memory_info().rss
        except psutil.Error:
            pass
    return total


def lmstudio_rss():
    total = 0
    for p in psutil.process_iter(["name", "memory_info"]):
        try:
            name = (p.info["name"] or "").lower()
            if "lm studio" in name or "lm-studio" in name or name in ("lms", "llmster"):
                total += p.info["memory_info"].rss
        except psutil.Error:
            pass
    return total


class Monitor(threading.Thread):
    """Samples memory once a second, keeps history, and calls on_tick(snapshot)."""

    def __init__(self, on_tick=None, interval=1.0):
        super().__init__(daemon=True)
        self.interval = interval
        self.on_tick = on_tick
        self.history = deque(maxlen=600)  # 10 minutes
        self.latest = None
        self._n = 0
        self._lms = 0

    def sample(self):
        cfg = settings.get()
        vm = psutil.virtual_memory()
        sw = psutil.swap_memory()
        avail_pct = vm.available / vm.total * 100
        if self._n % 3 == 0:
            self._lms = lmstudio_rss()
        self._n += 1
        pressure = _mac_pressure()
        return {
            "t": time.time(),
            "total_gb": round(vm.total / GB, 2),
            "used_gb": round((vm.total - vm.available) / GB, 2),
            "available_gb": round(vm.available / GB, 2),
            "available_pct": round(avail_pct, 1),
            "swap_used_gb": round(sw.used / GB, 2),
            "swap_total_gb": round(sw.total / GB, 2),
            "pressure": pressure,
            "lmstudio_gb": round(self._lms / GB, 2),
            "level": classify(avail_pct, pressure, cfg),
        }

    def run(self):
        while True:
            try:
                snap = self.sample()
                self.latest = snap
                self.history.append(snap)
                if self.on_tick:
                    self.on_tick(snap)
            except Exception as e:  # keep the monitor alive no matter what
                print("memory monitor error:", e, file=sys.stderr)
            time.sleep(self.interval)
