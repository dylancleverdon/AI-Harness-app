"""Edit a script (or any text file) with the model loaded in LM Studio.

Ported from lm_edit.py. Default mode: the model never retypes the file, it only writes SEARCH/REPLACE
blocks; each is applied only if its SEARCH text really exists, and for .py/.json an edit that would
break the file is rejected. Rewrite mode retypes whole sections (for prose). `edit_stream` yields
progress events so the UI can show them.
"""
import difflib
import json
import re

import httpx

from . import lmstudio
from .config import settings

TEMPERATURE = 0.2
DEFAULT_CONTEXT = 8000
CHARS_PER_TOKEN = 3.0
CONTEXT_LINES = 15
MAX_CHUNK_TOKENS = 12000

EDIT_PROMPT = """You edit files by writing find-and-replace blocks. Never retype the file.

Format for each change:
<<<<<<< SEARCH
exact lines copied from the SECTION
=======
the new lines
>>>>>>> REPLACE

Rules:
- SEARCH must be copied EXACTLY from the SECTION, same spaces and indentation.
- Keep SEARCH short: just enough lines to be unique (usually 2 to 6 lines).
- To ADD code: SEARCH for the line just before where it goes, and in REPLACE repeat
  that line followed by the new code.
- To DELETE code: put it in SEARCH and leave REPLACE empty.
- Only change what the instruction asks for. Never remove or rewrite anything else.
- Never write placeholder code, stubs, "..." or "rest of code here".
- The OUTLINE lists everything in the whole file. Things listed there already exist:
  don't redefine them.
- If nothing in this SECTION needs to change, reply exactly: NO CHANGES
- No explanations. Only the blocks."""

REWRITE_PROMPT = (
    "You are a precise file editor. You will receive one section of a file and an "
    "instruction. Apply the instruction to that section and return the COMPLETE updated "
    "section - every line, not just the changed parts. You may also be shown read-only "
    "context from before and after the section; never include that context in your "
    "output. Do not add explanations or markdown code fences. Output only the raw edited "
    "section. Preserve formatting and anything the instruction does not ask you to change. "
    "If the instruction doesn't apply to this section, return it unchanged."
)


class EditError(Exception):
    pass


# ---------- splitting ----------

def split_into_chunks(text, max_chars):
    """Split at blank lines where possible, else line breaks, else hard-split. Joined chunks == text."""
    lines = text.splitlines(keepends=True)
    chunks, current, size = [], [], 0

    def flush():
        nonlocal current, size
        if current:
            chunks.append("".join(current))
        current, size = [], 0

    last_blank = None
    for line in lines:
        while len(line) > max_chars:
            flush()
            chunks.append(line[:max_chars])
            line = line[max_chars:]
            last_blank = None
        if size + len(line) > max_chars and current:
            if last_blank and last_blank < len(current):
                head, tail = current[:last_blank], current[last_blank:]
                chunks.append("".join(head))
                current, size = tail, sum(len(x) for x in tail)
            else:
                flush()
            last_blank = None
        current.append(line)
        size += len(line)
        if line.strip() == "":
            last_blank = len(current)
    flush()
    return chunks


def head_lines(text, n):
    return "".join(text.splitlines(keepends=True)[:n])


def tail_lines(text, n):
    return "".join(text.splitlines(keepends=True)[-n:])


def strip_fences(text):
    t = text.strip("\n")
    m = re.match(r"^```[^\n]*\n(.*)\n```\s*$", t, re.DOTALL)
    return m.group(1) if m else text


def outline(text, max_chars):
    """Short map of the whole file: the def/class/function lines."""
    pat = re.compile(r"^\s*(async\s+def|def|class)\s+\w+|"
                     r"^[A-Za-z_][\w\s\*&:<>,]*\b\w+\s*\([^;]*\)\s*\{?\s*$|"
                     r"^#{1,4}\s+\S")
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        if pat.match(line) and not line.strip().startswith(("if", "for", "while", "return")):
            out.append(f"{i}: {line.strip()[:100]}")
    s = "\n".join(out)
    if len(s) > max_chars:
        s = s[:max_chars].rsplit("\n", 1)[0] + "\n..."
    return s


# ---------- find-and-replace blocks ----------

BLOCK = re.compile(r"<{5,}\s*SEARCH[^\n]*\n(.*?)\n?={5,}[ \t]*\n(.*?)\n?>{5,}\s*REPLACE", re.DOTALL)


def parse_blocks(reply):
    return list(BLOCK.findall(reply or ""))


def find_unique(text, search):
    """(start, end) of `search` in text: exactly, else ignoring trailing spaces, else ignoring
    indentation. None if missing or ambiguous."""
    if not search.strip():
        return None
    if text.count(search) == 1:
        i = text.index(search)
        return i, i + len(search)
    if text.count(search) > 1:
        return None
    lines = text.splitlines(keepends=True)
    want = search.splitlines()
    for norm in (str.rstrip, str.strip):
        w = [norm(x) for x in want]
        hits = [i for i in range(len(lines) - len(w) + 1)
                if all(norm(lines[i + k]) == w[k] for k in range(len(w)))]
        if len(hits) == 1:
            start = sum(len(x) for x in lines[:hits[0]])
            end = start + sum(len(x) for x in lines[hits[0]:hits[0] + len(w)])
            if lines[hits[0] + len(w) - 1].endswith("\n") and not search.endswith("\n"):
                end -= 1
            return start, end
        if len(hits) > 1:
            return None
    return None


def reindent(search, found, replace):
    """If the model got SEARCH's indentation wrong, shift REPLACE by the same amount."""
    def ind(s):
        first = next((x for x in s.splitlines() if x.strip()), "")
        return first[:len(first) - len(first.lstrip())]
    have, wrote = ind(found), ind(search)
    if have == wrote:
        return replace
    out = []
    for x in replace.splitlines(keepends=True):
        if x.strip() and x.startswith(wrote):
            x = have + x[len(wrote):]
        out.append(x)
    return "".join(out)


def syntax_error(text, name):
    """Short error message if a .py/.json file is no longer valid, else None."""
    low = name.lower()
    if low.endswith(".py"):
        try:
            compile(text, name, "exec")
        except SyntaxError as e:
            return f"line {e.lineno}: {e.msg}"
    elif low.endswith(".json"):
        try:
            json.loads(text)
        except ValueError as e:
            return str(e)
    return None


# ---------- model access ----------

def context_length(model):
    try:
        info = httpx.get(f"{lmstudio.base_url()}/api/v0/models/{model}", timeout=10).json()
        return int(info.get("loaded_context_length") or info.get("max_context_length"))
    except Exception:
        return None


class Chat:
    def __init__(self, model):
        self.model = model
        self.errors = 0
        self.notes = []

    def __call__(self, system, user, max_tokens):
        """(reply, finish_reason). (None, 'length') means LM Studio choked and the caller should split."""
        payload = {"model": self.model, "temperature": TEMPERATURE, "max_tokens": max_tokens,
                   "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        try:
            r = httpx.post(f"{lmstudio.base_url()}/v1/chat/completions", json=payload, timeout=900)
        except httpx.HTTPError as e:
            raise EditError(f"Can't reach LM Studio: {e}")
        if r.status_code != 200:
            low = r.text.lower()
            if any(k in low for k in ("context", "token", "compute error", "memory", "server_error")):
                self.errors += 1
                if self.errors >= 3:
                    raise EditError("LM Studio failed 3 times in a row, even on smaller sections. The model "
                                    "probably crashed or ran out of memory: eject it, reload with a smaller "
                                    "context length (e.g. 8192) and retry. Your script was not changed.")
                self.notes.append("LM Studio couldn't handle a section; splitting and retrying")
                return None, "length"
            raise EditError(f"LM Studio error {r.status_code}: {r.text[:300]}")
        self.errors = 0
        choice = r.json()["choices"][0]
        text = choice["message"].get("content") or ""
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)  # reasoning models
        return text, choice.get("finish_reason")


# ---------- the two modes ----------

def run_edit_mode(chat, instruction, text, name, chunk_chars, max_tokens, check, report):
    """Section by section: ask for SEARCH/REPLACE blocks, apply only the safe ones. Returns (text, stats)."""
    chunks = split_into_chunks(text, chunk_chars)
    file_map = outline(text, max(1500, chunk_chars // 3))
    stats = {"applied": 0, "not_found": 0, "broke": 0}

    def ask(section, depth=0):
        user = (f"INSTRUCTION:\n{instruction}\n\nFILE: {name}\n\n"
                f"OUTLINE OF THE WHOLE FILE (line: definition):\n{file_map}\n\nSECTION:\n{section}")
        reply, reason = chat(EDIT_PROMPT, user, max_tokens)
        if reason == "length" and reply is None:
            if depth >= 5 or len(section) < 400:
                chat.notes.append("a section couldn't fit and was skipped")
                return []
            parts = split_into_chunks(section, max(len(section) // 2, 200))
            return [b for p in parts for b in ask(p, depth + 1)]
        if reason == "length":
            chat.notes.append("a reply was cut off; only complete edits were used")
        return parse_blocks(reply)

    for i, chunk in enumerate(chunks):
        check()
        report(i + 1, len(chunks), stats)
        for search, replace in ask(chunk):
            if search == replace:
                continue
            spot = find_unique(text, search)
            if not spot:
                stats["not_found"] += 1
                continue
            s, e = spot
            new_part = reindent(search, text[s:e], replace)
            if text[s:e].endswith("\n") and new_part and not new_part.endswith("\n"):
                new_part += "\n"
            candidate = text[:s] + new_part + text[e:]
            err = syntax_error(candidate, name)
            if err and not syntax_error(text, name):
                stats["broke"] += 1
                chat.notes.append(f"rejected an edit that would break the file ({err})")
                continue
            text = candidate
            stats["applied"] += 1
    return text, stats


def run_rewrite_mode(chat, instruction, text, chunk_chars, max_tokens, check, report):
    chunks = split_into_chunks(text, chunk_chars)

    def edit(chunk, before, after, depth=0):
        parts = [f"INSTRUCTION:\n{instruction}\n"]
        if before:
            parts.append(f"READ-ONLY CONTEXT BEFORE (do not output):\n{before}\n")
        parts.append(f"SECTION TO EDIT:\n{chunk}")
        if after:
            parts.append(f"\nREAD-ONLY CONTEXT AFTER (do not output):\n{after}")
        result, reason = chat(REWRITE_PROMPT, "\n".join(parts), max_tokens)
        if reason == "length":
            if depth >= 5 or len(chunk) < 200:
                chat.notes.append("a section couldn't fit and was left unchanged")
                return chunk
            halves = split_into_chunks(chunk, max(len(chunk) // 2, 100))
            out = []
            for j, h in enumerate(halves):
                b = tail_lines("".join(halves[:j]), CONTEXT_LINES) or before
                a = head_lines("".join(halves[j + 1:]), CONTEXT_LINES) or after
                out.append(edit(h, b, a, depth + 1))
            return "".join(out)
        result = strip_fences(result)
        if chunk.endswith("\n") and not result.endswith("\n"):
            result += "\n"
        return result

    out = []
    for i, chunk in enumerate(chunks):
        check()
        report(i + 1, len(chunks), None)
        before = tail_lines(chunks[i - 1], CONTEXT_LINES) if i else ""
        after = head_lines(chunks[i + 1], CONTEXT_LINES) if i + 1 < len(chunks) else ""
        out.append(edit(chunk, before, after))
    return "".join(out)


def unified_diff(name, original, edited):
    return "".join(l if l.endswith("\n") else l + "\n" for l in difflib.unified_diff(
        original.splitlines(keepends=True), edited.splitlines(keepends=True),
        fromfile=f"{name} (original)", tofile=f"{name} (edited)"))


def edit_stream(name, original, instruction, model=None, mode="edit", mem_level=lambda: "green"):
    """Runs in a worker thread and yields dicts: {type: info|progress|done|error, ...}."""
    import queue
    import threading

    q = queue.Queue()
    levels = ["green", "yellow", "orange", "red"]
    trip = settings.get("guard_trip_level")
    state = {"done": 0}
    cancelled = threading.Event()

    def work():
        try:
            m = model or lmstudio.loaded_model()
            if not m:
                raise EditError("No model is loaded in LM Studio. Load one, then retry.")
            ctx = context_length(m) or DEFAULT_CONTEXT
            rewrite = mode == "rewrite"
            chunk_tokens = min(int(ctx * (0.38 if rewrite else 0.45)), MAX_CHUNK_TOKENS)
            chunk_chars = int(chunk_tokens * CHARS_PER_TOKEN)
            max_tokens = min(int(ctx * 0.5), int(chunk_chars / CHARS_PER_TOKEN * 1.5) + 1024)
            if not rewrite:
                max_tokens = min(max_tokens, max(1024, int(ctx * 0.3)))
            n = len(split_into_chunks(original, chunk_chars))
            q.put({"type": "info", "model": m, "context": ctx, "chunks": n, "mode": mode})

            def check():  # cancel + memory guard between sections
                if cancelled.is_set():
                    raise EditError("Cancelled.")
                if settings.get("guard_enabled") and levels.index(mem_level()) >= levels.index(trip):
                    raise EditError(f"Stopped by the memory guard ({mem_level()}) after {state['done']}/{n} "
                                    "sections. Your script was not changed.")
                state["done"] += 1

            def report(i, total, stats):
                q.put({"type": "progress", "chunk": i, "chunks": total, "stats": stats})

            chat = Chat(m)
            if rewrite:
                edited = run_rewrite_mode(chat, instruction, original, chunk_chars, max_tokens, check, report)
                if not original.endswith("\n") and edited.endswith("\n"):
                    edited = edited.rstrip("\n")
                err = syntax_error(edited, name)
                if err and not syntax_error(original, name):
                    chat.notes.append(f"the rewritten file has an error ({err}); for code use find-and-replace mode")
                stats = None
            else:
                edited, stats = run_edit_mode(chat, instruction, original, name, chunk_chars, max_tokens,
                                              check, report)
            q.put({"type": "done", "edited": edited, "changed": edited != original, "notes": chat.notes,
                   "stats": stats, "diff": unified_diff(name, original, edited)})
        except EditError as e:
            q.put({"type": "error", "message": str(e)})
        except Exception as e:  # never leave the UI hanging
            q.put({"type": "error", "message": f"{type(e).__name__}: {e}"})
        q.put(None)

    threading.Thread(target=work, daemon=True).start()
    try:
        while True:
            ev = q.get()
            if ev is None:
                return
            yield ev
    finally:  # the client went away (Cancel/close): stop after the section in flight
        cancelled.set()
