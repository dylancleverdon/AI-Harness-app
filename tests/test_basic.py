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
