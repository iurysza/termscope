#!/usr/bin/env python3
"""Tests for the Herdr.app backend, float launcher and key merge."""

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
sys.path.insert(0, str(ROOT / "scripts"))

_loader = SourceFileLoader("termscope_for_app", str(ROOT / "termscope"))
_spec = importlib.util.spec_from_loader("termscope_for_app", _loader)
ts = importlib.util.module_from_spec(_spec)
sys.modules["termscope_for_app"] = ts
_spec.loader.exec_module(ts)

import herdr_app_keys  # noqa: E402
import termscope_app  # noqa: E402


def make_fake(directory: Path, name: str, script: str) -> str:
    path = directory / name
    path.write_text("#!/bin/sh\n" + script)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return str(path)


class FakeTools(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.log = self.dir / "calls.log"
        self.addCleanup(self.tmp.cleanup)
        self.work = self.dir / "work"
        self.work.mkdir()
        get = json.dumps({"cwd": str(self.dir), "foreground": {"cwd": str(self.work)},
                          "status": {"app": "pi"}})
        self.hc = make_fake(self.dir, "hc", f'''
echo "hc $*" >> "{self.log}"
case "$1" in
  get) cat <<'JSON'
{get}
JSON
  ;;
  read) cat <<'JSON'
{{"complete":true,"how":"screen","text":"src/a.py\\nhello"}}
JSON
  ;;
esac
''')
        ls = json.dumps({"spaces": [{"id": "sp1", "tabs": [{"terminals": [
            {"terminal": "t1", "pane": "pe1"}]}]}]})
        self.app = make_fake(self.dir, "herdr-app", f'''
echo "herdr-app $*" >> "{self.log}"
case "$1" in
  ls) cat <<'JSON'
{ls}
JSON
  ;;
esac
''')
        env = {"HC_BIN_PATH": self.hc, "HERDR_APP_BIN_PATH": self.app,
               "TERMSCOPE_CONFIG": str(self.dir / "config.toml"),
               "TERMSCOPE_LOG": str(self.dir / "log")}
        patcher = patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)

    def calls(self):
        return self.log.read_text().splitlines() if self.log.exists() else []


class TestAppBackend(FakeTools):
    def test_detect_and_choose(self):
        self.assertEqual(ts.detect_backend("t14x").name, "app")
        self.assertEqual(ts.detect_backend("w1:p2").name, "herdr")
        self.assertEqual(ts.detect_backend("%3").name, "tmux")
        self.assertEqual(ts.choose_backend("app", "whatever").name, "app")
        self.assertEqual(ts.choose_backend("auto", "t9").name, "app")

    def test_resolve_prefers_foreground_cwd(self):
        b = ts.AppBackend()
        self.assertEqual(b.resolve_source_pane_path(Path("/nope"), "t1"), self.work)
        self.assertEqual(b.resolve_source_pane_path(Path("/nope"), ""), Path("/nope"))

    def test_capture(self):
        self.assertEqual(ts.AppBackend().capture_pane_text("t1"), "src/a.py\nhello")
        self.assertIn("hc read t1 --json --lines 0", self.calls())

    def test_annotate_agent_vs_shell(self):
        b = ts.AppBackend()
        b.send_annotate_command("t1", "/a b.md")
        self.assertIn("hc send t1 /plannotator-annotate '/a b.md'", self.calls())
        shell_get = json.dumps({"cwd": "/", "status": {}})
        make_fake(self.dir, "hc", f'''
echo "hc $*" >> "{self.log}"
[ "$1" = get ] && echo '{shell_get}'
''')
        b.send_annotate_command("t1", "/x.md")
        self.assertIn("hc send t1 plannotator annotate /x.md", self.calls())

    def test_split_open(self):
        with self.assertRaises(SystemExit) as cm:
            ts.AppBackend().open_in_nvim_split(Path("/f.py"), "12", self.work, "t1")
        self.assertEqual(cm.exception.code, 0)
        call = [c for c in self.calls() if c.startswith("herdr-app do pane.split")][0]
        self.assertIn("--pane pe1", call)
        self.assertIn("--direction right", call)
        self.assertIn('"+12"', call)

    def test_tab_open(self):
        Path(os.environ["TERMSCOPE_CONFIG"]).write_text('open_target = "tab"\n')
        with self.assertRaises(SystemExit):
            ts.AppBackend().open_in_nvim_split(Path("/f.py"), "", self.work, "t1")
        call = [c for c in self.calls() if c.startswith("herdr-app do tab.new")][0]
        self.assertIn("--space sp1", call)
        self.assertIn(f"--folder {self.work}", call)

    def test_tab_unknown_terminal_fails(self):
        Path(os.environ["TERMSCOPE_CONFIG"]).write_text('open_target = "tab"\n')
        with self.assertRaises(SystemExit) as cm:
            ts.AppBackend().open_in_nvim_split(Path("/f.py"), "", self.work, "t404")
        self.assertEqual(cm.exception.code, 1)
        self.assertFalse(any(c.startswith("herdr-app do tab.new") for c in self.calls()))

    def test_split_unknown_terminal_fails(self):
        with self.assertRaises(SystemExit) as cm:
            ts.AppBackend().open_in_nvim_split(Path("/f.py"), "1", self.work, "t404")
        self.assertEqual(cm.exception.code, 1)

    def test_settings_sources(self):
        cfg = Path(os.environ["TERMSCOPE_CONFIG"])
        cfg.write_text('open_target = "popup"\nclose_on_exit = true\n')
        self.assertEqual(ts.open_settings(app=True),
                         {"open_target": "popup", "close_on_exit": True})
        # Legacy path ignores TERMSCOPE_CONFIG.
        with patch.dict(os.environ, {"HERDR_PLUGIN_CONFIG_DIR": ""}):
            self.assertEqual(ts.open_settings()["open_target"], "split")


class TestLauncher(FakeTools):
    def test_build_request(self):
        req = termscope_app.build_float_request("pick", "t1", "/d", "alpha",
                                                script="/s/termscope", python="/py")
        self.assertEqual(req["cwd"], "/d")
        self.assertEqual(req["argv"], ["/py", "/s/termscope", "pick", "--pane-path", "/d",
                                       "--pane-id", "t1", "--multiplexer", "app",
                                       "--sort", "alpha"])
        req = termscope_app.build_float_request("links", "t1", "/d", script="/s", python="/py",
                                                television="/tv")
        self.assertEqual(req["argv"][:3], ["/usr/bin/env", "TERMSCOPE_TV=/tv", "/py"])
        self.assertNotIn("--sort", req["argv"])
        plain = termscope_app.build_float_request("pick", "t1", "/d", None, script="/s", python="/py")
        self.assertNotIn("--sort", plain["argv"])

    def test_resolve_sort(self):
        with patch.dict(os.environ, {"TERMSCOPE_SORT": "alpha"}):
            self.assertEqual(termscope_app.resolve_sort(None), "alpha")
            self.assertEqual(termscope_app.resolve_sort("appearance"), "appearance")
        with patch.dict(os.environ, {"TERMSCOPE_SORT": "sideways"}):
            self.assertIsNone(termscope_app.resolve_sort(None))
        with patch.dict(os.environ, {"TERMSCOPE_SORT": ""}):
            self.assertIsNone(termscope_app.resolve_sort(None))

    def test_parse_response(self):
        self.assertIsNone(termscope_app.parse_float_response('{"ok":true}'))
        self.assertEqual(termscope_app.parse_float_response('{"ok":false,"error":{"message":"boom"}}'), "boom")
        self.assertIn("unreadable", termscope_app.parse_float_response("nope"))

    def run_main(self, ui_script, *argv):
        ui = make_fake(self.dir, "herdr-ui", ui_script)
        with patch.dict(os.environ, {"HERDR_UI_BIN": ui}):
            return termscope_app.main(list(argv))

    def test_success_passes_terminal_and_request(self):
        captured = self.dir / "req.json"
        rc = self.run_main(
            f'cat > "{captured}"; echo "$HC_TERMINAL_ID" > "{self.dir}/tid"; '
            'echo \'{"version":1,"ok":true,"value":{"placement":"float"}}\'',
            "--open", "--terminal", "t1")
        self.assertEqual(rc, 0)
        req = json.loads(captured.read_text())
        self.assertEqual(req["name"], "termscope")
        self.assertEqual(req["cwd"], str(self.work))
        self.assertIn("pick", req["argv"])
        self.assertEqual((self.dir / "tid").read_text().strip(), "t1")

    def test_links_subcommand(self):
        captured = self.dir / "req.json"
        self.run_main(f'cat > "{captured}"; echo \'{{"ok":true}}\'', "--open-links", "--terminal", "t1")
        self.assertIn("links", json.loads(captured.read_text())["argv"])

    def test_sort_from_env_is_forwarded(self):
        captured = self.dir / "req.json"
        with patch.dict(os.environ, {"TERMSCOPE_SORT": "alpha"}):
            self.run_main(f'cat > "{captured}"; echo \'{{"ok":true}}\'', "--open", "--terminal", "t1")
        argv = json.loads(captured.read_text())["argv"]
        self.assertEqual(argv[argv.index("--sort") + 1], "alpha")

    def test_unset_sort_is_omitted(self):
        captured = self.dir / "req.json"
        with patch.dict(os.environ, {"TERMSCOPE_SORT": ""}):
            self.run_main(f'cat > "{captured}"; echo \'{{"ok":true}}\'', "--open", "--terminal", "t1")
        self.assertNotIn("--sort", json.loads(captured.read_text())["argv"])

    def test_float_failure(self):
        rc = self.run_main('echo \'{"ok":false,"error":"no window"}\'; exit 3', "--open", "--terminal", "t1")
        self.assertEqual(rc, 1)

    def test_missing_herdr_ui(self):
        with patch.dict(os.environ, {"HERDR_UI_BIN": "", "PATH": str(self.dir), "HOME": str(self.dir)}):
            self.assertEqual(termscope_app.main(["--open", "--terminal", "t1"]), 1)

    def test_no_terminal(self):
        env = {k: v for k, v in os.environ.items() if k != "HC_TERMINAL_ID"}
        ui = make_fake(self.dir, "herdr-ui", "exit 0")
        env["HERDR_UI_BIN"] = ui
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(termscope_app.main(["--open"]), 1)


class TestMods(unittest.TestCase):
    def test_launch_keeps_env_and_closes_after_exec(self):
        for name in ("termscope", "termscope-links"):
            text = (ROOT / "herdr-app" / "mods" / name / "main.js").read_text()
            self.assertNotIn('"-i"', text)
            self.assertNotIn('"PATH=', text)
            self.assertNotIn('"HOME=', text)
            body = text[text.index("cx.spawn"):]
            self.assertLess(body.index("await launch"), body.index("close()"))


class TestKeys(unittest.TestCase):
    def test_adds_when_free(self):
        out, added, skipped = herdr_app_keys.merge({"global": {"cmd-q": "app.quit"}})
        self.assertEqual(added, ["ctrl-shift-a", "ctrl-shift-e"])
        self.assertEqual(out["global"]["ctrl-shift-a"], "mod.open:termscope")
        self.assertEqual(skipped, [])

    def test_never_overwrites(self):
        keys = {"global": {"ctrl-shift-e": "other"}}
        out, added, skipped = herdr_app_keys.merge(keys)
        self.assertEqual(added, ["ctrl-shift-a"])
        self.assertEqual(out["global"]["ctrl-shift-e"], "other")
        self.assertIn("already bound to other", skipped[0])
        self.assertEqual(keys, {"global": {"ctrl-shift-e": "other"}})

    def test_idempotent(self):
        once, _, _ = herdr_app_keys.merge({})
        twice, added, _ = herdr_app_keys.merge(once)
        self.assertEqual(once, twice)
        self.assertEqual(added, [])

    def test_remove_only_ours(self):
        keys = {"global": {"ctrl-shift-a": "mod.open:termscope", "ctrl-shift-e": "other"}}
        out, removed = herdr_app_keys.remove(keys)
        self.assertEqual(removed, ["ctrl-shift-a"])
        self.assertEqual(out["global"], {"ctrl-shift-e": "other"})

    def test_cli_dry_run_and_write(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "keys.json"
            path.write_text("{}")
            herdr_app_keys.main(["x", "add", str(path), "--dry-run"])
            self.assertEqual(json.loads(path.read_text()), {})
            herdr_app_keys.main(["x", "add", str(path)])
            self.assertIn("ctrl-shift-a", json.loads(path.read_text())["global"])


if __name__ == "__main__":
    unittest.main()
