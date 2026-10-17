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


def test_ai_edit_chunks_and_stream(monkeypatch):
    from harness import ai_edit
    text = "".join(f"line {i}\n" if i % 5 else "\n" for i in range(400))
    chunks = ai_edit.split_into_chunks(text, 300)
    assert "".join(chunks) == text and len(chunks) > 5

    class R:
        status_code = 200
        text = ""

        def __init__(self, content):
            self._c = content

        def json(self):
            return {"choices": [{"message": {"content": self._c}, "finish_reason": "stop"}]}

    def fake_post(url, json=None, timeout=None):
        user = json["messages"][1]["content"]
        section = user.split("SECTION TO EDIT:\n")[1].split("\nREAD-ONLY CONTEXT AFTER")[0]
        return R("```\n" + section.replace("line", "LINE") + "\n```")

    monkeypatch.setattr(ai_edit.httpx, "post", fake_post)
    monkeypatch.setattr(ai_edit, "context_length", lambda m: 500)
    events = list(ai_edit.edit_stream("a.py", text, "uppercase", model="m"))
    assert events[-1]["type"] == "done" and events[-1]["changed"]
    assert events[-1]["edited"].count("LINE") == text.count("line")

    monkeypatch.setattr(ai_edit.httpx, "post", lambda *a, **k: (_ for _ in ()).throw(ai_edit.httpx.ConnectError("x")))
    assert list(ai_edit.edit_stream("a.py", "x\n", "i", model="m"))[-1]["type"] == "error"

    events = list(ai_edit.edit_stream("a.py", "x\n", "i", model="m", mem_level=lambda: "red"))
    assert "memory guard" in events[-1]["message"]


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
