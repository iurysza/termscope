# Plan: Visible-screen tmux file picker

## Solution approach

Refactor the existing single Python script in phases, with instrumentation first. Phase 1 makes the picker reliable as a strict visible-screen opener. Phase 2 adds the sharper Pi annotation action with `Ctrl-y`, only for files. Each phase records commands, failures, manual smoke results, and subagent/reviewer feedback in `dev-log.md` so the implementation loop can be driven without guessing.

Subagent critique captured in `subagent-critique.md`: visible picker makes sense; annotation is useful but fragile because it sends text into a live pane.

## Phase 0: Instrument the development loop

1. **Add a non-interactive scan/debug path**
   - Touch: `termscope`, tests, README.
   - Add a `scan` subcommand, or equivalent dry-run mode, that captures the source pane, extracts candidates, and prints JSON without opening fzf or launching actions.
   - JSON should include at least: `pane_id`, `source_pane_path`, `search_root`, `screen_line_count`, `indexed_count`, `candidate_count`, `candidates`, and whether capture was visible-only.
   - Extend existing `TERMSCOPE_DEBUG_DIR` output to include enough state to diagnose capture, candidate extraction, fzf decisions, no-candidate exits, and action dispatch.
   - Verification:
     - Unit tests cover the JSON shape and no-action behavior.
     - Manual command can run against the current pane and append result notes to `goals/visible-screen-picker/dev-log.md`.

2. **Use phase logs and subagent review checkpoints**
   - Touch: `goals/visible-screen-picker/dev-log.md` during implementation.
   - After each implementation phase, record:
     - changed files
     - commands run
     - pass/fail output summary
     - manual smoke result
     - known failures or blockers
     - subagent/reviewer output path if one was launched
   - Launch read-only reviewer/oracle subagents after major phases when behavior is not obvious from tests, especially copy-mode capture and Pi annotation.
   - Verification:
     - `dev-log.md` exists and is updated before final handoff.

## Phase 1: Visible-screen picker and open actions

3. **Make pane capture truly visible-only**
   - Touch: `termscope`, tests in `tests/test_termscope.py`.
   - Change `capture_pane_text` to call `tmux capture-pane -pJ` without `-S -<limit>`.
   - Remove or stop using the `--limit` picker argument.
   - Keep stripping ANSI after capture.
   - Verification:
     - Unit test mocks `subprocess.run` and asserts no `-S`/limit argument is passed.
     - `python3 -m unittest discover -s tests`.
     - Record command results in `dev-log.md`.

4. **Wire `C-S-a` without losing copy-mode viewport**
   - Touch: `/path/to/user/.tmux.conf`, README tmux snippet.
   - Bind `C-S-a` in normal mode and `copy-mode-vi`.
   - In copy-mode, do not cancel copy mode before launching the picker; cancellation before capture would lose the scrolled viewport.
   - Keep old picker aliases only if they call the same visible-only picker path.
   - Verification:
     - Config/text checks assert both `C-S-a` bindings exist.
     - Manual tmux check: enter copy-mode, scroll up, press `C-S-a`, confirm candidates come from the scrolled viewport.
     - Record success/failure in `dev-log.md`.

5. **Keep candidate extraction conservative, but include files, folders, and line targets**
   - Touch: `extract_visible_candidates`, `parse_selected_target`, tests.
   - Continue indexing files and dirs from the source pane git root with `fd`.
   - Match only real paths/folders inferred from visible text: full relative paths, absolute paths, tilde paths, quoted/backticked tokens, exact basenames, and README without `.md`.
   - Do not introduce fuzzy substring matching.
   - Preserve line suffixes when visible text contains `path:12` so nvim can jump to the line.
   - Verification:
     - Add/adjust unit tests for dirs, backticks, basename exact matches, README omission, no fuzzy substring match, and `path:12` preservation.
     - Use `scan` JSON to inspect real candidates from current pane.

6. **Remove repo-wide fallback from the picker flow**
   - Touch: `cmd_pick`, `_open_target`, fallback-related tests.
   - If candidate extraction returns empty, show `No visible files/folders found` via tmux and return without opening fzf.
   - Do not replace empty candidates with `repo_paths`.
   - Do not treat an fzf query with no selected candidate as a repo-wide search.
   - Remove or isolate fallback code so `pick` cannot show all repo files.
   - Verification:
     - Unit tests assert no candidates means no fzf call and a tmux message call.
     - Unit tests assert typed query alone does not open or fallback.
     - `scan` confirms empty-candidate behavior before opening fzf.

7. **Keep existing open actions working**
   - Touch: `_open_target`, `open_in_nvim_split`, `open_with_default_app`, tests.
   - Enter opens a new nvim split from the source pane.
   - Ctrl-o opens with the configured/default app.
   - If a selected candidate includes `:line`, nvim uses it; default app ignores it.
   - Verification:
     - Existing path resolution/open tests still pass.
     - Add explicit test for `src/main.py:12` through picker selection.

8. **Phase 1 review checkpoint**
   - Launch a read-only reviewer/oracle subagent to inspect the visible-only/open-action diff.
   - Ask it specifically to look for fallback regressions, capture mistakes, and test blind spots.
   - Save output under `goals/visible-screen-picker/reviews/phase-1.md` or summarize it in `dev-log.md`.

## Phase 2: Pi annotation action

9. **Add fzf `ctrl-y` action after Phase 1 works**
   - Touch: `parse_fzf_result`, `run_fzf_visible`, `cmd_pick`, tests.
   - Add `ctrl-y` to `--expect`.
   - Header documents `enter=nvim`, `ctrl-o=default app`, `ctrl-y=annotate`.
   - Map fzf keys:
     - `enter` / blank key → nvim
     - `ctrl-o` → default app
     - `ctrl-y` → annotate
   - Verification:
     - Unit tests for parsing `ctrl-y`.
     - Unit tests for fzf command args/header.

10. **Implement Pi-agent annotation by sending the slash command literally**
    - Touch: `termscope`, tests.
    - Add an annotate mode that resolves the selected path and strips any line number.
    - If the resolved path is a folder, show a tmux message and do not send `/plannotator-annotate`.
    - If the resolved path is a file, send `/plannotator-annotate <file>` plus Enter to the source pane.
    - Use literal tmux sends: `tmux send-keys -t <pane> -l '<command text>'`, then `tmux send-keys -t <pane> Enter`.
    - Quote/wrap paths with spaces so Pi's `/plannotator-annotate` parser receives the correct path.
    - Always auto-send; do not detect whether the source pane is Pi.
    - Do not run standalone `plannotator annotate` and do not add a non-Pi fallback.
    - Verification:
      - Unit test mocks subprocess and asserts file annotate uses literal `tmux send-keys` with `/plannotator-annotate`.
      - Unit test asserts folder annotate displays a message and sends no slash command.
      - Unit test asserts no `plannotator annotate` subprocess is used.
      - Manual smoke in a Pi pane confirms feedback returns to the agent.
      - Record failures and exact command behavior in `dev-log.md`.

11. **Phase 2 review checkpoint**
    - Launch a read-only reviewer/oracle subagent after annotation is implemented.
    - Ask it to inspect wrong-pane behavior, quoting, folder blocking, and no-standalone fallback.
    - Save output under `goals/visible-screen-picker/reviews/phase-2.md` or summarize it in `dev-log.md`.

## Phase 3: Docs and final checks

12. **Update live tmux config and docs**
    - Touch: `/path/to/user/.tmux.conf`, `README.md`.
    - Document `C-S-a` as the primary picker binding.
    - Update/replace old picker snippets that pass `--limit`.
    - Document strict visible-only behavior, no repo-wide fallback, no-candidate message, instrumentation, `scan`/dry-run usage, and fzf actions.
    - Document that annotation is file-only and sends `/plannotator-annotate` to the source pane with `Ctrl-y`.
    - Verification:
      - `rg -n "C-S-a|ctrl-y|--limit|plannotator-annotate|scan|TERMSCOPE_DEBUG_DIR" README.md /path/to/user/.tmux.conf`.
      - `tmux source-file ~/.tmux.conf`.

13. **Final verification**
    - Run:
      - `python3 -m unittest discover -s tests`
      - `python3 -m py_compile termscope`
    - Manual smoke:
      - Normal pane: visible file path → `C-S-a` → Enter opens nvim.
      - Normal pane: visible file path → `C-S-a` → Ctrl-o opens default app.
      - Pi pane: visible file path → `C-S-a` → Ctrl-y sends `/plannotator-annotate <file>` to the agent.
      - Folder candidate: `C-S-a` → Ctrl-y shows folder-blocked message and sends nothing.
      - Copy-mode scrolled viewport: `C-S-a` only shows paths currently visible there.
      - No visible paths: tmux message, no popup.
    - Record final pass/fail matrix in `dev-log.md`.

14. **Final review checkpoint**
    - Launch a final read-only reviewer subagent over the implementation diff and `dev-log.md`.
    - Address blockers only; record optional suggestions as deferred.

## Risks

- `C-S-a` depends on terminal/tmux extended key behavior. This machine already uses `C-S-e`, so odds are good.
- Copy-mode viewport capture must be manually verified; tmux docs say default `capture-pane` captures visible contents, but copy-mode scrolled viewport behavior is the key smoke test.
- Always auto-sending `/plannotator-annotate` can type into a non-Pi pane if used there. This is intentional per decision, but sharp.
- `/path/to/user/.tmux.conf` has unrelated existing changes. Implementation should touch only the picker binding block and keybinding reference lines.

## Open questions

- None blocking.
