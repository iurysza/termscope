#!/usr/bin/env python3
"""Herdr plugin wrapper for termscope.

This script is invoked in two modes:

  --open-pane       action mode: open the plugin overlay pane for file picking
  --open-links-pane action mode: open the plugin overlay pane for link picking
  (no flag)         pane mode: run inside the overlay pane and launch fzf

Action mode receives HERDR_PANE_ID (the source pane) and passes the source
pane id/cwd to the overlay pane via env vars. Pane mode reads those vars and
runs the shared picker script.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys


def herdr_bin() -> str:
    return os.environ.get("HERDR_BIN_PATH", "herdr")


def plugin_id() -> str:
    return os.environ.get("HERDR_PLUGIN_ID", "termscope")


def plugin_root() -> str:
    return os.environ.get("HERDR_PLUGIN_ROOT", os.getcwd())


def get_source_pane() -> tuple[str, str]:
    """Return (pane_id, cwd) for the source pane."""
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
        cwd = data["result"]["pane"]["cwd"]
    except (json.JSONDecodeError, KeyError) as exc:
        print(f"termscope: bad pane get response: {exc}", file=sys.stderr)
        sys.exit(1)

    return pane_id, cwd


def open_overlay(entrypoint: str) -> None:
    pane_id, cwd = get_source_pane()
    subprocess.run(
        [
            herdr_bin(),
            "plugin",
            "pane",
            "open",
            "--plugin",
            plugin_id(),
            "--entrypoint",
            entrypoint,
            "--placement",
            "overlay",
            "--env",
            f"SOURCE_PANE_ID={pane_id}",
            "--env",
            f"SOURCE_PANE_CWD={cwd}",
        ],
        check=False,
    )


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
    subprocess.run(cmd, check=False)


def main() -> None:
    args = sys.argv[1:]
    if "--open-pane" in args:
        open_overlay("picker")
    elif "--open-links-pane" in args:
        open_overlay("link-picker")
    elif "--links" in args:
        run_picker("links")
    else:
        run_picker("pick")


if __name__ == "__main__":
    main()
