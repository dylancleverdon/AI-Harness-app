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
