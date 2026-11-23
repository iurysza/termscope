#!/usr/bin/env python3
"""Tests for the Rex backend and floating-layer launcher. The rex CLI is fake."""

import importlib.util
import json
import os
import stat
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

_loader = SourceFileLoader("termscope_for_rex", str(ROOT / "termscope"))
_spec = importlib.util.spec_from_loader("termscope_for_rex", _loader)
ts = importlib.util.module_from_spec(_spec)
sys.modules["termscope_for_rex"] = ts
_spec.loader.exec_module(ts)

import termscope_rex  # noqa: E402


FAKE_REX = r'''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path

log = Path(os.environ["REX_FAKE_LOG"])
argv = sys.argv[1:]
stdin = ""
if len(argv) >= 2 and argv[0] == "api" and argv[1] == "call" and argv[-1] == "-":
    stdin = sys.stdin.read()
with log.open("a", encoding="utf-8") as fh:
    fh.write(json.dumps({"argv": argv, "stdin": stdin}) + "\n")

def fail(message, code):
    sys.stderr.write(message + "\n")
    raise SystemExit(code)

if argv[:1] == ["capture"]:
    if os.environ.get("REX_FAKE_CAPTURE_FAIL") == "1":
        fail("capture failed", 1)
    screen = os.environ.get("REX_FAKE_SCREEN") or "src/a.py\nhttps://example.com/a\n"
    sys.stdout.write(screen)
    raise SystemExit(0)

method = ""
if argv[:2] == ["api", "call"]:
    rest = argv[2:]
    if rest[:1] == ["-s"] and len(rest) >= 3:
        method = rest[2]
    elif rest:
        method = rest[0]

if method == "com.superlogical.terminal.pwd":
    if os.environ.get("REX_FAKE_PWD") == "empty":
        sys.stdout.write("{}")
    else:
        cwd = os.environ["REX_FAKE_CWD"]
        sys.stdout.write(json.dumps({"pwd": "file://rex" + cwd}))
    raise SystemExit(0)
if method == "com.superlogical.terminal.process":
    sys.stdout.write(json.dumps({
        "foreground": {
            "name": os.environ.get("REX_FAKE_FG", "zsh"),
            "cwd": os.environ.get("REX_FAKE_CWD", ""),
        },
    }))
    raise SystemExit(0)
if method == "session.describe_block":
    if os.environ.get("REX_FAKE_DESCRIBE") == "empty":
        sys.stdout.write("{}")
    else:
        sys.stdout.write(json.dumps({
            "block": {"window_id": "window:abc", "block_id": "block:src"},
        }))
    raise SystemExit(0)
if method == "session.view":
    block = os.environ.get("REX_BLOCK", "block:src")
    sys.stdout.write(json.dumps({"windows": [{
        "window_id": "window:from-view",
        "layers": [{"kind": "tiled", "blocks": [{"block_id": block}]}],
    }]}))
    raise SystemExit(0)
if method == "session.new_layer":
    if os.environ.get("REX_FAKE_LAYER_FAIL") == "1":
        fail("no window", 4)
    sys.stdout.write(json.dumps({
        "layer_id": "layer:01234567-89ab-cdef-0123-456789abcdef",
    }))
    raise SystemExit(0)
if argv[:1] and argv[0] in {"split", "run", "send", "send-key"}:
    code = int(os.environ.get("REX_FAKE_EXIT", "0"))
    if code != 0:
        fail("open failed", code)
    raise SystemExit(0)
fail("unexpected: " + " ".join(argv), 2)
'''


class RexFake(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.work = self.dir / "work"
        self.work.mkdir()
        self.log = self.dir / "rex.log"
        rex = self.dir / "rex"
        rex.write_text(FAKE_REX)
        rex.chmod(rex.stat().st_mode | stat.S_IXUSR)
        self.rex = str(rex)
        env = {
            "REX_BIN": self.rex,
            "REX_FAKE_LOG": str(self.log),
            "REX_FAKE_CWD": str(self.work),
            "REX_SESSION": "session:test",
            "REX_BLOCK": "block:src",
            "TERMSCOPE_LOG": str(self.dir / "termscope.log"),
            "TERMSCOPE_CONFIG": str(self.dir / "missing.toml"),
            "REX_FAKE_PWD": "",
            "REX_FAKE_FG": "zsh",
            "REX_FAKE_DESCRIBE": "",
            "REX_FAKE_CAPTURE_FAIL": "",
            "REX_FAKE_LAYER_FAIL": "",
            "REX_FAKE_EXIT": "0",
            "REX_FAKE_SCREEN": "",
        }
        patcher = patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)

    def records(self):
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines() if line]


class TestRexPaths(unittest.TestCase):
    def test_file_url_and_plain_path(self):
        self.assertEqual(ts.rex_file_url_path("file://host/Users/a%20b"), "/Users/a b")
        self.assertEqual(ts.rex_file_url_path("file:///Users/me"), "/Users/me")
        self.assertEqual(ts.rex_file_url_path("/tmp/x"), "/tmp/x")
        self.assertIsNone(ts.rex_file_url_path("file://host-only"))
        self.assertIsNone(ts.rex_file_url_path(""))
        self.assertIsNone(ts.rex_file_url_path(None))

    def test_window_from_view(self):
        view = {"windows": [
            {"window_id": "window:other", "layers": [{"blocks": [{"block_id": "block:no"}]}]},
            {"window_id": "window:yes", "layers": [
                {"kind": "tiled", "blocks": [{"block_id": "block:src"}]},
            ]},
        ]}
        self.assertEqual(ts.window_id_from_view(view, "block:src"), "window:yes")
        self.assertIsNone(ts.window_id_from_view(view, "block:missing"))
        self.assertIsNone(ts.window_id_from_view({}, "block:src"))


class TestRexBinary(unittest.TestCase):
    def test_rex_bin_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            custom = Path(tmp) / "custom-rex"
            custom.write_text("#!/bin/sh\n")
            custom.chmod(0o755)
            with patch.dict(os.environ, {"REX_BIN": str(custom), "PATH": "/usr/bin:/bin"}):
                self.assertEqual(ts.rex_binary(), str(custom))

    def test_path_then_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            path_dir = home / "bin"
            path_dir.mkdir()
            on_path = path_dir / "rex"
            on_path.write_text("#!/bin/sh\n")
            on_path.chmod(0o755)
            bundle = home / ts._REX_BUNDLE
            bundle.parent.mkdir(parents=True)
            bundle.write_text("#!/bin/sh\n")
            bundle.chmod(0o755)
            with patch.dict(os.environ, {"REX_BIN": "", "PATH": str(path_dir), "HOME": str(home)}):
                self.assertEqual(ts.rex_binary(), str(on_path))
            with patch.dict(os.environ, {"REX_BIN": "", "PATH": "/usr/bin:/bin", "HOME": str(home)}):
                self.assertEqual(ts.rex_binary(), str(bundle))
            empty = home / "empty-home"
            empty.mkdir()
            with patch.dict(os.environ, {"REX_BIN": "", "PATH": "/usr/bin:/bin", "HOME": str(empty)}):
                self.assertIsNone(ts.rex_binary())


class TestRexDetect(unittest.TestCase):
    def test_block_id_and_environment(self):
        cleared = {"REX_SESSION": "", "REX_BLOCK": ""}
        with patch.dict(os.environ, cleared):
            self.assertEqual(ts.detect_backend("block:0123abcd").name, "rex")
            self.assertEqual(ts.detect_backend("").name, "tmux")
            self.assertEqual(ts.detect_backend("%1").name, "tmux")
        present = {"REX_SESSION": "session:s", "REX_BLOCK": "block:b"}
        with patch.dict(os.environ, present):
            self.assertEqual(ts.detect_backend("").name, "rex")
            self.assertEqual(ts.detect_backend("block:b").name, "rex")
            self.assertEqual(ts.detect_backend("%3").name, "tmux")
            self.assertEqual(ts.detect_backend("w1:p1").name, "herdr")
            self.assertEqual(ts.detect_backend("1-2").name, "herdr")
            self.assertEqual(ts.detect_backend("t14x").name, "app")
            self.assertEqual(ts.detect_backend("other").name, "tmux")
        self.assertEqual(ts.choose_backend("rex", "%1").name, "rex")

    def test_cli_accepts_rex(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(sys, "argv", [
                 "termscope", "pick", "--pane-path", "/tmp", "--pane-id", "block:ab",
                 "--multiplexer", "rex",
             ]), patch.object(ts, "cmd_pick") as pick, \
             patch.dict(os.environ, {"TERMSCOPE_LOG": str(Path(tmp) / "log")}):
            ts.main()
        self.assertEqual(pick.call_args.args[0].multiplexer, "rex")


class TestRexBackend(RexFake):
    def test_capture_is_screen_and_scrollback_command(self):
        text = ts.RexBackend().capture_pane_text("block:src")
        self.assertEqual(text, "src/a.py\nhttps://example.com/a\n")
        argv = self.records()[0]["argv"]
        self.assertEqual(argv[0], "capture")
        self.assertEqual(argv[argv.index("-s") + 1], "session:test")
        self.assertEqual(argv[argv.index("-b") + 1], "block:src")
        self.assertIn("--trim", argv)
        self.assertIn("--unwrap", argv)
        self.assertNotIn("--lines", argv)

    def test_capture_failure_is_empty(self):
        os.environ["REX_FAKE_CAPTURE_FAIL"] = "1"
        self.assertEqual(ts.RexBackend().capture_pane_text("block:src"), "")

    def test_capture_without_rex_is_empty(self):
        os.environ["REX_BIN"] = ""
        os.environ["PATH"] = "/usr/bin:/bin"
        os.environ["HOME"] = str(self.dir)
        self.assertEqual(ts.RexBackend().capture_pane_text("block:src"), "")

    def test_cwd_from_pwd_file_url(self):
        backend = ts.RexBackend()
        self.assertEqual(backend.resolve_source_pane_path(Path("/nope"), "block:src"), self.work)
        methods = [r["argv"] for r in self.records()]
        self.assertTrue(any("com.superlogical.terminal.pwd" in argv for argv in methods))
        self.assertFalse(any("com.superlogical.terminal.process" in argv for argv in methods))

    def test_cwd_falls_back_to_foreground(self):
        os.environ["REX_FAKE_PWD"] = "empty"
        backend = ts.RexBackend()
        self.assertEqual(backend.resolve_source_pane_path(Path("/nope"), "block:src"), self.work)
        methods = [" ".join(r["argv"]) for r in self.records()]
        self.assertTrue(any("com.superlogical.terminal.process" in item for item in methods))

    def test_cwd_falls_back_to_pane_path(self):
        os.environ["REX_FAKE_PWD"] = "empty"
        os.environ["REX_FAKE_CWD"] = str(self.dir / "missing")
        self.assertEqual(
            ts.RexBackend().resolve_source_pane_path(Path("/nope"), "block:src"),
            Path("/nope"),
        )

    def test_window_from_describe_then_view(self):
        self.assertEqual(ts.RexBackend().window_id("block:src"), "window:abc")
        self.assertFalse(any("session.view" in r["argv"] for r in self.records()))
        self.log.write_text("")
        os.environ["REX_FAKE_DESCRIBE"] = "empty"
        self.assertEqual(ts.RexBackend().window_id("block:src"), "window:from-view")

    def test_annotate_shell_and_agent(self):
        backend = ts.RexBackend()
        backend.send_annotate_command("block:src", "/a b.md")
        send = next(r for r in self.records() if r["argv"][0] == "send")
        self.assertEqual(send["argv"][-1], "plannotator annotate '/a b.md'")
        key = next(r for r in self.records() if r["argv"][0] == "send-key")
        self.assertEqual(key["argv"][-1], "enter")

        self.log.write_text("")
        os.environ["REX_FAKE_FG"] = "claude"
        backend.send_annotate_command("block:src", "/a b.md")
        send = next(r for r in self.records() if r["argv"][0] == "send")
        self.assertEqual(send["argv"][-1], "/plannotator-annotate '/a b.md'")

    def _open(self, line, target="split"):
        if target != "split":
            Path(os.environ["TERMSCOPE_CONFIG"]).write_text(
                f'open_target = "{target}"\n', encoding="utf-8",
            )
        with self.assertRaises(SystemExit) as caught:
            ts.RexBackend().open_in_nvim_split(Path("/f.py"), line, self.work, "block:src")
        return caught.exception.code

    def test_split_open(self):
        self.assertEqual(self._open("12"), 0)
        argv = next(r["argv"] for r in self.records() if r["argv"][0] == "split")
        self.assertIn("--split=right", argv)
        self.assertIn("--keep-open", argv)
        self.assertEqual(argv[argv.index("-b") + 1], "block:src")
        self.assertEqual(argv[argv.index("-c") + 1], str(self.work))
        tail = argv[argv.index("--") + 1:]
        self.assertEqual(tail[-2:], ["+12", "/f.py"])

    def test_tab_open_and_close_on_exit(self):
        self.assertEqual(self._open("", "tab"), 0)
        argv = next(r["argv"] for r in self.records() if r["argv"][0] == "run")
        self.assertNotIn("--split=right", argv)
        self.assertIn("--keep-open", argv)
        Path(os.environ["TERMSCOPE_CONFIG"]).write_text(
            'open_target = "split"\nclose_on_exit = true\n', encoding="utf-8",
        )
        self.log.write_text("")
        self.assertEqual(self._open("3"), 0)
        argv = next(r["argv"] for r in self.records() if r["argv"][0] == "split")
        self.assertNotIn("--keep-open", argv)

    def test_open_failure(self):
        os.environ["REX_FAKE_EXIT"] = "1"
        self.assertEqual(self._open("1"), 1)

    def test_popup_replaces_the_layer(self):
        Path(os.environ["TERMSCOPE_CONFIG"]).write_text('open_target = "popup"\n', encoding="utf-8")
        with patch.object(ts, "_has_terminal", return_value=True), \
             patch.object(ts, "_nvim_path", return_value="/usr/bin/nvim"), \
             patch.object(ts.os, "chdir") as chdir, \
             patch.object(ts.os, "execvp", side_effect=SystemExit(0)) as execvp:
            with self.assertRaises(SystemExit):
                ts.RexBackend().open_in_nvim_split(Path("/f.py"), "4", self.work, "block:src")
        chdir.assert_called_once_with(self.work)
        execvp.assert_called_once_with("/usr/bin/nvim", ["/usr/bin/nvim", "+4", "/f.py"])
        self.assertFalse(self.records())

    def test_missing_block_does_not_split(self):
        os.environ["REX_BLOCK"] = ""
        with self.assertRaises(SystemExit) as caught:
            ts.RexBackend().open_in_nvim_split(Path("/f.py"), "", self.work, "")
        self.assertEqual(caught.exception.code, 1)
        self.assertFalse(any(r["argv"][0] in {"split", "run"} for r in self.records()))


class TestRexLauncher(RexFake):
    def setUp(self):
        super().setUp()
        # Keep Television resolution inside the temp home.
        os.environ["HOME"] = str(self.dir)
        os.environ["XDG_CONFIG_HOME"] = str(self.dir / "config")
        os.environ["HOMEBREW_PREFIX"] = ""
        os.environ["TERMSCOPE_TV"] = ""
        os.environ["TERMSCOPE_SORT"] = ""
        os.environ["PATH"] = "/usr/bin:/bin"
        # REX_BIN is an absolute fake, so the stripped PATH does not hide it.
        termscope_rex._picker_module = None

    def test_request_shape(self):
        body = termscope_rex.build_layer_request(
            "pick", "block:src", "/work", "session:test",
            sort="alpha", script="/s/termscope", python="/py", television="/tv",
            window_id="window:abc",
        )
        self.assertEqual(body["bounds"], [0.1, 0.2, 0.8, 0.6])
        self.assertTrue(body["focus"])
        self.assertEqual(body["window_id"], "window:abc")
        options = body["layout"]["block"]["options"]
        self.assertEqual(options["shell"], "none")
        self.assertEqual(options["cwd"], "/work")
        self.assertNotIn("exit", options)
        command = options["command"]
        self.assertEqual(command[:3], ["/usr/bin/env", "TERMSCOPE_TV=/tv", "REX_SESSION=session:test"])
        self.assertEqual(command[command.index("--multiplexer") + 1], "rex")
        self.assertEqual(command[command.index("--sort") + 1], "alpha")
        self.assertIn("pick", command)

    def test_parse_layer_id(self):
        good = "layer:01234567-89ab-cdef-0123-456789abcdef"
        self.assertEqual(termscope_rex.parse_layer_id(json.dumps({"layer_id": good})), good)
        self.assertIsNone(termscope_rex.parse_layer_id('{"ok":false,"error":"x"}'))
        self.assertIsNone(termscope_rex.parse_layer_id('{"layer_id":"nope"}'))
        self.assertIsNone(termscope_rex.parse_layer_id("nope"))

    def test_open_launches_layer_over_the_block_window(self):
        code = termscope_rex.main(["--open", "--session", "session:test", "--block", "block:src"])
        self.assertEqual(code, 0)
        layer = next(r for r in self.records() if "session.new_layer" in r["argv"])
        self.assertEqual(layer["argv"][layer["argv"].index("-s") + 1], "session:test")
        body = json.loads(layer["stdin"])
        self.assertEqual(body["window_id"], "window:abc")
        self.assertEqual(body["bounds"], [0.1, 0.2, 0.8, 0.6])
        command = body["layout"]["block"]["options"]["command"]
        self.assertIn("pick", command)
        self.assertEqual(command[command.index("--pane-id") + 1], "block:src")
        self.assertEqual(command[command.index("--multiplexer") + 1], "rex")
        self.assertIn("REX_SESSION=session:test", command)
        self.assertEqual(body["layout"]["block"]["options"]["cwd"], str(self.work))

    def test_links_and_explicit_cwd(self):
        code = termscope_rex.main([
            "--open-links", "--session", "session:test", "--block", "block:src",
            "--cwd", "/given", "--sort", "alpha",
        ])
        self.assertEqual(code, 0)
        self.assertFalse(any("com.superlogical.terminal.pwd" in r["argv"] for r in self.records()))
        layer = next(r for r in self.records() if "session.new_layer" in r["argv"])
        body = json.loads(layer["stdin"])
        command = body["layout"]["block"]["options"]["command"]
        self.assertIn("links", command)
        self.assertEqual(command[command.index("--sort") + 1], "alpha")
        self.assertEqual(body["layout"]["block"]["options"]["cwd"], "/given")

    def test_float_failure(self):
        os.environ["REX_FAKE_LAYER_FAIL"] = "1"
        code = termscope_rex.main(["--open"])
        self.assertEqual(code, 1)

    def test_missing_session_or_rex(self):
        os.environ["REX_SESSION"] = ""
        self.assertEqual(termscope_rex.main(["--open", "--block", "block:src"]), 1)
        self.assertFalse(self.records())
        os.environ["REX_BIN"] = ""
        os.environ["HOME"] = str(self.dir / "no-bundle")
        Path(os.environ["HOME"]).mkdir()
        self.assertEqual(termscope_rex.main([
            "--open", "--session", "session:test", "--block", "block:src",
        ]), 1)


if __name__ == "__main__":
    unittest.main()
