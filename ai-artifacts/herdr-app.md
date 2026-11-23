# Herdr.app backend and float flow

Herdr.app is the window (`herdr-app`) over `hc` terminals. The legacy Herdr multiplexer (`herdr pane ...`) is a separate backend and is unchanged.

## Flow

1. A key in `keys.json` runs `mod.open:termscope` (files) or `mod.open:termscope-links`.
2. The mod (`herdr-app/mods/*/main.js`, rendered by `scripts/install-herdr-app.sh`) is a 1x1 headless overlay. It reads `focused()` for terminal and cwd, runs `/usr/bin/env -i ... python3 termscope_app.py --open|--open-links --terminal T --cwd D`, and calls `notify` on failure.
3. `termscope_app.py` builds a `herdr-ui float` JSON request (`build_float_request`) with argv `termscope pick|links --multiplexer app --pane-id T ...`, and runs `herdr-ui float` with `HC_TERMINAL_ID=T`. `herdr-ui` creates the float as a child of the source terminal; it closes when the picker exits.
4. The picker runs `AppBackend` (`termscope`, name `app`). The pane id is the source terminal id. `detect_backend` picks it for `^t[0-9a-z]+$`.

## AppBackend

- cwd: `hc get T` foreground cwd, else cwd.
- screen: `hc read T --json --lines 0` (visible screen). hc does not join soft-wrapped rows, so a wrapped path can be missed.
- open: `open_target` split -> `herdr-app do pane.split --pane <pane> --direction right --argv [...]`; tab -> `tab.new` in the source space; popup -> exec nvim in the float. The pane id comes from `herdr-app ls`.
- annotate: `hc send T ...`; slash command when `status.app` names an agent, shell command otherwise.
- messages: stderr (no CLI toast exists).
- settings: `TERMSCOPE_CONFIG`, else `HERDR_PLUGIN_CONFIG_DIR/config.toml`, else the legacy `~/.config/herdr/plugins/config/termscope/config.toml`.

## Installer

`scripts/install-herdr-app.sh` (`--dry-run`, `--uninstall`) copies files to `TERMSCOPE_APP_HOME`, renders mods into `HERDR_APP_HOME/mods`, and merges keys through `scripts/herdr_app_keys.py` (adds only unbound keys, backs up `keys.json`, removes only exact matches).
