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

is_executable() {
  [ -n "${1:-}" ] && [ -f "$1" ] && [ -x "$1" ]
}

use_homebrew_fallbacks() {
  case "${TERMSCOPE_USE_HOMEBREW_FALLBACKS:-1}" in
    0|false|no) return 1 ;;
    *) return 0 ;;
  esac
}

consider_tv() {
  if is_executable "${1:-}" && television_supported "$1"; then
    tv_bin=$1
    return 0
  fi
  return 1
}

resolve_tv() {
  tv_bin=
  [ -n "${TERMSCOPE_TV:-}" ] && consider_tv "$TERMSCOPE_TV" && return 0
  path_bin=$(command -v tv 2>/dev/null || true)
  [ -n "$path_bin" ] && consider_tv "$path_bin" && return 0
  [ -n "${HOMEBREW_PREFIX:-}" ] && consider_tv "$HOMEBREW_PREFIX/bin/tv" && return 0
  if use_homebrew_fallbacks; then
    consider_tv /opt/homebrew/bin/tv && return 0
    consider_tv /usr/local/bin/tv && return 0
  fi
  return 1
}

find_brew() {
  if [ -n "${HOMEBREW_PREFIX:-}" ] && is_executable "$HOMEBREW_PREFIX/bin/brew"; then
    printf '%s\n' "$HOMEBREW_PREFIX/bin/brew"
    return 0
  fi
  if command -v brew >/dev/null 2>&1; then
    command -v brew
    return 0
  fi
  if use_homebrew_fallbacks; then
    for candidate in /opt/homebrew/bin/brew /usr/local/bin/brew; do
      if is_executable "$candidate"; then
        printf '%s\n' "$candidate"
        return 0
      fi
    done
  fi
  return 1
}

record_television() {
  config_dir="${XDG_CONFIG_HOME:-${HOME}/.config}/termscope"
  mkdir -p "$config_dir"
  printf '%s\n' "$1" > "$config_dir/television.path"
}

if resolve_tv; then
  record_television "$tv_bin"
  echo "Television 0.15+ already installed: $tv_bin"
  exit 0
fi

if ! brew_bin=$(find_brew); then
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

brew_prefix=$("$brew_bin" --prefix 2>/dev/null || true)
if [ -n "$brew_prefix" ] && consider_tv "$brew_prefix/bin/tv"; then
  :
elif resolve_tv; then
  :
else
  echo "Homebrew completed, but Television 0.15+ is not available as 'tv'." >&2
  echo "Looked on PATH and in /opt/homebrew/bin and /usr/local/bin." >&2
  exit 1
fi

record_television "$tv_bin"
echo "Television installed: $tv_bin"
