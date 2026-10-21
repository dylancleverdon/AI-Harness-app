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
- **Model dropdowns:** any option that asks for a model (`--model`, `--lmstudio-model`, a `models` argument...) becomes a dropdown of the models you've downloaded in LM Studio, with the ones loaded right now listed first and marked ●. It reads them with LM Studio's `lms ls`, so it works even when the server is off (and falls back to the server's list if `lms` isn't installed); ↻ reloads the list. Options that take several models get a checklist. *Other (type a name)* is there for anything not listed, such as an Ollama model. Picking a model also shows its maximum context length on the context box.
- **Python packages:** scripts run in AI Harness's own private virtual environment, so you never need to create a venv or fight Homebrew's pip protection. `openai`, `requests` and `libclang` come preinstalled; anything else is one click on the *pip install* button after a failed run, or the *Install a Python package* box in Run settings (Settings → Python shows the interpreter in use and the equivalent manual command). Repeatable options (`action="append"`) get a one-value-per-line box.
- Options set through constants at the top of a script (rather than argparse) can't be detected; use AI Edit or env vars for those.

## Remote access (phone)

Control AI Harness from your phone: start and stop scripts, watch the live console, memory and reports. It works over **Tailscale**, a private network between your own devices, so nothing is opened to the internet.

1. Install Tailscale on the Mac and on your phone, and sign in to the same account on both.
2. In AI Harness on the Mac: Settings → **Remote access** → set a password, tick *Allow my Tailscale devices to sign in*, then **Restart AI Harness now**.
3. On the phone (Tailscale on), open the address the panel shows (`http://<your-mac>:8765`) and sign in.

Only this Mac and signed-in Tailscale devices are answered; other devices on your Wi-Fi are refused. Turning remote access on or off, changing the password and the shell prompt only work on the Mac itself. *Sign out all devices* (or a new password) signs every phone out.

## Memory guard

Memory is classified green / yellow / orange / red from % available (defaults: yellow < 30%, orange < 15%, red < 8%) and macOS memory pressure. If the level stays at or above your trip level (default **orange**) for 2 consecutive seconds, running scripts get SIGTERM (SIGKILL after 4s), a macOS notification fires, and the run is marked `killed` with the memory numbers. Optionally it also unloads LM Studio models via the `lms` CLI. Try it with `memory_stress.py`.

## Scripts run in a real terminal

Scripts run inside a pseudo-terminal, so `sys.stdout.isatty()` is true and they behave exactly as they do in Terminal: live spinners and progress bars, `now: … 47s` timers, terminal-width-aware output. (Programs that don't see a terminal usually go quiet between results, which looks like a stall.) The live line is pinned above the input row while finished lines scroll above it. Colors are stripped. Output from a script's stdout and stderr is shown together, as in a terminal. Turn it off in Settings → Python if you ever need plain pipes.

## Running several scripts at once

Every script has its own console, Run/Stop button, timer and status, so you can start one script, click another and start that too (a green dot and timer in the list show what's running). Click between them to see each one's output; each has its own input line and Stop button. If you reload the page or reopen the window while scripts are running, they re-attach and replay their output. The memory and thermal guards watch the whole machine and stop *all* running scripts when they trip. Very long consoles keep the latest 20,000 lines in view (the full log is in Reports).

## Typing into the console

The input line under the console works in two modes:

- **While a script is running**, what you type is sent to the script (answers `input()` prompts; the prompt text shows pinned above the line). **Ctrl-D** closes the script's input for programs that read until end-of-file.
- **When nothing is running**, it's a small shell prompt: it runs commands in the scripts folder (`cd` works and is remembered), with `python` and `pip` being the same ones your scripts use. Output streams into the console, shows up in Reports, and can be stopped like any run. ↑/↓ recall earlier commands.

The server only answers requests from this app itself (local Host names, plus a header on every write), because it can run code.

## Keep awake, timers

- **☕ Keep awake** (top bar switch, on by default): while a script is running, the Mac is kept from sleeping using macOS's built-in `caffeinate` (idle and system sleep, plus the disk; the screen is still allowed to turn off). It's released the moment the last script finishes or you flip the switch off, and it can't outlive the app. Closing the lid on battery power will still put a Mac to sleep.
- **Run timers:** running scripts show a live ⏱ timer next to their name in the script list, in the console header, and on the Memory page. There's no maximum runtime, so long jobs run until they finish or you stop them (the memory guard still protects you).

## CPU and thermal monitoring

The **System** tab (and the top bar) shows live CPU use, per-core load, load average, the Mac's thermal state, and how much CPU each running script is using (peak CPU is also saved in Reports and the failure report).

- **Thermal state** (nominal / fair / serious / critical) comes from macOS itself, plus the CPU speed limit when the Mac is throttling. No installs or admin rights needed. Throttled periods are shaded red on the CPU chart.
- **Exact temperatures** aren't available to apps on macOS without admin rights. If you install a free helper, AI Harness picks it up automatically within a few seconds and also shows GPU load and power: `brew install macmon` (Apple Silicon) or `brew install osx-cpu-temp` (Intel).
- **Thermal guard** (Settings, off by default): stop running scripts if the Mac reports *serious* or *critical* for 5 seconds, like the memory guard.

## Failure diagnosis

Failed runs are explained in plain English: LM Studio unreachable, model not loaded, context exceeded, timeouts, bad JSON from the model, killed by the OS, and missing Python packages (with a one-click `pip install`).

## Decomp pipeline (`decomp_pipeline.py`)

`scripts/examples/decomp_pipeline.py` combines `pseudo_to_cpp.py` and `DECOMP_FIXER.py` (kept unchanged in `scripts/legacy/`) into one resumable pipeline: **export** (Ghidra pseudocode) → **rewrite** (model writes readable C++) → **split** (libclang: `shared.h` + one file per function) → **fix** → **recover** → **link** → **improve** → **organize** (modules, classes, privacy check, `final/`).

```bash
python3 decomp_pipeline.py --workdir ~/decomp/MyApp                 # everything, or carry on
python3 decomp_pipeline.py --workdir ~/decomp/MyApp --to rewrite    # stop after the rewrite
python3 decomp_pipeline.py --workdir ~/decomp/MyApp --from improve  # another round of improving
```

- **Small steps, not rewrites.** After the first rewrite the model never writes a whole function again. Checks find one small problem at a time (decompiler names, Ghidra helper notation, stack-protector code, pointer arithmetic, warnings, goto, missing calls, behaviour that differs from Ghidra's version, privacy…). A rule fixes it, or the model plans one edit and rewrites only those few lines. A change is kept only if the function still compiles and still behaves like Ghidra's version. Each function's notes (`build/improve/notes/`) tell the model what was tried before; every version is kept in `build/improve/history/`.
- **Calls are checked against Ghidra's.** A draft must call other functions by the names the pseudocode uses; made-up names are matched back to the real ones when `rewritten.cpp` is built, and drafts that leave out the original's calls (or call things it doesn't) are flagged for *Redo suspect*. Functions are named in one pass in the improve stage, so callers and callees always agree.
- **Always the model loaded in LM Studio**, checked at each stage. Tasks it couldn't do are retried when a different model is loaded.
- **`--redo` never deletes.** Results are replaced in place; the current files are copied to `snapshots/` first.
- **Privacy:** put product/company names in `privacy_blocklist.txt`. `final/` isn't written while the privacy check still finds something.
- `REPORT.md` / `report.json` sum up every stage, including the improve score (lower is better).
- **The log** shows stage headers, one result line per stage, each function the fix and recover stages finish, warnings, and at the end *what the script struggled with* (things it couldn't handle or had to work around, marked when they keep coming back). Everything else goes to `pipeline.log` and `build/worklist.log`; `--verbose` prints it all.
- **Diagnostics report:** every run (also when stopped) writes `diagnostics/report-<time>.md`: the struggle report, the run's log, every function that doesn't compile grouped by error (with compiler output, code and notes for examples of each), the rewrite's failures and the stages' own reports. AI Harness sends it to the `decomp-reports` branch of this repo when the run ends, so Claude can read it (Settings → Reports; **this repo is public**, so anyone can read what's sent).

### Updates to the script

The app's example scripts are kept current: when an update changes an example, your copy in `~/AIHarness/scripts` is replaced (an edited copy is backed up to `~/AIHarness/backups` first). So a new `decomp_pipeline.py` arrives with a normal app update.

## Dev

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt pytest
.venv/bin/python -m harness --open      # http://127.0.0.1:8765
.venv/bin/python -m pytest tests
```
