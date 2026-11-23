#!/bin/sh
# Install Termscope for Herdr.app: copy files, render two headless mods, add keys.
# Usage: install-herdr-app.sh [--dry-run] [--uninstall]
# Env: TERMSCOPE_APP_HOME (default ~/.local/share/termscope-app)
#      HERDR_APP_HOME     (default ~/.config/herdr-app)
set -eu

DRY=0
UNINSTALL=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY=1 ;;
    --uninstall) UNINSTALL=1 ;;
    *) echo "usage: $0 [--dry-run] [--uninstall]" >&2; exit 2 ;;
  esac
done

SRC=$(cd "$(dirname "$0")/.." && pwd)
APP_DIR=${TERMSCOPE_APP_HOME:-$HOME/.local/share/termscope-app}
HERDR_HOME=${HERDR_APP_HOME:-$HOME/.config/herdr-app}
MODS="$HERDR_HOME/mods"
KEYS="$HERDR_HOME/keys.json"
PY=${PYTHON:-$(command -v python3)}

run() {
  if [ "$DRY" = 1 ]; then echo "would: $*"; else "$@"; fi
}

# Extra flags for the keys helper
KEYS_FLAGS=""
[ "$DRY" = 1 ] && KEYS_FLAGS="--dry-run"

if [ "$UNINSTALL" = 1 ]; then
  if [ -f "$KEYS" ]; then
    [ "$DRY" = 1 ] || cp "$KEYS" "$KEYS.bak-termscope-$(date +%Y%m%d%H%M%S)"
    # shellcheck disable=SC2086
    "$PY" -I "$SRC/scripts/herdr_app_keys.py" remove "$KEYS" $KEYS_FLAGS
  fi
  for mod in termscope termscope-links; do
    run rm -rf "$MODS/$mod"
  done
  run rm -rf "$APP_DIR"
  echo "termscope: uninstalled from Herdr.app"
  exit 0
fi

tool() {
  # Absolute path of a CLI, else ~/.local/bin fallback.
  found=$(command -v "$1" 2>/dev/null || true)
  [ -n "$found" ] && { echo "$found"; return; }
  echo "$HOME/.local/bin/$1"
}
HC=$(tool hc)
HERDR_APP=$(tool herdr-app)
HERDR_UI=$(tool herdr-ui)
[ -x "$HERDR_UI" ] || echo "notice: herdr-ui not found at $HERDR_UI; the mods need it at run time" >&2

# 1. Copy program files.
run mkdir -p "$APP_DIR"
for f in termscope termscope_app.py termscope_herdr.py; do
  run cp "$SRC/$f" "$APP_DIR/$f"
done
run rm -rf "$APP_DIR/cable"
run cp -R "$SRC/cable" "$APP_DIR/cable"
run chmod +x "$APP_DIR/termscope" "$APP_DIR/termscope_app.py"

# 2. Render mods with absolute paths.
LAUNCHER="$APP_DIR/termscope_app.py"
render() {
  # $1 = mod name. '|' delimiter; none of the values contain it.
  run mkdir -p "$MODS/$1"
  run cp "$SRC/herdr-app/mods/$1/mod.json" "$MODS/$1/mod.json"
  if [ "$DRY" = 1 ]; then
    echo "would: render $MODS/$1/main.js"
  else
    sed \
      -e "s|@@HOME@@|$HOME|g" \
      -e "s|@@PATH@@|$PATH|g" \
      -e "s|@@HC@@|$HC|g" \
      -e "s|@@HERDR_APP@@|$HERDR_APP|g" \
      -e "s|@@HERDR_UI@@|$HERDR_UI|g" \
      -e "s|@@PYTHON@@|$PY|g" \
      -e "s|@@LAUNCHER@@|$LAUNCHER|g" \
      "$SRC/herdr-app/mods/$1/main.js" > "$MODS/$1/main.js"
  fi
}
render termscope
render termscope-links

# 3. Keys: add only unbound ones, with a backup.
if [ -f "$KEYS" ]; then
  [ "$DRY" = 1 ] || cp "$KEYS" "$KEYS.bak-termscope-$(date +%Y%m%d%H%M%S)"
  # shellcheck disable=SC2086
  "$PY" -I "$SRC/scripts/herdr_app_keys.py" add "$KEYS" $KEYS_FLAGS
else
  echo "notice: $KEYS not found; add \"ctrl-shift-a\": \"mod.open:termscope\" yourself"
fi
echo "termscope: installed for Herdr.app (files: $APP_DIR)"
