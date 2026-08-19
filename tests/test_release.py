#!/usr/bin/env python3
"""Contract tests for Release Please configuration."""

import json
import unittest
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]


class TestReleaseConfiguration(unittest.TestCase):
    def test_simple_release_config_updates_plugin_manifest(self) -> None:
        config = json.loads((ROOT / "release-please-config.json").read_text())

        self.assertEqual(
            config["packages"]["."],
            {
                "release-type": "simple",
                "package-name": "termscope",
                "version-file": "version.txt",
                "include-component-in-tag": False,
                "include-v-in-tag": True,
                "extra-files": [
                    {
                        "type": "toml",
                        "path": "herdr-plugin.toml",
                        "jsonpath": "$.version",
                    }
                ],
            },
        )

    def test_release_versions_are_aligned(self) -> None:
        version = (ROOT / "version.txt").read_text().strip()
        plugin_manifest = tomllib.loads((ROOT / "herdr-plugin.toml").read_text())
        release_manifest = json.loads(
            (ROOT / ".release-please-manifest.json").read_text()
        )

        self.assertEqual(plugin_manifest["version"], version)
        self.assertEqual(release_manifest["."], version)


if __name__ == "__main__":
    unittest.main()
