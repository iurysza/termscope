# Dev Log: Visible-screen tmux file picker

## Goal setup

- Facts reviewed and accepted through Plannotator.
- Initial implementation plan was gated, then denied for deeper critique.
- Subagent critique saved to `subagent-critique.md`.
- Plan revised to phase annotation after visible-picker work.
- Second gate requested more instrumentation, a different ctrl key, and folder annotation blocking.
- Facts revised: annotate key is `Ctrl-y`; folder annotation is blocked; instrumentation/dev-log required.

## Phase 0 + 1: Visible-screen picker and open actions

**Date:** 2026-06-04
**Subagents:** 3 parallel workers (script, tests, docs/config)

### Changes made

- `termscope`:
  - Added `scan` subcommand (dry-run JSON output).
  - `capture_pane_text` now calls `tmux capture-pane -pJ` without `-S` or limit.
  - Removed `--limit` argument from `pick` subparser.
  - `cmd_pick` shows tmux message and exits when no visible candidates found (no fallback).
  - `_open_target` simplified: no fallback branch.
  - `run_fzf_visible` header updated to document `ctrl-y=annotate`.
  - `--expect` includes `ctrl-y`.
  - `parse_fzf_result` recognizes `ctrl-y`.

- `tests/test_termscope.py`:
  - Added `TestCapturePaneVisibleOnly` (asserts no `-S` flag).
  - Added `TestScanCommand` (JSON output shape).
  - Added `TestNoCandidates` (empty candidates → tmux message, no fzf).
  - Added `TestOpenTargetAnnotate` (file sends slash command, folder blocked).
  - Added `TestLineTargetPreservation` (nvim keeps line, annotate strips line).
  - Updated `TestFzfCommands` for `ctrl-y` in expect/header.
  - Added `TestExtractVisibleCandidates` cases for dirs and fuzzy-substring blocking.

- `.tmux.conf`:
  - Added `C-S-a` normal-mode binding (no prefix, no copy-mode enter).
  - Added `C-S-a` copy-mode-vi binding (preserves scrolled viewport, no cancel).
  - Updated `P` binding to remove `--limit`.
  - Updated `C-e` binding to remove `--limit` and mark as legacy.

- `README.md`:
  - Documented visible-screen-only behavior.
  - Documented `C-S-a`, `Ctrl-y` annotate, `scan` subcommand.
  - Removed fallback/repo-wide search references.

### Verification

- `python3 -m py_compile termscope` ✅
- `python3 -m unittest discover -s tests` — **50/50 pass** ✅
- `tmux source-file ~/.tmux.conf` — no errors ✅

### Manual smoke

- Pending: normal pane open, copy-mode scrolled viewport, empty-candidate message, annotate in Pi pane, folder block.

## Phase 2: Pi annotation action

**Date:** 2026-06-04
**Implemented alongside Phase 1 in same subagent batch.**

### Changes made

- Added `send_annotate_command(pane_id, file_path)`:
  - `tmux send-keys -t <pane> -l '/plannotator-annotate <path>'`
  - `tmux send-keys -t <pane> Enter`
- `_open_target` handles `mode="annotate"`:
  - Strips line numbers.
  - Blocks folders with tmux message.
  - Sends slash command for files.
- `cmd_pick` maps `ctrl-y` → `annotate`.

### Verification

- Unit tests: `TestOpenTargetAnnotate` passes (file sends command, folder blocked).
- Unit tests: `TestLineTargetPreservation` passes (annotate strips `:12`).
- Query-only no-open fix: `cmd_pick` no longer falls back to `fzf_result.query` when `selection` is empty.
- Line suffix preservation fix: `extract_visible_candidates` now detects `:digits` after matched paths and includes the line number in the display candidate.
- Added `TestQueryOnlyNoOpen` and `TestExtractVisibleCandidatesLineSuffix` tests (53 total, all pass).
- Copy-mode viewport capture initial formula was wrong in real tmux: it treated `#{scroll_position}` as viewport bottom and could capture only 1 line.
- Fixed formula: `-S -scroll`; `-E pane_height-scroll-1` for shallow scroll, else `-E -(scroll-pane_height+1)` for deep history.
- Added tests for deep and shallow copy-mode scroll (57 total, all pass).
- Full relative paths now resolve directly against pane cwd/search root even when `fd` does not index them (important for gitignored `scripts/`).
- Detached tmux repro verified: copy-mode `history-top` over visible `tests/test_termscope.py` captures 46 viewport lines and returns 1 candidate.
- Remaining manual smoke: normal pane open, empty-candidate message, annotate in Pi pane, folder block.
