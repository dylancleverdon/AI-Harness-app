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
    assert all(st["stages"][s]["done"] for s in dp.STAGES)
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
    assert run(tmp_path, model, "--to", "fix") == 0
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
    while time.time() < deadline and not (log.exists() and "Stage 4/8" in log.read_text()):
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
    assert "━━━━ Stage 4/8" in out and "fixer loop done" in out         # headers and results
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
    assert len(L.rules_for(kind)) == 1
    out = L.apply(L.rules_for(kind)[0][1], "  int *items = malloc(count * 4);")
    assert out is None                                    # a different shape: no match
    out = L.apply(L.rules_for(kind)[0][1], "  int *items = malloc(count);")
    assert out.startswith("  int") and "malloc(count)" in out and "(int*)" in out.replace(" ", "")
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
