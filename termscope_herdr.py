#!/usr/bin/env python3
"""Herdr plugin wrapper for Termscope.

Action mode captures the originating pane id/cwd and opens a session-modal
popup. Popup mode launches Television through the shared picker script. Herdr
closes the popup automatically when that command exits.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

_HOMEBREW_TV_PATHS = ("/opt/homebrew/bin/tv", "/usr/local/bin/tv")


def herdr_bin() -> str:
    return os.environ.get("HERDR_BIN_PATH", "herdr")


def plugin_id() -> str:
    return os.environ.get("HERDR_PLUGIN_ID", "termscope")


def plugin_root() -> str:
    return os.environ.get("HERDR_PLUGIN_ROOT", os.getcwd())


def _is_executable(path: str) -> bool:
    return bool(path) and os.path.isfile(path) and os.access(path, os.X_OK)


def television_bin() -> str | None:
    """Resolve Television without relying on a Herdr popup PATH."""
    env_path = os.environ.get("TERMSCOPE_TV", "").strip()
    if env_path and _is_executable(env_path):
        return env_path

    config_home = os.environ.get("XDG_CONFIG_HOME") or os.path.join(
        os.path.expanduser("~"), ".config"
    )
    recorded_file = os.path.join(config_home, "termscope", "television.path")
    try:
        with open(recorded_file, encoding="utf-8") as handle:
            recorded = handle.read().strip()
    except OSError:
        recorded = ""
    if _is_executable(recorded):
        return recorded

    prefix = os.environ.get("HOMEBREW_PREFIX", "").strip()
    candidates = []
    if prefix:
        candidates.append(os.path.join(prefix, "bin", "tv"))
    candidates.extend(_HOMEBREW_TV_PATHS)
    for candidate in candidates:
        if _is_executable(candidate):
            return candidate
    return None


def get_source_pane() -> tuple[str, str, str]:
    """Return (pane_id, cwd, agent) for the source pane."""
    pane_id = os.environ.get("HERDR_PANE_ID") or os.environ.get("HERDR_ACTIVE_PANE_ID")
    if not pane_id:
        print("termscope: no source pane id", file=sys.stderr)
        sys.exit(1)

    result = subprocess.run(
        [herdr_bin(), "pane", "get", pane_id],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        print(f"termscope: pane get failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(result.stdout)
        pane = data["result"]["pane"]
        cwd = pane["cwd"]
        agent = pane.get("agent") or ""
    except (json.JSONDecodeError, KeyError) as exc:
        print(f"termscope: bad pane get response: {exc}", file=sys.stderr)
        sys.exit(1)

    return pane_id, cwd, agent


def open_popup(entrypoint: str) -> None:
    pane_id, cwd, agent = get_source_pane()
    command = [
        herdr_bin(),
        "plugin",
        "pane",
        "open",
        "--plugin",
        plugin_id(),
        "--entrypoint",
        entrypoint,
        "--placement",
        "popup",
        "--env",
        f"SOURCE_PANE_ID={pane_id}",
        "--env",
        f"SOURCE_PANE_CWD={cwd}",
        "--env",
        f"SOURCE_PANE_AGENT={agent}",
    ]
    television = television_bin()
    if television:
        command.extend(["--env", f"TERMSCOPE_TV={television}"])
    result = subprocess.run(
        command,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise SystemExit(f"termscope: popup launch failed: {detail}")


def run_picker(subcommand: str) -> None:
    pane_id = os.environ.get("SOURCE_PANE_ID")
    cwd = os.environ.get("SOURCE_PANE_CWD")
    if not pane_id or not cwd:
        print("termscope: missing SOURCE_PANE_ID or SOURCE_PANE_CWD", file=sys.stderr)
        sys.exit(1)

    sort = os.environ.get("TERMSCOPE_SORT", "appearance")

    script = os.path.join(plugin_root(), "termscope")
    cmd = [
        sys.executable,
        script,
        subcommand,
        "--pane-path",
        cwd,
        "--pane-id",
        pane_id,
        "--multiplexer",
        "herdr",
        "--sort",
        sort,
    ]
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> None:
    args = sys.argv[1:]
    if "--open-pane" in args:
        open_popup("picker")
    elif "--open-links-pane" in args:
        open_popup("link-picker")
    elif "--links" in args:
        run_picker("links")
    else:
        run_picker("pick")


if __name__ == "__main__":
    main()
