# Termscope

Herdr plugin that opens files and links already visible in the terminal viewport. The same `termscope` script also runs under tmux.

## Map

- Product, install, usage: `README.md`
- Publishing and version alignment: `docs/publishing.md`
- How the project works (agents): `ai-artifacts/_index.md`
- Picker (no `.py` suffix; shebang `python3`): `termscope`
- Herdr action and popup wrapper: `termscope_herdr.py`
- Plugin manifest (`id = "termscope"`): `herdr-plugin.toml`
- Version source of truth: `version.txt`
- Release Please version: `.release-please-manifest.json`
- Install-time Television bootstrap: `scripts/install-dependencies.sh`
- Television channels: `cable/termscope-appearance.toml`, `cable/termscope-alpha.toml`
- Tests: `tests/`
- CI: `.github/workflows/ci.yml`

Keep `version.txt`, `herdr-plugin.toml`, and `.release-please-manifest.json` on the same version.

## Commands

There is no package manager, linter, or formatter job. CI uses `python` after setup-python. Locally and in shebangs, use `python3`.

Compile and test (README and `.github/workflows/ci.yml`):

```bash
python3 -m py_compile termscope termscope_herdr.py
python3 -m unittest discover -s tests
```

Then run the `Validate Herdr manifest` Python in `.github/workflows/ci.yml`. That step checks:

- `herdr-plugin.toml` id `termscope`
- version lockstep with `version.txt` and `.release-please-manifest.json`
- `min_herdr_version` at least `0.7.4`
- platforms `linux` and `macos`
- build command `sh scripts/install-dependencies.sh`
- actions `open` and `open-links`
- popup panes `picker` and `link-picker` at 80% by 60%
- `cable/termscope-*.toml` source command length 2, `no_sort` true, frecency false

Manifest checks use stdlib `tomllib` (Python 3.11+).

CI matrix: Python 3.11 and 3.12 on Ubuntu; Python 3.12 on macOS.

Optional Herdr smoke (not in CI; needs Herdr on `PATH`):

```bash
herdr plugin link "$PWD"
herdr plugin action list --plugin termscope
```

## Loop

1. Read the files you will change. Follow the map. Do not invent architecture notes.
2. Make the change.
3. If behavior or architecture changed, update `ai-artifacts/`.
4. Compile, run the tests, then run the CI Herdr manifest check.
5. Stop when those three CI steps pass.

## Git identity

Never include Cursor (or any Cursor agent/bot) as git author, committer, or Co-authored-by / similar trailer.
