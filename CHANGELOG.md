# Changelog

## [0.3.1](https://github.com/iurysza/termscope/compare/v0.3.0...v0.3.1) (2026-09-08)


### Bug Fixes

* find Homebrew Television in Herdr panes ([472e53a](https://github.com/iurysza/termscope/commit/472e53ac5f52a03d15fc86e732334dfb8d5b5035))
* **pick:** match repo paths only at path boundaries ([#6](https://github.com/iurysza/termscope/issues/6)) ([eeca533](https://github.com/iurysza/termscope/commit/eeca533af6951a11bbf5868308ed882f40dc62e8))

## [0.3.0](https://github.com/iurysza/termscope/compare/v0.2.0...v0.3.0) (2026-08-19)


### Features

* capture every pane in the current window/tab; merge visible links into the file picker ([5187e1e](https://github.com/iurysza/termscope/commit/5187e1ea978c0d08855fd97416a2d32cbb78690d))


### Bug Fixes

* **herdr:** keep source pane in direct capture ([c41c60c](https://github.com/iurysza/termscope/commit/c41c60c3bfffb60ce467759c4a7e4fd4d8627fcd))
* **pick:** keep full-repo fallback when only URLs are visible; harden pane enumeration ([d5fe32a](https://github.com/iurysza/termscope/commit/d5fe32aa19795b2d366a592f4a931294e0ac7ec5))
* **pick:** keep URLs when repo index is empty ([bfb005e](https://github.com/iurysza/termscope/commit/bfb005e2c7569661528682335ae4d953ab18eced))

## [0.2.0](https://github.com/iurysza/termscope/releases/tag/v0.2.0) (2026-07-17)

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
