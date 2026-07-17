# Changelog

## 0.2.0 - Unreleased

### Added

- Television channels with file previews, always-visible action hints, and `Ctrl-S` appearance/alphabetical source cycling.
- Built-in text and directory previews when `bat` is unavailable.
- Install-time Television provisioning through Homebrew for Herdr plugin installs.

### Changed

- Replaced fzf with Television `0.15+`.
- Replaced full-pane Herdr overlays with bounded `80% × 60%` session-modal popups.
- Raised the minimum Herdr version to `0.7.4`.

### Fixed

- Encoded picker targets before Television preview interpolation so filenames cannot inject shell syntax.
- Propagated Herdr popup and Television runtime failures while keeping user cancellation successful.
- Used the Plannotator slash command in agent panes and the CLI command in plain shells.
- Bounded preview reads by size, output, and wall-clock time.

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
