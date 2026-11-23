# Rex backend and floating layer

Rex (Rex Beta.app) is a separate backend from tmux, legacy Herdr, and Herdr.app. The picker is still `termscope`. `termscope_rex.py` only creates the floating layer.

## Flow

1. A Rex terminal has `REX_SESSION` and `REX_BLOCK`. A key action may be outside that terminal, so it passes `--session` and `--block` from `ctx`.
2. `termscope_rex.py` resolves the Rex CLI: `REX_BIN`, else `rex` on `PATH`, else `~/Library/Application Support/com.superlogical.rex/RexServer/Versions/Current/Rex Server.app/Contents/MacOS/rex`.
3. The working directory comes from `com.superlogical.terminal.pwd` (a `file://` URL, or a plain absolute path). An empty `pwd` falls back to `process.foreground.cwd`, then to the launcher's cwd. `--cwd` skips both calls.
4. The window comes from `session.describe_block` (`block.window_id`). If that field is missing, `session.view` is walked the way `herdr-ui` walks it: windows, layers, blocks. No window id means Rex uses the active window.
5. `rex api call -s SESSION session.new_layer -` creates the layer. Bounds are `[0.1, 0.2, 0.8, 0.6]` (80% by 60%, centred). `focus` is true. The block flavor is `com.superlogical.terminal.shell` with `shell: "none"`, `cwd`, and `command` set to the picker: `termscope pick|links --multiplexer rex --pane-id BLOCK`. `REX_SESSION` is passed with `/usr/bin/env` because `shell: "none"` starts the command with the server environment. The layer options match `herdr-ui` (`shell`, `command`, `cwd`); `exit` is left at Rex's default.

## RexBackend

The pane id is the source block id. Inside the layer, `REX_BLOCK` is the layer's own block, so capture and open use `--pane-id`, not `REX_BLOCK`.

- cwd: the same `pwd` then `process` lookup as the launcher.
- screen: `rex capture -s SESSION -b BLOCK --trim --unwrap`. This is the screen plus the scrollback, so the backend keeps the last `rows` lines from the block's `size` method (verified on Rex 0.1.0-preview.21: `{"columns":80,"rows":24,...}`). `--unwrap` joins soft-wrapped lines. A 15s timeout returns empty text, and the picker then falls back to the repo list.
- open: `open_target` from the Herdr.app settings path (`TERMSCOPE_CONFIG`, else the plugin file). `split` is `rex split --split=right`. `tab` is `rex run` (a new window). `popup` execs nvim in the layer when the picker has a TTY. `close_on_exit` false adds `--keep-open`.
- annotate: `rex send` then `rex send-key enter`. A foreground name of `pi`, `opencode`, `claude`, or `codex`, or an empty name, sends `/plannotator-annotate`. Any other name runs `plannotator annotate`.
- messages: stderr.
- auto: a `block:` pane id selects Rex. So do `REX_SESSION` and `REX_BLOCK` when the pane id is empty or equal to `REX_BLOCK`. tmux (`%…`), Herdr (`w…:p…` or `N-N`), and Herdr.app (`t…`) ids still win, including when those variables are inherited.

## What Rex can and cannot do

`rex capture` and `com.superlogical.terminal.format` both return terminal text. The CLI documents capture as the screen and the scrollback. `format` is described as the current screen, and people who have run `rex api describe` report the same formatting flags (`format`, `unwrap`, `trim`) with no viewport or scroll-offset field. This backend uses `rex capture` and clips it to the row count from `size`.

A file opens in a new block (`rex split`, `rex run`) or in the picker layer (`popup`). A URL opens with the system opener, the same path the other backends use. Rex has no method that opens an arbitrary URL inside a block.
