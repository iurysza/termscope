#!/usr/bin/env python3
"""Contract tests for the Herdr plugin surface."""

import importlib.util
import json
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

ROOT = Path(__file__).parent.parent
spec = importlib.util.spec_from_file_location("termscope_herdr", ROOT / "termscope_herdr.py")
wrapper = importlib.util.module_from_spec(spec)
sys.modules["termscope_herdr"] = wrapper
spec.loader.exec_module(wrapper)


class TestManifest(unittest.TestCase):
    def test_popup_contract(self):
        manifest = tomllib.loads((ROOT / "herdr-plugin.toml").read_text())
        self.assertEqual(manifest["version"], "0.2.0")
        self.assertEqual(manifest["min_herdr_version"], "0.7.4")
        self.assertEqual(
            manifest["build"],
            [{
                "platforms": ["linux", "macos"],
                "command": ["sh", "scripts/install-dependencies.sh"],
            }],
        )
        self.assertEqual({pane["id"] for pane in manifest["panes"]}, {"picker", "link-picker"})
        for pane in manifest["panes"]:
            self.assertEqual(pane["placement"], "popup")
            self.assertEqual(pane["width"], "80%")
            self.assertEqual(pane["height"], "60%")

    def test_television_channels_preserve_both_orders(self):
        appearance = tomllib.loads((ROOT / "cable" / "termscope-appearance.toml").read_text())
        alpha = tomllib.loads((ROOT / "cable" / "termscope-alpha.toml").read_text())
        self.assertEqual(appearance["metadata"]["name"], "termscope-appearance")
        self.assertEqual(alpha["metadata"]["name"], "termscope-alpha")
        self.assertEqual(appearance["source"]["command"][0]["name"], "Appearance")
        self.assertEqual(alpha["source"]["command"][0]["name"], "Alphabetical")
        for channel in (appearance, alpha):
            self.assertEqual(channel["source"]["display"], "{split:\\t:1..}")
            self.assertEqual(channel["source"]["output"], "{split:\\t:0}")
            self.assertTrue(channel["source"]["no_sort"])
            self.assertFalse(channel["source"]["frecency"])
            self.assertEqual(channel["keybindings"]["ctrl-s"], "cycle_sources")
            preview = channel["preview"]["command"]
            self.assertIn("{split:\\t:0}", preview)
            self.assertNotIn("'{}'", preview)
            self.assertEqual(
                channel["ui"]["preview_panel"]["footer"],
                "Enter  Neovim  ·  Ctrl-O  Default app  ·  Ctrl-Y  Plannotator",
            )


class TestHerdrWrapper(unittest.TestCase):
    def test_action_opens_popup_with_source_context(self):
        pane = json.dumps({"result": {"pane": {"cwd": "/tmp/repo", "agent": "pi"}}})
        responses = [
            SimpleNamespace(returncode=0, stdout=pane, stderr=""),
            SimpleNamespace(returncode=0, stdout="", stderr=""),
        ]
        env = {
            "HERDR_PANE_ID": "1-1",
            "HERDR_BIN_PATH": "/tmp/herdr",
            "HERDR_PLUGIN_ID": "termscope",
        }
        with patch.dict(os.environ, env, clear=True), \
             patch.object(wrapper.subprocess, "run", side_effect=responses) as run:
            wrapper.open_popup("picker")

        self.assertEqual(run.call_args_list[0].args[0], ["/tmp/herdr", "pane", "get", "1-1"])
        command = run.call_args_list[1].args[0]
        self.assertEqual(command[:6], [
            "/tmp/herdr", "plugin", "pane", "open", "--plugin", "termscope"
        ])
        self.assertIn("--placement", command)
        self.assertEqual(command[command.index("--placement") + 1], "popup")
        self.assertIn("SOURCE_PANE_ID=1-1", command)
        self.assertIn("SOURCE_PANE_CWD=/tmp/repo", command)
        self.assertIn("SOURCE_PANE_AGENT=pi", command)
        self.assertTrue(run.call_args_list[1].kwargs["capture_output"])

    def test_popup_launch_failure_is_propagated(self):
        pane = json.dumps({"result": {"pane": {"cwd": "/tmp/repo"}}})
        responses = [
            SimpleNamespace(returncode=0, stdout=pane, stderr=""),
            SimpleNamespace(returncode=1, stdout="", stderr="ui_busy"),
        ]
        with patch.dict(os.environ, {"HERDR_PANE_ID": "1-1"}, clear=True), \
             patch.object(wrapper.subprocess, "run", side_effect=responses):
            with self.assertRaisesRegex(SystemExit, "ui_busy"):
                wrapper.open_popup("picker")

    def test_popup_runs_shared_television_picker(self):
        env = {
            "SOURCE_PANE_ID": "1-1",
            "SOURCE_PANE_CWD": "/tmp/repo",
            "HERDR_PLUGIN_ROOT": str(ROOT),
            "TERMSCOPE_SORT": "alpha",
        }
        with patch.dict(os.environ, env, clear=True), \
             patch.object(
                 wrapper.subprocess,
                 "run",
                 return_value=SimpleNamespace(returncode=0),
             ) as run:
            wrapper.run_picker("pick")

        command = run.call_args.args[0]
        self.assertEqual(command[1], str(ROOT / "termscope"))
        self.assertEqual(command[2], "pick")
        self.assertIn("--multiplexer", command)
        self.assertEqual(command[command.index("--multiplexer") + 1], "herdr")
        self.assertEqual(command[command.index("--sort") + 1], "alpha")


if __name__ == "__main__":
    unittest.main()
