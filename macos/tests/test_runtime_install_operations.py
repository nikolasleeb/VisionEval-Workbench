import threading
import time
import unittest

from backend.workbench.server import RuntimeInstallOperationManager


class FakeRuntime:
    def __init__(self):
        self.started = threading.Event()
        self.release = threading.Event()
        self.calls = 0

    def install_or_update_runtime(self):
        self.calls += 1
        self.started.set()
        self.release.wait(2)
        return {"image": "local/visioneval:1.0.0-arm64", "verified": True}


class RuntimeInstallOperationTests(unittest.TestCase):
    def test_long_install_runs_in_background_and_reuses_active_operation(self):
        runtime = FakeRuntime()
        manager = RuntimeInstallOperationManager(runtime)

        first = manager.start()
        self.assertTrue(runtime.started.wait(1))
        second = manager.start()

        self.assertEqual(first["id"], second["id"])
        self.assertIn(second["state"], {"waiting", "running"})
        self.assertEqual(runtime.calls, 1)

        runtime.release.set()
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            status = manager.status(first["id"])
            if status["state"] == "succeeded":
                break
            time.sleep(0.01)

        self.assertEqual(status["state"], "succeeded")
        self.assertTrue(status["result"]["verified"])


if __name__ == "__main__":
    unittest.main()
