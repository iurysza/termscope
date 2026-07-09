# termscope

[![CI](https://github.com/iurysza/termscope/actions/workflows/ci.yml/badge.svg)](https://github.com/iurysza/termscope/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![herdr 0.7+](https://img.shields.io/badge/herdr-0.7%2B-8a2be2)
![platforms: macOS • Linux](https://img.shields.io/badge/platforms-macOS%20%E2%80%A2%20Linux-informational)

Open files and links that are already visible in your terminal.

`termscope` turns the current pane into a menu: it reads the visible text, finds
real paths and URLs, shows them in `fzf`, then opens the selected target next to
the pane you were looking at.

```text
agent output / stack trace / git status
        │
        ▼
Ctrl-Shift-A  →  fzf picker  →  nvim split at src/main.py:42
Ctrl-E        →  fzf picker  →  browser opens visible URL
```

## Why

A stack trace says `src/server/main.py:42`. A README mentions
`docs/install.md`. An agent suggests `tests/test_api.py`. The terminal already
knows the target; your hands should not have to select, copy, cd, paste, and add
the line number.

Termscope is intentionally conservative:

- scans only what is visible in the active pane
- checks paths against the repo/worktree on disk
- preserves `file:line` targets
- falls back to a full repo file picker when nothing visible matches
- opens results outside the picker overlay, so the original pane stays intact

## Requirements

- [Herdr](https://herdr.dev) `>= 0.7.0` or tmux
- Python `>= 3.10`
- [`fd`](https://github.com/sharkdp/fd)
- [`fzf`](https://github.com/junegunn/fzf)
- `nvim` for the default file-open action
- `open` on macOS or `xdg-open` on Linux for default-app opens

Native Windows is not claimed yet. WSL may work through `wslview` when your WSL
environment provides it.

## Install as a Herdr plugin

```bash
herdr plugin install iurysza/termscope
```

For local development:

```bash
git clone https://github.com/iurysza/termscope.git
herdr plugin link ./termscope
```

Verify Herdr sees the actions:

```bash
herdr plugin action list --plugin termscope
```

## Bind keys in Herdr

Herdr plugins register actions; keybindings still live in your
`~/.config/herdr/config.toml`.

```toml
[[keys.command]]
key = "ctrl+shift+a"
type = "plugin_action"
command = "termscope.open"
description = "visible-screen file picker"

[[keys.command]]
key = "ctrl+e"
type = "plugin_action"
command = "termscope.open-links"
description = "visible-screen link picker"
```

Reload config:

```bash
herdr server reload-config
```

## Use it

| Key | Action |
| --- | --- |
| `Ctrl-Shift-A` | Open visible file picker |
| `Ctrl-E` | Open visible link picker |

File picker controls:

| Key | Action |
| --- | --- |
| `Enter` | Open in a new Neovim split beside the source pane |
| `Ctrl-O` | Open with the default app |
| `Ctrl-Y` | Send `/plannotator-annotate <file>` to the source pane |
| `Ctrl-S` | Toggle appearance order / alphabetical sort |

Link picker controls:

| Key | Action |
| --- | --- |
| `Enter` | Open URL in the browser/default opener |
| `Ctrl-Y` | Copy URL to clipboard |
| `Ctrl-S` | Toggle appearance order / alphabetical sort |

## tmux usage

Herdr is the main plugin target, but the same picker works in tmux.

```tmux
set -g @termscope "/path/to/termscope/termscope"

bind-key -n C-S-a run-shell "tmux display-popup -E -w 80% -h 60% '#{@termscope} pick --pane-path #{q:pane_current_path} --pane-id #{q:pane_id}'"
bind-key -n C-e run-shell "tmux display-popup -E -w 80% -h 60% '#{@termscope} links --pane-path #{q:pane_current_path} --pane-id #{q:pane_id}'"

bind-key -T copy-mode-vi C-S-a run-shell "tmux display-popup -E -w 80% -h 60% '#{@termscope} pick --pane-path #{q:pane_current_path} --pane-id #{q:pane_id}'"
bind-key -T copy-mode-vi C-e run-shell "tmux display-popup -E -w 80% -h 60% '#{@termscope} links --pane-path #{q:pane_current_path} --pane-id #{q:pane_id}'"

bind-key -T copy-mode-vi 'o' send -F -X copy-pipe-and-cancel "#{@termscope} open --mode nvim --pane-path #{q:pane_current_path} --pane-id #{q:pane_id}"
bind-key -T copy-mode-vi 'O' send -F -X copy-pipe-and-cancel "#{@termscope} open --mode default --pane-path #{q:pane_current_path} --pane-id #{q:pane_id}"
bind-key -T copy-mode-vi P run-shell "tmux display-popup -E -w 80% -h 60% '#{@termscope} pick --pane-path #{q:pane_current_path} --pane-id #{q:pane_id}'"
```

In tmux copy-mode these bindings preserve the scrolled viewport instead of
jumping back to the live bottom of the pane.

## Configuration

| Environment variable | Purpose |
| --- | --- |
| `TERMSCOPE_OPENER` | Override default opener, e.g. `open -a Zen` or `open -a Firefox` |
| `TERMSCOPE_SORT` | Default sort mode: `appearance` or `alpha` |
| `TERMSCOPE_LOG` | Path to the JSON event log |
| `TERMSCOPE_DEBUG_DIR` | Directory for per-run debug dumps |

Examples:

```bash
export TERMSCOPE_OPENER='open -a Zen'
export TERMSCOPE_SORT=alpha
```

## Dry run / debug

See what the scanner would offer without opening `fzf`:

```bash
./termscope scan --pane-path "$PWD" --pane-id "$HERDR_PANE_ID" --multiplexer herdr
```

Enable debug dumps:

```bash
export TERMSCOPE_DEBUG_DIR=/tmp/termscope-debug
```

Each run writes the captured screen, indexed files, candidates, and final
selection decision.

## How it works

Herdr plugin actions run without a TTY, so `termscope.open` does not run `fzf`
directly. It opens a Herdr-managed overlay pane. That pane inherits the source
pane id/cwd, captures visible text with `herdr pane read --source visible`, scans
the repo with `fd`, and runs the interactive picker.

When you choose a file, Termscope asks Herdr to split beside the source pane and
runs `nvim +line path`. For URLs, it uses the default opener unless
`TERMSCOPE_OPENER` is set.

## Development

```bash
python3 -m py_compile termscope termscope_herdr.py
python3 -m unittest discover -s tests
herdr plugin link "$PWD"
herdr plugin action invoke termscope.open
```

The repo intentionally has no package manager or build step. Herdr installs it
by cloning the repo and reading `herdr-plugin.toml`.

## Publishing notes

To appear in the Herdr marketplace, the GitHub repo must be public and include
the `herdr-plugin` topic. Recommended repo metadata:

- description: `Open files and links already visible on your terminal screen.`
- topics: `herdr-plugin`, `herdr`, `fzf`, `tmux`, `terminal`, `python`

## License

[MIT](LICENSE) © iury souza
