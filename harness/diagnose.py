"""Turns a failed run into a plain-English explanation plus fix suggestions."""
import re

PIP_NAMES = {"cv2": "opencv-python", "PIL": "pillow", "yaml": "pyyaml", "sklearn": "scikit-learn",
             "bs4": "beautifulsoup4", "dotenv": "python-dotenv"}


def extract_traceback(text):
    """Last Python traceback in text -> {text, exception, file, line}, or None."""
    idx = text.rfind("Traceback (most recent call last):")
    if idx < 0:
        return None
    block = text[idx:].rstrip().splitlines()
    exc = next((l for l in reversed(block) if l and not l.startswith(" ")), "")
    frames = re.findall(r'File "([^"]+)", line (\d+)', "\n".join(block))
    user = [f for f in frames if "site-packages" not in f[0]] or frames
    last = user[-1] if user else ("", "0")
    return {"text": "\n".join(block), "exception": exc, "file": last[0], "line": int(last[1])}


def diagnose(run):
    """run: dict with status, exit_code, kill_reason, output (str). Returns list of hint dicts."""
    out = run.get("output", "")
    hints = []

    def add(title, detail, action=None):
        hints.append({"title": title, "detail": detail, **({"action": action} if action else {})})

    if run.get("kill_reason", "").startswith("memory guard"):
        add("Stopped by the memory guard",
            "System memory hit the trip level, so the run was stopped to protect your Mac. "
            "Try a smaller/more quantized model, a shorter context, fewer parallel agents, "
            "or lower the guard level in Settings.")
    elif run.get("kill_reason"):
        add("Stopped", run["kill_reason"])
    elif run.get("exit_code") in (-9, 137):
        add("Killed by the OS (SIGKILL)", "macOS usually does this when memory runs out. Check the Memory tab.")

    if re.search(r"ConnectError|APIConnectionError|Connection refused|Connection error|ConnectionRefusedError", out):
        add("Can't reach LM Studio",
            "Open LM Studio -> Developer tab -> Start Server, and make sure the URL in Settings matches.")
    m = re.search(r"No module named '([\w\.]+)'", out)
    if m:
        pkg = PIP_NAMES.get(m.group(1).split(".")[0], m.group(1).split(".")[0])
        add(f"Missing Python package: {pkg}", f"Install it into the harness environment.", {"pip": pkg})
    if re.search(r"model_not_found|model .{0,60}not found|No models loaded|model_not_loaded", out, re.I):
        add("Model not loaded", "The script asked for a model LM Studio hasn't loaded. "
            "Load it in LM Studio (or enable JIT loading), or change the model name in the script.")
    if re.search(r"context length|context_length|maximum context|n_ctx|too many tokens", out, re.I):
        add("Context window exceeded", "Shorten the prompt/history or raise the model's context length when loading it.")
    if re.search(r"ReadTimeout|TimeoutError|timed out|APITimeoutError", out):
        add("Timed out", "The model may still be loading or generating slowly. "
            "Raise the client timeout or check memory pressure (swapping makes generation crawl).")
    if re.search(r"SyntaxError|IndentationError", out):
        add("Syntax error in the script", "See the traceback for the line number.")
    if re.search(r"JSONDecodeError", out):
        add("Model output wasn't valid JSON", "Small models often add prose around JSON. "
            "Strip code fences, or use LM Studio's structured output (response_format).")
    if run.get("status") == "failed" and not hints:
        add("Script exited with an error", f"Exit code {run.get('exit_code')}. See the traceback and output below.")
    if run.get("status") == "ok" and not out.strip():
        add("Finished but printed nothing", "Add print() calls or check the script actually ran your logic.")
    return hints
