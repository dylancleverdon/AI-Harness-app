import os
import sys
import tempfile
import time

os.environ["AIHARNESS_HOME"] = tempfile.mkdtemp()

from fastapi.testclient import TestClient  # noqa: E402

from harness import diagnose, memory  # noqa: E402
from harness.config import SCRIPTS_DIR, ensure_dirs, settings  # noqa: E402


def test_classify():
    cfg = settings.get()
    assert memory.classify(50, 1, cfg) == "green"
    assert memory.classify(25, 1, cfg) == "yellow"
    assert memory.classify(12, 1, cfg) == "orange"
    assert memory.classify(5, 1, cfg) == "red"
    assert memory.classify(80, 4, cfg) == "red"


def test_diagnose_traceback_and_hints():
    out = 'Traceback (most recent call last):\n  File "/x/a.py", line 3, in <module>\n    import cv2\nModuleNotFoundError: No module named \'cv2\''
    tb = diagnose.extract_traceback(out)
    assert tb["line"] == 3 and "cv2" in tb["exception"]
    hints = diagnose.diagnose({"status": "failed", "exit_code": 1, "output": out})
    assert hints[0]["action"]["pip"] == "opencv-python"


def test_run_lifecycle_and_guard():
    ensure_dirs()
    from harness.server import app, runs
    c = TestClient(app, headers={"x-harness": "1"})
    (SCRIPTS_DIR / "t_ok.py").write_text("print('hi')")
    (SCRIPTS_DIR / "t_bad.py").write_text("raise RuntimeError('boom')")
    (SCRIPTS_DIR / "t_sleep.py").write_text("import time; print('x', flush=True); time.sleep(60)")

    rid = c.post("/api/runs", json={"script": "t_ok.py"}).json()["id"]
    for _ in range(50):
        d = c.get(f"/api/runs/{rid}").json()
        if d["status"] != "running":
            break
        time.sleep(0.1)
    assert d["status"] == "ok" and "hi" in d["output"]

    rid = c.post("/api/runs", json={"script": "t_bad.py"}).json()["id"]
    time.sleep(1.5)
    d = c.get(f"/api/runs/{rid}").json()
    assert d["status"] == "failed" and d["traceback"]["exception"].startswith("RuntimeError")
    assert "boom" in c.get(f"/api/runs/{rid}/report").text

    # simulate memory pressure: the guard should stop the sleeping script after 2 samples
    rid = c.post("/api/runs", json={"script": "t_sleep.py"}).json()["id"]
    snap = {"level": "red", "available_pct": 3, "available_gb": 0.5, "swap_used_gb": 9}
    runs.on_tick(snap)
    runs.on_tick(snap)
    for _ in range(60):
        d = c.get(f"/api/runs/{rid}").json()
        if d["status"] != "running":
            break
        time.sleep(0.1)
    assert d["status"] == "killed" and "memory guard" in d["kill_reason"]
    assert runs.events


def test_script_path_traversal_blocked():
    from harness.server import app
    c = TestClient(app, headers={"x-harness": "1"})
    assert c.put("/api/scripts/../evil.py", json={"content": ""}).status_code in (400, 404)
    assert c.put("/api/scripts/x.txt", json={"content": ""}).status_code == 400


def _fake_lm(monkeypatch, reply_fn):
    from harness import ai_edit

    class R:
        status_code = 200
        text = ""

        def __init__(self, content):
            self._c = content

        def json(self):
            return {"choices": [{"message": {"content": self._c}, "finish_reason": "stop"}]}

    monkeypatch.setattr(ai_edit.httpx, "post", lambda url, json=None, timeout=None: R(reply_fn(json["messages"])))
    monkeypatch.setattr(ai_edit, "context_length", lambda m: 8000)
    return ai_edit


def block(search, replace):
    return f"<<<<<<< SEARCH\n{search}\n=======\n{replace}\n>>>>>>> REPLACE\n"


def test_ai_edit_find_replace_is_safe(monkeypatch):
    src = "def a():\n    return 1\n\n\ndef b():\n    return 2\n"
    replies = iter([
        block("def a():\n    return 1", "def a():\n    return 10")            # good
        + block("return 999", "return 0")                                      # text not in file -> skipped
        + block("def b():\n    return 2", "def b(:\n    return 2")           # breaks syntax -> rejected
        + block("  return 2", "  return 20"),                                  # wrong indentation -> still found
    ])
    ai = _fake_lm(monkeypatch, lambda m: next(replies))
    ev = list(ai.edit_stream("x.py", src, "change", model="m"))[-1]
    assert ev["type"] == "done" and ev["stats"] == {"applied": 2, "not_found": 1, "broke": 1}
    assert ev["edited"] == "def a():\n    return 10\n\n\ndef b():\n    return 20\n"
    assert "NO CHANGES" not in ev["edited"]
    rv = ev["review"]
    assert "Review request" in rv and "change" in rv  # instruction included
    assert "APPLIED" in rv and "SKIPPED" in rv and "REJECTED" in rv and "def b(:" in rv
    assert "## Original file" in rv and "## Edited file" in rv and "return 20" in rv
    assert "SEARCH/REPLACE" in rv or "SEARCH" in rv  # system prompt included

    ai = _fake_lm(monkeypatch, lambda m: "NO CHANGES")
    ev = list(ai.edit_stream("x.py", src, "change", model="m"))[-1]
    assert ev["type"] == "done" and not ev["changed"] and "NO CHANGES" in ev["review"]  # model's reply is shown


def test_ai_edit_rewrite_mode_and_guards(monkeypatch):
    ai = _fake_lm(monkeypatch, lambda m: "```\nHELLO there\n```")
    ev = list(ai.edit_stream("n.md", "hello there\n", "shout", model="m", mode="rewrite"))[-1]
    assert ev["edited"] == "HELLO there\n"

    ev = list(ai.edit_stream("a.py", "x = 1\n", "i", model="m", mem_level=lambda: "red"))[-1]
    assert ev["type"] == "error" and "memory guard" in ev["message"]

    monkeypatch.setattr(ai.httpx, "post", lambda *a, **k: (_ for _ in ()).throw(ai.httpx.ConnectError("x")))
    assert list(ai.edit_stream("a.py", "x\n", "i", model="m"))[-1]["type"] == "error"


def test_ai_edit_endpoint_apply_backs_up():
    from harness.config import DATA_DIR
    from harness.server import app
    c = TestClient(app, headers={"x-harness": "1"})
    (SCRIPTS_DIR / "e.py").write_text("old = 1\n")
    r = c.post("/api/ai-edit/apply", json={"name": "e.py", "content": "new = 2\n"}).json()
    assert (SCRIPTS_DIR / "e.py").read_text() == "new = 2\n"
    assert r["backup"].startswith(str(DATA_DIR / "backups")) and open(r["backup"]).read() == "old = 1\n"


def test_params_discovery_and_files(tmp_path):
    from harness import params
    src = open("scripts/examples/cpp_generator_example.py").read()
    ps = params.parse_params(src)
    names = [p["dest"] for p in ps]
    assert names == ["task", "out_dir", "workers", "max_tokens", "style", "verbose"]
    assert ps[1]["path"] and ps[4]["choices"] == ["modern", "c-like"] and ps[5]["kind"] == "bool"
    argv = params.build_argv(ps, {"task": "sort ints", "workers": 4, "verbose": True, "max_tokens": 2048})
    assert argv == ["sort ints", "--workers", "4", "--verbose"]
    params.save("a.py", {"values": {"workers": 4}, "extra": "-x"})
    assert params.get_saved("a.py")["values"] == {"workers": 4}
    assert params.parse_env("A=1\n# c\nB = two") == {"A": "1", "B": "two"}

    from harness.server import app
    c = TestClient(app, headers={"x-harness": "1"})
    out = tmp_path / "gen"
    (SCRIPTS_DIR / "w.py").write_text(
        "import argparse, pathlib\nap=argparse.ArgumentParser()\nap.add_argument('--out-dir')\n"
        "a=ap.parse_args()\np=pathlib.Path(a.out_dir); p.mkdir(parents=True); (p/'main.cpp').write_text('int main(){}')\n")
    rid = c.post("/api/runs", json={"script": "w.py", "values": {"out_dir": str(out)}}).json()["id"]
    for _ in range(50):
        d = c.get(f"/api/runs/{rid}").json()
        if d["status"] != "running":
            break
        time.sleep(0.1)
    assert d["status"] == "ok" and [f["path"] for f in d["files"]] == [str(out / "main.cpp")]
    assert c.get("/api/run-file", params={"run": rid, "path": str(out / "main.cpp")}).text == "int main(){}"
    assert c.get("/api/run-file", params={"run": rid, "path": "/etc/passwd"}).status_code == 403
    assert c.get("/api/script-settings/w.py").json()["values"]["out_dir"] == str(out)


def test_progress_bar_stays_one_live_line():
    ensure_dirs()
    from harness.server import app
    c = TestClient(app, headers={"x-harness": "1"})
    (SCRIPTS_DIR / "bar.py").write_text(
        "import sys, time\n"
        "for i in range(1, 4):\n"
        "    sys.stderr.write(f'\\r\\x1b[K {i}/3 |###|'); sys.stderr.flush(); time.sleep(0.15)\n"
        "    if i == 2:\n"
        "        sys.stderr.write('\\r\\x1b[K'); print('FUN_1 -> done', flush=True)\n"
        "sys.stderr.write('\\n'); print('end')\n")
    rid = c.post("/api/runs", json={"script": "bar.py"}).json()["id"]
    for _ in range(60):
        d = c.get(f"/api/runs/{rid}").json()
        if d["status"] != "running":
            break
        time.sleep(0.1)
    texts = [l["x"] for l in d["lines"] if l["s"] != "sys"]
    assert d["status"] == "ok"
    assert "FUN_1 -> done" in texts and "end" in texts
    assert [t for t in texts if "/3" in t] == [" 3/3 |###|"]  # redraws collapsed, no escape codes
    assert not any("\x1b" in t or "\r" in t for t in texts)


def test_keep_awake_and_no_runtime_limit(monkeypatch):
    from harness import config, runner
    assert "max_runtime_sec" not in config.DEFAULTS and config.settings.get("keep_awake") is True
    started = []

    class FakeProc:
        def __init__(self, cmd):
            started.append(cmd)
            self.alive = True

        def poll(self):
            return None if self.alive else 0

        def terminate(self):
            self.alive = False

    monkeypatch.setattr(runner.sys, "platform", "darwin")
    monkeypatch.setattr(runner.shutil, "which", lambda n: "/usr/bin/" + n)
    monkeypatch.setattr(runner.subprocess, "Popen", lambda cmd, **k: FakeProc(cmd))
    m = runner.RunManager()
    m._sync_awake(True)
    m._sync_awake(True)  # idempotent: one caffeinate only
    assert len(started) == 1 and started[0][0] == "caffeinate" and "-w" in started[0] and m.awake()
    m._sync_awake(False)
    assert not m.awake()
    m._sync_awake(True)
    assert len(started) == 2


def test_stale_runtime_setting_ignored(tmp_path, monkeypatch):
    import json
    from harness import config
    f = tmp_path / "s.json"
    f.write_text(json.dumps({"max_runtime_sec": 5, "guard_trip_level": "red"}))
    monkeypatch.setattr(config, "SETTINGS_FILE", f)
    s = config.Settings()
    assert s.get("guard_trip_level") == "red" and "max_runtime_sec" not in s.get()


def test_pip_uses_script_python_and_maps_clang(monkeypatch):
    from harness import config, diagnose, server
    out = "ModuleNotFoundError: No module named 'clang'"
    h = diagnose.diagnose({"status": "failed", "exit_code": 1, "output": out})
    assert h[0]["action"]["pip"] == "libclang"  # not the unrelated 'clang' package
    h = diagnose.diagnose({"status": "failed", "exit_code": 1, "output": "error: externally-managed-environment"})
    assert "pip is blocked" in h[0]["title"]

    calls = []

    class P:
        returncode, stdout, stderr = 0, "ok", ""

    monkeypatch.setattr(server.subprocess, "run", lambda cmd, **k: calls.append(cmd) or P())
    c = TestClient(server.app, headers={"x-harness": "1"})
    r = c.post("/api/pip", json={"package": "libclang requests>=2"}).json()
    assert r["ok"] and calls[-1][1:] == ["-m", "pip", "install", "libclang", "requests>=2"]
    assert calls[-1][0] == config.script_python()
    config.settings.update({"python": "/opt/custom/bin/python3"})  # pip must follow the interpreter scripts use
    c.post("/api/pip", json={"package": "libclang"})
    assert calls[-1][0] == "/opt/custom/bin/python3"
    config.settings.update({"python": ""})
    for bad in ("--break-system-packages", "x; rm -rf /", "", "a $(b)"):
        assert c.post("/api/pip", json={"package": bad}).status_code == 400


def test_params_path_default_append_and_help_path(tmp_path, monkeypatch):
    from harness import params, runner
    src = (
        "import argparse\nfrom pathlib import Path\nap = argparse.ArgumentParser()\n"
        "ap.add_argument('--input', required=True, type=Path)\n"
        "ap.add_argument('--workdir', default=Path('./build'), type=Path)\n"
        "ap.add_argument('--libclang', default=None, help='path to libclang dylib/so')\n"
        "ap.add_argument('--flag', action='append', default=[], dest='extra_flags')\n"
        "ap.add_argument('--resume', action='store_true')\n")
    ps = {p["dest"]: p for p in params.parse_params(src)}
    assert ps["workdir"]["default"] == "./build" and ps["workdir"]["path"]
    assert ps["libclang"]["path"] and ps["input"]["path"] and ps["input"]["required"]
    assert ps["extra_flags"]["kind"] == "append"
    argv = params.build_argv(list(ps.values()), {"input": "/a/b.cpp", "extra_flags": "-I/x\n\n-DFOO=1\n", "resume": True})
    assert argv == ["--input", "/a/b.cpp", "--flag", "-I/x", "--flag", "-DFOO=1", "--resume"]  # workdir left at default

    monkeypatch.setattr(runner.os.path, "isdir", lambda d: d == "/opt/homebrew/bin")
    assert runner.gui_safe_path("/usr/bin:/bin").split(":")[:2] == ["/opt/homebrew/bin", "/usr/bin"]
    assert runner.gui_safe_path("/opt/homebrew/bin:/usr/bin") == "/opt/homebrew/bin:/usr/bin"  # no duplicates


def _wait_done(c, rid, n=80):
    for _ in range(n):
        d = c.get(f"/api/runs/{rid}").json()
        if d["status"] != "running":
            return d
        time.sleep(0.1)
    return d


def test_console_input_terminal_and_guards(tmp_path):
    ensure_dirs()
    from harness.server import app, runs
    c = TestClient(app, headers={"x-harness": "1"})
    (SCRIPTS_DIR / "ask.py").write_text("name = input('Your name? ')\nprint('hello', name)\nprint('rest:', input())\n")
    rid = c.post("/api/runs", json={"script": "ask.py"}).json()["id"]
    time.sleep(0.8)
    assert c.post(f"/api/runs/{rid}/input", json={"text": "Ada"}).status_code == 200
    assert c.post(f"/api/runs/{rid}/input", json={"text": "bye"}).status_code == 200
    d = _wait_done(c, rid)
    out = d["output"]
    assert d["status"] == "ok" and "hello Ada" in out and "rest: bye" in out and "Your name?" in out
    assert any(l["s"] == "in" and l["x"] == "Ada" for l in d["lines"])  # typed text is echoed
    assert c.post(f"/api/runs/{rid}/input", json={"text": "late"}).status_code == 409  # finished

    (SCRIPTS_DIR / "eof.py").write_text("import sys\nprint(len(sys.stdin.read()))\n")
    rid = c.post("/api/runs", json={"script": "eof.py"}).json()["id"]
    time.sleep(0.5)
    c.post(f"/api/runs/{rid}/input", json={"text": "abc"})
    c.post(f"/api/runs/{rid}/input", json={"eof": True})
    assert _wait_done(c, rid)["output"].strip().endswith("4")  # 'abc\n' then EOF

    # shell prompt: cd persists, commands run there, python/pip are the scripts' interpreter
    sub = tmp_path / "work dir"
    sub.mkdir()
    (sub / "marker.txt").write_text("x")
    assert c.post("/api/terminal", json={"command": f'cd "{sub}"'}).json()["cwd"] == str(sub.resolve())
    r = c.post("/api/terminal", json={"command": "ls && python -c 'import sys; print(sys.executable)'"}).json()
    d = _wait_done(c, r["run"]["id"])
    assert d["status"] == "ok" and "marker.txt" in d["output"] and d["script"].startswith("$ ls")
    assert c.post("/api/terminal", json={"command": "cd /definitely/not/here"}).json()["cd"] is False
    assert c.post("/api/terminal", json={"command": "exit 3"}).status_code == 200
    runs.term_cwd = SCRIPTS_DIR

    # security: writes need the header, and only local Host names are served
    bare = TestClient(app)
    assert bare.post("/api/terminal", json={"command": "ls"}).status_code == 403
    assert bare.get("/api/ping").status_code == 200
    assert TestClient(app, headers={"x-harness": "1", "host": "evil.example.com"}).get("/api/ping").status_code == 403


def test_origin_alternative_and_static_not_cached():
    from harness.server import app
    bare = TestClient(app)
    ok = bare.post("/api/terminal", json={"command": "cd ."}, headers={"origin": "http://127.0.0.1:8765"})
    assert ok.status_code == 200  # older cached page: no header, but same-site Origin
    for evil in ("https://evil.example.com", "null"):
        r = bare.post("/api/terminal", json={"command": "cd ."}, headers={"origin": evil})
        assert r.status_code == 403 and "Reload the page" in r.text
    assert bare.post("/api/terminal", json={"command": "cd ."}).status_code == 403  # no header, no origin
    assert bare.get("/static/app.js").headers["cache-control"] == "no-cache"


def test_scripts_get_a_terminal_so_live_progress_works():
    from harness import config
    from harness.server import app, runs
    c = TestClient(app, headers={"x-harness": "1"})
    (SCRIPTS_DIR / "tty.py").write_text(
        "import sys, threading, time, shutil\n"
        "print('isatty', sys.stdout.isatty(), sys.stdin.isatty(), sys.stderr.isatty(), shutil.get_terminal_size().columns, flush=True)\n"
        "live = sys.stdout.isatty()\n"
        "stop = threading.Event()\n"
        "def spin():\n"
        "    i = 0\n"
        "    while not stop.wait(0.1):\n"
        "        i += 1; sys.stdout.write(f'\\r\\x1b[K spinner {i} | now: work'); sys.stdout.flush()\n"
        "if live: threading.Thread(target=spin, daemon=True).start()\n"
        "time.sleep(1.0)\n"
        "stop.set(); print('\\r\\x1b[Kdone', flush=True)\n")
    rid = c.post("/api/runs", json={"script": "tty.py"}).json()["id"]
    seen = ""
    for _ in range(30):  # while it runs, the pinned live line must be moving (a quiet script shows nothing)
        run = runs.runs[rid]
        seen = run.live.get("out") or seen
        if "spinner" in seen:
            break
        time.sleep(0.05)
    assert "spinner" in seen
    d = _wait_done(c, rid)
    assert d["status"] == "ok"
    first = [l["x"] for l in d["lines"] if l["s"] != "sys"][0]
    assert first == "isatty True True True 400"
    texts = [l["x"] for l in d["lines"] if l["s"] != "sys"]
    assert texts[-1] == "done" and not any("spinner" in t for t in texts)  # redraws never pile up as lines

    # switching it off restores plain pipes: the script then sees no terminal (and stays quiet)
    config.settings.update({"use_pty": False})
    try:
        rid = c.post("/api/runs", json={"script": "tty.py"}).json()["id"]
        d = _wait_done(c, rid)
        assert [l["x"] for l in d["lines"] if l["s"] != "sys"][0].startswith("isatty False False False")
    finally:
        config.settings.update({"use_pty": True})


def test_sensor_parsers():
    from harness import sensors as s
    assert [s.parse_thermal_state(x) for x in ("0\n", "1", "2", "3", "", "weird")] == [
        "nominal", "fair", "serious", "critical", "unknown", "unknown"]
    assert s.parse_pmset("CPU_Scheduler_Limit = 100\nCPU_Available_CPUs = 8\nCPU_Speed_Limit = 75\n") == 75
    assert s.parse_pmset("Note: No thermal warning level has been recorded\n") is None
    modern = ('{"timestamp":"2026-10-18T10:00:00Z","temp":{"cpu_temp_avg":51.26,"gpu_temp_avg":44.0},'
              '"fans":[{"name":"Fan 1","rpm":2310,"max_rpm":6000}],"cpu_active_ratio":0.4,'
              '"gpu_freq_mhz":444.0,"gpu_scaled_ratio":0.2,"gpu_active_ratio":0.37,"all_power":12.34,"sys_power":20.1}\n')
    assert s.parse_macmon(modern) == {
        "temp_c": 51.3, "gpu_temp_c": 44.0, "gpu_pct": 37, "gpu_mhz": 444, "power_w": 12.3, "sys_power_w": 20.1,
        "fans": [{"name": "Fan 1", "rpm": 2310, "max_rpm": 6000}]}
    legacy = '{"temp":{"cpu_temp_avg":51.26,"gpu_temp_avg":44.0},"gpu_usage":[444,0.37],"all_power":12.34}\n'
    assert s.parse_macmon(legacy)["gpu_pct"] == 37 and s.parse_macmon(legacy)["temp_c"] == 51.3
    # sensors with no valid reading are null (and a VM reports zeros / no fans): never invent values
    vm = '{"temp":{"cpu_temp_avg":null,"gpu_temp_avg":null},"fans":[],"gpu_freq_mhz":0,"gpu_active_ratio":0.0}'
    assert s.parse_macmon(vm) == {"gpu_pct": 0}
    assert s.parse_macmon("not json") == {} and s.parse_macmon('{"temp":{}}') == {}
    assert s.parse_osx_cpu_temp("61.2°C") == {"temp_c": 61.2} and s.parse_osx_cpu_temp("0.0°C") == {}
    r = s.read_once({})  # never raises, whatever the platform
    assert r["thermal"] in ("unknown", "nominal", "fair", "serious", "critical")


def test_snapshot_has_cpu_and_runs_report_cpu():
    from harness import memory
    from harness.server import app, runs
    snap = memory.Monitor().sample()
    assert 0 <= snap["cpu_pct"] <= 100 and snap["cores"] and snap["cpu_count"] >= 1 and "thermal" in snap
    c = TestClient(app, headers={"x-harness": "1"})
    (SCRIPTS_DIR / "burn.py").write_text("import time\nt=time.time()\nwhile time.time()-t<3: pass\n")
    rid = c.post("/api/runs", json={"script": "burn.py"}).json()["id"]
    for _ in range(4):  # on_tick is normally driven by the monitor thread; drive it here
        time.sleep(0.6)
        runs.on_tick({**snap, "level": "green"})
    d = _wait_done(c, rid, 100)
    assert d["peak_cpu_pct"] >= 50 and d["mem"][-1]["cpu_pct"] >= 0
    assert "peak CPU" in c.get(f"/api/runs/{rid}/report").text


def test_thermal_guard_stops_runs_only_when_enabled():
    from harness import config
    from harness.server import app, runs
    c = TestClient(app, headers={"x-harness": "1"})
    (SCRIPTS_DIR / "t_sleep.py").write_text("import time; time.sleep(60)")
    hot = {"level": "green", "available_pct": 80, "available_gb": 10, "swap_used_gb": 0,
           "thermal": "serious", "temp_c": 96.0, "speed_limit": 70}

    rid = c.post("/api/runs", json={"script": "t_sleep.py"}).json()["id"]
    for _ in range(8):
        runs.on_tick(hot)  # guard is off by default: just monitoring
    assert c.get(f"/api/runs/{rid}").json()["status"] == "running"

    config.settings.update({"thermal_guard": "critical"})
    for _ in range(8):
        runs.on_tick(hot)  # serious < critical: still fine
    assert c.get(f"/api/runs/{rid}").json()["status"] == "running"

    config.settings.update({"thermal_guard": "serious"})
    try:
        for _ in range(5):
            runs.on_tick(hot)
        d = _wait_done(c, rid)
        assert d["status"] == "killed" and d["kill_reason"].startswith("thermal guard")
        assert "96.0 C" in d["kill_reason"] and any("Thermal state SERIOUS" in e["msg"] for e in runs.events)
        assert any("thermal guard" in h["title"].lower() for h in d["hints"])
    finally:
        config.settings.update({"thermal_guard": "off"})


def test_helper_tool_installed_while_running_is_noticed(monkeypatch):
    from harness import sensors as s
    monkeypatch.setattr(s.sys, "platform", "darwin")
    monkeypatch.setattr(s, "_run", lambda cmd, timeout=4: (
        '{"temp":{"cpu_temp_avg":61.0}}' if cmd[:2] == ["/opt/homebrew/bin/macmon", "pipe"] else ""))
    installed = {"macmon": None}
    monkeypatch.setattr(s, "find_tool", lambda n: installed.get(n))
    state = {}
    assert s.read_once(state).get("temp_c") is None  # not installed yet
    installed["macmon"] = "/opt/homebrew/bin/macmon"  # the user runs `brew install macmon`
    assert s.read_once(state).get("temp_c") is None  # within 20s: still not rechecked
    state["looked"] -= 21
    out = s.read_once(state)
    assert out["temp_c"] == 61.0 and out["temp_source"] == "macmon"


def test_display_sleep_button(monkeypatch):
    from harness import server
    c = TestClient(server.app, headers={"x-harness": "1"})
    assert c.post("/api/display-sleep").status_code == 501  # this test machine isn't a Mac
    calls = []

    class R:
        returncode, stdout, stderr = 0, "", ""

    monkeypatch.setattr(server.sys, "platform", "darwin")
    monkeypatch.setattr(server.subprocess, "run", lambda cmd, **k: calls.append(cmd) or R())
    assert c.post("/api/display-sleep").json() == {"ok": True} and calls == [["pmset", "displaysleepnow"]]
    R.returncode, R.stderr = 1, "denied"
    r = c.post("/api/display-sleep")
    assert r.status_code == 500 and "denied" in r.text
    assert TestClient(server.app).post("/api/display-sleep").status_code == 403  # needs the app's header


def test_downloaded_models_from_lms(monkeypatch, tmp_path):
    from harness import lmstudio
    js = ('[{"type":"llm","modelKey":"qwen/qwen3-4b-2507","displayName":"Qwen3 4B 2507","paramsString":"4B",'
          '"architecture":"qwen3","format":"gguf","quantization":{"name":"Q4_K_M","bits":4},"sizeBytes":2500000000,'
          '"maxContextLength":262144},{"type":"embedding","modelKey":"nomic-embed","sizeBytes":84000000},'
          '{"type":"llm","modelKey":"google/gemma-3-12b"}]')
    got = lmstudio.parse_lms_ls(js)
    assert [m["id"] for m in got] == ["qwen/qwen3-4b-2507", "nomic-embed", "google/gemma-3-12b"]
    assert got[0]["quant"] == "Q4_K_M" and got[0]["size_gb"] == 2.5 and got[0]["ctx"] == 262144
    assert lmstudio.parse_lms_ls('{"models":[{"modelKey":"a/b"}]}')[0]["id"] == "a/b"
    table = ("You have 2 models, taking up 7 GB of disk space.\n\nLLM                 PARAMS   ARCH     SIZE\n"
             "qwen/qwen3-4b-2507  4B       qwen3    2.50 GB\ngoogle/gemma-3-12b  12B      gemma3   7.30 GB\n\n"
             "EMBEDDING           PARAMS   ARCH     SIZE\nnomic-embed         137M     nomic    0.08 GB\n")
    t = lmstudio.parse_lms_ls(table)
    assert [(m["id"], m["type"]) for m in t] == [("qwen/qwen3-4b-2507", "llm"), ("google/gemma-3-12b", "llm"),
                                                  ("nomic-embed", "embeddings")]

    fake = tmp_path / "lms"
    fake.write_text(f"#!/bin/sh\n[ \"$1 $2\" = \"ls --json\" ] && cat <<'EOF'\n{js}\nEOF\n")
    fake.chmod(0o755)
    monkeypatch.setattr(lmstudio, "find_lms", lambda: str(fake))
    monkeypatch.setattr(lmstudio, "status", lambda: {"ok": True, "error": None, "models": [
        {"id": "google/gemma-3-12b", "loaded": True, "type": "llm", "arch": "", "quant": "", "ctx": 4096}]})
    r = lmstudio.downloaded_models()
    assert r["source"] == "lms" and not r["error"]
    assert [m["id"] for m in r["models"]] == ["google/gemma-3-12b", "qwen/qwen3-4b-2507", "nomic-embed"]  # loaded first, llms before embeddings
    assert r["models"][0]["loaded"] and not r["models"][1]["loaded"]

    # no lms: fall back to what the running server reports; nothing at all: a helpful message
    monkeypatch.setattr(lmstudio, "find_lms", lambda: None)
    assert lmstudio.downloaded_models()["source"] == "server"
    monkeypatch.setattr(lmstudio, "status", lambda: {"ok": False, "error": "down", "models": []})
    r = lmstudio.downloaded_models()
    assert r["models"] == [] and "lms" in r["error"]
    c = TestClient(__import__("harness.server", fromlist=["app"]).app)
    assert c.get("/api/models/downloaded").json()["models"] == []


def test_model_param_detection_for_dropdowns():
    from harness import params
    src = ("import argparse\nap = argparse.ArgumentParser()\nap.add_argument('models', nargs='*')\n"
           "ap.add_argument('--ctx', type=int)\nap.add_argument('--lmstudio-model', default='local-model')\n"
           "ap.add_argument('--model', default='qwen3:8b')\nap.add_argument('--model-temperature', type=float, default=0.1)\n")
    ps = {p["dest"]: p for p in params.parse_params(src)}
    assert ps["models"]["nargs"] == "*" and ps["models"]["positional"]
    assert params.build_argv(list(ps.values()), {"models": 'qwen/qwen3-4b-2507 "my model"', "ctx": 32768}) == [
        "qwen/qwen3-4b-2507", "my model", "--ctx", "32768"]


def test_reports_are_sent_to_their_own_branch(tmp_path, monkeypatch):
    import subprocess
    from harness import reports
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
    monkeypatch.setattr(reports, "_remote", lambda: (str(origin), "someone/repo"))
    monkeypatch.setattr(reports, "CLONE", tmp_path / "clone")
    work = tmp_path / "fastpass 3" / "diagnostics"
    work.mkdir(parents=True)
    rep = work / "report-20261021-010203.md"
    rep.write_text("# Diagnostics\nsomething broke\n")
    assert reports.find_report(f"x\nDIAGNOSTICS: {rep}\ny") == rep
    assert reports.find_report("DIAGNOSTICS: /no/such/file.md") is None
    r = reports.send(rep)
    assert r["ok"], r
    assert r["url"].endswith("/blob/decomp-reports/reports/fastpass-3/report-20261021-010203.md")
    rep2 = work / "report-20261021-020000.md"
    rep2.write_text("# Diagnostics\nsecond\n")
    assert reports.send(rep2)["ok"]
    show = lambda p: subprocess.run(["git", "--git-dir", str(origin), "show", f"decomp-reports:{p}"],
                                    capture_output=True, text=True).stdout
    assert "second" in show("reports/LATEST.md")
    assert "something broke" in show("reports/fastpass-3/report-20261021-010203.md")
    assert show("reports/LATEST.txt").strip() == "reports/fastpass-3/report-20261021-020000.md"


def test_example_scripts_follow_updates_without_losing_edits(tmp_path, monkeypatch):
    from harness import config
    root, data = tmp_path / "app", tmp_path / "data"
    (root / "scripts" / "examples").mkdir(parents=True)
    ex = root / "scripts" / "examples" / "pipe.py"
    monkeypatch.setattr(config, "ROOT", root)
    monkeypatch.setattr(config, "DATA_DIR", data)
    monkeypatch.setattr(config, "SCRIPTS_DIR", data / "scripts")
    (data / "scripts").mkdir(parents=True)
    mine = data / "scripts" / "pipe.py"
    mine.write_text("old version I dragged in\n")        # never installed by the app
    ex.write_text("v1\n")
    assert config.sync_examples() == ["pipe.py"]
    assert mine.read_text() == "v1\n"
    assert list((data / "backups").glob("pipe-*.py"))   # the old copy was kept
    mine.write_text("v1 + my edit\n")
    assert config.sync_examples() == [] and mine.read_text() == "v1 + my edit\n"   # edits stay
    ex.write_text("v2\n")
    assert config.sync_examples() == ["pipe.py"] and mine.read_text() == "v2\n"     # update wins
    assert len(list((data / "backups").glob("pipe-*.py"))) >= 1
    ex.write_text("v3\n")
    assert config.sync_examples() == ["pipe.py"] and mine.read_text() == "v3\n"


def test_remote_access_only_for_signed_in_tailscale_devices(monkeypatch):
    from harness import remote
    from harness.server import app
    from starlette.testclient import TestClient as TC
    phone = TC(app, client=("100.101.102.103", 50000), headers={"x-harness": "1"})
    lan = TC(app, client=("192.168.1.20", 50000), headers={"x-harness": "1"})
    mac = TestClient(app, headers={"x-harness": "1"})
    assert phone.get("/api/status").status_code == 403            # remote access is off
    assert mac.post("/api/remote", json={"enabled": True}).status_code == 400   # no password yet
    assert mac.post("/api/remote", json={"password": "short"}).status_code == 400
    assert mac.post("/api/remote", json={"password": "correct horse", "enabled": True}).json()["enabled"]
    assert "remote_password" not in mac.put("/api/settings", json={"remote_password": "x$y"}).json() \
        or mac.get("/api/settings").json()["remote_password"] == "set"
    assert remote.check_password("correct horse")                 # the PUT didn't overwrite it
    assert lan.get("/api/status").status_code == 403              # not on Tailscale
    assert phone.get("/api/status").status_code == 401            # not signed in
    assert phone.get("/", follow_redirects=False).status_code in (302, 307)
    assert phone.get("/login").status_code == 200
    assert phone.post("/api/login", json={"password": "wrong"}).status_code == 401
    assert phone.post("/api/login", json={"password": "correct horse"}).status_code == 200
    assert phone.get("/api/status").status_code == 200            # signed in (cookie)
    assert phone.post("/api/remote", json={"enabled": False}).status_code == 403   # Mac only
    assert phone.post("/api/terminal", json={"command": "ls"}).status_code == 403
    assert phone.post("/api/runs/x/stop").status_code != 401
    mac.post("/api/remote", json={"sign_out_all": True})
    assert phone.get("/api/status").status_code == 401
    mac.post("/api/remote", json={"enabled": False})


def test_option_groups_and_popout_console(tmp_path):
    from harness import params
    from harness.server import app
    src = ("import argparse\nap = argparse.ArgumentParser()\nap.add_argument('--top')\n"
           "g = ap.add_argument_group('model')\ng.add_argument('--ctx', type=int)\n"
           "g = ap.add_argument_group('build')\ng.add_argument('--fix-attempts', type=int)\n")
    ps = {p["dest"]: p["group"] for p in params.parse_params(src)}
    assert ps == {"top": "", "ctx": "model", "fix_attempts": "build"}
    c = TestClient(app, headers={"x-harness": "1"})
    page = c.get("/static/console.html")
    assert page.status_code == 200 and "console.js" in page.text
    assert c.get("/static/console.js").status_code == 200


def test_update_asks_before_downloading_while_scripts_run(monkeypatch):
    # updating restarts the app, which stops running scripts: with scripts running,
    # nothing is downloaded unless the user says go ahead (force)
    from harness import server, updater
    c = TestClient(server.app, headers={"x-harness": "1"})
    pulled = []
    monkeypatch.setattr(updater, "apply", lambda: pulled.append(1) or {"ok": True, "log": "", "version": "v2"})
    monkeypatch.setattr(server.runs, "active", lambda: ["a run"])
    r = c.post("/api/update/apply")
    assert r.status_code == 409 and not pulled
    assert c.post("/api/update/apply?force=true").json()["ok"] and pulled
    monkeypatch.setattr(server.runs, "active", lambda: [])
    assert c.post("/api/update/apply").status_code == 200


def test_downloaded_but_not_restarted_is_shown(monkeypatch):
    # an update pulled while the app kept running the old code: "restart to use it",
    # not "up to date"
    from harness import server, updater
    monkeypatch.setattr(updater, "RUNNING", "old 2026-10-20")
    monkeypatch.setattr(updater, "version", lambda: "new 2026-10-21")
    monkeypatch.setattr(updater, "_seen", {"at": 0.0, "value": False})
    monkeypatch.setattr(updater, "_check", lambda: {"available": False, "behind": 0, "error": None})
    assert updater.check()["restart_needed"] is True
    s = TestClient(server.app, headers={"x-harness": "1"}).get("/api/status").json()
    assert s["update"]["restart_needed"] is True and s["update"]["running"] == "old 2026-10-20"


IOREG_AC = '''+-o AppleSmartBattery  <class AppleSmartBattery>
    {
      "ExternalConnected" = Yes
      "IsCharging" = Yes
      "Voltage" = 12650
      "InstantAmperage" = 1500
      "PowerTelemetryData" = {"AdapterEfficiencyLoss"=1250,"BatteryPower"=5000,"SystemCurrentIn"=1500,"SystemPowerIn"=30000,"SystemLoad"=24500,"SystemVoltageIn"=20000}
    }'''

IOREG_BATTERY = '''+-o AppleSmartBattery  <class AppleSmartBattery>
    {
      "ExternalConnected" = No
      "Voltage" = 12000
      "InstantAmperage" = 18446744073709549616
    }'''


def test_heat_is_the_power_the_laptop_uses_plus_its_chargers_losses():
    from harness import sensors
    # on the charger: the system's own use (not what goes into the battery), plus
    # the brick's losses on what it delivers
    r = sensors.heat_reading(IOREG_AC, {}, {})
    assert r["laptop_w"] == 24.5 and r["brick_w"] == round(30.0 * sensors.BRICK_LOSS, 1)
    assert r["heat_w"] == round(24.5 + 30.0 * sensors.BRICK_LOSS, 1)
    assert r["heat_btu_h"] == round(r["heat_w"] * 3.412, 0) or abs(r["heat_btu_h"] - r["heat_w"] * 3.412) < 1
    assert "system load" in r["power_source"] and r["on_ac"]
    # on battery: voltage x current (ioreg prints the negative current as unsigned)
    r = sensors.heat_reading(IOREG_BATTERY, {}, {})
    assert r["laptop_w"] == 24.0 and r["brick_w"] is None and r["heat_w"] == 24.0
    # nothing from the battery controller: macmon's system power
    r = sensors.heat_reading("", {"sys_power_w": 18.2}, {})
    assert r["heat_w"] == 18.2 and "macmon" in r["power_source"]
    assert sensors.heat_reading("", {}, {}) == {} or sys.platform.startswith("linux")


def test_a_run_adds_up_the_heat_given_off_while_it_ran():
    from harness import runner as rn
    from harness.server import app, runs
    ensure_dirs()
    (SCRIPTS_DIR / "t_heat.py").write_text("import time; print('warm', flush=True); time.sleep(30)")
    c = TestClient(app, headers={"x-harness": "1"})
    rid = c.post("/api/runs", json={"script": "t_heat.py"}).json()["id"]
    try:
        run = runs.runs[rid]
        for _ in range(50):
            if run.proc:
                break
            time.sleep(0.1)
        run._heat_t = time.time() - 30                    # the last reading, 30 s ago
        runs.on_tick({"available_pct": 50, "level": "green", "heat_w": 36.0})
        assert abs(run.heat_wh - 36.0 * 30 / 3600) < 0.01  # 0.3 Wh
        assert c.get(f"/api/runs/{rid}").json()["heat_wh"] > 0
    finally:
        c.post(f"/api/runs/{rid}/stop")
    assert rn.fmt_energy(1500) == "1.50 kWh (5,118 BTU)" and rn.fmt_energy(2.5) == "2.5 Wh (9 BTU)"


def test_console_runs_a_multi_line_shell_script():
    from harness.server import app, runs
    c = TestClient(app, headers={"x-harness": "1"})
    r = c.post("/api/terminal", json={"command": "cd /tmp\necho one\necho two-$((1+1))"}).json()
    assert "run" in r and "more line" in r["run"]["script"]          # one run, not a folder change
    rid = r["run"]["id"]
    for _ in range(50):
        d = c.get(f"/api/runs/{rid}").json()
        if d["status"] != "running":
            break
        time.sleep(0.1)
    assert "one" in d["output"] and "two-2" in d["output"]


def test_restarts_natively_only_under_rosetta_on_apple_silicon(monkeypatch):
    import subprocess as sp
    from harness import __main__ as hm
    answers = {"sysctl.proc_translated": "1", "hw.optional.arm64": "1"}
    monkeypatch.setattr(hm, "_sysctl", lambda name: answers[name])
    monkeypatch.setattr(hm.sys, "platform", "darwin")
    monkeypatch.delenv("AIHARNESS_NATIVE_TRIED", raising=False)
    runs_native = {"ok": 0}
    monkeypatch.setattr(hm.subprocess, "run", lambda *a, **k: sp.CompletedProcess(a, runs_native["ok"]))
    argv = hm.native_restart_argv()
    assert argv[:2] == ["/usr/bin/arch", "-arm64"] and argv[3:5] == ["-m", "harness"]
    runs_native["ok"] = 1                        # this Python has no Apple Silicon code: stays as is
    assert hm.native_restart_argv() is None
    runs_native["ok"] = 0
    answers["sysctl.proc_translated"] = "0"      # already native
    assert hm.native_restart_argv() is None
    answers["sysctl.proc_translated"] = "1"
    monkeypatch.setenv("AIHARNESS_NATIVE_TRIED", "1")   # tried once already: never loops
    assert hm.native_restart_argv() is None
