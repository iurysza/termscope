# ai-artifacts

How-the-project-works docs for agents live here. Update them when behavior or architecture changes.

Human-facing sources already in the tree:

- `README.md`
- `docs/` (`docs/publishing.md`)
- `scripts/` (`scripts/install-dependencies.sh`)

Deeper agent docs (context glossaries, ADRs, architecture notes) should grow in this folder when there is a real decision or term to record.

## Clipboard

`copy_to_clipboard` tries `pbcopy` on macOS, `wl-copy` when `WAYLAND_DISPLAY` is set, then `xclip -selection clipboard` and `xsel --clipboard --input` when `DISPLAY` is set. If none succeed it raises `ClipboardError`. Ctrl-Y in the file and link pickers shows "Could not copy link to clipboard" instead of "Link copied to clipboard". Opening a file still proceeds when the path copy fails.
