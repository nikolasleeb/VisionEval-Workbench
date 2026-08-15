from __future__ import annotations

from pathlib import Path
import unittest


class BackendMainTests(unittest.TestCase):
    def test_windows_parent_watcher_does_not_use_os_kill(self) -> None:
        source = (Path(__file__).parents[1] / "backend" / "main.py").read_text(
            encoding="utf-8"
        )
        windows_branch = source.split('if sys.platform == "win32":', 1)[1].split(
            "while True:", 1
        )[0]

        self.assertIn("WaitForSingleObject", windows_branch)
        self.assertNotIn("os.kill(parent_pid, 0)\n", windows_branch)


if __name__ == "__main__":
    unittest.main()
