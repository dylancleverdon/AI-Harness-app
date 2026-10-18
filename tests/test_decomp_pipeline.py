"""Offline end-to-end tests for scripts/examples/decomp_pipeline.py.

A fake LM Studio server (and, for one test, a fake Ghidra HTTP plugin) stands in
for the real ones, so the whole pipeline runs with real clang + libclang:
export -> rewrite -> split -> fix -> recover -> link.
"""
import importlib.util
import json
import re
import shutil
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "examples" / "decomp_pipeline.py"


def _load():
    spec = importlib.util.spec_from_file_location("decomp_pipeline", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["decomp_pipeline"] = mod          # dataclasses look the module up
    spec.loader.exec_module(mod)
    return mod


dp = _load()


def _have_toolchain():
    if not (shutil.which("clang++") or shutil.which("g++")):
        return False
    try:
        import clang.cindex as cx
        cfg = dp.Config(input_file=Path("x.cpp"), workdir=Path("."))
        dp._load_libclang(cfg)
        cx.Index.create()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _have_toolchain(),
                                reason="needs clang++/g++ and libclang")


# ---------------------------------------------------------------- the program

PSEUDO = {
    "1000": ("FUN_00001000", "int FUN_00001000(int param_1,int param_2)\n\n{\n"
                             "  return param_1 + param_2;\n}\n"),
    "1010": ("FUN_00001010", "int FUN_00001010(int param_1,int param_2,int param_3)\n\n{\n"
                             "  int iVar1;\n  iVar1 = FUN_00001000(param_1,param_2);\n"
                             "  return FUN_00001000(iVar1,param_3);\n}\n"),
    "1020": ("FUN_00001020", "uint FUN_00001020(uint param_1)\n\n{\n"
                             "  return param_1 * 3;\n}\n"),
    "1030": ("FUN_00001030", "int FUN_00001030(int param_1)\n\n{\n"
                             "  if (param_1 < 0) {\n    param_1 = 0;\n  }\n"
                             "  return param_1;\n}\n"),
    "1040": ("FUN_00001040", "int FUN_00001040(int param_1)\n\n{\n"
                             "  return param_1 * param_1;\n}\n"),
    "1050": ("FUN_00001050", "int FUN_00001050(int *param_1)\n\n{\n"
                             "  return *param_1 + param_1[1];\n}\n"),
    "1060": ("FUN_00001060", "void FUN_00001060(void)\n\n{\n"
                             "  DAT_00002000 = DAT_00002000 + 1;\n  return;\n}\n"),
}

# what the "model" writes for each function
REWRITES = {
    "FUN_00001000": ("int addNumbers(int a, int b) {\n    return a + b;\n}", "addNumbers"),
    "FUN_00001010": ("int addNumbers(int a, int b);\n\n"
                     "int sumThree(int a, int b, int c) {\n"
                     "    return addNumbers(addNumbers(a, b), c);\n}", "sumThree"),
    # uses a local it never declares -> the deterministic fix declares it
    "FUN_00001020": ("unsigned int tripleValue(unsigned int value) {\n"
                     "    uVar1 = value * 3;\n    return uVar1;\n}", "tripleValue"),
    # calls a helper that doesn't exist -> the model fix repairs it
    "FUN_00001030": ("int clampToZero(int x) {\n    return clampHelper(x);\n}", "clampToZero"),
    # broken in a way the model fix can't repair -> quarantined, then recovered
    "FUN_00001040": ("int squareIt(int n) {\n    return n * notDeclaredAnywhere(n, n);\n}",
                     "squareIt"),
    "FUN_00001050": ("struct Pair {\n    int first;\n    int second;\n};\n\n"
                     "int pairSum(Pair *p) {\n    return p->first + p->second;\n}", "pairSum"),
    "FUN_00001060": ("int g_counter = 0;\n\nvoid bumpCounter() {\n    g_counter++;\n}",
                     "bumpCounter"),
}

REPAIRS = {
    "clampToZero": "int clampToZero(int x) {\n    return x < 0 ? 0 : x;\n}",
    # a "fix" that drops the function: must be rejected
    "squareIt": "int somethingElse(int n) {\n    return 0;\n}",
}

RECOVERIES = {"squareIt": "int squareIt(int n) {\n    return n * n;\n}"}


# ---------------------------------------------------------------- fake servers

class FakeModel:
    """A fake LM Studio: /v1/models, /api/v0/models and streamed chat completions."""

    def __init__(self, model_id="fake-model"):
        self.model_id = model_id
        self.calls = {"rewrite": 0, "repair": 0, "recover": 0, "other": 0}
        self.rewrite_override = {}
        fake = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _json(self, obj, code=200):
                body = json.dumps(obj).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                if self.path.startswith("/api/v0/models"):
                    return self._json({"data": [{"id": fake.model_id, "state": "loaded",
                                                 "type": "llm"}]})
                if self.path.startswith("/v1/models"):
                    return self._json({"data": [{"id": fake.model_id}]})
                self._json({"error": "nope"}, 404)

            def do_POST(self):
                n = int(self.headers.get("Content-Length", 0))
                req = json.loads(self.rfile.read(n))
                text = fake.reply(req["messages"])
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                for i in range(0, len(text), 40):
                    chunk = {"choices": [{"delta": {"content": text[i:i + 40]}}]}
                    self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
                self.wfile.write(b"data: [DONE]\n\n")

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_port}/v1"

    def reply(self, messages):
        system, user = messages[0]["content"], messages[-1]["content"]
        if system.startswith("You turn Ghidra decompiler pseudocode"):
            self.calls["rewrite"] += 1
            g = re.search(r"Function: (\S+)", messages[1]["content"]).group(1)
            code, name = self.rewrite_override.get(g) or REWRITES[g]
            return f"```cpp\n{code}\n```\nNAME: {name}"
        if system.startswith("You are a C++ repair tool"):
            self.calls["repair"] += 1
            body = user.split("// Function to fix:")[-1]
            for name, fixed in REPAIRS.items():
                if re.search(rf"\b{name}\s*\(", body):
                    return f"```cpp\n{fixed}\n```"
            return "no idea"
        if system.startswith("You rewrite ONE function"):
            self.calls["recover"] += 1
            for name, fixed in RECOVERIES.items():
                if re.search(rf"\b{name}\s*\(", user.split("Target prototype")[-1][:400]):
                    return f"```cpp\n{fixed}\n```"
            return "no idea"
        self.calls["other"] += 1
        return "no idea"

    def close(self):
        self.server.shutdown()


class FakeGhidra:
    """The original (plain-text) Ghidra MCP plugin: /list_functions + /decompile_function."""

    def __init__(self, pseudo):
        self.pseudo = dict(pseudo)
        self.decompiles = 0
        fake = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _text(self, text, code=200):
                body = text.encode()
                self.send_response(code)
                self.send_header("Content-Type", "text/plain")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                u = urlparse(self.path)
                if u.path == "/list_functions":
                    return self._text("".join(f"{n} at {a}\n"
                                              for a, (n, _) in fake.pseudo.items()))
                if u.path == "/decompile_function":
                    a = parse_qs(u.query)["address"][0].lower().removeprefix("0x")
                    fake.decompiles += 1
                    return self._text(fake.pseudo[a][1])
                self._text("not found", 404)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_port}/"

    def close(self):
        self.server.shutdown()


@pytest.fixture
def model():
    m = FakeModel()
    yield m
    m.close()


def write_export(workdir: Path, pseudo=PSEUDO):
    g = workdir / "ghidra"
    g.mkdir(parents=True, exist_ok=True)
    (g / "ghidra_export.json").write_text(json.dumps({
        "version": 2, "ghidra": "test",
        "functions": [{"name": n, "addr": a} for a, (n, _) in pseudo.items()],
        "pseudocode": {a: c for a, (_, c) in pseudo.items()},
        "signatures": {a: c.split("\n")[0] for a, (_, c) in pseudo.items()},
        "datatypes": [{"kind": "struct", "name": "Pair", "path": "/", "size": 8,
                       "fields": [{"off": 0, "size": 4, "name": "first", "type": "int"},
                                  {"off": 4, "size": 4, "name": "second", "type": "int"}]}]}))


def run(workdir, model, *extra):
    argv = ["--workdir", str(workdir), "--api", model.url, *extra]
    return dp.main(argv)


def manifest(workdir):
    return json.loads((workdir / "build" / "manifest.json").read_text())


def by_name(workdir):
    return {r["name"]: r for r in manifest(workdir).values()}


# ---------------------------------------------------------------- tests

def test_end_to_end(tmp_path, model):
    write_export(tmp_path)
    assert run(tmp_path, model) == 0

    cpp = (tmp_path / "rewrite" / "rewritten.cpp").read_text()
    for name in ("addNumbers", "sumThree", "tripleValue", "clampToZero", "squareIt",
                 "pairSum", "bumpCounter"):
        assert re.search(rf"\b{name}\s*\(", cpp), name
    assert cpp.count("//@ghidra ") == 7
    assert "FUN_00001000" not in cpp.split("//@ghidra")[0]   # caller sees the new name

    recs = by_name(tmp_path)
    assert all(r["compiles"] for r in recs.values())
    assert recs["squareIt"]["rederived"] and recs["squareIt"]["recovery"] == "rewrite"
    assert recs["clampToZero"]["attempts"] >= 1
    assert "uVar1" in (tmp_path / "build" / recs["tripleValue"]["file"]).read_text()
    assert (tmp_path / "build" / "quarantine").is_dir()      # original kept there

    report = json.loads((tmp_path / "report.json").read_text())
    assert report["link"]["ok"] is True
    assert report["build"]["compile"] == 7 and report["build"]["quarantined"] == 0
    assert report["build"]["rederived"] == 1
    assert report["rewrite"]["done"] == 7 and report["rewrite"]["renamed"] == 7
    assert report["export"]["datatypes"] == 1 and report["export"]["signatures"] == 7
    st = json.loads((tmp_path / "pipeline_state.json").read_text())
    assert all(st["stages"][s]["done"] for s in dp.STAGES)
    assert st["stages"]["rewrite"]["model"] == "fake-model"
    assert (tmp_path / "REPORT.md").read_text().startswith("# Decomp pipeline report")
    assert model.calls["rewrite"] == 7 and model.calls["recover"] == 1


def test_second_run_is_a_noop(tmp_path, model):
    write_export(tmp_path)
    assert run(tmp_path, model) == 0
    before = dict(model.calls)
    files = {p: p.read_text() for p in (tmp_path / "build" / "funcs").glob("*.cpp")}
    assert run(tmp_path, model) == 0
    assert model.calls == before                      # nothing asked of the model
    assert {p: p.read_text() for p in (tmp_path / "build" / "funcs").glob("*.cpp")} == files
    assert json.loads((tmp_path / "report.json").read_text())["link"]["ok"] is True


def test_redo_rewrite_replaces_in_place_and_never_deletes(tmp_path, model):
    write_export(tmp_path)
    assert run(tmp_path, model) == 0
    old_cpp = (tmp_path / "rewrite" / "rewritten.cpp").read_text()

    # redo, but stop after one function (like an accidental click, then Ctrl+C):
    # every other function must still be there, in its old version
    model.rewrite_override["FUN_00001000"] = (
        "int addTwo(int left, int right) {\n    return left + right;\n}", "addTwo")
    assert run(tmp_path, model, "--redo", "rewrite", "--max", "1") == 0
    cpp = (tmp_path / "rewrite" / "rewritten.cpp").read_text()
    assert cpp.count("//@ghidra ") == 7
    assert "left + right" in cpp            # the new version...
    assert "addTwo" not in cpp              # ...under the name its callers already use
    for name in ("tripleValue", "clampToZero", "squareIt", "pairSum", "bumpCounter"):
        assert re.search(rf"\b{name}\s*\(", cpp)
    progress = json.loads((tmp_path / "rewrite" / "progress.json").read_text())
    stale = [e for e in progress["functions"].values() if e.get("stale")]
    assert len(stale) == 6 and all(e["status"] == "done" for e in stale)
    assert progress["functions"]["1000"]["suggested_name"] == "addTwo"

    snaps = list((tmp_path / "snapshots").iterdir())
    assert len(snaps) == 1 and "redo-rewrite" in snaps[0].name
    assert (snaps[0] / "rewrite" / "rewritten.cpp").read_text() == old_cpp

    # carrying on finishes the redo, then updates the build: the changed function
    # gets its new code, the unchanged ones keep their fixes
    calls = model.calls["rewrite"]
    assert run(tmp_path, model) == 0
    assert model.calls["rewrite"] == calls + 6
    recs = by_name(tmp_path)
    assert "left + right" in (tmp_path / "build" / recs["addNumbers"]["file"]).read_text()
    assert "x < 0 ? 0 : x" in (tmp_path / "build" / recs["clampToZero"]["file"]).read_text()
    assert json.loads((tmp_path / "report.json").read_text())["link"]["ok"] is True


def test_redo_split_snapshots_the_fixed_build(tmp_path, model):
    write_export(tmp_path)
    assert run(tmp_path, model) == 0
    clamp = tmp_path / "build" / by_name(tmp_path)["clampToZero"]["file"]
    fixed = clamp.read_text()
    assert run(tmp_path, model, "--redo", "split") == 0
    snap = next(p for p in (tmp_path / "snapshots").iterdir() if "redo-build" in p.name)
    assert (snap / "build" / "funcs" / clamp.name).read_text() == fixed
    assert by_name(tmp_path)["clampToZero"]["compiles"]
    assert json.loads((tmp_path / "report.json").read_text())["link"]["ok"] is True


def test_from_and_to(tmp_path, model):
    write_export(tmp_path)
    assert run(tmp_path, model, "--to", "rewrite") == 0
    assert (tmp_path / "rewrite" / "rewritten.cpp").exists()
    assert not (tmp_path / "build" / "manifest.json").exists()
    with pytest.raises(SystemExit):
        run(tmp_path, model, "--from", "fix")             # no build yet
    assert run(tmp_path, model, "--from", "split", "--to", "fix") == 0
    st = json.loads((tmp_path / "pipeline_state.json").read_text())
    assert st["stages"]["fix"]["done"] and "recover" not in st["stages"]
    calls = model.calls["rewrite"]
    assert run(tmp_path, model, "--from", "recover") == 0
    assert model.calls["rewrite"] == calls
    assert json.loads((tmp_path / "report.json").read_text())["link"]["ok"] is True


def test_changed_pseudocode_rewrites_just_that_function(tmp_path, model):
    write_export(tmp_path)
    assert run(tmp_path, model) == 0
    pseudo = dict(PSEUDO)
    pseudo["1050"] = ("FUN_00001050", PSEUDO["1050"][1].replace("param_1[1]", "param_1[1] + 0"))
    write_export(tmp_path, pseudo)
    calls = model.calls["rewrite"]
    assert run(tmp_path, model) == 0
    assert model.calls["rewrite"] == calls + 1


def test_adopt_old_runs(tmp_path, model):
    # make an old-style pseudo_to_cpp folder and DECOMP_FIXER workdir from a run
    first = tmp_path / "first"
    write_export(first)
    assert run(first, model, "--to", "split") == 0
    old_out = tmp_path / "old_out"
    old_out.mkdir()
    shutil.copy(first / "ghidra" / "ghidra_export.json", old_out)
    for name in ("progress.json", "names.txt", "function_index.json"):
        shutil.copy(first / "rewrite" / name, old_out)
    shutil.copytree(first / "rewrite" / ".rewritten", old_out / ".rewritten")
    shutil.copy(first / "rewrite" / "rewritten.cpp", old_out / "rewritten code.cpp")
    old_build = tmp_path / "old_build"
    shutil.copytree(first / "build", old_build)
    (old_build / "build_state.json").rename(old_build / "pipeline_state.json")

    proj = tmp_path / "proj"
    calls = dict(model.calls)
    assert run(proj, model, "--adopt-rewrite", str(old_out), "--adopt-build",
               str(old_build)) == 0
    assert model.calls["rewrite"] == calls["rewrite"]   # nothing rewritten again
    assert (proj / "build" / "build_state.json").exists()
    assert (old_out / "progress.json").exists()          # copied, not moved
    assert json.loads((proj / "report.json").read_text())["link"]["ok"] is True


def test_http_export_and_redo_export_in_place(tmp_path, model):
    ghidra = FakeGhidra(PSEUDO)
    try:
        assert run(tmp_path, model, "--ghidra", ghidra.url, "--to", "export") == 0
        data = json.loads((tmp_path / "ghidra" / "ghidra_export.json").read_text())
        assert len(data["pseudocode"]) == 7 and ghidra.decompiles == 7
        assert run(tmp_path, model, "--ghidra", ghidra.url, "--to", "rewrite") == 0

        # rename-in-Ghidra style change, then --redo export: entries replaced in place,
        # and only the function whose pseudocode changed is rewritten again
        ghidra.pseudo["1020"] = ("FUN_00001020", PSEUDO["1020"][1].replace("* 3", "* 3U"))
        calls = model.calls["rewrite"]
        assert run(tmp_path, model, "--ghidra", ghidra.url, "--redo", "export",
                   "--to", "rewrite") == 0
        assert ghidra.decompiles == 14
        data = json.loads((tmp_path / "ghidra" / "ghidra_export.json").read_text())
        assert "* 3U" in data["pseudocode"]["1020"] and len(data["pseudocode"]) == 7
        assert model.calls["rewrite"] == calls + 1
        assert any("redo-export" in p.name for p in (tmp_path / "snapshots").iterdir())
    finally:
        ghidra.close()


def test_unreadable_progress_is_kept_not_overwritten(tmp_path, model):
    write_export(tmp_path)
    (tmp_path / "rewrite").mkdir(parents=True)
    (tmp_path / "rewrite" / "progress.json").write_text("{not json")
    assert run(tmp_path, model, "--to", "rewrite") == 0
    kept = list((tmp_path / "rewrite").glob("progress.json.unreadable-*"))
    assert len(kept) == 1 and kept[0].read_text() == "{not json"


def test_emit_ghidra_script(tmp_path):
    assert dp.main(["--workdir", str(tmp_path), "--emit-ghidra-script"]) == 0
    java = (tmp_path / "ghidra" / "GhidraExport.java").read_text()
    assert str(tmp_path / "ghidra") in java and '"version\\":2' in java
    assert "getPrototypeString" in java and "dataTypesJson" in java


def test_options():
    ap = dp.build_parser()
    for a in ap._actions:
        if a.dest in ("from_stage", "to_stage", "redo"):
            assert list(a.choices) == dp.STAGES
    assert ap.parse_args(["--redo"]).redo == ["rewrite"]          # old bare --redo
    assert ap.parse_args(["--redo", "export", "--redo", "fix"]).redo == ["export", "fix"]


def test_pause_without_input_carries_on(tmp_path, model):
    write_export(tmp_path)
    assert run(tmp_path, model, "--to", "rewrite", "--pause-between-stages") == 0
