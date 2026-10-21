"""Finds a script's command-line options (argparse) by reading its source, and remembers the values
used last time. Nothing is executed: options are discovered with the `ast` module."""
import ast
import json
import re
import shlex
import threading
from pathlib import Path

from .config import DATA_DIR

STORE = DATA_DIR / "script_settings.json"
_lock = threading.Lock()
PATHY = re.compile(r"(out|dir|folder|path|file|dest|target|src|input)", re.I)


def _lit(node, default=None):
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError):
        pass
    # Path("./build") / PurePath(...) -> "./build"
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("Path", "PurePath")
            and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)):
        return node.args[0].value
    return default


def parse_params(source):
    """[{dest, flags, positional, kind, type, default, help, choices, required, nargs, path}] in source order."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr == "add_argument"]
    # argparse groups (g = ap.add_argument_group("model")): the form shows each as its own section
    groups = sorted((a.lineno, a.targets[0].id, _lit(a.value.args[0], ""))
                    for a in ast.walk(tree) if isinstance(a, ast.Assign) and len(a.targets) == 1
                    and isinstance(a.targets[0], ast.Name) and isinstance(a.value, ast.Call)
                    and isinstance(a.value.func, ast.Attribute)
                    and a.value.func.attr == "add_argument_group" and a.value.args)

    def group_of(n):
        v = n.func.value
        if not isinstance(v, ast.Name):
            return ""
        title = ""
        for line, name, t in groups:
            if line <= n.lineno and name == v.id:
                title = t
        return title or ""
    out = []
    for n in sorted(calls, key=lambda n: (n.lineno, n.col_offset)):
        flags = [a.value for a in n.args if isinstance(a, ast.Constant) and isinstance(a.value, str)]
        if not flags:
            continue
        kw = {k.arg: k.value for k in n.keywords if k.arg}
        positional = not flags[0].startswith("-")
        dest = _lit(kw["dest"]) if "dest" in kw else None
        if not dest:
            longs = [f for f in flags if f.startswith("--")]
            dest = (longs[0] if longs else flags[0]).lstrip("-").replace("-", "_")
        action = _lit(kw["action"], "store") if "action" in kw else "store"
        typ = kw["type"].id if "type" in kw and isinstance(kw["type"], ast.Name) else "str"
        if typ not in ("int", "float", "str", "Path"):
            typ = "str"
        kind = {"store_true": "bool", "store_false": "bool", "count": "count", "append": "append"}.get(
            action, typ if typ != "Path" else "str")
        default = _lit(kw["default"]) if "default" in kw else (False if action == "store_true" else True if action == "store_false" else None)
        out.append({"dest": dest, "flags": flags, "positional": positional, "kind": kind, "action": action,
                    "default": default, "help": _lit(kw.get("help"), "") if "help" in kw else "",
                    "choices": _lit(kw["choices"]) if "choices" in kw else None,
                    "required": bool(_lit(kw["required"], False)) if "required" in kw else positional,
                    "nargs": _lit(kw["nargs"]) if "nargs" in kw else None,
                    "group": group_of(n),
                    "path": typ == "Path" or kind == "str" and bool(
                        PATHY.search(dest) or re.search(r"\bpath\b|\bfolder\b|\bdirectory\b", str(_lit(kw.get("help"), "")), re.I))})
    return out


def build_argv(params, values):
    """Turn saved/edited form values into an argv list. Options left at their default are omitted."""
    pos, opts = [], []
    for p in params:
        v = values.get(p["dest"], p["default"])
        flag = next((f for f in p["flags"] if f.startswith("--")), p["flags"][0])
        if p["kind"] == "bool":
            if bool(v) != bool(p["default"]):
                opts.append(flag)
            continue
        if p["kind"] == "append":  # repeatable option: one value per line
            for line in str(v or "").splitlines() if not isinstance(v, list) else v:
                if str(line).strip():
                    opts += [flag, str(line).strip()]
            continue
        if p["kind"] == "count":
            opts += [flag] * int(v or 0)
            continue
        if v in (None, "") or (not p["positional"] and not p["required"] and str(v) == str(p["default"])):
            continue
        vals = shlex.split(str(v)) if p["nargs"] not in (None, 1) else [str(v)]
        (pos if p["positional"] else opts).extend(vals if p["positional"] else [flag, *vals])
    return pos + opts


def _load():
    try:
        return json.loads(STORE.read_text())
    except (OSError, ValueError):
        return {}


def get_saved(script):
    with _lock:
        return _load().get(script, {"values": {}, "extra": "", "env": ""})


def save(script, data):
    with _lock:
        all_ = _load()
        cur = all_.get(script, {"values": {}, "extra": "", "env": ""})
        for k in cur:
            if k in data:
                cur[k] = data[k]
        all_[script] = cur
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        STORE.write_text(json.dumps(all_, indent=2))
        return cur


def parse_env(text):
    env = {}
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def literal_paths(source):
    """Hard-coded path strings like '~/Projects/out' or '/Users/me/x' in the script."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    return sorted({n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
                   and len(n.value) > 3 and "\n" not in n.value and re.match(r"^(~/|/Users/|/home/|/tmp/|/Volumes/)", n.value)})


def watch_dirs(params, values, source, cwd):
    """Folders to snapshot before/after a run to find files the script produced."""
    cands = list(literal_paths(source))
    for p in params:
        v = values.get(p["dest"], p["default"])
        if p["path"] and isinstance(v, str) and v:
            cands.append(v)
    roots = [Path(cwd)]
    for c in cands:
        q = Path(c).expanduser()
        q = q if q.is_absolute() else Path(cwd) / q
        root = q if q.is_dir() or (not q.suffix and not q.exists()) else q.parent
        if root not in (Path.home(), Path("/")) and root not in roots:
            roots.append(root)
    return roots
