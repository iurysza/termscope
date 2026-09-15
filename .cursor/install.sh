#!/usr/bin/env bash
# Idempotent Cloud Agent bootstrap for termscope.
#
# termscope is a single-file, stdlib-only Python tool, so there is no package
# manager step. The real work here is provisioning the runtime binaries the
# tool shells out to: python3, fd, nvim, an opener (xdg-open), a multiplexer
# (tmux), Television (tv) for the picker UI, and optional bat previews.
set -euo pipefail

TV_VERSION="0.15.9"
TV_TARBALL="tv-${TV_VERSION}-x86_64-unknown-linux-musl.tar.gz"
TV_URL="https://github.com/alexpasmantier/television/releases/download/${TV_VERSION}/${TV_TARBALL}"

log() { printf '\n\033[1;34m==>\033[0m %s\n' "$*"; }

log "Installing system packages via apt"
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  python3 \
  fd-find \
  bat \
  neovim \
  tmux \
  xdg-utils \
  ca-certificates \
  curl \
  tar

# Debian/Ubuntu ship these under alternate binary names. termscope calls `fd`
# and (optionally) `bat`, so expose the expected names on PATH.
log "Linking fd/bat to the names termscope expects"
if command -v fdfind >/dev/null 2>&1; then
  sudo ln -sf "$(command -v fdfind)" /usr/local/bin/fd
fi
if command -v batcat >/dev/null 2>&1; then
  sudo ln -sf "$(command -v batcat)" /usr/local/bin/bat
fi

# Television is not packaged in apt; install the prebuilt static (musl) binary.
tv_supported() {
  command -v tv >/dev/null 2>&1 || return 1
  local out major minor
  out="$(tv --version 2>/dev/null)" || return 1
  case "$out" in
    "television "*) out="${out#television }" ;;
    *) return 1 ;;
  esac
  out="${out%% *}"
  major="${out%%.*}"
  minor="${out#*.}"; minor="${minor%%.*}"
  [ "$major" -gt 0 ] 2>/dev/null || { [ "$major" -eq 0 ] 2>/dev/null && [ "$minor" -ge 15 ] 2>/dev/null; }
}

if tv_supported; then
  log "Television already present: $(tv --version)"
else
  log "Installing Television ${TV_VERSION}"
  tmpdir="$(mktemp -d)"
  trap 'rm -rf "$tmpdir"' EXIT
  curl -fsSL "$TV_URL" -o "$tmpdir/tv.tar.gz"
  tar -xzf "$tmpdir/tv.tar.gz" -C "$tmpdir"
  tv_bin="$(find "$tmpdir" -type f -name tv | head -n 1)"
  if [ -z "$tv_bin" ]; then
    echo "error: tv binary not found in $TV_TARBALL" >&2
    exit 1
  fi
  sudo install -m 0755 "$tv_bin" /usr/local/bin/tv
fi

# Fast sanity check that the sources still parse under the target interpreter.
log "Byte-compiling termscope sources"
python3 -m py_compile termscope termscope_herdr.py

log "Bootstrap complete"
command -v python3 fd bat nvim tmux tv xdg-open
