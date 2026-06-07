# Plannotator annotate hardening — implementation summary

## Changes

### 1. `tmux-file-picker` — `send_annotate_command()` hardened

- Checks source pane `#{pane_in_mode}` before sending the slash command.
- If `1` (pane in copy mode), runs `tmux send-keys -t <pane> -X cancel` first.
- Then sends literal `/plannotator-annotate <quoted path>` and Enter as before.
- After send, fires `tmux display-message "Plannotator annotation requested"`.
- Folder blocking behavior unchanged (still guarded in `_open_target`).

### 2. `tests/test_tmux_file_picker.py` — new `TestSendAnnotateCommand` class

Three new tests:
- **`test_copy_mode_cancelled_before_slash`**: verifies that when `pane_in_mode=1`, cancel is sent before the slash command + Enter sequence, and the display-message fires.
- **`test_not_in_copy_mode_no_cancel`**: verifies that when `pane_in_mode=0`, no cancel is sent, but the slash command + Enter + display-message still fire.
- **`test_path_with_spaces_is_quoted`**: verifies that `shlex.quote` wraps the full absolute path in single quotes, confirming space safety.

### 3. `README.md` — updated

- Keys section updated to mention automatic copy-mode cancel.
- Notes section updated to reflect the copy-mode safety.

## Test results

```
Ran 60 tests in 0.013s
OK
```

All existing tests pass. All new tests pass.

## Caveats

- `shlex.quote` wraps the full path in single quotes. Pi's slash command handler strips wrapping quotes, so this works. Paths containing literal single quotes may not parse correctly (known sharp edge, not specific to this change).
- Copy-mode cancel is safe: if Pi is mid-generation, the cancel exits copy mode but doesn't interrupt Pi's output. The slash command then lands at Pi's next prompt.
- Non-Pi pane guard is still documentation-only (README note). No runtime check for pane process name.

## Files changed

- `tmux-file-picker` — `send_annotate_command()` function (lines 577-603)
- `tests/test_tmux_file_picker.py` — `TestSendAnnotateCommand` class (3 new tests)
- `README.md` — Keys and Notes sections
