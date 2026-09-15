# termscope

![termscope cover](./assets/cover.png)




[![CI](https://github.com/iurysza/termscope/actions/workflows/ci.yml/badge.svg)](https://github.com/iurysza/termscope/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![herdr 0.7.4+](https://img.shields.io/badge/herdr-0.7.4%2B-8a2be2)
![platforms: macOS • Linux](https://img.shields.io/badge/platforms-macOS%20%E2%80%A2%20Linux-informational)

Open the files and links your agent just mentioned.

`termscope` turns terminal output into a jump list. It reads the visible
terminal viewport of every pane in the current window/tab, finds real files and
URLs, then opens the selected target beside the conversation you were already
reading.

```text
visible terminal viewport
        │
        ▼
Ctrl-Shift-A  →  pick a visible file  →  nvim opens src/main.py:42
Ctrl-E        →  pick a visible link  →  browser opens it
```

## Demo

https://github.com/user-attachments/assets/af573bbc-abf9-4947-9ed6-955723b722f5


## Why

Agents constantly mention files: stack traces, changed tests, docs, configs,
links, PRs. `termscope` lets you keep up without doing the little dance:
select text, copy, cd, paste, fix the path, add the line number.

If it's visible in the window and exists in the repo, you can jump to it.

Termscope stays conservative:

- scans only the visible text of the current window's panes
- verifies paths against the repo/worktree on disk
- preserves `file:line` targets
- falls back to a full repo picker when no visible file matches
- uses a session-modal Herdr popup, leaving the tiled pane layout untouched

## Requirements

You must already have these on `PATH`. Plugin install does not install them.

- `python3` 3.10+ (the plugin and shebang call `python3`, not `python`)
- [`fd`](https://github.com/sharkdp/fd) as the `fd` binary. Debian/Ubuntu `apt install fd-find` ships `fdfind`; symlink it to `fd` (a shell alias is not enough).
- `nvim` for the default file-open action
- a URL/default-app opener: `open` on macOS, `xdg-open` on Linux, `wslview` on WSL

Host — pick one:

- [Herdr](https://herdr.dev) `>= 0.7.4` for the plugin
- tmux for the standalone `termscope` script

Picker UI:

- [Television](https://alexpasmantier.github.io/television/) `>= 0.15` (`tv` on `PATH`). `herdr plugin install` and `./scripts/install-dependencies.sh` install or upgrade it through Homebrew when needed.
- [Homebrew](https://brew.sh) only if `tv` is missing or older than `0.15`. The installer never installs Homebrew; without it, and without a new enough `tv`, install aborts before the plugin is registered.
- [`bat`](https://github.com/sharkdp/bat) optional for syntax-highlighted file previews

Native Windows is not claimed. WSL may work through `wslview` when your WSL
environment provides it.

## Install

### Herdr plugin

```bash
herdr plugin install iurysza/termscope
```

Pin a release tag with `--ref vX.Y.Z`.

Herdr clones the repo, then runs `scripts/install-dependencies.sh` before
registering the plugin. That script:

1. exits 0 if `tv` already reports Television 0.15+
2. otherwise `brew install` / `brew upgrade` the `television` formula
3. exits 1 (plugin not registered) if Homebrew is missing or `tv` is still too old

It does not install `python3`, `fd`, `nvim`, `bat`, or Homebrew.

Confirm the actions exist:

```bash
herdr plugin action list --plugin termscope
```

You should see `open` and `open-links`. The install does not bind keys; add the
bindings below and reload config.

### Local Herdr checkout

`herdr plugin link` skips install-time build commands, so provision Television
yourself:

```bash
git clone https://github.com/iurysza/termscope.git
cd termscope
./scripts/install-dependencies.sh
herdr plugin link "$PWD"
herdr plugin action list --plugin termscope
```

### tmux

Clone this repo, run `./scripts/install-dependencies.sh` (or install Television
0.15+ another way), and keep `python3`, `fd`, and `nvim` on `PATH`. Point tmux
at the `termscope` script in that clone — see [tmux usage](#tmux-usage).

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

`termscope.open` captures the **visible** text of every pane in the current
Herdr tab or tmux window, indexes the git worktree with `fd` (pane cwd if git
is missing or you are not in a repo), and opens a Television popup of matching
paths plus any visible `http://` / `https://` URLs.

- A path is listed only if it exists on disk in that tree. `file:line` is kept
  and passed to Neovim as `nvim +line path`.
- If no visible file matches, the picker falls back to the full repo listing
  (visible URLs stay first). Indexing `$HOME` is skipped.
- `termscope.open-links` is URLs only.

With the bindings above:

| Key | Action |
| --- | --- |
| `Ctrl-Shift-A` | `termscope.open` — file picker (URLs included after files) |
| `Ctrl-E` | `termscope.open-links` — URL picker |

File picker (Television):

| Key | Action |
| --- | --- |
| `Enter` | Open in a new Neovim split beside the source pane |
| `Ctrl-O` | Open with the default app |
| `Ctrl-Y` | Agent pane: send `/plannotator-annotate <file>`; shell pane: run `plannotator annotate <file>` |
| `Ctrl-S` | Cycle appearance order / alphabetical sort |

On a URL row, `Enter` / `Ctrl-O` open it with the default opener and `Ctrl-Y`
copies it (`pbcopy`; no-op if `pbcopy` is missing).

Link picker:

| Key | Action |
| --- | --- |
| `Enter` | Open URL with the default opener |
| `Ctrl-Y` | Copy URL (`pbcopy`; no-op if `pbcopy` is missing) |
| `Ctrl-S` | Cycle appearance order / alphabetical sort |

## tmux usage

After the [tmux install](#tmux) steps, set `@termscope` to the absolute path of
the `termscope` script in your clone (not the repo directory).

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
jumping back to the live bottom of the pane. Reload tmux config after editing
(`tmux source-file ~/.tmux.conf`, or your config path).

The script also accepts `--multiplexer tmux|herdr|auto` (default `auto`).

## Configuration

| Environment variable | Purpose |
| --- | --- |
| `TERMSCOPE_OPENER` | Override default opener, e.g. `open -a Zen` or `open -a Firefox` |
| `TERMSCOPE_SORT` | Default sort: `appearance` (default) or `alpha` |
| `TERMSCOPE_LOG` | JSON event log path. Default: `$XDG_CACHE_HOME/termscope/termscope.log` (`~/.cache/...` if unset) |
| `TERMSCOPE_DEBUG_DIR` | Directory for per-run debug dumps (unset = off) |

Examples:

```bash
export TERMSCOPE_OPENER='open -a Zen'
export TERMSCOPE_SORT=alpha
```

Put these in the environment of the Herdr server / tmux session that launches
the picker, not only an unrelated interactive shell.

## Dry run / debug

`scan` prints JSON of visible **file** candidates (no URLs, no Television). It
needs a real pane id:

```bash
# inside a Herdr pane
./termscope scan --pane-path "$PWD" --pane-id "$HERDR_PANE_ID" --multiplexer herdr

# tmux
./termscope scan --pane-path "$PWD" --pane-id "$(tmux display-message -p '#{pane_id}')" --multiplexer tmux
```

Enable debug dumps:

```bash
export TERMSCOPE_DEBUG_DIR=/tmp/termscope-debug
```

Each run writes the captured screen, indexed files, candidates, picker result,
and final selection decision.

## How it works

Herdr plugin actions run without a TTY, so `termscope.open` first opens an
`80% × 60%` session-modal popup. The popup inherits the source pane id/cwd,
captures visible text from every pane in the tab with
`herdr pane read --source visible`, scans the repo with `fd`, and runs
Television. Two bundled channels let `Ctrl-S` cycle between
appearance and alphabetical order. File previews use `bat` when available and a
built-in text preview otherwise.

When you choose a file, Termscope asks Herdr to split beside the source pane and
runs `nvim +line path`. For URLs, it uses the default opener unless
`TERMSCOPE_OPENER` is set.

## Project documentation

- [Publishing and releases](docs/publishing.md)
- [Changelog](CHANGELOG.md)

## Development

```bash
python3 -m py_compile termscope termscope_herdr.py
python3 -m unittest discover -s tests
herdr plugin link "$PWD"
herdr plugin action invoke termscope.open
```

There is no package manager. `herdr plugin install` clones the repo, reads
`herdr-plugin.toml`, and runs `scripts/install-dependencies.sh`. `plugin link`
does not run that script.

## License

[MIT](LICENSE) © iury souza
