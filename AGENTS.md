# AGENTS.md

## Project

`tmux-file-picker` is a small terminal integration tool. Keep it portable, boring, and easy to wire into other agents.

## First stop

- Check `ai-artifacts/` if this repo has one.
- Use existing goal docs under `goals/` when they match the task. They capture decisions, facts, and smoke-test notes.

## Design priorities

- Tmux is the primary runtime. Preserve source-pane behavior and copy-mode viewport behavior.
- Neovim is the primary editor integration. Keep `nvim` open paths simple and predictable.
- Agent integrations should be easy to add without making the core picker agent-specific.
- Prefer explicit subcommands and small functions over framework code.
- Keep dependencies minimal: Python stdlib plus terminal tools already in the README (`tmux`, `fd`, `fzf`, `nvim`, default opener).
- Favor pragmatic extension points: env vars, small action modes, documented CLI behavior.

## Coding rules

- Read `README.md`, the relevant code, and relevant `goals/` docs before editing.
- Keep the main script portable Python. No project-local virtualenv required for normal use.
- Preserve conservative matching. Do not add fuzzy/path-wide behavior that shows files not visible in the pane unless explicitly requested.
- Avoid broad fallbacks. If no visible candidates exist, show a tmux message and stop.
- Keep tmux command construction explicit and testable.
- Be careful with `tmux send-keys`; send literal text when typing commands into agent panes.
- Isolate integration-specific behavior, like Plannotator, behind named actions.
- Update tests and README when behavior or keybindings change.

## Verification

For code changes, run:

```sh
python3 -m unittest discover -s tests
python3 -m py_compile tmux-file-picker
```

For picker behavior, prefer the dry-run path first:

```sh
./tmux-file-picker scan --pane-path "$PWD" --pane-id "$TMUX_PANE"
```

Manual smoke matters for tmux behavior: normal pane, copy-mode scrolled viewport, no visible files, Enter to nvim, Ctrl-o default opener, and Ctrl-y agent annotation when touched.
