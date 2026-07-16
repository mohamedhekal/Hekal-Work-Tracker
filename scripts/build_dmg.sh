#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

APP_NAME="Hekal Work Tracker"
APP_BUNDLE="${APP_NAME}.app"
APP_PATH="dist/${APP_BUNDLE}"
VERSION="1.1.1"
DMG_FILE="dist/HekalWorkTracker-${VERSION}.dmg"
STAGING="dist/dmg-staging"
RW_DMG="dist/HekalWorkTracker-temp.dmg"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "DMG builds are supported on macOS only." >&2
  exit 1
fi

if [[ ! -d "$APP_PATH" ]]; then
  echo "==> App bundle not found, building first..."
  "$ROOT/scripts/build_mac.sh"
fi

echo "==> Preparing DMG contents"
rm -rf "$STAGING" "$RW_DMG" "$DMG_FILE"
mkdir -p "$STAGING"
cp -R "$APP_PATH" "$STAGING/"
ln -sf /Applications "$STAGING/Applications"

APP_SIZE_MB="$(du -sm "$STAGING" | awk '{print $1}')"
DMG_SIZE_MB="$((APP_SIZE_MB + 64))"

echo "==> Creating disk image (${DMG_SIZE_MB} MB)"
hdiutil create \
  -volname "$APP_NAME" \
  -srcfolder "$STAGING" \
  -ov \
  -format UDRW \
  -size "${DMG_SIZE_MB}m" \
  "$RW_DMG" >/dev/null

MOUNT_OUTPUT="$(hdiutil attach -readwrite -noverify -noautoopen "$RW_DMG")"
MOUNT_DIR="$(echo "$MOUNT_OUTPUT" | grep -o '/Volumes/.*' | tail -1)"

if [[ -z "$MOUNT_DIR" || ! -d "$MOUNT_DIR" ]]; then
  echo "Failed to mount temporary DMG." >&2
  exit 1
fi

cleanup() {
  if [[ -n "${MOUNT_DIR:-}" ]] && mount | grep -q "$MOUNT_DIR"; then
    hdiutil detach "$MOUNT_DIR" >/dev/null 2>&1 || hdiutil detach "$MOUNT_DIR" -force >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

echo "==> Configuring Finder window layout"
if osascript >/dev/null 2>&1 <<APPLESCRIPT; then
tell application "Finder"
  tell disk "$APP_NAME"
    open
    set current view of container window to icon view
    set toolbar visible of container window to false
    set statusbar visible of container window to false
    set the bounds of container window to {200, 120, 760, 440}
    set viewOptions to the icon view options of container window
    set arrangement of viewOptions to not arranged
    set icon size of viewOptions to 96
    set position of item "$APP_BUNDLE" of container window to {150, 150}
    set position of item "Applications" of container window to {430, 150}
    close
    open
    update without registering applications
    delay 1
  end tell
end tell
APPLESCRIPT
  echo "    Layout applied"
else
  echo "    Skipped Finder layout (osascript unavailable or failed)"
fi

echo "==> Finalizing compressed DMG"
chmod -Rf go-w "$MOUNT_DIR" 2>/dev/null || true
sync
hdiutil detach "$MOUNT_DIR" >/dev/null
trap - EXIT
MOUNT_DIR=""

hdiutil convert "$RW_DMG" -format UDZO -imagekey zlib-level=9 -o "$DMG_FILE" >/dev/null
rm -f "$RW_DMG"
rm -rf "$STAGING"

echo ""
echo "DMG ready:"
echo "  $ROOT/$DMG_FILE"
echo ""
echo "Install: open the DMG, drag the app to Applications."
