#!/usr/bin/env python3
"""Merge or remove Termscope key bindings in a Herdr.app keys.json.

Only adds a key to `global` when it is unbound. Never overwrites a binding.
`remove` deletes only bindings whose value is exactly what we would add.
"""

from __future__ import annotations

import json
import sys

BINDINGS = {
    "ctrl-shift-a": "mod.open:termscope",
    "ctrl-shift-e": "mod.open:termscope-links",
}


def merge(keys: dict, bindings: dict[str, str] | None = None) -> tuple[dict, list[str], list[str]]:
    """Return (new keys, added keys, skipped notices). Does not mutate input."""
    bindings = BINDINGS if bindings is None else bindings
    out = json.loads(json.dumps(keys))
    section = out.setdefault("global", {})
    added: list[str] = []
    skipped: list[str] = []
    for key, action in bindings.items():
        current = section.get(key)
        if current is None:
            section[key] = action
            added.append(key)
        elif current == action:
            skipped.append(f"{key} already bound to {action}")
        else:
            skipped.append(f"{key} is already bound to {current}; not adding {action}")
    return out, added, skipped


def remove(keys: dict, bindings: dict[str, str] | None = None) -> tuple[dict, list[str]]:
    """Return (new keys, removed keys). Only exact matches are removed."""
    bindings = BINDINGS if bindings is None else bindings
    out = json.loads(json.dumps(keys))
    section = out.get("global", {})
    removed = [k for k, a in bindings.items() if section.get(k) == a]
    for key in removed:
        del section[key]
    return out, removed


def main(argv: list[str]) -> int:
    """herdr_app_keys.py add|remove <keys.json> [--dry-run]: prints notices, writes file."""
    if len(argv) < 3 or argv[1] not in ("add", "remove"):
        print("usage: herdr_app_keys.py add|remove <keys.json> [--dry-run]", file=sys.stderr)
        return 2
    action, path = argv[1], argv[2]
    dry = "--dry-run" in argv[3:]
    try:
        with open(path, encoding="utf-8") as fh:
            keys = json.load(fh)
    except FileNotFoundError:
        keys = {}
    except (OSError, ValueError) as exc:
        print(f"termscope: cannot read {path}: {exc}", file=sys.stderr)
        return 1
    if action == "add":
        new, changed, notices = merge(keys)
    else:
        new, changed = remove(keys)
        notices = []
    for note in notices:
        print(f"notice: {note}")
    for key in changed:
        print(f"{'would ' if dry else ''}{action}: {key}")
    if changed and not dry:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(new, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
