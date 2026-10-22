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

# what the "model" writes when asked to replace a few lines containing this text
EDITS = {
    "clampHelper(x)": "    return x < 0 ? 0 : x;",
    "v + v + 1": "    return v + v;",
    "addNumbers(x, 1, 2)": "    return addNumbers(addNumbers(x, 1), 2);",
    # an edit that makes things worse: must be undone
    "notDeclaredAnywhere(n, n)": "    return n * notDeclaredAnywhere(n, n) + alsoMissing(n);",
}

RECOVERIES = {"squareIt": "int squareIt(int n) {\n    return n * n;\n}"}


# ---------------------------------------------------------------- fake servers

class FakeModel:
    """A fake LM Studio: /v1/models, /api/v0/models and streamed chat completions."""

    def __init__(self, model_id="fake-model"):
        self.model_id = model_id
        self.calls = {"rewrite": 0, "goal": 0, "plan": 0, "edit": 0, "locate": 0,
                      "names": 0, "recover": 0, "other": 0}
        self.named = 0
        self.rewrite_override = {}
        self.no_code = set()          # Ghidra names the "model" returns no code for
        self.think_only = set()       # ... or only "thinks" about, with no reply
        self.think_unless_told = set()  # ... thinks only, unless asked with /no_think
        self.cut_fence = set()        # ... answers with the closing ``` missing
        self.too_long = set()         # ... whose whole-function answer hits the token limit
        self.piece_limit = 0          # pieces longer than this get a cut-off answer
        self.ctx_error = {}           # Ghidra name -> "<ctxerr>" or "<http400>"
        self.seen_no_think = 0
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
                if text == "<http400>":             # refused before answering
                    return self._json({"error": "Trying to keep the first 9000 tokens when "
                                                "context the overflows."}, 400)
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                finish = None
                if text == "<ctxerr>":              # LM Studio's error inside the stream
                    err = {"error": {"message": "The number of tokens to keep from the "
                                                "initial prompt is greater than the context length"}}
                    self.wfile.write(f"data: {json.dumps(err)}\n\n".encode())
                    return
                if text.startswith("<cut>"):        # an answer that hit the token limit
                    text, finish = text[5:], "length"
                if text == "<think-only>":     # LM Studio's separate reasoning stream
                    chunk = {"choices": [{"delta": {"reasoning_content": "hmm " * 50}}]}
                    self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
                    text = ""
                for i in range(0, len(text), 40):
                    chunk = {"choices": [{"delta": {"content": text[i:i + 40]}}]}
                    self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
                if finish:
                    chunk = {"choices": [{"delta": {}, "finish_reason": finish}]}
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
            if g in self.no_code:
                return "Sorry, I can't help with that."
            if g in self.think_only:
                return "<think-only>"
            if g in self.think_unless_told:
                if "/no_think" not in user:
                    return "<think-only>"
                self.seen_no_think += 1
            if g in self.ctx_error:
                return self.ctx_error[g]
            if g in self.too_long:
                return "<cut>```cpp\nint startedWriting(int a) {\n    if (a) {"
            if g in self.cut_fence:
                code, name = REWRITES[g]
                return f"```cpp\n{code}"
            code, name = self.rewrite_override.get(g) or REWRITES[g]
            return f"```cpp\n{code}\n```\nNAME: {name}"
        if system.startswith("You turn part of a Ghidra"):
            self.calls["piece"] = self.calls.get("piece", 0) + 1
            piece = user.split("to rewrite:\n```c\n", 1)[1].rsplit("\n```", 1)[0]
            if self.piece_limit and len(piece) > self.piece_limit:
                return "<cut>```cpp\n" + piece[:len(piece) // 3]
            return f"```cpp\n{piece}\n```"
        if system.startswith("In 1-2 sentences"):
            self.calls["goal"] += 1
            return "It does a small calculation and returns the result."
        if system.startswith("You plan ONE small edit"):
            self.calls["plan"] += 1
            return "Change the marked line so it does what the task asks."
        if system.startswith("Output the corrected replacement"):
            self.calls["edit"] += 1
            window = user.split("Replace ONLY these line(s):")[-1]
            window = window.split("```cpp\n", 1)[-1].rsplit("```", 1)[0].rstrip("\n")
            for pattern, fixed in EDITS.items():
                if pattern in window:
                    return f"```cpp\n{fixed}\n```"
            return f"```cpp\n{window}\n```"             # no idea: same lines back
        if system.startswith("You find the line"):
            self.calls["locate"] += 1
            for l in user.splitlines():
                m = re.match(r"\s*(?:>>)?\s*(\d+) \| (.*)", l)
                if m and any(p in m.group(2) for p in EDITS):
                    return f"{m.group(1)} because that line looks wrong"
            return "2"
        if system.startswith("You choose names"):
            self.calls["names"] += 1
            kind = re.search(r"Name these (\w+)s", user).group(1)
            out = []
            for item in re.findall(r"^- (\S+)$", user, re.M):
                self.named += 1
                out.append(f"{item} -> " + {
                    "variable": f"value{self.named}", "field": f"amount{self.named}",
                    "global": f"globalValue{self.named}", "constant": f"MAGIC_{self.named}",
                    "function": f"computeThing{self.named}",
                    "module": f"part_{self.named}"}[kind])
            return "\n".join(out)
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
    assert recs["squareIt"]["rederived"] and recs["squareIt"]["recovery"] == "faithful-pseudocode"
    assert recs["clampToZero"]["attempts"] >= 1
    trip = (tmp_path / "build" / recs["tripleValue"]["file"]).read_text()
    assert "uVar1" not in trip and re.search(r"\bvalue\d+\b", trip)   # renamed by improve
    assert (tmp_path / "build" / "quarantine").is_dir()      # original kept there

    report = json.loads((tmp_path / "report.json").read_text())
    assert report["link"]["ok"] is True
    assert report["build"]["compile"] == 7 and report["build"]["quarantined"] == 0
    assert report["build"]["rederived"] == 1
    assert report["rewrite"]["done"] == 7 and report["rewrite"]["renamed"] == 7
    assert report["export"]["datatypes"] == 1 and report["export"]["signatures"] == 7
    st = json.loads((tmp_path / "pipeline_state.json").read_text())
    assert all(st["stages"][s]["done"] for s in dp.STAGES if s != "test")
    assert st["stages"]["test"]["note"] == "no --plugin"          # skipped, and says why
    assert st["stages"]["rewrite"]["model"] == "fake-model"
    assert (tmp_path / "REPORT.md").read_text().startswith("# Decomp pipeline report")
    assert model.calls["rewrite"] == 7 and model.calls["recover"] == 0


def test_second_run_is_a_noop(tmp_path, model):
    write_export(tmp_path)
    assert run(tmp_path, model) == 0
    assert run(tmp_path, model) == 0     # (a task rejected once gets one more try here)
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
    assert run(tmp_path, model, "--to", "rewrite") == 0      # option off: left alone
    assert model.calls["rewrite"] == calls
    assert "still marked to be rewritten again" in (tmp_path / "pipeline.log").read_text()
    assert run(tmp_path, model, "--redo", "rewrite") == 0     # on again: carries on
    assert model.calls["rewrite"] == calls + 6
    by_addr = {r["ghidra_addr"]: r for r in manifest(tmp_path).values()}
    assert "left + right" in (tmp_path / "build" / by_addr["1000"]["file"]).read_text()
    recs = by_name(tmp_path)
    assert "x < 0 ? 0 : x" in (tmp_path / "build" / recs["clampToZero"]["file"]).read_text()
    assert json.loads((tmp_path / "report.json").read_text())["link"]["ok"] is True


def test_redo_split_snapshots_the_fixed_build(tmp_path, model):
    write_export(tmp_path)
    assert run(tmp_path, model, "--to", "link") == 0
    clamp = tmp_path / "build" / by_name(tmp_path)["clampToZero"]["file"]
    fixed = clamp.read_text()
    assert run(tmp_path, model, "--redo", "split", "--to", "link") == 0
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
    assert run(tmp_path, model, "--from", "recover", "--to", "link") == 0
    assert model.calls["rewrite"] == calls
    assert json.loads((tmp_path / "report.json").read_text())["link"]["ok"] is True


def test_changed_pseudocode_rewrites_just_that_function(tmp_path, model):
    write_export(tmp_path)
    assert run(tmp_path, model, "--to", "link") == 0
    pseudo = dict(PSEUDO)
    pseudo["1050"] = ("FUN_00001050", PSEUDO["1050"][1].replace("param_1[1]", "param_1[1] + 0"))
    write_export(tmp_path, pseudo)
    calls = model.calls["rewrite"]
    assert run(tmp_path, model, "--to", "link") == 0
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
               str(old_build), "--to", "link") == 0
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


def test_skipped_functions_are_marked_redo_and_tried_again(tmp_path, model):
    write_export(tmp_path)
    model.no_code = {"FUN_00001050"}
    assert run(tmp_path, model, "--to", "rewrite") == 0
    prog = json.loads((tmp_path / "rewrite" / "progress.json").read_text())
    assert prog["functions"]["1050"]["status"] == "skipped"
    assert prog["functions"]["1050"]["reason"].startswith("model returned no code")

    # next run: marked redo at start-up and tried again (still no code -> still listed)
    calls = model.calls["rewrite"]
    assert run(tmp_path, model, "--to", "rewrite") == 0
    assert model.calls["rewrite"] == calls + 2         # the try and its automatic retry
    prog = json.loads((tmp_path / "rewrite" / "progress.json").read_text())
    assert prog["functions"]["1050"]["retries"] == 1

    # the model behaves now: it's rewritten and the whole thing links
    model.no_code = set()
    assert run(tmp_path, model, "--to", "link") == 0
    prog = json.loads((tmp_path / "rewrite" / "progress.json").read_text())
    assert prog["functions"]["1050"]["status"] == "done"
    assert json.loads((tmp_path / "report.json").read_text())["link"]["ok"] is True


def test_failed_redo_keeps_old_version_and_retries(tmp_path, model):
    write_export(tmp_path)
    assert run(tmp_path, model, "--to", "rewrite") == 0
    model.no_code = {"FUN_00001000"}
    assert run(tmp_path, model, "--to", "rewrite", "--redo", "rewrite",
               "--functions", "FUN_00001000") == 0
    e = json.loads((tmp_path / "rewrite" / "progress.json").read_text())["functions"]["1000"]
    assert e["status"] == "done" and e["stale"] and e["redo_failed"]
    assert "addNumbers" in (tmp_path / "rewrite" / "rewritten.cpp").read_text()
    model.no_code = set()
    calls = model.calls["rewrite"]
    assert run(tmp_path, model, "--to", "rewrite", "--redo", "rewrite") == 0   # carries on
    assert model.calls["rewrite"] == calls + 1


def test_model_activity_is_visible(tmp_path, model, capsys):
    write_export(tmp_path)
    model.think_only = {"FUN_00001050"}
    assert run(tmp_path, model, "--to", "rewrite") == 0
    out = capsys.readouterr().out
    assert "answered a test request" in out                   # startup check
    assert "model call" in out                                # per-function note
    assert "spent its whole answer thinking" in out           # thinking-only warning
    assert re.search(r"this run: \d+ function\(s\) done .* model answers", out)
    prog = json.loads((tmp_path / "rewrite" / "progress.json").read_text())
    assert prog["functions"]["1050"]["reason"].startswith("model returned no code")


# ---------------------------------------------------------------- the improve stage

def _p(addr, header, body):
    name = f"FUN_{int(addr, 16):08x}"
    return addr, (name, f"{header.replace('NAME', name)}\n\n{{\n{body}\n}}\n")


EXTRA = dict([
    _p("2000", "ulonglong NAME(uint param_1,uint param_2)",
       "  return CONCAT44(param_1,param_2) + ZEXT48(param_2);"),
    _p("2010", "uint NAME(uint param_1)", "  return (uint)((ulonglong)param_1 * 0xaaaaaaab >> 0x21);"),
    _p("2020", "int NAME(byte *param_1,int param_2)", "  return param_1[0] + param_2;"),
    _p("2030", "int NAME(int param_1)", "  return param_1 + 1;"),
    _p("2040", "char * NAME(void)", "  return s_text_00004000;"),
    _p("2050", "int NAME(int param_1)", "  return param_1 ^ 0x5a;"),
    _p("2060", "int NAME(int param_1,int param_2)", "  return (param_1 * 0x1f ^ param_2) + (param_1 >> 2);"),
    _p("2070", "int NAME(int param_1,int param_2)", "  return (param_1 * 0x1f ^ param_2) + (param_1 >> 2);"),
    _p("2080", "ulong NAME(char *param_1)", "  ulong n = 0;\n  while (param_1[n] != 0) n++;\n  return n;"),
    _p("2090", "int NAME(int *param_1)", "  return *param_1 - param_1[1];"),
    _p("20a0", "float NAME(int *param_1)", "  return *(float *)(param_1 + 1) * (float)*param_1;"),
    _p("20b0", "uint NAME(uint param_1)", "  return param_1 ^ 0x5f3759df;"),
    _p("20c0", "uint NAME(uint param_1)", "  return param_1 + 0x5f3759df;"),
    _p("20d0", "uint NAME(uint param_1)", "  return param_1 - 0x5f3759df;"),
    _p("20e0", "int NAME(int param_1,int param_2)", "  return param_1 + param_2;"),
    _p("20f0", "int NAME(int param_1)", "  int iVar1 = 0;\n  while (0 < param_1) { param_1--; iVar1++; }\n  return iVar1;"),
    _p("2100", "int NAME(int *param_1)", "  return param_1[1];"),
    _p("2110", "int NAME(int param_1)", "  return FUN_00001000(FUN_00001000(param_1,1),2);"),
    _p("2120", "bool NAME(int param_1)", "  return 0 < param_1;"),
    _p("2130", "int NAME(int param_1)", "  return param_1 * 2;"),
    _p("2140", "int NAME(void)", "  return DAT_00003000;"),
    _p("2150", "int NAME(int param_1)", "  return param_1 * 5 + 1;"),
])

EXTRA_REWRITES = {
    "FUN_00002000": ("uint64_t joinHalves(uint32_t high, uint32_t low) {\n"
                     "    return CONCAT44(high, low) + ZEXT48(low);\n}", "joinHalves"),
    "FUN_00002010": ("uint32_t divideByThree(uint32_t n) {\n"
                     "    return (uint32_t)(((uint64_t)n * 0xaaaaaaab) >> 0x21);\n}", "divideByThree"),
    "FUN_00002020": ("long ___stack_chk_guard = 0;\nvoid __stack_chk_fail();\n\n"
                     "int sumFirst(const unsigned char *data, int extra) {\n"
                     "    long guard = ___stack_chk_guard;\n    int total = data[0] + extra;\n"
                     "    if (___stack_chk_guard != guard) {\n        __stack_chk_fail();\n    }\n"
                     "    return total;\n}", "sumFirst"),
    "FUN_00002030": ("int addOne(int x) {\n    int unusedThing = 0;\n    return x + 1;\n}", "addOne"),
    "FUN_00002040": ("const char *bannerText() {\n    // AcmeCorp internal build\n"
                     "    return \"AcmeCorp Toolkit (c) 2021\";\n}", "bannerText"),
    "FUN_00002050": ("int acmecorpChecksum(int v) {\n    return v ^ 0x5a;\n}", "acmecorpChecksum"),
    "FUN_00002060": ("int mixValues(int a, int b) {\n    int t = a * 31;\n    t = t ^ b;\n"
                     "    return t + (a >> 2);\n}", "mixValues"),
    "FUN_00002070": ("int mixValuesCopy(int a, int b) {\n    int t = a * 31;\n    t = t ^ b;\n"
                     "    return t + (a >> 2);\n}", "mixValuesCopy"),
    "FUN_00002080": ("unsigned long textLength(const char *s) {\n    unsigned long n = 0;\n"
                     "    while (s[n] != 0) {\n        n++;\n    }\n    return n;\n}", "textLength"),
    "FUN_00002090": ("struct Couple {\n    int first;\n    int second;\n};\n\n"
                     "int coupleDiff(Couple *c) {\n    return c->first - c->second;\n}", "coupleDiff"),
    "FUN_000020a0": ("struct Blob {\n    int field_0x0;\n    float field_0x4;\n};\n\n"
                     "float blobScale(Blob *b) {\n    return b->field_0x4 * (float)b->field_0x0;\n}",
                     "blobScale"),
    "FUN_000020b0": ("unsigned int hashA(unsigned int x) {\n    return x ^ 0x5f3759df;\n}", "hashA"),
    "FUN_000020c0": ("unsigned int hashB(unsigned int x) {\n    return x + 0x5f3759df;\n}", "hashB"),
    "FUN_000020d0": ("unsigned int hashC(unsigned int x) {\n    return x - 0x5f3759df;\n}", "hashC"),
    "FUN_000020e0": ("int addCast(int a, int b) {\n    return (int)a + b;\n}", "addCast"),
    "FUN_000020f0": ("int countDown(int n) {\n    int steps = 0;\ntop:\n    if (n > 0) {\n"
                     "        n--;\n        steps++;\n        goto top;\n    }\n    return steps;\n}",
                     "countDown"),
    "FUN_00002100": ("int readSecond(Pair *p) {\n    return *(int *)((char *)p + 4);\n}", "readSecond"),
    "FUN_00002110": ("int addNumbers(int a, int b, int c);\n\nint addThree(int x) {\n"
                     "    return addNumbers(x, 1, 2);\n}", "addThree"),
    "FUN_00002120": ("bool isPositive(int x) {\n    if (x > 0)\n        return true;\n    else\n"
                     "        return false;\n}", "isPositive"),
    "FUN_00002130": ("int doubleIt(int v) {\n    return v + v + 1;\n}", "doubleIt"),
    "FUN_00002140": ("int DAT_00003000 = 7;\n\nint readSetting() {\n    return DAT_00003000;\n}",
                     "readSetting"),
    "FUN_00002150": ("int FUN_00002150(int x) {\n    return x * 5 + 1;\n}", "FUN_00002150"),
}


def test_improve_and_organize(tmp_path, model):
    REWRITES.update(EXTRA_REWRITES)
    write_export(tmp_path, {**PSEUDO, **EXTRA})
    (tmp_path / "privacy_blocklist.txt").write_text("# test\nAcmeCorp\n")
    assert run(tmp_path, model, "--improve-rounds", "4") == 0
    recs = by_name(tmp_path)
    b = tmp_path / "build"

    def code(name):
        return (b / recs[name]["file"]).read_text()

    assert "CONCAT44" not in code("joinHalves") and "ZEXT48" not in code("joinHalves")
    assert "/ 3" in code("divideByThree")
    assert "stack_chk" not in code("sumFirst")
    assert "unusedThing" not in code("addOne")
    assert "AcmeCorp" not in code("bannerText")
    assert "acmecorpChecksum" not in recs and "appChecksum" in recs
    assert re.search(r"return mixValues\(a, b\)", code("mixValuesCopy"))
    assert "strlen(" in code("textLength")
    lay = dp.struct_layouts(dp.Config(input_file=tmp_path / "rewrite" / "rewritten.cpp",
                                      workdir=b))
    assert ("Pair" in lay) != ("Couple" in lay)                 # merged into one
    assert not any(f.startswith("field_0x") for _, f, _, _ in lay["Blob"]["fields"])
    assert re.search(r"constexpr auto MAGIC_\d+ = 0x5f3759df;", (b / "shared.h").read_text())
    assert "0x5f3759df" not in code("hashA")
    assert "(int)a" not in code("addCast")
    assert "->second" in code("readSecond")
    assert "addNumbers(addNumbers(x, 1), 2)" in code("addThree")
    if shutil.which("clang-tidy"):
        assert "return x > 0;" in code("isPositive")
    assert "v + v;" in code("doubleIt") and "+ 1" not in code("doubleIt")
    assert "DAT_00003000" not in code("readSetting")
    assert "FUN_00002150" not in recs and any(n.startswith("computeThing") for n in recs)
    assert "goto" in code("countDown")                           # the model couldn't: parked
    notes = (b / "improve" / "notes" / (Path(recs["countDown"]["file"]).stem + ".md")).read_text()
    assert "[goto]" in notes and "rejected" in notes
    assert (b / "improve" / "history" / Path(recs["doubleIt"]["file"]).name).is_dir()

    report = json.loads((tmp_path / "report.json").read_text())
    assert report["improve"]["kept"] >= 15
    assert report["improve"]["score_after"] < report["improve"]["score_before"]
    assert (tmp_path / "privacy_report.txt").read_text().startswith("Nothing found")
    readme = (tmp_path / "final" / "README.md").read_text()
    assert "## Classes" in readme and "readSecond" in readme
    assert (tmp_path / "final" / "include" / "program.h").exists()

    # a re-split (e.g. after a rewrite redo) keeps the improvements to shared.h
    assert run(tmp_path, model, "--redo", "split", "--to", "link") == 0
    assert re.search(r"constexpr auto MAGIC_\d+", (b / "shared.h").read_text())
    assert "appChecksum" in by_name(tmp_path)
    for k in list(EXTRA_REWRITES):
        REWRITES.pop(k, None)


def test_no_code_is_explained_salvaged_and_retried(tmp_path, model):
    write_export(tmp_path)
    model.think_unless_told = {"FUN_00001000"}       # thinks until told /no_think
    model.cut_fence = {"FUN_00001010"}               # complete code, closing ``` missing
    model.no_code = {"FUN_00001020"}                 # never gives code
    assert run(tmp_path, model, "--to", "rewrite") == 0
    prog = json.loads((tmp_path / "rewrite" / "progress.json").read_text())["functions"]
    assert prog["1000"]["status"] == "done" and model.seen_no_think == 1
    assert prog["1010"]["status"] == "done"
    assert prog["1020"]["status"] == "skipped"
    assert prog["1020"]["reason"] == "model returned no code (no code block in the reply)"
    saved = (tmp_path / "rewrite" / "no_code" / "1020.txt").read_text()
    assert "===== reply 2 =====" in saved and "Sorry" in saved


def test_cut_off_function_is_split_right_away(tmp_path, model):
    write_export(tmp_path)
    model.too_long = {"FUN_00001010"}
    assert run(tmp_path, model, "--to", "rewrite") == 0
    e = json.loads((tmp_path / "rewrite" / "progress.json").read_text())["functions"]["1010"]
    assert e["status"] == "done" and e["pieces"] >= 1      # split in the same run
    assert e["cut_off_sizes"] and e["split_chars"] >= 600
    assert "//@ghidra 1010" in (tmp_path / "rewrite" / "rewritten.cpp").read_text()


def test_cut_off_pieces_are_split_further(tmp_path, model):
    body = "\n".join(f"  iVar1 = iVar1 + 0x{k:x} * param_1;" for k in range(1, 90))
    big = {"3000": ("FUN_00003000", "int FUN_00003000(int param_1)\n\n{\n  int iVar1;\n"
                                    f"  iVar1 = 0;\n{body}\n  return iVar1;\n}}\n")}
    REWRITES["FUN_00003000"] = ("int x(int a) {", "x")
    try:
        write_export(tmp_path, big)
        model.too_long = {"FUN_00003000"}
        model.piece_limit = 700
        assert run(tmp_path, model, "--to", "rewrite") == 0
        e = json.loads((tmp_path / "rewrite" / "progress.json").read_text())["functions"]["3000"]
        assert e["status"] == "done"
        assert len(e["cut_off_sizes"]) >= 2                  # whole function, then pieces
        assert e["split_chars"] < max(e["cut_off_sizes"])   # next time: start smaller
        code = (tmp_path / "rewrite" / ".rewritten" / "3000.cpp").read_text()
        assert "left as Ghidra" not in code and code.count("0x59") == 1
    finally:
        REWRITES.pop("FUN_00003000", None)


def test_context_sizes_follow_ctx(tmp_path, model):
    write_export(tmp_path)
    assert run(tmp_path, model, "--to", "export", "--ctx", "8192") == 0
    log = (tmp_path / "pipeline.log").read_text()
    assert f"recover stage up to {dp.recovery_chars(8192)}" in log
    assert dp.recovery_chars(4096) < dp.recovery_chars(8192) < dp.recovery_chars(16384)
    assert run(tmp_path, model, "--to", "export", "--model-ctx-chars", "5000") == 0
    assert "recover stage up to 5000 (set by --model-ctx-chars)" in (tmp_path / "pipeline.log").read_text()


def test_fix_stage_sees_whole_types_and_undoes_bad_edits(tmp_path, model):
    write_export(tmp_path)
    assert run(tmp_path, model, "--to", "fix", "--recover-later") == 0   # keep the quarantine to look at
    b = tmp_path / "build"
    cfg = dp.Config(input_file=tmp_path / "rewrite" / "rewritten.cpp", workdir=b)
    decls = dp.gather_declarations(cfg, ["first", "Pair", "NoSuchType"])
    assert "int first;" in decls and "int second;" in decls       # the whole struct
    assert "NoSuchType: not declared anywhere" in decls
    # squareIt couldn't be fixed: its quarantined copy is the code from before the
    # attempts, not the model's (worse) edit
    rec = by_name(tmp_path)["squareIt"]
    q = (b / "quarantine" / Path(rec["file"]).name).read_text()
    assert "alsoMissing" not in q and "notDeclaredAnywhere(n, n)" in q
    assert "notDeclaredAnywhere" in (b / "fix_report.txt").read_text() or \
        "undeclared" in (b / "fix_report.txt").read_text()
    notes = (b / "improve" / "notes" / (Path(rec["file"]).stem + ".md")).read_text()
    assert "undone" in notes


def test_prompt_too_long_for_lm_studio_is_split_not_fatal(tmp_path, model):
    write_export(tmp_path)
    model.ctx_error = {"FUN_00001010": "<ctxerr>", "FUN_00001030": "<http400>"}
    assert run(tmp_path, model, "--to", "rewrite") == 0          # the run carries on
    prog = json.loads((tmp_path / "rewrite" / "progress.json").read_text())["functions"]
    for k in ("1010", "1030"):
        assert prog[k]["status"] == "done" and prog[k]["pieces"] >= 1, k
        assert prog[k]["cut_off_sizes"]
    assert prog["1000"]["status"] == "done"


def test_platform_code_in_one_function_doesnt_hide_the_rest(tmp_path, model):
    # one rewrite with a Windows header and an #ifdef that's never closed: before,
    # the split lost every function after it
    model.rewrite_override["FUN_00001010"] = (
        "#include <windows.h>\n#ifdef _WIN32\nint addNumbers(int a, int b);\n\n"
        "int sumThree(int a, int b, int c) {\n    return addNumbers(addNumbers(a, b), c);\n}",
        "applyLowpassFilter")                       # and the copied example name
    write_export(tmp_path)
    assert run(tmp_path, model, "--to", "split") == 0
    cpp = (tmp_path / "rewrite" / "rewritten.cpp").read_text()
    assert "windows.h" not in cpp and "#ifdef" not in cpp
    assert len(manifest(tmp_path)) == 7                 # every function made it
    assert "applyLowpassFilter" not in by_name(tmp_path)  # the copied name was refused


def test_methods_namespaces_and_templates_reach_the_split(tmp_path, model):
    # shapes libclang doesn't list as top-level functions: before, they vanished
    model.rewrite_override["FUN_00001000"] = (
        "int Math::addNumbers(int a, int b) {\n    return a + b;\n}", "addNumbers")
    model.rewrite_override["FUN_00001020"] = (
        "namespace util {\nunsigned int tripleValue(unsigned int v) {\n"
        "    return v * 3;\n}\n}  // namespace util", "tripleValue")
    model.rewrite_override["FUN_00001040"] = (
        "template <typename T>\nT squareIt(T n) {\n    return n * n;\n}", "squareIt")
    write_export(tmp_path)
    assert run(tmp_path, model, "--to", "split") == 0
    cpp = (tmp_path / "rewrite" / "rewritten.cpp").read_text()
    assert "Math::" not in cpp and "addNumbers(" in cpp and "namespace util" not in cpp
    assert len(manifest(tmp_path)) == 7                 # every function made it
    assert "cut out by their marker" in (tmp_path / "build" / "worklist.log").read_text()


def test_stop_button_prints_errors_and_stops_cleanly(tmp_path, model):
    """The app's Stop button sends SIGTERM and kills after 4 seconds."""
    import signal
    import subprocess
    import time
    write_export(tmp_path)
    orig = model.reply

    def slow(msgs):
        time.sleep(1.5)
        return orig(msgs)
    model.reply = slow
    proc = subprocess.Popen([sys.executable, str(SCRIPT), "--workdir", str(tmp_path),
                             "--api", model.url, "--to", "link"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    log = tmp_path / "pipeline.log"
    deadline = time.time() + 240
    while time.time() < deadline and not (log.exists() and "Stage 5/10" in log.read_text()):
        time.sleep(0.5)
    time.sleep(3)                                   # well into the fix stage
    proc.send_signal(signal.SIGTERM)
    t0 = time.time()
    out, _ = proc.communicate(timeout=30)
    assert time.time() - t0 < 4, "must finish before the app's 4-second kill"
    text = log.read_text()
    assert "what the script struggled with" in text and "Paused." in text
    assert "what the script struggled with" in out          # printed, not just logged
    # nothing was quarantined just because the compilers were killed
    for r in manifest(tmp_path).values():
        if r["quarantined"]:
            assert r["name"] == "squareIt", r["name"]


def test_redo_suspect_marks_only_count_while_asked(tmp_path, model):
    write_export(tmp_path)
    assert run(tmp_path, model, "--to", "rewrite") == 0
    calls = model.calls["rewrite"]
    # tripleValue is flagged (decompiler names left): marked, but --max 0-ish stop
    assert run(tmp_path, model, "--to", "rewrite", "--redo-suspect", "--max", "1") == 0
    marked = [e for e in json.loads((tmp_path / "rewrite" / "progress.json").read_text())
              ["functions"].values() if e.get("stale")]
    after_max = model.calls["rewrite"]
    # without the option: nothing is redone, nothing is "not done"
    assert run(tmp_path, model, "--to", "rewrite") == 0
    assert model.calls["rewrite"] == after_max
    rep = json.loads((tmp_path / "report.json").read_text())["rewrite"]
    assert rep["done"] == 7
    # --cancel-redo drops whatever marks are left
    assert run(tmp_path, model, "--to", "rewrite", "--cancel-redo") == 0
    assert not any(e.get("stale") for e in json.loads(
        (tmp_path / "rewrite" / "progress.json").read_text())["functions"].values())
    assert after_max >= calls and marked is not None


def test_rejected_prompt_teaches_the_size_estimate(tmp_path, model):
    write_export(tmp_path)
    model.ctx_error = {"FUN_00001010": "<ctxerr>"}
    assert run(tmp_path, model, "--to", "rewrite") == 0
    learned = json.loads((tmp_path / "pipeline_state.json").read_text())["chars_per_token"]
    assert learned["value"] < 3.2 and learned["ctx"] == 16384
    assert dp.CHARS_PER_TOKEN == learned["value"]


def test_copied_example_names_are_renamed_everywhere(tmp_path, model):
    # an older run let the model name a function after the prompt's example
    write_export(tmp_path)
    assert run(tmp_path, model, "--to", "split") == 0
    prog = tmp_path / "rewrite" / "progress.json"
    data = json.loads(prog.read_text())
    data["functions"]["1000"]["name"] = "applyLowpassFilter839"
    prog.write_text(json.dumps(data))
    for f in [*(tmp_path / "rewrite" / ".rewritten").glob("*.cpp"),
              *(tmp_path / "build" / "funcs").glob("*.cpp")]:
        f.write_text(f.read_text().replace("addNumbers", "applyLowpassFilter839"))
    assert run(tmp_path, model, "--to", "split") == 0
    assert "applyLowpassFilter839" not in (tmp_path / "rewrite" / "rewritten.cpp").read_text()
    for f in (tmp_path / "build" / "funcs").glob("*.cpp"):
        assert "applyLowpassFilter839" not in f.read_text()
    e = json.loads(prog.read_text())["functions"]["1000"]
    assert e["name"] == "FUN_00001000" and e["renamed_from"] == "applyLowpassFilter839"
    assert len(manifest(tmp_path)) == 7
    assert any((tmp_path / "snapshots").glob("*rename-copied-names*"))


def test_console_shows_only_what_needs_attention(tmp_path, model, capsys):
    model.no_code = {"FUN_00001040"}
    write_export(tmp_path)
    assert run(tmp_path, model, "--to", "fix") == 0
    out = capsys.readouterr().out
    log = (tmp_path / "pipeline.log").read_text() + (tmp_path / "build" / "worklist.log").read_text()
    assert "fixer loop over" in log and "fixer loop over" not in out   # detail: file only
    assert "━━━━ Stage 5/10" in out and "fixer loop done" in out         # headers and results
    assert "couldn't handle:" in out and "no usable rewrite" in out
    assert "run(s)]" not in out
    # the same problem next run is flagged as repeating
    assert run(tmp_path, model, "--to", "fix") == 0
    assert "[also in the last 1 run(s)]" in capsys.readouterr().out
    # --verbose prints everything again
    assert run(tmp_path, model, "--to", "fix", "--verbose", "--redo", "fix") == 0
    assert "fixer loop over" in capsys.readouterr().out


def test_runaway_function_doesnt_swallow_the_rest(tmp_path, model):
    # an unclosed raw string: libclang reads on to the end of the file, so the
    # function "contains" every function after it
    model.rewrite_override["FUN_00001010"] = (
        'const char *sumThree() {\n    return R"(abc;\n}', "sumThree")
    write_export(tmp_path)
    assert run(tmp_path, model, "--to", "split") == 0
    assert len(manifest(tmp_path)) == 7
    report = (tmp_path / "build" / "split_report.txt").read_text()
    assert "ran past the end" in report and "raw string" in report


def test_done_without_a_draft_file_is_rewritten(tmp_path, model):
    write_export(tmp_path)
    assert run(tmp_path, model, "--to", "rewrite") == 0
    (tmp_path / "rewrite" / ".rewritten" / "1000.cpp").unlink()
    calls = model.calls["rewrite"]
    assert run(tmp_path, model, "--to", "rewrite") == 0
    assert model.calls["rewrite"] == calls + 1
    assert (tmp_path / "rewrite" / ".rewritten" / "1000.cpp").exists()


def test_compile_results_are_remembered(tmp_path, model):
    write_export(tmp_path)
    assert run(tmp_path, model, "--to", "split") == 0
    before = {r["name"]: r["compiles"] for r in manifest(tmp_path).values()}
    st = tmp_path / "build" / "build_state.json"
    data = json.loads(st.read_text())
    data["sweep_done"] = False                  # as if the sweep had been stopped
    st.write_text(json.dumps(data))
    assert run(tmp_path, model, "--to", "split") == 0
    log = (tmp_path / "build" / "worklist.log").read_text()
    assert "7 function(s) unchanged since their last compile" in log
    assert {r["name"]: r["compiles"] for r in manifest(tmp_path).values()} == before


def test_draft_defining_a_copied_name_is_renamed(tmp_path, model):
    write_export(tmp_path)
    assert run(tmp_path, model, "--to", "rewrite") == 0
    draft = tmp_path / "rewrite" / ".rewritten" / "1020.cpp"
    draft.write_text("unsigned int theFunctionName(unsigned int v) {\n    return v * 3;\n}\n")
    assert run(tmp_path, model, "--to", "split", "--redo", "rewrite", "--functions", "FUN_00001040") == 0
    cpp = (tmp_path / "rewrite" / "rewritten.cpp").read_text()
    assert "theFunctionName" not in cpp and "tripleValue(unsigned int v)" in cpp


def test_missing_header_doesnt_blind_libclang_and_lost_files_come_back(tmp_path, model):
    write_export(tmp_path)
    assert run(tmp_path, model, "--to", "rewrite") == 0
    cpp = tmp_path / "rewrite" / "rewritten.cpp"
    cpp.write_text("#include_next <no_such_header.h>\n" + cpp.read_text())   # gets past the include filter
    assert run(tmp_path, model, "--from", "split", "--to", "split") == 0
    log = (tmp_path / "build" / "worklist.log").read_text()
    assert "line 1: #include_next <no_such_header.h>" in log
    assert len(manifest(tmp_path)) == 7
    gone = tmp_path / "build" / next(iter(manifest(tmp_path).values()))["file"]
    gone.unlink()
    assert run(tmp_path, model, "--from", "fix", "--to", "fix") == 0
    assert gone.exists()
    assert "function file(s) were missing" in (tmp_path / "build" / "worklist.log").read_text()


def test_fix_lessons_learn_rules_and_block_repeats(tmp_path):
    cfg = dp.Config(input_file=tmp_path / "x.cpp", workdir=tmp_path)
    L = dp.FixLessons(cfg)
    kind = dp.error_kind("cannot initialize a variable of type 'int *' with an rvalue of type 'void *'")
    for a, b in (("p", "n"), ("buf", "len"), ("q", "size")):
        L.learned(kind, "msg", f"x\n    int *{a} = malloc({b});\ny",
                  f"x\n    int *{a} = (int *)malloc({b});\ny")
    rules = L.rules_for(kind)
    assert len(rules) == 2                                # the whole line, and the part that changed
    whole = next(r for _, r in rules if not r.get("span"))
    part = next(r for _, r in rules if r.get("span"))
    assert L.apply(whole, "  int *items = malloc(count * 4);") is None   # a different shape
    out = L.apply(whole, "  int *items = malloc(count);")
    assert out.startswith("  int") and "malloc(count)" in out and "(int*)" in out.replace(" ", "")
    out = L.apply(part, "  int *items = malloc(count * 4);")             # matches inside it
    assert "(int*)malloc(count*4)" in out.replace(" ", "")
    assert "before:" in L.prompt(kind, "funcs/a.cpp")      # examples for other functions
    L.failed("funcs/a.cpp", "a\nb", "a\nc")
    assert L.is_repeat("funcs/a.cpp", "a\nc") and not L.is_repeat("funcs/b.cpp", "a\nc")
    assert "did NOT work" in L.prompt(kind, "funcs/a.cpp")
    L.save()
    assert dp.FixLessons(cfg).rules_for(kind)              # kept between runs


def test_failed_edit_is_not_repeated(tmp_path, model):
    write_export(tmp_path)
    assert run(tmp_path, model, "--to", "fix") == 0
    notes = "".join(p.read_text() for p in (tmp_path / "build" / "improve" / "notes").glob("*.md"))
    assert "already failed" in notes                       # squareIt's bad edit came back
    lessons = json.loads((tmp_path / "build" / "fix_lessons.json").read_text())
    assert lessons["examples"] and lessons["tried"]


def test_extra_parenthesis_doesnt_unclose_functions():
    # an extra ')' used to cut a draft apart: its "return 0;" was moved to the top
    # and its closing brace dropped as a duplicate, so libclang swallowed every
    # function after it
    a = dp.mark_function(dp.clean_for_monolith(
        "int f(int x) {\n    if (x)) {\n        return 1;\n    }\n    return 0;\n}"), "FUN_1", "1")
    b = dp.mark_function(dp.clean_for_monolith(
        "struct S { int a; };\nint g(int y) {\n    if ((y) {\n        return 2;\n    }\n"
        "    return 0;\n}"), "FUN_2", "2")
    out = dp.combine([a, b])
    assert dp.brace_balance(out) == 0
    assert out.index("//@ghidra 1") < out.index("return 0;") < out.index("//@ghidra 2")
    assert out.startswith("struct S")


def test_narrowing_and_pointer_casts_dont_need_the_model(tmp_path, model):
    model.rewrite_override["FUN_00001050"] = (
        "struct Pair {\n    char first;\n    int second;\n};\n\n"
        "int pairSum(Pair *p) {\n    int n = (int)p;\n    Pair q{p->second, n};\n"
        "    return q.first + q.second;\n}", "pairSum")
    write_export(tmp_path)
    assert run(tmp_path, model, "--to", "fix") == 0
    r = by_name(tmp_path)["pairSum"]
    assert r["compiles"]
    assert "(int)(uintptr_t)p" in (tmp_path / "build" / r["file"]).read_text()


def test_diagnostics_report_has_everything(tmp_path, model, capsys):
    write_export(tmp_path)
    assert run(tmp_path, model, "--to", "recover") == 0
    out = capsys.readouterr().out
    m = re.search(r"DIAGNOSTICS: (.+\.md)", out)
    assert m
    rep = Path(m.group(1)).read_text()
    for part in ("## Run", "## What the script struggled with", "## Build status",
                 "build/split_report.txt", "Log of this run", "command:"):
        assert part in rep, part
    assert (tmp_path / "diagnostics" / "latest.md").read_text() == rep


def test_guessed_declarations_dont_conflict_with_the_real_one(tmp_path, model):
    # a caller's draft guesses its callee's parameters wrong: shared.h used to get
    # both declarations, and calls matched the wrong one
    model.rewrite_override["FUN_00001060"] = (
        "int addNumbers(long *values);\nint g_counter = 0;\n\n"
        "void bumpCounter() {\n    g_counter++;\n}", "bumpCounter")
    write_export(tmp_path)
    assert run(tmp_path, model, "--to", "split") == 0
    header = (tmp_path / "build" / "shared.h").read_text()
    assert len(re.findall(r"\baddNumbers\s*\(", header)) == 1
    assert "addNumbers(int" in header.replace(" ", "")
    assert by_name(tmp_path)["sumThree"]["compiles"]


def test_made_up_callee_names_are_matched_to_the_original(tmp_path, model):
    # the model calls "addTwo" where the original calls FUN_00001000 (addNumbers)
    model.rewrite_override["FUN_00001010"] = (
        "int addTwo(int x, int y);\n\nint sumThree(int a, int b, int c) {\n"
        "    return addTwo(addTwo(a, b), c);\n}", "sumThree")
    model.rewrite_override["FUN_00001060"] = (     # invents a main(): flagged, not trusted
        "int g_counter = 0;\n\nint main() {\n    g_counter++;\n    return 0;\n}\n\n"
        "void bumpCounter() {\n    g_counter++;\n}", "bumpCounter")
    write_export(tmp_path)
    assert run(tmp_path, model, "--to", "split") == 0
    cpp = (tmp_path / "rewrite" / "rewritten.cpp").read_text()
    assert "addNumbers(addNumbers(a, b), c)" in cpp and "addTwo(a" not in cpp
    assert by_name(tmp_path)["sumThree"]["compiles"]
    prog = json.loads((tmp_path / "rewrite" / "progress.json").read_text())["functions"]
    assert not any("calls functions" in w for w in prog["1010"].get("suspect", []))


def test_definitions_take_ghidra_parameter_types(tmp_path, model):
    # Ghidra says squareIt takes an int and bumpCounter nothing; the drafts take a
    # pointer and an extra parameter. The definitions take Ghidra's parameters and
    # convert on their first lines, so every caller agrees. A "Pair *" where Ghidra
    # says "int *" is kept: it says more.
    model.rewrite_override["FUN_00001040"] = (
        "int squareIt(long *n) {\n    return (int)(*n * *n);\n}", "squareIt")
    model.rewrite_override["FUN_00001060"] = (
        "int g_counter = 0;\n\nvoid bumpCounter(int amount) {\n    g_counter += amount;\n}",
        "bumpCounter")
    write_export(tmp_path)
    assert run(tmp_path, model, "--to", "split") == 0
    cpp = (tmp_path / "rewrite" / "rewritten.cpp").read_text()
    assert "int squareIt(int n_in)" in cpp and "long * n = (long *)n_in;" in cpp
    assert "void bumpCounter() {" in cpp and "int amount{};" in cpp
    assert "int pairSum(Pair *p)" in cpp
    assert by_name(tmp_path)["bumpCounter"]["compiles"]
    assert dp.ghidra_param_types("undefined8 FUN_1(undefined8 param_1,float f,Foo *p)\n{") == \
        ["uint64_t", "float", "void *"]


def test_mismatched_argument_is_cast_without_the_model(tmp_path):
    import shutil as sh
    cxx = sh.which("clang++") or sh.which("g++")
    cfg = dp.Config(input_file=tmp_path / "x.cpp", workdir=tmp_path, cxx=cxx)
    (tmp_path / "funcs").mkdir()
    (tmp_path / "shared.h").write_text("#include <cstdint>\nvoid takeAddress(uint64_t addr);\n")
    rel = "funcs/caller.cpp"
    src = '#include "shared.h"\n\nvoid caller(int *buf) {\n    takeAddress(buf);\n}\n'
    (tmp_path / rel).write_text(src)
    ok, err, _ = dp.compile_tu(cfg, rel)
    assert not ok
    rec = dp.FuncRecord(name="caller", mangled="caller", file=rel, start=0, end=0)
    assert dp._cast_args_fix(cfg, rec, rel, src, err)
    assert rec.compiles
    assert "takeAddress((uint64_t)(buf));" in (tmp_path / rel).read_text()


def test_ghidra_globals_and_library_calls_are_declared_once(tmp_path, model):
    # the drafts use a Ghidra global and a library function nothing declares; both
    # are in Ghidra's pseudocode, so they're declared once in shared.h. A name the
    # model made up isn't, and stays an error.
    write_export(tmp_path)
    exp = tmp_path / "ghidra" / "ghidra_export.json"
    data = json.loads(exp.read_text())
    data["pseudocode"]["1040"] = ("int FUN_00001040(int param_1)\n\n{\n  _mach_absolute_time();\n"
                                  "  return param_1 * param_1 + DAT_00424a80;\n}\n")
    exp.write_text(json.dumps(data))
    model.rewrite_override["FUN_00001040"] = (
        "int squareIt(int n) {\n    mach_absolute_time();\n    return n * n + DAT_00424a80;\n}",
        "squareIt")
    model.rewrite_override["FUN_00001030"] = (
        "int clampToZero(int x) {\n    madeUpHelper(x);\n    return x < 0 ? 0 : x;\n}", "clampToZero")
    assert run(tmp_path, model, "--to", "fix") == 0
    header = (tmp_path / "build" / "shared.h").read_text()
    assert 'extern "C" uint64_t mach_absolute_time(...);' in header
    assert "extern uint64_t DAT_00424a80;" in header and "madeUpHelper" not in header
    assert "uint64_t DAT_00424a80 = 0;" in (tmp_path / "build" / "globals.cpp").read_text()
    assert by_name(tmp_path)["squareIt"]["compiles"]
    log = (tmp_path / "build" / "worklist.log").read_text()
    assert "quick fixes (no model)" in log


def test_declaring_missing_names_never_breaks_shared_h(tmp_path, model):
    # errors saved by an earlier compile say 'code' is undeclared, but the headers
    # define it by now: declaring it again broke shared.h, and with it every compile
    write_export(tmp_path)
    assert run(tmp_path, model, "--to", "split") == 0
    cfg = dp.Config(input_file=tmp_path / "rewrite" / "rewritten.cpp", workdir=tmp_path / "build",
                    cxx=dp.COMPILER["cmd"] or shutil.which("clang++") or shutil.which("g++"))
    records = dp.load_manifest(cfg)
    r = next(iter(records.values()))
    r.compiles, r.last_error = False, ("x.cpp:1:1: error: use of undeclared identifier 'code'\n"
                                       "x.cpp:2:1: error: use of undeclared identifier 'undefined8'")
    dp.declare_missing(cfg, records)
    header = (tmp_path / "build" / "shared.h").read_text()
    assert "extern uint64_t code" not in header and "uint64_t undefined8" not in header
    assert dp._compile_header_human(cfg, "shared.h")[0]


def test_error_count_ignores_the_summary_line():
    # "1 error generated." used to count as an error, so 2 -> 1 looked like no progress
    assert dp.n_errors("a.cpp:1:2: error: x\n1 error generated.") == 1
    assert dp.n_errors("/p/fastpass 3/a.cpp:1:2: error: x\n/p/b.h:3:4: error: y\n"
                       "2 errors generated.") == 2
    assert dp.n_errors("") == 0


def test_quick_fixes_are_remembered_and_quarantined_functions_rebuilt_right_away(tmp_path, model):
    write_export(tmp_path)
    assert run(tmp_path, model, "--to", "fix") == 0
    log = (tmp_path / "build" / "worklist.log").read_text()
    # squareIt can't be fixed: it's rebuilt from pseudocode as soon as the fixer gives up
    assert re.search(r"squareIt -> quarantined, then re-derived", log)
    assert by_name(tmp_path)["squareIt"]["compiles"]
    st = tmp_path / "build" / "build_state.json"
    data = json.loads(st.read_text())
    data["sweep_done"] = False
    st.write_text(json.dumps(data))
    m = json.loads((tmp_path / "build" / "manifest.json").read_text())
    for r in m.values():                      # pretend some still fail (unchanged since)
        if r["quick_key"]:
            r["compiles"] = False
    (tmp_path / "build" / "manifest.json").write_text(json.dumps(m))


def test_faithful_rebuild_uses_the_programs_names_and_signatures(tmp_path, model):
    # a draft nothing can fix: it's rebuilt from Ghidra's pseudocode, which calls
    # FUN_00001000 - known to the program as addNumbers
    model.rewrite_override["FUN_00001010"] = (
        "int sumThree(int a, int b, int c) {\n    return addNumbers(a, b, c, wrongThing);\n}",
        "sumThree")
    write_export(tmp_path)
    assert run(tmp_path, model, "--to", "fix") == 0
    r = by_name(tmp_path)["sumThree"]
    assert r["compiles"] and r["recovery"] == "faithful-pseudocode"
    code = (tmp_path / "build" / r["file"]).read_text()
    assert "addNumbers(" in code and "FUN_00001000" not in code


def test_match_prototype_keeps_ghidras_types_inside():
    body = "long FUN_1(long param_1,int param_2) {\n  return param_1 + param_2;\n}"
    out = dp._match_prototype(body, "FUN_1", "Pair *FUN_1(Pair *, int);")
    assert out.startswith("Pair * FUN_1(Pair * param_1_in, int param_2) {")
    assert "long param_1 = (long)param_1_in;" in out and "return (Pair *)(param_1 + param_2);" in out
    out = dp._match_prototype("void FUN_2(long param_1) {\n  g(param_1);\n}", "FUN_2", "void FUN_2();")
    assert "void FUN_2() {" in out and "long param_1 = 0;" in out


def test_privacy_stage_sweeps_the_export_and_keeps_the_details_private(tmp_path, model):
    write_export(tmp_path)
    exp = tmp_path / "ghidra" / "ghidra_export.json"
    data = json.loads(exp.read_text())
    data["pseudocode"]["1060"] = ('void FUN_00001060(void)\n\n{\n  _printf("Visit https://acme-audio.example.com/'
                                  'support or mail jo@acmeaudio.com");\n'
                                  '  _CFBundleGetBundleWithIdentifier("com.AcmeAudio.GlitchBox");\n'
                                  '  _printf("/Users/jdoe/Library/x Copyright 2021 AcmeAudio Ltd");\n'
                                  '  DAT_00002000 = DAT_00002000 + 1;\n  return;\n}\n')
    exp.write_text(json.dumps(data))
    assert run(tmp_path, model, "--to", "privacy") == 0
    clean = exp.read_text()
    for gone in ("acme-audio.example.com", "jo@acmeaudio.com", "com.AcmeAudio.GlitchBox", "jdoe",
                 "AcmeAudio", "GlitchBox"):
        assert gone not in clean, gone
    assert "com.example.app1" in clean and "example.invalid" in clean
    original = (tmp_path / "ghidra" / "ghidra_export.original.json").read_text()
    assert "AcmeAudio" in original                              # kept, to sweep again from
    report = (tmp_path / "private" / "privacy_report.txt").read_text()
    assert "AcmeAudio" in report
    assert "AcmeAudio" in (tmp_path / "privacy_blocklist.txt").read_text()
    log = (tmp_path / "pipeline.log").read_text()
    assert "replacement(s)" in log and "AcmeAudio" not in log   # counts only, never the words
    # starting later with an export that hasn't been swept sweeps it first
    shutil.copyfile(tmp_path / "ghidra" / "ghidra_export.original.json", exp)
    assert run(tmp_path, model, "--from", "rewrite", "--to", "rewrite") == 0
    assert "AcmeAudio" not in exp.read_text()


C_PSEUDO = {
    **PSEUDO,
    # a thunk to a library function, and a function using Ghidra's notation, a data
    # type, a library call through the thunk and an int <-> pointer mix (fine in C)
    "1070": ("_strlen", "size_t _strlen(char *param_1)\n\n{\n  size_t sVar1;\n"
                        "  sVar1 = (*(code *)PTR__strlen_00004000)(param_1);\n  return sVar1;\n}\n"),
    "1080": ("FUN_00001080", "long FUN_00001080(Pair *param_1,long param_2)\n\n{\n  long lVar1;\n"
                             "  undefined8 uVar2;\n  uVar2 = CONCAT44(param_1->first,param_1->second);\n"
                             "  lVar1 = _strlen((char *)param_2);\n  *(long *)(param_2 + 8) = (long)param_1;\n"
                             "  return lVar1 + (long)uVar2;\n}\n"),
}


def test_c_mode_builds_ghidras_pseudocode_without_the_model(tmp_path, model):
    write_export(tmp_path, C_PSEUDO)
    assert run(tmp_path, model, "--lang", "c", "--to", "link") == 0
    src = (tmp_path / "rewrite" / "pseudocode.c").read_text()
    assert "_Static_assert(sizeof(Pair) == 8" in src
    assert "strlen((char *)param_2)" in src and "_strlen(" not in src    # the thunk is skipped
    m = json.loads((tmp_path / "build_c" / "manifest.json").read_text())
    names = {r["name"]: r for r in m.values()}
    assert "FUN_00001080" in names and names["FUN_00001080"]["compiles"]
    assert model.calls["rewrite"] == 0                                   # no model rewrite
    assert (tmp_path / "build" / "manifest.json").exists() is False     # the C++ build untouched
    log = (tmp_path / "pipeline.log").read_text()
    assert "C source from Ghidra's pseudocode" in log


def test_c_mode_embeds_the_programs_data_and_fixes_up_its_pointers(tmp_path, model):
    import base64
    import ctypes
    import struct
    pseudo = {**C_PSEUDO,
              "10a0": ("FUN_000010a0", "long FUN_000010a0(void)\n\n{\n  long lVar1;\n"
                                       "  lVar1 = (*(code *)PTR_FUN_00002008)(DAT_00002000,1);\n"
                                       "  return lVar1;\n}\n"),
              "10b0": ("FUN_000010b0", "char * FUN_000010b0(void)\n\n{\n  return s_AcmeAudio_00002010;\n}\n")}
    write_export(tmp_path, pseudo)
    (tmp_path / "privacy_blocklist.txt").write_text("AcmeAudio\n")
    blob = struct.pack("<qq", 41, 0x1000) + b"AcmeAudio Ltd\0\0\0"
    (tmp_path / "ghidra" / "ghidra_data.json").write_text(json.dumps({
        "version": 1, "image_base": "0",
        "blocks": [{"name": "__data", "start": "2000", "size": len(blob), "write": True,
                    "bytes": base64.b64encode(blob).decode()}],
        "symbols": [{"addr": "2000", "name": "DAT_00002000", "type": "long", "size": 8},
                    {"addr": "2008", "name": "PTR_FUN_00002008", "type": "pointer", "size": 8, "pointer": True},
                    {"addr": "2010", "name": "s_AcmeAudio_00002010", "type": "char[16]", "size": 16}],
        "refs": [{"from": "2008", "to": "1000", "kind": "function", "name": "FUN_00001000"}],
        "callees": {}}))
    assert run(tmp_path, model, "--lang", "c", "--to", "link") == 0
    lib = next((tmp_path / "build_c").glob("program.*"))
    so = ctypes.CDLL(str(lib))
    so.FUN_000010a0.restype = ctypes.c_long
    assert so.FUN_000010a0() == 42          # data read, and the pointer fixed up to addNumbers
    so.FUN_000010b0.restype = ctypes.c_char_p
    s = so.FUN_000010b0()
    assert b"AcmeAudio" not in s and s.startswith(b"Name1")     # swept, same length
    assert "AcmeAudio" not in (tmp_path / "ghidra" / "ghidra_data.json").read_text()


# ---- the test stage (macOS only for real; here its host is checked against
# stand-in Apple headers, and its steps run with a stand-in host)

STUB_CF = """// declarations only: lets the test host be syntax-checked away from a Mac
#include <stdint.h>
typedef int32_t OSStatus; typedef uint32_t OSType; typedef uint32_t UInt32; typedef uint8_t UInt8;
typedef double Float64; typedef unsigned char Boolean; typedef long CFIndex; typedef unsigned long CFTypeID;
typedef const struct __CFAllocator *CFAllocatorRef; typedef const struct __CFURL *CFURLRef;
typedef struct __CFBundle *CFBundleRef; typedef struct __CFError *CFErrorRef;
typedef const struct __CFString *CFStringRef; typedef const struct __CFDictionary *CFDictionaryRef;
typedef const void *CFTypeRef; typedef uint32_t CFStringEncoding;
#define kCFStringEncodingUTF8 0x08000100
#define CFSTR(s) ((CFStringRef)s)
#define noErr 0
CFURLRef CFURLCreateFromFileSystemRepresentation(CFAllocatorRef, const UInt8 *, CFIndex, Boolean);
CFBundleRef CFBundleCreate(CFAllocatorRef, CFURLRef);
Boolean CFBundleLoadExecutableAndReturnError(CFBundleRef, CFErrorRef *);
void *CFBundleGetFunctionPointerForName(CFBundleRef, CFStringRef);
CFStringRef CFErrorCopyDescription(CFErrorRef); CFDictionaryRef CFErrorCopyUserInfo(CFErrorRef);
const void *CFDictionaryGetValue(CFDictionaryRef, const void *);
CFTypeID CFGetTypeID(CFTypeRef); CFTypeID CFStringGetTypeID(void);
Boolean CFStringGetCString(CFStringRef, char *, CFIndex, CFStringEncoding);
CFStringRef CFStringCreateWithCString(CFAllocatorRef, const char *, CFStringEncoding);
void CFRelease(CFTypeRef);
"""

STUB_AT = """#include <CoreFoundation/CoreFoundation.h>
typedef struct { OSType componentType, componentSubType, componentManufacturer; UInt32 componentFlags, componentFlagsMask; } AudioComponentDescription;
typedef struct OpaqueAudioComponent *AudioComponent;
typedef struct ComponentInstanceRecord *AudioComponentInstance; typedef AudioComponentInstance AudioUnit;
typedef struct AudioComponentPlugInInterface AudioComponentPlugInInterface;
typedef AudioComponentPlugInInterface *(*AudioComponentFactoryFunction)(const AudioComponentDescription *);
typedef UInt32 AudioUnitPropertyID, AudioUnitScope, AudioUnitElement, AudioUnitParameterID, AudioUnitRenderActionFlags;
typedef float AudioUnitParameterValue;
typedef struct { Float64 mSampleRate; UInt32 mFormatID, mFormatFlags, mBytesPerPacket, mFramesPerPacket, mBytesPerFrame, mChannelsPerFrame, mBitsPerChannel, mReserved; } AudioStreamBasicDescription;
typedef struct { UInt32 mNumberChannels, mDataByteSize; void *mData; } AudioBuffer;
typedef struct { UInt32 mNumberBuffers; AudioBuffer mBuffers[1]; } AudioBufferList;
typedef struct { Float64 mSampleTime; uint64_t mHostTime; Float64 mRateScalar; uint64_t mWordClockTime; char smpte[24]; UInt32 mFlags, mReserved; } AudioTimeStamp;
typedef OSStatus (*AURenderCallback)(void *, AudioUnitRenderActionFlags *, const AudioTimeStamp *, UInt32, UInt32, AudioBufferList *);
typedef struct { AURenderCallback inputProc; void *inputProcRefCon; } AURenderCallbackStruct;
typedef OSStatus (*HostCallback_GetBeatAndTempo)(void *, Float64 *, Float64 *);
typedef struct { void *hostUserData; HostCallback_GetBeatAndTempo beatAndTempoProc; void *a, *b, *c; } HostCallbackInfo;
typedef struct { char name[52]; CFStringRef unitName; UInt32 clumpID; CFStringRef cfNameString; UInt32 unit; float minValue, maxValue, defaultValue; UInt32 flags; } AudioUnitParameterInfo;
enum { kAudioUnitErr_InvalidProperty = -10879, kAudioUnitErr_InvalidParameter = -10878, kAudioUnitErr_InvalidElement = -10877,
 kAudioUnitErr_NoConnection = -10876, kAudioUnitErr_FailedInitialization = -10875, kAudioUnitErr_TooManyFramesToProcess = -10874,
 kAudioUnitErr_InvalidFile = -10871, kAudioUnitErr_FormatNotSupported = -10868, kAudioUnitErr_Uninitialized = -10867,
 kAudioUnitErr_InvalidScope = -10866, kAudioUnitErr_PropertyNotWritable = -10865, kAudioUnitErr_CannotDoInCurrentContext = -10863,
 kAudioUnitErr_InvalidPropertyValue = -10851, kAudioUnitErr_PropertyNotInUse = -10850, kAudioUnitErr_Initialized = -10849,
 kAudioUnitErr_InvalidOfflineRender = -10848, kAudioUnitErr_Unauthorized = -10847, kAudioComponentErr_InstanceInvalidated = -66749 };
enum { kAudioUnitType_MusicDevice = 'aumu', kAudioUnitType_MusicEffect = 'aumf', kAudioUnitType_Generator = 'augn',
 kAudioFormatLinearPCM = 'lpcm', kAudioFormatFlagsNativeFloatPacked = 9, kAudioFormatFlagIsNonInterleaved = 32,
 kAudioUnitProperty_StreamFormat = 8, kAudioUnitProperty_MaximumFramesPerSlice = 14, kAudioUnitProperty_HostCallbacks = 27,
 kAudioUnitProperty_SetRenderCallback = 23, kAudioUnitProperty_ParameterList = 3, kAudioUnitProperty_ParameterInfo = 4,
 kAudioUnitScope_Global = 0, kAudioUnitScope_Input = 1, kAudioUnitScope_Output = 2, kAudioTimeStampSampleTimeValid = 1,
 kAudioUnitParameterFlag_HasCFNameString = 1 << 27, kAudioUnitParameterFlag_CFNameRelease = 1 << 4, kAudioUnitParameterFlag_IsWritable = 1 << 31 };
AudioComponent AudioComponentRegister(const AudioComponentDescription *, CFStringRef, UInt32, AudioComponentFactoryFunction);
OSStatus AudioComponentInstanceNew(AudioComponent, AudioComponentInstance *);
OSStatus AudioComponentInstanceDispose(AudioComponentInstance);
OSStatus AudioUnitSetProperty(AudioUnit, AudioUnitPropertyID, AudioUnitScope, AudioUnitElement, const void *, UInt32);
OSStatus AudioUnitGetProperty(AudioUnit, AudioUnitPropertyID, AudioUnitScope, AudioUnitElement, void *, UInt32 *);
OSStatus AudioUnitGetPropertyInfo(AudioUnit, AudioUnitPropertyID, AudioUnitScope, AudioUnitElement, UInt32 *, Boolean *);
OSStatus AudioUnitInitialize(AudioUnit); OSStatus AudioUnitUninitialize(AudioUnit);
OSStatus AudioUnitSetParameter(AudioUnit, AudioUnitParameterID, AudioUnitScope, AudioUnitElement, AudioUnitParameterValue, UInt32);
OSStatus AudioUnitRender(AudioUnit, AudioUnitRenderActionFlags *, const AudioTimeStamp *, UInt32, UInt32, AudioBufferList *);
OSStatus MusicDeviceMIDIEvent(AudioUnit, UInt32, UInt32, UInt32, UInt32);
"""


def test_au_test_host_compiles_against_apples_api(tmp_path):
    cc = shutil.which("clang") or shutil.which("gcc")
    if not cc:
        pytest.skip("no C compiler")
    import subprocess
    (tmp_path / "CoreFoundation").mkdir()
    (tmp_path / "AudioToolbox").mkdir()
    (tmp_path / "CoreFoundation" / "CoreFoundation.h").write_text(STUB_CF)
    (tmp_path / "AudioToolbox" / "AudioToolbox.h").write_text(STUB_AT)
    (tmp_path / "host.c").write_text(dp.AU_HOST_C)
    r = subprocess.run([cc, "-fsyntax-only", "-Wall", "-Wextra", "-Werror", "-Wno-multichar",
                        "-Wno-unused-result", "-D_GNU_SOURCE", f"-I{tmp_path}",
                        str(tmp_path / "host.c")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


FAKE_HOST = r"""
import json, os, signal, sys, math
from array import array
cmd, bundle, factory = sys.argv[1], sys.argv[2], sys.argv[3]
rebuilt = bundle.endswith("Rebuilt.component")
print("STEP load bundle " + bundle)
if rebuilt:
    import plistlib
    info = plistlib.load(open(os.path.join(bundle, "Contents", "Info.plist"), "rb"))
    assert info["CFBundleExecutable"] == "program", info
    assert os.path.exists(os.path.join(bundle, "Contents", "MacOS", "program"))
    assert factory == "Name1AUFactory", factory
print("STEP instantiate")
if cmd == "info":
    print("INFO " + json.dumps({"type": "aufx", "params": [
        {"id": 0, "name": "Gain", "min": 0, "max": 2, "default": 1, "writable": True}]}))
    sys.exit(0)
sig, secs, out = sys.argv[7], float(sys.argv[8]), sys.argv[9]
gain = 1.0
for a in sys.argv[10:]:
    gain = float(a.split("=")[1])
print("FORMAT channels=2")
print("STEP render " + sig)
if rebuilt and sig == "sweep" and gain == 0:
    print("CRASH signal=11 (SIGSEGV: bad memory access) address=0x8")
    print("CRASH stack:")
    print("2   program   0x0000000100001234 FUN_00001000 + 20")
    print("CRASH end")
    sys.stdout.flush()
    os.kill(os.getpid(), signal.SIGSEGV)
n = int(secs * 1000)
off = 0.5 if (rebuilt and sig == "noise" and gain == 2) else 0.0
array("f", [gain * math.sin(i / 10.0) + off for i in range(2 * n)]).tofile(open(out, "wb"))
print("OK")
"""


def test_test_stage_packages_runs_compares_and_explains(tmp_path, monkeypatch):
    import plistlib
    import subprocess
    from types import SimpleNamespace
    cc = shutil.which("clang") or shutil.which("gcc")
    if not cc:
        pytest.skip("no C compiler")
    P = dp.Paths(tmp_path / "proj")
    P.use_c()
    P.make()
    (P.root / "private").mkdir()
    (P.root / "private" / "privacy_map.json").write_text(json.dumps(
        {"name": {"Acme": "Name1"}, "bundle ID": {"com.acme.verb": "com.example.app1"}}))
    lib = P.build / ("program.dylib" if sys.platform == "darwin" else "program.so")
    (tmp_path / "f.c").write_text("void *Name1AUFactory(void *d) { return d; }\n")
    subprocess.run([cc, "-shared", "-fPIC", str(tmp_path / "f.c"), "-o", str(lib)], check=True)
    plugin = tmp_path / "Acme Verb.component"
    (plugin / "Contents" / "MacOS").mkdir(parents=True)
    (plugin / "Contents" / "Resources").mkdir()
    (plugin / "Contents" / "MacOS" / "Acme Verb").write_bytes(b"\0")
    with open(plugin / "Contents" / "Info.plist", "wb") as f:
        plistlib.dump({"CFBundleExecutable": "Acme Verb", "CFBundleIdentifier": "com.acme.verb",
                       "AudioComponents": [{"type": "aufx", "subtype": "verb", "manufacturer": "Acme",
                                            "name": "Acme: Verb", "factoryFunction": "AcmeAUFactory"}]}, f)
    fake = tmp_path / "fake_host.py"
    fake.write_text(FAKE_HOST)
    monkeypatch.setattr(dp, "_can_run_au_test", lambda: True)
    monkeypatch.setattr(dp, "_build_host", lambda P, arch: fake)
    monkeypatch.setattr(dp, "_archs", lambda p: [])
    monkeypatch.setattr(dp, "_host_argv", lambda host, arch: [sys.executable, str(host)])
    monkeypatch.setattr(dp, "_crash_report", lambda since: [])
    cfg = SimpleNamespace(workdir=P.build, manifest_path=P.build / "manifest.json")
    args = SimpleNamespace(plugin=str(plugin), test_tolerance=1e-4, keep_test_bundle=False)
    res = dp.run_test(P, cfg, args)
    rep = (P.build / "test" / "test_report.txt").read_text()
    assert res["ran"], rep
    # 4 settings x 4 signals; at the lowest gain the sweep crashes, at the highest
    # the noise differs
    assert res["cases"] == 16 and res["passed"] == 14, rep
    assert "rebuilt Name1AUFactory" in rep
    assert "crashed (SIGSEGV)" in rep and "FUN_00001000 + 20" in rep and "null pointer" in rep
    assert "all highest / noise: FAIL" in rep and "max difference 0.5" in rep
    assert sorted(p.name for p in (P.build / "test" / "listen").iterdir()) == [
        "all-highest-noise-original.wav", "all-highest-noise-rebuilt.wav"]
    assert not list((P.build / "test").glob("run-*"))       # the temporary bundle is gone
    assert "Acme" not in rep and "tmp_path" not in rep and "Original.component" in rep  # sent on: scrubbed
    # the original that won't load: said plainly, nothing compared
    (plugin / "Contents" / "Info.plist").write_bytes(b"not a plist")
    res = dp.run_test(P, cfg, args)
    assert not res["ran"] and "couldn't be read" in (P.build / "test" / "test_report.txt").read_text()


def test_test_stage_is_skipped_without_a_plugin_or_off_macos(tmp_path, monkeypatch):
    from types import SimpleNamespace
    P = dp.Paths(tmp_path)
    P.make()
    cfg = SimpleNamespace(workdir=P.build, manifest_path=P.build / "manifest.json")
    assert dp.run_test(P, cfg, SimpleNamespace(plugin=None))["skipped"] == "no --plugin"
    monkeypatch.setattr(dp, "_can_run_au_test", lambda: False)
    assert dp.run_test(P, cfg, SimpleNamespace(plugin="x.component"))["skipped"] == "not macOS"


def test_find_factory_follows_privacy_and_underscores():
    m = {"name": {"Acme": "Name1"}}
    assert dp._find_factory("AcmeFactory", {"_Name1Factory"}, m)[0] == "_Name1Factory"
    assert dp._find_factory("AcmeFactory", {"AcmeFactory"}, m)[0] == "AcmeFactory"
    assert dp._find_factory("AcmeFactory", {"other", "Thing_Factory"}, m)[0] == "Thing_Factory"
    name, why = dp._find_factory("AcmeFactory", {"other"}, m)
    assert name is None and "Name1Factory" in why


# ---- fixes learned from the model's edits: tried from the first success, also
# inside other lines, never changing what a line does; quarantined functions get them

def test_learned_fix_is_tried_from_its_first_success_and_inside_other_lines(tmp_path):
    cfg = dp.Config(input_file=tmp_path / "x.c", workdir=tmp_path)
    L = dp.FixLessons(cfg)
    kind = "cannot cast from type 'X' to pointer type 'X'"
    L.learned(kind, "msg", "  p = (float *)val;\n", "  p = (float *)(uintptr_t)val;\n", "f1")
    rules = L.rules_for(kind)
    assert rules and all(L.tier(r) == "candidate" for _, r in rules)
    span = next(r for _, r in rules if r.get("span"))
    # a different line, a different name: the part around the change still matches
    assert dp.FixLessons.apply(span, "    q = (char *)buf;") == "    q = (char*)(uintptr_t)buf;"
    assert dp.FixLessons.apply(span, "    return x + 1;") is None
    fp = L.fingerprint(kind)
    for rid, _ in rules:
        L.rule_result(rid, True)
        L.rule_result(rid, True)
    assert all(L.tier(r) == "proven" for _, r in L.rules_for(kind))
    assert L.fingerprint(kind) == fp                 # same rules: nothing new to retry
    rid = rules[0][0]
    for _ in range(12):
        L.rule_result(rid, False)
    assert L.tier(L.data["rules"][rid]) == "retired"
    L.write_readable(tmp_path / "learned_fixes.txt")
    text = (tmp_path / "learned_fixes.txt").read_text()
    assert "== proven" in text and "== retired: 1" in text


def test_learned_fixes_never_change_what_a_line_does():
    assert dp._keeps_meaning("x = (int *)p;", "x = (int *)(uintptr_t)p;")
    assert not dp._keeps_meaning("x = foo(a);", "x = 0;")              # a call dropped
    assert not dp._keeps_meaning("x = a + 4;", "x = a;")               # a number dropped
    assert not dp._keeps_meaning("x = y;", "(void)y;")                 # an assignment dropped
    assert not dp._keeps_meaning("x = y;", "// x = y;")                # commented out


def test_quarantined_functions_get_fixes_learned_after_them(tmp_path, monkeypatch):
    cfg = dp.Config(input_file=tmp_path / "x.c", workdir=tmp_path)
    (tmp_path / "funcs").mkdir()
    cfg.quarantine_dir.mkdir(parents=True)
    err = "funcs/f.c:3:5: error: cannot cast from type 'long' to pointer type 'float *'\n"
    recs = {}
    for n in ("good", "bad"):
        (tmp_path / "funcs" / f"{n}.c").write_text("// QUARANTINED stub\n")
        (cfg.quarantine_dir / f"{n}.c").write_text(f"ORIGINAL {n}\n")
        recs[n] = dp.FuncRecord(name=n, mangled=n, file=f"funcs/{n}.c", start=0, end=0,
                                quarantined=True, last_error=err.replace("f.c", f"{n}.c"))
    monkeypatch.setattr(dp, "_LESSONS", {})
    monkeypatch.setattr(dp, "save_manifest", lambda cfg, records: None)
    calls = []

    def fake_quick_fix(cfg, rec, cache):
        calls.append(rec.name)
        text = (cfg.workdir / rec.file).read_text()
        assert text.startswith("ORIGINAL")          # works on the original, not the stub
        if rec.name == "good":
            rec.compiles = True
            return True
        (cfg.workdir / rec.file).write_text("half-fixed\n")
        return False
    monkeypatch.setattr(dp, "quick_fix", fake_quick_fix)
    # nothing learned for this error yet: nothing to retry
    assert dp.retry_quarantined(cfg, recs, {}) == 0 and not calls
    L = dp.fix_lessons(cfg)
    L.learned(dp.error_kind("cannot cast from type 'long' to pointer type 'float *'"), "m",
              "p = (float *)v;", "p = (float *)(uintptr_t)v;", "elsewhere")
    assert dp.retry_quarantined(cfg, recs, {}) == 1
    assert not recs["good"].quarantined and recs["good"].compiles
    assert recs["bad"].quarantined and not recs["bad"].compiles
    assert (tmp_path / "funcs" / "bad.c").read_text() == "// QUARANTINED stub\n"   # put back
    # the same learned fixes again: not retried
    calls.clear()
    assert dp.retry_quarantined(cfg, recs, {}) == 0 and not calls


def test_link_fixes_functions_that_dont_compile_with_a_live_bar(tmp_path, model, capsys):
    write_export(tmp_path, C_PSEUDO)
    assert run(tmp_path, model, "--lang", "c", "--to", "link") == 0
    m = json.loads((tmp_path / "build_c" / "manifest.json").read_text())
    rec = next(r for r in m.values() if not r["quarantined"])
    path = tmp_path / "build_c" / rec["file"]
    path.write_text(path.read_text() + "\nint broken_here(void) { return undeclared_thing; }\n")
    capsys.readouterr()
    assert run(tmp_path, model, "--lang", "c", "--from", "link", "--to", "link", "--no-pseudo") == 0
    out = capsys.readouterr().out
    assert "1 file(s) didn't compile; the fixer works on them" in out
    assert "fixing functions that don't compile" in out                 # the bar
    assert re.search(rf"{re.escape(rec['name'])} -> (fixed|quarantined)", out)
    assert re.search(r"link round 1: \d fixed, \d quarantined; compiling again", out)


def test_fixes_that_undo_each_other_stop_and_the_model_still_gets_its_tries(tmp_path, monkeypatch):
    # from a real run: two learned fixes turned "(void *)f()" into "(long)f()" and
    # back, each swap used up an attempt, and the function was quarantined without
    # the model ever seeing it
    cfg = dp.Config(input_file=tmp_path / "x.c", workdir=tmp_path, max_model_attempts=2)
    (tmp_path / "funcs").mkdir()
    rel = "funcs/f.c"
    (tmp_path / rel).write_text("p = (void *)g();\n")
    rec = dp.FuncRecord(name="f", mangled="f", file=rel, start=0, end=0)

    def compile_tu(cfg, r):
        text = (tmp_path / r).read_text()
        if "fixed" in text:
            return True, "", []
        msg = ("operand of type 'void' where arithmetic or pointer type is required"
               if "(long)" in text else "assigning to 'void *' from incompatible type 'void'")
        return False, f"{tmp_path / r}:1:5: error: {msg}\n1 error generated.\n", []

    def flip(cfg, rec, rel, src, err, line, kind, lessons):
        text = src.replace("(void *)", "(long)") if "(void *)" in src else src.replace("(long)", "(void *)")
        (cfg.workdir / rel).write_text(text)
        return True
    asked = []

    def model(cfg, rec, src, err):
        asked.append(src)
        return "p = fixed();\n"
    monkeypatch.setattr(dp, "compile_tu", compile_tu)
    monkeypatch.setattr(dp, "_rule_fix", flip)
    monkeypatch.setattr(dp, "templated_fix", lambda cfg, rel, err: False)
    monkeypatch.setattr(dp, "compile_fix_edit", model)
    monkeypatch.setattr(dp, "_cast_args_fix", lambda *a: False)
    monkeypatch.setattr(dp, "header_implicated", lambda err: False)
    monkeypatch.setattr(dp, "_LESSONS", {})
    assert dp.repair_tu(cfg, rec, {}) is True
    assert len(asked) == 1 and rec.compiles                   # the model got it, and fixed it


# ---- C mode: what C can't say in Ghidra's pseudocode, rewritten once for every
# function (real cases from a run), checked by compiling and running the result

C_PASS_CASES = [
    ("FUN_00003c94", "void FUN_00003c94(long *param_1)", "{\n  FUN_00009999(param_1);\n  return;\n}"),
    ("FUN_00009999", "long FUN_00009999(long *param_1)", "{\n  return *param_1 + 1;\n}"),
    ("FUN_00003cb4", "void FUN_00003cb4(long *param_1)",
     "{\n  void *pvVar1;\n\n  pvVar1 = (void *)FUN_00003c94(param_1);\n  FUN_001da834(pvVar1);\n  return;\n}"),
    ("FUN_001da834", "void FUN_001da834(void *p)", "{\n  return;\n}"),
    ("FUN_0000cac4", "undefined1  [16] FUN_0000cac4(double *param_1,double *param_2)",
     "{\n  undefined1 auVar1 [16];\n\n  if (*param_2 <= *param_1) {\n    param_1 = param_2;\n  }\n"
     "  auVar1._8_8_ = 0;\n  auVar1._0_8_ = *param_1;\n  return auVar1;\n}"),
    ("FUN_00004574", "undefined1  [16] FUN_00004574(long param_1)",
     "{\n  undefined1 auVar1 [16];\n  auVar1._8_8_ = 0;\n  auVar1._0_8_ = (double)param_1 * 2.0;\n"
     "  return auVar1;\n}"),
    ("FUN_00004560", "int FUN_00004560(double param_1)", "{\n  return (int)param_1;\n}"),
    ("FUN_00003780", "int FUN_00003780(double param_1)",
     "{\n  int iVar1;\n  undefined1 auVar2 [16];\n\n  auVar2 = FUN_00004574((long)param_1);\n"
     "  iVar1 = FUN_00004560(param_1 + auVar2._0_8_ * 0.5);\n  return iVar1;\n}"),
    ("FUN_00005555", "uint FUN_00005555(undefined8 param_1)",
     "{\n  uint uVar1;\n  long lVar2;\n  lVar2 = param_1;\n  uVar1 = lVar2._4_4_;\n  return uVar1;\n}"),
    ("runtime_error_385dbc",
     "void __thiscall std::runtime_error::runtime_error_385dbc(runtime_error *this,string *param_1)",
     "{\n  FUN_001da834(this);\n  return;\n}"),
    ("CGColorSpace", "ID __objc_msgSend_stub objc_stub::CGColorSpace(undefined8 self,...)",
     "{\n  ID IVar1;\n  IVar1 = (ID)self;\n  return IVar1;\n}"),
    ("FUN_0000a02c", "void FUN_0000a02c(undefined8 *param_1)",
     "{\n  undefined1 local_68 [16];\n  local_68._0_8_ = *param_1;\n  local_68._8_8_ = 5;\n"
     "  FUN_00007777((undefined8 *)local_68,1);\n  return;\n}"),
    ("FUN_00007777", "void FUN_00007777(undefined8 *p, int n)", "{\n  return;\n}"),
    # a label before a call isn't a use of its result; x._0_4_ += 1; "a & x._0_4_" is an and
    ("FUN_00006666", "uint FUN_00006666(undefined8 param_1)",
     "{\n  undefined8 uVar1;\n  uint uVar2;\n  uVar1 = param_1;\n  uVar1._0_4_ += 1;\n"
     "  uVar2 = 0xff & uVar1._0_4_;\n  if (uVar2 == 0) goto LAB_1;\n  return uVar2;\nLAB_1:\n"
     "  FUN_001da834(0);\n  return 0;\n}"),
]


def test_c_mode_passes_make_ghidras_c_compile_and_keep_its_values(tmp_path):
    import subprocess
    cc = shutil.which("clang") or shutil.which("gcc")
    if not cc:
        pytest.skip("no C compiler")
    entries = [{"tag": "", "head": h, "body": b, "name": n} for n, h, b in C_PASS_CASES]
    known = set(re.findall(r"\btypedef\b[^;]*?\b([A-Za-z_]\w*)\s*;", dp.GHIDRA_INTRINS_H))
    res = dp.c_mode_passes(entries, known)
    heads = {e["name"]: e["head"] for e in entries}
    assert heads["runtime_error_385dbc"].startswith("void runtime_error_385dbc(")    # no std::, no __thiscall
    assert heads["CGColorSpace"].startswith("ID CGColorSpace(")
    assert heads["FUN_0000cac4"].startswith("gh16 ") and heads["FUN_00003c94"].startswith("uint64_t ")
    assert heads["FUN_001da834"].startswith("void ")          # its result is never used: left alone
    assert "typedef struct string string;" in res["opaque"] and "typedef uint64_t ID;" in res["opaque"]
    src = (dp.GHIDRA_INTRINS_H + "\n" + res["opaque"] + "\n"
           + "\n".join(e["head"] + ";" for e in entries) + "\n"
           + "\n".join(e["head"] + "\n" + e["body"] for e in entries) + r'''
#include <stdio.h>
int main(void) {
  double a = 3.5, b = 1.25;
  gh16 r = FUN_0000cac4(&a, &b);
  long x = 41;
  printf("%g %d %lld %u %u\n", r.d[0], FUN_00003780(10.0), (long long)FUN_00003c94(&x),
         FUN_00005555(0x1234567800000000ULL), FUN_00006666(0x100000005ULL));
  return 0;
}
''')
    (tmp_path / "t.c").write_text(src)
    r = subprocess.run([cc, "-x", "c", "-std=gnu11", "-w", *dp.C_LENIENT, str(tmp_path / "t.c"),
                        "-o", str(tmp_path / "t")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = subprocess.run([str(tmp_path / "t")], capture_output=True, text=True).stdout.split()
    # the double's bits kept; the caller reads the callee's double as a double
    # (10 + 20 * 0.5); the lost return value is the tail call's; the right 4 bytes
    assert out == ["1.25", "20", "42", str(0x12345678), "6"]


# ---- the idea loop: the model proposes fixes for a whole kind of error; each is
# tested on copies, repeats are caught and sent back, stuck groups are parked

def _idea_setup(tmp_path, monkeypatch, replies, n=10):
    cfg = dp.Config(input_file=tmp_path / "x.c", workdir=tmp_path, lang="c")
    cfg.fix_model_used = "test-model"
    (tmp_path / "funcs").mkdir()
    cfg.shared_h.write_text("// shared\n")
    recs = {}
    for i in range(n):
        rel = f"funcs/f{i}.c"
        (tmp_path / rel).write_text(f"long f{i}(long param_1) {{\n  long lVar{i} = param_1;\n"
                                    f"  return lVar{i}.hi + {i};\n}}\n")
        recs[f"f{i}"] = dp.FuncRecord(name=f"f{i}", mangled=f"f{i}", file=rel, start=0, end=0)
    for i in range(3):                               # these compile today
        rel = f"funcs/ok{i}.c"
        (tmp_path / rel).write_text(f"int ok{i}(void) {{ return {i}; }}\n")
        recs[f"ok{i}"] = dp.FuncRecord(name=f"ok{i}", mangled=f"ok{i}", file=rel, start=0, end=0,
                                       compiles=True)

    def compile_tu(cfg, rel):
        lines = (cfg.workdir / rel).read_text().split("\n")
        errs = [f"{cfg.workdir / rel}:{n}:3: error: member reference base type 'long' is not a structure or union"
                for n, l in enumerate(lines, 1) if ".hi" in l]
        return (not errs), "\n".join(errs) + ("\n1 error generated.\n" if errs else ""), []
    monkeypatch.setattr(dp, "compile_tu", compile_tu)
    monkeypatch.setattr(dp, "_LESSONS", {})
    monkeypatch.setattr(dp, "save_manifest", lambda cfg, records: None)
    asked = []

    class Client:
        def chat(self, model, messages, **kw):
            asked.append(messages[1]["content"])
            return replies[min(len(asked), len(replies)) - 1]
    cfg.client = Client()
    for r in recs.values():
        if not r.compiles:
            r.last_error = compile_tu(cfg, r.file)[1]
    return cfg, recs, asked


def test_idea_loop_retries_with_feedback_and_adopts_what_works(tmp_path, monkeypatch, capsys):
    replies = ["I think you should fix it.",                                     # unusable
               '{"type": "rewrite", "before": "NOPE(y)", "after": "OK(y)"}',     # matches nothing
               '{"type": "flag", "flag": "-Wno-error=foo"}',                    # 3rd: another kind
               '{"type": "rewrite", "before": "lVar0.hi", "after": "GH_GET(lVar0, 8, 8)"}']  # works
    cfg, recs, asked = _idea_setup(tmp_path, monkeypatch, replies)
    counts = dp.idea_round(cfg, recs, {})
    assert len(asked) == 4
    assert "wasn't one of the four JSON forms" in asked[1]
    assert "doesn't appear in the failing lines" in asked[2]
    assert "different KIND of idea" in asked[2] or "different KIND of idea" in asked[3]
    assert "was tested on copies" in asked[3]                      # the flag's result, fed back
    assert counts["adopted"] == 1 and counts["rescued"] == 10
    assert all(recs[f"f{i}"].compiles for i in range(10))
    assert "GH_GET(lVar3,8,8)" in (tmp_path / "funcs" / "f3.c").read_text().replace(" ", "")  # each its own names
    book = json.loads((tmp_path / "ideas.json").read_text())
    assert [i["result"] for i in book["ideas"]] == ["no effect", "rejected", "adopted"]
    text = (tmp_path / "ideas.txt").read_text()
    assert "[adopted]" in text and "[rejected]" in text
    assert "ideas for kinds of error many functions share" in capsys.readouterr().out   # the bar


def test_idea_loop_catches_repeats_and_parks_a_stuck_group(tmp_path, monkeypatch):
    same = '{"type": "rewrite", "before": "lVar0.hi", "after": "(lVar0).hi"}'      # changes nothing useful
    cfg, recs, asked = _idea_setup(tmp_path, monkeypatch, [same, same, same, same])
    counts = dp.idea_round(cfg, recs, {})
    assert counts["tested"] == 1 and counts["adopted"] == 0
    assert counts["repeats"] >= 2                                  # caught, not tested again
    assert any("the same as idea #1" in a for a in asked[1:])
    book = json.loads((tmp_path / "ideas.json").read_text())
    g = next(iter(book["groups"].values()))
    assert g["parked"] and g["until_run"] == 3          # sits out the next run
    # nothing changed: parked, the model isn't asked again
    asked.clear()
    assert dp.idea_round(cfg, recs, {})["parked"] == 1 and not asked


def test_header_ideas_must_not_break_what_compiles(tmp_path, monkeypatch):
    cfg, recs, asked = _idea_setup(tmp_path, monkeypatch, ['{"type": "typedef", "line": "#define hi lo"}',
                                                           '{"type": "typedef", "line": "typedef long hi_t;"}'])
    real = dp.compile_tu

    def compile_tu(cfg, rel):                        # the header idea "fixes" BAD but breaks ok1
        if "hi_t" in cfg.shared_h.read_text():
            if "ok1" in rel:
                return False, f"{cfg.workdir / rel}:1:1: error: broken\n", []
            return True, "", []
        return real(cfg, rel)
    monkeypatch.setattr(dp, "compile_tu", compile_tu)
    counts = dp.idea_round(cfg, recs, {})
    assert counts["adopted"] == 0
    assert "A macro may only define a NEW name" in asked[1]      # "hi" is used: refused, re-asked
    assert "hi_t" not in cfg.shared_h.read_text()                # put back after the test
    book = json.loads((tmp_path / "ideas.json").read_text())
    assert "compiling function(s) broke" in book["ideas"][0]["why_result"]


def test_ideas_run_twice_a_run_without_counting_two_runs(tmp_path, monkeypatch):
    same = '{"type": "rewrite", "before": "lVar0.hi", "after": "(lVar0).hi"}'
    cfg, recs, asked = _idea_setup(tmp_path, monkeypatch, [same] * 4)
    dp.idea_round(cfg, recs, {}, new_run=True, when="before the one-by-one fixes")
    asked.clear()
    # the round after the one-by-one fixes, same run, nothing changed: still parked
    assert dp.idea_round(cfg, recs, {}, new_run=False)["parked"] == 1 and not asked
    assert json.loads((tmp_path / "ideas.json").read_text())["run"] == 1



C_PASS_CASES_2 = [
    # a 16-byte variable given a plain 64-bit value
    ("FUN_0000a1d8", "uint64_t FUN_0000a1d8(long *p, long n)", "{\n  return (uint64_t)(*p + n);\n}"),
    ("FUN_000659a0", "long FUN_000659a0(long param_1)",
     "{\n  undefined1 auVar2 [16];\n  long lStack_40;\n  lStack_40 = param_1;\n"
     "  auVar2 = FUN_0000a1d8(&lStack_40,0x10);\n  return auVar2._0_8_;\n}"),
    # a piece inside a store's value; pieces of an array element
    ("FUN_0009083c", "uint FUN_0009083c(undefined8 *param_1)",
     "{\n  undefined1 local_b0 [16];\n  undefined1 local_68 [16];\n  undefined8 uStack_28;\n"
     "  undefined8 local_60 [2];\n  local_60[0] = 0x0000000700000009;\n  uStack_28 = 0x0000000500000003;\n"
     "  local_b0._8_4_ = 11;\n  local_68._8_4_ = local_b0._8_4_;\n  local_68._12_4_ = uStack_28._4_4_;\n"
     "  return local_68._8_4_ + local_68._12_4_ + local_60[0]._0_4_;\n}"),
    # a 16-byte value cast to a number, and passed as a 16-byte parameter
    ("FUN_00079e9c", "long FUN_00079e9c(long v)", "{\n  return v * 2;\n}"),
    ("FUN_0006a52c", "undefined8 FUN_0006a52c(undefined1 param_1 [16], double param_2)",
     "{\n  return param_1._0_8_ + (long)param_2;\n}"),
    ("FUN_000795e8", "long FUN_000795e8(long x)",
     "{\n  undefined1 local_50 [16];\n  local_50._0_8_ = x;\n  local_50._8_8_ = 0;\n"
     "  return FUN_00079e9c((long)local_50) + FUN_0006a52c(local_50, 1.0);\n}"),
    # a 128-bit number and 16 bytes of memory returned as a 16-byte value
    ("FUN_00065024", "undefined1  [16] FUN_00065024(void)", "{\n  return ZEXT816(0);\n}"),
    ("FUN_0007a35c", "undefined1  [16] FUN_0007a35c(long param_1)",
     "{\n  return *(undefined1 (*) [16])(param_1 + 0x18);\n}"),
    # a destructor; a name that's a type and a function; a switch on a pointer
    ("runtime_error_dtor", "void __thiscall std::runtime_error::~runtime_error_dtor(runtime_error *this)",
     "{\n  return;\n}"),
    ("bad_cast", "long bad_cast(bad_cast *this)", "{\n  return 3;\n}"),
    ("FUN_0013e3ec", "long FUN_0013e3ec(bad_cast *this)",
     "{\n  long uVar1;\n  uVar1 = bad_cast(this);\n  return uVar1;\n}"),
    ("FUN_0008fecc", "int FUN_0008fecc(long *plVar6)",
     "{\n  switch(plVar6) {\n  case (long *)0x0:\n    return 10;\n  case (long *)0x1:\n    return 11;\n  }\n"
     "  return 12;\n}"),
]


def test_c_mode_passes_second_round_cases_from_a_real_run(tmp_path):
    import subprocess
    cc = shutil.which("clang") or shutil.which("gcc")
    if not cc:
        pytest.skip("no C compiler")
    entries = [{"tag": "", "head": h, "body": b, "name": n} for n, h, b in C_PASS_CASES_2]
    known = set(re.findall(r"\btypedef\b[^;]*?\b([A-Za-z_]\w*)\s*;", dp.GHIDRA_INTRINS_H))
    res = dp.c_mode_passes(entries, known)
    heads = {e["name"]: e["head"] for e in entries}
    assert heads["runtime_error_dtor"].startswith("void runtime_error_dtor(")      # no ~
    assert "gh16 param_1" in heads["FUN_0006a52c"] and "struct bad_cast *this" in heads["bad_cast"]
    src = (dp.GHIDRA_INTRINS_H + "\n" + res["opaque"] + "\n"
           + "\n".join(e["head"] + ";" for e in entries) + "\n"
           + "\n".join(e["head"] + "\n" + e["body"] for e in entries) + r"""
#include <stdio.h>
int main(void) {
  unsigned char mem[0x30] = {0}; mem[0x18] = 0x2a;
  gh16 z = FUN_00065024(), r = FUN_0007a35c((long)mem);
  printf("%ld %u %ld %llu %u %ld %d\n", FUN_000659a0(5), FUN_0009083c(0), FUN_000795e8(4),
         (unsigned long long)(z.q[0] + z.q[1]), (unsigned)r.b[0], FUN_0013e3ec(0), FUN_0008fecc((long *)1));
  return 0;
}
""")
    (tmp_path / "t.c").write_text(src)
    r = subprocess.run([cc, "-x", "c", "-std=gnu11", "-w", *dp.C_LENIENT, str(tmp_path / "t.c"),
                        "-o", str(tmp_path / "t")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = subprocess.run([str(tmp_path / "t")], capture_output=True, text=True).stdout.split()
    assert out == ["21", "25", "13", "0", "42", "3", "11"]


def test_phantom_variables_only_when_the_function_doesnt_declare_them():
    src = "void f(void)\n{\n  undefined4 extraout_s0;\n  g(extraout_s0, unaff_x19);\n}\n"
    out = dp.deghidra_text(src)
    assert "uint64_t unaff_x19 = 0;" in out and "uint64_t extraout_s0" not in out


def test_data_the_code_calls_through_is_a_function_pointer(tmp_path):
    import base64
    P = dp.Paths(tmp_path)
    P.make()
    data = {"blocks": [{"name": "__data", "start": "2000", "size": 16, "bytes": base64.b64encode(bytes(16)).decode()}],
            "symbols": [{"addr": "2000", "name": "DAT_00002000", "type": "undefined8", "size": 8},
                        {"addr": "2008", "name": "DAT_00002008", "type": "undefined8", "size": 8}]}
    h, c, macros, _ = dp.data_sources(P, data, {}, {"DAT_00002000", "DAT_00002008"},
                                      frozenset({"DAT_00002000"}))
    assert "#define GD_DAT_00002000 (*(uint64_t (**)())(g_block_0 + 0x0))" in h
    assert "#define GD_DAT_00002008 (*(undefined8 *)(g_block_0 + 0x8))" in h      # a plain value as before


def test_c_mode_a_data_type_that_is_also_a_function_keeps_its_struct_tag(tmp_path, model):
    # like "struct stat" and stat(): Ghidra's type Pair, and a function called Pair
    pseudo = {**C_PSEUDO,
              "10c0": ("Pair", "long Pair(Pair *param_1)\n\n{\n  return (long)param_1->first;\n}\n"),
              "10d0": ("FUN_000010d0", "long FUN_000010d0(Pair *param_1)\n\n{\n  long lVar1;\n"
                                       "  lVar1 = Pair(param_1);\n  return lVar1;\n}\n")}
    write_export(tmp_path, pseudo)
    assert run(tmp_path, model, "--lang", "c", "--to", "link") == 0
    src = (tmp_path / "rewrite" / "pseudocode.c").read_text()
    assert "typedef struct Pair Pair;" not in src and "long Pair(struct Pair *param_1)" in src
    names = {r["name"]: r for r in json.loads((tmp_path / "build_c" / "manifest.json").read_text()).values()}
    assert names["Pair"]["compiles"] and names["FUN_000010d0"]["compiles"]


def test_many_object_files_are_linked_through_a_response_file(tmp_path):
    # 30,000 object paths are more than macOS allows on one command line
    import subprocess
    cc = shutil.which("clang") or shutil.which("gcc")
    if not cc:
        pytest.skip("no C compiler")
    d = tmp_path / "fast pass 3"                    # a space in the folder name, like a real one
    d.mkdir()
    objs = []
    for i in range(3):
        (d / f"f{i}.c").write_text(f"int f{i}(void) {{ return {i}; }}\n")
        subprocess.run([cc, "-c", "-fPIC", str(d / f"f{i}.c"), "-o", str(d / f"f{i}.o")], check=True)
        objs.append(str(d / f"f{i}.o"))
    assert dp.objects_arg(objs, d / "objs.rsp") == objs                  # few: on the command line
    args = dp.objects_arg(objs, d / "objs.rsp", limit=10)
    assert args == [f"@{d / 'objs.rsp'}"]
    out = d / "lib.so"
    r = subprocess.run([cc, "-shared", *args, "-o", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    syms = subprocess.run(["nm", "-g", str(out)], capture_output=True, text=True).stdout
    assert all(f"f{i}" in syms for i in range(3))
