#!/usr/bin/env python3
"""
decomp_pipeline.py - from a Ghidra project to readable C++ that compiles and links,
in one resumable local pipeline. (pseudo_to_cpp.py and DECOMP_FIXER.py, combined.)

Stages, in order:
  export    Ghidra's function list and pseudocode -> ghidra/ghidra_export.json
            (HTTP/MCP plugin, analyzeHeadless, or a script you run in Ghidra's GUI).
            The headless/GUI export also records Ghidra's data types and function
            signatures, for later use.
  rewrite   a local model rewrites each function as clean C++ and names the ones
            Ghidra only had a placeholder for -> rewrite/rewritten.cpp
  split     libclang splits that file into build/shared.h, globals.cpp and one file
            per function; de-ghidra cleanup; header gate; compile every function
  fix       dependency-ordered repair of the functions that don't compile:
            deterministic fixes, then the model, then quarantine
  recover   quarantined functions are rebuilt from their Ghidra pseudocode
  link      build the whole program, stub what's missing, report what's left

Usage:
  python3 decomp_pipeline.py --workdir PROJ                    everything, or carry on
  python3 decomp_pipeline.py --workdir PROJ --to rewrite       stop after the rewrite
  python3 decomp_pipeline.py --workdir PROJ --from fix         e.g. after loading a
                                                               bigger model
  python3 decomp_pipeline.py --workdir PROJ --project ~/G/App.gpr --ghidra-home ~/ghidra_11.3
                                                               export headless first

Running the same command again carries on where it stopped, in any stage. Ctrl+C
pauses. Each stage skips work that's already done.

Models: whatever model is loaded in LM Studio is used, checked again at the start of
each stage, so you can swap models between stages (--pause-between-stages waits for
you at each stage that uses the model). --rewrite-model / --fix-model / --model pick
one by name; --backend ollama uses Ollama instead.

Redoing work never deletes anything:
  --redo rewrite    rewrite every function again (--functions A B for just those).
                    Each new rewrite REPLACES the old one in place as it finishes;
                    until then the old one stays in rewritten.cpp.
  --redo-suspect    the same, for the functions flagged for a second look
  --redo export     fetch every function's pseudocode from Ghidra again, replacing
                    entries in place. Functions whose pseudocode changed are then
                    rewritten again automatically.
  --redo split      rebuild the build folder from the current rewrite: function files
  --redo fix        are overwritten with fresh copies (the model's earlier fixes are
                    replaced), then compiled and fixed again
  --redo recover    give the quarantined functions another recovery pass
  --redo link       relink from scratch (placeholders regenerated)
  Before a redo replaces anything, the current files are copied to
  PROJ/snapshots/<time>-<what>/ (--no-snapshot to skip). Nothing is ever removed from
  snapshots/; delete old ones yourself when you no longer need them.
  Functions whose upstream code changed (rewritten again) are refreshed in the build
  automatically; functions that didn't change keep the fixes they already have.

Folder layout (--workdir PROJ):
  REPORT.md, report.json   summary of every stage (the numbers to compare runs by)
  pipeline_state.json      which stages finished, with which model
  pipeline.log             one line per stage event
  ghidra/                  ghidra_export.json, callgraph.json, pseudocode/
  rewrite/                 rewritten.cpp, names.txt, function_index.json, progress.json
  build/                   shared.h, globals.cpp, funcs/, quarantine/, stubs.cpp,
                           manifest.json, worklist.log and the *_report.txt files
  snapshots/               copies taken before a redo replaced anything

Carrying on from the old scripts (files are copied, never moved):
  --adopt-rewrite DIR   a pseudo_to_cpp.py output folder (--out)
  --adopt-build DIR     a DECOMP_FIXER.py --workdir

Needs: LM Studio (or Ollama) with a model loaded; clang++ or g++; pip install libclang;
for the export, Ghidra with the MCP plugin, or a Ghidra install for --project.
"""

from __future__ import annotations

import argparse
import atexit
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

PIPELINE_VERSION = "2026-10-18.1"
STAGES = ["export", "rewrite", "split", "fix", "recover", "link"]
MODEL_STAGES = {"rewrite": "rewrite", "fix": "fix"}   # stage -> which model it uses


# ============================================================================
# Pipeline plumbing: folders, log, state, lock, snapshots
# ============================================================================

class Paths:
    def __init__(self, root: Path):
        self.root = root
        self.ghidra = root / "ghidra"
        self.rewrite = root / "rewrite"
        self.build = root / "build"
        self.snapshots = root / "snapshots"
        self.state = root / "pipeline_state.json"
        self.report_md = root / "REPORT.md"
        self.report_json = root / "report.json"
        self.log = root / "pipeline.log"
        self.lock = root / ".pipeline.lock"
        self.export = self.ghidra / "ghidra_export.json"
        self.callgraph = self.ghidra / "callgraph.json"
        self.pseudocode = self.ghidra / "pseudocode"
        self.rewritten = self.rewrite / "rewritten.cpp"
        self.rewritten_dir = self.rewrite / ".rewritten"
        self.progress = self.rewrite / "progress.json"
        self.index = self.rewrite / "function_index.json"
        self.names = self.rewrite / "names.txt"
        self.manifest = self.build / "manifest.json"
        self.no_snapshot = False

    def make(self):
        for d in (self.root, self.ghidra, self.pseudocode, self.rewrite,
                  self.rewritten_dir, self.build):
            d.mkdir(parents=True, exist_ok=True)


def plog(P: Paths, msg: str) -> None:
    """A pipeline-level line: printed and appended to pipeline.log."""
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        with open(P.log, "a") as f:
            f.write(line + "\n")
    except OSError:
        pass


def write_atomic(path: Path, text: str) -> None:
    """Write via a temporary file, so an interrupted write never leaves half a file."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text)
    tmp.replace(path)


def set_aside(path: Path, why: str) -> Path:
    """Keep an unreadable file under a new name instead of overwriting it."""
    dest = path.with_name(f"{path.name}.unreadable-{time.strftime('%Y%m%d-%H%M%S')}")
    path.replace(dest)
    print(f"WARNING: {path.name} couldn't be read ({why}); kept it as {dest.name} "
          f"and started a new one.", flush=True)
    return dest


def load_pstate(P: Paths) -> dict:
    try:
        st = json.loads(P.state.read_text())
    except Exception:
        st = {}
    st.setdefault("stages", {})
    return st


def mark_stage(P: Paths, stage: str, **info) -> None:
    st = load_pstate(P)
    entry = st["stages"].get(stage, {})
    entry.update(info, at=time.strftime("%Y-%m-%d %H:%M:%S"))
    st["stages"][stage] = entry
    st["version"] = PIPELINE_VERSION
    write_atomic(P.state, json.dumps(st, indent=2))


def snapshot(P: Paths, reason: str, items: list[Path]) -> Optional[Path]:
    """Copy files/folders into snapshots/<time>-<reason>/ before they get replaced."""
    if P.no_snapshot:
        return None
    items = [p for p in items if p.exists()]
    if not items:
        return None
    dest = P.snapshots / f"{time.strftime('%Y%m%d-%H%M%S')}-{reason}"
    n = 1
    while dest.exists():
        n += 1
        dest = P.snapshots / f"{time.strftime('%Y%m%d-%H%M%S')}-{reason}-{n}"
    for p in items:
        target = dest / p.relative_to(P.root)
        target.parent.mkdir(parents=True, exist_ok=True)
        if p.is_dir():
            shutil.copytree(p, target)
        else:
            shutil.copy2(p, target)
    plog(P, f"  snapshot of the current files before '{reason}': {dest}")
    return dest


def acquire_lock(P: Paths, force: bool) -> None:
    """One run per project folder at a time."""
    if P.lock.exists():
        alive = False
        try:
            pid = int(P.lock.read_text().split()[0])
            if pid != os.getpid():
                os.kill(pid, 0)
                alive = True
        except PermissionError:
            alive = True
        except (ProcessLookupError, ValueError, IndexError, OSError):
            alive = False
        if alive and not force:
            sys.exit(f"Another run is working in {P.root} (process {pid}). Stop it first, "
                     f"or pass --force if that's wrong.")
    P.lock.write_text(f"{os.getpid()} {time.time():.0f}\n")

    def release():
        try:
            if P.lock.read_text().split()[0] == str(os.getpid()):
                P.lock.unlink()
        except Exception:
            pass
    atexit.register(release)


# ============================================================================
# Model client (LM Studio or Ollama), shared by every stage
# ============================================================================

class ModelGate:
    """Limits how many requests go to the model at once. The limit can change while
    running (--auto-parallel)."""

    def __init__(self, limit):
        self.limit, self.active, self.peak = max(1, limit), 0, 0
        self.cv = threading.Condition()

    def acquire(self):
        with self.cv:
            while self.active >= self.limit:
                self.cv.wait()
            self.active += 1
            self.peak = max(self.peak, self.active)

    def release(self):
        with self.cv:
            self.active -= 1
            self.cv.notify_all()

    def set_limit(self, n):
        with self.cv:
            self.limit = max(1, n)
            self.peak = self.active
            self.cv.notify_all()


GATE = {"gate": None, "tuner": None}


class ModelError(Exception):
    pass


class ModelClient:
    """Talks to LM Studio's local server (OpenAI-style) or Ollama. Requests are
    streamed, so a long answer never trips a timeout while it's still arriving."""

    def __init__(self, backend: str, api: Optional[str] = None):
        self.kind = backend
        if backend == "lmstudio":
            base = (api or os.environ.get("OPENAI_BASE_URL") or "http://localhost:1234/v1")
            base = base.rstrip("/")
            if not base.endswith("/v1"):
                base += "/v1"
        else:
            base = (api or os.environ.get("OLLAMA_HOST") or "http://localhost:11434")
            if not base.startswith("http"):
                base = "http://" + base
            base = base.rstrip("/")
        self.base = base + "/"
        self.calls = 0

    @property
    def name(self) -> str:
        return "LM Studio" if self.kind == "lmstudio" else "Ollama"

    def _get(self, url: str, timeout=20):
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.load(r)

    def models(self) -> Optional[list[str]]:
        """Usable models, the loaded ones first. None if the server isn't reachable."""
        try:
            if self.kind == "lmstudio":
                root = self.base[:-len("v1/")]
                try:   # LM Studio's own API says which models are actually loaded
                    data = self._get(root + "api/v0/models").get("data", [])
                    loaded = [m["id"] for m in data if m.get("state") == "loaded"
                              and m.get("type") != "embeddings"]
                    if loaded:
                        return loaded
                except Exception:
                    pass
                ids = [m["id"] for m in self._get(self.base + "models").get("data", [])]
                return [i for i in ids if "embed" not in i.lower()]
            running = []
            try:
                running = [m["name"] for m in self._get(self.base + "api/ps").get("models", [])]
            except Exception:
                pass
            tags = [m["name"] for m in self._get(self.base + "api/tags").get("models", [])]
            return running + [t for t in tags if t not in running]
        except Exception:
            return None

    def resolve(self, wanted: Optional[str]) -> str:
        """The model to use: the one asked for if it's there, else the loaded one."""
        ids = self.models()
        if ids is None:
            raise ModelError(f"{self.name} isn't reachable at {self.base}. "
                             + ("In LM Studio, open the Developer tab, load a model and "
                                "switch the server on." if self.kind == "lmstudio" else
                                "Is the Ollama app running?"))
        if not ids:
            raise ModelError(f"{self.name} is running but has no model loaded. Load one, "
                             f"then run this again.")
        if not wanted:
            return ids[0]
        if wanted in ids:
            return wanted
        close = [i for i in ids if wanted.lower().replace(":", "-") in i.lower()]
        if close:
            return close[0]
        print(f"  model '{wanted}' isn't loaded in {self.name}; using '{ids[0]}' "
              f"(available: {', '.join(ids[:6])})", flush=True)
        return ids[0]

    def chat(self, model, messages, max_out=None, temperature=0.2, ctx=None,
             timeout=1800, fatal=True) -> Optional[str]:
        """The model's reply with any <think> block removed. On failure: exit with
        advice (fatal=True) or return None."""
        gate, tuner = GATE["gate"], GATE["tuner"]
        if gate:
            gate.acquire()
        sent = time.time()
        self.calls += 1
        try:
            if self.kind == "lmstudio":
                body = {"model": model, "messages": messages, "stream": True,
                        "temperature": temperature, "repeat_penalty": 1.1}
                if max_out:
                    body["max_tokens"] = max_out
                url = self.base + "chat/completions"
            else:
                opts = {"temperature": temperature, "repeat_penalty": 1.1}
                if ctx:
                    opts["num_ctx"] = ctx
                if max_out:
                    opts["num_predict"] = max_out   # stops a model stuck repeating itself
                body = {"model": model, "messages": messages, "stream": True,
                        "think": False, "options": opts}
                url = self.base + "api/chat"
            req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
            text, first_word = _read_stream(req, self.kind, timeout)
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:300]
            if fatal:
                sys.exit(f"\n{self.name} answered with an error: {detail}")
            return None
        except Exception as e:
            if fatal:
                sys.exit(f"\nCould not reach {self.name} at {self.base} ({e}). Check the "
                         f"server is on and the model is loaded.")
            return None
        finally:
            if gate:
                gate.release()
        if tuner:
            tuner.record(sent, sum(len(m["content"]) for m in messages), first_word, len(text))
        return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()


def _read_stream(req, kind, timeout=1800):
    """Reads a streamed reply. Returns (text, seconds until the first word)."""
    t0, first, parts = time.time(), None, []
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        for raw in resp:
            line = raw.decode(errors="replace").strip()
            if not line:
                continue
            if kind == "lmstudio":
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                j = json.loads(data)
                ch = (j.get("choices") or [{}])[0]
                piece = (ch.get("delta") or ch.get("message") or {}).get("content") or ""
            else:
                j = json.loads(line)
                if j.get("error"):
                    raise RuntimeError(j["error"])
                piece = (j.get("message") or {}).get("content") or ""
            if piece:
                if first is None:
                    first = time.time() - t0
                parts.append(piece)
            if kind == "ollama" and j.get("done"):
                break
    return "".join(parts), (first if first is not None else time.time() - t0)


CLIENT: dict = {"c": None}


def ask_model(model, messages, ctx, max_out=None, temperature=0.2):
    """The rewrite stage's model call (exits with advice if the server is gone)."""
    return CLIENT["c"].chat(model, messages, max_out, temperature, ctx)


# ============================================================================
# Compiler
# ============================================================================

COMPILER = {"cmd": None, "clang": True}


def find_compiler(choice):
    """Path of the C++ compiler to use (auto: clang++, else g++), or None."""
    if choice == "none":
        return None
    for name in (["clang++", "g++"] if choice == "auto" else [choice]):
        path = shutil.which(name) or (name if os.path.isfile(name) else None)
        if path:
            try:
                ver = subprocess.run([path, "--version"], capture_output=True, text=True,
                                     timeout=30).stdout
            except Exception:
                continue
            COMPILER["cmd"], COMPILER["clang"] = path, "clang" in ver.lower()
            return path
    return None


# ============================================================================
# Stage: export (Ghidra)
# ============================================================================

# ---------------------------------------------------------------- Ghidra

def ghidra_request(base, path, params=None):
    """Returns the reply text (also for error replies), or None if nothing answered."""
    url = base.rstrip("/") + "/" + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=180) as r:
            return r.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        try:
            return e.read().decode(errors="replace")
        except Exception:
            return None
    except Exception:
        return None


def _json(text):
    try:
        return json.loads(text) if text and text.lstrip().startswith("{") else None
    except Exception:
        return None


def _items(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in ("items", "functions", "results", "data"):
            if isinstance(data.get(k), list):
                return data[k]
    return []


def _longest_code(obj):
    if isinstance(obj, str):
        return obj if "{" in obj and len(obj) > 10 else ""
    best = ""
    vals = obj.values() if isinstance(obj, dict) else obj if isinstance(obj, list) else []
    for v in vals:
        c = _longest_code(v)
        if len(c) > len(best):
            best = c
    return best


FUNC_LINE = re.compile(r"^\s*(.+?)\s+(?:at|@)\s+(?:(\w+):)?(?:0x)?([0-9a-fA-F]+)\s*$")


class Ghidra:
    """Talks to either kind of Ghidra MCP plugin: the original one (plain text replies,
    /list_functions, /decompile_function) or JSON ones ({"success": ..., "data": ...})."""

    def __init__(self, base):
        self.base = base
        self.style = None
        self.decomp = None          # the JSON plugin's pseudocode command, once found
        self.notice = None          # a one-off message for the person running this
        self.probe_lock = threading.Lock()

    def functions(self):
        """[(name, address)] in program order, or exit with advice."""
        found = self._json_list() or self._text_list()
        if not found:
            sys.exit(
                f"Couldn't get the list of functions from Ghidra at {self.base}\n"
                "- Open the program in Ghidra's CodeBrowser and let the analysis finish.\n"
                "- Make sure the MCP plugin is ticked under File > Configure > Developer.\n"
                "- If its port isn't 8080, add --ghidra http://127.0.0.1:PORT/\n"
                f"Test it with:  curl \"{self.base.rstrip('/')}/functions\"")
        return sorted(set(found), key=lambda f: f[1])

    def _json_list(self):
        found, seen, offset, page, paging, last = [], set(), 0, 1, "offset", None
        for _ in range(100000):
            params = ({"offset": offset, "limit": 1000} if paging == "offset"
                      else {"page": page, "page_size": 1000, "limit": 1000})
            j = _json(ghidra_request(self.base, "functions", params))
            if not j or not j.get("success"):
                break
            last = j.get("data")
            batch, new = _items(last), 0
            for it in batch:
                if not isinstance(it, dict) or it.get("external") or it.get("is_external") \
                        or it.get("isExternal"):
                    continue
                name = it.get("name") or it.get("function") or ""
                a = str(it.get("address") or it.get("entry") or it.get("entry_point") or "")
                m = re.search(r"(?:0x)?([0-9a-fA-F]+)$", a)
                if name and m and not a.upper().startswith("EXTERNAL") \
                        and int(m.group(1), 16) not in seen:
                    seen.add(int(m.group(1), 16))
                    found.append((name, int(m.group(1), 16)))
                    new += 1
            if not batch:
                break
            if not new:
                if paging == "offset" and page == 1:
                    paging, page = "page", 2          # it ignored "offset"; try pages
                    continue
                break
            offset += len(batch)
            page += 1
            total = last.get("total") if isinstance(last, dict) else None
            if (isinstance(total, int) and len(found) >= total) or \
                    (isinstance(last, dict) and last.get("has_more") is False):
                break
        if found:
            self.style = "json"
            total = last.get("total") if isinstance(last, dict) else None
            if isinstance(total, int) and len(found) < total:
                print(f"WARNING: Ghidra says it has {total} functions but only "
                      f"{len(found)} could be listed. Only those will be rewritten.")
        return found

    def _text_list(self):
        text = ghidra_request(self.base, "list_functions")
        if not text or _json(text) is not None:
            return []
        found = []
        for line in text.splitlines():
            m = FUNC_LINE.match(line)
            if m and (m.group(2) or "").upper() != "EXTERNAL":
                found.append((m.group(1).strip(), int(m.group(3), 16)))
        if found:
            self.style = "text"
        return found

    def pseudocode(self, name, addr):
        if self.style == "json":
            return self._json_decompile(addr)
        text = ghidra_request(self.base, "decompile_function", {"address": hex(addr)})
        if text and "{" in text and _json(text) is None:
            return text.strip()
        return None

    def _json_decompile(self, addr):
        a = f"{addr:x}"

        def call(path, params):
            path = path.replace("{A}", a).replace("{0xA}", "0x" + a)
            params = {k: v.replace("{A}", a).replace("{0xA}", "0x" + a)
                      for k, v in params.items()}
            return _longest_code(_json(ghidra_request(self.base, path, params)) or {}) or None

        if self.decomp:
            return call(*self.decomp)
        with self.probe_lock:                 # only one thread works out the command
            if self.decomp:
                return call(*self.decomp)
            return self._probe(addr, a, call)

    def _probe(self, addr, a, call):
        tries = []
        for A in ("{A}", "{0xA}"):
            for key in ("address", "addr"):
                for path in ("decompile", "decompile_function", "function/decompile",
                             "functions/decompile", "decompiler", "decomp"):
                    tries.append((path, {key: A}))
            tries += [(f"functions/{A}/decompile", {}), (f"decompile/{A}", {}),
                      (f"function/{A}/decompile", {}), (f"functions/{A}", {"decompile": "true"})]
        for path, params in tries:
            code = call(path, params)
            if code:
                self.decomp = (path, params)
                self.notice = (f"(Your Ghidra plugin gives pseudocode at "
                               f"/{path.replace('{A}', '…').replace('{0xA}', '…')})")
                return code
        sys.exit("Your Ghidra plugin listed the functions, but none of the usual commands "
                 "for pseudocode worked. Send a screenshot of this to whoever is helping you:\n"
                 f"  curl \"{self.base.rstrip('/')}/decompile?address={a}\"")


# ---------------------------------------------------------------- Ghidra cache
# Everything this pipeline needs from Ghidra is written once to ghidra_export.json:
# the function list and each function's pseudocode (version 2 exports from the
# headless/GUI script also carry "signatures" {addr: prototype} and "datatypes",
# Ghidra's structs/unions/enums/typedefs). After that the pipeline reads the file
# and Ghidra can be closed. The recover stage reads the same file to rebuild
# quarantined functions straight from their pseudocode.

EXPORT_VERSION = 1      # what the HTTP plugin path writes (no types/signatures)


class GhidraCache:
    """Drop-in stand-in for Ghidra that serves functions() and pseudocode() from
    ghidra_export.json. A live Ghidra is used only to build the file (first run
    or --refresh-ghidra) and to fill the rare gap the export is missing."""

    def __init__(self, export_path: Path, live: "Ghidra | None"):
        self.path = export_path
        self.live = live
        self.notice = None
        self.style = getattr(live, "style", None)
        self._lock = threading.Lock()
        self._dirty = 0
        self._last_save = 0.0
        self.refresh: set = set()       # keys to fetch again even though cached
        self.data = {"version": EXPORT_VERSION, "ghidra": getattr(live, "base", None),
                     "functions": [], "pseudocode": {}}
        if export_path.exists():
            try:
                loaded = json.loads(export_path.read_text())
                if loaded.get("functions"):
                    self.data = loaded
                    self.data.setdefault("pseudocode", {})
            except Exception as e:
                set_aside(export_path, str(e))     # keep it rather than overwrite it

    # -- read interface (same shape as Ghidra) --------------------------------

    def functions(self):
        if self.data.get("functions"):
            return [(f["name"], int(f["addr"], 16) if isinstance(f["addr"], str)
                     else f["addr"]) for f in self.data["functions"]]
        if not self.live:
            sys.exit(f"No {self.path.name} and Ghidra isn't reachable. Open the program "
                     f"in Ghidra (with the MCP plugin) once so the export can be built, "
                     f"or point --out at the folder that has {self.path.name}.")
        funcs = self.live.functions()
        self.style = self.live.style
        self.data["functions"] = [{"name": n, "addr": f"{a:x}"} for n, a in funcs]
        self._save(force=True)
        return funcs

    def pseudocode(self, name, addr):
        key = f"{addr:x}"
        with self._lock:
            hit = self.data["pseudocode"].get(key)
            again = key in self.refresh
        if hit is not None and not (again and self.live):
            return hit or None
        if not self.live:
            return None
        code = self.live.pseudocode(name, addr)
        if getattr(self.live, "notice", None):
            self.notice = self.live.notice
            self.live.notice = None
        with self._lock:
            if code or not hit:          # a failed re-fetch keeps what was there
                self.data["pseudocode"][key] = code or ""
            self.refresh.discard(key)
            self._dirty += 1
        self._save()
        return code or hit or None

    # -- building the export --------------------------------------------------

    def _save(self, force=False):
        with self._lock:
            now = time.time()
            if not force and (self._dirty < 50 and now - self._last_save < 20):
                return
            tmp = self.path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(self.data))
            tmp.replace(self.path)
            self._dirty, self._last_save = 0, now

    def have_pseudocode(self, addr) -> bool:
        return bool(self.data["pseudocode"].get(f"{addr:x}"))

    def build_full_export(self, parallel=4, progress_print=print, refresh=False):
        """Fetch pseudocode for every function so the file is complete and Ghidra
        can be closed. Resumable: skips functions already in the cache. refresh:
        fetch every function again, replacing each entry as its new one arrives
        (the old entry stays until then, so stopping halfway loses nothing)."""
        if refresh and self.live:
            funcs = self.live.functions()           # the list may have changed too
            self.style = self.live.style
            with self._lock:
                self.data["functions"] = [{"name": n, "addr": f"{a:x}"} for n, a in funcs]
                self.refresh = {f"{a:x}" for _, a in funcs}
            self._save(force=True)
        elif refresh:
            progress_print("--redo export: Ghidra isn't reachable, so nothing was "
                           "fetched again; using the existing export.")
            return
        funcs = self.functions()
        missing = [(n, a) for n, a in funcs if not self.have_pseudocode(a)
                   or f"{a:x}" in self.refresh]
        if not missing:
            progress_print(f"Ghidra export already complete "
                           f"({len(funcs)} functions in {self.path.name}).")
            return
        if not self.live:
            progress_print(f"{len(missing)} function(s) missing from {self.path.name} "
                           f"and Ghidra isn't reachable — continuing with what's cached.")
            return
        progress_print(f"{'Refreshing' if refresh else 'Building'} {self.path.name}: fetching pseudocode for "
                       f"{len(missing)} function(s) from Ghidra (one-time; after this "
                       f"you can close Ghidra)...")
        done = [0]
        dlock = threading.Lock()

        def fetch(item):
            n, a = item
            self.pseudocode(n, a)
            with dlock:
                done[0] += 1
                if done[0] % 100 == 0 or done[0] == len(missing):
                    progress_print(f"  exported {done[0]}/{len(missing)}")

        try:
            with ThreadPoolExecutor(max_workers=max(1, parallel)) as pool:
                list(pool.map(fetch, missing))
        finally:
            self._save(force=True)
        got = sum(1 for _, a in funcs if self.have_pseudocode(a))
        progress_print(f"Export complete: {got}/{len(funcs)} functions have pseudocode "
                       f"in {self.path.name}. Ghidra is no longer needed for this program.")

    def write_callgraph(self, path: Path, name_for: "dict[str,str] | None" = None):
        """Call graph derived from the pseudocode, in the JSON edge format the fix
        stage reads (--callgraph) for exact dependency ordering.
        Keyed by final function names when name_for maps a Ghidra name to one."""
        funcs = self.functions()
        by_addr_name = {f"{a:x}": n for n, a in funcs}
        known = set(by_addr_name.values())
        name_for = name_for or {}

        def final(ghidra_name):
            return name_for.get(ghidra_name, ghidra_name)

        graph = {}
        call_re = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(")
        for n, a in funcs:
            code = self.data["pseudocode"].get(f"{a:x}") or ""
            callees = set()
            for m in call_re.findall(strip_comments(code)):
                if m in known and m != n:
                    callees.add(final(m))
            if callees:
                graph[final(n)] = sorted(callees)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(graph, indent=0))
        tmp.replace(path)
        return len(graph)



# ---------------------------------------------------------------- headless export
# The decompiler API only runs inside Ghidra's JVM, so "headless export" means
# launching Ghidra's analyzeHeadless with the embedded GhidraScript below. It
# writes the same ghidra_export.json (merging with any existing one), far faster
# than the one-at-a-time HTTP/MCP export. --emit-ghidra-script writes the script
# out for running by hand from Ghidra's GUI Script Manager instead.

GHIDRA_EXPORT_SCRIPT = r"""
// Ghidra export for decomp_pipeline.py (Java GhidraScript — runs natively on
// Ghidra 11/12, no Jython or PyGhidra needed). Decompiles every function and
// writes ghidra_export.json (format version 2: the function list, pseudocode,
// each function's signature and the program's data types). It MERGES with an
// existing export: functions that already have pseudocode are kept and skipped,
// so it resumes prior progress and is itself resumable (checkpoints every 500
// functions). With the second argument "refresh" every function is decompiled
// again, each entry replaced in place as its new version arrives.
//
// Run it headless (launched automatically by decomp_pipeline.py --project) or
// from the GUI Script Manager. Script arguments: OUTPUT FOLDER [refresh]; if no
// folder is given, DEFAULT_OUT below is used.
//
// @category Decomp
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.decompiler.DecompiledFunction;
import ghidra.program.model.data.Composite;
import ghidra.program.model.data.DataType;
import ghidra.program.model.data.DataTypeComponent;
import ghidra.program.model.data.DataTypeManager;
import ghidra.program.model.data.Structure;
import ghidra.program.model.data.TypeDef;
import ghidra.program.model.data.Union;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class GhidraExport extends GhidraScript {

    static final String DEFAULT_OUT = "";
    static final int DECOMP_TIMEOUT = 60;   // seconds per function
    static final int SAVE_EVERY = 500;

    @Override
    public void run() throws Exception {
        String[] a = getScriptArgs();
        String outDir = (a.length >= 1 && a[0].trim().length() > 0) ? a[0].trim() : DEFAULT_OUT;
        boolean refresh = a.length >= 2 && a[1].trim().equalsIgnoreCase("refresh");
        if (outDir.length() == 0) {
            outDir = askDirectory("Folder for ghidra_export.json", "Export here").getPath();
        }
        File dir = new File(outDir);
        if (!dir.exists()) dir.mkdirs();
        File out = new File(dir, "ghidra_export.json");

        LinkedHashMap<String, String> pseudo = new LinkedHashMap<String, String>();
        int had = loadExisting(out, pseudo);
        println("Export -> " + out.getPath());
        println("Already have pseudocode for " + had + " function(s); "
                + (refresh ? "each will be replaced by a fresh decompile." : "they will be skipped."));

        DecompInterface decomp = new DecompInterface();
        if (!decomp.openProgram(currentProgram)) {
            println("ERROR: could not open the decompiler for this program.");
            return;
        }
        FunctionManager fm = currentProgram.getFunctionManager();
        int total = fm.getFunctionCount();
        println("Program has " + total + " function(s). Decompiling the missing ones...");

        List<String[]> funcs = new ArrayList<String[]>();
        LinkedHashMap<String, String> sigs = new LinkedHashMap<String, String>();
        int done = 0, newly = 0;
        long t0 = System.currentTimeMillis();
        for (Function func : fm.getFunctions(true)) {
            if (monitor.isCancelled()) break;
            if (func.isExternal()) continue;
            long off = func.getEntryPoint().getOffset();
            String addr = Long.toHexString(off);
            funcs.add(new String[] { func.getName(), addr });
            try {
                sigs.put(addr, func.getPrototypeString(false, false));
            } catch (Exception e) {
                // no signature for this one; the pseudocode still has its header
            }
            done++;
            String have = pseudo.get(addr);
            if (!refresh && have != null && have.length() > 0) continue;   // resume: skip done
            String code = "";
            try {
                DecompileResults res = decomp.decompileFunction(func, DECOMP_TIMEOUT, monitor);
                if (res != null && res.decompileCompleted()) {
                    DecompiledFunction d = res.getDecompiledFunction();
                    if (d != null && d.getC() != null) code = d.getC();
                }
            } catch (Exception e) {
                println("  ! " + func.getName() + " @ " + addr + " failed: " + e);
            }
            if (code.length() > 0 || have == null) pseudo.put(addr, code);   // keep old on failure
            newly++;
            if (newly % SAVE_EVERY == 0) {
                write(out, pseudo, funcs, sigs, null);
                double rate = newly / Math.max((System.currentTimeMillis() - t0) / 1000.0, 0.001);
                println(String.format("  %d/%d  (+%d new, %.1f/s)", done, total, newly, rate));
            }
        }
        String types = "[]";
        try {
            types = dataTypesJson(currentProgram.getDataTypeManager());
        } catch (Exception e) {
            println("  (could not export data types: " + e + ")");
        }
        write(out, pseudo, funcs, sigs, types);
        int got = 0;
        for (String v : pseudo.values()) if (v != null && v.length() > 0) got++;
        println("Done. " + got + "/" + total + " functions have pseudocode in " + out.getPath());
        println("Ghidra is no longer needed for this program.");
    }

    // Minimal, dependency-free read of our own export: pull "<hex>":"<escaped>"
    // entries out of the "pseudocode" object so a rerun resumes. Tolerant of a
    // missing/short file (returns 0).
    private int loadExisting(File out, Map<String, String> pseudo) {
        if (!out.exists()) return 0;
        StringBuilder sb = new StringBuilder();
        try {
            BufferedReader r = new BufferedReader(
                new InputStreamReader(new FileInputStream(out), StandardCharsets.UTF_8));
            char[] buf = new char[1 << 16];
            int n;
            while ((n = r.read(buf)) > 0) sb.append(buf, 0, n);
            r.close();
        } catch (Exception e) {
            return 0;
        }
        String s = sb.toString();
        int p = s.indexOf("\"pseudocode\":{");
        if (p < 0) return 0;
        p = s.indexOf('{', p);
        if (p < 0) return 0;
        int i = p + 1, len = s.length(), had = 0;
        while (i < len) {
            while (i < len && s.charAt(i) != '"' && s.charAt(i) != '}') i++;
            if (i >= len || s.charAt(i) == '}') break;
            StringBuilder key = new StringBuilder();
            i = readString(s, i, key);
            while (i < len && s.charAt(i) != ':') i++;
            i++;
            while (i < len && Character.isWhitespace(s.charAt(i))) i++;
            StringBuilder val = new StringBuilder();
            if (i < len && s.charAt(i) == '"') i = readString(s, i, val);
            if (key.length() > 0) {
                pseudo.put(key.toString(), val.toString());
                if (val.length() > 0) had++;
            }
            while (i < len && s.charAt(i) != ',' && s.charAt(i) != '}') i++;
            if (i < len && s.charAt(i) == '}') break;
            i++;
        }
        return had;
    }

    // read a JSON string starting at s[i]=='"', append decoded chars to sb,
    // return index just past the closing quote.
    private int readString(String s, int i, StringBuilder sb) {
        i++;  // skip opening quote
        int len = s.length();
        while (i < len) {
            char c = s.charAt(i++);
            if (c == '"') break;
            if (c == '\\' && i < len) {
                char e = s.charAt(i++);
                switch (e) {
                    case 'n': sb.append('\n'); break;
                    case 'r': sb.append('\r'); break;
                    case 't': sb.append('\t'); break;
                    case 'b': sb.append('\b'); break;
                    case 'f': sb.append('\f'); break;
                    case 'u':
                        if (i + 4 <= len) {
                            sb.append((char) Integer.parseInt(s.substring(i, i + 4), 16));
                            i += 4;
                        }
                        break;
                    default: sb.append(e);
                }
            } else {
                sb.append(c);
            }
        }
        return i;
    }

    // Ghidra's own structs, unions, enums and typedefs, as a JSON array.
    private String dataTypesJson(DataTypeManager dtm) {
        StringBuilder b = new StringBuilder("[");
        boolean first = true;
        Iterator<DataType> it = dtm.getAllDataTypes();
        while (it.hasNext()) {
            DataType dt = it.next();
            String kind;
            StringBuilder body = new StringBuilder();
            if (dt instanceof Composite) {
                kind = (dt instanceof Union) ? "union" : "struct";
                Composite c = (Composite) dt;
                DataTypeComponent[] comps = (dt instanceof Structure)
                    ? ((Structure) dt).getDefinedComponents() : c.getComponents();
                body.append(",\"fields\":[");
                for (int i = 0; i < comps.length; i++) {
                    DataTypeComponent f = comps[i];
                    if (i > 0) body.append(",");
                    String fname = f.getFieldName();
                    if (fname == null) fname = "field_0x" + Integer.toHexString(f.getOffset());
                    body.append("{\"off\":").append(f.getOffset())
                        .append(",\"size\":").append(f.getLength())
                        .append(",\"name\":\"").append(esc(fname))
                        .append("\",\"type\":\"").append(esc(f.getDataType().getDisplayName()))
                        .append("\"}");
                }
                body.append("]");
            } else if (dt instanceof ghidra.program.model.data.Enum) {
                kind = "enum";
                ghidra.program.model.data.Enum en = (ghidra.program.model.data.Enum) dt;
                body.append(",\"values\":{");
                String[] names = en.getNames();
                for (int i = 0; i < names.length; i++) {
                    if (i > 0) body.append(",");
                    body.append("\"").append(esc(names[i])).append("\":")
                        .append(en.getValue(names[i]));
                }
                body.append("}");
            } else if (dt instanceof TypeDef) {
                kind = "typedef";
                body.append(",\"type\":\"")
                    .append(esc(((TypeDef) dt).getDataType().getDisplayName())).append("\"");
            } else {
                continue;
            }
            if (!first) b.append(",");
            first = false;
            b.append("{\"kind\":\"").append(kind)
             .append("\",\"name\":\"").append(esc(dt.getName()))
             .append("\",\"path\":\"").append(esc(dt.getCategoryPath().getPath()))
             .append("\",\"size\":").append(dt.getLength())
             .append(body).append("}");
        }
        return b.append("]").toString();
    }

    private void write(File out, Map<String, String> pseudo, List<String[]> funcs,
                       Map<String, String> sigs, String types) throws Exception {
        File tmp = new File(out.getParentFile(), out.getName() + ".tmp");
        Writer w = new BufferedWriter(
            new OutputStreamWriter(new FileOutputStream(tmp), StandardCharsets.UTF_8));
        w.write("{\"version\":2,\"ghidra\":\"headless-java\",\"functions\":[");
        boolean first = true;
        for (String[] fn : funcs) {
            if (!first) w.write(",");
            first = false;
            w.write("{\"name\":\"" + esc(fn[0]) + "\",\"addr\":\"" + fn[1] + "\"}");
        }
        w.write("],\"pseudocode\":{");
        first = true;
        for (Map.Entry<String, String> e : pseudo.entrySet()) {
            if (!first) w.write(",");
            first = false;
            w.write("\"" + e.getKey() + "\":\"" + esc(e.getValue()) + "\"");
        }
        w.write("},\"signatures\":{");
        first = true;
        for (Map.Entry<String, String> e : sigs.entrySet()) {
            if (!first) w.write(",");
            first = false;
            w.write("\"" + e.getKey() + "\":\"" + esc(e.getValue()) + "\"");
        }
        w.write("}");
        if (types != null) w.write(",\"datatypes\":" + types);
        w.write("}");
        w.close();
        Files.move(tmp.toPath(), out.toPath(),
            StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
    }

    private String esc(String s) {
        if (s == null) return "";
        StringBuilder b = new StringBuilder(s.length() + 16);
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            switch (c) {
                case '"': b.append("\\\""); break;
                case '\\': b.append("\\\\"); break;
                case '\n': b.append("\\n"); break;
                case '\r': b.append("\\r"); break;
                case '\t': b.append("\\t"); break;
                case '\b': b.append("\\b"); break;
                case '\f': b.append("\\f"); break;
                default:
                    if (c < 0x20) b.append(String.format("\\u%04x", (int) c));
                    else b.append(c);
            }
        }
        return b.toString();
    }
}
"""


def find_analyze_headless(ghidra_home):
    import glob
    names = ["analyzeHeadless.bat", "analyzeHeadless"] if os.name == "nt" else ["analyzeHeadless"]
    roots = []
    if ghidra_home:
        roots.append(ghidra_home)
    if os.environ.get("GHIDRA_INSTALL_DIR"):
        roots.append(os.environ["GHIDRA_INSTALL_DIR"])
    roots += ["/opt/homebrew/Caskroom/ghidra", "/Applications", os.path.expanduser("~"),
              "/opt", "/usr/share"]
    for root in roots:
        for nm in names:
            direct = os.path.join(root, "support", nm)
            if os.path.isfile(direct):
                return direct
            hits = glob.glob(os.path.join(root, "**", "support", nm), recursive=True)
            if hits:
                return hits[0]
    return None


def _project_dir_name(project):
    """Ghidra wants <projectDir> <projectName> (name without extension). Accept
    the .gpr file, the .rep data folder, a project dir, or a bare name."""
    p = Path(project).expanduser()
    # a Ghidra project is <name>.gpr + <name>.rep; both identify project <name>
    if p.suffix in (".gpr", ".rep"):
        return str(p.parent), p.stem
    if p.is_dir():
        gprs = list(p.glob("*.gpr"))
        if len(gprs) == 1:
            return str(p), gprs[0].stem        # a folder containing one project
        return str(p.parent), p.name
    return str(p.parent), p.name


def run_headless_export(P: Paths, args, refresh=False):
    """Launch Ghidra analyzeHeadless with the embedded export script. Returns True
    on success. Resumes automatically (the script merges with any existing
    ghidra_export.json); refresh decompiles everything again, in place."""
    ah = find_analyze_headless(args.ghidra_home)
    if not ah:
        sys.exit("Couldn't find Ghidra's analyzeHeadless. Pass --ghidra-home "
                 "/path/to/ghidra_<version> (the folder that contains support/).")
    if not args.project:
        sys.exit("The headless export needs --project /path/to/YourProject.gpr "
                 "(or the project folder).")
    proj_dir, proj_name = _project_dir_name(args.project)
    script_dir = P.ghidra / ".script"
    script_dir.mkdir(parents=True, exist_ok=True)
    (script_dir / "GhidraExport.java").write_text(GHIDRA_EXPORT_SCRIPT)
    # -readOnly: we only decompile and write an external JSON, never modify the
    # program, so headless shouldn't check out or save anything.
    cmd = [ah, proj_dir, proj_name, "-noanalysis", "-readOnly",
           "-scriptPath", str(script_dir),
           "-postScript", "GhidraExport.java", str(P.ghidra)] + (["refresh"] if refresh else [])
    if args.program:
        cmd[3:3] = ["-process", args.program]
    else:
        cmd[3:3] = ["-process"]        # every program in the project
    print("Launching Ghidra headless export:\n  " + " ".join(cmd) + "\n", flush=True)
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True)
    except Exception as e:
        sys.exit("Couldn't launch analyzeHeadless (%s)" % e)
    print("  (Ghidra is starting its JVM and opening the project — this is silent "
          "for a minute or so before the export begins)", flush=True)
    for line in proc.stdout:
        line = line.rstrip()
        if line:                       # stream everything so it's visibly working
            print("  " + line, flush=True)
    code = proc.wait()
    export_path = P.export
    if not export_path.exists():
        sys.exit("Ghidra headless export produced no %s (exit %d). Check the project/"
                 "program names and --ghidra-home, and the output above." % (export_path, code))
    return True


# ============================================================================
# Stage: rewrite (pseudocode -> readable C++)
# ============================================================================

# Names a model writes when it hasn't really chosen one
BAD_NAME = re.compile(r"(?i)^(the|some|my|a|new)?_?(function|func|method)(_?name)?\d*$|"
                      r"^(the|some|my)[A-Z_]\w*$|^placeholder\w*$|^fun_?[0-9a-f]+$|"
                      r"^unknown\w*$|^name\d*$")
PLACEHOLDER = re.compile(r"^(?:thunk_)?(?:FUN|SUB|LAB)_[0-9a-fA-F]+$")
CHARS_PER_TOKEN = 3.2      # rough size of a "token" (what the model's limit is counted in)
GHIDRA_HELPERS = re.compile(r"^(CONCAT\d+|SUB\d+|ZEXT\d+|SEXT\d+|CARRY\d*|SCARRY\d*|SBORROW\d*|"
                            r"NEON_\w+|POPCOUNT|LZCOUNT|SQRT|ROUND|TRUNC|ABS|"
                            r"_?_?(malloc|free|calloc|realloc|memcpy|memmove|memset|strlen|fwrite|"
                            r"printf|fprintf|sin|cos|sqrt|exp|log|pow|sincos_stret))$")

SYSTEM_PROMPT = """You turn Ghidra decompiler pseudocode into clean, readable C++.

You get ONE function. Rewrite it as the C++ a person would plausibly have written:
- Keep the behaviour exactly the same: same conditions, loops, calculations, calls and
  return values. Don't add features, error handling or logging that isn't there.
- Replace decompiler artifacts with normal C++: undefined4/undefined8 become real types
  (int, float, uint64_t, pointers, bool); CONCAT/SUB/ZEXT become ordinary expressions;
  things like *(float *)(param_1 + 0x18) become members of a struct or class you define,
  with sensible names (add the struct definition above the function).
- Give the parameters and local variables meaningful names.
- If the function has a placeholder name (like FUN_100003a20), give it a meaningful
  name in lowerCamelCase that says what it does. Otherwise keep its name.
- Calls to other functions: use the names you are given. Declare them (no body) if
  you need to.
- Write ONLY this one function. Never write bodies for other functions, not even
  small helpers: declare them instead.
- Ghidra helper notation is not real code: CONCAT44(a, b), SUB84(x, 0), ZEXT48(x),
  NEON_xxx(...) and the like describe bit or vector operations. Turn them into plain
  C++ (shifts, casts, ordinary float maths, or a simple loop over 4 floats); never
  declare or define functions with those names.
- _malloc, _free, _memcpy, _fwrite, ___sincos_stret etc. are standard library calls:
  use malloc, free, memcpy, fwrite, sinf/cosf.
- DAT_xxx / PTR_xxx are global variables: give them meaningful names if you can tell
  what they are.
- Rewrite, don't transcribe: replace uVar3/iVar7/param_1/local_28/DAT_xxx with names
  describing what they hold, and replace goto/labels with if/else or loops where
  possible. No decompiler-style names may be left in your code.
- No raw addresses or offsets: never leave hex addresses (like 0x100003a20) in names
  or values, and turn pointer-plus-offset access into struct members. Only keep casts
  the types really need.
- Remove names and strings that identify the original program: replace or drop product
  names, company names, copyright notices, version strings, file paths and URLs. String
  literals from the pseudocode should not appear unchanged in your code unless they are
  format specifiers, single characters, or standard C strings like "rb" or "\\n".
- Your code is compiled on its own, so it must compile as standard C++17: include the
  headers you use, define the structs and globals it uses, and declare (no body) the
  other functions it calls.
- Never add printing, logging, messages or text strings that aren't in the pseudocode.
{comments}
Reply with ONE ```cpp code block, then one final line with the name you chose, e.g.:
NAME: applyLowpassFilter"""

NO_COMMENTS = "- Do not write any comments in the code."
WITH_COMMENTS = "- Add short comments where the purpose of a step isn't obvious."


class AutoParallel:
    """Finds a good number of requests to run at once.

    The model app works on a set number of requests at a time and queues the rest. A
    queued request is easy to spot: its first word arrives far later than the size of
    its prompt explains. So:
      - a request that sat in the queue  -> one fewer at a time
      - no queueing for `every` seconds  -> one more at a time (if all slots were busy)
      - one more made the model slower overall -> step back and wait a while"""

    def __init__(self, gate, max_parallel, every, log):
        self.gate, self.maxp, self.every, self.log = gate, max_parallel, every, log
        self.lock = threading.Lock()
        self.rates = []                    # prompt characters per second until 1st word
        self.n = 0
        self.changed_at = time.time()
        self.queued = 0                    # queued requests since the last change
        self.chars = 0                     # characters written since the last change
        self.last_step, self.speed_before_up, self.hold_until = None, None, 0.0
        self.fails = {}                    # limit -> times it turned out too many
        self.stop = threading.Event()
        threading.Thread(target=self._run, daemon=True).start()

    def record(self, sent_at, prompt_chars, first_word, out_chars):
        with self.lock:
            self.n += 1
            rate = prompt_chars / max(first_word, 0.05)
            typical = sorted(self.rates)[int(len(self.rates) * 0.8)] \
                if len(self.rates) >= 5 else None
            self.rates = (self.rates + [rate])[-40:]
            if sent_at < self.changed_at:
                return                          # sent under the previous setting
            self.chars += out_chars
            if typical is None or self.n <= 3:  # first ones include loading the model
                return
            if first_word > 2.5 * prompt_chars / typical + 1.5:
                self.queued += 1
                if self.gate.limit > 1 and \
                        time.time() - self.changed_at >= min(30, self.every / 2):
                    self._too_many(self.gate.limit, "requests were waiting in the model's queue")

    def _too_many(self, limit, why):
        """`limit` at once was too many: step back, and wait before trying it again,
        longer each time it fails (15 min, 30, 1 hour at most, with --auto-every 5)."""
        k = self.fails[limit] = self.fails.get(limit, 0) + 1
        wait_for = min(3 * self.every * 2 ** (k - 1), max(3600, 3 * self.every))
        self.last_step, self.speed_before_up = "down", None
        self.hold_until = time.time() + wait_for
        self._set(limit - 1, f"{why}; trying {limit} again in {fmt_duration(wait_for)}")

    def _set(self, n, why):
        old = self.gate.limit
        self.gate.set_limit(n)
        self.changed_at, self.queued, self.chars = time.time(), 0, 0
        if n != old:
            self.log(f"  parallel {old} -> {n} ({why})")

    def _run(self):
        while not self.stop.wait(5):
            with self.lock:
                now = time.time()
                elapsed = now - self.changed_at
                if elapsed < self.every:
                    continue
                speed = self.chars / elapsed
                limit = self.gate.limit
                if self.last_step == "up" and self.speed_before_up \
                        and speed < 0.9 * self.speed_before_up:
                    self._too_many(limit, "one more at a time made it slower")
                elif self.queued == 0 and self.gate.peak >= limit and limit < self.maxp \
                        and now >= self.hold_until:
                    self.last_step, self.speed_before_up = "up", speed
                    self._set(limit + 1, f"no queue for {fmt_duration(elapsed)}")
                else:
                    self.last_step, self.speed_before_up = None, None
                    self._set(limit, "")        # start a fresh measuring window


def _func_name(item):
    head = item.split("{", 1)[0]
    m = re.search(r"([A-Za-z_~][\w:~]*)\s*\([^()]*(\([^()]*\)[^()]*)*\)\s*(const\s*)?"
                  r"(noexcept\s*)?(override\s*)?$", head.strip())
    return m.group(1).split("::")[-1] if m else None


def _is_statement(line):
    """True for a line that is code from inside a function, not a declaration."""
    if re.match(r"(if|for|while|do|switch|return|goto|break|continue|else)\b", line) or \
            re.match(r"\w+:\s*$", line) or line.startswith(("*", "(", "++", "--")):
        return True
    flat = line
    while re.search(r"\([^()]*\)", flat):           # ignore '=' inside (...), e.g. default args
        flat = re.sub(r"\([^()]*\)", "", flat)
    m = re.search(r"(?<![=!<>+\-*/%&|^])([-+*/%&|^]|<<|>>)?=(?!=)", flat)
    if not m:
        return False
    lhs = flat[:m.start()].strip()
    # a declaration has a type and a name ("float gain = 1"); a statement assigns to
    # an existing variable or memory ("x = ...", "p->f = ...", "*(int *)(p + 4) = ...")
    return bool(re.search(r"->|\.|\(|\+", lhs)) or bool(m.group(1)) or \
        re.fullmatch(r"[A-Za-z_]\w*(\[[^\]]*\])?", lhs) is not None


def brace_balance(text):
    """Opening minus closing braces, ignoring string and character literals."""
    n, i, L = 0, 0, len(text)
    while i < L:
        ch = text[i]
        if ch in "\"'":
            j = i + 1
            while j < L and text[j] != ch and text[j] != "\n":
                j += 2 if text[j] == "\\" else 1
            i = j + 1
            continue
        n += 1 if ch == "{" else -1 if ch == "}" else 0
        i += 1
    return n


def invented_strings(code, pseudo):
    """Text strings in the rewrite that aren't anywhere in Ghidra's pseudocode: almost
    always printing or messages the model made up."""
    lit = re.compile(r'"((?:[^"\\\n]|\\.)*)"')
    have = set(lit.findall(pseudo))
    body = "\n".join(l for l in code.splitlines() if not l.lstrip().startswith("#"))
    return [x for x in lit.findall(body) if x.strip() and x not in have]


# Strings short enough or generic enough to keep (format specifiers, modes, single chars)
_GENERIC_STR = re.compile(
    r"^[\s%\-+#0-9.*lhLqjzt]*[diouxXeEfFgGaAcspn%]\s*$"   # printf format
    r"|^\\[nrt0\\]$"                                         # escaped char
    r"|^.{0,2}$"                                             # 1-2 chars (rb, w, \n, etc.)
)


def surviving_strings(code, pseudo):
    """String literals from the pseudocode that survived into the rewrite unchanged.
    These may identify the original program (product names, paths, versions, etc.)."""
    lit = re.compile(r'"((?:[^"\\\n]|\\.)*)"')
    orig = set(lit.findall(pseudo))
    body = "\n".join(l for l in code.splitlines() if not l.lstrip().startswith("#"))
    found = set(lit.findall(body))
    return sorted(s for s in orig & found if not _GENERIC_STR.match(s))


_FORMAT_STR = re.compile(r'%[-+#0-9.*lhLqjzt]*[diouxXeEfFgGaAcspn]')
_IDENTIFYING = re.compile(r'[A-Za-z]{4,}|[/\\][A-Za-z0-9._]|\b\d+\.\d+\b')


def strip_identifying(code):
    """Blank string literals that look like they identify the original program
    (product names, paths, version numbers), while keeping generic ones: short
    strings, modes like "rb", and printf format strings (even with escapes)."""
    lit = re.compile(r'"((?:[^"\\\n]|\\.)*)"')

    def repl(m):
        s = m.group(1)
        if _GENERIC_STR.match(s) or _FORMAT_STR.search(s):
            return m.group(0)                     # generic or a format string: keep
        return '""' if _IDENTIFYING.search(s) else m.group(0)

    return lit.sub(repl, code)


def faithful_from_pseudo(shown):
    """A faithful, deterministic C++ version of a function straight from its
    Ghidra pseudocode: type cleanup, no identifying strings, no model. Used only
    when the model couldn't produce a compiling rewrite — the honest raw version
    is better for the downstream fixer (which has the ghidra intrinsics) to
    recover than a half-broken model attempt."""
    return strip_identifying(tidy_tiny(shown))


# Ghidra's names for parameters, locals and globals. FUN_ isn't here: calls to functions
# that haven't been rewritten yet keep it until they get their own name.
LEFTOVER_NAMES = re.compile(r"\b(param_\d+|local_[0-9a-fA-F]+|[a-z]{1,3}Var\d+|"
                            r"(?:DAT|PTR|LAB)_[0-9a-fA-F]+|in_\w+|extraout_\w+|unaff_\w+)\b")
# An address inside a macOS program (they start at 0x100000000)
RAW_ADDRESS = re.compile(r"\b0x0*1000[0-9a-fA-F]{5}\b")


def leftover_names(code):
    return sorted(set(LEFTOVER_NAMES.findall(strip_comments(code))))


def suspect_reasons(code, pseudo, name, check_names=True):
    why = []
    if invented_strings(code, pseudo or ""):
        why.append("invented text/printing")
    if name and BAD_NAME.match(name):
        why.append("no real name")
    if brace_balance(code) != 0:
        why.append("cut off")
    if check_names and leftover_names(code):
        why.append("decompiler names left")
    if check_names and RAW_ADDRESS.search(strip_comments(code)):
        why.append("raw addresses left")
    if check_names and surviving_strings(code, pseudo or ""):
        why.append("identifying strings left")
    return why



# ---------------------------------------------------------------- standalone compile check

PRELUDE = ("#include <cstdint>\n#include <cstddef>\n#include <cstdlib>\n#include <cstring>\n"
           "#include <cmath>\n#include <cstdio>\n")


def compile_errors(code):
    """None if the code compiles on its own (syntax and types, no linking), else the
    compiler's error messages. Line numbers match the code as given."""
    limit = "-ferror-limit=10" if COMPILER["clang"] else "-fmax-errors=10"
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "function.cpp")
        with open(src, "w") as f:
            f.write(PRELUDE + '#line 1 "function.cpp"\n' + code + "\n")
        try:
            r = subprocess.run([COMPILER["cmd"], "-std=c++17", "-fsyntax-only", "-w", limit,
                                "-x", "c++", src], capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            return "the compiler gave up (took over 2 minutes)"
    if r.returncode == 0:
        return None
    err = (r.stderr or r.stdout).replace(src, "function.cpp").strip()
    if len(err) > 3000:
        err = err[:3000].rsplit("\n", 1)[0] + "\n..."
    return err or "the compiler failed without saying why"


def n_errors(err):
    return len(re.findall(r"\berror\b", err)) if err else 0


# ---------------------------------------------------------------- incremental fix
# Instead of regenerating a whole function when it won't compile (a small model
# drifts and guts it), fix it the way a person would: understand the goal once,
# then for each compile error read the exact line the compiler flags, diagnose
# it, plan the minimal change, and edit JUST that line. Recompile and repeat. A
# no-progress guard stops the loop as soon as an edit stops moving the error.

FIX_GOAL_SYS = ("In 1-2 sentences, state what this function does: its inputs, what "
                "it computes, and what it returns. Describe behaviour only; output no code.")
FIX_DIAG_SYS = ("A C++ compiler reported an error on one line of a function. In ONE "
                "sentence say what is wrong with that line (syntax or types). Do not "
                "propose a fix yet and output no code.")
FIX_PLAN_SYS = ("Choose the smallest change that fixes a C++ compile error WITHOUT "
                "changing what the code does. Given the goal, the diagnosis and the "
                "failing line, say in ONE sentence what the corrected line should be. "
                "Output no code.")
FIX_EDIT_SYS = ("Output the corrected replacement for the given line(s) of C++ and "
                "nothing else. Change as little as possible; keep the same behaviour; do "
                "not rename the function; do not add or remove braces that would "
                "unbalance the surrounding code. Return ONLY the replacement line(s) in "
                "one ```cpp code block.")


def _first_err_line(err):
    m = re.search(r'function\.cpp:(\d+):(\d+):\s*(?:fatal\s+)?error:\s*(.*)', err)
    return (int(m.group(1)), int(m.group(2)), m.group(3).strip()) if m else None


def _edit_span(lines, ln):
    """0-based [lo, hi) to edit for an error on 1-based line `ln`: that line plus
    any continuation lines until its brackets balance (a multi-line statement)."""
    lo = ln - 1
    if lo < 0 or lo >= len(lines):
        return None
    hi = ln
    while hi < min(len(lines), lo + 5):
        seg = "\n".join(lines[lo:hi])
        if seg.count("{") == seg.count("}") and seg.count("(") >= seg.count(")"):
            break
        hi += 1
    return lo, hi


def incremental_fix(args, code, pseudo, name, prog, key):
    """Drive a standalone function to compile by minimal, line-anchored edits.
    Returns (code, compiled_bool, n_edits). Makes no model call when the code
    already compiles."""
    goal = None
    seen = {}
    edits = 0
    max_iters = max(4, args.compile_retries * 3)
    for _ in range(max_iters):
        errors = compile_errors(code)
        if errors is None:
            return code, True, edits
        loc = _first_err_line(errors)
        if not loc:
            break
        ln, col, emsg = loc
        lines = code.split("\n")
        span = _edit_span(lines, ln)
        if not span:
            break
        lo, hi = span
        target = "\n".join(lines[lo:hi])
        sig = (ln, emsg[:60])
        seen[sig] = seen.get(sig, 0) + 1
        if seen[sig] >= 2:          # this exact error survived an edit -> stop
            break
        if args.fix_steps == "chain":
            if goal is None:
                goal = ask_model(args.model_in_use, [{"role": "system", "content": FIX_GOAL_SYS},
                    {"role": "user", "content": f"Function {name}:\n```c\n{pseudo[:6000]}\n```"}],
                    args.ctx, 160)
            diagnosis = ask_model(args.model_in_use, [{"role": "system", "content": FIX_DIAG_SYS},
                {"role": "user", "content": f"Error: {emsg}\nLine {ln}: {target}"}],
                args.ctx, 120)
            plan = ask_model(args.model_in_use, [{"role": "system", "content": FIX_PLAN_SYS},
                {"role": "user", "content": f"Goal: {goal}\nDiagnosis: {diagnosis}\n"
                 f"Failing line {ln}: {target}\nCompiler error: {emsg}"}], args.ctx, 120)
            user = (f"Function goal: {goal}\nPlan: {plan}\nCompiler error: {emsg}\n\n"
                    f"Replace ONLY these line(s):\n```cpp\n{target}\n```")
        else:
            user = (f"Compiler error: {emsg}\n\nReplace ONLY these line(s):\n"
                    f"```cpp\n{target}\n```")
        prog.set_phase(key, f"fixing line {ln} (edit {edits + 1})")
        reply = ask_model(args.model_in_use, [{"role": "system", "content": FIX_EDIT_SYS},
                          {"role": "user", "content": user}], args.ctx,
                          min(600, max(200, (hi - lo) * 48)))
        new, _ = parse_reply(reply)
        if new is None:
            new = reply.strip()
        new = "\n".join(l for l in new.split("\n")
                        if not l.lstrip().startswith("#include")).strip()
        if not new or new.strip() == target.strip():
            break
        if (new.count("{") - new.count("}")) != (target.count("{") - target.count("}")):
            break                   # would unbalance the braces
        indent = re.match(r"[ \t]*", lines[lo]).group(0)
        nl = new.split("\n")
        if indent and nl and not nl[0][:1].isspace():
            nl = [indent + x if x.strip() else x for x in nl]
        lines[lo:hi] = nl
        code = "\n".join(lines)
        edits += 1
    return code, compile_errors(code) is None, edits


def keep_one_function(code, wanted):
    """Keep only what belongs in this function's rewrite: #includes, types, declarations,
    and ONE function body (the one named `wanted`, else the longest). Extra function
    bodies the model invented, Ghidra helper functions and stray statements are dropped.
    Returns (code, found_the_function)."""
    items = split_items(code)
    bodies = [it for it in items if it.rstrip().endswith("}") and _func_name(it)
              and not re.match(r"\s*(template\s*<[^>]*>\s*)?(struct|class|union|enum|namespace)\b",
                               it)]
    target = next((b for b in bodies if _func_name(b) in wanted), None)
    if target is None and bodies:
        target = max(bodies, key=len)
    kept = []
    for it in items:
        first = it.split("\n", 1)[0].strip()
        if it in bodies and it is not target:
            continue                                     # another function's body
        name = _func_name(it.rstrip(";")) if it.rstrip().endswith(";") else None
        if name and GHIDRA_HELPERS.match(name):
            continue                                     # e.g. a CONCAT44 declaration
        if it is not target and not it.rstrip().endswith((";", "}")) \
                and not first.startswith("#"):
            continue                                     # unfinished fragment
        if it is not target and _is_statement(first):
            continue                                     # a loose statement or label
        kept.append(it)
    # A reply that was cut off: close its braces so it can't swallow what follows
    out = "\n\n".join(kept)
    missing = brace_balance(out)
    if missing > 0:
        out = out.rstrip() + "\n" + "}" * missing
    return out, target is not None


def parse_reply(reply):
    blocks = re.findall(r"```[\w+\-]*[ \t]*\n(.*?)```", reply, flags=re.S)
    code = max(blocks, key=len).strip() if blocks else None
    m = re.search(r"^\s*NAME:\s*`?([A-Za-z_][\w:~]*)`?\s*$", reply, flags=re.M)
    return code, (m.group(1) if m else None)


# ---------------------------------------------------------------- tiny functions
# Getters, setters, one-line wrappers and the like gain almost nothing from the model,
# so with --tiny they are copied over from Ghidra with its types tidied up.

GHIDRA_TYPES = [
    (r"\bundefined8\b", "uint64_t"), (r"\bundefined4\b", "uint32_t"),
    (r"\bundefined2\b", "uint16_t"), (r"\bundefined1\b", "uint8_t"),
    (r"\bundefined\s*\*", "void *"), (r"\bundefined\b", "uint8_t"),
    (r"\bulonglong\b", "uint64_t"), (r"\blonglong\b", "int64_t"),
    (r"\bulong\b", "uint64_t"), (r"\buint\b", "uint32_t"), (r"\bushort\b", "uint16_t"),
    (r"\buchar\b", "uint8_t"), (r"\bbyte\b", "uint8_t"), (r"\bsbyte\b", "int8_t"),
    (r"\bcode\s*\*", "void *"), (r"\b__(thiscall|cdecl|stdcall|fastcall)\b\s*", ""),
]
DECL_LINE = re.compile(r"^[\w\s\*&:<>]+?[\s\*&]\**\w+(\s*\[\w*\])*\s*;$")


def body_statements(pseudo):
    """The statements inside a function's outermost { }, without declarations/comments."""
    code = strip_comments(pseudo)
    if "{" not in code or "}" not in code:
        return None
    body = code[code.index("{") + 1:code.rindex("}")]
    out = []
    for line in body.splitlines():
        t = line.strip()
        if not t or (DECL_LINE.match(t) and "=" not in t and "(" not in t
                     and not re.match(r"(return|goto|break|continue|delete|throw)\b", t)):
            continue
        out.append(t)
    return out


def is_tiny(pseudo, limit):
    stmts = body_statements(pseudo)
    if stmts is None or len(stmts) > limit:
        return False
    return not any(re.match(r"(if|else|for|while|do|switch|case|goto)\b", t)
                   or re.match(r"\w+:$", t) or t.startswith(("{", "}")) for t in stmts)


def tidy_types(code):
    for rx, rep_ in GHIDRA_TYPES:
        code = re.sub(rx, rep_, code)
    return code


def tidy_tiny(pseudo):
    code = strip_comments(pseudo)
    for rx, rep_ in GHIDRA_TYPES:
        code = re.sub(rx, rep_, code)
    code = re.sub(r"\)\s*\n\s*\{", ") {", code, count=1)    # "f(...)\n\n{" -> "f(...) {"
    return "#include <cstdint>\n\n" + code.strip()


# ---------------------------------------------------------------- big functions
# A function too big for the model is cut into pieces at sensible places (between
# statements, preferring the outermost level), each piece is rewritten on its own, and
# the pieces are joined back together in order inside one function.

PIECE_PROMPT = """You turn part of a Ghidra decompiler function into clean, readable C++.
The function is too long to rewrite in one go, so you get one piece of it at a time.
The pieces are joined back together afterwards, in order.
- Rewrite ONLY the lines of this piece, in the same order, as C++ statements.
  No function header, no #include, no new struct or function definitions.
- The piece may start or end in the middle of a block. Every { or } in it that doesn't
  have its partner inside the piece must stay exactly where it is, so the pieces still
  fit together.
- Keep variable names exactly as they are: other pieces use them too.
- Keep the behaviour exactly the same. Keep goto and LAB_ labels as they are (they can
  jump between pieces).
- Ghidra helper notation is not real code: CONCAT44(a, b), SUB84(x, 0), ZEXT48(x),
  NEON_xxx(...) describe bit or vector operations. Write them as plain C++.
- _malloc, _free, _memcpy, ___sincos_stret etc. are standard library calls: use malloc,
  free, memcpy, sinf/cosf. Turn undefined4/undefined8 into real types.
- Never add printing, logging, messages or text strings that aren't in the piece.
{comments}
Reply with ONE ```cpp code block containing just the rewritten lines."""


def split_function(pseudo):
    """(header, declaration lines, body lines) of a function, or None."""
    code = strip_comments(pseudo)
    i, j = code.find("{"), code.rfind("}")
    if i < 0 or j <= i:
        return None
    header = " ".join(code[:i].split())
    lines = code[i + 1:j].strip("\n").split("\n")
    decls = []
    for l in lines:
        t = l.strip()
        if not t:
            if decls:
                break
            continue
        if DECL_LINE.match(t) and "=" not in t and "(" not in t:
            decls.append(l)
        else:
            break
    return header, decls, lines


def chunk_lines(lines, max_chars):
    """Cut lines into pieces of at most max_chars, choosing cut points between
    statements and as close to the outermost level as possible."""
    depth_after, d = [], 0
    for l in lines:
        d = max(0, d + brace_balance(l))
        depth_after.append(d)
    pieces, start, n = [], 0, len(lines)
    while start < n:
        size, end = 0, start
        while end < n and (end == start or size + len(lines[end]) + 1 <= max_chars):
            size += len(lines[end]) + 1
            end += 1
        if end >= n:
            pieces.append(lines[start:])
            break
        best, best_key = end - 1, None
        for c in range(start + (end - start) // 2, end):
            t = lines[c].strip()
            if t and not t.endswith((";", "{", "}")) and not re.match(r"\w+:$", t):
                continue                                  # mid-statement: don't cut here
            key = (depth_after[c], -c)
            if best_key is None or key < best_key:
                best, best_key = c, key
        pieces.append(lines[start:best + 1])
        start = best + 1
    return ["\n".join(p) for p in pieces]


def clean_piece(code, original, names):
    """The model's rewrite of a piece if it still fits the jigsaw, else None."""
    lines = [l for l in code.split("\n") if not re.match(r"\s*#\s*(include|import)\b", l)]
    while lines and not lines[0].strip():
        lines.pop(0)
    # Unwrap a function header the model added around the piece
    if lines and lines[0].strip() not in original:
        first = lines[0].strip()
        hdr = re.match(r"[\w\s\*&:<>,]*\b(\w+)\s*\([^;]*\)\s*(const\s*)?\{?$", first)
        if hdr and not re.match(r"(if|for|while|switch|do|else|return)\b", first) and \
                (hdr.group(1) in names or first.endswith("{") or
                 (len(lines) > 1 and lines[1].strip() == "{")):
            lines.pop(0)
            if not first.endswith("{") and lines and lines[0].strip() == "{":
                lines.pop(0)
            body = "\n".join(lines).rstrip()
            if body.endswith("}") and brace_balance(body) == brace_balance(original) - 1:
                body = body[:body.rfind("}")].rstrip()
            lines = body.split("\n")
    out = "\n".join(lines).strip("\n")
    if not out.strip() or brace_balance(out) != brace_balance(original):
        return None
    return out


# ---------------------------------------------------------------- tidying the output

def strip_comments(code):
    """Remove // and /* */ comments, leaving string and character literals alone."""
    MARK, out, i, n = "\x00", [], 0, len(code)
    while i < n:
        two = code[i:i + 2]
        if two == "//":
            j = code.find("\n", i)
            i = n if j < 0 else j
            out.append(MARK)
            continue
        if two == "/*":
            j = code.find("*/", i + 2)
            i = n if j < 0 else j + 2
            out.append(MARK)
            continue
        m = re.match(r'(?:u8|u|U|L)?R"([^(\s"\\]{0,16})\(', code[i:])
        if m and (i == 0 or not (code[i - 1].isalnum() or code[i - 1] == "_")):
            end = code.find(")" + m.group(1) + '"', i + m.end())
            j = n if end < 0 else end + len(m.group(1)) + 2
            out.append(code[i:j])
            i = j
            continue
        if code[i] in "\"'":
            q, j = code[i], i + 1
            while j < n and code[j] != q and code[j] != "\n":
                j += 2 if code[j] == "\\" else 1
            j = min(j + 1, n)
            out.append(code[i:j])
            i = j
            continue
        out.append(code[i])
        i += 1
    lines = []
    for line in "".join(out).split("\n"):
        if MARK in line and not line.replace(MARK, "").strip():
            continue
        line = re.sub(r"^([ \t]*)\x00[ \t]*", r"\1", line)
        line = re.sub(r"(\S)[ \t]*\x00[ \t]*(?=\S)", r"\1 ", line)
        lines.append(line.replace(MARK, "").rstrip())
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip("\n")


IMPORT_RE = re.compile(r"^\s*#\s*(include|import)\b")


def _depth_change(line):
    d, i, n = 0, 0, len(line)
    while i < n:
        ch = line[i]
        if ch in "\"'":
            j = i + 1
            while j < n and line[j] != ch:
                j += 2 if line[j] == "\\" else 1
            i = j + 1
            continue
        d += 1 if ch in "{([" else -1 if ch in "})]" else 0
        i += 1
    return d


def split_items(code):
    """Top-level pieces of a file: an #include, a declaration, a struct, a function."""
    items, cur, depth = [], [], 0
    for line in code.split("\n"):
        s = line.strip()
        if not cur and not s:
            continue
        cur.append(line)
        depth = max(0, depth + _depth_change(line))
        last = next((l.strip() for l in reversed(cur) if l.strip()), "")
        if depth == 0 and ((not s and not last.endswith(")")) or s.startswith("#")
                           or s.endswith((";", "}"))):
            items.append("\n".join(cur).rstrip())
            cur = []
    if cur:
        items.append("\n".join(cur).rstrip())
    return [it for it in items if it.strip()]


def combine(codes):
    """One file from many: each #include once at the top, type definitions and
    declarations once (before the functions), functions in program order."""
    includes, types, decls, funcs, seen = [], [], [], [], set()
    for code in codes:
        for item in split_items(code):
            first = item.split("\n", 1)[0].strip()
            norm = re.sub(r"\s+", " ", item).strip()
            if IMPORT_RE.match(first):
                if norm not in seen:
                    seen.add(norm)
                    includes.append(first)
                continue
            if first.startswith("#"):                     # other preprocessor lines
                funcs.append(item)
                continue
            if norm in seen:
                continue
            seen.add(norm)
            if re.match(r"(typedef|enum|using)\b", first) or \
                    re.match(r"(template\s*<[^>]*>\s*)?(struct|class|union)\s+[\w:]+\s*(final\s*)?"
                             r"(:[^{;]*)?(\{|$)", first) and not item.rstrip().endswith("}"):
                types.append(item)                        # struct/class definitions, typedefs
            elif norm.endswith(";") and "{" not in norm:
                decls.append(item)                        # forward declarations, prototypes
            else:
                funcs.append(item)
    parts = ["\n".join(includes)] if includes else []
    if types:
        parts.append("\n\n".join(types))
    if decls:
        parts.append("\n".join(decls))
    parts += funcs
    return "\n\n".join(parts).strip() + "\n"


# ---------------------------------------------------------------- bookkeeping

def load_progress(P: Paths):
    if not P.progress.exists():
        return {}
    try:
        return json.loads(P.progress.read_text())
    except Exception as e:
        set_aside(P.progress, str(e))     # keep it rather than overwrite it
        return {}


def save_progress(P: Paths, progress):
    write_atomic(P.progress, json.dumps(progress, indent=0))


def apply_names(text, names):
    """Swap Ghidra's placeholder names for the new ones (whole words only)."""
    if not names:
        return text
    rx = re.compile(r"\b(" + "|".join(re.escape(k) for k in
                                       sorted(names, key=len, reverse=True)) + r")\b")
    return rx.sub(lambda m: names[m.group(1)], text)


def mark_function(code, ghidra_name, addr_hex):
    """Tag the function body with a one-line marker carrying its Ghidra address,
    so the recover stage can map a function in the combined file back to its
    pseudocode. The marker rides on the body item through combine()."""
    items = split_items(code)
    for idx, it in enumerate(items):
        if it.rstrip().endswith("}") and _func_name(it) and not re.match(
                r"\s*(template\s*<[^>]*>\s*)?(struct|class|union|enum|namespace)\b", it):
            items[idx] = f"//@ghidra {addr_hex} {ghidra_name}\n{it}"
            break
    return "\n\n".join(items)


def write_outputs(P: Paths, progress, order, keep_comments):
    """rewritten.cpp from every finished function (including ones waiting to be
    rewritten again: their current version stays until the new one replaces it)."""
    names = {e["ghidra"]: e["name"] for e in progress.get("functions", {}).values()
             if e.get("name") and e["name"] != e["ghidra"]}
    codes, index = [], {}
    for key in order:
        e = progress.get("functions", {}).get(key)
        if e and e.get("status") == "done":
            f = P.rewritten_dir / f"{key}.cpp"
            if f.exists():
                code = f.read_text()
                code, _ = keep_one_function(code if keep_comments else strip_comments(code),
                                            {e.get("name"), e.get("ghidra")})
                # apply names FIRST, then add the marker, so the marker's literal
                # Ghidra name/address are never rewritten by apply_names
                code = mark_function(apply_names(code, names), e["ghidra"], key)
                codes.append(code)
                final = e.get("name") or e["ghidra"]
                index[final] = {"ghidra": e["ghidra"], "addr": key,
                                "status": e.get("status"),
                                "pieces": e.get("pieces"), "tiny": e.get("tiny", False)}
    if codes:
        write_atomic(P.rewritten, combine(codes))
    # sidecar map (final name -> Ghidra address), a fallback for the fixer when a
    # function in the combined file has no inline marker
    write_atomic(P.index, json.dumps(index, indent=0))
    write_atomic(P.names, "".join(
        f"{e['ghidra']}  ->  {e['name']}\n" for k in order
        if (e := progress.get("functions", {}).get(k)) and e.get("name")))


def unique_name(name, taken):
    base, n = name, 2
    while name in taken:
        name = f"{base}{n}"
        n += 1
    return name


# ---------------------------------------------------------------- progress display

def fmt_duration(secs):
    secs = int(secs)
    if secs < 60:
        return f"{secs}s"
    m, h = secs // 60, secs // 3600
    if h == 0:
        return f"{m}m"
    if h < 48:
        return f"{h}h {m % 60:02d}m"
    return f"{h // 24}d {h % 24}h"


def fmt_clock(secs):
    when = datetime.now() + timedelta(seconds=secs)
    clock = when.strftime("%I:%M %p").lstrip("0")
    if when.date() == datetime.now().date():
        return clock
    if when.date() == (datetime.now() + timedelta(days=1)).date():
        return "tomorrow " + clock
    return when.strftime("%a ") + clock


class Progress:
    """A progress bar that stays at the bottom of the window while finished functions
    scroll past above it, with a time estimate and timers for the functions in progress.
    Speed and time left are averaged over the whole session."""
    SPIN = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self, total, already):
        self.total, self.done = total, already
        self.finished_at = []                 # when each function finished, this run
        self.started = time.time()
        self.active = {}                      # key -> [label, phase, started]
        self.extra = None                     # optional callable: more text for the bar
        self.live = sys.stdout.isatty()
        self.lock = threading.RLock()
        self.stop_flag = threading.Event()
        self.thread = None
        if self.live:
            self.thread = threading.Thread(target=self._spin, daemon=True)
            self.thread.start()

    def rate(self):
        """Functions finished per second, averaged over the whole session (since this
        command was started)."""
        n = len(self.finished_at)
        elapsed = time.time() - self.started
        if n < 2 or elapsed <= 0:
            return None
        return n / elapsed

    def estimate(self):
        r = self.rate()
        if not r:
            return "estimating time left..."
        secs = (self.total - self.done) / r
        per = 60 * r
        speed = f"{per:.1f}/min" if per >= 1 else f"{fmt_duration(1 / r)} each"
        return f"{speed}, about {fmt_duration(secs)} left, done around {fmt_clock(secs)}"

    def bar_line(self, spin=""):
        frac = self.done / self.total if self.total else 1.0
        width = 22
        full = int(frac * width)
        bar = "█" * full + "░" * (width - full)
        running = fmt_duration(time.time() - self.started)
        line = (f"{spin} {self.done}/{self.total} {bar} {frac * 100:4.1f}%  "
                f"running {running} | {self.estimate()}")
        if self.extra:
            line += f" | {self.extra()}"
        if self.active:
            label, phase, t0 = min(self.active.values(), key=lambda v: v[2])
            line += f"  | now: {label} {phase} {int(time.time() - t0)}s"
            if len(self.active) > 1:
                line += f" (+{len(self.active) - 1} more)"
        cols = shutil.get_terminal_size((100, 20)).columns
        return line[:max(20, cols - 1)]

    def _draw(self, spin=""):
        sys.stdout.write("\r\x1b[K" + self.bar_line(spin))
        sys.stdout.flush()

    def _spin(self):
        i = 0
        while not self.stop_flag.wait(0.25):
            with self.lock:
                self._draw(self.SPIN[i % len(self.SPIN)])
            i += 1

    def log(self, text):
        """Print a line above the bar."""
        with self.lock:
            if self.live:
                sys.stdout.write("\r\x1b[K" + text + "\n")
                self._draw(" ")
            else:
                print(text, flush=True)

    def begin(self, key, label):
        with self.lock:
            self.active[key] = [label, "", time.time()]

    def set_phase(self, key, phase):
        with self.lock:
            if key in self.active:
                self.active[key][1] = phase

    def end(self, key, text):
        with self.lock:
            t0 = self.active.pop(key, [None, None, time.time()])[2]
            self.done += 1
            self.finished_at.append(time.time())
            self.log(text.replace("{secs}", fmt_duration(time.time() - t0)))
            if not self.live and (self.done % 10 == 0 or self.done == self.total):
                print(self.bar_line(), flush=True)

    def close(self):
        if self.stop_flag.is_set():
            return
        self.stop_flag.set()
        if self.thread:
            self.thread.join(timeout=1)
        if self.live:
            with self.lock:
                sys.stdout.write("\r\x1b[K" + self.bar_line(" ") + "\n")
                sys.stdout.flush()

# ---------------------------------------------------------------- export stage

def export_info(P: Paths) -> dict:
    try:
        data = json.loads(P.export.read_text())
    except Exception:
        return {}
    pc = data.get("pseudocode") or {}
    return {"functions": len(data.get("functions") or []),
            "with_pseudocode": sum(1 for v in pc.values() if v),
            "export_version": data.get("version"),
            "source": data.get("ghidra"),
            "datatypes": len(data.get("datatypes") or []),
            "signatures": len(data.get("signatures") or {})}


def open_ghidra(P: Paths, args, live_ok=True) -> GhidraCache:
    """The export, with a live Ghidra plugin behind it to fill any gap (unless the
    export came from headless, where the plugin usually isn't running)."""
    live = Ghidra(args.ghidra) if live_ok and not (args.headless_export or args.project) \
        else None
    return GhidraCache(P.export, live)


def run_export(P: Paths, args, redo: set) -> dict:
    refresh = "export" in redo
    headless = bool(args.headless_export or args.project)
    if refresh:
        snapshot(P, "redo-export", [P.export])
    if headless and (refresh or not P.export.exists() or args.export_complete):
        plog(P, "  exporting with Ghidra headless (analyzeHeadless)"
                + (" — every function again, replacing entries in place" if refresh else ""))
        run_headless_export(P, args, refresh)
        ghidra = GhidraCache(P.export, None)
    else:
        ghidra = open_ghidra(P, args)
        if not P.export.exists() or refresh or args.export_complete:
            ghidra.build_full_export(
                parallel=args.export_parallel or max(8, args.parallel), refresh=refresh,
                progress_print=lambda m: plog(P, "  " + m))
        else:
            plog(P, f"  using the existing {P.export.name} (Ghidra not needed)")
    names_known = {e["ghidra"]: e["name"]
                   for e in load_progress(P).get("functions", {}).values()
                   if e.get("name") and e["name"] != e["ghidra"]}
    try:
        n_edges = ghidra.write_callgraph(P.callgraph, names_known)
        plog(P, f"  callgraph.json: {n_edges} functions with internal calls")
    except Exception as e:
        plog(P, f"  (could not write callgraph.json: {e})")
    info = export_info(P)
    plog(P, f"  export: {info.get('with_pseudocode', 0)}/{info.get('functions', 0)} functions "
            f"have pseudocode"
            + (f", {info['datatypes']} data types, {info['signatures']} signatures"
               if info.get("datatypes") or info.get("signatures") else ""))
    return info


# ---------------------------------------------------------------- rewrite stage

def _pseudo_sha(code: Optional[str]) -> str:
    return hashlib.sha1((code or "").encode()).hexdigest()[:16]


def run_rewrite(P: Paths, args, redo: set, client: ModelClient) -> dict:
    """Rewrite every function that isn't done yet. Returns a summary; summary["stop"]
    is True when the run should stop here (--max reached, or nothing to build)."""
    ghidra = open_ghidra(P, args)
    funcs = ghidra.functions()
    selected = funcs
    if args.functions:
        wanted = {w.lower().removeprefix("0x") for w in args.functions}
        selected = [f for f in funcs if f[0].lower() in wanted or f"{f[1]:x}" in wanted]
        plog(P, f"  working on {len(selected)} of {len(funcs)} functions (--functions)")
    sel_keys = {f"{a:x}" for _, a in selected}

    progress = load_progress(P)
    done = progress.setdefault("functions", {})
    # every function stays in the output, in program order, whatever is selected
    order = [f"{a:x}" for _, a in funcs]

    # entries an older pseudo_to_cpp marked "redo" still have their code: keep it
    # in the output until the new rewrite replaces it
    for e in done.values():
        if e.get("status") == "redo":
            e["status"], e["stale"] = "done", True

    marked = 0
    if "rewrite" in redo:
        snapshot(P, "redo-rewrite", [P.progress, P.rewritten, P.rewritten_dir, P.names,
                                     P.index])
        progress["redo_gen"] = progress.get("redo_gen", 0) + 1
        for key in sel_keys:
            e = done.get(key)
            if e and e.get("status") == "done":
                e["stale"] = True
                marked += 1
            elif e:
                e["status"] = "todo"
        plog(P, f"  --redo rewrite: {marked} function(s) will be rewritten again; each "
                f"replaces its old version as it finishes")

    # pseudocode that changed since a function was rewritten (e.g. --redo export
    # after renaming things in Ghidra) -> rewrite that function again
    changed = 0
    for n, a in funcs:
        key = f"{a:x}"
        e = done.get(key)
        if not e or e.get("status") != "done":
            continue
        sha = _pseudo_sha(ghidra.data["pseudocode"].get(key))
        if e.get("pseudo_sha") is None:
            e["pseudo_sha"] = sha
        elif e["pseudo_sha"] != sha and not e.get("stale"):
            e["stale"] = True
            changed += 1
    if changed:
        plog(P, f"  {changed} function(s) have new pseudocode since they were rewritten — "
                f"rewriting them again")

    taken = {e["name"] for e in done.values() if e.get("name")} | \
            {n for n, _ in funcs if not PLACEHOLDER.match(n)}
    if args.redo_suspect:
        n_sus = 0
        for n, a in selected:
            e = done.get(f"{a:x}")
            if not e or e.get("status") != "done" or e.get("tiny"):
                continue
            if "suspect" not in e:              # done by an earlier version: check it now
                f = P.rewritten_dir / f"{a:x}.cpp"
                pf = P.pseudocode / (re.sub(r"[^\w.-]", "_", n) + ".c")
                code = f.read_text(errors="replace") if f.exists() else ""
                pseudo = pf.read_text(errors="replace") if pf.exists() else ""
                why = suspect_reasons(code, pseudo, e.get("name"),
                                      check_names=not e.get("pieces"))
                if PLACEHOLDER.match(n) and e.get("name") in (None, n):
                    why.append("no real name")
                e["suspect"] = sorted(set(why))
            if e["suspect"] and not e.get("stale"):
                e["stale"] = True
                n_sus += 1
        if n_sus:
            snapshot(P, "redo-suspect", [P.progress, P.rewritten, P.rewritten_dir])
        plog(P, f"  {n_sus} function(s) flagged for a second look will be rewritten again "
                f"(their current version stays until then)")
    save_progress(P, progress)

    todo = [(n, a) for n, a in selected
            if done.get(f"{a:x}", {}).get("status") not in ("done", "skipped")
            or done.get(f"{a:x}", {}).get("stale")]
    if len(todo) < len(selected):
        plog(P, f"  {len(selected) - len(todo)} already done, {len(todo)} to go")
    if not todo:
        write_outputs(P, progress, order, args.comments)
        return _rewrite_summary(progress, order, stop=False)

    model = client.resolve(args.rewrite_model or args.model)
    args.model_in_use = model
    plog(P, f"  rewriting with {client.name} model '{model}'"
            + (f", compile check with {COMPILER['cmd']}" if COMPILER["cmd"] else
               " (compile check off: the build stages compile against shared.h)"))
    print("Working through functions in program order. Press Ctrl+C to pause; run the "
          "same command to resume.\n", flush=True)

    system = SYSTEM_PROMPT.replace("{comments}",
                                   WITH_COMMENTS if args.comments else NO_COMMENTS)
    t_start, last_write = time.time(), time.time()
    prog = Progress(len(selected), len(selected) - len(todo))
    GATE["gate"] = ModelGate(args.parallel)
    GATE["tuner"] = None
    if args.auto_parallel:
        GATE["tuner"] = AutoParallel(GATE["gate"], args.max_parallel,
                                     args.auto_every * 60, prog.log)
        prog.extra = lambda: f"parallel {GATE['gate'].limit}"
        prog.log(f"  parallel starts at {args.parallel}; adjusting every "
                 f"{args.auto_every} min (max {args.max_parallel})")
    state = threading.RLock()          # guards progress/names when several run at once
    stopping = threading.Event()
    counts = {"done": 0}
    redo_gen = str(progress.get("redo_gen", 0))

    def finish(key, entry, text):
        with state:
            old = done.get(key) or {}
            if entry["status"] != "done" and old.get("status") == "done":
                # a redo that came back empty-handed: keep the previous rewrite
                old.pop("stale", None)
                old["redo_failed"] = entry["status"]
                entry = old
                text += "  (kept the previous version)"
            done[key] = entry
            save_progress(P, progress)
            if entry["status"] == "done":
                counts["done"] += 1
        prog.end(key, text)

    def work(gname, addr):
        key = f"{addr:x}"
        if stopping.is_set():
            return
        prog.begin(key, gname)
        prog.set_phase(key, "getting pseudocode")
        pseudo = ghidra.pseudocode(gname, addr)
        if ghidra.notice:
            prog.log(ghidra.notice)
            ghidra.notice = None
        if not pseudo:
            return finish(key, {"ghidra": gname, "status": "skipped"},
                          f"  {gname}: no pseudocode from Ghidra, skipped")
        safe = re.sub(r"[^\w.-]", "_", gname)
        (P.pseudocode / f"{safe}.c").write_text(pseudo + "\n")
        psha = _pseudo_sha(pseudo)

        # Names already chosen for other functions, swapped in so the model sees them
        with state:
            names = {e["ghidra"]: e["name"] for e in done.values()
                     if e.get("name") and e["name"] != e["ghidra"]}
        shown = apply_names(pseudo, names)
        if args.tiny and is_tiny(shown, args.tiny):
            (P.rewritten_dir / f"{key}.cpp").write_text(tidy_tiny(shown) + "\n")
            return finish(key, {"ghidra": gname, "name": gname, "status": "done",
                                "tiny": True, "pseudo_sha": psha},
                          f"  {gname}: small, copied without the model")
        in_tokens = int((len(shown) + len(system)) / CHARS_PER_TOKEN) + 200
        room = args.ctx - in_tokens
        if room < 1500:
            if not args.no_split:
                return work_in_pieces(gname, key, shown, names, psha)
            # Too big to fit: cutting it off produces garbage, so leave it for a later
            # run with a larger --ctx
            return finish(key, {"ghidra": gname, "status": "too big"},
                          f"  {gname}: too big for --ctx {args.ctx} (needs about "
                          f"{in_tokens * 2 // 1000 + 1}k), left for later")
        max_out = min(room - 200, max(1500, int(in_tokens * 1.5)))
        called = sorted({n for n in names.values()
                         if re.search(rf"\b{re.escape(n)}\s*\(", shown)})
        msg = (f"Function: {gname}"
               + (" (placeholder name: choose a meaningful one)" if PLACEHOLDER.match(gname)
                  else " (keep this name)")
               + (f"\nOther functions it calls were already given these names: "
                  f"{', '.join(called)}" if called else "")
               + f"\n\nGhidra pseudocode:\n```c\n{shown}\n```")
        prog.set_phase(key, f"writing C++ ({len(shown.splitlines())} lines)")
        reply = ask_model(args.model_in_use, [{"role": "system", "content": system},
                                              {"role": "user", "content": msg}],
                          args.ctx, max_out)
        code, new_name = parse_reply(reply)
        ok = False
        if code:
            code, ok = keep_one_function(code, {new_name, gname})

        def problems(c):
            return (len(invented_strings(c, shown)) + len(leftover_names(c))
                    + len(surviving_strings(c, shown)))

        if (not ok or (code and problems(code))) and args.retry_quality \
                and not args.no_retry:
            prog.set_phase(key, "retrying")
            left = leftover_names(code) if code else []
            surv = surviving_strings(code, shown) if code else []
            reply = ask_model(args.model_in_use, [
                {"role": "system", "content": system},
                {"role": "user", "content": msg},
                {"role": "user", "content": "Write ONLY this one function, complete, in one "
                                            "```cpp code block, then NAME: <the name you chose>. Don't add "
                                            "printing or text that isn't in the pseudocode."
                 + (f" Give these decompiler names descriptive names: {', '.join(left[:20])}."
                    if left else "")
                 + (f" Remove these identifying strings (they belong to the original program): "
                    f"{', '.join(repr(s) for s in surv[:10])}."
                    if surv else "")}],
                args.ctx, max_out, temperature=0.4)
            code2, new_name2 = parse_reply(reply)
            if code2:
                code2, ok2 = keep_one_function(code2, {new_name2, gname})
                better = ok2 and (not ok or problems(code2) < problems(code))
                if better or not code:
                    code, new_name, ok = code2, new_name2 or new_name, ok2
        if not code:
            return finish(key, {"ghidra": gname, "status": "skipped"},
                          f"  {gname}: the model didn't return code, skipped")

        # Compile it; if that fails, repair it incrementally (minimal edits to the
        # failing lines) rather than regenerating the whole function.
        compiled, fixes = None, 0
        if COMPILER["cmd"]:
            prog.set_phase(key, "compiling")
            if args.fix_mode == "edit":
                code, compiled, fixes = incremental_fix(
                    args, code, shown, new_name or gname, prog, key)
            else:
                errors = compile_errors(code)
                while errors and fixes < args.compile_retries:
                    fix = (f"That didn't compile. The compiler said:\n```\n{errors}\n```\n"
                           "Fix it so it compiles as standard C++17 on its own, with the "
                           "same behaviour: include the headers you need, define the structs "
                           "and globals you use, and declare (no body) other functions. Reply "
                           "with the whole function again in one ```cpp code block, then "
                           "NAME: <the name>.")
                    prior = f"```cpp\n{code}\n```\nNAME: {new_name or gname}"
                    need = in_tokens + (len(prior) + len(fix)) / CHARS_PER_TOKEN
                    if need + 500 > args.ctx:
                        break
                    fixes += 1
                    prog.set_phase(key, f"fixing compile errors ({fixes}/{args.compile_retries})")
                    reply = ask_model(args.model_in_use, [
                        {"role": "system", "content": system},
                        {"role": "user", "content": msg},
                        {"role": "assistant", "content": prior},
                        {"role": "user", "content": fix}],
                        args.ctx, max(1500, min(max_out, int(args.ctx - need - 200))))
                    code2, new_name2 = parse_reply(reply)
                    if not code2:
                        continue
                    code2, ok2 = keep_one_function(code2, {new_name2, new_name, gname})
                    if not ok2:
                        continue
                    errors2 = compile_errors(code2)
                    if errors2 is None or n_errors(errors2) <= n_errors(errors):
                        code, errors = code2, errors2
                        new_name = new_name2 or new_name
                compiled = errors is None

        # Faithful fallback: the model couldn't make it compile. Emit the
        # deterministic pseudocode-derived version (type-cleaned, identifying
        # strings removed) instead of a broken rewrite — it's more faithful to
        # the binary and the fixer's recovery (which has the ghidra intrinsics)
        # can compile it. Flagged so you can review these.
        faithful = False
        if compiled is False and COMPILER["cmd"]:
            fb = faithful_from_pseudo(shown)
            if fb and keep_one_function(fb, {gname})[1]:
                code = fb
                new_name = gname          # the faithful version keeps the Ghidra name
                faithful = True

        with state:
            prev_name = done.get(key, {}).get("name")
            if not PLACEHOLDER.match(gname):
                name = gname                              # Ghidra already had a real name
            elif prev_name and prev_name != gname:
                name = prev_name      # rewritten again: keep the name its callers use
            elif new_name and new_name != gname and not PLACEHOLDER.match(new_name) \
                    and not BAD_NAME.match(new_name):
                name = unique_name(new_name, taken - {done.get(key, {}).get("name")})
                taken.add(name)
            else:
                name = gname
        # Make the code use the chosen name. This also covers the case where the
        # model's name was REJECTED (name == gname): the body was written with
        # new_name (e.g. "theFunctionName"), so it must be swapped back to gname,
        # or every rejected function ends up defining the same duplicate name.
        if new_name and new_name != name and new_name != gname:
            code = re.sub(rf"\b{re.escape(new_name)}\b", name, code)
        if name != gname:
            code = re.sub(rf"\b{re.escape(gname)}\b", name, code)
        (P.rewritten_dir / f"{key}.cpp").write_text(code + "\n")
        entry = {"ghidra": gname, "name": name, "status": "done", "pseudo_sha": psha}
        if new_name and new_name not in (name, gname) and name == prev_name:
            entry["suggested_name"] = new_name
        if compiled is not None:
            entry["compiled"] = compiled
        why = suspect_reasons(code, shown, name if name != gname else None)
        if PLACEHOLDER.match(gname) and name == gname:
            why.append("no real name")      # the model's name was unusable
        if faithful:
            entry["faithful"] = True
            why.append("faithful fallback (model couldn't compile a clean rewrite)")
        if compiled is False:
            why.append("doesn't compile")
        if why:
            entry["suspect"] = sorted(set(why))
        note = ("compiles" if compiled and not fixes else
                f"compiles after {fixes} fix{'es' if fixes > 1 else ''}" if compiled else "")
        finish(key, entry, f"  {gname} -> {name}  ({{secs}}{', ' + note if note else ''})"
               + (f"  [check: {', '.join(entry['suspect'])}]" if why else ""))

    piece_system = PIECE_PROMPT.replace("{comments}",
                                        WITH_COMMENTS if args.comments else NO_COMMENTS)

    def work_in_pieces(gname, key, shown, names, psha):
        parts = split_function(shown)
        if not parts:
            return finish(key, {"ghidra": gname, "status": "too big"},
                          f"  {gname}: too big, and couldn't be split, left for later")
        header, decls, lines = parts
        decl_text = "\n".join(d.strip() for d in decls)
        if len(decl_text) > 2000:
            decl_text = decl_text[:2000].rsplit("\n", 1)[0] + "\n..."
        overhead = len(piece_system) + len(header) + len(decl_text) + 900
        budget = (args.ctx - overhead / CHARS_PER_TOKEN - 300) / 2.3   # input + reply
        max_chars = max(1200, int(budget * CHARS_PER_TOKEN))
        pieces = chunk_lines(lines, max_chars)
        n = len(pieces)
        pdir = P.rewritten_dir / f"{key}.parts"
        pdir.mkdir(exist_ok=True)
        # pieces saved by an interrupted attempt are reused, unless they belong to an
        # earlier round than this --redo (then they're overwritten one by one)
        gen_file = pdir / "gen.txt"
        reuse = not gen_file.exists() or gen_file.read_text().strip() == redo_gen
        gen_file.write_text(redo_gen)
        placeholder = PLACEHOLDER.match(gname)
        state_ = {"done": 0, "fallback": 0, "name": None}
        lock_ = threading.Lock()
        prog.set_phase(key, f"big: 0/{n} parts")

        def one(i):
            piece = pieces[i]
            h = hashlib.sha1(piece.encode()).hexdigest()[:10]
            f = pdir / f"{i:04d}-{h}.cpp"
            if f.exists() and reuse:            # done in an earlier session
                got = f.read_text()
                if i == 0 and (pdir / "name.txt").exists():
                    state_["name"] = (pdir / "name.txt").read_text().strip() or None
            else:
                ctx_text = ""
                if i > 0:
                    tail = "\n".join(pieces[i - 1].split("\n")[-8:])
                    ctx_text = (f"Its local variables:\n```c\n{decl_text}\n```\n"
                                f"The piece before this one ends with:\n```c\n{tail}\n```\n")
                ask_name = i == 0 and placeholder
                msg = (f"Function: {gname}, piece {i + 1} of {n}\n"
                       f"Function header: {header}\n{ctx_text}\n"
                       f"Piece {i + 1} to rewrite:\n```c\n{piece}\n```"
                       + ("\n\nAfter the code block, also write one line NAME: followed by "
                          "a meaningful lowerCamelCase name for the whole function, "
                          "judging from this first piece." if ask_name else ""))
                tok = len(piece) / CHARS_PER_TOKEN
                max_out = int(tok * 1.5) + 300
                reply = ask_model(args.model_in_use,
                                  [{"role": "system", "content": piece_system},
                                   {"role": "user", "content": msg}], args.ctx, max_out)
                code, new_name = parse_reply(reply)
                got = clean_piece(code or "", piece, set(names.values()) | {gname})
                if got is None and not args.no_retry:
                    reply = ask_model(args.model_in_use, [
                        {"role": "system", "content": piece_system},
                        {"role": "user", "content": msg + "\n\nRewrite ONLY these lines, "
                         "keeping every unmatched { and } where it is. No function header."}],
                        args.ctx, max_out, temperature=0.4)
                    code, new_name2 = parse_reply(reply)
                    got = clean_piece(code or "", piece, set(names.values()) | {gname})
                    new_name = new_name or new_name2
                if got is None:                 # doesn't fit: keep Ghidra's version
                    got = "// [left as Ghidra wrote it]\n" + tidy_types(piece)
                pdir.mkdir(parents=True, exist_ok=True)
                if ask_name and new_name:
                    state_["name"] = new_name
                    (pdir / "name.txt").write_text(new_name)
                f.write_text(got)
            with lock_:
                state_["done"] += 1
                if got.startswith("// [left as Ghidra wrote it]"):
                    state_["fallback"] += 1
                prog.set_phase(key, f"big: {state_['done']}/{n} parts")
            return got

        # The pieces don't depend on each other, so several can be written at once;
        # the model limit still applies to all of them together.
        with ThreadPoolExecutor(max_workers=min(n, max(1, GATE["gate"].limit))) as pp:
            results = list(pp.map(one, range(n)))

        new_name = state_["name"]
        with state:
            prev_name = done.get(key, {}).get("name")
            if not placeholder:
                name = gname
            elif prev_name and prev_name != gname:
                name = prev_name      # rewritten again: keep the name its callers use
            elif new_name and not PLACEHOLDER.match(new_name) and not BAD_NAME.match(new_name):
                name = unique_name(new_name, taken - {done.get(key, {}).get("name")})
                taken.add(name)
            else:
                name = gname
        head = tidy_types(header)
        if name != gname:
            head = re.sub(rf"\b{re.escape(gname)}\b", name, head)
        body = "\n".join(r.replace("// [left as Ghidra wrote it]\n", "") for r in results)
        code = f"{head} {{\n{body}\n}}"
        # Drive the REASSEMBLED big function to compile with the same line-anchored
        # edit loop used for normal functions. This is what makes it size-proof:
        # the fix step only ever sends the ONE failing line to the model, never the
        # whole function, so --ctx is never a constraint during repair.
        compiled, fixes = None, 0
        if COMPILER["cmd"] and args.fix_mode == "edit":
            prog.set_phase(key, "compiling (big)")
            code, compiled, fixes = incremental_fix(args, code, shown, name, prog, key)
        # faithful fallback (same as normal functions): if the reassembled big
        # function still won't compile, emit the deterministic pseudocode version
        faithful = False
        if compiled is False and COMPILER["cmd"]:
            fb = faithful_from_pseudo(shown)
            if fb:
                if name != gname:
                    fb = re.sub(rf"\b{re.escape(gname)}\b", name, fb)
                code = fb
                faithful = True
        (P.rewritten_dir / f"{key}.cpp").write_text(code + "\n")
        shutil.rmtree(pdir, ignore_errors=True)    # scratch pieces, now joined above
        entry = {"ghidra": gname, "name": name, "status": "done", "pieces": n,
                 "pseudo_sha": psha}
        if compiled is not None:
            entry["compiled"] = compiled
        # the pieces keep Ghidra's variable names on purpose, so don't flag those
        why = suspect_reasons(code, shown, name if name != gname else None, check_names=False)
        if placeholder and name == gname:
            why.append("no real name")
        if faithful:
            entry["faithful"] = True
            why.append("faithful fallback (model couldn't compile a clean rewrite)")
        if compiled is False:
            why.append("doesn't compile")
        if state_["fallback"]:
            why.append(f"{state_['fallback']} of {n} parts left as Ghidra wrote them")
        if why:
            entry["suspect"] = sorted(set(why))
        note = ("compiles" if compiled and not fixes else
                f"compiles after {fixes} fix{'es' if fixes != 1 else ''}" if compiled else
                "not compiling" if compiled is False else "")
        finish(key, entry, f"  {gname} -> {name}  (big: {n} parts"
               + (f", {note}" if note else "") + ", {secs})"
               + (f"  [check: {', '.join(entry['suspect'])}]" if why else ""))

    # Keep functions in progress, handed out in program order
    pending, it = set(), iter(todo)
    reached_max = False
    try:
        workers = (args.max_parallel + 4) if args.auto_parallel else args.parallel
        # (not a "with" block: leaving one waits for every function in progress to
        # finish, which made Ctrl+C slow to pause)
        pool = ThreadPoolExecutor(max_workers=workers)
        while True:
            # with --auto-parallel, a few extra functions are kept ready (pseudocode
            # fetched) so the model never waits on Ghidra
            target = GATE["gate"].limit + 4 if args.auto_parallel else args.parallel
            while len(pending) < target and not stopping.is_set():
                nxt = next(it, None)
                if nxt is None:
                    break
                pending.add(pool.submit(work, *nxt))
            if not pending:
                break
            finished, pending = wait(pending, timeout=5, return_when=FIRST_COMPLETED)
            for f in finished:
                f.result()                            # surface any error
            if time.time() - last_write > 30:
                with state:
                    write_outputs(P, progress, order, args.comments)
                last_write = time.time()
            if args.max and counts["done"] >= args.max and not stopping.is_set():
                stopping.set()                        # let the ones running finish
                reached_max = True
        pool.shutdown(wait=True)
    except KeyboardInterrupt:
        stopping.set()
        prog.close()
        with state:
            write_outputs(P, progress, order, args.comments)
        try:
            write_report(P)
        except Exception:
            pass
        print("\nPaused. Run the same command to carry on from here.")
        os._exit(0)                       # don't wait for replies still being written
    prog.close()
    if GATE["tuner"]:
        GATE["tuner"].stop.set()
    write_outputs(P, progress, order, args.comments)
    try:
        ghidra.write_callgraph(P.callgraph, {e["ghidra"]: e["name"] for e in done.values()
                                             if e.get("name") and e["name"] != e["ghidra"]})
    except Exception:
        pass
    mins = (time.time() - t_start) / 60
    plog(P, f"  this run: {counts['done']} function(s) rewritten in {fmt_duration(mins * 60)}")
    if reached_max:
        plog(P, f"  reached --max {args.max}; stopping here. Run the same command to continue.")
    return _rewrite_summary(progress, order, stop=reached_max, model=model)


def _rewrite_summary(progress, order, stop=False, model=None) -> dict:
    fs = progress.get("functions", {})
    es = [fs[k] for k in order if k in fs]
    done = [e for e in es if e.get("status") == "done"]
    reasons: dict[str, int] = {}
    for e in done:
        for r in e.get("suspect") or []:
            r = re.sub(r"^\d+ of \d+ parts", "some parts", r)
            reasons[r] = reasons.get(r, 0) + 1
    out = {"functions": len(order), "done": len(done),
           "stale": sum(1 for e in done if e.get("stale")),
           "skipped": sum(1 for e in es if e.get("status") == "skipped"),
           "too_big": sum(1 for e in es if e.get("status") == "too big"),
           "not_started": len(order) - len(es),
           "renamed": sum(1 for e in done if e.get("name") and e["name"] != e.get("ghidra")),
           "tiny": sum(1 for e in done if e.get("tiny")),
           "in_pieces": sum(1 for e in done if e.get("pieces")),
           "faithful": sum(1 for e in done if e.get("faithful")),
           "suspect": sum(1 for e in done if e.get("suspect")),
           "suspect_reasons": dict(sorted(reasons.items(), key=lambda t: -t[1])),
           "stop": stop}
    if model:
        out["model"] = model
    return out



# ============================================================================
# Stages: split / fix / recover / link  (the build)
# ============================================================================
# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------

@dataclass
class Config:
    input_file: Path
    workdir: Path
    cxx: str = "clang++"
    std: str = "c++17"
    # the shared model client, the model asked for (None: the loaded one), and the
    # one actually used once model_check() has run
    client: Optional[ModelClient] = None
    wanted_model: Optional[str] = None
    fix_model_used: Optional[str] = None
    model_temperature: float = 0.1
    model_max_tokens: int = 2048
    model_timeout_s: int = 180
    # fixer loop
    max_model_attempts: int = 3
    # libclang dylib path override (macOS Homebrew LLVM often needs this)
    libclang_path: Optional[str] = None
    # extra include dirs / compile flags for the real build
    extra_flags: list[str] = field(default_factory=list)
    # optional Ghidra call-graph export (json / csv / graphml). When set, used
    # for dependency ordering instead of the regex heuristic.
    callgraph_path: Optional[Path] = None
    # keep going even if the header gate / preflight says everything will fail
    force: bool = False
    # link step: stub every undefined symbol that has a prototype, not only
    # quarantined functions and Ghidra FUN_/DAT_ names
    stub_all: bool = False
    # pseudocode recovery: the export and the rewrite's name -> address index.
    # model_ctx_chars: prompt budget before a function is repaired by error-window
    # patching instead of a full rewrite.
    export_path: Optional[Path] = None
    index_path: Optional[Path] = None
    model_ctx_chars: int = 24000
    retry_quarantined: bool = False   # revive manifest quarantines for another pass
    no_pseudo: bool = False           # skip the pseudocode recovery stage
    # where files about to be replaced are copied first (None: don't)
    snapshot_dir: object = field(default_factory=lambda: (lambda: None))

    @property
    def funcs_dir(self) -> Path: return self.workdir / "funcs"
    @property
    def shared_h(self) -> Path: return self.workdir / "shared.h"
    @property
    def intrins_h(self) -> Path: return self.workdir / "ghidra_intrins.h"
    @property
    def globals_cpp(self) -> Path: return self.workdir / "globals.cpp"
    @property
    def manifest_path(self) -> Path: return self.workdir / "manifest.json"
    @property
    def cache_path(self) -> Path: return self.workdir / "fix_cache.json"
    @property
    def quarantine_dir(self) -> Path: return self.workdir / "quarantine"
    @property
    def log_path(self) -> Path: return self.workdir / "worklist.log"


# ----------------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------------

def log(cfg: Config, msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    sys.stdout.flush()
    with open(cfg.log_path, "a") as f:
        f.write(line + "\n")
        f.flush()
        os.fsync(f.fileno())


# ----------------------------------------------------------------------------
# Stage 0 — intrinsics header
# ----------------------------------------------------------------------------

GHIDRA_INTRINS_H = r"""#pragma once
// ghidra_intrins.h — typedefs + helpers to make Ghidra pseudocode-ish C++ compile.
#include <cstdint>
#include <cstring>

// --- Ghidra "undefined" width typedefs ---
typedef uint8_t   undefined;
typedef uint8_t   undefined1;
typedef uint16_t  undefined2;
typedef uint32_t  undefined4;
typedef uint64_t  undefined8;
typedef uint8_t   byte;
typedef uint16_t  word;
typedef uint32_t  dword;
typedef uint64_t  qword;
typedef unsigned int   uint;
typedef unsigned short ushort;
typedef unsigned char  uchar;
typedef unsigned long  ulong;

// --- CONCAT / SUB / ZEXT / SEXT family (common Ghidra pseudo-intrinsics) ---
// CONCATxy: concatenate an x-byte high part and a y-byte low part.
static inline uint16_t CONCAT11(uint8_t  h, uint8_t  l){ return (uint16_t(h)<<8)  | l; }
static inline uint32_t CONCAT22(uint16_t h, uint16_t l){ return (uint32_t(h)<<16) | l; }
static inline uint32_t CONCAT13(uint8_t  h, uint32_t l){ return (uint32_t(h)<<24) | (l & 0x00FFFFFFu); }
static inline uint32_t CONCAT31(uint32_t h, uint8_t  l){ return (uint32_t(h)<<8)  | l; }
static inline uint64_t CONCAT44(uint32_t h, uint32_t l){ return (uint64_t(h)<<32) | l; }
static inline uint64_t CONCAT17(uint8_t  h, uint64_t l){ return (uint64_t(h)<<56) | (l & 0x00FFFFFFFFFFFFFFull); }
static inline uint64_t CONCAT71(uint64_t h, uint8_t  l){ return (uint64_t(h)<<8)  | l; }

// SUBxy(value, byteOffset-ish): extract y low bytes after shifting. Ghidra's SUB
// means "take y bytes of an x-byte value". We approximate with masking helpers;
// the de-ghidra text pass rewrites the common SUBxy(v,0) forms to plain casts,
// so these are a safety net for the rarer offsets.
template<typename T> static inline uint8_t  SUB_u8 (T v){ return  (uint8_t)v;  }
template<typename T> static inline uint16_t SUB_u16(T v){ return (uint16_t)v; }
template<typename T> static inline uint32_t SUB_u32(T v){ return (uint32_t)v; }

static inline uint32_t ZEXT14(uint8_t  v){ return v; }
static inline uint32_t ZEXT24(uint16_t v){ return v; }
static inline uint64_t ZEXT18(uint8_t  v){ return v; }
static inline uint64_t ZEXT48(uint32_t v){ return v; }
static inline int32_t  SEXT14(int8_t   v){ return v; }
static inline int32_t  SEXT24(int16_t  v){ return v; }
static inline int64_t  SEXT48(int32_t  v){ return v; }
"""

# Standard headers the decompiled C++ leans on (std::string, ostream, exceptions,
# pthread types...). Included both when libclang parses the monolith and at the
# top of shared.h, so these types resolve instead of being dropped as unknown.
STD_INCLUDES = [
    "<cstdint>", "<cstddef>", "<cstring>", "<cstdlib>", "<cstdio>", "<cmath>",
    "<string>", "<vector>", "<map>", "<set>", "<list>", "<deque>", "<memory>",
    "<functional>", "<algorithm>", "<utility>", "<iostream>", "<ostream>",
    "<istream>", "<sstream>", "<fstream>", "<stdexcept>", "<exception>", "<new>",
    "<typeinfo>", "<locale>", "<mutex>", "<atomic>", "<pthread.h>",
]


def write_intrinsics(cfg: Config) -> None:
    cfg.intrins_h.write_text(GHIDRA_INTRINS_H)


# ----------------------------------------------------------------------------
# Stage 1 — Splitter (libclang two-pass)
# ----------------------------------------------------------------------------
#
# shared.h is now REBUILT from libclang's typed view of every declaration
# (struct fields, enum constants, typedef targets, globals, prototypes) instead
# of slicing raw source text. Every declaration is written as one "unit":
#
#     //@unit 42 record applyLowpassFilter6432
#     struct applyLowpassFilter6432 {
#         undefined8 field_0x0;
#         float coeff;
#     };
#
# The markers let the header repair step switch off a WHOLE declaration with
# #if 0 / #endif (or drop one single-line field inside a struct). It never
# comments out a lone line like `struct X {` or `};`, which is what used to
# leave a struct unclosed and swallow every prototype after it.

@dataclass
class FuncRecord:
    name: str            # spelling
    mangled: str         # mangled name -> filename key
    file: str            # relative path under funcs/
    start: int           # byte offset in monolith
    end: int             # byte offset in monolith
    compiles: bool = False
    quarantined: bool = False
    deps: list[str] = field(default_factory=list)   # mangled names of internal callees
    attempts: int = 0
    last_error: str = ""
    ghidra_addr: str = ""   # address from the //@ghidra marker, to find pseudocode
    rederived: bool = False # rebuilt from pseudocode by the recovery stage
    recovery: str = ""      # how it was recovered (rewrite / window-patch / faithful)
    recovery_tried: bool = False  # pseudocode recovery attempted and failed
    src_sha: str = ""       # hash of the function's code in the rewrite, at split time:
                            # tells a resume whether the rewrite changed this function


def _load_libclang(cfg: Config):
    import clang.cindex as cx
    if cx.Config.loaded:          # already set up earlier in this process
        return cx
    if cfg.libclang_path:
        cx.Config.set_library_file(cfg.libclang_path)
    else:
        # best-effort autodiscovery for common macOS/Linux locations
        for cand in (
            "/Library/Developer/CommandLineTools/usr/lib/libclang.dylib",
            "/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/lib/libclang.dylib",
            "/opt/homebrew/opt/llvm/lib/libclang.dylib",
            "/usr/local/opt/llvm/lib/libclang.dylib",
            "/usr/lib/llvm-18/lib/libclang.so.1",
            "/usr/lib/x86_64-linux-gnu/libclang-18.so.1",
        ):
            if os.path.exists(cand):
                cx.Config.set_library_file(cand)
                break
    return cx


def _libclang_args(cfg: Config) -> list[str]:
    """Args for libclang. Same std/include/extra flags as the real compile, and
    on macOS the SDK sysroot — without it libclang often can't find <cstdint>
    and silently turns every uint32_t etc. into `int`."""
    args = [f"-std={cfg.std}", f"-I{cfg.workdir}", "-x", "c++", *cfg.extra_flags]
    if sys.platform == "darwin" and not any(a.startswith("-isysroot") for a in args):
        try:
            sdk = subprocess.run(["xcrun", "--show-sdk-path"], capture_output=True,
                                 text=True, timeout=20).stdout.strip()
            if sdk:
                args += ["-isysroot", sdk]
        except Exception:
            pass
    return args


ANON_MARKERS = ("(unnamed", "(anonymous", "(lambda")
RECORD_KIND_NAMES = {"STRUCT_DECL", "CLASS_DECL", "UNION_DECL"}


def _is_anon_text(s: str) -> bool:
    return any(m in s for m in ANON_MARKERS)


def _anon(c) -> bool:
    return (not c.spelling) or _is_anon_text(c.spelling)


def _cmt(s: str) -> str:
    """Make arbitrary text safe inside a /* */ comment, on one line."""
    s = re.sub(r"\s+", " ", s).strip().replace("*/", "* /")
    return s[:140] + ("..." if len(s) > 140 else "")


class _ErrIndex:
    """Byte offsets of libclang ERROR diagnostics in the monolith, so a
    declaration whose text contains an error can be detected. libclang does NOT
    mark these types invalid — an unknown type name is silently reported as
    `int` — so this is the only reliable signal."""
    def __init__(self, tu, path: str):
        import bisect
        self._bisect = bisect
        items = sorted(
            (d.location.offset, d.spelling) for d in tu.diagnostics
            if d.severity >= 3 and d.location.file is not None
            and d.location.file.name == path)
        self.offs = [o for o, _ in items]
        self.msgs = [m for _, m in items]

    def within(self, c, ignore: Optional[re.Pattern] = None) -> bool:
        s, e = c.extent.start.offset, c.extent.end.offset
        i = self._bisect.bisect_left(self.offs, s)
        while i < len(self.offs) and self.offs[i] <= e:
            if ignore is None or not ignore.search(self.msgs[i]):
                return True
            i += 1
        return False


# errors that only say "this name is already defined" — expected for duplicate
# definitions, which get renamed instead of skipped
_DUP_DEF_ERR = re.compile(r"differ only in their return type|^redefinition of")


def _declarator(t, inner: str) -> str:
    """Build a C++ declaration of `inner` with type `t`, from libclang's type
    tree, so arrays and function pointers come out right:
    int[4] + 'x' -> 'int x[4]',  void(*)(int) + 'cb' -> 'void (*cb)(int)'."""
    k = t.kind.name
    if k in ("POINTER", "LVALUEREFERENCE", "RVALUEREFERENCE"):
        sym = {"POINTER": "*", "LVALUEREFERENCE": "&", "RVALUEREFERENCE": "&&"}[k]
        pointee = t.get_pointee()
        q = "const " if (k == "POINTER" and t.is_const_qualified()) else ""
        new = f"{sym}{q}{inner}"
        if pointee.kind.name in ("FUNCTIONPROTO", "FUNCTIONNOPROTO",
                                 "CONSTANTARRAY", "INCOMPLETEARRAY"):
            new = f"({new})"
        return _declarator(pointee, new)
    if k == "CONSTANTARRAY":
        return _declarator(t.element_type, f"{inner}[{t.element_count}]")
    if k == "INCOMPLETEARRAY":
        return _declarator(t.element_type, f"{inner}[]")
    if k in ("FUNCTIONPROTO", "FUNCTIONNOPROTO"):
        params = [a.spelling for a in t.argument_types()] if k == "FUNCTIONPROTO" else []
        if k == "FUNCTIONPROTO" and t.is_function_variadic():
            params.append("...")
        return _declarator(t.get_result(), f"{inner}({', '.join(params)})")
    base = t.spelling or "int"
    return f"{base} {inner}".strip() if inner else base


def _needs(t, by_value: bool, out: set, depth: int = 0) -> None:
    """Collect USRs of declarations that must appear BEFORE something using
    type `t`. Typedef names always (the name must exist); records only when
    used by value (pointers are covered by the forward-declaration block)."""
    if depth > 25:
        return
    k = t.kind.name
    try:
        if k == "TYPEDEF":
            u = t.get_declaration().get_usr()
            if u:
                out.add(u)
            if by_value:
                _needs(t.get_canonical(), True, out, depth + 1)
        elif k == "ELABORATED":
            _needs(t.get_named_type(), by_value, out, depth + 1)
        elif k == "RECORD":
            if by_value:
                u = t.get_declaration().get_usr()
                if u:
                    out.add(u)
        elif k in ("POINTER", "LVALUEREFERENCE", "RVALUEREFERENCE"):
            _needs(t.get_pointee(), False, out, depth + 1)
        elif k in ("CONSTANTARRAY", "INCOMPLETEARRAY"):
            _needs(t.element_type, by_value, out, depth + 1)
        elif k == "FUNCTIONPROTO":
            _needs(t.get_result(), False, out, depth + 1)
            for a in t.argument_types():
                _needs(a, False, out, depth + 1)
    except Exception:
        pass


@dataclass
class _Unit:
    kind: str               # fwd | record | enum | typedef | global | proto
    label: str
    lines: list[str]
    order: int
    provides: set = field(default_factory=set)
    needs: set = field(default_factory=set)


class _SplitStats:
    def __init__(self):
        self.notes: list[str] = []
        self.unresolved_fields = 0
        self.skipped: dict[str, int] = {}

    def skip(self, kind: str, what: str, why: str):
        self.skipped[kind] = self.skipped.get(kind, 0) + 1
        self.notes.append(f"skipped {kind} {what}: {why}")


def _enum_line(c, name: Optional[str]) -> str:
    under = c.enum_type.spelling or "int"
    try:
        scoped = c.is_scoped_enum()
    except Exception:
        scoped = False
    items = [f"{e.spelling} = {e.enum_value}" for e in c.get_children()
             if e.kind.name == "ENUM_CONSTANT_DECL"]
    head = "enum class" if scoped else "enum"
    nm = f" {name}" if name else ""
    return f"{head}{nm} : {under} {{ {', '.join(items)} }};"


def _method_line(m, err: "_ErrIndex", owner: str) -> Optional[str]:
    k = m.kind.name
    try:
        if k == "CONSTRUCTOR":
            params = ", ".join(a.spelling for a in m.type.argument_types())
            return f"{owner}({params});"
        if k == "DESTRUCTOR":
            v = "virtual " if m.is_virtual_method() else ""
            return f"{v}~{owner}();"
        # CXX_METHOD
        pre = ("static " if m.is_static_method() else "") + \
              ("virtual " if m.is_virtual_method() else "")
        post = (" const" if m.is_const_method() else "") + \
               (" = 0" if m.is_pure_virtual_method() else "")
        return f"{pre}{_declarator(m.type, m.spelling)}{post};"
    except Exception:
        return None


def _record_members(c, err: "_ErrIndex", stats: _SplitStats, needs: set,
                    provides: set) -> list[str]:
    """One string per member, each COMPLETE on a single line (nested records are
    written inline on one line). That guarantees any single interior line of a
    struct can be dropped without unbalancing braces."""
    owner = c.spelling
    out: list[str] = []
    children = list(c.get_children())

    # anonymous records that a field uses as its type (`struct { .. } inner;`)
    field_anon_decls = []
    for f in children:
        if f.kind.name == "FIELD_DECL":
            t = f.type
            while t.kind.name in ("CONSTANTARRAY", "INCOMPLETEARRAY"):
                t = t.element_type
            d = t.get_canonical().get_declaration()
            if d.kind.name in RECORD_KIND_NAMES and _anon(d):
                field_anon_decls.append(d)

    for m in children:
        k = m.kind.name
        if k == "FIELD_DECL":
            if err.within(m):
                stats.unresolved_fields += 1
                out.append(f"/* [unresolved field: unknown type] "
                           f"{_cmt(_raw(m))} */")
                continue
            name = m.spelling or ""
            d = _declarator(m.type, name)
            if _is_anon_text(d):
                # field of an anonymous record type -> write the record inline
                t, dims = m.type, ""
                while t.kind.name == "CONSTANTARRAY":
                    dims += f"[{t.element_count}]"
                    t = t.element_type
                rd = t.get_canonical().get_declaration()
                if rd.kind.name in RECORD_KIND_NAMES and _anon(rd):
                    out.append(f"{_record_inline(rd, err, stats, needs, provides)} {name}{dims};")
                else:
                    sz = m.type.get_size()
                    if sz and sz > 0:
                        out.append(f"uint8_t {name}[{sz}]; /* opaque: anonymous type */")
                    else:
                        out.append(f"/* [dropped field with anonymous type] {_cmt(_raw(m))} */")
                continue
            try:
                if m.is_bitfield():
                    d += f" : {m.get_bitfield_width()}"
            except Exception:
                pass
            _needs(m.type, True, needs)
            out.append(d + ";")
        elif k in RECORD_KIND_NAMES:
            if any(m == fd for fd in field_anon_decls):
                continue  # written inline with its field
            if not m.is_definition():
                if not _anon(m):
                    kw = "union" if k == "UNION_DECL" else "struct"
                    out.append(f"{kw} {m.spelling};")
                continue
            out.append(_record_inline(m, err, stats, needs, provides) + ";")
        elif k == "ENUM_DECL":
            if m.is_definition():
                out.append(_enum_line(m, None if _anon(m) else m.spelling))
        elif k in ("TYPEDEF_DECL", "TYPE_ALIAS_DECL"):
            if err.within(m):
                out.append(f"/* [unresolved typedef] {_cmt(_raw(m))} */")
                continue
            d = _declarator(m.underlying_typedef_type, m.spelling)
            if not _is_anon_text(d):
                _needs(m.underlying_typedef_type, False, needs)
                out.append(f"typedef {d};")
        elif k in ("CXX_METHOD", "CONSTRUCTOR", "DESTRUCTOR"):
            if err.within(m):
                out.append(f"/* [unresolved method] {_cmt(m.displayname)} */")
                continue
            line = _method_line(m, err, owner)
            if line and not _is_anon_text(line):
                _needs(m.type, False, needs)
                out.append(line)
        elif k == "VAR_DECL":  # static data member
            if not err.within(m):
                d = _declarator(m.type, m.spelling)
                if not _is_anon_text(d):
                    out.append(f"static {d};")
        elif k == "CXX_ACCESS_SPEC_DECL":
            try:
                out.append(m.access_specifier.name.lower() + ":")
            except Exception:
                pass
        # base specifiers handled by the caller; anything else is ignored
    return out


def _record_inline(c, err, stats, needs, provides) -> str:
    kw = "union" if c.kind.name == "UNION_DECL" else "struct"
    try:
        u = c.get_usr()
        if u:
            provides.add(u)
    except Exception:
        pass
    nm = "" if _anon(c) else f" {c.spelling}"
    members = _record_members(c, err, stats, needs, provides)
    return f"{kw}{nm} {{ {' '.join(members)} }}"


def _record_bases(c, err, needs) -> str:
    bases = []
    for b in c.get_children():
        if b.kind.name == "CXX_BASE_SPECIFIER" and not err.within(b):
            try:
                acc = b.access_specifier.name.lower()
                acc = acc if acc in ("public", "protected", "private") else "public"
            except Exception:
                acc = "public"
            bases.append(f"{acc} {b.type.spelling}")
            _needs(b.type, True, needs)
    return (" : " + ", ".join(bases)) if bases else ""


def _record_unit(c, err, stats, order: int, typedef_name: Optional[str] = None) -> _Unit:
    """Multi-line struct: header line, one member per line, closing line."""
    kw = "union" if c.kind.name == "UNION_DECL" else "struct"
    needs: set = set()
    provides: set = set()
    try:
        provides.add(c.get_usr())
    except Exception:
        pass
    members = _record_members(c, err, stats, needs, provides)
    bases = _record_bases(c, err, needs)
    if typedef_name:   # typedef of an anonymous struct
        lines = [f"typedef {kw}{bases} {{"] + ["    " + m for m in members] + [f"}} {typedef_name};"]
        label = typedef_name
    else:
        lines = [f"{kw} {c.spelling}{bases} {{"] + ["    " + m for m in members] + ["};"]
        label = c.spelling
    return _Unit("record", label, lines, order, provides, needs - provides)


_RAW_BYTES: bytes = b""


def _raw(c) -> str:
    return _RAW_BYTES[c.extent.start.offset:c.extent.end.offset].decode("utf-8", "replace")


def _top_level(tu, path: str):
    """Top-level cursors from the monolith itself, descending into extern "C"
    blocks (which the old splitter skipped entirely)."""
    for c in tu.cursor.get_children():
        if c.location.file is None or c.location.file.name != path:
            continue
        if c.kind.name == "LINKAGE_SPEC":
            for k in c.get_children():
                yield k
        else:
            yield c


def _order_units(units: list[_Unit]) -> list[_Unit]:
    """Source order, but anything a unit needs (a struct used by value, a
    typedef name) is moved ahead of it. Cycles fall back to source order."""
    by_usr: dict[str, _Unit] = {}
    for u in units:
        for p in u.provides:
            by_usr.setdefault(p, u)
    out: list[_Unit] = []
    done: set[int] = set()
    active: set[int] = set()

    def visit(u: _Unit):
        if id(u) in done or id(u) in active:
            return
        active.add(id(u))
        for n in sorted(u.needs):
            dep = by_usr.get(n)
            if dep is not None and dep is not u:
                visit(dep)
        active.discard(id(u))
        done.add(id(u))
        out.append(u)

    for u in sorted(units, key=lambda x: x.order):
        visit(u)
    return out


def _strip_leading_static(body: str, name: str) -> str:
    """Each function now lives in its own .cpp, so a `static` function would be
    invisible to its callers in other files. Drop `static` before the name."""
    i = body.find(name)
    if i <= 0:
        return body
    head = re.sub(r"\bstatic\b\s*", "", body[:i], count=1)
    return head + body[i:]


def write_shared_header(cfg: Config, fwd: list[_Unit], types: list[_Unit],
                        globs: list[_Unit], protos: list[_Unit]) -> None:
    out = ['#pragma once'] + [f"#include {h}" for h in STD_INCLUDES] + \
          ['#include "ghidra_intrins.h"', '']
    uid = 0

    def emit(section: str, units: list[_Unit]):
        nonlocal uid
        out.append(f"// ==== {section} ====")
        for u in units:
            uid += 1
            out.append(f"//@unit {uid} {u.kind} {u.label}")
            out.extend(u.lines)
        out.append("")

    emit("forward declarations", fwd)
    emit("type definitions", types)
    emit("extern globals", globs)
    emit("function prototypes", protos)
    cfg.shared_h.write_text("\n".join(out) + "\n")


def split_monolith(cfg: Config, tu_dir: Optional[Path] = None) -> dict[str, FuncRecord]:
    """tu_dir: where to write the per-function files (default funcs/). Resume
    writes them to a scratch folder and then decides file by file what to keep."""
    global _RAW_BYTES
    cx = _load_libclang(cfg)
    raw = cfg.input_file.read_bytes()

    # prepend the intrinsics include so libclang resolves the ghidra types
    # (we parse a version that includes the header, but slice from the ORIGINAL
    #  raw bytes — so offsets must account for the prefix).
    prefix = ("".join(f"#include {h}\n" for h in STD_INCLUDES)
              + '#include "ghidra_intrins.h"\n').encode()

    # A missing #include "x.h" is a FATAL error, and after a fatal error clang
    # stops reporting every later error — so unknown types further down would
    # silently become `int`. Neutralize missing project includes by turning
    # `#include` into `//nclude` (same byte length, so all offsets stay valid).
    search_dirs = [cfg.input_file.parent, cfg.workdir] + [
        Path(f[2:]) for f in cfg.extra_flags if f.startswith("-I") and len(f) > 2]
    neutralized = []

    def _fix_inc(m: re.Match) -> bytes:
        inc = m.group(2).decode("utf-8", "replace")
        if any((d / inc).exists() for d in search_dirs):
            return m.group(0)
        neutralized.append(inc)
        return m.group(1) + b"//nclude" + m.group(0)[len(m.group(1)) + len(b"#include"):]

    parse_raw = re.sub(rb'(?m)^([ \t]*)#include[ \t]*"([^"\n]+)"', _fix_inc, raw)
    assert len(parse_raw) == len(raw)
    if neutralized:
        log(cfg, f"  ignored {len(neutralized)} #include line(s) for files that don't "
                 f"exist (e.g. {', '.join(neutralized[:3])}) — they'd stop libclang "
                 f"from reporting any later errors")
    parse_bytes = prefix + parse_raw
    prefix_len = len(prefix)
    _RAW_BYTES = parse_bytes

    parse_path = str(cfg.workdir / "_parse_monolith.cpp")
    Path(parse_path).write_bytes(parse_bytes)

    args = _libclang_args(cfg)
    idx = cx.Index.create()
    stats = _SplitStats()

    # ---- Pass 1: declarations only (bodies skipped -> robust to broken funcs) ----
    opts1 = (cx.TranslationUnit.PARSE_INCOMPLETE
             | cx.TranslationUnit.PARSE_SKIP_FUNCTION_BODIES)
    tu1 = idx.parse(parse_path, args=args, options=opts1)
    err = _ErrIndex(tu1, parse_path)

    # Show what libclang itself couldn't understand — this is where silent
    # `int` substitutions come from.
    parse_errs = [d for d in tu1.diagnostics if d.severity >= 3]
    if parse_errs:
        lines = []
        for d in parse_errs:
            loc = d.location
            fname = Path(loc.file.name).name if loc.file else "?"
            lines.append(f"{fname}:{loc.line}: {d.spelling}")
        (cfg.workdir / "libclang_parse_errors.txt").write_text("\n".join(lines) + "\n")
        log(cfg, f"  libclang reported {len(parse_errs)} error(s) in the declarations "
                 f"(saved to libclang_parse_errors.txt), e.g.:")
        for ln in lines[:5]:
            log(cfg, f"    {ln[:180]}")
        # Only a missing SYSTEM header (#include <...>) means uint32_t etc. are
        # broken. A missing project header (#include "DAT_x.h") is just a stray
        # include in the monolith.
        src_lines = parse_bytes.decode("utf-8", "replace").splitlines()
        sys_missing = []
        for d in parse_errs:
            if "file not found" not in d.spelling:
                continue
            ln = d.location.line
            text = src_lines[ln - 1] if d.location.file and 0 < ln <= len(src_lines) else ""
            if "<" in text or d.location.file is None or d.location.file.name != parse_path:
                sys_missing.append(d.spelling)
        if sys_missing:
            log(cfg, "  !! libclang can't find a system header. Types like uint32_t "
                     "will be wrong. Point --libclang at Xcode's libclang.dylib or add "
                     "--flag=-isysroot --flag=\"$(xcrun --show-sdk-path)\"")

    fwd: list[_Unit] = []
    types: list[_Unit] = []
    globs: list[_Unit] = []
    protos: list[_Unit] = []
    seen_fwd: set[str] = set()
    seen_type: set[str] = set()
    seen_proto: set[str] = set()
    seen_global: set[str] = set()
    namespaces = 0
    order = 0
    def_counts: dict[tuple, int] = {}
    renames: dict[int, str] = {}   # parse offset of a definition -> new name

    for c in _top_level(tu1, parse_path):
        order += 1
        k = c.kind.name

        if k == "NAMESPACE":
            namespaces += 1
            continue

        if k in RECORD_KIND_NAMES:
            if _anon(c):
                continue  # emitted through its typedef / variable instead
            kw = "union" if k == "UNION_DECL" else "struct"
            if c.spelling not in seen_fwd:
                seen_fwd.add(c.spelling)
                fwd.append(_Unit("fwd", c.spelling, [f"{kw} {c.spelling};"], order))
            if not c.is_definition():
                continue
            key = "R:" + c.spelling
            if key in seen_type:
                stats.notes.append(f"duplicate struct {c.spelling}: kept first definition")
                continue
            seen_type.add(key)
            types.append(_record_unit(c, err, stats, order))

        elif k == "ENUM_DECL":
            if not c.is_definition():
                continue
            name = None if _anon(c) else c.spelling
            key = "E:" + (name or f"anon{order}")
            if key in seen_type:
                continue
            seen_type.add(key)
            u = _Unit("enum", name or "<anon enum>", [_enum_line(c, name)], order)
            try:
                u.provides.add(c.get_usr())
            except Exception:
                pass
            if name:
                try:
                    scoped = "enum class" if c.is_scoped_enum() else "enum"
                except Exception:
                    scoped = "enum"
                fwd.append(_Unit("fwd", name,
                                 [f"{scoped} {name} : {c.enum_type.spelling or 'int'};"], order))
            types.append(u)

        elif k in ("TYPEDEF_DECL", "TYPE_ALIAS_DECL"):
            name = c.spelling
            key = "T:" + name
            if key in seen_type:
                continue
            if err.within(c):
                stats.skip("typedef", name, "libclang could not resolve its type")
                continue
            under = c.underlying_typedef_type
            target = under
            while target.kind.name == "ELABORATED":
                target = target.get_named_type()
            tdecl = target.get_declaration()
            if (tdecl.kind.name in RECORD_KIND_NAMES and _anon(tdecl)
                    and tdecl.is_definition()):
                # typedef struct { ... } Name;  (older libclang leaves it unnamed)
                seen_type.add(key)
                u = _record_unit(tdecl, err, stats, order, typedef_name=name)
                try:
                    u.provides.add(c.get_usr())
                except Exception:
                    pass
                types.append(u)
                continue
            d = _declarator(under, name)
            if _is_anon_text(d):
                stats.skip("typedef", name, "refers to an anonymous type")
                continue
            seen_type.add(key)
            u = _Unit("typedef", name, [f"typedef {d};"], order)
            try:
                u.provides.add(c.get_usr())
            except Exception:
                pass
            _needs(under, False, u.needs)
            types.append(u)

        elif k == "FUNCTION_DECL":
            # pass 1 skips bodies, so libclang's is_definition() is always False
            # here; a definition is a declaration whose text ends in its body.
            is_def = (c.is_definition()
                      or _RAW_BYTES[c.extent.end.offset:c.extent.end.offset + 400]
                      .lstrip()[:1] in (b"{", b":"))
            if err.within(c, ignore=_DUP_DEF_ERR if is_def else None):
                stats.skip("prototype", c.spelling,
                           "its signature uses a type libclang could not resolve")
                continue
            fname_out = c.spelling
            if is_def:
                # The rewrite reused names (theFunctionName x30...). Two
                # definitions with the same name AND same parameters can't both
                # exist in C++ ("differ only in return type" / duplicate symbol),
                # so later copies get a unique name. Different parameter lists
                # are legal overloads and are left alone.
                try:
                    params = tuple(a.spelling for a in c.type.argument_types())
                except Exception:
                    params = ()
                dkey = (c.spelling, params)
                n = def_counts.get(dkey, 0)
                def_counts[dkey] = n + 1
                if n:
                    fname_out = f"{c.spelling}__dup{n}"
                    renames[c.extent.start.offset] = fname_out
                    stats.notes.append(f"renamed duplicate definition {c.spelling}"
                                       f"({', '.join(params)}) -> {fname_out}")
            proto = _declarator(c.type, fname_out) + ";"
            try:
                if c.lexical_parent is not None and c.lexical_parent.kind.name == "LINKAGE_SPEC":
                    proto = 'extern "C" ' + proto
            except Exception:
                pass
            if _is_anon_text(proto):
                stats.skip("prototype", c.spelling, "uses an anonymous type")
                continue
            pkey = re.sub(r"\s+", " ", proto)
            if pkey in seen_proto:
                continue
            seen_proto.add(pkey)
            protos.append(_Unit("proto", fname_out, [proto], order))

        elif k == "CXX_METHOD":
            # out-of-line `Foo::bar` definitions: declared inside struct Foo already
            continue

        elif k == "VAR_DECL":
            gname = c.spelling
            if not gname:
                continue
            if err.within(c):
                stats.skip("global", gname, "its type could not be resolved")
                continue
            decl = "extern " + _declarator(c.type, gname) + ";"
            if _is_anon_text(decl):
                stats.skip("global", gname, "has an anonymous type")
                continue
            gkey = re.sub(r"\s+", " ", decl)
            if gkey in seen_global:
                continue
            seen_global.add(gkey)
            globs.append(_Unit("global", gname, [decl], order))

    types = _order_units(types)
    write_shared_header(cfg, fwd, types, globs, protos)

    # ---- Pass 2: with bodies, to get exact function spans ----
    opts2 = cx.TranslationUnit.PARSE_INCOMPLETE
    tu2 = idx.parse(parse_path, args=args, options=opts2)

    records: dict[str, FuncRecord] = {}
    spans: list[tuple[int, int, str, str]] = []  # (start,end,name,mangled) in raw coords
    name_counts: dict[str, int] = {}

    for c in _top_level(tu2, parse_path):
        if c.kind.name not in ("FUNCTION_DECL", "CXX_METHOD") or not c.is_definition():
            continue
        s = c.extent.start.offset - prefix_len
        e = c.extent.end.offset - prefix_len
        if s < 0 or e <= s or e > len(raw):
            continue  # defensive: parse artifact, skip
        name = c.spelling or f"anon_{s}"
        mangled = c.mangled_name or name
        new = renames.get(c.extent.start.offset)
        if new:
            mangled = f"{mangled}__{new[len(name):].lstrip('_')}"
            name = new
        # disambiguate colliding mangled names (duplicate statics, etc.)
        if mangled in name_counts:
            name_counts[mangled] += 1
            mangled = f"{mangled}__{name_counts[mangled]}"
        else:
            name_counts[mangled] = 0
        spans.append((s, e, name, mangled))

    # ---- Reconciliation guard: spans must be sane & non-overlapping ----
    spans.sort(key=lambda t: t[0])
    clean_spans: list[tuple[int, int, str, str]] = []
    last_end = -1
    overlaps = 0
    for (s, e, name, mangled) in spans:
        if s < last_end:
            overlaps += 1
            log(cfg, f"  ! overlap: {name} ({s}:{e}) starts before previous end {last_end} — quarantining span")
            continue
        clean_spans.append((s, e, name, mangled))
        last_end = e

    if overlaps:
        log(cfg, f"  reconciliation: {overlaps} overlapping span(s) dropped to manual bucket")

    # ---- Emit per-function TUs ----
    tu_dir = tu_dir or cfg.funcs_dir
    tu_dir.mkdir(parents=True, exist_ok=True)
    include_line = '#include "shared.h"\n\n'
    # positions of every //@ghidra <addr> marker, to tag each function with the
    # address its pseudocode lives under (written by the rewrite stage)
    markers = [(m.start(), m.group(1)) for m in
               re.finditer(rb"//@ghidra\s+([0-9a-fA-F]+)\b", raw)]
    marker_offs = [p for p, _ in markers]
    import bisect
    prev_end = 0
    for (s, e, name, mangled) in clean_spans:
        body = raw[s:e].decode("utf-8", "replace")
        m_dup = re.match(r"^(.*)__dup\d+$", name)
        if m_dup:   # rename the definition itself to match its new prototype
            body = re.sub(rf"\b{re.escape(m_dup.group(1))}\b(?=\s*\()", name, body, count=1)
        body = _strip_leading_static(body, name)
        safe = re.sub(r"[^A-Za-z0-9_]", "_", mangled)[:120]
        fname = f"{safe}.cpp"
        (tu_dir / fname).write_text(include_line + body + "\n")
        i = bisect.bisect_left(marker_offs, s) - 1   # nearest marker before this func
        # only this function's own marker counts: it must sit between the previous
        # function and this one, not be a leftover from an unmarked gap
        addr = markers[i][1].decode() if i >= 0 and marker_offs[i] >= prev_end else ""
        prev_end = e
        records[mangled] = FuncRecord(
            name=name, mangled=mangled, file=f"funcs/{fname}",
            start=s, end=e, ghidra_addr=addr,
            src_sha=hashlib.sha1(raw[s:e]).hexdigest()[:16],
        )

    # ---- globals.cpp (file-scope definitions) ----
    glob_lines = [include_line, "// ==== global definitions ===="]
    gnames = seen_global_names(globs)
    gid = 0
    for c in _top_level(tu2, parse_path):
        if c.kind.name == "VAR_DECL" and c.is_definition() and c.spelling in gnames:
            s = c.extent.start.offset - prefix_len
            e = c.extent.end.offset - prefix_len
            if 0 <= s < e <= len(raw):
                text = raw[s:e].decode("utf-8", "replace").rstrip()
                text = _strip_leading_static(text, c.spelling)
                if not text.endswith(";"):
                    text += ";"
                gid += 1
                glob_lines.append(f"//@unit {gid} global {c.spelling}")
                glob_lines.append(text)
    cfg.globals_cpp.write_text("\n".join(glob_lines) + "\n")

    # ---- report ----
    rep = [f"unresolved struct fields (unknown type, left as comments): {stats.unresolved_fields}"]
    for kind, n in sorted(stats.skipped.items()):
        rep.append(f"skipped {kind}s: {n}")
    rep.append("")
    rep += stats.notes
    (cfg.workdir / "split_report.txt").write_text("\n".join(rep) + "\n")

    n_types = sum(1 for u in types)
    log(cfg, f"  split -> {len(records)} function TUs, {n_types} types "
             f"(+{len(fwd)} forward decls), {len(protos)} prototypes, {len(globs)} globals")
    if stats.unresolved_fields or stats.skipped:
        sk = ", ".join(f"{n} {k}s" for k, n in sorted(stats.skipped.items())) or "nothing"
        log(cfg, f"  {stats.unresolved_fields} struct field(s) with unknown types left as "
                 f"comments; skipped {sk} — details in split_report.txt")
    if renames:
        log(cfg, f"  renamed {len(renames)} duplicate function definition(s) to unique "
                 f"names (e.g. theFunctionName__dup1) — listed in split_report.txt")
    if namespaces:
        log(cfg, f"  note: {namespaces} top-level namespace block(s) were not split "
                 f"(functions inside namespaces are not handled yet)")
    return records


def seen_global_names(globs: list[_Unit]) -> set[str]:
    return {u.label for u in globs}

# ----------------------------------------------------------------------------
# Stage 2 — Per-TU de-ghidra text cleanup (safe transforms)
# ----------------------------------------------------------------------------

DEGHIDRA_SUBS: list[tuple[str, str]] = [
    # calling-convention junk
    (r"\b__fastcall\b", ""),
    (r"\b__cdecl\b", ""),
    (r"\b__thiscall\b", ""),
    (r"\b__stdcall\b", ""),
    # SUBxy(v,0) -> cast to the low width (the common, safe case)
    (r"\bSUB84\s*\(([^,]+),\s*0\s*\)", r"(uint32_t)(\1)"),
    (r"\bSUB84\s*\(([^,]+),\s*4\s*\)", r"(uint32_t)((\1)>>32)"),
    (r"\bSUB164\s*\(([^,]+),\s*0\s*\)", r"(uint32_t)(\1)"),
    (r"\bSUB41\s*\(([^,]+),\s*0\s*\)", r"(uint8_t)(\1)"),
    (r"\bSUB42\s*\(([^,]+),\s*0\s*\)", r"(uint16_t)(\1)"),
    (r"\bSUB21\s*\(([^,]+),\s*0\s*\)", r"(uint8_t)(\1)"),
]

# phantom register/unaffected variables Ghidra emits with no real definition
PHANTOM_VAR_RE = re.compile(r"\b((?:unaff_|in_|extraout_|unique0x)[A-Za-z0-9_]+)\b")


def deghidra_text(src: str) -> str:
    out = src
    for pat, repl in DEGHIDRA_SUBS:
        out = re.sub(pat, repl, out)
    # declare phantom vars locally as 0-initialized so the TU at least compiles;
    # these get flagged for review (they indicate incomplete lifting).
    phantoms = sorted(set(PHANTOM_VAR_RE.findall(out)))
    if phantoms:
        decls = "".join(f"    uint64_t {p} = 0; // TODO: phantom var (incomplete lift)\n"
                        for p in phantoms)
        # insert after the first '{' of the function body
        idx = out.find("{")
        if idx != -1:
            out = out[:idx+1] + "\n" + decls + out[idx+1:]
    return out


def apply_deghidra_pass(cfg: Config, records: dict[str, FuncRecord]) -> None:
    changed = 0
    for rec in records.values():
        p = cfg.workdir / rec.file
        src = p.read_text()
        new = deghidra_text(src)
        if new != src:
            p.write_text(new)
            changed += 1
    log(cfg, f"  de-ghidra text pass touched {changed} TU(s)")


# ----------------------------------------------------------------------------
# Stage 3 — Isolated compile sweep + diagnostics
# ----------------------------------------------------------------------------

# Position-independent code: default on macOS; on Linux it has to be passed,
# and the PCH is only accepted when every compile uses the same setting.
PIC_FLAGS: list[str] = [] if sys.platform == "darwin" else ["-fPIC"]


def _pch_path(cfg: Config) -> Path:
    return cfg.workdir / "shared.h.pch"


def build_pch(cfg: Config) -> bool:
    """Precompile shared.h once. With the standard-library includes, parsing the
    header is ~85% of each function's compile time; the PCH skips that."""
    cmd = [cfg.cxx, f"-std={cfg.std}", f"-I{cfg.workdir}", "-w", *PIC_FLAGS,
           "-x", "c++-header", *cfg.extra_flags, str(cfg.shared_h),
           "-o", str(_pch_path(cfg))]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        _pch_path(cfg).unlink(missing_ok=True)
        log(cfg, "  (precompiled header failed to build — compiling without it, slower)")
        return False
    return True


def _pch_flags(cfg: Config) -> list[str]:
    """Use the PCH only if it's at least as new as shared.h (the header can be
    repaired mid-run); rebuild it once if it's stale."""
    pch = _pch_path(cfg)
    try:
        if not pch.exists() or pch.stat().st_mtime < cfg.shared_h.stat().st_mtime:
            if not build_pch(cfg):
                return []
        return ["-include-pch", str(pch)]
    except OSError:
        return []


def compile_tu(cfg: Config, rel_path: str) -> tuple[bool, str, list[dict]]:
    """Compile one TU with -fsyntax-only. Returns (ok, raw_stderr, diags).
    (The old version passed -fdiagnostics-format=json, which is a GCC-only flag:
    clang rejects it, so EVERY function was reported as failing.)"""
    src = cfg.workdir / rel_path
    cmd = [cfg.cxx, f"-std={cfg.std}", f"-I{cfg.workdir}",
           "-fsyntax-only", "-w", "-ferror-limit=20", *PIC_FLAGS,
           *_pch_flags(cfg), *cfg.extra_flags, str(src)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode == 0, proc.stderr, []


def _compile_header_human(cfg: Config, header_rel: str) -> tuple[bool, str]:
    """Compile a header alone with human-format diagnostics (regex-parseable)."""
    src = cfg.workdir / header_rel
    # -ferror-limit=0: report every error in one pass. -w: errors only.
    lang = ["-x", "c++-header"] if header_rel.endswith(".h") else [*_pch_flags(cfg)]
    cmd = [cfg.cxx, f"-std={cfg.std}", f"-I{cfg.workdir}",
           "-fsyntax-only", "-ferror-limit=0", "-w", *PIC_FLAGS, *lang,
           *cfg.extra_flags, str(src)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode == 0, proc.stderr


DIAG_RE = re.compile(r"^(?P<file>.+?):(?P<line>\d+):(?P<col>\d+):\s*"
                     r"(?P<sev>fatal error|error|warning|note):\s*(?P<msg>.*)$")
UNIT_RE = re.compile(r"^//@unit (\d+) (\w+) ?(.*)$")


def _parse_units(lines: list[str]) -> list[dict]:
    """Find the //@unit blocks in shared.h. Each unit's content runs from the
    line after its marker up to the next marker / section line."""
    units = []
    i, n = 0, len(lines)
    while i < n:
        m = UNIT_RE.match(lines[i])
        if not m:
            i += 1
            continue
        j = i + 1
        while j < n and not UNIT_RE.match(lines[j]) and not lines[j].startswith("// ===="):
            j += 1
        end = j
        while end > i + 1 and not lines[end - 1].strip():
            end -= 1
        units.append({"uid": m.group(1), "kind": m.group(2), "label": m.group(3),
                      "start": i, "end": end})   # content = lines[start+1:end]
        i = j
    return units


def _unit_at(units: list[dict], idx: int) -> Optional[dict]:
    lo, hi = 0, len(units) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        u = units[mid]
        if idx < u["start"]:
            hi = mid - 1
        elif idx >= u["end"]:
            lo = mid + 1
        else:
            return u if idx > u["start"] else None
    return None


def repair_header(cfg: Config, header_rel: str, max_iter: int = 60) -> bool:
    """Make shared.h compile by switching off broken DECLARATIONS, never by
    commenting out arbitrary lines.

      - error on a single field line inside a struct  -> drop just that field
      - any other error inside a declaration          -> wrap the whole
                                                          declaration in #if 0
      - "to match this '{'" pointing into a decl       -> whole declaration

    Disabled structs stay usable through pointers because every struct also
    has a `struct X;` in the forward-declaration block. Everything removed is
    listed in header_repair_report.txt. Returns True once the header compiles."""
    hpath = cfg.workdir / header_rel
    hname = Path(header_rel).name
    report_path = cfg.workdir / ("header_repair_report.txt" if hname.endswith(".h")
                                 else f"{Path(hname).stem}_repair_report.txt")
    report: list[str] = []
    dropped_fields = 0
    disabled_units = 0
    last_err = ""

    for _ in range(max_iter):
        ok, err = _compile_header_human(cfg, header_rel)
        last_err = err
        if ok:
            if report:
                report_path.write_text("\n".join(report) + "\n")
                log(cfg, f"  {hname}: repaired — disabled {disabled_units} "
                         f"declaration(s), dropped {dropped_fields} struct field(s) "
                         f"(list in {report_path.name})")
            return True

        lines = hpath.read_text().splitlines()
        units = _parse_units(lines)
        field_drops: dict[int, str] = {}
        unit_disables: dict[str, tuple[dict, str]] = {}
        foreign: list[str] = []

        for raw_ln in err.splitlines():
            m = DIAG_RE.match(raw_ln.strip())
            if not m:
                continue
            sev, msg = m.group("sev"), m.group("msg")
            is_brace_note = sev == "note" and "to match this" in msg
            if "error" not in sev and not is_brace_note:
                continue
            if Path(m.group("file")).name != hname:
                if "error" in sev:
                    foreign.append(raw_ln.strip())
                continue
            idx = int(m.group("line")) - 1
            u = _unit_at(units, idx)
            if u is None:
                if "error" in sev:
                    foreign.append(raw_ln.strip())
                continue
            first, last = u["start"] + 1, u["end"] - 1
            interior = (u["kind"] == "record" and first < idx < last
                        and not is_brace_note
                        and not lines[idx].lstrip().startswith(("//", "/*", "#")))
            if interior:
                field_drops.setdefault(idx, msg)
            else:
                unit_disables.setdefault(u["uid"], (u, msg))

        if not field_drops and not unit_disables:
            break   # nothing we can attribute to a declaration -> can't repair

        for idx, msg in field_drops.items():
            u = _unit_at(units, idx)
            if u and u["uid"] in unit_disables:
                continue
            report.append(f"dropped field in {u['label'] if u else '?'}: "
                          f"{lines[idx].strip()}   <- {msg}")
            lines[idx] = f"    // [dropped: {msg[:80]}] {lines[idx].strip()}"
            dropped_fields += 1

        for u, msg in sorted(unit_disables.values(), key=lambda t: -t[0]["start"]):
            s, e = u["start"], u["end"]
            if s + 1 < len(lines) and lines[s + 1].startswith("#if 0"):
                continue
            report.append(f"disabled {u['kind']} {u['label']}   <- {msg}")
            lines.insert(e, "#endif")
            lines.insert(s + 1, f"#if 0 // [disabled: {msg[:100]}]")
            disabled_units += 1

        hpath.write_text("\n".join(lines) + "\n")

    if report:
        report_path.write_text("\n".join(report) + "\n")
    (cfg.workdir / "header_errors.txt").write_text(last_err)
    log(cfg, f"  header {hname}: could not be made to compile.")
    shown = 0
    for ln in last_err.splitlines():
        if "error" in ln:
            log(cfg, f"    | {ln[:200]}")
            shown += 1
            if shown >= 8:
                break
    log(cfg, f"  (full compiler output saved to header_errors.txt)")
    return False


def validate_headers(cfg: Config) -> bool:
    """Gate: both generated headers must compile before the per-TU sweep, or
    every function fails identically."""
    ok_intr, err = _compile_header_human(cfg, "ghidra_intrins.h")
    if not ok_intr:
        (cfg.workdir / "header_errors.txt").write_text(err)
        log(cfg, "  ghidra_intrins.h itself does not compile — this is the script's "
                 "own header, so it's a toolchain/flag problem. First lines:")
        for ln in err.strip().splitlines()[:6]:
            log(cfg, f"    | {ln[:200]}")
        return False
    if not repair_header(cfg, "shared.h"):
        return False
    build_pch(cfg)
    # globals.cpp: definitions whose extern was disabled, duplicates, unknown
    # types... switch those off too so the final link isn't blocked by them.
    if not repair_header(cfg, "globals.cpp"):
        log(cfg, "  (globals.cpp still has errors — the link step will report them)")
    return True


def header_implicated(stderr: str) -> bool:
    """True if a TU's failure originates in a shared header rather than its own
    body — including an unclosed '{' in the header that clang only notices at
    the end of the function file."""
    return bool(re.search(
        r"(shared\.h|ghidra_intrins\.h):\d+:\d+:\s*(?:(?:fatal\s+)?error|note: to match this)",
        stderr))


def preflight_diagnose(cfg: Config, records: dict[str, FuncRecord]) -> bool:
    """Compile the first handful of TUs with full (human) diagnostics. If they
    ALL fail, the cause is systemic (shared header / missing include / bad flag),
    and rewriting 5063 bodies would be hours of wasted work that can't fix it.
    Surface the real error loudly and save it so it's not guesswork.
    Returns True if the failure looks systemic."""
    sample = list(records.values())[:20]
    if not sample:
        return False
    first_fail_err = None
    n_fail = 0
    for rec in sample:
        src = cfg.workdir / rec.file
        # -w so the sample shows ERRORS, not the wall of harmless warnings
        cmd = [cfg.cxx, f"-std={cfg.std}", f"-I{cfg.workdir}",
               "-fsyntax-only", "-w", "-ferror-limit=5", *PIC_FLAGS, *_pch_flags(cfg),
               *cfg.extra_flags, str(src)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            n_fail += 1
            if first_fail_err is None:
                first_fail_err = (rec, proc.stderr)
    if n_fail == len(sample) and first_fail_err:
        rec, err = first_fail_err
        (cfg.workdir / "first_error.txt").write_text(err)
        log(cfg, "  " + "!"*58)
        log(cfg, f"  SYSTEMIC FAILURE: all {len(sample)} sampled TUs fail.")
        log(cfg, "  This is a shared cause (header / include / flag), NOT per-function.")
        log(cfg, "  The fixer loop canNOT fix this by rewriting bodies. Real error below:")
        log(cfg, "  " + "-"*58)
        for ln in err.strip().splitlines()[:18]:
            log(cfg, "  | " + ln[:200])
        log(cfg, "  " + "-"*58)
        log(cfg, f"  (full text saved to {cfg.workdir/'first_error.txt'})")
        log(cfg, "  " + "!"*58)
        return True
    elif n_fail:
        log(cfg, f"  preflight: {n_fail}/{len(sample)} sampled TUs fail — looks "
                 f"per-function, proceeding to full sweep + fixer")
    else:
        log(cfg, "  preflight: sampled TUs compile — proceeding")
    return False


def compile_sweep(cfg: Config, records: dict[str, FuncRecord]) -> None:
    from concurrent.futures import ThreadPoolExecutor
    ok_n = 0
    total = len(records)
    t0 = time.time()
    _pch_flags(cfg)   # build the PCH once before the workers start
    workers = max(1, (os.cpu_count() or 2) - 1)
    log(cfg, f"  compiling with {workers} parallel worker(s)")
    recs = list(records.values())
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = pool.map(lambda r: compile_tu(cfg, r.file), recs)
        paired = zip(recs, results)
        for i, (rec, (ok, err, _)) in enumerate(paired, 1):
            _sweep_record(rec, ok, err)
            if ok:
                ok_n += 1
            if i % 100 == 0 or i == total:
                rate = i / max(time.time() - t0, 0.001)
                eta = (total - i) / max(rate, 0.001)
                log(cfg, f"    compiled {i}/{total} ({ok_n} pass) "
                         f"~{rate:.0f}/s, eta {eta:.0f}s")
    log(cfg, f"  isolated compile: {ok_n}/{len(records)} TUs pass, "
             f"{len(records)-ok_n} need repair")


def _sweep_record(rec: FuncRecord, ok: bool, err: str) -> None:
    rec.compiles = ok
    if not ok:
        rec.last_error = err[-4000:]


# ----------------------------------------------------------------------------
# Dependency ordering
# ----------------------------------------------------------------------------

def import_callgraph(cfg: Config) -> Optional[dict[str, list[str]]]:
    """Load a Ghidra-exported call graph as {caller_name: [callee_names]}.

    Accepts three formats, chosen by extension / sniffed content:
      .json     -> {"caller": ["callee", ...], ...}
      .csv/.tsv -> edge list, one 'caller,callee' (or caller<TAB>callee) per line
      .graphml  -> Ghidra graph export; node id->label map + <edge source target>
    Names are function spellings as they appear in Ghidra (e.g. FUN_00401abc),
    which match the 'name' we stored per record.
    """
    p = cfg.callgraph_path
    if not p or not p.exists():
        return None
    text = p.read_text()
    ext = p.suffix.lower()
    graph: dict[str, list[str]] = {}

    try:
        if ext == ".json" or text.lstrip().startswith("{"):
            data = json.loads(text)
            for caller, callees in data.items():
                graph.setdefault(caller, [])
                for c in (callees or []):
                    if c and c != caller:
                        graph[caller].append(c)

        elif ext in (".csv", ".tsv") or ("," in text and "<" not in text[:200]):
            sep = "\t" if ext == ".tsv" else ","
            for line in text.splitlines():
                line = line.strip()
                if not line or line.lower().startswith(("caller", "source", "#")):
                    continue
                parts = [x.strip() for x in line.split(sep)]
                if len(parts) >= 2 and parts[0] and parts[1]:
                    caller, callee = parts[0], parts[1]
                    if callee != caller:
                        graph.setdefault(caller, []).append(callee)

        elif ext == ".graphml" or "<graphml" in text[:500].lower():
            # Minimal GraphML parse: node id -> label, then edges by id.
            import xml.etree.ElementTree as ET
            root = ET.fromstring(text)
            ns = {"g": "http://graphml.graphdrawing.org/xmlns"}
            # Map any node id to a human label if a <data> holds one, else the id.
            id_to_name: dict[str, str] = {}
            for node in root.iter():
                if node.tag.endswith("node"):
                    nid = node.get("id", "")
                    label = nid
                    for d in node:
                        if d.tag.endswith("data") and (d.text or "").strip():
                            label = d.text.strip()
                            break
                    id_to_name[nid] = label
            for edge in root.iter():
                if edge.tag.endswith("edge"):
                    s = id_to_name.get(edge.get("source", ""), edge.get("source", ""))
                    t = id_to_name.get(edge.get("target", ""), edge.get("target", ""))
                    if s and t and s != t:
                        graph.setdefault(s, []).append(t)
        else:
            log(cfg, f"  callgraph: unrecognized format for {p.name}, ignoring")
            return None
    except Exception as e:
        log(cfg, f"  callgraph: failed to parse {p.name} ({e}); falling back to heuristic")
        return None

    # de-dup callee lists
    for k in graph:
        graph[k] = sorted(set(graph[k]))
    edges = sum(len(v) for v in graph.values())
    log(cfg, f"  callgraph imported: {len(graph)} callers, {edges} edges from {p.name}")
    return graph


def build_dep_order(cfg: Config, records: dict[str, FuncRecord]) -> list[str]:
    """Dependency order, leaves first. Uses an imported Ghidra call graph when
    available (exact), otherwise a regex heuristic over source text.
    Returns mangled names leaves-first. Cycles are broken arbitrarily."""
    name_to_mangled: dict[str, str] = {}
    for m, r in records.items():
        name_to_mangled.setdefault(r.name, m)

    imported = import_callgraph(cfg)

    if imported is not None:
        matched = 0
        unmatched_names: set[str] = set()
        for m, r in records.items():
            callees = imported.get(r.name)
            if callees is None:
                # no entry for this function in the export -> fall back to regex
                # for just this function so ordering still has signal.
                src = (cfg.workdir / r.file).read_text()
                calls = set(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", src))
                r.deps = [name_to_mangled[c] for c in calls
                          if c in name_to_mangled and name_to_mangled[c] != m]
                continue
            deps = []
            for c in callees:
                cm = name_to_mangled.get(c)
                if cm and cm != m:
                    deps.append(cm)
                elif c not in name_to_mangled:
                    unmatched_names.add(c)
            r.deps = deps
            matched += 1
        if unmatched_names:
            log(cfg, f"  callgraph: {len(unmatched_names)} callee name(s) not in our "
                     f"TU set (external/library calls) — ignored for ordering")
        log(cfg, f"  callgraph: exact deps for {matched}/{len(records)} functions")
    else:
        for m, r in records.items():
            src = (cfg.workdir / r.file).read_text()
            calls = set(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", src))
            r.deps = [name_to_mangled[c] for c in calls
                      if c in name_to_mangled and name_to_mangled[c] != m]

    # topological sort (leaves first), tolerant of cycles
    visited: set[str] = set()
    order: list[str] = []
    temp: set[str] = set()

    def visit(m: str):
        if m in visited or m in temp:
            return
        temp.add(m)
        for d in records[m].deps:
            if d in records:
                visit(d)
        temp.discard(m)
        visited.add(m)
        order.append(m)

    for m in records:
        visit(m)
    return order


# ----------------------------------------------------------------------------
# Context slicing for the model
# ----------------------------------------------------------------------------

ERR_SYMBOL_RE = re.compile(r"'([A-Za-z_][A-Za-z0-9_:<>~ ]*)'")

def extract_error_symbols(stderr: str) -> list[str]:
    syms = []
    for m in ERR_SYMBOL_RE.findall(stderr):
        s = m.strip()
        if s and s not in syms:
            syms.append(s)
    return syms[:20]


def gather_declarations(cfg: Config, symbols: list[str]) -> str:
    """Pull just the declaration lines for named symbols from shared.h."""
    header = cfg.shared_h.read_text().splitlines()
    picked: list[str] = []
    for sym in symbols:
        base = re.split(r"[:<]", sym)[0].strip()
        if not base:
            continue
        for line in header:
            if re.search(rf"\b{re.escape(base)}\b", line) and line.strip().endswith(";"):
                if line not in picked:
                    picked.append(line.strip())
    return "\n".join(picked[:60])


# ----------------------------------------------------------------------------
# Deterministic / templated repair (no model)
# ----------------------------------------------------------------------------

def templated_fix(cfg: Config, rel_path: str, stderr: str) -> bool:
    """Apply mechanical fixes for common diagnostics. Returns True if it changed."""
    src_path = cfg.workdir / rel_path
    src = src_path.read_text()
    orig = src

    # implicit function declaration -> the prototype is in shared.h already;
    # usually means a spelling/namespace issue. Skip (model handles).
    # missing ';' before '}' style — clang usually recovers; skip.

    # "use of undeclared identifier 'X'": a Ghidra local (uVar1, local_28,
    # unaff_x...) the rewrite used but never declared -> declare it at the top
    # of the function. Names used as calls are functions, not variables, and
    # are left for the model. (The old check skipped any variable that was
    # assigned somewhere, i.e. most of them.)
    body_open = src.find("{")
    for m in sorted(set(re.findall(
            r"use of undeclared identifier '([A-Za-z_][A-Za-z0-9_]*)'", stderr))):
        if re.search(rf"\b{re.escape(m)}\s*\(", src):
            continue
        if body_open != -1 and not re.search(rf"\b(uint64_t|auto)\s+{re.escape(m)}\b", src):
            decl = f"\n    uint64_t {m} = 0; // auto-declared (undeclared in the rewrite)\n"
            src = src[:body_open + 1] + decl + src[body_open + 1:]

    if src != orig:
        src_path.write_text(src)
        return True
    return False


# ----------------------------------------------------------------------------
# LM Studio slice repair
# ----------------------------------------------------------------------------

REPAIR_SYSTEM = (
    "You are a C++ repair tool for decompiled code. You receive ONE function that "
    "fails to compile, the exact compiler errors, and the declarations of the "
    "types and functions the errors reference. Fix ONLY the compile errors. "
    "Preserve the function's logic and signature exactly. Do not invent new "
    "behavior, do not add includes, do not rename the function. Return ONLY the "
    "corrected function body as a single C++ code block, nothing else."
)

MODEL_STATS = {"calls": 0, "no_answer": 0, "rejected": 0}


def model_check(cfg: Config) -> bool:
    """Is the model server up, and which model does this stage use? Checked at the
    start of each stage, so a model swapped in between stages is picked up.
    Without this, a stopped server made every model call fail silently and the
    fixer quarantined thousands of functions."""
    if cfg.client is None:
        return False
    try:
        cfg.fix_model_used = cfg.client.resolve(cfg.wanted_model)
    except ModelError as e:
        log(cfg, f"  {e}")
        return False
    log(cfg, f"  {cfg.client.name} OK — repairing with {cfg.fix_model_used}")
    return True


def _fix_chat(cfg: Config, system: str, user: str, max_tokens: int) -> Optional[str]:
    """One fix/recover request. None when there's no usable answer (the caller
    then moves on: quarantine, or the next strategy)."""
    if cfg.fix_model_used is None and not model_check(cfg):
        cfg.fix_model_used = ""            # don't ask again for every function
    if not cfg.fix_model_used:
        return None
    return cfg.client.chat(cfg.fix_model_used,
                           [{"role": "system", "content": system},
                            {"role": "user", "content": user}],
                           max_out=max_tokens, temperature=cfg.model_temperature,
                           timeout=cfg.model_timeout_s, fatal=False)


def _accept_model_fix(name: str, original: str, fixed: str) -> Optional[str]:
    """Reject 'fixes' that make the compile error go away by deleting the
    problem: dropping/renaming the function or gutting most of its body. For
    vulnerability work a function that compiles but lost its logic is worse
    than one that is quarantined and flagged."""
    if name and not re.search(rf"\b{re.escape(name.split('::')[-1])}\s*\(", fixed):
        return f"model output no longer defines {name}"
    if "{" not in fixed or fixed.count("{") != fixed.count("}"):
        return "model output is not a complete function"
    orig_len = len(re.sub(r"\s+", "", original))
    new_len = len(re.sub(r"\s+", "", fixed))
    if orig_len > 300 and new_len < 0.4 * orig_len:
        return f"model output is {new_len * 100 // max(orig_len, 1)}% of the original size (gutted)"
    return None


def model_repair(cfg: Config, func_src: str, stderr: str, decls: str,
                 name: str = "") -> Optional[str]:
    user = (
        f"// Compiler errors:\n{stderr[-2500:]}\n\n"
        f"// Relevant declarations (for reference, do not redefine):\n{decls}\n\n"
        f"// Function to fix:\n{func_src}"
    )
    MODEL_STATS["calls"] += 1
    content = _fix_chat(cfg, REPAIR_SYSTEM, user, cfg.model_max_tokens)
    if content is None:
        MODEL_STATS["no_answer"] += 1
        return None
    # extract the code block (also when the closing fence got cut off)
    m = re.search(r"```(?:cpp|c\+\+|c)?\s*(.*?)```", content, re.DOTALL)
    if m:
        code = m.group(1)
    elif "```" in content:
        code = re.sub(r"^.*?```(?:cpp|c\+\+|c)?\s*", "", content, count=1, flags=re.DOTALL)
    else:
        code = content
    # the header already provides includes; keep the TU consistent
    code = "\n".join(l for l in code.splitlines()
                     if not l.lstrip().startswith("#include")).strip()
    if not code:
        MODEL_STATS["no_answer"] += 1
        return None
    why = _accept_model_fix(name, func_src, code)
    if why:
        MODEL_STATS["rejected"] += 1
        log(cfg, f"      rejected model fix for {name or '?'}: {why}")
        return None
    return code


# ----------------------------------------------------------------------------
# Fix cache
# ----------------------------------------------------------------------------

def load_cache(cfg: Config) -> dict:
    if cfg.cache_path.exists():
        return json.loads(cfg.cache_path.read_text())
    return {}

def save_cache(cfg: Config, cache: dict) -> None:
    cfg.cache_path.write_text(json.dumps(cache, indent=0))

def cache_key(src: str, err: str) -> str:
    h = hashlib.sha256()
    h.update(src.encode()); h.update(b"||"); h.update(err[-1000:].encode())
    return h.hexdigest()[:24]


# ----------------------------------------------------------------------------
# Stage 4 — Fixer loop
# ----------------------------------------------------------------------------

def quarantine(cfg: Config, rec: FuncRecord) -> None:
    cfg.quarantine_dir.mkdir(parents=True, exist_ok=True)
    src = cfg.workdir / rec.file
    dst = cfg.quarantine_dir / Path(rec.file).name
    shutil.copy(src, dst)
    # replace the TU with a compilable stub so the build can progress
    stub = (f'#include "shared.h"\n\n'
            f'// QUARANTINED: {rec.name} — could not be repaired automatically.\n'
            f'// Original saved at quarantine/{Path(rec.file).name}\n')
    src.write_text(stub)
    rec.quarantined = True
    log(cfg, f"  QUARANTINE {rec.name}: {rec.last_error.splitlines()[-1] if rec.last_error else '?'}")


def repair_tu(cfg: Config, rec: FuncRecord, cache: dict) -> bool:
    """Drive one TU to compile. Returns True if it compiles, False if quarantined."""
    rel = rec.file
    header_fix_tries = 0
    for attempt in range(cfg.max_model_attempts + 1):
        ok, err, _ = compile_tu(cfg, rel)
        if ok:
            rec.compiles = True
            return True
        rec.last_error = err[-4000:]

        # 0) if this failure comes from a shared header, fix the HEADER, not the
        #    body — otherwise we rewrite a fine function that can never pass.
        if header_implicated(err) and header_fix_tries < 2:
            header_fix_tries += 1
            log(cfg, f"      {rec.name}: failure originates in a shared header — "
                     f"repairing header, not the function")
            repair_header(cfg, "shared.h")
            continue

        # 1) templated / deterministic
        if templated_fix(cfg, rel, err):
            continue

        # 2) cache
        src = (cfg.workdir / rel).read_text()
        key = cache_key(src, err)
        if key in cache:
            (cfg.workdir / rel).write_text(cache[key])
            ok2, _, _ = compile_tu(cfg, rel)
            if ok2:
                rec.compiles = True
                return True

        # 3) model slice repair
        if attempt >= cfg.max_model_attempts:
            break
        # keep only the function body (strip the #include line we prepended)
        body = re.sub(r'^\s*#include\s+"shared.h"\s*', "", src, count=1).strip()
        decls = gather_declarations(cfg, extract_error_symbols(err))
        fixed = model_repair(cfg, body, err, decls, rec.name)
        rec.attempts += 1
        if fixed:
            (cfg.workdir / rel).write_text('#include "shared.h"\n\n' + fixed + "\n")
            ok3, err3, _ = compile_tu(cfg, rel)
            if ok3:
                cache[key] = (cfg.workdir / rel).read_text()
                save_cache(cfg, cache)
                rec.compiles = True
                return True
            rec.last_error = err3[-4000:]

    quarantine(cfg, rec)
    return False


def fixer_loop(cfg: Config, records: dict[str, FuncRecord], order: list[str]) -> None:
    cache = load_cache(cfg)
    failing = [m for m in order if m in records and not records[m].compiles
               and not records[m].quarantined]
    total = len(failing)
    log(cfg, f"  fixer loop over {total} failing TU(s), dependency-ordered")
    t0 = time.time()
    fixed_n = 0
    for i, m in enumerate(failing, 1):
        rec = records[m]
        log(cfg, f"    [{i}/{total}] {rec.name} ...")   # heartbeat before each (model calls are slow)
        ok = repair_tu(cfg, rec, cache)
        if ok:
            fixed_n += 1
        elapsed = time.time() - t0
        rate = i / max(elapsed, 0.001)
        eta = (total - i) / max(rate, 0.001)
        log(cfg, f"    [{i}/{total}] {rec.name} -> "
                 f"{'fixed' if ok else 'quarantined'} "
                 f"({fixed_n} fixed so far, eta {eta:.0f}s)")
        if i % 25 == 0:
            # this loop can run for hours; save so --resume picks up from here
            save_manifest(cfg, records)
    save_cache(cfg, cache)
    if MODEL_STATS["calls"]:
        log(cfg, f"  model: {MODEL_STATS['calls']} call(s), {MODEL_STATS['no_answer']} "
                 f"without a usable answer, {MODEL_STATS['rejected']} rejected as "
                 f"unsafe (dropped/gutted the function)")
    done = sum(1 for r in records.values() if r.compiles)
    q = sum(1 for r in records.values() if r.quarantined)
    log(cfg, f"  fixer loop done: {done} compiling, {q} quarantined")


# ----------------------------------------------------------------------------
# Stage 5 — Link pass
# ----------------------------------------------------------------------------

GHIDRA_AUTONAME_RE = re.compile(r"^(FUN_|DAT_|PTR_|thunk_|LAB_|SUB_|switchD_|caseD_|s_|u_)")


def _demangle_all(cfg: Config, syms: list[str]) -> dict[str, str]:
    """Raw linker symbol -> readable name. macOS adds a leading underscore to
    every symbol; C++ ones are then demangled with c++filt."""
    out: dict[str, str] = {}
    to_dm: list[str] = []
    for s in syms:
        t = s
        if sys.platform == "darwin" and t.startswith("_") and not t.startswith("_Z") \
                and "(" not in t:
            t = t[1:]
        out[s] = t
        if t.startswith("_Z"):
            to_dm.append(t)
    if to_dm:
        try:
            pr = subprocess.run(["c++filt"], input="\n".join(to_dm), capture_output=True,
                                text=True, timeout=60)
            dm = pr.stdout.splitlines()
            if len(dm) == len(to_dm):
                table = dict(zip(to_dm, dm))
                for s, t in out.items():
                    if t in table:
                        out[s] = table[t]
        except Exception:
            pass
    return out


def _parse_link_errors(err: str) -> tuple[list[str], list[tuple[str, str]]]:
    """Returns (undefined symbols, [(duplicate symbol, text block)]) for
    macOS ld64/ld-prime, GNU ld and lld output."""
    undefined: list[str] = []
    for pat in (r'^\s*"(.+?)", referenced from:',            # macOS
                r"undefined reference to [`'](.+?)'",          # GNU ld
                r"undefined symbol: (.+?)\s*$"):               # lld
        for m in re.finditer(pat, err, re.M):
            sym = m.group(1).strip()
            if sym and sym not in undefined:
                undefined.append(sym)
    dups: list[tuple[str, str]] = []
    for pat in (r"duplicate symbol '(.+?)' in:",                # macOS
                r"multiple definition of [`'](.+?)'",           # GNU ld
                r"duplicate symbol: (.+?)\s*$"):                # lld
        for m in re.finditer(pat, err, re.M):
            dups.append((m.group(1).strip(), err[max(0, m.start() - 300): m.end() + 600]))
    return undefined, dups


def _enabled_header_lines(cfg: Config) -> list[tuple[str, str, str]]:
    """(kind, label, line) for every declaration still enabled in shared.h."""
    lines = cfg.shared_h.read_text().splitlines()
    out = []
    for u in _parse_units(lines):
        body = lines[u["start"] + 1:u["end"]]
        if not body or body[0].startswith("#if 0"):
            continue
        if u["kind"] in ("proto", "global") and len(body) == 1:
            out.append((u["kind"], u["label"], body[0].strip()))
    return out


def _stub_for(kind: str, line: str, name: str) -> Optional[str]:
    """Turn a prototype / extern line from shared.h into a placeholder
    definition that returns / holds a zero value."""
    if kind == "global":
        if not line.startswith("extern ") or line.startswith('extern "C"'):
            return None
        return line[len("extern "):].rstrip(";").rstrip() + "{};"
    decl = line.rstrip(";").rstrip()
    head = decl[:decl.find(name + "(")] if (name + "(") in decl else ""
    if re.search(r"&\s*$", head):
        return None            # returns a reference: no safe placeholder
    if re.match(r'^(extern "C"\s+)?void\s+$', head):
        return decl + " {}"
    return decl + " { return {}; }"


# ----------------------------------------------------------------------------
# Stage 4b — recover quarantined functions from their Ghidra pseudocode
# ----------------------------------------------------------------------------
#
# A quarantined function compiled on its own in pseudo_to_cpp.py (against invented
# declarations) but not against the shared header. Instead of leaving it stubbed,
# go back to the SOURCE — Ghidra's pseudocode — and rewrite it to compile against
# shared.h, with a real compile check. Three strategies, in order:
#   (a) full rewrite from pseudocode + the shared.h declarations it needs
#   (b) error-window patching (for functions too big for one prompt): fix only
#       the lines around each compile error, a window at a time
#   (c) faithful fallback: make Ghidra's own pseudocode compile (ugly but true)
# A function that comes through is marked rederived, not silently "fixed".

PSEUDO_SYSTEM = (
    "You rewrite ONE function from a decompiler's pseudocode into C++ that compiles "
    "as part of an existing program. The program already defines its types, globals "
    "and the other functions — their declarations are given to you, and you MUST use "
    "them instead of redefining them. Rules: keep the behaviour exactly as in the "
    "pseudocode (same conditions, loops, arithmetic, calls, return values); do not "
    "invent logging, printing or error handling; keep the function's name and "
    "signature EXACTLY as in the provided prototype; do not add #include lines or "
    "redefine any provided type/global/function; turn Ghidra artifacts (undefined4, "
    "CONCAT/SUB/ZEXT, param_1, local_28, uVarN, DAT_x) into ordinary C++. Reply with "
    "ONLY the one function as a single ```cpp code block."
)

_PSEUDO_CACHE: dict = {}


def _load_pseudocode(cfg: Config) -> tuple[dict, dict]:
    """(address -> pseudocode, final-name -> {ghidra,addr}). Loaded once."""
    key = str(cfg.workdir)
    if key in _PSEUDO_CACHE:
        return _PSEUDO_CACHE[key]
    export, index = {}, {}
    try:
        data = json.loads(Path(cfg.export_path).read_text())
        export = data.get("pseudocode", {}) or {}
    except Exception:
        export = {}
    try:
        index = json.loads(Path(cfg.index_path).read_text()) or {}
    except Exception:
        index = {}
    _PSEUDO_CACHE[key] = (export, index)
    return export, index


def _pseudo_for(rec: FuncRecord, export: dict, index: dict) -> Optional[str]:
    addr = rec.ghidra_addr
    if not addr:
        base = re.sub(r"__dup\d+$", "", rec.name)
        addr = (index.get(rec.name) or index.get(base) or {}).get("addr", "")
    code = export.get(addr) if addr else None
    return code or None


def _proto_for(cfg: Config, name: str) -> Optional[str]:
    base = re.sub(r"__dup\d+$", "", name)
    for _, label, line in _enabled_header_lines(cfg):
        if label in (name, base):
            return line
    return None


def _idents(text: str) -> list[str]:
    seen, out = set(), []
    for m in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text):
        if m not in seen:
            seen.add(m)
            out.append(m)
    return out


def _decls_for(cfg: Config, text: str, extra: str = "") -> str:
    syms = _idents(text)[:80] + extract_error_symbols(extra)
    return gather_declarations(cfg, syms)


def _post_chat(cfg: Config, system: str, user: str, max_tokens: int) -> Optional[str]:
    content = _fix_chat(cfg, system, user, max_tokens)
    if content is None:
        return None
    m =re.search(r"```(?:cpp|c\+\+|c)?\s*(.*?)```", content, re.DOTALL)
    code = m.group(1) if m else content
    code = "\n".join(l for l in code.splitlines()
                     if not l.lstrip().startswith("#include")).strip()
    return code or None


def _write_and_compile(cfg: Config, rec: FuncRecord, body: str) -> tuple[bool, str]:
    (cfg.workdir / rec.file).write_text('#include "shared.h"\n\n' + body + "\n")
    ok, err, _ = compile_tu(cfg, rec.file)
    return ok, err


def _rename_defined_func(src: str, newname: str) -> str:
    i = src.find("{")
    if i < 0:
        return src
    head = src[:i]
    m = re.search(r"([A-Za-z_]\w*)\s*\(", head)
    if not m:
        return src
    return head[:m.start(1)] + newname + head[m.end(1):] + src[i:]


def _recover_full_rewrite(cfg: Config, rec: FuncRecord, pseudo: str,
                          proto: str, orig_body: str) -> Optional[str]:
    decls = _decls_for(cfg, pseudo)
    user = (f"// Target prototype (keep this name and signature):\n{proto}\n\n"
            f"// Declarations already provided by the program (use, do not redefine):\n"
            f"{decls}\n\n// Ghidra pseudocode of the function to rewrite:\n{pseudo}")
    for attempt in range(cfg.max_model_attempts):
        fixed = _post_chat(cfg, PSEUDO_SYSTEM, user, cfg.model_max_tokens)
        if not fixed:
            return None
        # compare against the decompiled body (not the verbose pseudocode) so a
        # legitimately concise rewrite isn't mistaken for a gutted one
        why = _accept_model_fix(rec.name, orig_body or pseudo, fixed)
        if why:
            return None
        ok, err = _write_and_compile(cfg, rec, fixed)
        if ok:
            return fixed
        user = (f"// That did not compile. Compiler errors:\n{err[-1800:]}\n\n"
                f"// Target prototype:\n{proto}\n\n// Declarations:\n{decls}\n\n"
                f"// Pseudocode:\n{pseudo}")
    return None


def _recover_window_patch(cfg: Config, rec: FuncRecord, pseudo: str,
                          rounds: int = 6) -> bool:
    """For functions too big for one prompt: fix the lines around the first
    compile error, recompile, repeat. The whole file stays on disk between rounds."""
    pseudo_slice = pseudo[:cfg.model_ctx_chars // 2]
    for _ in range(rounds):
        ok, err, _ = compile_tu(cfg, rec.file)
        if ok:
            return True
        mm = re.search(rf"{re.escape(Path(rec.file).name)}:(\d+):", err)
        if not mm:
            return False
        ln = int(mm.group(1))
        lines = (cfg.workdir / rec.file).read_text().splitlines()
        lo, hi = max(0, ln - 16), min(len(lines), ln + 15)
        window = "\n".join(lines[lo:hi])
        user = (f"// Part of a decompiled function that fails to compile against the "
                f"program's shared header.\n// Compiler errors:\n{err[-1200:]}\n\n"
                f"// The function's Ghidra pseudocode (reference):\n{pseudo_slice}\n\n"
                f"// Fix ONLY these lines (return the same lines, corrected, nothing "
                f"else):\n```cpp\n{window}\n```")
        fixed = _post_chat(cfg, PSEUDO_SYSTEM, user,
                           min(cfg.model_max_tokens, max(400, (hi - lo) * 24)))
        if not fixed or fixed.count("{") - fixed.count("}") != \
                window.count("{") - window.count("}"):
            return False   # would unbalance the braces: give up on this strategy
        lines[lo:hi] = fixed.splitlines()
        (cfg.workdir / rec.file).write_text("\n".join(lines) + "\n")
    ok, _, _ = compile_tu(cfg, rec.file)
    return ok


def _recover_faithful(cfg: Config, rec: FuncRecord, pseudo: str) -> bool:
    """Last resort: make Ghidra's own pseudocode compile against shared.h, with
    its name fixed to match the prototype. Ugly but faithful to the binary."""
    body = deghidra_text(_rename_defined_func(pseudo, re.sub(r"__dup\d+$", "", rec.name)))
    ok, _ = _write_and_compile(cfg, rec, body)
    return ok


def recover_one(cfg: Config, rec: FuncRecord, export: dict, index: dict) -> bool:
    pseudo = _pseudo_for(rec, export, index)
    if not pseudo:
        return False
    proto = _proto_for(cfg, rec.name)
    saved = (cfg.workdir / rec.file).read_text()   # current stub, to restore on failure
    # the original decompiled body (saved at quarantine time), used both as the
    # starting point for window patching and as the size reference for guards
    orig = cfg.quarantine_dir / Path(rec.file).name
    orig_text = orig.read_text() if orig.exists() else saved
    orig_body = re.sub(r'^\s*#include\s+"shared.h"\s*', "", orig_text, count=1).strip()

    big = len(pseudo) + len(orig_text) > cfg.model_ctx_chars
    # (a) full rewrite when it fits
    if proto and not big:
        fixed = _recover_full_rewrite(cfg, rec, pseudo, proto, orig_body)
        if fixed is not None:
            rec.recovery = "rewrite"
            return _finish_recovery(cfg, rec)

    # (b) error-window patching: start from the original decompiled body, which is
    # closer to correct than the stub
    (cfg.workdir / rec.file).write_text(orig_text)
    if _recover_window_patch(cfg, rec, pseudo):
        body = (cfg.workdir / rec.file).read_text()
        body = re.sub(r'^\s*#include\s+"shared.h"\s*', "", body, count=1).strip()
        if not _accept_model_fix(rec.name, orig_body, body):
            rec.recovery = "window-patch"
            return _finish_recovery(cfg, rec)

    # (c) faithful fallback
    if _recover_faithful(cfg, rec, pseudo):
        rec.recovery = "faithful-pseudocode"
        return _finish_recovery(cfg, rec)

    (cfg.workdir / rec.file).write_text(saved)   # restore the stub; stays quarantined
    rec.recovery_tried = True
    return False


def _finish_recovery(cfg: Config, rec: FuncRecord) -> bool:
    rec.compiles = True
    rec.quarantined = False
    rec.rederived = True
    return True


def pseudocode_recovery(cfg: Config, records: dict[str, FuncRecord]) -> None:
    if cfg.no_pseudo:
        return
    export, index = _load_pseudocode(cfg)
    if not export:
        log(cfg, f"  pseudocode recovery: no pseudocode in {cfg.export_path} — skipping")
        return
    targets = [m for m, r in records.items() if r.quarantined
               and (cfg.retry_quarantined or not r.recovery_tried)]
    if not targets:
        already = sum(1 for r in records.values() if r.quarantined and r.recovery_tried)
        if already:
            log(cfg, f"  pseudocode recovery: {already} quarantined function(s) already "
                     f"tried and skipped — use --retry-quarantined to try again "
                     f"(e.g. after loading a bigger model)")
        return
    have = sum(1 for m in targets if _pseudo_for(records[m], export, index))
    log(cfg, f"  pseudocode recovery: {len(targets)} quarantined, {have} have "
             f"pseudocode to rebuild from")
    if not have:
        return
    if not model_check(cfg):
        cfg.fix_model_used = ""
        log(cfg, "  (model not available — only the faithful fallback will run)")
    fixed_n, faithful_n, t0 = 0, 0, time.time()
    for i, m in enumerate(targets, 1):
        rec = records[m]
        if not _pseudo_for(rec, export, index):
            continue
        log(cfg, f"    [{i}/{len(targets)}] recovering {rec.name} from pseudocode ...")
        if recover_one(cfg, rec, export, index):
            fixed_n += 1
            if rec.recovery == "faithful-pseudocode":
                faithful_n += 1
            log(cfg, f"    [{i}/{len(targets)}] {rec.name} -> re-derived ({rec.recovery})")
        if i % 20 == 0:
            save_manifest(cfg, records)
    save_manifest(cfg, records)
    log(cfg, f"  pseudocode recovery: {fixed_n} re-derived "
             f"({faithful_n} as faithful pseudocode — review these), "
             f"{len(targets) - fixed_n} still quarantined. Took {time.time()-t0:.0f}s")
    rederived = [r.name for r in records.values() if r.rederived]
    if rederived:
        (cfg.workdir / "rederived.txt").write_text("\n".join(sorted(rederived)) + "\n")


def link_pass(cfg: Config, records: dict[str, FuncRecord]) -> bool:
    """Compile every TU to an object (parallel, incremental, with the PCH) and
    link a shared library. Problems are handled deterministically:

      - a TU that no longer compiles      -> fixer (model) or quarantine
      - globals.cpp / stubs.cpp errors     -> disable the broken definition
      - undefined function/global that this
        program owns (quarantined, or a
        Ghidra FUN_/DAT_ name) with a
        prototype in shared.h               -> placeholder in stubs.cpp
      - duplicate symbol                    -> keep the first, quarantine the rest
      - anything else (system frameworks)   -> reported in link_report.txt

    The model is never asked to fix "symbol not found": that can't be fixed by
    editing the caller, and the old loop quarantined innocent callers."""
    from concurrent.futures import ThreadPoolExecutor
    cache = load_cache(cfg)
    obj_dir = cfg.workdir / "obj"
    obj_dir.mkdir(exist_ok=True)
    stubs_cpp = cfg.workdir / "stubs.cpp"
    stubs: dict[str, str] = {}          # name -> stub definition
    report: list[str] = []
    if sys.platform == "darwin":
        out = cfg.workdir / "program.dylib"
        lib_flags = ["-dynamiclib"]
    else:
        out = cfg.workdir / "program.so"
        lib_flags = ["-shared", "-Wl,--no-undefined"]
    stem_to_rec = {Path(r.file).stem: m for m, r in records.items()}
    quarantined_names = lambda: {r.name for r in records.values() if r.quarantined}

    def write_stubs():
        body = ['#include "shared.h"', "", "// ==== placeholder definitions ====",
                "// Functions/globals that are referenced but have no recovered",
                "// definition. Each returns / holds zero. Review before trusting",
                "// any behaviour that depends on them."]
        for i, (nm, text) in enumerate(sorted(stubs.items()), 1):
            body += [f"//@unit {i} stub {nm}", text]
        stubs_cpp.write_text("\n".join(body) + "\n")

    # start from no placeholders: an earlier run's stubs could stand in for functions
    # that now compile (duplicate symbols); the rounds below add back what's needed
    write_stubs()

    def _obj(src: Path) -> tuple[Path, Path, str]:
        o = obj_dir / (src.stem + ".o")
        if o.exists() and o.stat().st_mtime >= max(src.stat().st_mtime,
                                                   cfg.shared_h.stat().st_mtime):
            return src, o, ""
        pch = _pch_flags(cfg)
        cmd = [cfg.cxx, f"-std={cfg.std}", f"-I{cfg.workdir}", "-w", "-c",
               *PIC_FLAGS, *pch, *cfg.extra_flags, str(src), "-o", str(o)]
        pr = subprocess.run(cmd, capture_output=True, text=True)
        if pr.returncode != 0 and pch:   # PCH/flag mismatch -> retry without
            pr = subprocess.run([x for x in cmd if x not in pch],
                                capture_output=True, text=True)
        if pr.returncode != 0:
            o.unlink(missing_ok=True)
        return src, o, ("" if pr.returncode == 0 else pr.stderr)

    workers = max(1, (os.cpu_count() or 2) - 1)
    err = ""
    for round_no in range(1, 16):
        _pch_flags(cfg)   # make sure the PCH is current before workers start
        sources = [cfg.workdir / r.file for r in records.values()] + [cfg.globals_cpp]
        if stubs_cpp.exists():
            sources.append(stubs_cpp)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            built = list(pool.map(_obj, sources))
        failed = [(src, e) for src, o, e in built if e]

        if failed:
            log(cfg, f"  link round {round_no}: {len(failed)} file(s) failed to compile")
            for src, e in failed:
                if src in (cfg.globals_cpp, stubs_cpp):
                    rel = src.name
                    if not repair_header(cfg, rel):
                        (cfg.workdir / "link_errors.txt").write_text(e)
                        log(cfg, f"  {rel} can't be repaired — see link_errors.txt")
                        return False
                    if src == stubs_cpp:   # forget stubs that were switched off
                        txt = stubs_cpp.read_text().splitlines()
                        for u in _parse_units(txt):
                            if txt[u["start"] + 1].startswith("#if 0"):
                                stubs.pop(u["label"], None)
                                report.append(f"stub for {u['label']} did not compile — removed")
                        write_stubs()
                    continue
                m = stem_to_rec.get(src.stem)
                if m is None:
                    continue
                rec = records[m]
                rec.compiles = False
                rec.last_error = e[-4000:]
                if not repair_tu(cfg, rec, cache):
                    report.append(f"quarantined {rec.name}: stopped compiling at link time")
            continue

        objs = [str(o) for _, o, _ in built]
        cmd = [cfg.cxx, *lib_flags, *PIC_FLAGS, *cfg.extra_flags, *objs, "-o", str(out)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            if stubs:
                log(cfg, f"  {len(stubs)} placeholder definition(s) in stubs.cpp "
                         f"(listed in link_report.txt)")
            (cfg.workdir / "link_report.txt").write_text("\n".join(report) + "\n")
            log(cfg, f"  LINK OK (round {round_no}) -> {out}")
            return True

        err = proc.stderr
        undefined, dups = _parse_link_errors(err)
        changed = False

        # --- duplicate symbols: keep the first definition, quarantine the rest
        for sym, block in dups:
            stems = sorted({Path(p).stem for p in re.findall(r"[^\s'`\"():]+\.o\b", block)}
                           & set(stem_to_rec))
            for stem in stems[1:]:
                rec = records[stem_to_rec[stem]]
                if not rec.quarantined:
                    rec.last_error = f"duplicate symbol {sym}"
                    quarantine(cfg, rec)
                    report.append(f"quarantined {rec.name}: duplicate definition of {sym} "
                                  f"(kept {records[stem_to_rec[stems[0]]].name})")
                    changed = True

        # --- undefined symbols: stub the ones this program owns
        names = _demangle_all(cfg, undefined)
        header = _enabled_header_lines(cfg)
        external: list[str] = []
        qnames = quarantined_names()
        for raw_sym in undefined:
            readable = names.get(raw_sym, raw_sym)
            if "::" in readable.split("(")[0]:
                external.append(readable)       # class method / namespaced: not stubbed
                continue
            base = readable.split("(")[0].strip()
            owned = base in qnames or bool(GHIDRA_AUTONAME_RE.match(base)) or cfg.stub_all
            if not owned or base in stubs:
                external.append(readable)
                continue
            cands = [(k, l) for k, lbl, l in header if lbl == base]
            if "(" in readable and len(cands) > 1:   # pick the matching overload
                want = re.sub(r"\s+", "", readable[readable.find("("):])
                exact = [(k, l) for k, l in cands
                         if re.sub(r"\s+", "", l[l.find(base + "(") + len(base):]
                                   ).rstrip(";").startswith(want)]
                cands = exact or cands[:1]
            stub = _stub_for(cands[0][0], cands[0][1], base) if cands else None
            if stub:
                stubs[base] = stub
                why = "quarantined" if base in qnames else "never defined"
                report.append(f"stubbed {readable} ({why})")
                changed = True
            else:
                external.append(readable)
        if changed:
            write_stubs()
            log(cfg, f"  link round {round_no}: {len(undefined)} undefined, {len(dups)} "
                     f"duplicate symbol(s) — stubbed/quarantined, relinking")
            continue

        # nothing left we can fix automatically
        (cfg.workdir / "link_errors.txt").write_text(err)
        report.append("")
        report.append(f"unresolved external symbols ({len(external)}):")
        report += [f"  {x}" for x in external]
        (cfg.workdir / "link_report.txt").write_text("\n".join(report) + "\n")
        if external:
            log(cfg, f"  link: {len(external)} undefined symbol(s) come from outside this "
                     f"code (system frameworks / libraries), e.g. {', '.join(external[:4])}")
            if sys.platform == "darwin":
                log(cfg, "  -> add the frameworks with --flag=-framework --flag=<Name>, or "
                         "let the dylib resolve them at load time with "
                         "--flag=-Wl,-undefined,dynamic_lookup")
            else:
                log(cfg, "  -> add the libraries with --flag=-l<name>")
            log(cfg, "     (or --stub-all-missing to stub anything that has a prototype)")
        else:
            log(cfg, "  link errors not handled automatically — see link_errors.txt")
        return False
    (cfg.workdir / "link_errors.txt").write_text(err)
    log(cfg, "  link pass hit round cap — see link_errors.txt")
    return False


# ----------------------------------------------------------------------------
# Manifest I/O
# ----------------------------------------------------------------------------

def save_manifest(cfg: Config, records: dict[str, FuncRecord]) -> None:
    data = {m: asdict(r) for m, r in records.items()}
    tmp = cfg.manifest_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(cfg.manifest_path)      # never leave a half-written manifest


def load_manifest(cfg: Config) -> dict[str, FuncRecord]:
    data = json.loads(cfg.manifest_path.read_text())
    known = set(FuncRecord.__dataclass_fields__)
    return {m: FuncRecord(**{k: v for k, v in r.items() if k in known})
            for m, r in data.items()}


# ----------------------------------------------------------------------------
# Run state + resume check
# ----------------------------------------------------------------------------
#
# build/build_state.json records which version of this script produced the split
# and which build steps finished. Every run checks that against what's on disk,
# so a build started with an OLDER version (or from an older rewrite) is updated
# in place: the header and globals are rebuilt, function files nobody touched are
# refreshed, functions the rewrite changed get the new code, files the model
# already fixed are kept, and old quarantines are retried.

SCRIPT_VERSION = "2026-10-18.1"   # bump when the split / header format changes


def _state_path(cfg: Config) -> Path:
    return cfg.workdir / "build_state.json"


def load_state(cfg: Config) -> dict:
    try:
        return json.loads(_state_path(cfg).read_text())
    except Exception:
        return {}


def save_state(cfg: Config, **updates) -> None:
    st = load_state(cfg)
    st.update(updates)
    st["version"] = SCRIPT_VERSION
    _state_path(cfg).write_text(json.dumps(st, indent=2))


def _input_sha(cfg: Config) -> str:
    return hashlib.sha256(cfg.input_file.read_bytes()).hexdigest()[:16]


def _untouched_variants(raw_body: str, name: str) -> set[str]:
    """Every way an earlier version of this script could have written a
    function's file before any fixing happened."""
    inc = '#include "shared.h"\n\n'
    bodies = {raw_body, _strip_leading_static(raw_body, name)}
    out = set()
    for b in bodies:
        t = inc + b + "\n"
        out.add(t)
        out.add(deghidra_text(t))
    return {re.sub(r"\s+", " ", v).strip() for v in out}


def reconcile_resume(cfg: Config, old: dict[str, FuncRecord]) -> dict[str, FuncRecord]:
    """Re-split the monolith with the current logic and merge it with the
    previous run's work, function by function."""
    raw = cfg.input_file.read_bytes()
    fresh_dir = cfg.workdir / "_fresh_funcs"
    if fresh_dir.exists():
        shutil.rmtree(fresh_dir)
    new = split_monolith(cfg, tu_dir=fresh_dir)

    old_by_start = {r.start: r for r in old.values()}
    counts = {"refreshed": 0, "kept": 0, "retry": 0, "new": 0, "changed": 0}
    to_deghidra: list[FuncRecord] = []
    cfg.funcs_dir.mkdir(parents=True, exist_ok=True)
    # read every old file first: a function's file can be renamed onto another's
    old_text: dict[str, Optional[str]] = {}
    for r in old.values():
        p = cfg.workdir / r.file
        old_text[r.file] = p.read_text() if p.exists() else None
    written: set[Path] = set()
    renamed_from: set[Path] = set()

    def keep_copy(rel_file: str, text: Optional[str]) -> None:
        """A fixed function file is about to be replaced: copy it to the snapshot."""
        d = cfg.snapshot_dir()
        if d is None or not text:
            return
        dest = d / "build" / rel_file
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text)

    for m, rec in new.items():
        fresh_text = (fresh_dir / Path(rec.file).name).read_text()
        target = cfg.workdir / rec.file
        written.add(target)
        # the same function in the old run: by its (mangled) name, else by position
        prev = old.get(m)
        if prev is None:
            prev = old_by_start.get(rec.start)
            if prev is not None and not (prev.name == rec.name
                                         or rec.name.startswith(prev.name + "__dup")):
                # same position but a different function: the input file was edited
                # since the old run, so its offsets no longer line up — don't carry
                # another function's code over
                prev = None
        if prev is None:
            target.write_text(fresh_text)
            to_deghidra.append(rec)
            counts["new"] += 1
            continue
        prev_path = cfg.workdir / prev.file
        if prev_path != target:
            renamed_from.add(prev_path)
        cur = old_text.get(prev.file)
        raw_body = raw[rec.start:rec.end].decode("utf-8", "replace")
        if prev.src_sha and prev.src_sha != rec.src_sha:
            # the rewrite changed this function (e.g. it was rewritten again):
            # take the new code; earlier fixes were for code that's gone
            if cur and "// QUARANTINED:" not in cur:
                keep_copy(prev.file, cur)
            target.write_text(fresh_text)
            to_deghidra.append(rec)
            counts["changed"] += 1
        elif prev.quarantined or cur is None or "// QUARANTINED:" in (cur or ""):
            # old quarantines happened against a broken/incomplete header:
            # restore the original code and let the fixer try again
            target.write_text(fresh_text)
            to_deghidra.append(rec)
            counts["retry"] += 1
        elif re.sub(r"\s+", " ", cur).strip() in _untouched_variants(raw_body, prev.name):
            target.write_text(fresh_text)      # nothing done to it yet: use new split
            to_deghidra.append(rec)
            counts["refreshed"] += 1
        else:
            # the fixer / model already changed this file: keep that work,
            # applying any rename the new split gave this function
            if rec.name != prev.name and rec.name.startswith(prev.name + "__dup"):
                cur = re.sub(rf"\b{re.escape(prev.name)}\b(?=\s*\()", rec.name, cur, count=1)
            target.write_text(cur)
            rec.attempts = prev.attempts
            rec.rederived, rec.recovery = prev.rederived, prev.recovery
            counts["kept"] += 1
    shutil.rmtree(fresh_dir)                   # this function's own scratch copies
    # files whose function moved to a new file name: their content was carried over
    # above. Moved out of funcs/ (not deleted), unless another function now uses it.
    leftovers = [p for p in renamed_from if p not in written and p.exists()
                 and p.parent == cfg.funcs_dir]
    if leftovers:
        dest = (cfg.snapshot_dir() or cfg.workdir / "funcs_unused") / "build" / "funcs_renamed"
        dest.mkdir(parents=True, exist_ok=True)
        for p in leftovers:
            shutil.move(str(p), str(dest / p.name))

    for rec in to_deghidra:
        p = cfg.workdir / rec.file
        p.write_text(deghidra_text(p.read_text()))

    log(cfg, f"    functions: {counts['changed']} changed in the rewrite (new code taken), "
             f"{counts['kept']} already fixed by the model (kept), "
             f"{counts['refreshed']} untouched (refreshed with the new split), "
             f"{counts['retry']} previously quarantined (restored for another try), "
             f"{counts['new']} not in the old run")
    if counts["changed"] and cfg.snapshot_dir() is not None:
        log(cfg, f"    (the replaced versions are in {cfg.snapshot_dir()})")
    return new


def _header_is_current(cfg: Config) -> bool:
    try:
        txt = cfg.shared_h.read_text()
    except OSError:
        return False
    return "//@unit " in txt and "#include <string>" in txt


# ----------------------------------------------------------------------------
# Orchestrator
# ----------------------------------------------------------------------------

def _gate_header(cfg: Config, records: dict[str, FuncRecord]) -> None:
    if not validate_headers(cfg):
        save_manifest(cfg, records)
        if not cfg.force:
            log(cfg, "STOPPED: shared.h does not compile, so every function would "
                     "fail and the model would rewrite thousands of fine functions "
                     "for nothing. See header_errors.txt. (--force to continue anyway)")
            sys.exit(2)
        log(cfg, "  --force: continuing despite broken header")
    save_state(cfg, header_ok=True)


def _sweep_all(cfg: Config, records: dict[str, FuncRecord]) -> None:
    log(cfg, f"Stage 2c: preflight diagnose (surface any systemic cause before "
             f"spending model time on {len(records)} functions)")
    if preflight_diagnose(cfg, records):
        save_manifest(cfg, records)
        if not cfg.force:
            log(cfg, "STOPPED: every sampled function fails for a shared reason "
                     "(see first_error.txt). Fix that first. (--force to continue anyway)")
            sys.exit(2)
    log(cfg, "Stage 3: isolated compile sweep")
    live = {m: r for m, r in records.items() if not r.quarantined}
    compile_sweep(cfg, live)
    save_manifest(cfg, records)
    save_state(cfg, sweep_done=True)


# ----------------------------------------------------------------------------
# Build stages (split / fix / recover / link)
# ----------------------------------------------------------------------------

def _set_aside_unused(cfg: Config, records: dict[str, FuncRecord]) -> None:
    """Function files left over from an earlier split that no function uses any
    more: moved out of funcs/ (into the snapshot, or funcs_unused/), never deleted."""
    used = {Path(r.file).name for r in records.values()}
    extra = [p for p in cfg.funcs_dir.glob("*.cpp") if p.name not in used]
    if not extra:
        return
    dest = (cfg.snapshot_dir() or cfg.workdir / "funcs_unused") / "build" / "funcs_unused"
    dest.mkdir(parents=True, exist_ok=True)
    for p in extra:
        shutil.move(str(p), str(dest / p.name))
    log(cfg, f"  moved {len(extra)} function file(s) no longer in the split to {dest}")


def build_split(cfg: Config, redo_split: bool) -> dict[str, FuncRecord]:
    """Stage 'split': split + de-ghidra + header gate + compile sweep, or carry on
    from (and update) an earlier build."""
    cfg.workdir.mkdir(parents=True, exist_ok=True)
    log(cfg, f"build {SCRIPT_VERSION} on {cfg.input_file}")
    write_intrinsics(cfg)

    if cfg.manifest_path.exists() and not redo_split:
        # ---------------- resume: check what's done, redo what's stale -------
        records = load_manifest(cfg)
        state = load_state(cfg)
        sha = _input_sha(cfg)
        log(cfg, f"Resume check ({len(records)} functions in manifest):")
        same_version = state.get("version") == SCRIPT_VERSION
        same_input = state.get("input_sha") in (None, sha)
        if not same_input:
            log(cfg, "  the rewrite changed since the last build — updating the split "
                     "(functions whose code changed get the new code; the others keep "
                     "their fixes)")
        files_missing = [r for r in records.values() if not (cfg.workdir / r.file).exists()]

        if not (same_version and same_input and _header_is_current(cfg)) or files_missing:
            why = ("made by an older version of this script" if not same_version
                   else "out of date" if same_input and not files_missing
                   else f"{len(files_missing)} function file(s) missing" if files_missing
                   else "input changed")
            log(cfg, f"  [redo] split + header: {why} — rebuilding shared.h/globals.cpp "
                     f"and merging with the work already done")
            records = reconcile_resume(cfg, records)
            _set_aside_unused(cfg, records)
            save_manifest(cfg, records)
            save_state(cfg, input_sha=sha, split_done=True, header_ok=False,
                       sweep_done=False)
            state = load_state(cfg)
        else:
            log(cfg, "  [ok]   split + header are current")

        if not state.get("header_ok") or not _compile_header_human(cfg, "shared.h")[0]:
            log(cfg, "  [redo] header check")
            log(cfg, "Stage 2b: validate/repair shared headers")
            _gate_header(cfg, records)
        else:
            log(cfg, "  [ok]   header compiles")
            _pch_flags(cfg)

        if not state.get("sweep_done"):
            log(cfg, "  [redo] compile status")
            _sweep_all(cfg, records)
        else:
            log(cfg, "  [ok]   compile sweep done")
    else:
        # ---------------- fresh split (first time, or --redo split/fix) -------
        # function files are overwritten in place; anything the earlier build had
        # was copied to a snapshot first (see run_pipeline)
        log(cfg, "Stage 1: split (parsing the whole file with libclang — "
                 "this can take a minute on a large monolith with no output; not stalled)")
        records = split_monolith(cfg)
        _set_aside_unused(cfg, records)
        save_state(cfg, input_sha=_input_sha(cfg), split_done=True,
                   header_ok=False, sweep_done=False)
        log(cfg, "Stage 2: de-ghidra text pass")
        apply_deghidra_pass(cfg, records)
        save_manifest(cfg, records)
        log(cfg, "Stage 2b: validate/repair shared headers (gate — a broken "
                 "header fails every TU identically)")
        _gate_header(cfg, records)
        _sweep_all(cfg, records)

    done = sum(1 for r in records.values() if r.compiles)
    quar = sum(1 for r in records.values() if r.quarantined)
    todo = sum(1 for r in records.values() if not r.compiles and not r.quarantined)
    log(cfg, f"  status: {done} compile, {todo} still to fix, {quar} quarantined")
    return records


def build_fix(cfg: Config, records: dict[str, FuncRecord]) -> None:
    n_failing = sum(1 for r in records.values() if not r.compiles and not r.quarantined)
    if not n_failing:
        log(cfg, "  nothing to fix")
        return
    if not model_check(cfg):
        save_manifest(cfg, records)
        if not cfg.force:
            log(cfg, f"STOPPED: {n_failing} function(s) need the model but it isn't "
                     f"available. Start the server, load a model and run the same command "
                     f"again (no re-split needed), or add --force to quarantine whatever "
                     f"the deterministic fixes can't handle.")
            sys.exit(2)
        log(cfg, "  --force: continuing without the model")
    log(cfg, "Stage 4: dependency order + fixer loop")
    order = build_dep_order(cfg, records)
    fixer_loop(cfg, records, order)
    save_manifest(cfg, records)


def build_recover(cfg: Config, records: dict[str, FuncRecord]) -> None:
    log(cfg, "Stage 4b: recover quarantined functions from Ghidra pseudocode")
    pseudocode_recovery(cfg, records)
    save_manifest(cfg, records)


def build_link(cfg: Config, records: dict[str, FuncRecord]) -> bool:
    log(cfg, "Stage 5: link pass")
    linked = link_pass(cfg, records)
    save_manifest(cfg, records)
    save_state(cfg, link_ok=linked)
    return linked


def build_summary(cfg: Config, records: dict[str, FuncRecord]) -> dict:
    out = {"functions": len(records),
           "compile": sum(1 for r in records.values() if r.compiles),
           "quarantined": sum(1 for r in records.values() if r.quarantined),
           "fixed_by_model": sum(1 for r in records.values()
                                 if r.compiles and r.attempts and not r.rederived),
           "rederived": sum(1 for r in records.values() if r.rederived)}
    by: dict[str, int] = {}
    for r in records.values():
        if r.rederived:
            by[r.recovery or "?"] = by.get(r.recovery or "?", 0) + 1
    out["rederived_by"] = by
    return out


# ----------------------------------------------------------------------------
# Adopting runs of the old scripts
# ----------------------------------------------------------------------------

def _copy_missing(src: Path, dst: Path, counts: dict) -> None:
    """Copy src (file or folder) to dst without replacing anything already there."""
    if src.is_dir():
        for p in src.rglob("*"):
            if p.is_file():
                _copy_missing(p, dst / p.relative_to(src), counts)
        return
    if dst.exists():
        counts["kept"] += 1
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    counts["copied"] += 1


def adopt_rewrite(P: Paths, old: Path) -> None:
    """A pseudo_to_cpp.py --out folder -> ghidra/ + rewrite/ (copies)."""
    if not old.is_dir():
        sys.exit(f"--adopt-rewrite: {old} is not a folder")
    counts = {"copied": 0, "kept": 0}
    for name in ("ghidra_export.json", "callgraph.json"):
        if (old / name).exists():
            _copy_missing(old / name, P.ghidra / name, counts)
    if (old / "pseudocode").is_dir():
        _copy_missing(old / "pseudocode", P.pseudocode, counts)
    for name in ("progress.json", "names.txt", "function_index.json"):
        if (old / name).exists():
            _copy_missing(old / name, P.rewrite / name, counts)
    if (old / ".rewritten").is_dir():
        _copy_missing(old / ".rewritten", P.rewritten_dir, counts)
    if (old / "rewritten code.cpp").exists():
        _copy_missing(old / "rewritten code.cpp", P.rewritten, counts)
    if not (P.progress.exists() or P.export.exists()):
        sys.exit(f"--adopt-rewrite: {old} has no progress.json or ghidra_export.json — is "
                 f"it a pseudo_to_cpp.py output folder?")
    plog(P, f"adopted {old}: {counts['copied']} file(s) copied, {counts['kept']} already "
            f"here and left alone")


def adopt_build(P: Paths, old: Path) -> None:
    """A DECOMP_FIXER.py --workdir -> build/ (copies)."""
    if not (old / "manifest.json").exists():
        sys.exit(f"--adopt-build: {old} has no manifest.json — is it a DECOMP_FIXER.py "
                 f"--workdir?")
    counts = {"copied": 0, "kept": 0}
    for p in old.iterdir():
        if p.name in ("pipeline_state.json", "_fresh_funcs", "_parse_monolith.cpp"):
            continue
        _copy_missing(p, P.build / p.name, counts)
    if (old / "pipeline_state.json").exists():
        _copy_missing(old / "pipeline_state.json", P.build / "build_state.json", counts)
    plog(P, f"adopted {old}: {counts['copied']} file(s) copied, {counts['kept']} already "
            f"here and left alone")


# ----------------------------------------------------------------------------
# Report
# ----------------------------------------------------------------------------

def _link_details(P: Paths) -> dict:
    out = {"stubs": 0, "unresolved": 0}
    rep = P.build / "link_report.txt"
    if rep.exists():
        txt = rep.read_text(errors="replace")
        out["stubs"] = len(re.findall(r"^stubbed ", txt, re.M))
        m = re.search(r"unresolved external symbols \((\d+)\)", txt)
        out["unresolved"] = int(m.group(1)) if m else 0
    return out


def write_report(P: Paths) -> dict:
    st = load_pstate(P)
    data: dict = {"generated": time.strftime("%Y-%m-%d %H:%M:%S"),
                  "pipeline_version": PIPELINE_VERSION, "workdir": str(P.root)}
    data["export"] = export_info(P)
    progress = load_progress(P)
    order = list(progress.get("functions", {}).keys())
    try:
        order = [f["addr"] if isinstance(f["addr"], str) else f"{f['addr']:x}"
                 for f in json.loads(P.export.read_text()).get("functions", [])]
    except Exception:
        pass
    data["rewrite"] = _rewrite_summary(progress, order) if progress.get("functions") else {}
    data["rewrite"].pop("stop", None)
    bstate = {}
    if P.manifest.exists():
        try:
            cfg = Config(input_file=P.rewritten, workdir=P.build)
            data["build"] = build_summary(cfg, load_manifest(cfg))
            bstate = load_state(cfg)
        except Exception:
            data["build"] = {}
    else:
        data["build"] = {}
    data["link"] = {"ok": bstate.get("link_ok"), **_link_details(P)} if bstate else {}
    data["stages"] = st.get("stages", {})
    write_atomic(P.report_json, json.dumps(data, indent=2))

    def row(label, val):
        return f"| {label} | {val if val not in (None, '') else '—'} |"

    ex, rw, bd, lk = data["export"], data["rewrite"], data["build"], data["link"]
    md = ["# Decomp pipeline report", "",
          f"`{P.root}` · generated {data['generated']} · pipeline {PIPELINE_VERSION}", "",
          "## Stages", "", "| Stage | Last finished | Model | Notes |",
          "|---|---|---|---|"]
    for s in STAGES:
        e = data["stages"].get(s, {})
        md.append(f"| {s} | {e.get('at', '—') if e.get('done') else ('stopped' if e else '—')}"
                  f" | {e.get('model', '') or ''} | {e.get('note', '') or ''} |")
    md += ["", "## Export", "", "| | |", "|---|---|",
           row("Functions", ex.get("functions")),
           row("With pseudocode", ex.get("with_pseudocode")),
           row("Data types / signatures", f"{ex.get('datatypes', 0)} / {ex.get('signatures', 0)}"
               if ex else None),
           "", "## Rewrite", "", "| | |", "|---|---|",
           row("Rewritten", f"{rw.get('done')}/{rw.get('functions')}" if rw else None),
           row("Waiting to be rewritten again", rw.get("stale")),
           row("Renamed from placeholders", rw.get("renamed")),
           row("Skipped / too big / not started",
               f"{rw.get('skipped')} / {rw.get('too_big')} / {rw.get('not_started')}" if rw else None),
           row("Copied without the model (--tiny)", rw.get("tiny")),
           row("Done in pieces", rw.get("in_pieces")),
           row("Faithful fallbacks", rw.get("faithful")),
           row("Flagged for a second look", rw.get("suspect"))]
    for r, n in (rw.get("suspect_reasons") or {}).items():
        md.append(row(f"&nbsp;&nbsp;{r}", n))
    md += ["", "## Build", "", "| | |", "|---|---|",
           row("Functions in the build", bd.get("functions")),
           row("Compile", bd.get("compile")),
           row("Fixed by the model", bd.get("fixed_by_model")),
           row("Re-derived from pseudocode", bd.get("rederived")),
           row("Quarantined", bd.get("quarantined"))]
    for r, n in (bd.get("rederived_by") or {}).items():
        md.append(row(f"&nbsp;&nbsp;re-derived: {r}", n))
    md += ["", "## Link", "", "| | |", "|---|---|",
           row("Linked", {True: "yes", False: "no"}.get(lk.get("ok"))),
           row("Placeholder definitions (stubs.cpp)", lk.get("stubs")),
           row("Unresolved external symbols", lk.get("unresolved")),
           "", "## Where to look", "",
           "- `build/quarantine/` originals of functions that couldn't be fixed",
           "- `build/rederived.txt` functions rebuilt from pseudocode (review the "
           "faithful-pseudocode ones first)",
           "- `build/link_report.txt` placeholders and unresolved symbols",
           "- `build/split_report.txt`, `build/header_repair_report.txt` what the split "
           "renamed or switched off",
           "- `rewrite/progress.json` per-function flags (`suspect`)", ""]
    write_atomic(P.report_md, "\n".join(md))
    return data


# ----------------------------------------------------------------------------
# Orchestrator
# ----------------------------------------------------------------------------

def _pause_for_model(P: Paths, client: ModelClient, stage: str) -> None:
    current = client.models()
    plog(P, f"  next: '{stage}' uses the model. Loaded in {client.name} now: "
            f"{', '.join(current[:3]) if current else 'nothing / not reachable'}")
    print(f"Load the model you want for '{stage}' in {client.name}, then press Enter "
          f"(Ctrl+C to stop here; the same command resumes).", flush=True)
    try:
        input()
    except (EOFError, OSError):
        print("(no input available — carrying on)", flush=True)


def _check_inputs(P: Paths, first: str) -> None:
    i = STAGES.index(first)
    if i > STAGES.index("export") and not P.export.exists():
        sys.exit(f"--from {first}: there's no {P.export} yet. Run the export first "
                 f"(drop --from), or --adopt-rewrite an old pseudo_to_cpp folder.")
    if i > STAGES.index("rewrite") and not P.rewritten.exists():
        sys.exit(f"--from {first}: there's no {P.rewritten} yet. Run the rewrite first.")
    if i > STAGES.index("split") and not P.manifest.exists():
        sys.exit(f"--from {first}: there's no build yet ({P.manifest}). Run from split.")


def make_build_config(P: Paths, args, client: ModelClient, cxx: str) -> Config:
    snap: dict = {"dir": None}

    def snapshot_dir():
        if P.no_snapshot:
            return None
        if snap["dir"] is None:
            snap["dir"] = P.snapshots / f"{time.strftime('%Y%m%d-%H%M%S')}-build-update"
        return snap["dir"]

    cfg = Config(
        input_file=P.rewritten, workdir=P.build, cxx=cxx, std=args.std,
        libclang_path=args.libclang, max_model_attempts=args.fix_attempts,
        extra_flags=args.extra_flags,
        callgraph_path=args.callgraph or (P.callgraph if P.callgraph.exists() else None),
        force=args.force, stub_all=args.stub_all, export_path=P.export,
        index_path=P.index, no_pseudo=args.no_pseudo,
        retry_quarantined=args.retry_quarantined, model_ctx_chars=args.model_ctx_chars)
    cfg.client = client
    cfg.wanted_model = args.fix_model or args.model
    cfg.snapshot_dir = snapshot_dir
    return cfg


def run_pipeline(args) -> int:
    P = Paths(args.workdir.expanduser().resolve())
    P.no_snapshot = args.no_snapshot
    P.make()
    acquire_lock(P, args.force)

    redo = set(args.redo or [])
    if args.refresh_ghidra:
        redo.add("export")
    if args.retry_quarantined or "recover" in redo:
        args.retry_quarantined = True
    first = args.from_stage or "export"
    last = args.to_stage or ("export" if args.export_only else "link")
    if STAGES.index(first) > STAGES.index(last):
        sys.exit(f"--from {first} comes after --to {last}")
    # a redo of an earlier stage starts the run there
    for r in redo:
        if STAGES.index(r) < STAGES.index(first):
            first = r
    args.export_complete = args.export_only or last == "export"

    if args.adopt_rewrite:
        adopt_rewrite(P, args.adopt_rewrite.expanduser())
    if args.adopt_build:
        adopt_build(P, args.adopt_build.expanduser())
    _check_inputs(P, first)

    client = ModelClient(args.backend, args.api)
    CLIENT["c"] = client
    cxx = find_compiler(args.cxx)
    if not cxx and STAGES.index(last) >= STAGES.index("split"):
        sys.exit(f"No C++ compiler found ({args.cxx}). On a Mac: xcode-select --install; "
                 f"or pass --cxx /path/to/clang++")
    if not args.rewrite_compile_check:
        COMPILER["cmd"] = None

    run_stages = STAGES[STAGES.index(first):STAGES.index(last) + 1]
    plog(P, f"decomp_pipeline {PIPELINE_VERSION}: {P.root} — stages "
            f"{run_stages[0]} → {run_stages[-1]}"
            + (f" (redo: {', '.join(sorted(redo))})" if redo else ""))
    cfg = make_build_config(P, args, client, cxx or "clang++")
    records = None
    ran_something = False
    try:
        for stage in run_stages:
            if args.pause_between_stages and ran_something and stage in MODEL_STAGES:
                _pause_for_model(P, client, stage)
            plog(P, f"== {stage} ==")
            t0 = time.time()
            mark_stage(P, stage, done=False, started=time.strftime("%Y-%m-%d %H:%M:%S"))
            info: dict = {}
            if stage == "export":
                ei = run_export(P, args, redo)
                info = {"note": f"{ei.get('with_pseudocode', 0)}/{ei.get('functions', 0)} "
                                f"with pseudocode"}
            elif stage == "rewrite":
                try:
                    s = run_rewrite(P, args, redo, client)
                except ModelError as e:
                    plog(P, f"STOPPED: {e}")
                    return 2
                info = {"model": s.get("model", ""),
                        "note": f"{s['done']}/{s['functions']} rewritten"}
                if s["stop"]:
                    mark_stage(P, stage, done=False, **info)
                    break
                if not s["done"]:
                    plog(P, "  nothing has been rewritten yet, so there's nothing to build")
                    mark_stage(P, stage, done=False, **info)
                    break
            elif stage == "split":
                redo_split = bool({"split", "fix"} & redo)
                if redo_split and P.manifest.exists():
                    snapshot(P, "redo-build", [P.build / "funcs", P.build / "quarantine",
                                               P.manifest, P.build / "shared.h",
                                               P.build / "globals.cpp", P.build / "stubs.cpp"])
                records = build_split(cfg, redo_split)
                info = {"note": f"{sum(1 for r in records.values() if r.compiles)}/"
                                f"{len(records)} compile after the sweep"}
            elif stage in ("fix", "recover", "link"):
                if records is None:
                    records = load_manifest(cfg)
                if stage == "fix":
                    build_fix(cfg, records)
                    info = {"model": cfg.fix_model_used or ""}
                elif stage == "recover":
                    build_recover(cfg, records)
                    info = {"model": cfg.fix_model_used or ""}
                else:
                    ok = build_link(cfg, records)
                    info = {"note": "linked" if ok else "incomplete"}
            ran_something = True
            mark_stage(P, stage, done=True, seconds=round(time.time() - t0), **info)
    except KeyboardInterrupt:
        if records is not None:
            save_manifest(cfg, records)
        plog(P, "Paused. Run the same command to carry on from here.")
        write_report(P)
        return 130
    except SystemExit:
        if records is not None:
            save_manifest(cfg, records)
        write_report(P)
        raise
    data = write_report(P)
    bd, lk = data.get("build") or {}, data.get("link") or {}
    plog(P, "=" * 60)
    if bd:
        plog(P, f"SUMMARY: {bd['compile']}/{bd['functions']} functions compile, "
                f"{bd['quarantined']} quarantined, {bd['rederived']} re-derived, "
                f"link={'OK' if lk.get('ok') else 'INCOMPLETE' if lk else 'not run'}")
    plog(P, f"Report: {P.report_md}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    # (stage choices are written out, not STAGES, so the AI Harness Run settings
    # form can read them and show a dropdown)
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_argument_group("pipeline")
    g.add_argument("--workdir", type=Path, default=Path("./decomp_project"),
                   help="project folder for everything this pipeline writes")
    g.add_argument("--from", dest="from_stage", choices=["export", "rewrite", "split", "fix", "recover", "link"], default=None,
                   help="start at this stage (earlier stages must have run)")
    g.add_argument("--to", dest="to_stage", choices=["export", "rewrite", "split", "fix", "recover", "link"], default=None,
                   help="stop after this stage")
    g.add_argument("--redo", action="append", nargs="?", const="rewrite", choices=["export", "rewrite", "split", "fix", "recover", "link"],
                   help="do a stage's work again, replacing results in place (never "
                        "deletes; snapshots first). Bare --redo means --redo rewrite. "
                        "Repeatable")
    g.add_argument("--redo-suspect", action="store_true",
                   help="rewrite again only the functions flagged for a second look")
    g.add_argument("--no-snapshot", action="store_true",
                   help="don't copy current files to snapshots/ before a redo replaces them")
    g.add_argument("--pause-between-stages", action="store_true",
                   help="wait for Enter before each stage that uses the model, so you can "
                        "load a different model in LM Studio")
    g.add_argument("--force", action="store_true",
                   help="continue past a failed header gate / systemic preflight / missing "
                        "model, and ignore another run's lock")
    g.add_argument("--adopt-rewrite", type=Path, default=None, metavar="DIR",
                   help="copy in an old pseudo_to_cpp.py output folder (--out)")
    g.add_argument("--adopt-build", type=Path, default=None, metavar="DIR",
                   help="copy in an old DECOMP_FIXER.py --workdir")

    g = ap.add_argument_group("model")
    g.add_argument("--backend", choices=["lmstudio", "ollama"], default="lmstudio")
    g.add_argument("--api", default=None,
                   help="server address if it isn't the usual one "
                        "(default: $OPENAI_BASE_URL or http://localhost:1234/v1)")
    g.add_argument("--model", default=None,
                   help="model for every stage (default: whatever is loaded)")
    g.add_argument("--rewrite-model", default=None,
                   help="model for the rewrite stage (default: --model, else the loaded one)")
    g.add_argument("--fix-model", default=None,
                   help="model for fix/recover (default: --model, else the loaded one)")

    g = ap.add_argument_group("export (Ghidra)")
    g.add_argument("--ghidra", default="http://127.0.0.1:8080/",
                   help="Ghidra MCP/HTTP plugin address")
    g.add_argument("--headless-export", action="store_true",
                   help="export with analyzeHeadless instead of the plugin (needs --project)")
    g.add_argument("--ghidra-home", default=None,
                   help="Ghidra install folder (the one with support/analyzeHeadless); "
                        "default $GHIDRA_INSTALL_DIR or autodiscovery")
    g.add_argument("--project", default=None,
                   help="Ghidra project (.gpr or its folder); implies --headless-export")
    g.add_argument("--program", default=None,
                   help="program inside the project (default: every program)")
    g.add_argument("--export-parallel", type=int, default=0,
                   help="parallel requests to the plugin while exporting (default max(8, --parallel))")
    g.add_argument("--export-only", action="store_true",
                   help="complete the export and stop (same as --to export)")
    g.add_argument("--emit-ghidra-script", nargs="?", const="", default=None, metavar="PATH",
                   help="write the GhidraScript for Ghidra's Script Manager (default "
                        "<workdir>/ghidra/GhidraExport.java) and exit")
    g.add_argument("--refresh-ghidra", action="store_true", help=argparse.SUPPRESS)

    g = ap.add_argument_group("rewrite")
    g.add_argument("--ctx", type=int, default=16384,
                   help="how much text the model can take in at once (tokens)")
    g.add_argument("--max", type=int, default=None, help="stop after N functions")
    g.add_argument("--functions", nargs="+", help="only these functions (names or addresses)")
    g.add_argument("--comments", action="store_true", help="let the model keep comments")
    g.add_argument("--parallel", type=int, default=1, help="functions at once")
    g.add_argument("--auto-parallel", action="store_true",
                   help="adjust --parallel by watching the model's queue")
    g.add_argument("--max-parallel", type=int, default=16)
    g.add_argument("--auto-every", type=float, default=5, help="minutes between steps up")
    g.add_argument("--no-retry", action="store_true",
                   help="don't ask a second time when a reply is unusable")
    g.add_argument("--retry-quality", action="store_true",
                   help="also retry replies that still have decompiler names or strings")
    g.add_argument("--tiny", type=int, default=0,
                   help="copy functions with at most N simple statements without the model")
    g.add_argument("--no-split", action="store_true",
                   help="leave functions too big for --ctx for later instead of splitting")
    g.add_argument("--rewrite-compile-check", action="store_true",
                   help="compile each rewrite on its own and fix it there too (off by "
                        "default: the build compiles against the real shared.h)")
    g.add_argument("--rewrite-retries", dest="compile_retries", type=int, default=3,
                   help="fix attempts per function for --rewrite-compile-check")
    g.add_argument("--fix-mode", choices=["edit", "rewrite"], default="edit",
                   help="how --rewrite-compile-check repairs: edit the failing lines, or "
                        "regenerate the whole function")
    g.add_argument("--fix-steps", choices=["chain", "single"], default="chain",
                   help="chain: goal/diagnose/plan/edit; single: just the edit")

    g = ap.add_argument_group("build (split / fix / recover / link)")
    g.add_argument("--cxx", default="auto", help="C++ compiler: auto (clang++, else g++), "
                                                 "a name or a path")
    g.add_argument("--std", default="c++17")
    g.add_argument("--libclang", default=None, help="path to libclang .dylib/.so")
    g.add_argument("--callgraph", type=Path, default=None,
                   help="call graph for dependency order (default ghidra/callgraph.json)")
    g.add_argument("--fix-attempts", type=int, default=3, help="model attempts per function")
    g.add_argument("--flag", action="append", default=[], dest="extra_flags",
                   help="extra compile flag (repeatable), e.g. --flag -I/path")
    g.add_argument("--stub-all-missing", action="store_true", dest="stub_all",
                   help="at link time, stub EVERY undefined symbol that has a prototype")
    g.add_argument("--no-pseudo", action="store_true",
                   help="skip rebuilding quarantined functions from pseudocode")
    g.add_argument("--retry-quarantined", action="store_true",
                   help="retry recovery on functions already tried (same as --redo recover)")
    g.add_argument("--model-ctx-chars", type=int, default=24000,
                   help="prompt budget; bigger functions are recovered by error-window "
                        "patching instead of a full rewrite")
    g.add_argument("--resume", action="store_true", help=argparse.SUPPRESS)  # always on now
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    args.parallel = max(1, args.parallel)
    args.compile_retries = max(0, args.compile_retries)
    if args.auto_parallel:
        args.max_parallel = max(args.parallel, args.max_parallel)
    args.model_in_use = None
    # fresh module state (matters when called more than once in one process)
    GATE["gate"] = GATE["tuner"] = None
    MODEL_STATS.update(calls=0, no_answer=0, rejected=0)
    _PSEUDO_CACHE.clear()

    if args.emit_ghidra_script is not None:
        P = Paths(args.workdir.expanduser().resolve())
        P.make()
        dest = Path(args.emit_ghidra_script) if args.emit_ghidra_script \
            else P.ghidra / "GhidraExport.java"
        dest.write_text(GHIDRA_EXPORT_SCRIPT.replace(
            'static final String DEFAULT_OUT = "";',
            'static final String DEFAULT_OUT = "%s";' % str(P.ghidra).replace("\\", "\\\\")))
        print(f"Wrote {dest}. In Ghidra: Window > Script Manager > add this folder, then run "
              f"GhidraExport.java with your program open. It writes {P.export} (resuming "
              f"any existing one). Then run this pipeline without --emit-ghidra-script.")
        return 0
    return run_pipeline(args)


if __name__ == "__main__":
    sys.exit(main())
