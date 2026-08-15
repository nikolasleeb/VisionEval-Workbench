import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from backend.workbench.comparison import ComparisonScanManager
from backend.workbench.workspace import Workspace, write_json


class FakeComparisonService:
    def __init__(self, workspace, records):
        self.workspace = workspace
        self.records = records
        self.runtime = type("Runtime", (), {"adapter": "docker"})()

    def scan_request(self, reference_id, comparison_ids, year, filter_field="", filter_values=None):
        return {
            "year": year, "filterField": filter_field, "filterValues": filter_values or [],
            "records": self.records, "variables": [], "county": {"azone": {}, "bzone": {}},
        }


class ComparisonScanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Workspace(Path(self.temp.name) / "workspace")
        self.records = []
        for index in range(2):
            root = self.workspace.models / f"result-{index}" / "results" / "Datastore"
            (root / "2045" / "Azone").mkdir(parents=True)
            (root / "DatastoreListing.Rda").write_bytes(b"listing")
            (root / "2045" / "Azone" / "Value.Rda").write_bytes(bytes([index]))
            self.records.append({"id": f"result-{index}", "path": str(root), "registrationFingerprint": "one"})
        self.manager = ComparisonScanManager(FakeComparisonService(self.workspace, self.records))

    def tearDown(self):
        self.temp.cleanup()

    def test_cache_key_changes_with_datastore_or_registration(self):
        request = self.manager.service.scan_request("result-0", ["result-1"], "2045")
        first = self.manager._cache_key(request)
        (Path(self.records[1]["path"]) / "2045" / "Azone" / "Value.Rda").write_bytes(b"changed")
        second = self.manager._cache_key(request)
        self.assertNotEqual(first, second)
        request["records"][1]["registrationFingerprint"] = "two"
        self.assertNotEqual(second, self.manager._cache_key(request))

    def test_cached_scan_is_reconnectable_and_immediate(self):
        request = self.manager.service.scan_request("result-0", ["result-1"], "2045")
        cache_key = self.manager._cache_key(request)
        expected = {"year": "2045", "scanned": 0, "changedVariables": 0, "results": [], "skipped": []}
        write_json(self.manager.root / "cache" / f"{cache_key}.json", expected)
        started = self.manager.start("result-0", ["result-1"], "2045")
        self.assertEqual(started["state"], "succeeded")
        self.assertTrue(started["cached"])
        self.assertEqual(self.manager.status(started["id"])["result"], expected)

    def test_manager_runs_batch_command_and_reports_progress(self):
        expected = {"year": "2045", "scanned": 1, "changedVariables": 0, "results": [], "skipped": [], "filterField": "", "filterValues": []}
        self.manager.service.scan_request = lambda *args, **kwargs: {
            "year":"2045", "filterField":"", "filterValues":[], "records":self.records,
            "variables":[{"table":"Azone","name":"Value","years":["2045"]}],
        }
        def command(request_path, output_path, progress_path, container_name):
            script = "from pathlib import Path; import json; Path(%r).write_text(json.dumps(%r)); Path(%r).write_text(json.dumps({'completed':1,'total':1,'table':'Azone','variable':'Value'}))" % (str(output_path), expected, str(progress_path))
            return [sys.executable, "-c", script]
        self.manager.service.scan_command = command
        started = self.manager.start("result-0", ["result-1"], "2045")
        deadline = __import__("time").monotonic() + 3
        status = started
        while status["state"] in {"waiting", "running"} and __import__("time").monotonic() < deadline:
            __import__("time").sleep(.01); status = self.manager.status(started["id"])
        self.assertEqual(status["state"], "succeeded", status.get("message"))
        self.assertEqual(status["phase"], "complete")
        self.assertEqual(status["progress"]["total"], 1)
        self.assertEqual(status["result"], expected)

    def test_native_scan_uses_package_free_workspace_scanner(self):
        expected = {"year": "2045", "scanned": 1, "changedVariables": 1, "results": [{"table": "Azone", "variable": "Value"}], "skipped": [], "filterField": "Azone", "filterValues": ["51001"]}
        service = self.manager.service
        service.runtime.adapter = "native"
        service.scan_request = lambda *args, **kwargs: {
            "year": "2045", "filterField": "Azone", "filterValues": ["51001"], "records": self.records,
            "variables": [{"table": "Azone", "name": "Value", "years": ["2045"]}],
        }
        calls = []
        service.scan_command = lambda *args, **kwargs: self.fail("native scans must not invoke comparison_scan.R")
        def changes(reference_id, comparison_ids, year, filter_field, filter_values, progress, cancelled):
            calls.append((reference_id, comparison_ids, year, filter_field, filter_values))
            progress(1, 1, "Azone", "Value")
            self.assertFalse(cancelled())
            return expected
        service.changes = changes

        started = self.manager.start("result-0", ["result-1"], "2045", "Azone", ["51001"])
        deadline = __import__("time").monotonic() + 3
        status = started
        while status["state"] in {"waiting", "running"} and __import__("time").monotonic() < deadline:
            __import__("time").sleep(.01); status = self.manager.status(started["id"])
        self.assertEqual(status["state"], "succeeded", status.get("message"))
        self.assertEqual(status["result"], expected)
        self.assertEqual(calls, [("result-0", ["result-1"], "2045", "Azone", ["51001"])])
        self.assertEqual(status["phase"], "complete")
        self.assertEqual(status["progress"]["completed"], 1)
        self.assertEqual(status["progress"]["phase"], "finalizing")
        self.assertEqual(status["progress"]["completed"], 1)

    @unittest.skipUnless(shutil.which("Rscript"), "Rscript is required for the batch-scan integration test")
    def test_r_batch_scan_loads_each_datastore_in_one_process(self):
        jsonlite = subprocess.run([shutil.which("Rscript"), "-e", "quit(status=if(requireNamespace('jsonlite', quietly=TRUE)) 0 else 1)"], capture_output=True)
        if jsonlite.returncode:
            self.skipTest("R jsonlite is required for the batch-scan integration test")
        for index, values in enumerate(([1, 2], [1, 3])):
            root = Path(self.records[index]["path"])
            command = (
                f"root <- {json.dumps(str(root))}; "
                "dir.create(file.path(root,'2045','Azone'), recursive=TRUE, showWarnings=FALSE); "
                "x <- c('a','b'); save(x,file=file.path(root,'2045','Azone','Azone.Rda')); "
                f"x <- c({','.join(str(value) for value in values)}); save(x,file=file.path(root,'2045','Azone','Value.Rda'))"
            )
            subprocess.run([shutil.which("Rscript"), "-e", command], check=True, capture_output=True, text=True)
        request = {
            "year": "2045", "filterField": "", "filterValues": [],
            "records": [{**record, "label": record["id"], "county": {"azone": {}, "bzone": {}}} for record in self.records],
            "variables": [{"table": "Azone", "name": "Value", "units": "", "description": ""}],
        }
        directory = self.workspace.exchange / "scan-integration"
        directory.mkdir()
        request_path, output_path, progress_path = directory / "request.json", directory / "result.json", directory / "progress.json"
        write_json(request_path, request)
        helper = Path(__file__).parents[1] / "backend" / "comparison_scan.R"
        scan = subprocess.run([shutil.which("Rscript"), str(helper), str(request_path), str(output_path), str(progress_path)], capture_output=True, text=True)
        self.assertEqual(scan.returncode, 0, scan.stderr or scan.stdout)
        result = json.loads(output_path.read_text())
        self.assertEqual(result["changedVariables"], 1)
        self.assertEqual(result["results"][0]["changedRows"], 1)
        self.assertAlmostEqual(result["results"][0]["pairStats"][0]["totalPercentChange"], 33.3333333)

    @unittest.skipUnless(os.environ.get("RUN_DOCKER_TESTS") == "1", "Set RUN_DOCKER_TESTS=1 for the VisionEval image smoke test")
    def test_docker_image_runs_batch_scanner(self):
        if not shutil.which("docker"):
            self.skipTest("Docker is not installed")
        for index, values in enumerate(([1, 2], [1, 3])):
            root = Path(self.records[index]["path"])
            command = (
                f"root <- {json.dumps(str(root))}; "
                "dir.create(file.path(root,'2045','Azone'), recursive=TRUE, showWarnings=FALSE); "
                "x <- c('a','b'); save(x,file=file.path(root,'2045','Azone','Azone.Rda')); "
                f"x <- c({','.join(str(value) for value in values)}); save(x,file=file.path(root,'2045','Azone','Value.Rda'))"
            )
            subprocess.run([shutil.which("Rscript"), "-e", command], check=True, capture_output=True, text=True)
        helper = self.workspace.exchange / "comparison_scan.R"
        shutil.copy2(Path(__file__).parents[1] / "backend" / "comparison_scan.R", helper)
        request = {
            "year": "2045", "filterField": "", "filterValues": [],
            "records": [{**record, "path": "/workspace/" + Path(record["path"]).relative_to(self.workspace.root).as_posix(), "label": record["id"], "county": {"azone": {}, "bzone": {}}} for record in self.records],
            "variables": [{"table": "Azone", "name": "Value", "units": "", "description": ""}],
        }
        request_path = self.workspace.exchange / "docker-request.json"
        output_path = self.workspace.exchange / "docker-result.json"
        progress_path = self.workspace.exchange / "docker-progress.json"
        write_json(request_path, request)
        scan = subprocess.run([
            shutil.which("docker"), "run", "--rm", "--platform", "linux/amd64", "--entrypoint", "Rscript",
            "-v", f"{self.workspace.root}:/workspace", "local/visioneval:ve-40-rc6-household-id-ordering-amd64",
            "/workspace/exchange/comparison_scan.R", "/workspace/exchange/docker-request.json",
            "/workspace/exchange/docker-result.json", "/workspace/exchange/docker-progress.json",
        ], capture_output=True, text=True)
        self.assertEqual(scan.returncode, 0, scan.stderr or scan.stdout)
        result = json.loads(output_path.read_text())
        self.assertEqual(result["changedVariables"], 1)


if __name__ == "__main__":
    unittest.main()
