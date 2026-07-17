#!/usr/bin/env python3
"""Contract tests for the install-time Television bootstrap."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install-dependencies.sh"


class TestDependencyInstaller(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.bin_dir = Path(self.temp_dir.name) / "bin"
        self.bin_dir.mkdir()
        self.marker = Path(self.temp_dir.name) / "brew-called"
        self.env = os.environ.copy()
        self.env.update(
            {
                "PATH": f"{self.bin_dir}:/usr/bin:/bin",
                "FAKE_BIN": str(self.bin_dir),
                "BREW_MARKER": str(self.marker),
            }
        )

    def write_executable(self, name: str, content: str) -> Path:
        path = self.bin_dir / name
        path.write_text(content)
        path.chmod(0o755)
        return path

    def run_installer(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["sh", str(INSTALLER)],
            env=self.env,
            text=True,
            capture_output=True,
            check=False,
        )

    def write_brew(self, installed: bool) -> None:
        list_status = 0 if installed else 1
        self.write_executable(
            "brew",
            f"""#!/bin/sh
case "$1" in
  list) exit {list_status} ;;
  install|upgrade)
    echo "$1" > "$BREW_MARKER"
    cat > "$FAKE_BIN/tv" <<'TV'
#!/bin/sh
echo 'television 0.15.9'
TV
    chmod +x "$FAKE_BIN/tv"
    ;;
  *) exit 2 ;;
esac
""",
        )

    def test_supported_television_skips_homebrew(self) -> None:
        self.write_executable("tv", "#!/bin/sh\necho 'television 0.15.9'\n")
        self.write_executable(
            "brew", "#!/bin/sh\necho called > \"$BREW_MARKER\"\nexit 99\n"
        )

        result = self.run_installer()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.marker.exists())
        self.assertIn("already installed", result.stdout)

    def test_missing_homebrew_aborts_install(self) -> None:
        result = self.run_installer()

        self.assertEqual(result.returncode, 1)
        self.assertIn("requires Homebrew", result.stderr)

    def test_missing_television_is_installed(self) -> None:
        self.write_brew(installed=False)

        result = self.run_installer()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.marker.read_text().strip(), "install")
        self.assertIn("Television installed", result.stdout)

    def test_old_television_is_upgraded(self) -> None:
        self.write_executable("tv", "#!/bin/sh\necho 'television 0.7.1'\n")
        self.write_brew(installed=True)

        result = self.run_installer()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.marker.read_text().strip(), "upgrade")
        self.assertIn("Television installed", result.stdout)


if __name__ == "__main__":
    unittest.main()
