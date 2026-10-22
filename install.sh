#!/bin/bash
# AI Harness installer for macOS. Safe to re-run (it also repairs/updates an existing install).
#   curl -fsSL https://raw.githubusercontent.com/dylancleverdon/AI-Harness-app/main/install.sh | bash
set -euo pipefail

REPO_URL="${AIHARNESS_REPO:-https://github.com/dylancleverdon/AI-Harness-app.git}"
APP_HOME="${AIHARNESS_APP_HOME:-$HOME/AI-Harness}"
DATA_DIR="$HOME/AIHarness"
APP="$HOME/Applications/AI Harness.app"
PORT=8765

say() { printf '\033[1;35m==>\033[0m %s\n' "$*"; }

command -v git >/dev/null || { say "Installing Apple command line tools (git)..."; xcode-select --install || true; echo "Re-run this installer when that finishes."; exit 1; }
PY="$(command -v python3 || true)"
[ -n "$PY" ] || { echo "python3 not found. Install it from python.org or: brew install python"; exit 1; }

if [ -d "$APP_HOME/.git" ]; then
  say "Updating existing install in $APP_HOME"
  git -C "$APP_HOME" pull --rebase --autostash --quiet || true
elif [ -f "$(dirname "$0")/harness/__main__.py" ] 2>/dev/null; then
  APP_HOME="$(cd "$(dirname "$0")" && pwd)"
  say "Using this checkout: $APP_HOME"
else
  say "Downloading AI Harness to $APP_HOME"
  git clone --quiet --branch "${AIHARNESS_BRANCH:-main}" "$REPO_URL" "$APP_HOME"
fi

say "Setting up Python environment (one-time, ~1 minute)"
[ -x "$APP_HOME/.venv/bin/python" ] || "$PY" -m venv "$APP_HOME/.venv"
"$APP_HOME/.venv/bin/python" -m pip install -q --upgrade pip
"$APP_HOME/.venv/bin/python" -m pip install -q -r "$APP_HOME/requirements.txt"
mkdir -p "$DATA_DIR"

say "Creating $APP"
rm -rf "$APP"; mkdir -p "$APP/Contents/MacOS"
cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleName</key><string>AI Harness</string>
<key>CFBundleDisplayName</key><string>AI Harness</string>
<key>CFBundleIdentifier</key><string>local.aiharness</string>
<key>CFBundleExecutable</key><string>launch</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleVersion</key><string>1</string>
<key>LSUIElement</key><false/>
<key>LSArchitecturePriority</key><array><string>arm64</string><string>x86_64</string></array>
</dict></plist>
PLIST
cat > "$APP/Contents/MacOS/launch" <<LAUNCH
#!/bin/bash
APP_HOME="$APP_HOME"
DATA_DIR="$DATA_DIR"
URL="http://127.0.0.1:$PORT"
ping() { curl -fs "\$URL/api/ping" >/dev/null 2>&1; }
# Apps opened from the Dock get a bare PATH; add Homebrew so scripts can find clang++, git, etc.
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:\$PATH"

if ! ping; then
  # Easy updates: grab the latest code every time the app starts (turn off in Settings).
  if ! grep -q '"auto_update": false' "\$DATA_DIR/settings.json" 2>/dev/null; then
    timeout 20 git -C "\$APP_HOME" pull --rebase --autostash --quiet 2>/dev/null || true
  fi
  cd "\$APP_HOME"
  # macOS starts a script-based app like this one under Rosetta (as Intel) on Apple
  # Silicon; start Python natively, so the app and what it runs (the compiler) aren't Intel
  NATIVE=()
  if [ "\$(sysctl -n hw.optional.arm64 2>/dev/null)" = "1" ] && /usr/bin/arch -arm64 "\$APP_HOME/.venv/bin/python" -c "import psutil, uvicorn, fastapi, pydantic; import harness.server" >/dev/null 2>&1; then
    NATIVE=(/usr/bin/arch -arm64)
  fi
  nohup "\${NATIVE[@]}" "\$APP_HOME/.venv/bin/python" -m harness >> "\$DATA_DIR/harness.log" 2>&1 &
  for i in \$(seq 1 80); do ping && break; sleep 0.25; done
fi

# Open as an app-style window if Chrome/Edge/Brave is installed, otherwise the default browser.
for b in "Google Chrome" "Microsoft Edge" "Brave Browser"; do
  if [ -d "/Applications/\$b.app" ]; then open -na "\$b" --args --app="\$URL"; exit 0; fi
done
open "\$URL"
LAUNCH
chmod +x "$APP/Contents/MacOS/launch"
xattr -dr com.apple.quarantine "$APP" 2>/dev/null || true

say "Done! Opening AI Harness (find it in ~/Applications; drag it to your Dock)."
open "$APP"
