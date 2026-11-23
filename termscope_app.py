#!/usr/bin/env python3
"""Herdr.app launcher for Termscope: open the picker in a floating pane.

Run from a Herdr.app shell, or from a key-bound mod:
    termscope_app.py --open            files visible in the focused terminal
    termscope_app.py --open-links      links visible in the focused terminal
Optional: --terminal <t..>  --cwd <dir>  --sort appearance|alpha
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_HOMEBREW_TV_PATHS = ("/opt/homebrew/bin/tv", "/usr/local/bin/tv")


def _is_executable(path: str) -> bool:
    return bool(path) and os.path.isfile(path) and os.access(path, os.X_OK)


def _local_bin(env_name: str, name: str) -> str | None:
    configured = os.environ.get(env_name, "").strip()
    if configured:
        return configured
    found = shutil.which(name)
    if found:
        return found
    local = Path.home() / ".local" / "bin" / name
    return str(local) if _is_executable(str(local)) else None


def herdr_ui_bin() -> str | None:
    return _local_bin("HERDR_UI_BIN", "herdr-ui")


def hc_bin() -> str | None:
    return _local_bin("HC_BIN_PATH", "hc")


def television_bin() -> str | None:
    """Resolve Television without relying on the float's PATH."""
    candidates: list[str] = []
    env_path = os.environ.get("TERMSCOPE_TV", "").strip()
    if env_path:
        candidates.append(env_path)
    config_home = os.environ.get("XDG_CONFIG_HOME") or os.path.join(Path.home(), ".config")
    try:
        recorded = Path(config_home, "termscope", "television.path").read_text(encoding="utf-8").strip()
    except OSError:
        recorded = ""
    if recorded:
        candidates.append(recorded)
    which = shutil.which("tv")
    if which:
        candidates.append(which)
    prefix = os.environ.get("HOMEBREW_PREFIX", "").strip()
    if prefix:
        candidates.append(os.path.join(prefix, "bin", "tv"))
    candidates.extend(_HOMEBREW_TV_PATHS)
    return next((c for c in candidates if _is_executable(c)), None)


def terminal_cwd(terminal: str) -> str | None:
    """Foreground cwd (else cwd) of a terminal, via `hc get`."""
    hc = hc_bin()
    if not hc:
        return None
    try:
        result = subprocess.run([hc, "get", terminal], text=True, capture_output=True, check=False)
        data = json.loads(result.stdout)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    foreground = data.get("foreground")
    for candidate in (foreground.get("cwd") if isinstance(foreground, dict) else None, data.get("cwd")):
        if isinstance(candidate, str) and candidate:
            return candidate
    return None


_SORTS = ("appearance", "alpha")


def resolve_sort(explicit: str | None) -> str | None:
    """Sort to forward, or None so the picker can read its own environment."""
    if explicit in _SORTS:
        return explicit
    env = os.environ.get("TERMSCOPE_SORT", "").strip()
    return env if env in _SORTS else None


def build_float_request(
    subcommand: str,
    terminal: str,
    cwd: str,
    sort: str | None = None,
    script: str | None = None,
    python: str | None = None,
    television: str | None = None,
) -> dict:
    """The `herdr-ui float` JSON request. Pure, so it can be tested."""
    argv = [python or sys.executable, script or str(HERE / "termscope"), subcommand,
            "--pane-path", cwd, "--pane-id", terminal,
            "--multiplexer", "app"]
    if sort in _SORTS:
        argv.extend(["--sort", sort])
    if television:
        # The float may not inherit our env: pass Television explicitly.
        argv = ["/usr/bin/env", f"TERMSCOPE_TV={television}", *argv]
    return {"cwd": cwd, "argv": argv, "name": "termscope"}


def parse_float_response(stdout: str) -> str | None:
    """None when ok, else a human-readable error."""
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return f"unreadable herdr-ui response: {stdout.strip()[:200]}"
    if isinstance(data, dict) and data.get("ok"):
        return None
    err = data.get("error") if isinstance(data, dict) else None
    if isinstance(err, dict):
        err = err.get("message") or json.dumps(err)
    return str(err or "herdr-ui float failed")


def launch(args: argparse.Namespace) -> int:
    ui = herdr_ui_bin()
    if not ui:
        print("termscope: herdr-ui not found (set HERDR_UI_BIN or install ~/.local/bin/herdr-ui)",
              file=sys.stderr)
        return 1
    terminal = args.terminal or os.environ.get("HC_TERMINAL_ID", "")
    if not terminal:
        print("termscope: no source terminal (pass --terminal or run inside Herdr.app)", file=sys.stderr)
        return 1
    cwd = args.cwd or terminal_cwd(terminal) or os.getcwd()
    request = build_float_request(
        "links" if args.open_links else "pick",
        terminal, cwd, resolve_sort(args.sort), television=television_bin(),
    )
    env = dict(os.environ, HC_TERMINAL_ID=terminal)
    result = subprocess.run([ui, "float"], input=json.dumps(request), text=True,
                            capture_output=True, env=env, check=False)
    error = parse_float_response(result.stdout) if result.stdout.strip() else None
    if result.returncode != 0 or error or not result.stdout.strip():
        detail = error or result.stderr.strip() or f"exit {result.returncode}"
        print(f"termscope: float failed: {detail}", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="termscope_app")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--open", action="store_true", help="file picker")
    mode.add_argument("--open-links", action="store_true", help="link picker")
    parser.add_argument("--terminal", default=None)
    parser.add_argument("--cwd", default=None)
    parser.add_argument("--sort", choices=["appearance", "alpha"], default=None)
    return launch(parser.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
