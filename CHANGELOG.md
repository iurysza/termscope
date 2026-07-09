# Changelog

## 0.1.0 - 2026-07-09

### Added

- Herdr plugin manifest with file and link picker actions.
- Herdr overlay wrapper that opens interactive `fzf` panes from plugin actions.
- tmux support for visible-pane file/link picking, including copy-mode viewport capture.
- Real-path scanning against the current repo using `fd`.
- `file:line` parsing for Neovim opens.
- Link picker with copy-to-clipboard support.
- Sort toggle with `Ctrl-S`.
- Plannotator annotate shortcut with `Ctrl-Y`.

### Changed

- URL opening now uses the default opener by default; set `TERMSCOPE_OPENER` for app-specific browsers.
