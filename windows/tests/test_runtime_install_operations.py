import threading
import time
import unittest

from backend.workbench.server import RuntimeInstallOperationManager


class FakeRuntime:
    def __init__(self):
        self.started = threading.Event()
        self.release = threading.Event()
        self.calls = 0

    def install_or_update_runtime(self, profile=None, *, options=None, progress=None, cancel_event=None):
        self.calls += 1
        self.started.set()
        if progress:
            progress("downloading-visioneval", "Downloading VisionEval", percent=50)
        while not self.release.wait(0.01):
            if cancel_event and cancel_event.is_set():
                raise RuntimeError("Runtime installation was cancelled.")
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

    def test_install_can_be_cancelled_and_reports_progress(self):
        runtime = FakeRuntime()
        manager = RuntimeInstallOperationManager(runtime)
        operation = manager.start(install_options={"veRuntime": "D:/VE_Runtime"})
        self.assertTrue(runtime.started.wait(1))
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline:
            status = manager.status(operation["id"])
            if status.get("percent") == 50:
                break
            time.sleep(0.01)
        self.assertEqual(status["phase"], "downloading-visioneval")
        self.assertEqual(status["percent"], 50)
        manager.cancel(operation["id"])
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            status = manager.status(operation["id"])
            if status["state"] == "cancelled":
                break
            time.sleep(0.01)
        self.assertEqual(status["state"], "cancelled")


if __name__ == "__main__":
    unittest.main()
