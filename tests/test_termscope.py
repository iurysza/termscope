#!/usr/bin/env python3
"""Unit tests for termscope pure functions."""

import importlib.util
import json
import os
import sys
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

# Load the script as a module since it has no .py extension.
script_path = Path(__file__).parent.parent / "termscope"
loader = SourceFileLoader("termscope", str(script_path.resolve()))
spec = importlib.util.spec_from_loader("termscope", loader)
tfp = importlib.util.module_from_spec(spec)
sys.modules["termscope"] = tfp
spec.loader.exec_module(tfp)


class TestStripAnsi(unittest.TestCase):
    def test_csi_codes(self):
        self.assertEqual(tfp.strip_ansi("\x1b[31mhello\x1b[0m"), "hello")

    def test_osc_sequences(self):
        self.assertEqual(tfp.strip_ansi("\x1b]0;title\x07hello"), "hello")
        self.assertEqual(tfp.strip_ansi("\x1b]0;title\x1b\\hello"), "hello")

    def test_mixed(self):
        self.assertEqual(
            tfp.strip_ansi("\x1b[1m\x1b]0;t\x07hello\x1b[0m"), "hello"
        )


class TestCleanVisibleLine(unittest.TestCase):
    def test_markdown_list(self):
        self.assertEqual(tfp.clean_visible_line("- src/main.py"), "src/main.py")
        self.assertEqual(tfp.clean_visible_line("* src/main.py"), "src/main.py")
        self.assertEqual(tfp.clean_visible_line("> src/main.py"), "src/main.py")

    def test_numbered_list(self):
        self.assertEqual(tfp.clean_visible_line("1. src/main.py"), "src/main.py")
        self.assertEqual(tfp.clean_visible_line("2) src/main.py"), "src/main.py")

    def test_quotes(self):
        self.assertEqual(tfp.clean_visible_line("`src/main.py`"), "src/main.py")
        self.assertEqual(tfp.clean_visible_line("'src/main.py'"), "src/main.py")
        self.assertEqual(tfp.clean_visible_line('"src/main.py"'), "src/main.py")

    def test_trailing_punctuation(self):
        self.assertEqual(tfp.clean_visible_line("src/main.py,"), "src/main.py")
        self.assertEqual(tfp.clean_visible_line("src/main.py."), "src/main.py")
        self.assertEqual(tfp.clean_visible_line("src/main.py;"), "src/main.py")


class TestExtractVisibleLinks(unittest.TestCase):
    def test_raw_url(self):
        text = "check https://example.com/foo for details"
        self.assertEqual(tfp.extract_visible_links(text), ["https://example.com/foo"])

    def test_markdown_link(self):
        text = "[example](https://example.com) and [other](https://other.com/path)"
        self.assertEqual(
            tfp.extract_visible_links(text),
            ["https://example.com", "https://other.com/path"],
        )

    def test_angle_brackets(self):
        text = "see <https://example.com> here"
        self.assertEqual(tfp.extract_visible_links(text), ["https://example.com"])

    def test_multiple_schemes(self):
        text = "http://old.test https://new.test/path?q=1"
        self.assertEqual(
            tfp.extract_visible_links(text),
            ["http://old.test", "https://new.test/path?q=1"],
        )

    def test_deduplicates_preserves_order(self):
        text = "https://a.com\nhttps://b.com\nhttps://a.com"
        self.assertEqual(
            tfp.extract_visible_links(text),
            ["https://a.com", "https://b.com"],
        )

    def test_strips_trailing_punctuation(self):
        text = "visit https://example.com."
        self.assertEqual(tfp.extract_visible_links(text), ["https://example.com"])

    def test_strips_markdown_trailing_paren(self):
        text = "[link](https://example.com))"
        self.assertEqual(tfp.extract_visible_links(text), ["https://example.com"])

    def test_no_false_positives(self):
        text = "path/to/file.txt and ~/other"
        self.assertEqual(tfp.extract_visible_links(text), [])


class TestParseSelectedTarget(unittest.TestCase):
    def test_plain_path(self):
        p = tfp.parse_selected_target("src/main.py")
        self.assertEqual(p.path, "src/main.py")
        self.assertEqual(p.line, "")

    def test_colon_line(self):
        p = tfp.parse_selected_target("src/main.py:12")
        self.assertEqual(p.path, "src/main.py")
        self.assertEqual(p.line, "12")

    def test_colon_line_col(self):
        p = tfp.parse_selected_target("src/main.py:12:3")
        self.assertEqual(p.path, "src/main.py")
        self.assertEqual(p.line, "12")

    def test_colon_line_trailing(self):
        p = tfp.parse_selected_target("src/main.py:12:")
        self.assertEqual(p.path, "src/main.py")
        self.assertEqual(p.line, "12")

    def test_dash_line_dash(self):
        p = tfp.parse_selected_target("src/main.py-12-")
        self.assertEqual(p.path, "src/main.py")
        self.assertEqual(p.line, "12")

    def test_quoted(self):
        p = tfp.parse_selected_target("`src/main.py:12`")
        self.assertEqual(p.path, "src/main.py")
        self.assertEqual(p.line, "12")

    def test_empty(self):
        p = tfp.parse_selected_target("")
        self.assertEqual(p.path, "")

    def test_multiline_uses_first_line_only(self):
        p = tfp.parse_selected_target("src/main.py:12\nnoise")
        self.assertEqual(p.path, "src/main.py")
        self.assertEqual(p.line, "12")


class TestResolveExistingPath(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(__file__).parent / "_test_tmp"
        self.tmp.mkdir(exist_ok=True)
        (self.tmp / "file.txt").write_text("hello")
        self.nested = self.tmp / "sub"
        self.nested.mkdir(exist_ok=True)
        (self.nested / "deep.txt").write_text("deep")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_absolute(self):
        p = tfp.resolve_existing_path(str(self.tmp / "file.txt"), self.tmp, self.tmp)
        self.assertEqual(p, self.tmp / "file.txt")

    def test_tilde(self):
        home = str(Path.home())
        p = tfp.resolve_existing_path("~", self.tmp, self.tmp)
        self.assertEqual(p, Path.home())
        p = tfp.resolve_existing_path("~/", self.tmp, self.tmp)
        self.assertEqual(p, Path.home())

    def test_pane_relative(self):
        p = tfp.resolve_existing_path("file.txt", self.tmp, self.tmp)
        self.assertEqual(p, self.tmp / "file.txt")

    def test_search_root_relative(self):
        # pane_path is a subdir, search_root is parent
        p = tfp.resolve_existing_path("file.txt", self.nested, self.tmp)
        self.assertEqual(p, self.tmp / "file.txt")

    def test_missing(self):
        p = tfp.resolve_existing_path("nope.txt", self.tmp, self.tmp)
        self.assertIsNone(p)


class TestExtractVisibleCandidates(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(__file__).parent / "_test_repo"
        self.tmp.mkdir(exist_ok=True)
        (self.tmp / "README.md").write_text("# readme")
        nested = self.tmp / "src"
        nested.mkdir(exist_ok=True)
        (nested / "main.py").write_text("print(1)")
        (nested / "utils.py").write_text("")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_relative_path_inline(self):
        text = "see src/main.py for details"
        repo = ["README.md", "src", "src/main.py", "src/utils.py"]
        cands = tfp.extract_visible_candidates(text, repo, self.tmp, self.tmp)
        self.assertIn("src/main.py", cands)

    def test_relative_path_inline_without_repo_index(self):
        text = "see src/main.py for details"
        cands = tfp.extract_visible_candidates(text, [], self.tmp, self.tmp)
        self.assertIn("src/main.py", cands)

    def test_relative_path_inline_without_repo_index_preserves_line(self):
        text = "see src/main.py:12 for details"
        cands = tfp.extract_visible_candidates(text, [], self.tmp, self.tmp)
        self.assertIn("src/main.py:12", cands)

    def test_absolute_path_inline(self):
        text = f"edit {self.tmp}/src/main.py now"
        repo = ["README.md", "src", "src/main.py"]
        cands = tfp.extract_visible_candidates(text, repo, self.tmp, self.tmp)
        self.assertIn("src/main.py", cands)

    def test_tilde_path(self):
        home = Path.home()
        rel = self.tmp.relative_to(home) if self.tmp.is_relative_to(home) else None
        if rel:
            text = f"edit ~/{rel}/src/main.py"
            repo = ["src/main.py"]
            cands = tfp.extract_visible_candidates(text, repo, self.tmp, self.tmp)
            self.assertIn("src/main.py", cands)

    def test_markdown_backticks(self):
        text = "check `src/main.py` for logic"
        repo = ["src/main.py", "src/utils.py"]
        cands = tfp.extract_visible_candidates(text, repo, self.tmp, self.tmp)
        self.assertIn("src/main.py", cands)

    def test_md_extension_omission(self):
        text = "see README for details"
        repo = ["README.md", "src/main.py"]
        cands = tfp.extract_visible_candidates(text, repo, self.tmp, self.tmp)
        self.assertIn("README.md", cands)

    def test_basename_exact_line_match(self):
        text = "README.md\nsrc/main.py"
        repo = ["README.md", "src/main.py"]
        cands = tfp.extract_visible_candidates(text, repo, self.tmp, self.tmp)
        self.assertIn("README.md", cands)
        self.assertIn("src/main.py", cands)

    def test_generic_basename_no_explosion(self):
        # "main" appears inside "src/main.py" as a substring but not as exact line
        text = "src/main.py is the main entrypoint"
        repo = ["src/main.py", "src/utils.py"]
        cands = tfp.extract_visible_candidates(text, repo, self.tmp, self.tmp)
        # "main" alone should NOT create a candidate for src/main.py
        # but src/main.py should appear because the full path is inline
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0], "src/main.py")

    def test_directory_candidate(self):
        # If fd returns a directory and the dir name appears on a line by itself
        text = "src\nREADME.md"
        repo = ["README.md", "src", "src/main.py", "src/utils.py"]
        cands = tfp.extract_visible_candidates(text, repo, self.tmp, self.tmp)
        self.assertIn("src", cands)
        self.assertIn("README.md", cands)

    def test_fuzzy_substring_no_match(self):
        # "utils" appears inside text but not as exact token matching src/utils.py
        text = "useful utils for the project"
        repo = ["src/main.py", "src/utils.py"]
        cands = tfp.extract_visible_candidates(text, repo, self.tmp, self.tmp)
        # Neither path should match because no exact path/basename is visible
        self.assertEqual(len(cands), 0)


class TestParseFzfResult(unittest.TestCase):
    def test_query_key_selection(self):
        r = tfp.parse_fzf_result("query\nenter\nselection")
        self.assertEqual(r.query, "query")
        self.assertEqual(r.key, "enter")
        self.assertEqual(r.selection, "selection")

    def test_query_blank_key_selection(self):
        r = tfp.parse_fzf_result("query\n\nselection")
        self.assertEqual(r.query, "query")
        self.assertEqual(r.key, "")
        self.assertEqual(r.selection, "selection")

    def test_query_only(self):
        r = tfp.parse_fzf_result("query")
        self.assertEqual(r.query, "query")
        self.assertEqual(r.key, "")
        self.assertEqual(r.selection, "")

    def test_ctrl_o(self):
        r = tfp.parse_fzf_result("query\nctrl-o\nselection")
        self.assertEqual(r.key, "ctrl-o")

    def test_ctrl_y(self):
        r = tfp.parse_fzf_result("query\nctrl-y\nselection")
        self.assertEqual(r.query, "query")
        self.assertEqual(r.key, "ctrl-y")
        self.assertEqual(r.selection, "selection")

    def test_query_selection_no_expect(self):
        # First rest is not a known key, treat as selection
        r = tfp.parse_fzf_result("query\nselection")
        self.assertEqual(r.query, "query")
        self.assertEqual(r.key, "")
        self.assertEqual(r.selection, "selection")


class TestCapturePaneVisibleOnly(unittest.TestCase):
    def test_no_limit_flag(self):
        completed = SimpleNamespace(returncode=0, stdout="line1\nline2\n")
        with patch.object(tfp.subprocess, "run", return_value=completed) as run:
            result = tfp.capture_pane_text("%42")

        self.assertEqual(result, "line1\nline2\n")
        cmd = run.call_args.args[0]
        self.assertNotIn("-S", cmd)
        # No numeric limit should be present
        for arg in cmd:
            self.assertFalse(arg.startswith("-") and arg[1:].isdigit(),
                             f"unexpected limit arg: {arg}")

    def test_pane_id_passed(self):
        completed = SimpleNamespace(returncode=0, stdout="pane text")
        with patch.object(tfp.subprocess, "run", return_value=completed) as run:
            tfp.capture_pane_text("%99")

        cmd = run.call_args.args[0]
        self.assertIn("-t", cmd)
        self.assertIn("%99", cmd)

    def test_copy_mode_viewport_capture(self):
        """When pane is in copy mode, capture the scrolled viewport."""
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            if cmd[0] == "tmux" and cmd[1] == "display-message":
                fmt = cmd[-1]
                if "pane_in_mode" in fmt:
                    return SimpleNamespace(returncode=0, stdout="1")
                if "scroll_position" in fmt:
                    return SimpleNamespace(returncode=0, stdout="102")
                if "pane_height" in fmt:
                    return SimpleNamespace(returncode=0, stdout="69")
            if cmd[0] == "tmux" and cmd[1] == "capture-pane":
                return SimpleNamespace(returncode=0, stdout="scrolled viewport text")
            return SimpleNamespace(returncode=0, stdout="")

        with patch.object(tfp.subprocess, "run", side_effect=fake_run):
            result = tfp.capture_pane_text("%42")

        self.assertEqual(result, "scrolled viewport text")
        # Find the capture-pane command
        capture_cmd = None
        for c in calls:
            if len(c) >= 2 and c[0] == "tmux" and c[1] == "capture-pane":
                capture_cmd = c
                break
        self.assertIsNotNone(capture_cmd)
        # Should include -S and -E for copy-mode viewport
        self.assertIn("-S", capture_cmd)
        self.assertIn("-E", capture_cmd)
        # Deep scroll: top is -scroll, bottom is -(scroll-height+1)
        s_idx = capture_cmd.index("-S")
        e_idx = capture_cmd.index("-E")
        self.assertEqual(capture_cmd[s_idx + 1], "-102")
        self.assertEqual(capture_cmd[e_idx + 1], "-34")

    def test_copy_mode_shallow_scroll_capture(self):
        """When scroll is inside the live viewport, -E is an absolute row."""
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            if cmd[0] == "tmux" and cmd[1] == "display-message":
                fmt = cmd[-1]
                if "pane_in_mode" in fmt:
                    return SimpleNamespace(returncode=0, stdout="1")
                if "scroll_position" in fmt:
                    return SimpleNamespace(returncode=0, stdout="5")
                if "pane_height" in fmt:
                    return SimpleNamespace(returncode=0, stdout="46")
            if cmd[0] == "tmux" and cmd[1] == "capture-pane":
                return SimpleNamespace(returncode=0, stdout="shallow viewport text")
            return SimpleNamespace(returncode=0, stdout="")

        with patch.object(tfp.subprocess, "run", side_effect=fake_run):
            result = tfp.capture_pane_text("%42")

        self.assertEqual(result, "shallow viewport text")
        capture_cmd = next(c for c in calls if len(c) >= 2 and c[0] == "tmux" and c[1] == "capture-pane")
        s_idx = capture_cmd.index("-S")
        e_idx = capture_cmd.index("-E")
        self.assertEqual(capture_cmd[s_idx + 1], "-5")
        self.assertEqual(capture_cmd[e_idx + 1], "40")


class TestScanCommand(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(__file__).parent / "_test_scan"
        self.tmp.mkdir(exist_ok=True)
        (self.tmp / "app.py").write_text("app")
        sub = self.tmp / "lib"
        sub.mkdir(exist_ok=True)
        (sub / "helper.py").write_text("helper")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    @unittest.skipUnless(hasattr(tfp, "cmd_scan"), "cmd_scan not yet implemented")
    def test_scan_outputs_valid_json(self):
        screen = "app.py\nlib/helper.py\n"
        fd_out = "app.py\nlib\nlib/helper.py\n"

        def fake_run(cmd, **kwargs):
            if cmd[0] == "tmux":
                if cmd[1] == "capture-pane":
                    return SimpleNamespace(returncode=0, stdout=screen)
                if cmd[1] == "display-message":
                    return SimpleNamespace(returncode=0, stdout=str(self.tmp))
            if cmd[0] == "fd":
                return SimpleNamespace(returncode=0, stdout=fd_out)
            if cmd[0] == "git":
                return SimpleNamespace(returncode=128, stdout="")
            return SimpleNamespace(returncode=0, stdout="")

        args = SimpleNamespace(
            pane_path=str(self.tmp),
            pane_id="%1",
        )

        with patch.object(tfp.subprocess, "run", side_effect=fake_run):
            with patch("sys.stdout", new_callable=lambda: sys.stdout):
                # cmd_scan should print JSON to stdout
                import io
                buf = io.StringIO()
                with patch("sys.stdout", buf):
                    tfp.cmd_scan(args)
                output = buf.getvalue()

        data = json.loads(output)
        required_keys = {
            "pane_id", "source_pane_path", "search_root",
            "screen_line_count", "indexed_count", "candidate_count",
            "candidates", "visible_only",
        }
        self.assertTrue(required_keys.issubset(data.keys()),
                        f"missing keys: {required_keys - set(data.keys())}")
        self.assertEqual(data["visible_only"], True)
        self.assertIsInstance(data["candidates"], list)
        self.assertEqual(data["pane_id"], "%1")


class TestNoCandidates(unittest.TestCase):
    def test_empty_candidates_falls_back_to_full_repo(self):
        args = SimpleNamespace(
            pane_path="/tmp/repo",
            pane_id="%1",
        )

        with patch.object(tfp, "capture_pane_text", return_value="no paths here\n"), \
             patch.object(tfp, "strip_ansi", side_effect=lambda x: x), \
             patch.object(tfp, "list_repo_files", return_value=[]), \
             patch.object(tfp, "extract_visible_candidates", return_value=[]), \
             patch.object(tfp, "run_fzf_visible") as mock_fzf, \
             patch.object(tfp, "run_fzf_full_repo", return_value=None) as mock_full, \
             patch.object(tfp.subprocess, "run") as mock_run, \
             patch("os.execvp"):

            # tmux display-message mock
            mock_run.return_value = SimpleNamespace(returncode=0, stdout="")

            tfp.cmd_pick(args)

        # run_fzf_visible should NOT be called when candidates are empty
        mock_fzf.assert_not_called()
        # Should fall back to full-repo listing
        mock_full.assert_called_once()

        # tmux display-message should be called with the empty-repo message
        display_calls = [
            call for call in mock_run.call_args_list
            if len(call.args[0]) >= 2
            and call.args[0][0] == "tmux"
            and call.args[0][1] == "display-message"
        ]
        self.assertTrue(
            any("No files found in repo" in str(call) for call in display_calls),
            f"expected 'No files found in repo' in display-message calls, got: {display_calls}"
        )


class TestQueryOnlyNoOpen(unittest.TestCase):
    def test_typed_query_without_selection_does_not_open(self):
        args = SimpleNamespace(
            pane_path="/tmp/repo",
            pane_id="%1",
        )

        with patch.object(tfp, "capture_pane_text", return_value="some text\n"), \
             patch.object(tfp, "strip_ansi", side_effect=lambda x: x), \
             patch.object(tfp, "list_repo_files", return_value=["src/main.py"]), \
             patch.object(tfp, "extract_visible_candidates", return_value=["src/main.py"]), \
             patch.object(tfp, "run_fzf_visible", return_value=tfp.FzfResult(query="README.md", key="enter", selection="")), \
             patch.object(tfp, "_open_target") as mock_open, \
             patch.object(tfp.subprocess, "run") as mock_run:

            tfp.cmd_pick(args)

        mock_open.assert_not_called()


class TestExtractVisibleCandidatesLineSuffix(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(__file__).parent / "_test_repo_line"
        self.tmp.mkdir(exist_ok=True)
        nested = self.tmp / "src"
        nested.mkdir(exist_ok=True)
        (nested / "main.py").write_text("print(1)")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_line_suffix_preserved_in_repo_path(self):
        text = "see src/main.py:12 for details"
        repo = ["src/main.py"]
        cands = tfp.extract_visible_candidates(text, repo, self.tmp, self.tmp)
        self.assertIn("src/main.py:12", cands)

    def test_line_suffix_preserved_in_basename(self):
        text = "main.py:12"
        repo = ["src/main.py"]
        cands = tfp.extract_visible_candidates(text, repo, self.tmp, self.tmp)
        self.assertIn("src/main.py:12", cands)


class TestOpenTargetAnnotate(unittest.TestCase):
    def test_annotate_file_sends_slash_command(self):
        state = tfp.DebugState()
        fake_file = Path("/tmp/repo/src/main.py")

        with patch.object(tfp, "resolve_existing_path", return_value=fake_file), \
             patch.object(tfp.subprocess, "run") as mock_run, \
             patch("os.execvp"):  # prevent process replacement if mode falls through
            mock_run.return_value = SimpleNamespace(returncode=0, stdout="")

            tfp._open_target(
                mode="annotate",
                target_text="src/main.py",
                pane_path=Path("/tmp/repo"),
                pane_id="%1",
                search_root=Path("/tmp/repo"),
                state=state,
            )

        # Should send literal text then Enter
        send_keys_calls = [
            call for call in mock_run.call_args_list
            if len(call.args[0]) >= 2 and call.args[0][0] == "tmux" and call.args[0][1] == "send-keys"
        ]
        self.assertEqual(len(send_keys_calls), 2, "expected two tmux send-keys calls")

        literal_call = send_keys_calls[0]
        self.assertIn("-l", literal_call.args[0])
        cmd_text = " ".join(literal_call.args[0])
        self.assertIn("/plannotator-annotate", cmd_text)
        self.assertIn("src/main.py", cmd_text)

        enter_call = send_keys_calls[1]
        self.assertIn("Enter", enter_call.args[0])

    def test_annotate_folder_blocked(self):
        state = tfp.DebugState()
        fake_dir = Path("/tmp/repo/src")
        fake_dir.mkdir(parents=True, exist_ok=True)

        try:
            with patch.object(tfp, "resolve_existing_path", return_value=fake_dir), \
                 patch.object(tfp.subprocess, "run") as mock_run, \
                 patch("os.execvp"):
                mock_run.return_value = SimpleNamespace(returncode=0, stdout="")

                tfp._open_target(
                    mode="annotate",
                    target_text="src",
                    pane_path=Path("/tmp/repo"),
                    pane_id="%1",
                    search_root=Path("/tmp/repo"),
                    state=state,
                )

            # Should show tmux message, not send keys
            send_keys_calls = [
                call for call in mock_run.call_args_list
                if len(call.args[0]) >= 2 and call.args[0][0] == "tmux" and call.args[0][1] == "send-keys"
            ]
            self.assertEqual(len(send_keys_calls), 0, "should not send keys for folder annotation")

            display_calls = [
                call for call in mock_run.call_args_list
                if len(call.args[0]) >= 2 and call.args[0][0] == "tmux" and call.args[0][1] == "display-message"
            ]
            self.assertTrue(
                any("folder" in str(call).lower() or "annotat" in str(call).lower() for call in display_calls),
                f"expected folder-blocked message, got: {display_calls}"
            )
        finally:
            import shutil
            shutil.rmtree(fake_dir, ignore_errors=True)

        # Should show tmux message, not send keys
        send_keys_calls = [
            call for call in mock_run.call_args_list
            if len(call.args[0]) >= 2 and call.args[0][0] == "tmux" and call.args[0][1] == "send-keys"
        ]
        self.assertEqual(len(send_keys_calls), 0, "should not send keys for folder annotation")

        display_calls = [
            call for call in mock_run.call_args_list
            if len(call.args[0]) >= 2 and call.args[0][0] == "tmux" and call.args[0][1] == "display-message"
        ]
        self.assertTrue(
            any("folder" in str(call).lower() or "annotat" in str(call).lower() for call in display_calls),
            f"expected folder-blocked message, got: {display_calls}"
        )


class TestLineTargetPreservation(unittest.TestCase):
    def test_nvim_preserves_line(self):
        state = tfp.DebugState()
        fake_file = Path("/tmp/repo/src/main.py")

        with patch.object(tfp, "resolve_existing_path", return_value=fake_file), \
             patch.object(tfp, "open_in_nvim_split") as mock_nvim:
            tfp._open_target(
                mode="nvim",
                target_text="src/main.py:12",
                pane_path=Path("/tmp/repo"),
                pane_id="%1",
                search_root=Path("/tmp/repo"),
                state=state,
            )

        mock_nvim.assert_called_once()
        args, _ = mock_nvim.call_args
        # open_in_nvim_split(path, line, pane_path, pane_id)
        self.assertEqual(args[1], "12")

    def test_annotate_strips_line(self):
        state = tfp.DebugState()
        fake_file = Path("/tmp/repo/src/main.py")

        with patch.object(tfp, "resolve_existing_path", return_value=fake_file), \
             patch.object(tfp.subprocess, "run") as mock_run, \
             patch("os.execvp"):
            mock_run.return_value = SimpleNamespace(returncode=0, stdout="")

            tfp._open_target(
                mode="annotate",
                target_text="src/main.py:12",
                pane_path=Path("/tmp/repo"),
                pane_id="%1",
                search_root=Path("/tmp/repo"),
                state=state,
            )

        literal_call = None
        for call in mock_run.call_args_list:
            cmd = call.args[0]
            if len(cmd) >= 3 and cmd[0] == "tmux" and cmd[1] == "send-keys" and "-l" in cmd:
                literal_call = call
                break

        self.assertIsNotNone(literal_call, "expected tmux send-keys -l call")
        cmd_text = " ".join(literal_call.args[0])
        self.assertIn("/plannotator-annotate", cmd_text)
        # Should NOT contain the line number in the annotate command
        self.assertNotIn(":12", cmd_text)
        self.assertIn("src/main.py", cmd_text)

    def test_default_app_ignores_line(self):
        state = tfp.DebugState()
        fake_file = Path("/tmp/repo/src/main.py")

        with patch.object(tfp, "resolve_existing_path", return_value=fake_file), \
             patch.object(tfp, "open_with_default_app") as mock_default:
            tfp._open_target(
                mode="default",
                target_text="src/main.py:12",
                pane_path=Path("/tmp/repo"),
                pane_id="%1",
                search_root=Path("/tmp/repo"),
                state=state,
            )

        mock_default.assert_called_once_with(fake_file)


class TestFzfCommands(unittest.TestCase):
    def test_visible_picker_not_called_when_empty_candidates(self):
        # After refactoring, empty candidates means no fzf call
        with patch.object(tfp.subprocess, "run") as mock_run:
            # If the implementation does call fzf, it should not happen for empty
            # This test documents that empty candidates => no fzf
            pass  # Covered by TestNoCandidates

    def test_fallback_picker_feeds_fd_results_to_fzf(self):
        completed = SimpleNamespace(returncode=0, stdout="src/main.py\n")
        with patch.object(tfp, "list_repo_files", return_value=["src/main.py", "README.md"]), \
             patch.object(tfp.subprocess, "run", return_value=completed) as run:
            selected = tfp.run_fallback_picker(Path("/tmp/repo"), "main")

        self.assertEqual(selected, "src/main.py")
        self.assertEqual(run.call_args.kwargs["input"], "src/main.py\nREADME.md\n")
        self.assertEqual(run.call_args.kwargs["stdout"], tfp.subprocess.PIPE)
        self.assertNotIn("capture_output", run.call_args.kwargs)

    def test_fzf_visible_includes_ctrl_y(self):
        completed = SimpleNamespace(returncode=1, stdout="query\nctrl-y\nselection")
        with patch.object(tfp.subprocess, "run", return_value=completed) as run:
            result = tfp.run_fzf_visible(["src/main.py"], Path("/tmp/repo"))

        self.assertIsNotNone(result)
        self.assertEqual(result.key, "ctrl-y")
        cmd = run.call_args.args[0]
        # Should be in --expect value
        expect_idx = cmd.index("--expect")
        self.assertIn("ctrl-y", cmd[expect_idx + 1])
        header_idx = cmd.index("--header")
        self.assertIn("annotate", cmd[header_idx + 1].lower())


class TestSendAnnotateCommand(unittest.TestCase):

    def test_copy_mode_cancelled_before_slash(self):
        """When pane is in copy mode, cancel is sent before the slash command."""
        calls = []
        responses = {
            ("display-message", "#{pane_in_mode}"): SimpleNamespace(returncode=0, stdout="1"),
        }

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            if cmd[0] == "tmux" and cmd[1] == "display-message":
                fmt = cmd[-1]
                if "pane_in_mode" in fmt:
                    return responses[("display-message", "#{pane_in_mode}")]
            return SimpleNamespace(returncode=0, stdout="")

        with patch.object(tfp.subprocess, "run", side_effect=fake_run):
            tfp.send_annotate_command("%1", "/tmp/repo/src/main.py")

        # First call should be display-message for pane_in_mode
        self.assertIn("pane_in_mode", calls[0][-1])

        # Second call should be cancel
        self.assertEqual(calls[1][0], "tmux")
        self.assertEqual(calls[1][1], "send-keys")
        self.assertIn("-X", calls[1])
        self.assertIn("cancel", calls[1])

        # Third call should be send-keys -l with slash command
        self.assertEqual(calls[2][0], "tmux")
        self.assertEqual(calls[2][1], "send-keys")
        self.assertIn("-l", calls[2])
        cmd_text = " ".join(calls[2])
        self.assertIn("/plannotator-annotate", cmd_text)

        # Fourth call should be Enter
        self.assertEqual(calls[3][0], "tmux")
        self.assertEqual(calls[3][1], "send-keys")
        self.assertIn("Enter", calls[3])

        # Fifth call should be display-message
        self.assertEqual(calls[4][0], "tmux")
        self.assertEqual(calls[4][1], "display-message")
        self.assertIn("Plannotator annotation requested", calls[4][-1])

    def test_not_in_copy_mode_no_cancel(self):
        """When pane is not in copy mode, no cancel is sent."""
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            if cmd[0] == "tmux" and cmd[1] == "display-message":
                fmt = cmd[-1]
                if "pane_in_mode" in fmt:
                    return SimpleNamespace(returncode=0, stdout="0")
            return SimpleNamespace(returncode=0, stdout="")

        with patch.object(tfp.subprocess, "run", side_effect=fake_run):
            tfp.send_annotate_command("%1", "/tmp/repo/src/main.py")

        # No cancel call should exist
        cancel_calls = [
            c for c in calls
            if len(c) >= 4 and c[0] == "tmux" and c[1] == "send-keys"
            and "-X" in c and "cancel" in c
        ]
        self.assertEqual(len(cancel_calls), 0, "no cancel should be sent when not in copy mode")

        # Should still send the slash command and Enter
        send_keys_calls = [
            c for c in calls
            if len(c) >= 3 and c[0] == "tmux" and c[1] == "send-keys"
        ]
        self.assertEqual(len(send_keys_calls), 2, "should send slash command + Enter")

        literal_call = send_keys_calls[0]
        self.assertIn("-l", literal_call)
        cmd_text = " ".join(literal_call)
        self.assertIn("/plannotator-annotate", cmd_text)
        self.assertIn("src/main.py", cmd_text)

        self.assertIn("Enter", send_keys_calls[1])

        # Should include display-message
        display_calls = [
            c for c in calls
            if len(c) >= 3 and c[0] == "tmux" and c[1] == "display-message"
            and "Plannotator" in c[-1]
        ]
        self.assertEqual(len(display_calls), 1, "should show Plannotator message")

    def test_path_with_spaces_is_quoted(self):
        """Paths containing spaces are shell-quoted with shlex.quote."""
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            if cmd[0] == "tmux" and cmd[1] == "display-message":
                return SimpleNamespace(returncode=0, stdout="0")
            return SimpleNamespace(returncode=0, stdout="")

        with patch.object(tfp.subprocess, "run", side_effect=fake_run):
            tfp.send_annotate_command("%1", "/tmp/repo/path with spaces/file.py")

        # Find the send-keys -l call
        literal_call = None
        for c in calls:
            if len(c) >= 4 and c[0] == "tmux" and c[1] == "send-keys" and "-l" in c:
                literal_call = c
                break

        self.assertIsNotNone(literal_call, "expected send-keys -l call")
        # The -l argument is the text. shlex.quote wraps the entire path in single quotes.
        quoted_idx = literal_call.index("-l") + 1
        text = literal_call[quoted_idx]
        self.assertIn("/plannotator-annotate", text)
        # The full absolute path should be single-quoted
        self.assertIn("'/tmp/repo/path with spaces/file.py'", text)


class TestChooseDefaultOpener(unittest.TestCase):
    def test_env_override(self):
        os.environ["TERMSCOPE_OPENER"] = "custom-opener --flag"
        self.assertEqual(tfp.choose_default_opener(), ["custom-opener", "--flag"])
        del os.environ["TERMSCOPE_OPENER"]

    def test_macos(self):
        orig = sys.platform
        try:
            sys.platform = "darwin"
            self.assertEqual(tfp.choose_default_opener(), ["open"])
        finally:
            sys.platform = orig

    def test_linux(self):
        orig = sys.platform
        try:
            sys.platform = "linux"
            # Ensure WSL env is not set
            wsl = os.environ.pop("WSL_DISTRO_NAME", None)
            self.assertEqual(tfp.choose_default_opener(), ["xdg-open"])
            if wsl is not None:
                os.environ["WSL_DISTRO_NAME"] = wsl
        finally:
            sys.platform = orig


class TestOpenUrl(unittest.TestCase):
    def test_macos_uses_safari(self):
        with patch.object(tfp.sys, "platform", "darwin"), \
             patch.object(tfp.os, "execvp") as mock_exec:
            # os.execvp replaces the process and never returns; simulate that.
            mock_exec.side_effect = SystemExit(0)
            with self.assertRaises(SystemExit):
                tfp.open_url("https://example.com")

        mock_exec.assert_called_once_with(
            "open",
            ["open", "-a", "Zen", "https://example.com"],
        )

    def test_non_macos_falls_back_to_default_app(self):
        with patch.object(tfp.sys, "platform", "linux"), \
             patch.object(tfp, "open_with_default_app") as mock_default:
            tfp.open_url("https://example.com")

        mock_default.assert_called_once_with("https://example.com")


class TestLinkPickerHeader(unittest.TestCase):
    def test_links_header_mentions_safari(self):
        completed = SimpleNamespace(returncode=1, stdout="query\nenter\nhttps://example.com")
        with patch.object(tfp.subprocess, "run", return_value=completed) as run:
            result = tfp.run_fzf_links(["https://example.com"])

        self.assertIsNotNone(result)
        self.assertEqual(result.key, "enter")
        cmd = run.call_args.args[0]
        header_idx = cmd.index("--header")
        self.assertIn("Zen", cmd[header_idx + 1])


class TestBackendDetection(unittest.TestCase):
    def test_tmux_pane_id(self):
        self.assertIsInstance(tfp.detect_backend("%1"), tfp.TmuxBackend)
        self.assertIsInstance(tfp.detect_backend("%42"), tfp.TmuxBackend)

    def test_herdr_pane_id(self):
        self.assertIsInstance(tfp.detect_backend("w1:p1"), tfp.HerdrBackend)
        self.assertIsInstance(tfp.detect_backend("w12:pT"), tfp.HerdrBackend)

    def test_empty_defaults_to_tmux(self):
        self.assertIsInstance(tfp.detect_backend(""), tfp.TmuxBackend)


class TestHerdrBackend(unittest.TestCase):
    def test_resolve_source_pane_path_parses_cwd(self):
        backend = tfp.HerdrBackend()
        pane_json = json.dumps({
            "result": {
                "pane": {"cwd": "/tmp/repo", "pane_id": "w1:p1"}
            }
        })

        with patch.object(tfp.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout=pane_json)) as run, \
             patch.object(backend, "_herdr_bin", return_value="herdr"):
            result = backend.resolve_source_pane_path(Path("/fallback"), "w1:p1")

        self.assertEqual(result, Path("/tmp/repo"))
        cmd = run.call_args.args[0]
        self.assertEqual(cmd[:3], ["herdr", "pane", "get"])
        self.assertEqual(cmd[3], "w1:p1")

    def test_resolve_source_pane_path_falls_back(self):
        backend = tfp.HerdrBackend()
        with patch.object(tfp.subprocess, "run", return_value=SimpleNamespace(returncode=1, stdout="")), \
             patch.object(backend, "_herdr_bin", return_value="herdr"):
            result = backend.resolve_source_pane_path(Path("/fallback"), "w1:p1")
        self.assertEqual(result, Path("/fallback"))

    def test_capture_pane_text_reads_visible(self):
        backend = tfp.HerdrBackend()
        with patch.object(tfp.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout="line1\nline2\n")) as run, \
             patch.object(backend, "_herdr_bin", return_value="herdr"):
            result = backend.capture_pane_text("w1:p1")
        self.assertEqual(result, "line1\nline2\n")
        cmd = run.call_args.args[0]
        self.assertEqual(cmd, ["herdr", "pane", "read", "w1:p1", "--source", "visible"])

    def test_send_annotate_command_runs_slash_command(self):
        backend = tfp.HerdrBackend()
        with patch.object(tfp.subprocess, "run") as run, \
             patch.object(backend, "_herdr_bin", return_value="herdr"):
            backend.send_annotate_command("w1:p1", "/tmp/repo/src/main.py")

        calls = run.call_args_list
        self.assertEqual(calls[0].args[0][:3], ["herdr", "pane", "run"])
        self.assertEqual(calls[0].args[0][3], "w1:p1")
        self.assertIn("/plannotator-annotate", calls[0].args[0][4])
        self.assertIn("/tmp/repo/src/main.py", calls[0].args[0][4])

        self.assertEqual(calls[1].args[0][:3], ["herdr", "notification", "show"])

    def test_open_in_nvim_split_splits_then_runs(self):
        backend = tfp.HerdrBackend()
        split_json = json.dumps({
            "result": {"pane": {"pane_id": "w1:p2"}}
        })

        with patch.object(tfp.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout=split_json)) as run, \
             patch.object(backend, "_herdr_bin", return_value="herdr"), \
             patch.object(tfp.sys, "exit") as mock_exit:
            backend.open_in_nvim_split(Path("/tmp/repo/src/main.py"), "12", Path("/tmp/repo"), "w1:p1")

        calls = run.call_args_list
        self.assertEqual(calls[0].args[0], [
            "herdr", "pane", "split", "w1:p1", "--direction", "right", "--cwd", "/tmp/repo"
        ])
        self.assertEqual(calls[1].args[0][:3], ["herdr", "pane", "run"])
        self.assertEqual(calls[1].args[0][3], "w1:p2")
        self.assertIn("nvim", calls[1].args[0][4])
        self.assertIn("+12", calls[1].args[0][4])
        mock_exit.assert_called_once_with(0)


if __name__ == "__main__":
    unittest.main()
