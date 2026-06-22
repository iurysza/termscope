# termscope

Open files and links that are already on your terminal screen.

## The problem

A stack trace, README, git status, or agent response mentions `src/main.py:42`.
You select it, copy it, change directory, open your editor, paste it, and add
`:42`. That is five or six context switches for something the terminal already
showed you.

`termscope` removes the middle steps. One key press turns the visible pane
into a focused list of real files and links. Pick one and open it in Neovim,
your default app, or the browser.

## What it does

- Captures the currently visible text from a tmux or Herdr pane.
- Builds an authoritative index of files and directories from the pane's git
  root using `fd`.
- Shows only real paths and URLs that appear in the visible output.
- Opens results next to the source pane, not inside the picker overlay.
- Falls back to a full repo file listing if nothing visible matches.

## Why it matters

Terminal multiplexers are great at showing context, but terrible at acting on
it. `termscope` closes that loop: the screen becomes a menu.

It is conservative on purpose. It does not fuzzy-search arbitrary text. It does
not guess. It only offers files and links that are actually visible and that
actually exist.

## Install

Dependencies: `tmux` or `herdr`, `fd`, `fzf`, `python3`, `nvim`, and a default
opener (`open` on macOS, `xdg-open` on Linux, `wslview` on WSL).

```sh
git clone https://github.com/iurysza/termscope.git
cd termscope
```

## Usage

| Key | Action |
| --- | --- |
| `Ctrl-Shift-a` | Open visible file picker |
| `Ctrl-e` | Open visible link picker |

Inside the file picker:

| Key | Action |
| --- | --- |
| `Enter` | Open in a new Neovim split |
| `Ctrl-o` | Open with the default app |
| `Ctrl-y` | Annotate the file in the source pane (Plannotator integration) |
| `Ctrl-s` | Toggle appearance / alphabetical sort |

Inside the link picker:

| Key | Action |
| --- | --- |
| `Enter` | Open URL in browser |
| `Ctrl-y` | Copy URL to clipboard |
| `Ctrl-s` | Toggle appearance / alphabetical sort |

In tmux copy-mode the same bindings work without canceling copy mode, so the
scrolled viewport is preserved.

## tmux configuration

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

## Herdr configuration

Link the plugin from the repo root:

```sh
herdr plugin link /path/to/termscope
```

Add keybindings to `~/.config/herdr/config.toml`:

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

Then reload Herdr:

```sh
herdr server reload-config
```

## Dry run

See what `termscope` would find without opening `fzf`:

```sh
./termscope scan --pane-path "$PWD" --pane-id "$TMUX_PANE"
```

## Sorting

By default the list matches the order in which paths appear on screen. Switch
to alphabetical order with `Ctrl-s` while the picker is open, or pass
`--sort alpha` at launch time:

```sh
./termscope pick --pane-path "$PWD" --pane-id "$TMUX_PANE" --sort alpha
```

Alphabetical sorting naturally keeps subfolders next to their parent folder:

```
README.md
src
src/main.py
src/utils.py
tests
```

You can also set a default with the `TERMSCOPE_SORT` environment variable
(`appearance` or `alpha`). Press `Ctrl-s` at any time to override it.

## Configuration

| Environment variable | Purpose |
| --- | --- |
| `TERMSCOPE_OPENER` | Override the default opener, e.g. `open -a Firefox` |
| `TERMSCOPE_SORT` | Default sort mode: `appearance` or `alpha` |
| `TERMSCOPE_LOG` | Path to the JSON log file |
| `TERMSCOPE_DEBUG_DIR` | Directory for per-run debug dumps |

## Tests

```sh
python3 -m unittest discover -s tests
python3 -m py_compile termscope termscope_herdr.py
```

## License

MIT
