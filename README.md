# tmux-file-picker

A tmux file picker for opening files mentioned in the currently visible pane output.

## What it does

- Captures only the currently visible text from the source tmux pane (not scrollback history).
- Builds an authoritative file/dir index from the pane's git root with `fd`.
- Shows only real files/dirs that appear in the visible pane output by path, basename, or visible absolute path.
- Opens results from the original source pane, not the popup pane.
- If no visible files or folders are found, a tmux message is shown and no fzf popup opens.

## Keys

From the main tmux pane:

- `Ctrl-Shift-a` (`C-S-a`) opens the visible-screen picker directly.
- `Ctrl-e` also opens the picker (legacy binding).

Inside the picker:

- `Enter` opens in a new `nvim` split.
- `Ctrl-o` opens with the default app.
- `Ctrl-y` annotates the selected file via Plannotator (sends `/plannotator-annotate <file>` to the source pane). Folders are blocked with a tmux message.

In tmux copy mode:

- `o` opens the selected text in a new `nvim` split.
- `O` opens the selected text with the default app.
- `P` opens the visible-screen file picker without canceling copy mode.
- `Ctrl-e` opens the visible-screen picker without canceling copy mode.
- `Ctrl-Shift-a` opens the visible-screen picker without canceling copy mode (preserves scrolled viewport).

## Script

- `tmux-file-picker` — single Python script with `pick`, `open`, `fallback`, and `scan` subcommands.

## Dry-run / Debug

Use the `scan` subcommand to see what the picker would find without opening fzf:

```sh
/path/to/user/scripts/tmux-file-picker/tmux-file-picker scan --pane-path /path --pane-id %1
```

This prints JSON with capture details, candidate count, and the candidate list.

Set `TMUX_FILE_PICKER_DEBUG_DIR` to a directory path for per-run debug dumps:

- `screen.txt` — captured pane text
- `files.txt` — indexed repo files
- `candidates.txt` — visible candidates
- `fzf.json` — fzf query/key/selection
- `decision.json` — full decision state

The debug directory path is printed to stderr.

## Dependencies

- `tmux`
- `fd`
- `fzf`
- `python3`
- `nvim`
- A default opener: macOS `open`, WSL `wslview`, or Linux `xdg-open`

Override the opener with the `TMUX_FILE_PICKER_OPENER` environment variable.

## tmux config

```tmux
# Normal mode: open visible-screen picker
bind-key -n C-S-a run-shell "tmux display-popup -E -w 80% -h 60% '/path/to/user/scripts/tmux-file-picker/tmux-file-picker pick --pane-path #{q:pane_current_path} --pane-id #{q:pane_id}'"

# Copy-mode: open picker without canceling copy mode (preserves scrolled viewport)
bind-key -T copy-mode-vi C-S-a run-shell "tmux display-popup -E -w 80% -h 60% '/path/to/user/scripts/tmux-file-picker/tmux-file-picker pick --pane-path #{q:pane_current_path} --pane-id #{q:pane_id}'"

# Legacy binding (also works)
bind-key -n C-e run-shell "tmux display-popup -E -w 80% -h 60% '/path/to/user/scripts/tmux-file-picker/tmux-file-picker pick --pane-path #{q:pane_current_path} --pane-id #{q:pane_id}'"
bind-key -T copy-mode-vi C-e run-shell "tmux display-popup -E -w 80% -h 60% '/path/to/user/scripts/tmux-file-picker/tmux-file-picker pick --pane-path #{q:pane_current_path} --pane-id #{q:pane_id}'"

# Copy-mode bindings
bind-key -T copy-mode-vi 'o' send -F -X copy-pipe-and-cancel "/path/to/user/scripts/tmux-file-picker/tmux-file-picker open --mode nvim --pane-path #{q:pane_current_path} --pane-id #{q:pane_id}"
bind-key -T copy-mode-vi 'O' send -F -X copy-pipe-and-cancel "/path/to/user/scripts/tmux-file-picker/tmux-file-picker open --mode default --pane-path #{q:pane_current_path} --pane-id #{q:pane_id}"
bind-key -T copy-mode-vi P run-shell "tmux display-popup -E -w 80% -h 60% '/path/to/user/scripts/tmux-file-picker/tmux-file-picker pick --pane-path #{q:pane_current_path} --pane-id #{q:pane_id}'"
```

## Tests

```sh
python3 -m unittest discover -s tests
```

## Notes

- The picker is strict visible-screen only: it never falls back to showing all repo files.
- `Shift+Enter` is intentionally not used because terminals/tmux/fzf often collapse it to plain `Enter`.
- `Ctrl-o` is reliable and mnemonic: open with default app.
- `Ctrl-y` sends `/plannotator-annotate <file>` into the source pane literally; use it only when the source pane is a Pi agent session.
