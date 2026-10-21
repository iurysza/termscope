# ai-artifacts

How-the-project-works docs for agents live here. Update them when behavior or architecture changes.

Human-facing sources already in the tree:

- `README.md`
- `docs/` (`docs/publishing.md`)
- `scripts/` (`scripts/install-dependencies.sh`)

Deeper agent docs (context glossaries, ADRs, architecture notes) should grow in this folder when there is a real decision or term to record.

## Clipboard

`copy_to_clipboard` tries `pbcopy` on macOS, `wl-copy` when `WAYLAND_DISPLAY` is set, then `xclip -selection clipboard` and `xsel --clipboard --input` when `DISPLAY` is set. If those fail, or when there is no display, it writes OSC 52 (`ESC ] 52 ; c ; <base64> BEL`) to `/dev/tty`. A set `TMUX` variable wraps that write in a tmux DCS passthrough. Base64 longer than 100 KB is refused. The function returns `"copied"` when a native tool exits 0 and `"sent"` after an OSC 52 write, which the terminal cannot confirm. Ctrl-Y shows "Link copied to clipboard", "Link sent to terminal clipboard", or "Could not copy link to clipboard". Opening a file still proceeds when the path copy fails.
