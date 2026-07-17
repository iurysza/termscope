#!/bin/sh
set -eu

television_supported() {
  candidate="${1:-}"
  [ -n "$candidate" ] || return 1

  output="$("$candidate" --version 2>/dev/null)" || return 1
  case "$output" in
    "television "*) version=${output#television } ;;
    *) return 1 ;;
  esac
  version=${version%% *}

  old_ifs=$IFS
  IFS=.
  set -- $version
  IFS=$old_ifs
  major=${1:-}
  minor=${2:-}
  case "$major" in ''|*[!0-9]*) return 1 ;; esac
  case "$minor" in ''|*[!0-9]*) return 1 ;; esac

  [ "$major" -gt 0 ] || { [ "$major" -eq 0 ] && [ "$minor" -ge 15 ]; }
}

tv_bin="$(command -v tv 2>/dev/null || true)"
if television_supported "$tv_bin"; then
  echo "Television 0.15+ already installed: $tv_bin"
  exit 0
fi

brew_bin="$(command -v brew 2>/dev/null || true)"
if [ -z "$brew_bin" ]; then
  echo "Termscope requires Homebrew to install Television 0.15+." >&2
  echo "Install Homebrew from https://brew.sh, then retry the plugin install." >&2
  exit 1
fi

if "$brew_bin" list --formula television >/dev/null 2>&1; then
  echo "Upgrading Television with Homebrew"
  "$brew_bin" upgrade television
else
  echo "Installing Television with Homebrew"
  "$brew_bin" install television
fi

hash -r 2>/dev/null || true
tv_bin="$(command -v tv 2>/dev/null || true)"
if ! television_supported "$tv_bin"; then
  echo "Homebrew completed, but Television 0.15+ is not available as 'tv' on PATH." >&2
  [ -n "$tv_bin" ] && echo "Current tv: $tv_bin" >&2
  exit 1
fi

echo "Television installed: $tv_bin"
