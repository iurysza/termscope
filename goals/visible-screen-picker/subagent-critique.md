# Subagent critique: visible-screen picker

## 1. Guessed use case

You live in tmux with Pi/opencode/nvim. An agent, test run, grep output, or terminal scrollback shows file paths; you want one keystroke to turn the paths you can see into actions: open in nvim, open with macOS/default app, or annotate through Pi so Plannotator feedback returns to the active agent.

The key nuance is attention scope: "current visible screen" means "what I'm looking at now", not old scrollback noise. Copy-mode support matters because you often scroll up to an older agent/test output and want the same path actions there.

Evidence:
- Current script captures `-S -{limit}` scrollback and falls back to repo-wide fzf; facts explicitly reject both.
- Current tmux config already binds selected-text open (`o`/`O`) and picker (`C-e`, `P`) with a 3-page limit.
- Plan adds Pi `/plannotator-annotate` injection, so annotation feedback loop is the real new workflow, not just file opening.

## 2. Strongest critique

This is two features wearing one trench coat:

1. **Visible-screen file opener** — reasonable, already mostly exists.
2. **Agent-connected annotation launcher** — fragile, because it is command routing into a live terminal pane.

The opener part makes sense. The annotation part is the risky bit: `Ctrl-p` in fzf will send `/plannotator-annotate <path>` into whatever the source pane is doing. If the pane is not Pi, if Pi is busy, if focus/prompt state is weird, or if the selected path needs quoting, the tool types into the wrong context. That is not a file-picker bug; it is an agent integration problem.

Strict visible-only also has a cost. If conservative parsing misses a path, the planned behavior is "message, no popup". That is clean, but brittle. The current fallback is noisy, yes, but it gives recovery. Removing all fallback makes the tool feel magic when it works and dead when it misses.

Also: existing tmux copy-mode selection already covers the deterministic case. If you can select the exact path, `o`/`O` already open it. The new picker mainly helps when multiple paths are visible or selection is annoying.

## 3. Viable simpler alternatives

### A. Selection-first annotate binding

Add one copy-mode binding for selected text → `/plannotator-annotate <selection>`.

- Much simpler than parsing the whole screen.
- Deterministic: user selects the exact path.
- Keeps feedback in Pi if sent to the Pi pane.
- Downside: slower when many paths are visible; still needs command injection.

### B. Minimal visible-only opener, defer annotate

Implement only:
- default tmux visible capture (`capture-pane -pJ`)
- no repo-wide fallback in `pick`
- `C-S-a` launcher
- Enter/Ctrl-o actions

Then add annotation only after a manual smoke test proves command injection is sane.

This covers most open-file pain with less risk.

### C. Pi-native annotation command/picker

Best architecture for annotation: make Pi/Plannotator own it. Example workflow: `/plannotator-annotate` plus a Pi-side picker over paths in the last assistant message or visible transcript context.

- Feedback routing is first-class.
- No tmux send-keys hack.
- Better fit for "annotate this for the agent".
- Downside: likely more work in the Pi extension, not this script.

### D. Editor-native fallback

For editing files, nvim already has `gf`, `:find`, Telescope, and fzf-style file search. This is better once you are inside nvim. It does not solve terminal-output-to-agent annotation, so it is not a full replacement.

## 4. Recommended path

Keep the feature, but narrow the implementation mindset:

- Treat **visible-screen picker** as the core feature.
- Treat **Pi annotation** as a sharp, explicit action, not a general opener.
- Do not overbuild detection or fuzzy matching. Conservative is right.
- Keep the existing selected-text `o`/`O` bindings; they are still the precise workflow.
- Strongly consider shipping open actions first, then annotation after manual tmux/Pi smoke.

If you want the fastest useful version: implement the current plan, but do not pretend the annotation route is robust. It is a deliberate hack. Useful hack, but still a hack.

## 5. Plan changes I recommend

1. **Split annotate into a separate step/gate.**
   - Phase 1: visible-only picker + nvim/default actions.
   - Phase 2: `Ctrl-p` Pi annotation after manual verification.

2. **Specify literal tmux send-keys.**
   - Use `tmux send-keys -t <pane> -l '/plannotator-annotate "path with spaces"'` then `tmux send-keys -t <pane> Enter`.
   - Do not rely on tmux parsing a shell-quoted command string.

3. **Add a test/plan note for wrong-pane behavior.**
   - Current fact says always auto-send. Fine, but document it as intentional sharp edge.

4. **Clarify folder annotation expectations.**
   - `/plannotator-annotate <folder>` may only be useful for markdown/HTML folder review, not arbitrary code folder browsing. If selected candidate is a code directory, annotation may fail.

5. **Reconsider `Ctrl-p` if fzf navigation matters.**
   - `Ctrl-p` is normally previous-item muscle memory. It works as an action key, but steals navigation. `Alt-o`/`Alt-a` would be less annoying.

6. **Keep no-fallback, but improve failure message.**
   - Message should say exactly what happened: `No visible files/folders found`.
   - Debug mode already helps; keep it.

Bottom line: the visible picker is worth doing. The annotation action is useful only because it routes back into Pi, but that is the most fragile part. Build it small, test it manually, and do not let it turn into a general agent-control framework.
