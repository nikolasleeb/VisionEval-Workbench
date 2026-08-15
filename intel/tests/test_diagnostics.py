import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from backend.workbench.diagnostics import DiagnosticsService
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
