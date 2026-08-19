import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from backend.workbench.diagnostics import APP_ERROR_MAX_ENTRIES, DiagnosticsService
from backend.workbench.workspace import Workspace


class FakeNativeRuntime:
    adapter = "native"

    def __init__(self, job):
        self._job = job

    def list_jobs(self, include_archived=False):
        return [self._job]

    def job(self, job_id):
        if job_id != self._job["id"]:
            raise KeyError(job_id)
        return self._job

    def docker_status(self):
        return {"adapter": "native", "ready": True, "veRuntime": "installed"}


class DiagnosticsTests(unittest.TestCase):
    def test_app_errors_are_pruned_capped_and_clearable(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory) / "workspace")
            service = DiagnosticsService(workspace, FakeNativeRuntime({}), "1.0.1")
            service.error_log_path.parent.mkdir(parents=True, exist_ok=True)
            entries = [{"timestamp": "2020-01-01T00:00:00+00:00", "message": "expired"}]
            entries.extend({"timestamp": "2099-01-01T00:00:00+00:00", "message": f"error-{index}"} for index in range(APP_ERROR_MAX_ENTRIES + 20))
            service.error_log_path.write_text("".join(json.dumps(entry) + "\n" for entry in entries), encoding="utf-8")

            retained = service.recent_errors(limit=APP_ERROR_MAX_ENTRIES)
            self.assertEqual(len(retained), APP_ERROR_MAX_ENTRIES)
            self.assertNotIn("expired", {entry["message"] for entry in retained})
            self.assertEqual(len(service.error_log_path.read_text(encoding="utf-8").splitlines()), APP_ERROR_MAX_ENTRIES)

            result = service.clear_errors()
            self.assertEqual(result["cleared"], APP_ERROR_MAX_ENTRIES)
            self.assertFalse(service.error_log_path.exists())
            self.assertEqual(service.recent_errors(), [])

    def test_native_bundle_defaults_are_small_and_optional_artifacts_are_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory) / "workspace")
            job = {
                "id": "job-1",
                "state": "failed",
                "projectId": "project-1",
                "projectName": "Native project",
                "variationName": "Scenario 1",
                "modelPath": "",
            }
            run_dir = workspace.runs / job["id"]
            run_dir.mkdir(parents=True)
            (run_dir / "job.json").write_text(json.dumps(job), encoding="utf-8")
            (run_dir / "run.log").write_text("failed safely", encoding="utf-8")
            service = DiagnosticsService(workspace, FakeNativeRuntime(job), "2.0.0")

            service.record_app_error({"source": "frontend", "message": "example"})
            self.assertEqual(service.runs(), [job])
            self.assertEqual(service.recent_errors()[-1]["message"], "example")

            payload, filename = service.run_zip(job["id"])
            self.assertTrue(filename.endswith(".zip"))
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                names = set(archive.namelist())
                manifest = json.loads(archive.read("diagnostics/manifest.json"))
                self.assertEqual(manifest["runtime"]["adapter"], "native")
                self.assertEqual(manifest["runtime"]["profile"]["veRuntime"], "installed")
                self.assertFalse(manifest["options"]["includeResults"])
                self.assertFalse(manifest["options"]["includeComparisonCache"])
                self.assertIn("run/run.log", names)


if __name__ == "__main__":
    unittest.main()
