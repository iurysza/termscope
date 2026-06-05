# Facts

- The picker captures and parses only the currently visible tmux pane content, not recent scrollback beyond the visible screen.
- When launched from tmux copy/visual mode, the picker parses the visible scrolled viewport, and any active selection does not narrow the candidate list.
- The live tmux config binds Ctrl-Shift-A to launch the picker in both normal mode and copy-mode.
- The picker never falls back to showing all repo files; every displayed candidate must be inferred from the visible screen.
- If no visible files or folders are found, tmux shows a short message and no fzf popup opens.
- Path detection stays conservative: full relative paths, absolute paths, tilde paths, quoted or backticked tokens, exact basenames, and README without .md can match real files or folders; generic fuzzy substring matches do not create candidates.
- The candidate list includes both real files and real folders when they are inferred from visible text.
- Inside fzf, Enter opens the selected path in a new nvim split, Ctrl-o opens it with the default app, and Ctrl-y triggers annotation for files.
- Ctrl-y annotation sends /plannotator-annotate <selected-file> followed by Enter into the source pane, so Plannotator feedback returns through the Pi agent session.
- If the selected path is a folder, the annotation action is blocked with a tmux message and does not send /plannotator-annotate.
- The annotation action does not run standalone plannotator annotate and does not provide a non-Pi fallback.
- When a visible candidate includes a line number such as path:12, the nvim action opens that line; default-app and annotate actions use the path itself.
- The implementation includes enough debug or dry-run instrumentation to verify capture, candidate extraction, fzf decisions, and selected actions during development without guessing.
- Development records phase success, failures, manual smoke results, and follow-up agent/reviewer findings in the goal package.
- README.md documents the new screen-only behavior, key bindings, fzf actions, strict no-fallback behavior, instrumentation, and Plannotator annotation path.
