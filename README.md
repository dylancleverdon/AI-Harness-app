# AI Harness

A small Mac app that talks to the models loaded in **LM Studio**, runs your **Python scripts/agents** against them, watches **memory**, and gives you real **failure reports**.

## Install (one click)

Open Terminal and paste:

```bash
curl -fsSL https://raw.githubusercontent.com/dylancleverdon/AI-Harness-app/main/install.sh | bash
```

(Or clone the repo and double-click `Install.command`.) This creates `~/AI-Harness` (the code), a Python virtualenv, and **`~/Applications/AI Harness.app`**. Drag it to your Dock. Requires Python 3 and git (macOS prompts for the Command Line Tools if missing).

> If the repo is private, the curl line won't work; `git clone` it instead and double-click `Install.command`.

## Updating

The install is a git checkout, so updating is just a pull:

- **Automatic:** every time you open the app it pulls the latest code first (toggle in Settings).
- **In-app:** Settings → *Check for updates* → *Update & restart* (an "Update available" badge appears in the top bar).
- Changed dependencies are reinstalled automatically on next start. Your scripts, settings and run history live in `~/AIHarness` and are never touched by updates.

## Using it

1. In LM Studio: **Developer → Start Server** (default `http://localhost:1234`), load a model.
2. Open AI Harness. The top bar shows LM Studio status and the live memory level.
3. **Scripts**: pick or edit a script, then **▶ Run** (⌘↵). Scripts get `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `LMSTUDIO_BASE_URL` and `AIHARNESS_MODEL` set, so `OpenAI()` just works. Scripts live in `~/AIHarness/scripts`.
4. **Memory**: available/used/swap, LM Studio's own footprint, per-script RSS, a 10-minute chart with your thresholds, and macOS memory pressure.
5. **AI Edit**: in the Scripts toolbar, ✨ AI Edit lets your local model rewrite the open script from an instruction, shows a diff, and only applies it when you click Apply (old version backed up to `~/AIHarness/backups`).
5. **Models**: what LM Studio has loaded vs. on disk, quick chat, *Unload all*.
6. **Reports**: history of every run with traceback, output and memory over time, plus **Copy failure report** (markdown with diagnosis, traceback, output tail, LM Studio and memory state, and the script source, ready to paste to Claude).

## Memory guard

Memory is classified green / yellow / orange / red from % available (defaults: yellow < 30%, orange < 15%, red < 8%) and macOS memory pressure. If the level stays at or above your trip level (default **orange**) for 2 consecutive seconds, running scripts get SIGTERM (SIGKILL after 4s), a macOS notification fires, and the run is marked `killed` with the memory numbers. Optionally it also unloads LM Studio models via the `lms` CLI. Try it with `memory_stress.py`.

## Failure diagnosis

Failed runs are explained in plain English: LM Studio unreachable, model not loaded, context exceeded, timeouts, bad JSON from the model, killed by the OS, and missing Python packages (with a one-click `pip install`).

## Dev

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt pytest
.venv/bin/python -m harness --open      # http://127.0.0.1:8765
.venv/bin/python -m pytest tests
```
