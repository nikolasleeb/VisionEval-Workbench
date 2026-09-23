import sys
import tempfile
import unittest
from pathlib import Path


BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from main import WorkspaceLease  # noqa: E402


class BackendLifecycleTests(unittest.TestCase):
    def test_workspace_lease_rejects_a_second_backend_and_releases_cleanly(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            with WorkspaceLease(workspace, 50101):
                with self.assertRaisesRegex(RuntimeError, "workspace is already open"):
                    with WorkspaceLease(workspace, 50102):
                        self.fail("a second backend acquired the same workspace lease")
            with WorkspaceLease(workspace, 50103):
                self.assertTrue((workspace / ".workbench" / "backend.lock").is_file())


if __name__ == "__main__":
    unittest.main()
