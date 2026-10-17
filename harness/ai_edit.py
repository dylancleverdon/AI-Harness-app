"""Edit a script (or any text) with the model loaded in LM Studio, chunking big files.

Ported from the standalone lm_edit.py. `edit_stream` yields progress events so the UI can show them.
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

SYSTEM_PROMPT = (
    "You are a precise file editor. You will receive one section of a file and an "
    "instruction. Apply the instruction to that section and return the COMPLETE updated "
    "section - every line, not just the changed parts. You may also be shown read-only "
    "context from before and after the section so you understand where it sits; never "
    "include that context in your output. Do not add explanations, notes about your "
    "changes, or markdown code fences. Output only the raw edited section. Preserve "
    "formatting, indentation and anything the instruction does not ask you to change. "
    "If the instruction doesn't apply to this section, return it unchanged."
)


class EditError(Exception):
    pass


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


def context_length(model):
    try:
        info = httpx.get(f"{lmstudio.base_url()}/api/v0/models/{model}", timeout=10).json()
        return int(info.get("loaded_context_length") or info.get("max_context_length"))
    except Exception:
        return None


class Editor:
    def __init__(self, model, instruction):
        self.model, self.instruction = model, instruction
        self.errors = 0
        self.notes = []

    def ask(self, chunk, before, after, max_tokens):
        parts = [f"INSTRUCTION:\n{self.instruction}\n"]
        if before:
            parts.append(f"READ-ONLY CONTEXT BEFORE (do not output):\n{before}\n")
        parts.append(f"SECTION TO EDIT:\n{chunk}")
        if after:
            parts.append(f"\nREAD-ONLY CONTEXT AFTER (do not output):\n{after}")
        payload = {"model": self.model, "temperature": TEMPERATURE, "max_tokens": max_tokens,
                   "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                                {"role": "user", "content": "\n".join(parts)}]}
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
        return strip_fences(choice["message"]["content"]), choice.get("finish_reason")

    def edit_chunk(self, chunk, before, after, max_tokens, depth=0):
        result, reason = self.ask(chunk, before, after, max_tokens)
        if reason == "length" or result is None:
            if depth >= 6 or len(chunk) < 200:
                self.notes.append("a section couldn't fit even after splitting and was left unchanged")
                return chunk
            halves = split_into_chunks(chunk, max(len(chunk) // 2, 100))
            out = []
            for i, h in enumerate(halves):
                b = tail_lines("".join(halves[:i]), CONTEXT_LINES) or before
                a = head_lines("".join(halves[i + 1:]), CONTEXT_LINES) or after
                out.append(self.edit_chunk(h, b, a, max_tokens, depth + 1))
            return "".join(out)
        if chunk.endswith("\n") and not result.endswith("\n"):
            result += "\n"
        return result


def unified_diff(name, original, edited):
    return "".join(l if l.endswith("\n") else l + "\n" for l in difflib.unified_diff(
        original.splitlines(keepends=True), edited.splitlines(keepends=True),
        fromfile=f"{name} (original)", tofile=f"{name} (edited)"))


def edit_stream(name, original, instruction, model=None, mem_level=lambda: "green"):
    """Yields dicts: {type: info|progress|done|error, ...}. mem_level() is polled before each chunk."""
    try:
        if not model:
            model = lmstudio.loaded_model()
            if not model:
                raise EditError("No model is loaded in LM Studio. Load one, then retry.")
        ctx = context_length(model) or DEFAULT_CONTEXT
        chunk_tokens = min(int(ctx * 0.38), MAX_CHUNK_TOKENS)
        chunk_chars = int(chunk_tokens * CHARS_PER_TOKEN)
        max_tokens = min(int(ctx * 0.5), int(chunk_chars / CHARS_PER_TOKEN * 1.5) + 1024)
        chunks = split_into_chunks(original, chunk_chars)
        yield {"type": "info", "model": model, "context": ctx, "chunks": len(chunks)}
        ed = Editor(model, instruction)
        trip = settings.get("guard_trip_level")
        levels = ["green", "yellow", "orange", "red"]
        parts = []
        for i, chunk in enumerate(chunks):
            if settings.get("guard_enabled") and levels.index(mem_level()) >= levels.index(trip):
                raise EditError(f"Stopped by the memory guard ({mem_level()}) after {i}/{len(chunks)} sections. "
                                "Your script was not changed.")
            yield {"type": "progress", "chunk": i + 1, "chunks": len(chunks)}
            before = tail_lines(chunks[i - 1], CONTEXT_LINES) if i else ""
            after = head_lines(chunks[i + 1], CONTEXT_LINES) if i + 1 < len(chunks) else ""
            parts.append(ed.edit_chunk(chunk, before, after, max_tokens))
        edited = "".join(parts)
        if not original.endswith("\n") and edited.endswith("\n"):
            edited = edited.rstrip("\n")
        yield {"type": "done", "edited": edited, "changed": edited != original, "notes": ed.notes,
               "diff": unified_diff(name, original, edited)}
    except EditError as e:
        yield {"type": "error", "message": str(e)}
    except Exception as e:  # never leave the UI hanging
        yield {"type": "error", "message": f"{type(e).__name__}: {e}"}
