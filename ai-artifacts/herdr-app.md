# Herdr.app backend and float flow

Herdr.app is the window (`herdr-app`) over `hc` terminals. The legacy Herdr multiplexer (`herdr pane ...`) is a separate backend and is unchanged.

## Flow

1. A key in `keys.json` runs `mod.open:termscope` (files) or `mod.open:termscope-links`.
2. The mod (`herdr-app/mods/*/main.js`, rendered by `scripts/install-herdr-app.sh`) is a 1x1 headless overlay. It reads `focused()` for terminal and cwd, then runs `/usr/bin/env HC_BIN_PATH=... HERDR_APP_BIN_PATH=... HERDR_UI_BIN=... python3 termscope_app.py --open|--open-links --terminal T --cwd D`. That keeps the environment `exec` supplied (`TERMSCOPE_*`, `HERDR_APP_HOME`, `HC_SOCKET`, `XDG_*`) and only pins the tool paths from install. The overlay stays up until that process returns, then closes. Closing first cancels the view task, so `exec` may never start and a failure `notify` is lost.
3. `termscope_app.py` builds a `herdr-ui float` JSON request (`build_float_request`) with argv `termscope pick|links --multiplexer app --pane-id T ...`, and runs `herdr-ui float` with `HC_TERMINAL_ID=T`. `--sort` is added only when `--sort` or a valid `TERMSCOPE_SORT` is set; otherwise the picker reads its own environment. `herdr-ui` creates the float as a child of the source terminal; it closes when the picker exits.
4. The picker runs `AppBackend` (`termscope`, name `app`). The pane id is the source terminal id. `detect_backend` picks it for `^t[0-9a-z]+$`.

## AppBackend

- cwd: `hc get T` foreground cwd, else cwd.
- screen: `hc read T --json --lines 0` (visible screen). hc does not join soft-wrapped rows, so a wrapped path can be missed.
- open: `open_target` split -> `herdr-app do pane.split --pane <pane> --direction right --argv [...]`; tab -> `tab.new --space <source space>` (exit 1 when `herdr-app ls` has no space for the terminal); popup -> exec nvim in the float. The pane and space ids come from `herdr-app ls`.
- annotate: `hc send T ...`; slash command when `status.app` names an agent, shell command otherwise.
- messages: stderr (no CLI toast exists).
- settings: `TERMSCOPE_CONFIG`, else `HERDR_PLUGIN_CONFIG_DIR/config.toml`, else the legacy `~/.config/herdr/plugins/config/termscope/config.toml`.

## Installer

`scripts/install-herdr-app.sh` (`--dry-run`, `--uninstall`) copies files to `TERMSCOPE_APP_HOME`, renders mods into `HERDR_APP_HOME/mods`, and merges keys through `scripts/herdr_app_keys.py` (adds only unbound keys, backs up `keys.json`, removes only exact matches).
