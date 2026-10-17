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
5. **AI Edit**: in the Scripts toolbar, ✨ AI Edit lets your local model change the open script from a plain-English instruction. By default the model never retypes your file: it writes small find-and-replace edits, each applied only if its "find" text really exists, and any edit that would break a `.py`/`.json` file is rejected. You see a diff plus counts of applied/skipped/rejected edits, and nothing changes until you click Apply (the old version is backed up to `~/AIHarness/backups`). **Copy review / Download .md** build a file to hand to Claude so it can check the small model's work: your instruction, the model and prompt, every edit it proposed (applied, skipped or rejected), the diff, and the full before/after. Copies are also kept in `~/AIHarness/ai-edit-reviews`. A *Rewrite sections* method is there for prose, not code. Big files are split into sections that fit the model's context; the memory guard also stops an edit that runs memory too high.
6. **Models**: what LM Studio has loaded vs. on disk, quick chat, *Unload all*.
7. **Reports**: history of every run with traceback, output and memory over time, plus **Copy failure report** (markdown with diagnosis, traceback, output tail, LM Studio and memory state, and the script source, ready to paste to Claude).

## Script options, files and folders

- **Run settings:** if a script uses `argparse`, AI Harness reads its options (without running it) and shows a form: number boxes, dropdowns for `choices`, checkboxes for flags. The values you used last are saved per script and pre-filled next time. Options you leave at their default aren't passed. There are also free-form *Extra arguments* and *Environment variables* boxes for scripts that read `os.environ`.
- **Picking files/folders:** path-like options get 📁 / 📄 buttons that open the native macOS chooser.
- **Files the model/script generates:** scripts can write anywhere your user can (there's no sandbox). After each run, AI Harness lists files created or changed in the script folder, any folder passed as an option, and any `~/…` paths hard-coded in the script, with *Preview* and *Show in Finder*. The list is also in Reports and the failure report.
- Options set through constants at the top of a script (rather than argparse) can't be detected; use AI Edit or env vars for those.

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
