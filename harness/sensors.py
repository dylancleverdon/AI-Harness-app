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
    # GPU load: current macmon reports *_ratio fields (0-1); older versions had gpu_usage: [freq_mhz, ratio]
    ratio = next((j[k] for k in ("gpu_active_ratio", "gpu_scaled_ratio") if isinstance(j.get(k), (int, float))), None)
    legacy = j.get("gpu_usage")
    if ratio is None and isinstance(legacy, (list, tuple)) and len(legacy) == 2 and isinstance(legacy[1], (int, float)):
        ratio = legacy[1]
    if ratio is not None:
        out["gpu_pct"] = round(ratio * 100)
    if isinstance(j.get("gpu_freq_mhz"), (int, float)) and j["gpu_freq_mhz"] > 0:
        out["gpu_mhz"] = round(j["gpu_freq_mhz"])
    fans = [f for f in (j.get("fans") or []) if isinstance(f, dict) and isinstance(f.get("rpm"), (int, float))]
    if fans:
        out["fans"] = [{"name": str(f.get("name", "fan")), "rpm": round(f["rpm"]),
                        "max_rpm": round(f["max_rpm"]) if isinstance(f.get("max_rpm"), (int, float)) else None}
                       for f in fans]
    for key, field in (("all_power", "power_w"), ("sys_power", "sys_power_w")):
        if isinstance(j.get(key), (int, float)):
            out[field] = round(j[key], 1)
    return out


def parse_osx_cpu_temp(text):
    m = re.search(r"(\d+(?:\.\d+)?)\s*°?C", text or "")
    return {"temp_c": round(float(m.group(1)), 1)} if m and float(m.group(1)) > 0 else {}


# ---- heat: what the laptop gives off -----------------------------------------
# Practically all the electrical power a computer uses ends up as heat in the room
# (the little that leaves as light and sound turns to heat when it lands), so its
# heat output is the power it uses: 1 W = 3.412 BTU/h. Power going INTO the
# battery while charging is stored, not heat, so it's the power the system uses
# that counts, not what the charger delivers. The charger brick heats the room
# too: its losses are added (on the charger only), estimated at 10% of what it
# delivers, typical for a modern USB-C charger.

BTU_PER_WH = 3.412
BRICK_LOSS = 0.10 / 0.90          # losses per watt delivered, for a 90%-efficient charger


def _s64(v):
    """ioreg prints negative numbers (a discharging current) as unsigned 64-bit."""
    return v - 2 ** 64 if v >= 2 ** 63 else v


def parse_ioreg_power(text):
    """Power from `ioreg -rn AppleSmartBattery`: {laptop_w, delivered_w, on_ac, source}
    (whatever it could find; empty if nothing)."""
    text = text or ""
    out = {}
    on_ac = re.search(r'"ExternalConnected"\s*=\s*Yes', text) is not None
    out["on_ac"] = on_ac
    tele = {}
    m = re.search(r'"PowerTelemetryData"\s*=\s*\{([^}]*)\}', text)
    if m:
        tele = {k: _s64(int(v)) for k, v in re.findall(r'"(\w+)"\s*=\s*(-?\d+)', m.group(1))}

    def num(key):
        mm = re.search(rf'"{key}"\s*=\s*(-?\d+)\b', text)
        return _s64(int(mm.group(1))) if mm else None
    if tele.get("SystemLoad", 0) > 0:            # Apple Silicon: what the whole system uses, in mW
        out["laptop_w"] = tele["SystemLoad"] / 1000
        out["source"] = "battery controller (system load)"
    else:
        volt = num("Voltage")                     # mV
        amp = num("InstantAmperage")
        amp = num("Amperage") if amp is None else amp   # mA, negative while discharging
        if volt and amp is not None and amp < 0 and not on_ac:
            out["laptop_w"] = volt * -amp / 1e6
            out["source"] = "battery voltage × current"
    if on_ac and tele.get("SystemPowerIn", 0) > 0:
        out["delivered_w"] = tele["SystemPowerIn"] / 1000
    return out


def read_rapl(state):
    """Linux: the CPU package's power from its energy counter (CPU only). None
    until two readings exist."""
    try:
        with open("/sys/class/powercap/intel-rapl:0/energy_uj") as f:
            e = int(f.read())
    except (OSError, ValueError):
        return None
    now = time.time()
    last = state.get("rapl")
    state["rapl"] = (e, now)
    if not last or e < last[0] or now - last[1] <= 0:
        return None
    return (e - last[0]) / 1e6 / (now - last[1])


def heat_reading(ioreg_text, macmon, state):
    """{heat_w, laptop_w, brick_w, heat_btu_h, power_source, on_ac} from what's
    available, best first; {} if there's nothing to go on."""
    p = parse_ioreg_power(ioreg_text) if ioreg_text else {}
    laptop, source = p.get("laptop_w"), p.get("source")
    if laptop is None and isinstance(macmon.get("sys_power_w"), (int, float)) and macmon["sys_power_w"] > 0:
        laptop, source = macmon["sys_power_w"], "macmon (system power)"
    if laptop is None and sys.platform.startswith("linux"):
        w = read_rapl(state)
        if w is not None:
            laptop, source = w, "CPU package only (RAPL), the rest isn't measured"
    if laptop is None:
        return {}
    brick = None
    if p.get("on_ac"):
        brick = (p.get("delivered_w") or laptop) * BRICK_LOSS
    heat = laptop + (brick or 0)
    return {"heat_w": round(heat, 1), "laptop_w": round(laptop, 1),
            "brick_w": round(brick, 1) if brick is not None else None,
            "heat_btu_h": round(heat * BTU_PER_WH), "power_source": source, "on_ac": p.get("on_ac")}


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
        # look for the helper tools at startup and, until one is found, every 20s, so installing one while
        # the app is open is picked up without a restart
        if "macmon" not in state or (not (state["macmon"] or state["osx"]) and time.time() - state["looked"] > 20):
            state["macmon"] = find_tool("macmon")
            state["osx"] = find_tool("osx-cpu-temp")
            state["looked"] = time.time()
        got = {}
        if state["macmon"]:
            got = parse_macmon(_run([state["macmon"], "pipe", "-s", "1"], timeout=8))
            out["temp_source"] = "macmon"
        if not got.get("temp_c") and state["osx"]:
            got = {**got, **parse_osx_cpu_temp(_run([state["osx"]]))}
            out["temp_source"] = out["temp_source"] or "osx-cpu-temp"
        out.update(got)
        out.update(heat_reading(_run(["ioreg", "-rn", "AppleSmartBattery"]), got, state))
    else:
        try:
            temps = psutil.sensors_temperatures()
            vals = [t.current for group in temps.values() for t in group if t.current]
            if vals:
                out["temp_c"], out["temp_source"] = round(max(vals), 1), "psutil"
        except (AttributeError, OSError):
            pass
        out.update(heat_reading("", {}, state))
    return out


class Sensors(threading.Thread):
    """Reads the slower sensors every few seconds in the background so they never delay the 1s sampler."""

    def __init__(self, interval=5.0):
        super().__init__(daemon=True)
        self.interval = interval
        self.latest = {"thermal": "unknown", "speed_limit": None, "temp_source": None}
        self._state = {}

    def run(self):
        energy_wh, last = 0.0, None
        while True:
            try:
                r = read_once(self._state)
                now = time.time()
                if r.get("heat_w") is not None:     # heat given off since the app started
                    if last is not None:
                        energy_wh += r["heat_w"] * min(now - last, 60) / 3600
                    last = now
                r["heat_wh_session"] = round(energy_wh, 2)
                self.latest = r
            except Exception as e:  # never let a sensor error stop monitoring
                print("sensor error:", e, file=sys.stderr)
            time.sleep(self.interval)

    def tools(self):
        """Which optional temperature tools were found (for the UI hint)."""
        return {"macmon": bool(self._state.get("macmon")), "osx_cpu_temp": bool(self._state.get("osx")),
                "darwin": sys.platform == "darwin"}
