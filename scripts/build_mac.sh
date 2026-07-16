#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VENV="$ROOT/.build-venv"

echo "==> Preparing isolated build environment"
python3 -m venv "$VENV"
# shellcheck disable=SC1091
source "$VENV/bin/activate"

echo "==> Installing build dependencies"
python -m pip install -q --upgrade pip
python -m pip install -q -r requirements.txt -r requirements-build.txt

echo "==> Cleaning previous build"
rm -rf build dist

echo "==> Building macOS app bundle"
python -m PyInstaller --noconfirm --clean HekalWorkTracker.spec

APP_PATH="dist/Hekal Work Tracker.app"
BIN_PATH="$APP_PATH/Contents/MacOS/HekalWorkTracker"

if [[ ! -d "$APP_PATH" ]]; then
  echo "Build failed: app bundle not found at $APP_PATH" >&2
  exit 1
fi

echo "==> Smoke test (launch binary for 3s)"
"$BIN_PATH" &
APP_PID=$!
sleep 3
if kill -0 "$APP_PID" 2>/dev/null; then
  kill "$APP_PID" 2>/dev/null || true
  wait "$APP_PID" 2>/dev/null || true
  echo "    App started successfully"
else
  echo "Build smoke test failed. Run manually to inspect errors:" >&2
  echo "  \"$BIN_PATH\"" >&2
  exit 1
fi

deactivate

echo ""
echo "Build complete:"
echo "  $ROOT/$APP_PATH"
echo ""
echo "Run:"
echo "  open \"$APP_PATH\""
echo ""
echo "User data will be stored at:"
echo "  ~/Library/Application Support/HekalWorkTracker/data/"
