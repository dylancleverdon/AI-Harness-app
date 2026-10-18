"""Thermal and temperature readings.

macOS doesn't let apps read chip temperatures without admin rights, so this uses what is available:
  - the system's own thermal state (nominal/fair/serious/critical) via NSProcessInfo,
  - `pmset -g therm` for the CPU speed limit when the Mac is throttling,
  - optionally a free tool that reads the sensors: `macmon` (Apple Silicon) or `osx-cpu-temp` (Intel).
On Linux, psutil's own sensors are used. Everything degrades to "unknown" rather than failing.
"""
import json
import re
import shutil
import subprocess
import sys
import threading
import time

import psutil

THERMAL_NAMES = {0: "nominal", 1: "fair", 2: "serious", 3: "critical"}
THERMAL_ORDER = ["nominal", "fair", "serious", "critical"]
EXTRA_BIN_DIRS = ("/opt/homebrew/bin", "/usr/local/bin")


def find_tool(name):
    return shutil.which(name) or next((f"{d}/{name}" for d in EXTRA_BIN_DIRS
                                       if shutil.which(f"{d}/{name}")), None)


def parse_thermal_state(text):
    """`osascript` prints the NSProcessInfo.thermalState number."""
    try:
        return THERMAL_NAMES.get(int(text.strip()), "unknown")
    except (ValueError, AttributeError):
        return "unknown"


def parse_pmset(text):
    """CPU speed limit in percent from `pmset -g therm` (only present while throttling), else None."""
    m = re.search(r"CPU_Speed_Limit\s*=\s*(\d+)", text or "")
    return int(m.group(1)) if m else None


def parse_macmon(text):
    """Pull temperatures, GPU load and power from one line of `macmon pipe` JSON. Tolerant of missing fields."""
    try:
        j = json.loads((text or "").strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {}
    out = {}
    temp = j.get("temp") or {}
    if isinstance(temp.get("cpu_temp_avg"), (int, float)):
        out["temp_c"] = round(temp["cpu_temp_avg"], 1)
    if isinstance(temp.get("gpu_temp_avg"), (int, float)):
        out["gpu_temp_c"] = round(temp["gpu_temp_avg"], 1)
    gpu = j.get("gpu_usage")
    if isinstance(gpu, (list, tuple)) and len(gpu) == 2 and isinstance(gpu[1], (int, float)):
        out["gpu_pct"] = round(gpu[1] * 100)
    for key, field in (("all_power", "power_w"), ("sys_power", "sys_power_w")):
        if isinstance(j.get(key), (int, float)):
            out[field] = round(j[key], 1)
    return out


def parse_osx_cpu_temp(text):
    m = re.search(r"(\d+(?:\.\d+)?)\s*°?C", text or "")
    return {"temp_c": round(float(m.group(1)), 1)} if m and float(m.group(1)) > 0 else {}


def _run(cmd, timeout=4):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def read_once(state=None):
    """One reading of everything available. `state` caches which tools exist."""
    state = state if state is not None else {}
    out = {"thermal": "unknown", "speed_limit": None, "temp_source": None}
    if sys.platform == "darwin":
        out["thermal"] = parse_thermal_state(_run(
            ["osascript", "-l", "JavaScript", "-e",
             'ObjC.import("Foundation"); $.NSProcessInfo.processInfo.thermalState']))
        out["speed_limit"] = parse_pmset(_run(["pmset", "-g", "therm"]))
        if "macmon" not in state:
            state["macmon"] = find_tool("macmon")
            state["osx"] = find_tool("osx-cpu-temp")
        got = {}
        if state["macmon"]:
            got = parse_macmon(_run([state["macmon"], "pipe", "-s", "1"], timeout=8))
            out["temp_source"] = "macmon"
        if not got.get("temp_c") and state["osx"]:
            got = {**got, **parse_osx_cpu_temp(_run([state["osx"]]))}
            out["temp_source"] = out["temp_source"] or "osx-cpu-temp"
        out.update(got)
    else:
        try:
            temps = psutil.sensors_temperatures()
            vals = [t.current for group in temps.values() for t in group if t.current]
            if vals:
                out["temp_c"], out["temp_source"] = round(max(vals), 1), "psutil"
        except (AttributeError, OSError):
            pass
    return out


class Sensors(threading.Thread):
    """Reads the slower sensors every few seconds in the background so they never delay the 1s sampler."""

    def __init__(self, interval=5.0):
        super().__init__(daemon=True)
        self.interval = interval
        self.latest = {"thermal": "unknown", "speed_limit": None, "temp_source": None}
        self._state = {}

    def run(self):
        while True:
            try:
                self.latest = read_once(self._state)
            except Exception as e:  # never let a sensor error stop monitoring
                print("sensor error:", e, file=sys.stderr)
            time.sleep(self.interval)

    def tools(self):
        """Which optional temperature tools were found (for the UI hint)."""
        return {"macmon": bool(self._state.get("macmon")), "osx_cpu_temp": bool(self._state.get("osx")),
                "darwin": sys.platform == "darwin"}
