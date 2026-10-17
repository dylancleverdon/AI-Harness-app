import os
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
    c = TestClient(app)
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
    c = TestClient(app)
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
    c = TestClient(app)
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
    c = TestClient(app)
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
    c = TestClient(app)
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
