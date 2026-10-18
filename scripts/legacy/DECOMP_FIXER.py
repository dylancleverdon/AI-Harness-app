#!/usr/bin/env python3
"""
DECOMP_FIXER.py

A pipeline that takes a first-pass C++ reconstruction of a decompiled program
(one giant .cpp file, ~90% of functions compiling individually, still carrying
Ghidra artifacts) and drives it toward a compiling, linking artifact.

Stages:
  0. Emit the de-ghidra intrinsics header (static).
  1. SPLIT the monolith with libclang (two-pass) into:
        shared.h, ghidra_intrins.h, globals.cpp, funcs/<mangled>.cpp, manifest.json
     with a reconciliation guard so a malformed function can't corrupt the split.
  2. Per-TU DE-GHIDRA text cleanup (safe, reversible, one TU at a time).
  3. Isolated COMPILE sweep -> mark each TU compiles / fails.
  4. Dependency-ordered FIXER loop on the failing set:
        deterministic fixes -> templated fixes -> LM Studio slice repair
        -> recompile -> lock or quarantine.
  4b. RECOVER quarantined functions from their Ghidra pseudocode (needs
      ghidra_export.json + the //@ghidra markers from pseudo_to_cpp.py): full
      rewrite against shared.h, error-window patching for big functions, or a
      faithful fallback. Re-derived functions are listed in rederived.txt.
  5. LINK pass: build the whole program, route cross-TU / link errors back to
     the owning function's slice repair, loop until clean or quarantine stabilizes.

Quarantine recovery:
  Point --pseudo-dir at the folder with ghidra_export.json / function_index.json
  (default: the input file's folder). After loading a bigger model in LM Studio,
  re-run with --resume --retry-quarantined to give the still-quarantined
  functions another pass. --no-pseudo skips the stage.

The model (LM Studio local server, OpenAI-compatible) only ever sees ONE small
function body plus the *declarations* its errors reference. Never the monolith.

Usage:
  python3 DECOMP_FIXER.py --input giant.cpp --workdir ./build
  python3 DECOMP_FIXER.py --input giant.cpp --workdir ./build --resume

  --resume picks up where a run stopped, including a run started with an older
  version of this script: it checks what's done, rebuilds anything stale
  (header, globals, untouched function files), keeps functions the model
  already fixed, retries old quarantines, then continues. Safe to repeat.

  Quarantined = a function that still didn't compile after the quick fixes and
  the model's attempts. Its original is in quarantine/, its file becomes an
  empty placeholder so the build continues, and --resume retries it.

Outputs worth reading (in --workdir):
  split_report.txt          renamed duplicates, skipped declarations
  header_repair_report.txt  declarations / fields switched off in shared.h
  link_report.txt           placeholder stubs, unresolved external symbols

Requirements:
  pip install libclang requests
  A C++ compiler (clang recommended) on PATH.
  LM Studio running a local server with a loaded model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------

@dataclass
class Config:
    input_file: Path
    workdir: Path
    cxx: str = "clang++"
    std: str = "c++17"
    # LM Studio OpenAI-compatible endpoint
    lmstudio_url: str = "http://localhost:1234/v1/chat/completions"
    lmstudio_model: str = "local-model"   # LM Studio ignores/accepts this; set if you want
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
    # pseudocode recovery: folder holding ghidra_export.json / function_index.json
    # (default: the input file's folder). model_ctx_chars: prompt budget before a
    # function is repaired by error-window patching instead of a full rewrite.
    pseudo_dir: Optional[Path] = None
    model_ctx_chars: int = 24000
    retry_quarantined: bool = False   # revive manifest quarantines for another pass
    no_pseudo: bool = False           # skip the pseudocode recovery stage

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


def _load_libclang(cfg: Config):
    import clang.cindex as cx
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
    # address its pseudocode lives under (written by pseudo_to_cpp.py)
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


def lmstudio_check(cfg: Config) -> bool:
    """Is the LM Studio server up? If no model was named, use the one loaded.
    Without this, a stopped server made every model call fail silently and the
    fixer quarantined thousands of functions."""
    import requests
    base = cfg.lmstudio_url.split("/chat/completions")[0]
    try:
        r = requests.get(base + "/models", timeout=10)
        r.raise_for_status()
        ids = [m.get("id") for m in r.json().get("data", []) if m.get("id")]
    except Exception as e:
        log(cfg, f"  LM Studio is not reachable at {base} ({type(e).__name__})")
        return False
    if not ids:
        log(cfg, "  LM Studio is running but has no model loaded")
        return False
    if cfg.lmstudio_model in ("", "local-model") or cfg.lmstudio_model not in ids:
        chosen = next((i for i in ids if "embed" not in i.lower()), ids[0])
        if cfg.lmstudio_model not in ("", "local-model"):
            log(cfg, f"  model '{cfg.lmstudio_model}' isn't loaded; using {chosen}")
        cfg.lmstudio_model = chosen
    log(cfg, f"  LM Studio OK — repairing with {cfg.lmstudio_model}")
    return True


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
    import requests
    user = (
        f"// Compiler errors:\n{stderr[-2500:]}\n\n"
        f"// Relevant declarations (for reference, do not redefine):\n{decls}\n\n"
        f"// Function to fix:\n{func_src}"
    )
    payload = {
        "model": cfg.lmstudio_model,
        "messages": [
            {"role": "system", "content": REPAIR_SYSTEM},
            {"role": "user", "content": user},
        ],
        "temperature": cfg.model_temperature,
        "max_tokens": cfg.model_max_tokens,
        "stream": False,
    }
    MODEL_STATS["calls"] += 1
    try:
        r = requests.post(cfg.lmstudio_url, json=payload, timeout=cfg.model_timeout_s)
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"] or ""
    except Exception:
        MODEL_STATS["no_answer"] += 1
        return None
    # thinking models: drop the reasoning block
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
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
    base = cfg.pseudo_dir or cfg.input_file.parent
    export, index = {}, {}
    try:
        data = json.loads((base / "ghidra_export.json").read_text())
        export = data.get("pseudocode", {}) or {}
    except Exception:
        export = {}
    try:
        index = json.loads((base / "function_index.json").read_text()) or {}
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
    import requests
    payload = {"model": cfg.lmstudio_model,
               "messages": [{"role": "system", "content": system},
                            {"role": "user", "content": user}],
               "temperature": cfg.model_temperature, "max_tokens": max_tokens,
               "stream": False}
    try:
        r = requests.post(cfg.lmstudio_url, json=payload, timeout=cfg.model_timeout_s)
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"] or ""
    except Exception:
        return None
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
    m = re.search(r"```(?:cpp|c\+\+|c)?\s*(.*?)```", content, re.DOTALL)
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
        log(cfg, "  pseudocode recovery: no ghidra_export.json found (run "
                 "pseudo_to_cpp.py's --export-only, or pass --pseudo-dir) — skipping")
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
    if not lmstudio_check(cfg):
        log(cfg, "  (LM Studio not available — only the faithful fallback will run)")
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
# pipeline_state.json records which version of this script produced the split
# and which stages finished. On --resume the script checks that against what's
# on disk, so a run started with an OLDER version is upgraded in place: the
# header and globals are rebuilt, function files nobody touched are refreshed,
# files the model already fixed are kept, and old quarantines are retried.

SCRIPT_VERSION = "2026-10-17.1"   # bump when the split / header format changes


def _state_path(cfg: Config) -> Path:
    return cfg.workdir / "pipeline_state.json"


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
    counts = {"refreshed": 0, "kept": 0, "retry": 0, "new": 0}
    to_deghidra: list[FuncRecord] = []
    cfg.funcs_dir.mkdir(parents=True, exist_ok=True)

    for m, rec in new.items():
        fresh_text = (fresh_dir / Path(rec.file).name).read_text()
        target = cfg.workdir / rec.file
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
        cur = prev_path.read_text() if prev_path.exists() else None
        raw_body = raw[prev.start:prev.end].decode("utf-8", "replace")
        if prev.quarantined or cur is None or "// QUARANTINED:" in (cur or ""):
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
            counts["kept"] += 1
        if prev_path != target and prev_path.exists() and prev_path.parent == cfg.funcs_dir:
            prev_path.unlink()                 # file was renamed in the new split
    shutil.rmtree(fresh_dir)

    for rec in to_deghidra:
        p = cfg.workdir / rec.file
        p.write_text(deghidra_text(p.read_text()))

    log(cfg, f"    functions: {counts['kept']} already fixed by the model (kept), "
             f"{counts['refreshed']} untouched (refreshed with the new split), "
             f"{counts['retry']} previously quarantined (restored for another try), "
             f"{counts['new']} not in the old run")
    return new


def _another_run_active(cfg: Config) -> bool:
    """The old script writes worklist.log continuously; if it changed in the
    last few seconds another run is probably still going in this folder."""
    try:
        return time.time() - cfg.log_path.stat().st_mtime < 8
    except OSError:
        return False


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


def run(cfg: Config, resume: bool) -> None:
    cfg.workdir.mkdir(parents=True, exist_ok=True)
    if _another_run_active(cfg) and not cfg.force:
        print(f"error: {cfg.log_path} was written to seconds ago — another run looks "
              f"active in this folder. Stop it first (or wait a few seconds), then "
              f"re-run. (--force to ignore)", file=sys.stderr)
        sys.exit(3)
    if cfg.log_path.exists() and not resume:
        cfg.log_path.unlink()

    log(cfg, f"DECOMP_FIXER {SCRIPT_VERSION} starting on {cfg.input_file}")
    write_intrinsics(cfg)

    if resume and cfg.manifest_path.exists():
        # ---------------- resume: check what's done, redo what's stale -------
        records = load_manifest(cfg)
        state = load_state(cfg)
        sha = _input_sha(cfg)
        log(cfg, f"Resume check ({len(records)} functions in manifest):")
        same_version = state.get("version") == SCRIPT_VERSION
        same_input = state.get("input_sha") in (None, sha)
        if not same_input:
            log(cfg, "  !! the input file changed since this run started — re-splitting it")
        files_missing = [r for r in records.values() if not (cfg.workdir / r.file).exists()]

        if not (same_version and same_input and _header_is_current(cfg)) or files_missing:
            why = ("made by an older version of this script" if not same_version
                   else "out of date" if same_input and not files_missing
                   else f"{len(files_missing)} function file(s) missing" if files_missing
                   else "input changed")
            log(cfg, f"  [redo] split + header: {why} — rebuilding shared.h/globals.cpp "
                     f"and merging with the work already done")
            for f in ("shared.h.pch", "header_errors.txt", "header_repair_report.txt",
                      "globals_repair_report.txt"):
                (cfg.workdir / f).unlink(missing_ok=True)
            if (cfg.workdir / "obj").exists():
                shutil.rmtree(cfg.workdir / "obj")
            records = reconcile_resume(cfg, records)
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
            log(cfg, "  [redo] compile status (the old run's pass/fail can't be trusted "
                     "with the new header)")
            _sweep_all(cfg, records)
        else:
            log(cfg, "  [ok]   compile sweep done")

        done = sum(1 for r in records.values() if r.compiles)
        quar = sum(1 for r in records.values() if r.quarantined)
        todo = sum(1 for r in records.values() if not r.compiles and not r.quarantined)
        log(cfg, f"  status: {done} compile, {todo} still to fix, {quar} quarantined")
    else:
        # ---------------- fresh run ------------------------------------------
        # clear generated output from earlier runs so stale function files /
        # quarantine stubs / reports can't leak into this one
        for d in (cfg.funcs_dir, cfg.quarantine_dir, cfg.workdir / "obj"):
            if d.exists():
                shutil.rmtree(d)
        for f in ("stubs.cpp", "link_report.txt", "globals_repair_report.txt",
                  "stubs_repair_report.txt", "shared.h.pch", "header_errors.txt",
                  "header_repair_report.txt", "first_error.txt",
                  "libclang_parse_errors.txt", "split_report.txt", "link_errors.txt",
                  "pipeline_state.json"):
            (cfg.workdir / f).unlink(missing_ok=True)
        log(cfg, "Stage 1: split (parsing the whole file with libclang — "
                 "this can take a minute on a large monolith with no output; not stalled)")
        records = split_monolith(cfg)
        save_state(cfg, input_sha=_input_sha(cfg), split_done=True,
                   header_ok=False, sweep_done=False)
        log(cfg, "Stage 2: de-ghidra text pass")
        apply_deghidra_pass(cfg, records)
        save_manifest(cfg, records)
        log(cfg, "Stage 2b: validate/repair shared headers (gate — a broken "
                 "header fails every TU identically)")
        _gate_header(cfg, records)
        _sweep_all(cfg, records)

    n_failing = sum(1 for r in records.values() if not r.compiles and not r.quarantined)
    if n_failing and not lmstudio_check(cfg):
        save_manifest(cfg, records)
        if not cfg.force:
            log(cfg, f"STOPPED: {n_failing} function(s) need the model but LM Studio isn't "
                     f"available. Start its local server and re-run with --resume (no "
                     f"re-split needed), or add --force to quarantine whatever the "
                     f"deterministic fixes can't handle.")
            sys.exit(2)
        log(cfg, "  --force: continuing without the model")
    log(cfg, "Stage 4: dependency order + fixer loop")
    order = build_dep_order(cfg, records)
    fixer_loop(cfg, records, order)
    save_manifest(cfg, records)

    log(cfg, "Stage 4b: recover quarantined functions from Ghidra pseudocode")
    pseudocode_recovery(cfg, records)
    save_manifest(cfg, records)

    log(cfg, "Stage 5: link pass")
    linked = link_pass(cfg, records)
    save_manifest(cfg, records)
    save_state(cfg, link_ok=linked)

    # summary
    total = len(records)
    comp = sum(1 for r in records.values() if r.compiles)
    quar = sum(1 for r in records.values() if r.quarantined)
    rede = sum(1 for r in records.values() if r.rederived)
    faithful = sum(1 for r in records.values() if r.recovery == "faithful-pseudocode")
    log(cfg, "="*60)
    log(cfg, f"SUMMARY: {comp}/{total} functions compile, {quar} quarantined, "
             f"link={'OK' if linked else 'INCOMPLETE'}")
    if rede:
        log(cfg, f"  {rede} re-derived from pseudocode (list in rederived.txt"
                 + (f"; {faithful} are faithful-pseudocode fallbacks — review first)"
                    if faithful else ")"))
    log(cfg, f"  quarantined originals: {cfg.quarantine_dir}")
    log(cfg, f"  worklist / review: {cfg.log_path}")
    if quar:
        log(cfg, "  -> review quarantined functions manually; they indicate "
                 "incomplete lifting or logic the model couldn't safely repair.")


def main():
    ap = argparse.ArgumentParser(description="Decompiled-C++ repair pipeline")
    ap.add_argument("--input", required=True, type=Path, help="giant first-pass .cpp")
    ap.add_argument("--workdir", default=Path("./build"), type=Path)
    ap.add_argument("--cxx", default="clang++")
    ap.add_argument("--std", default="c++17")
    ap.add_argument("--lmstudio-url", default="http://localhost:1234/v1/chat/completions")
    ap.add_argument("--lmstudio-model", default="local-model")
    ap.add_argument("--libclang", default=None, help="path to libclang dylib/so")
    ap.add_argument("--callgraph", default=None, type=Path,
                    help="optional Ghidra call-graph export (.json/.csv/.tsv/.graphml) "
                         "for exact dependency ordering; omit to use the heuristic")
    ap.add_argument("--max-attempts", type=int, default=3)
    ap.add_argument("--flag", action="append", default=[], dest="extra_flags",
                    help="extra compile flag (repeatable), e.g. --flag -I/path")
    ap.add_argument("--resume", action="store_true", help="resume from manifest")
    ap.add_argument("--stub-all-missing", action="store_true", dest="stub_all",
                    help="at link time, add a placeholder for EVERY undefined symbol "
                         "that has a prototype (default: only quarantined functions "
                         "and Ghidra FUN_/DAT_ names)")
    ap.add_argument("--force", action="store_true",
                    help="continue past a failed header gate / systemic preflight "
                         "(normally the run stops there, since every function would fail)")
    ap.add_argument("--pseudo-dir", type=Path, default=None,
                    help="folder with ghidra_export.json / function_index.json from "
                         "pseudo_to_cpp.py (default: the input file's folder). Used to "
                         "rebuild quarantined functions from their pseudocode")
    ap.add_argument("--no-pseudo", action="store_true",
                    help="skip the pseudocode recovery stage for quarantined functions")
    ap.add_argument("--retry-quarantined", action="store_true",
                    help="re-attempt pseudocode recovery on functions already tried and "
                         "left quarantined (e.g. after loading a bigger model)")
    ap.add_argument("--model-ctx-chars", type=int, default=24000,
                    help="prompt budget; a function larger than this is repaired by "
                         "error-window patching instead of a single full rewrite")
    args = ap.parse_args()

    cfg = Config(
        input_file=args.input,
        workdir=args.workdir,
        cxx=args.cxx,
        std=args.std,
        lmstudio_url=args.lmstudio_url,
        lmstudio_model=args.lmstudio_model,
        libclang_path=args.libclang,
        max_model_attempts=args.max_attempts,
        extra_flags=args.extra_flags,
        callgraph_path=args.callgraph,
        force=args.force,
        stub_all=args.stub_all,
        pseudo_dir=args.pseudo_dir,
        no_pseudo=args.no_pseudo,
        retry_quarantined=args.retry_quarantined,
        model_ctx_chars=args.model_ctx_chars,
    )
    if not cfg.input_file.exists():
        print(f"error: input not found: {cfg.input_file}", file=sys.stderr)
        sys.exit(1)
    run(cfg, resume=args.resume)


if __name__ == "__main__":
    main()
