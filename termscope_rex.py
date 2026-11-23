#!/usr/bin/env python3
"""Rex launcher: open the termscope picker in a floating layer.

Run from a Rex terminal, or from a key action that passes --session and --block:
    termscope_rex.py --open            files in the focused block
    termscope_rex.py --open-links      links in the focused block
Optional: --session <id>  --block <id>  --cwd <dir>  --sort appearance|alpha

The layer is `session.new_layer` over the block's window, the same call
`herdr-ui float` makes when REX_SESSION and REX_BLOCK are set. The command
runs with shell "none", so the picker is the terminal's process.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

import termscope_app

HERE = Path(__file__).resolve().parent
# 80% by 60%, centred. Same size as the Herdr picker popup.
LAYER_BOUNDS = [0.1, 0.2, 0.8, 0.6]
_LAYER_ID_RE = re.compile(r"^layer:[0-9A-Fa-f-]+$")
_picker_module = None


def _env_assignment(name: str, value: str) -> str | None:
    """One /usr/bin/env argument, or None when the value cannot be one argument."""
    if not value or "\n" in value or "\0" in value:
        return None
    return f"{name}={value}"


def _picker():
    """Load the picker script (no .py suffix) once."""
    global _picker_module
    if _picker_module is None:
        path = HERE / "termscope"
        name = "termscope_picker"
        loader = SourceFileLoader(name, str(path))
        spec = importlib.util.spec_from_loader(name, loader)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load {path}")
        module = importlib.util.module_from_spec(spec)
        # dataclass looks the class's module up in sys.modules while the file loads.
        sys.modules[name] = module
        loader.exec_module(module)
        _picker_module = module
    return _picker_module


def build_layer_request(
    subcommand: str,
    block: str,
    cwd: str,
    session: str,
    sort: str | None = None,
    script: str | None = None,
    python: str | None = None,
    television: str | None = None,
    window_id: str | None = None,
) -> dict:
    """JSON body for `rex api call session.new_layer`. Pure, so it can be tested."""
    argv = [
        python or sys.executable,
        script or str(HERE / "termscope"),
        subcommand,
        "--pane-path", cwd,
        "--pane-id", block,
        "--multiplexer", "rex",
    ]
    if sort in ("appearance", "alpha"):
        argv.extend(["--sort", sort])
    # shell=none starts the command with the server environment, not the
    # caller's. Pass the session, and Television when we know its path.
    env_args = [item for item in (
        _env_assignment("TERMSCOPE_TV", television or ""),
        _env_assignment("REX_SESSION", session),
    ) if item]
    if env_args:
        argv = ["/usr/bin/env", *env_args, *argv]
    body: dict = {
        "bounds": list(LAYER_BOUNDS),
        "focus": True,
        "layout": {
            "block": {
                "flavor": "com.superlogical.terminal.shell",
                "label": "termscope",
                "options": {
                    "shell": "none",
                    "command": argv,
                    "cwd": cwd,
                },
            }
        },
    }
    if window_id:
        body["window_id"] = window_id
    return body


def parse_layer_id(stdout: str) -> str | None:
    """Layer id from a new_layer result, or None when the result is unusable."""
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or data.get("error") or data.get("ok") is False:
        return None
    layer = data.get("layer_id")
    if isinstance(layer, str) and _LAYER_ID_RE.fullmatch(layer):
        return layer
    return None


def _failure_detail(stdout: str, stderr: str, code: int) -> str:
    try:
        data = json.loads(stdout) if stdout.strip() else None
    except json.JSONDecodeError:
        data = None
    if isinstance(data, dict):
        err = data.get("error")
        if isinstance(err, dict):
            err = err.get("message") or json.dumps(err)
        if err:
            return str(err)[:500]
    text = stderr.strip() or stdout.strip()
    return (text[:500] if text else f"exit {code}")


def launch(args: argparse.Namespace) -> int:
    session = (args.session or os.environ.get("REX_SESSION", "")).strip()
    block = (args.block or os.environ.get("REX_BLOCK", "")).strip()
    if not session:
        print("termscope: no Rex session (pass --session or set REX_SESSION)", file=sys.stderr)
        return 1
    if not block:
        print("termscope: no Rex block (pass --block or set REX_BLOCK)", file=sys.stderr)
        return 1
    picker = _picker()
    rex = picker.rex_binary()
    if not rex:
        print("termscope: rex not found (set REX_BIN, or install rex on PATH)", file=sys.stderr)
        return 1
    # RexBackend reads the session and block from the environment.
    os.environ["REX_SESSION"] = session
    os.environ["REX_BLOCK"] = block
    backend = picker.RexBackend()
    if args.cwd:
        cwd = args.cwd
    else:
        cwd = str(backend.resolve_source_pane_path(Path.cwd(), block))
    request = build_layer_request(
        "links" if args.open_links else "pick",
        block,
        cwd,
        session,
        sort=termscope_app.resolve_sort(args.sort),
        television=termscope_app.television_bin(),
        window_id=backend.window_id(block),
    )
    result = subprocess.run(
        [rex, "api", "call", "-s", session, "session.new_layer", "-"],
        input=json.dumps(request),
        text=True,
        capture_output=True,
        check=False,
    )
    layer = parse_layer_id(result.stdout) if result.stdout.strip() else None
    if result.returncode != 0 or not layer:
        detail = _failure_detail(result.stdout, result.stderr, result.returncode)
        print(f"termscope: float failed: {detail}", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="termscope_rex")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--open", action="store_true", help="file picker")
    mode.add_argument("--open-links", action="store_true", help="link picker")
    parser.add_argument("--session", default=None)
    parser.add_argument("--block", default=None)
    parser.add_argument("--cwd", default=None)
    parser.add_argument("--sort", choices=["appearance", "alpha"], default=None)
    return launch(parser.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
