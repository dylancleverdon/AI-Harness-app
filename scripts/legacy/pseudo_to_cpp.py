#!/usr/bin/env python3
"""
pseudo_to_cpp.py - turn Ghidra's pseudocode into readable C++, one function at a time.

A local model reads each function's pseudocode and rewrites what it does as clean C++.
Each rewrite is compiled on its own (a syntax and type check, no linking); if the
compiler complains, its errors go back to the model to fix. There is no checking
against the original machine code: much faster than decomp_match.py, but the result
is the model's best understanding, not a proven copy.

How it works:
  1. Ghidra (through its MCP plugin) supplies the list of functions and the pseudocode.
     The program itself isn't read, so no Xcode tools are needed.
  2. Functions are worked through in the order they appear in the program.
  3. The model rewrites each one as C++ and picks a meaningful name for it if Ghidra
     only had a placeholder (FUN_100003a20). Those names are carried forward: later
     functions that call it see the new name, and earlier code is updated at the end.
  4. Each rewrite is compiled. If it fails, the compiler's errors are sent back to the
     model and it tries again (--compile-retries times). Functions that were split into
     pieces (too big for --ctx) and --tiny functions skip this check.
  5. Everything is written to "rewritten code.cpp", in program order.

Usage:
    python3 pseudo_to_cpp.py                         every function
    python3 pseudo_to_cpp.py --max 5                 just the first 5, to try it out
    python3 pseudo_to_cpp.py --functions FUN_100007f84 FUN_100007ffc

Have the program open and analysed in Ghidra's CodeBrowser with the MCP plugin running
for the FIRST run only. The first run writes ghidra_export.json (every function's
pseudocode) and callgraph.json; after that everything is read from those files and
Ghidra can be closed. --export-only builds them and stops; --refresh-ghidra rebuilds
them after you rename/retype things in Ghidra. rewritten code.cpp now carries a
//@ghidra <addr> marker above each function, and function_index.json maps names to
addresses, so DECOMP_FIXER.py can repair quarantined functions from their pseudocode.

Faster export (no HTTP plugin): --headless-export runs Ghidra's analyzeHeadless
in-process, far faster than the one-at-a-time plugin, and resumes from any export
you've already built. It needs a Ghidra install and your project:
    python3 pseudo_to_cpp.py --out DIR --headless-export --export-only \
        --ghidra-home /path/to/ghidra_11.x --project /path/to/YourProject.gpr
    (add --program NAME to export one program; default is all in the project)
Or run it from Ghidra's GUI Script Manager: --emit-ghidra-script writes the script
to <out>/ghidra_export.py; add that folder in the Script Manager and run it.

Pausing and resuming:
    Press Ctrl+C at any time. Run the same command later and it carries on where it
    stopped. --redo rewrites everything again from scratch.

Output (in the output folder):
    rewritten code.cpp    the C++ for every function, in program order, code only
    names.txt             Ghidra's name -> the new name, one per line (to find things)
    pseudocode/           what Ghidra produced for each function
    progress.json         what's been done (used for resuming)

Options:
    --model qwen3:8b      Ollama model
    --ctx 16384           how much text the model can take in at once (bigger handles
                          bigger functions but uses more memory)
    --max N               stop after N functions
    --functions A B ...   only these functions (Ghidra names or addresses)
    --comments            let the model keep explanatory comments (default: code only)
    --out DIR             where results go (default: current folder)
    --ghidra URL          plugin address (default http://127.0.0.1:8080/)
    --redo                ignore earlier progress and rewrite everything
    --parallel N          work on N functions at once (faster overall; see below)
    --no-retry            don't ask the model a second time when a reply is unusable
    --tiny N              functions with at most N simple statements (no ifs or loops)
                          are copied from Ghidra with tidied types, without the model.
                          --tiny 2 catches getters, setters and one-line wrappers.
    --backend lmstudio    use LM Studio's local server instead of Ollama (its MLX
                          models are often faster on Apple Silicon). Load the model and
                          switch the server on in LM Studio's Developer tab first.
                          --model picks one of LM Studio's models (default: the loaded one).
    --api URL             server address if it isn't the usual one
    --no-split            don't split functions too big for --ctx; leave them for later
                          (by default they are cut into pieces at sensible places, each
                          piece rewritten, and the pieces joined back in order)
    --auto-parallel       adjust --parallel by itself: one fewer whenever requests are
                          waiting in the model's queue, one more after --auto-every
                          minutes with no queue, and back again if one more made things
                          slower. --parallel is where it starts. Set the model app's own
                          limit (OLLAMA_NUM_PARALLEL / LM Studio's parallel setting) to at
                          least --max-parallel so the script, not the app, decides.
    --max-parallel 16     the most --auto-parallel will go up to
    --auto-every 5        minutes between steps up for --auto-parallel
    --redo-suspect        rewrite only the functions flagged for a second look: ones
                          where the model invented text/printing, gave no real name,
                          or was cut off, still has decompiler names (param_1, local_28,
                          uVar3, DAT_...) or raw addresses, has identifying strings from
                          the original program, or doesn't compile. Also checks functions
                          done by earlier versions.
    --compiler auto       C++ compiler for the compile check: auto (clang++, else g++),
                          a name or path, or none to skip the check
    --compile-retries 3   how many fix attempts per function on a failed compile
    --fix-mode edit       on a failed compile, repair INCREMENTALLY (default): derive the
                          function's goal once, then for each error read the exact line the
                          compiler flags, diagnose it, plan the minimal change, and edit
                          just that line, rechecking after each edit — instead of
                          regenerating the whole function (which a small model drifts/guts).
                          A no-progress guard stops as soon as an edit stops moving the
                          error. --fix-mode rewrite restores the old whole-function retry.
    --fix-steps chain     chain (default) runs goal/diagnose/plan/edit; single skips to the
                          edit for fewer model calls

Speed: --parallel only helps if Ollama is allowed to answer several requests at once.
Run this once, then quit and reopen the Ollama app:
    launchctl setenv OLLAMA_NUM_PARALLEL 4

Needs: Ollama running, Ghidra with an MCP plugin, and clang++ or g++ for the compile
check (on a Mac: xcode-select --install).
"""

import argparse
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
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timedelta
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

OLLAMA_URL = "http://localhost:11434/api/chat"
LMSTUDIO_URL = "http://localhost:1234/v1/"
BACKEND = {"kind": "ollama", "url": None}     # set from --backend / --api
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
# Everything this script needs from Ghidra is written once to ghidra_export.json:
# the function list and each function's pseudocode. After that the script reads
# the file and Ghidra can be closed. The quarantine fixer in DECOMP_FIXER.py
# reads the same file to repair functions straight from their pseudocode.

EXPORT_VERSION = 1


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
        self.data = {"version": EXPORT_VERSION, "ghidra": getattr(live, "base", None),
                     "functions": [], "pseudocode": {}}
        if export_path.exists():
            try:
                loaded = json.loads(export_path.read_text())
                if loaded.get("functions"):
                    self.data = loaded
                    self.data.setdefault("pseudocode", {})
            except Exception as e:
                print(f"WARNING: couldn't read {export_path.name} ({e}); rebuilding it.")

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
        if hit is not None:
            return hit or None
        if not self.live:
            return None
        code = self.live.pseudocode(name, addr)
        if getattr(self.live, "notice", None):
            self.notice = self.live.notice
            self.live.notice = None
        with self._lock:
            self.data["pseudocode"][key] = code or ""
            self._dirty += 1
        self._save()
        return code

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

    def build_full_export(self, parallel=4, progress_print=print):
        """Fetch pseudocode for every function so the file is complete and Ghidra
        can be closed. Resumable: skips functions already in the cache."""
        funcs = self.functions()
        missing = [(n, a) for n, a in funcs if not self.have_pseudocode(a)]
        if not missing:
            progress_print(f"Ghidra export already complete "
                           f"({len(funcs)} functions in {self.path.name}).")
            return
        if not self.live:
            progress_print(f"{len(missing)} function(s) missing from {self.path.name} "
                           f"and Ghidra isn't reachable — continuing with what's cached.")
            return
        progress_print(f"Building {self.path.name}: fetching pseudocode for "
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
        """Call graph derived from the pseudocode, in the JSON edge format
        DECOMP_FIXER.py accepts for --callgraph (exact dependency ordering).
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
// Ghidra export for the decomp pipeline (Java GhidraScript — runs natively on
// Ghidra 11/12, no Jython or PyGhidra needed). Decompiles every function and
// writes ghidra_export.json in the SAME format pseudo_to_cpp.py / DECOMP_FIXER.py
// use. It MERGES with an existing export: functions that already have pseudocode
// are kept and skipped, so it resumes prior progress and is itself resumable
// (checkpoints every 500 functions).
//
// Run it headless (launched automatically by pseudo_to_cpp.py --headless-export)
// or from the GUI Script Manager. The one script argument is the OUTPUT FOLDER;
// if none is given, DEFAULT_OUT below is used.
//
// @category Decomp
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.decompiler.DecompiledFunction;
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
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class GhidraExport extends GhidraScript {

    static final String DEFAULT_OUT = "/Users/admin/AIHarness/scripts";
    static final int DECOMP_TIMEOUT = 60;   // seconds per function
    static final int SAVE_EVERY = 500;

    @Override
    public void run() throws Exception {
        String[] a = getScriptArgs();
        String outDir = (a.length >= 1 && a[0].trim().length() > 0) ? a[0].trim() : DEFAULT_OUT;
        File dir = new File(outDir);
        if (!dir.exists()) dir.mkdirs();
        File out = new File(dir, "ghidra_export.json");

        LinkedHashMap<String, String> pseudo = new LinkedHashMap<String, String>();
        int had = loadExisting(out, pseudo);
        println("Export -> " + out.getPath());
        println("Already have pseudocode for " + had + " function(s); they will be skipped.");

        DecompInterface decomp = new DecompInterface();
        if (!decomp.openProgram(currentProgram)) {
            println("ERROR: could not open the decompiler for this program.");
            return;
        }
        FunctionManager fm = currentProgram.getFunctionManager();
        int total = fm.getFunctionCount();
        println("Program has " + total + " function(s). Decompiling the missing ones...");

        List<String[]> funcs = new ArrayList<String[]>();
        int done = 0, newly = 0;
        long t0 = System.currentTimeMillis();
        for (Function func : fm.getFunctions(true)) {
            if (monitor.isCancelled()) break;
            if (func.isExternal()) continue;
            long off = func.getEntryPoint().getOffset();
            String addr = Long.toHexString(off);
            funcs.add(new String[] { func.getName(), addr });
            done++;
            String have = pseudo.get(addr);
            if (have != null && have.length() > 0) continue;   // resume: skip done
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
            pseudo.put(addr, code);
            newly++;
            if (newly % SAVE_EVERY == 0) {
                write(out, pseudo, funcs);
                double rate = newly / Math.max((System.currentTimeMillis() - t0) / 1000.0, 0.001);
                println(String.format("  %d/%d  (+%d new, %.1f/s)", done, total, newly, rate));
            }
        }
        write(out, pseudo, funcs);
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
        int p = s.indexOf("\"pseudocode\"");
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

    private void write(File out, Map<String, String> pseudo, List<String[]> funcs)
            throws Exception {
        File tmp = new File(out.getParentFile(), out.getName() + ".tmp");
        Writer w = new BufferedWriter(
            new OutputStreamWriter(new FileOutputStream(tmp), StandardCharsets.UTF_8));
        w.write("{\"version\":1,\"ghidra\":\"headless-java\",\"functions\":[");
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
        w.write("}}");
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


def run_headless_export(args):
    """Launch Ghidra analyzeHeadless with the embedded export script. Returns True
    on success. Resumes automatically (the script merges with any existing
    ghidra_export.json)."""
    ah = find_analyze_headless(args.ghidra_home)
    if not ah:
        sys.exit("Couldn't find Ghidra's analyzeHeadless. Pass --ghidra-home "
                 "/path/to/ghidra_<version> (the folder that contains support/).")
    if not args.project:
        sys.exit("--headless-export needs --project /path/to/YourProject.gpr "
                 "(or the project folder).")
    proj_dir, proj_name = _project_dir_name(args.project)
    script_dir = args.out / ".ghidra"
    script_dir.mkdir(parents=True, exist_ok=True)
    (script_dir / "GhidraExport.java").write_text(GHIDRA_EXPORT_SCRIPT)
    # -readOnly: we only decompile and write an external JSON, never modify the
    # program, so headless shouldn't check out or save anything.
    cmd = [ah, proj_dir, proj_name, "-noanalysis", "-readOnly",
           "-scriptPath", str(script_dir),
           "-postScript", "GhidraExport.java", str(args.out)]
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
    export_path = args.out / "ghidra_export.json"
    if not export_path.exists():
        sys.exit("Ghidra headless export produced no %s (exit %d). Check the project/"
                 "program names and --ghidra-home, and the output above." % (export_path, code))
    return True


# ---------------------------------------------------------------- model

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


GATE = {"gate": None, "tuner": None}


def ask_model(model, messages, ctx, max_out=None, temperature=0.2):
    gate, tuner = GATE["gate"], GATE["tuner"]
    if gate:
        gate.acquire()
    sent = time.time()
    try:
        if BACKEND["kind"] == "lmstudio":
            text, first_word = ask_lmstudio(model, messages, max_out, temperature)
        else:
            text, first_word = ask_ollama(model, messages, ctx, max_out, temperature)
    finally:
        if gate:
            gate.release()
    if tuner:
        tuner.record(sent, sum(len(m["content"]) for m in messages), first_word, len(text))
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()


def _read_stream(req, kind):
    """Reads a streamed reply. Returns (text, seconds until the first word)."""
    t0, first, parts = time.time(), None, []
    with urllib.request.urlopen(req, timeout=1800) as resp:
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


def ask_lmstudio(model, messages, max_out=None, temperature=0.2):
    """LM Studio's local server (OpenAI-style). The context size is whatever the model
    was loaded with in LM Studio; --ctx only tells this script how much fits."""
    body = {"model": model, "messages": messages, "stream": True,
            "temperature": temperature, "repeat_penalty": 1.1}
    if max_out:
        body["max_tokens"] = max_out
    req = urllib.request.Request(BACKEND["url"] + "chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        return _read_stream(req, "lmstudio")
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300]
        sys.exit(f"\nLM Studio answered with an error: {detail}")
    except Exception as e:
        sys.exit(f"\nCould not reach LM Studio at {BACKEND['url']} ({e}). In LM Studio, open "
                 "the Developer tab, load the model and switch the server on.")


def lmstudio_model(wanted):
    """The model to use: the one asked for if LM Studio has it, else the loaded one."""
    try:
        with urllib.request.urlopen(BACKEND["url"] + "models", timeout=20) as r:
            ids = [m["id"] for m in json.load(r).get("data", [])]
    except Exception as e:
        sys.exit(f"Could not reach LM Studio at {BACKEND['url']} ({e}). In LM Studio, open "
                 "the Developer tab, load the model and switch the server on.")
    ids = [i for i in ids if "embed" not in i.lower()]
    if wanted in ids:
        return wanted
    close = [i for i in ids if wanted.lower().replace(":", "-") in i.lower()]
    if close:
        return close[0]
    if not ids:
        sys.exit("LM Studio's server is on but has no model loaded. Load one in the "
                 "Developer tab, then run this again.")
    print(f"Using LM Studio's model '{ids[0]}' (pass --model to choose another of: "
          f"{', '.join(ids[:6])}).")
    return ids[0]


def ask_ollama(model, messages, ctx, max_out=None, temperature=0.2):
    opts = {"temperature": temperature, "num_ctx": ctx, "repeat_penalty": 1.1}
    if max_out:
        opts["num_predict"] = max_out      # stops a model that gets stuck repeating itself
    body = json.dumps({"model": model, "messages": messages, "stream": True, "think": False,
                       "options": opts}).encode()
    req = urllib.request.Request(OLLAMA_URL, data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        return _read_stream(req, "ollama")
    except Exception as e:
        sys.exit(f"\nCould not reach Ollama ({e}). Is the Ollama app running, and is the "
                 f"model downloaded (ollama pull {model})?")


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


# ---------------------------------------------------------------- compile check

COMPILER = {"cmd": None, "clang": True}
PRELUDE = ("#include <cstdint>\n#include <cstddef>\n#include <cstdlib>\n#include <cstring>\n"
           "#include <cmath>\n#include <cstdio>\n")


def find_compiler(choice):
    """Path of the compiler to use, or None."""
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
                goal = ask_model(args.model, [{"role": "system", "content": FIX_GOAL_SYS},
                    {"role": "user", "content": f"Function {name}:\n```c\n{pseudo[:6000]}\n```"}],
                    args.ctx, 160)
            diagnosis = ask_model(args.model, [{"role": "system", "content": FIX_DIAG_SYS},
                {"role": "user", "content": f"Error: {emsg}\nLine {ln}: {target}"}],
                args.ctx, 120)
            plan = ask_model(args.model, [{"role": "system", "content": FIX_PLAN_SYS},
                {"role": "user", "content": f"Goal: {goal}\nDiagnosis: {diagnosis}\n"
                 f"Failing line {ln}: {target}\nCompiler error: {emsg}"}], args.ctx, 120)
            user = (f"Function goal: {goal}\nPlan: {plan}\nCompiler error: {emsg}\n\n"
                    f"Replace ONLY these line(s):\n```cpp\n{target}\n```")
        else:
            user = (f"Compiler error: {emsg}\n\nReplace ONLY these line(s):\n"
                    f"```cpp\n{target}\n```")
        prog.set_phase(key, f"fixing line {ln} (edit {edits + 1})")
        reply = ask_model(args.model, [{"role": "system", "content": FIX_EDIT_SYS},
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

def load_progress(out):
    try:
        return json.loads((out / "progress.json").read_text())
    except Exception:
        return {}


def save_progress(out, progress):
    f = out / "progress.json"
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(progress, indent=0))
    tmp.replace(f)


def apply_names(text, names):
    """Swap Ghidra's placeholder names for the new ones (whole words only)."""
    if not names:
        return text
    rx = re.compile(r"\b(" + "|".join(re.escape(k) for k in
                                       sorted(names, key=len, reverse=True)) + r")\b")
    return rx.sub(lambda m: names[m.group(1)], text)


def mark_function(code, ghidra_name, addr_hex):
    """Tag the function body with a one-line marker carrying its Ghidra address,
    so DECOMP_FIXER.py can map a function in the combined file back to its
    pseudocode. The marker rides on the body item through combine()."""
    items = split_items(code)
    for idx, it in enumerate(items):
        if it.rstrip().endswith("}") and _func_name(it) and not re.match(
                r"\s*(template\s*<[^>]*>\s*)?(struct|class|union|enum|namespace)\b", it):
            items[idx] = f"//@ghidra {addr_hex} {ghidra_name}\n{it}"
            break
    return "\n\n".join(items)


def write_outputs(out, progress, order, keep_comments):
    names = {e["ghidra"]: e["name"] for e in progress.get("functions", {}).values()
             if e.get("name") and e["name"] != e["ghidra"]}
    codes, index = [], {}
    for key in order:
        e = progress.get("functions", {}).get(key)
        if e and e.get("status") == "done":
            f = out / ".rewritten" / f"{key}.cpp"
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
        tmp = out / "rewritten code.cpp.tmp"
        tmp.write_text(combine(codes))
        tmp.replace(out / "rewritten code.cpp")
    # sidecar map (final name -> Ghidra address), a fallback for the fixer when a
    # function in the combined file has no inline marker
    (out / "function_index.json").write_text(json.dumps(index, indent=0))
    (out / "names.txt").write_text("".join(
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


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="qwen3:8b")
    ap.add_argument("--ctx", type=int, default=16384)
    ap.add_argument("--max", type=int, default=None)
    ap.add_argument("--functions", nargs="+")
    ap.add_argument("--comments", action="store_true")
    ap.add_argument("--out", type=Path, default=Path("."))
    ap.add_argument("--ghidra", default="http://127.0.0.1:8080/")
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--parallel", type=int, default=1)
    ap.add_argument("--export-parallel", type=int, default=0,
                    help="threads for the one-time Ghidra pseudocode export "
                         "(0 = auto, max(8, --parallel)). Raise it to fetch faster, "
                         "but Ghidra's decompiler/plugin is usually the real limit — "
                         "watch the exported X/Y rate and back off on timeouts")
    ap.add_argument("--no-retry", action="store_true",
                    help="also turn off the retry that refits an oversized big-function "
                         "piece (on by default; correctness, not quality)")
    ap.add_argument("--retry-quality", action="store_true",
                    help="re-run the model on a function whose rewrite compiled but still "
                         "has leftover decompiler names or identifying strings. OFF by "
                         "default now (it roughly doubles model calls); turn on for higher "
                         "naming quality at ~2x the time")
    ap.add_argument("--tiny", type=int, default=0)
    ap.add_argument("--backend", choices=["ollama", "lmstudio"], default="ollama")
    ap.add_argument("--api", default=None)
    ap.add_argument("--redo-suspect", action="store_true")
    ap.add_argument("--no-split", action="store_true")
    ap.add_argument("--auto-parallel", action="store_true")
    ap.add_argument("--max-parallel", type=int, default=16)
    ap.add_argument("--auto-every", type=float, default=5)
    ap.add_argument("--compiler", default="auto")
    ap.add_argument("--no-compile", action="store_true",
                    help="ROUGH PASS: skip the per-function compile gate entirely. "
                         "Decompiled functions can't compile in isolation anyway (they "
                         "reference shared types/globals/intrinsics/other functions), so "
                         "this just does the fast rewrite and leaves all compilation to "
                         "DECOMP_FIXER, which builds them together against shared.h. Much "
                         "faster — recommended for the first pass over the whole binary.")
    ap.add_argument("--compile-retries", type=int, default=3)
    ap.add_argument("--fix-mode", choices=["edit", "rewrite"], default="edit",
                    help="edit (default): on a failed compile, make minimal line-anchored "
                         "edits (goal -> diagnose -> plan -> edit -> recheck) instead of "
                         "regenerating the whole function; rewrite: the old behaviour")
    ap.add_argument("--fix-steps", choices=["chain", "single"], default="chain",
                    help="chain (default): derive the goal, then per error diagnose -> plan "
                         "-> edit; single: skip straight to the edit (fewer model calls)")
    ap.add_argument("--refresh-ghidra", action="store_true",
                    help="rebuild ghidra_export.json from Ghidra even if it exists "
                         "(use after renaming/retyping things in Ghidra)")
    ap.add_argument("--export-only", action="store_true",
                    help="build ghidra_export.json (+ callgraph.json) and stop, without "
                         "rewriting anything — do this once, then run normally")
    ap.add_argument("--headless-export", action="store_true",
                    help="build ghidra_export.json by launching Ghidra headless "
                         "(analyzeHeadless) instead of the HTTP/MCP plugin — much faster, "
                         "needs --project and a Ghidra install. Resumes from any existing "
                         "export. Pair with --export-only to build and stop.")
    ap.add_argument("--ghidra-home", default=None,
                    help="Ghidra install dir (the folder with support/analyzeHeadless); "
                         "defaults to $GHIDRA_INSTALL_DIR or autodiscovery")
    ap.add_argument("--project", default=None,
                    help="Ghidra project for --headless-export: the .gpr file or its folder")
    ap.add_argument("--program", default=None,
                    help="program name inside the project to export "
                         "(default: every program in the project)")
    ap.add_argument("--emit-ghidra-script", nargs="?", const="", default=None,
                    metavar="PATH",
                    help="write the Ghidra export GhidraScript to PATH (default "
                         "<out>/ghidra_export.py) for running from Ghidra's GUI Script "
                         "Manager, then exit")
    args = ap.parse_args()
    args.parallel = max(1, args.parallel)
    args.compile_retries = max(0, args.compile_retries)
    if args.no_compile or args.compiler == "none":
        print("Rough pass: per-function compile gate OFF — just rewriting. Compilation "
              "is left to DECOMP_FIXER (against shared.h), where these actually compile.")
    elif find_compiler(args.compiler):
        print(f"Compile check with {COMPILER['cmd']} (up to {args.compile_retries} "
              f"fix{'es' if args.compile_retries != 1 else ''} per function).")
    else:
        print(f"WARNING: no C++ compiler found ({args.compiler}), so rewrites won't be "
              "compile-checked. On a Mac: xcode-select --install")
    if args.auto_parallel:
        args.max_parallel = max(args.parallel, args.max_parallel)
    BACKEND["kind"] = args.backend
    if args.backend == "lmstudio":
        BACKEND["url"] = (args.api or LMSTUDIO_URL).rstrip("/") + "/"
        if not BACKEND["url"].endswith("/v1/"):
            BACKEND["url"] += "v1/"
        args.model = lmstudio_model(args.model)

    args.out.mkdir(parents=True, exist_ok=True)

    # Just write the GhidraScript for GUI use, then stop.
    if args.emit_ghidra_script is not None:
        dest = Path(args.emit_ghidra_script) if args.emit_ghidra_script \
            else args.out / "GhidraExport.java"
        script = GHIDRA_EXPORT_SCRIPT.replace(
            'static final String DEFAULT_OUT = "/Users/admin/AIHarness/scripts";',
            'static final String DEFAULT_OUT = "%s";' % str(args.out))
        dest.write_text(script)
        print(f"Wrote {dest}. In Ghidra: Window > Script Manager > add this folder, "
              f"then run GhidraExport.java with your program open. It writes "
              f"{args.out / 'ghidra_export.json'} (resuming any existing one).")
        return

    (args.out / ".rewritten").mkdir(exist_ok=True)
    (args.out / "pseudocode").mkdir(exist_ok=True)

    # Ghidra is consulted through a cache file. First run (or --refresh-ghidra)
    # builds ghidra_export.json; after that everything is read from the file and
    # Ghidra can be closed. --headless-export builds it via analyzeHeadless.
    export_path = args.out / "ghidra_export.json"
    if args.refresh_ghidra and export_path.exists():
        export_path.unlink()
    live = Ghidra(args.ghidra)
    ghidra = GhidraCache(export_path, live)
    building = not export_path.exists() or args.refresh_ghidra or args.export_only
    if building and args.headless_export:
        run_headless_export(args)
        ghidra = GhidraCache(export_path, None)   # reload what headless just wrote
    elif building:
        ghidra.build_full_export(
            parallel=args.export_parallel or max(8, args.parallel))
    elif export_path.exists():
        print(f"Using cached Ghidra export ({export_path.name}); Ghidra not needed. "
              f"(This also picks up an export built by the headless ghidra_export.py.)")
    # Refresh callgraph.json from whatever export is present — whether it was built
    # here over HTTP or by the headless ghidra_export.py — keyed by any final names
    # known so far (full final names once the rewrite is done).
    if export_path.exists():
        names_known = {e["ghidra"]: e["name"]
                       for e in load_progress(args.out).get("functions", {}).values()
                       if e.get("name") and e["name"] != e["ghidra"]}
        try:
            n_edges = ghidra.write_callgraph(args.out / "callgraph.json", names_known)
            print(f"Wrote callgraph.json ({n_edges} functions with internal calls) — "
                  f"pass it to DECOMP_FIXER.py with --callgraph for exact ordering.")
        except Exception as e:
            print(f"(could not write callgraph.json: {e})")
    if args.export_only:
        print("Export done (--export-only). Run again without it to rewrite.")
        return
    funcs = ghidra.functions()
    print(f"Ghidra export lists {len(funcs)} functions.")
    if args.functions:
        wanted = {w.lower().removeprefix("0x") for w in args.functions}
        funcs = [f for f in funcs if f[0].lower() in wanted or f"{f[1]:x}" in wanted]
        print(f"Working on {len(funcs)} of them (--functions).")

    progress = {} if args.redo else load_progress(args.out)
    done = progress.setdefault("functions", {})
    order = [f"{a:x}" for _, a in funcs]
    taken = {e["name"] for e in done.values() if e.get("name")} | \
            {n for n, _ in funcs if not PLACEHOLDER.match(n)}
    if args.redo_suspect:
        n_sus = 0
        for n, a in funcs:
            e = done.get(f"{a:x}")
            if not e or e.get("status") != "done" or e.get("tiny"):
                continue
            if "suspect" not in e:              # done by an earlier version: check it now
                f = args.out / ".rewritten" / f"{a:x}.cpp"
                pf = args.out / "pseudocode" / (re.sub(r"[^\w.-]", "_", n) + ".c")
                code = f.read_text(errors="replace") if f.exists() else ""
                pseudo = pf.read_text(errors="replace") if pf.exists() else ""
                why = suspect_reasons(code, pseudo, e.get("name"),
                                      check_names=not e.get("pieces"))
                if PLACEHOLDER.match(n) and e.get("name") in (None, n):
                    why.append("no real name")
                e["suspect"] = sorted(set(why))
            if e["suspect"]:
                e["status"] = "redo"
                taken.discard(e.get("name"))
                n_sus += 1
        save_progress(args.out, progress)
        print(f"{n_sus} function(s) flagged for a second look will be rewritten again.")
    todo = [(n, a) for n, a in funcs if done.get(f"{a:x}", {}).get("status") not in
            ("done", "skipped")]
    if len(todo) < len(funcs):
        print(f"Resuming: {len(funcs) - len(todo)} already done, {len(todo)} to go.")
    if not todo:
        write_outputs(args.out, progress, order, args.comments)
        print(f"Everything is done. See '{args.out / 'rewritten code.cpp'}'.")
        return
    print("Working through functions in program order. Press Ctrl+C to pause; run the "
          "same command to resume.\n", flush=True)

    system = SYSTEM_PROMPT.replace("{comments}",
                                   WITH_COMMENTS if args.comments else NO_COMMENTS)
    t_start, last_write = time.time(), time.time()
    prog = Progress(len(funcs), len(funcs) - len(todo))
    GATE["gate"] = ModelGate(args.parallel)
    if args.auto_parallel:
        GATE["tuner"] = AutoParallel(GATE["gate"], args.max_parallel,
                                     args.auto_every * 60, prog.log)
        prog.extra = lambda: f"parallel {GATE['gate'].limit}"
        prog.log(f"  parallel starts at {args.parallel}; adjusting every "
                 f"{args.auto_every} min (max {args.max_parallel})")
    state = threading.RLock()          # guards progress/names when several run at once
    stopping = threading.Event()
    counts = {"done": 0}

    def finish(key, entry, text):
        with state:
            done[key] = entry
            save_progress(args.out, progress)
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
        (args.out / "pseudocode" / f"{safe}.c").write_text(pseudo + "\n")

        # Names already chosen for other functions, swapped in so the model sees them
        with state:
            names = {e["ghidra"]: e["name"] for e in done.values()
                     if e.get("name") and e["name"] != e["ghidra"]}
        shown = apply_names(pseudo, names)
        if args.tiny and is_tiny(shown, args.tiny):
            (args.out / ".rewritten" / f"{key}.cpp").write_text(tidy_tiny(shown) + "\n")
            return finish(key, {"ghidra": gname, "name": gname, "status": "done", "tiny": True},
                          f"  {gname}: small, copied without the model")
        in_tokens = int((len(shown) + len(system)) / CHARS_PER_TOKEN) + 200
        room = args.ctx - in_tokens
        if room < 1500:
            if not args.no_split:
                return work_in_pieces(gname, key, shown, names)
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
        reply = ask_model(args.model, [{"role": "system", "content": system},
                                        {"role": "user", "content": msg}], args.ctx, max_out)
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
            reply = ask_model(args.model, [
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
                    reply = ask_model(args.model, [
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
            if not PLACEHOLDER.match(gname):
                name = gname                              # Ghidra already had a real name
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
        (args.out / ".rewritten" / f"{key}.cpp").write_text(code + "\n")
        entry = {"ghidra": gname, "name": name, "status": "done"}
        if compiled is not None:
            entry["compiled"] = compiled
        why = suspect_reasons(code, shown, name if name != gname else None)
        if PLACEHOLDER.match(gname) and name == gname:
            why.append("no real name")      # the model's name was unusable
        if faithful:
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

    def work_in_pieces(gname, key, shown, names):
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
        pdir = args.out / ".rewritten" / f"{key}.parts"
        pdir.mkdir(exist_ok=True)
        placeholder = PLACEHOLDER.match(gname)
        state_ = {"done": 0, "fallback": 0, "name": None}
        lock_ = threading.Lock()
        prog.set_phase(key, f"big: 0/{n} parts")

        def one(i):
            piece = pieces[i]
            h = hashlib.sha1(piece.encode()).hexdigest()[:10]
            f = pdir / f"{i:04d}-{h}.cpp"
            if f.exists():                      # done in an earlier session
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
                reply = ask_model(args.model, [{"role": "system", "content": piece_system},
                                               {"role": "user", "content": msg}],
                                  args.ctx, max_out)
                code, new_name = parse_reply(reply)
                got = clean_piece(code or "", piece, set(names.values()) | {gname})
                if got is None and not args.no_retry:
                    reply = ask_model(args.model, [
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
            if not placeholder:
                name = gname
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
        (args.out / ".rewritten" / f"{key}.cpp").write_text(code + "\n")
        shutil.rmtree(pdir, ignore_errors=True)
        entry = {"ghidra": gname, "name": name, "status": "done", "pieces": n}
        if compiled is not None:
            entry["compiled"] = compiled
        # the pieces keep Ghidra's variable names on purpose, so don't flag those
        why = suspect_reasons(code, shown, name if name != gname else None, check_names=False)
        if placeholder and name == gname:
            why.append("no real name")
        if faithful:
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
                    write_outputs(args.out, progress, order, args.comments)
                last_write = time.time()
            if args.max and counts["done"] >= args.max and not stopping.is_set():
                stopping.set()                        # let the ones running finish
                reached_max = True
        pool.shutdown(wait=True)
    except KeyboardInterrupt:
        stopping.set()
        prog.close()
        with state:
            write_outputs(args.out, progress, order, args.comments)
        print("\nPaused. Run the same command to carry on from here.")
        os._exit(0)                       # don't wait for replies still being written
    prog.close()
    if reached_max:
        print(f"\nReached --max {args.max}. Run the same command to continue.")

    write_outputs(args.out, progress, order, args.comments)
    n_done = sum(1 for e in done.values() if e.get("status") == "done")
    mins = (time.time() - t_start) / 60
    count = counts["done"]
    print(f"\nThis run: {count} function(s) rewritten in {fmt_duration(mins * 60)}. "
          f"Overall: {n_done}/{len(funcs)}.")
    n_sus = sum(1 for e in done.values() if e.get("status") == "done" and e.get("suspect"))
    if n_sus:
        print(f"{n_sus} function(s) were flagged for a second look (invented text, no real "
              f"name, cut off, decompiler names left, identifying strings left, or doesn't "
              f"compile). --redo-suspect rewrites just those, ideally with a bigger --model.")
    n_fail = sum(1 for e in done.values() if e.get("compiled") is False)
    if n_fail:
        print(f"{n_fail} function(s) still don't compile on their own.")
    print(f"Code: '{args.out / 'rewritten code.cpp'}'   Names: '{args.out / 'names.txt'}'")


if __name__ == "__main__":
    main()
