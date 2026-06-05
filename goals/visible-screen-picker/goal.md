# Visible-screen tmux file picker

Build a strict visible-screen tmux file/folder picker for paths shown in the current pane or copy-mode viewport. The picker launches with `C-S-a`, opens visible candidates via nvim/default app, and annotates selected files through Pi with `Ctrl-y` by sending `/plannotator-annotate <file>` to the source pane.

Shared understanding: `facts.md`.

Execution plan: `plan.md`.

Done when every accepted fact in `facts.md` is implemented, the verification in `plan.md` passes, phase results are recorded in `dev-log.md`, and final reviewer/subagent blockers are resolved or explicitly deferred.
