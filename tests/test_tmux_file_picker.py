#!/usr/bin/env python3
"""Unit tests for tmux-file-picker pure functions."""

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
script_path = Path(__file__).parent.parent / "tmux-file-picker"
loader = SourceFileLoader("tmux_file_picker", str(script_path.resolve()))
spec = importlib.util.spec_from_loader("tmux_file_picker", loader)
tfp = importlib.util.module_from_spec(spec)
sys.modules["tmux_file_picker"] = tfp
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
    def test_empty_candidates_shows_message_no_fzf(self):
        args = SimpleNamespace(
            pane_path="/tmp/repo",
            pane_id="%1",
        )

        with patch.object(tfp, "capture_pane_text", return_value="no paths here\n"), \
             patch.object(tfp, "strip_ansi", side_effect=lambda x: x), \
             patch.object(tfp, "list_repo_files", return_value=[]), \
             patch.object(tfp, "extract_visible_candidates", return_value=[]), \
             patch.object(tfp, "run_fzf_visible") as mock_fzf, \
             patch.object(tfp.subprocess, "run") as mock_run, \
             patch("os.execvp"):

            # tmux display-message mock
            mock_run.return_value = SimpleNamespace(returncode=0, stdout="")

            tfp.cmd_pick(args)

        # run_fzf_visible should NOT be called when candidates are empty
        mock_fzf.assert_not_called()

        # tmux display-message should be called with the no-candidates message
        display_calls = [
            call for call in mock_run.call_args_list
            if len(call.args[0]) >= 2
            and call.args[0][0] == "tmux"
            and call.args[0][1] == "display-message"
        ]
        self.assertTrue(
            any("No visible files/folders found" in str(call) for call in display_calls),
            f"expected 'No visible files/folders found' in display-message calls, got: {display_calls}"
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


class TestChooseDefaultOpener(unittest.TestCase):
    def test_env_override(self):
        os.environ["TMUX_FILE_PICKER_OPENER"] = "custom-opener --flag"
        self.assertEqual(tfp.choose_default_opener(), ["custom-opener", "--flag"])
        del os.environ["TMUX_FILE_PICKER_OPENER"]

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


if __name__ == "__main__":
    unittest.main()
