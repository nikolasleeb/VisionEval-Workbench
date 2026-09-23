import json
import shutil
import subprocess
import tempfile
import time
import unittest
import zipfile
from pathlib import Path

from backend.workbench.hypercube_analysis import HypercubeAnalysisOperationManager, HypercubeAnalysisService, HypercubeCaseExportManager, HypercubeDiscoveryManager
from backend.workbench.workspace import WorkspaceError


class FakeWorkspace:
    def __init__(self, root):
        self.root = Path(root)
        self.models = self.root / "Models"; self.models.mkdir()
        self.runs = self.root / "Runs"; self.runs.mkdir()
        self.exchange = self.root / "Exchange"; self.exchange.mkdir()
        self.project_data = {
            "id": "project", "name": "Hyper1", "projectType": "hypercube",
            "datastoreIds": ["baseline", "case-1", "case-2"],
            "hypercubes": [{
                "id": "cube", "scenarioIds": ["variation-1", "variation-2"],
                "axes": [
                    {"id": "axis-a", "column": "A", "values": ["10", "20"]},
                    {"id": "axis-b", "column": "B", "values": ["5"]},
                ],
            }],
            "variations": [
                {"id": "variation-1", "name": "Case 1", "hypercube": {"caseIndex": 1, "values": [{"axisId": "axis-a", "column": "A", "value": "10"}, {"axisId": "axis-b", "column": "B", "value": "5"}]}},
                {"id": "variation-2", "name": "Case 2", "hypercube": {"caseIndex": 2, "values": [{"axisId": "axis-a", "column": "A", "value": "20"}, {"axisId": "axis-b", "column": "B", "value": "5"}]}},
            ],
        }
        self.catalog = [
            {"id": "baseline", "variationId": "baseline", "role": "baseline", "verification": "verified", "runtimeImageDigest": "digest", "templateFingerprint": "template", "executionFingerprint": "execution-baseline"},
            {"id": "case-1", "variationId": "variation-1", "role": "scenario", "verification": "verified", "runtimeImageDigest": "digest", "templateFingerprint": "template", "executionFingerprint": "execution-1"},
            {"id": "case-2", "variationId": "variation-2", "role": "scenario", "verification": "verified", "runtimeImageDigest": "digest", "templateFingerprint": "template", "executionFingerprint": "execution-2"},
        ]

    def project(self, project_id):
        return self.root, self.project_data

    def display_catalog(self, *_args):
        return {"datastores": self.catalog}

    def active_run_records(self):
        return []

    def within(self, path, root=None, must_exist=True):
        path, root = Path(path).resolve(), Path(root or self.root).resolve()
        path.relative_to(root)
        return path


class FakeCache:
    def report(self):
        return {"bytes": 12, "entries": 1, "limitBytes": 5_000_000_000}


class FakeComparison:
    def __init__(self, workspace):
        self.workspace = workspace; self.cache = FakeCache(); self.runtime = FakeRuntime()
        self.records = {}
        values = {"baseline": [10, 20], "case-1": [11, 22], "case-2": [12, 24]}
        for record_id, column in values.items():
            results = workspace.models / record_id / "results"
            (results / "Datastore").mkdir(parents=True)
            (results / "Datastore" / "data.bin").write_bytes(b"1234")
            (results / "output").mkdir(); (results / "output" / "table.csv").write_bytes(b"123456")
            (workspace.models / record_id / "inputs").mkdir()
            (workspace.models / record_id / "inputs" / "resolved.csv").write_text("id,value\n1,2\n", encoding="utf-8")
            self.records[record_id] = {"id": record_id, "label": record_id, "path": str(results / "Datastore"), "column": column, "verification": "verified", "runtimeImage": "image", "runtimeImageDigest": "digest", "templateFingerprint": "template", "inputStateFingerprint": f"inputs-{record_id}"}

    def _record(self, record_id): return self.records[record_id]
    def _metadata(self, _record): return {"Bzone/Population": {"units": "persons", "description": "Population count"}}
    def _keyed(self, root, _year, _table, _variable):
        record = next(item for item in self.records.values() if Path(item["path"]) == Path(root))
        return {"keyName": "Bzone", "order": ["1", "2"], "values": {"1": record["column"][0], "2": record["column"][1]}}
    def _matching_location_keys(self, _record, _root, _year, _table, keys, _field, values): return set(keys) if "all" in values else {"1"}
    def _percent_change(self, left, right): return None if left in {None, 0} or right is None else (right - left) / abs(left) * 100
    def variables(self, _ids): return [{"table": "Bzone", "name": "Population", "years": ["2045"], "units": "persons"}]


class FakeRuntime:
    adapter = "native"

    def export_model_results(self, model_path, _log_path, cancelled=None):
        if cancelled and cancelled():
            raise WorkspaceError("Hypercube case export cancelled")
        output = Path(model_path) / "results" / "output"
        output.mkdir(parents=True, exist_ok=True)
        (output / "Bzone.csv").write_text("Bzone,Population\n1,10\n", encoding="utf-8")


class HypercubeAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = FakeWorkspace(self.temp.name)
        self.service = HypercubeAnalysisService(self.workspace, FakeComparison(self.workspace))

    def tearDown(self): self.temp.cleanup()

    def test_inventory_and_matrix_cover_every_case(self):
        inventory = self.service.inventory("project")
        self.assertEqual(inventory["completedCases"], 2)
        result = self.service.matrix({"projectId": "project", "year": "2045", "table": "Bzone", "variable": "Population", "metric": "percent_change", "aggregation": "auto"})
        self.assertEqual([cell["caseIndex"] for cell in result["cells"]], [1, 2])
        self.assertAlmostEqual(result["cells"][0]["percentChange"], 10)
        self.assertEqual(result["cells"][0]["aggregation"], "sum")

    def test_pair_comparison_uses_selected_cases(self):
        result = self.service.matrix({"projectId": "project", "year": "2045", "table": "Bzone", "variable": "Population", "metric": "absolute_change", "pairCaseIds": ["variation-1", "variation-2"]})
        self.assertEqual(result["pairComparison"]["value"], 3)

    def test_response_matrix_result_is_reused_by_a_new_manager(self):
        payload = {"projectId": "project", "year": "2045", "table": "Bzone", "variable": "Population", "metric": "percent_change", "aggregation": "sum"}
        first_manager = HypercubeAnalysisOperationManager(self.service)
        first = first_manager.start(payload)
        for _ in range(100):
            first = first_manager.status(first["id"])
            if first["state"] not in {"waiting", "running"}:
                break
            time.sleep(.01)
        self.assertEqual(first["state"], "succeeded")
        second_manager = HypercubeAnalysisOperationManager(self.service)
        self.service.matrix = lambda *_args, **_kwargs: self.fail("A cached matrix must not be recalculated")
        second = second_manager.start(payload)
        self.assertEqual(second["state"], "succeeded")
        self.assertTrue(second["cached"])
        self.assertEqual(len(second["result"]["cells"]), 2)

    def test_cleanup_removes_only_output_trees(self):
        before = self.service.storage("project")
        self.assertEqual(before["exportDirectories"], 3)
        result = self.service.cleanup_exports("project")
        self.assertEqual(result["removedDirectories"], 3)
        self.assertEqual(result["removedBytes"], 18)
        self.assertEqual(result["datastoreBytes"], 12)
        self.assertTrue(all((Path(item["path"]) / "data.bin").is_file() for item in self.service.comparison.records.values()))

    def test_discovery_is_a_service_contract_and_completed_work_is_reused(self):
        self.assertTrue(callable(self.service.discover))
        manager = HypercubeDiscoveryManager(self.service)
        calls = []
        self.service.discover = lambda payload, progress, cancelled: calls.append(payload) or {"results": [], "projectId": "project"}
        first = manager.start({"projectId": "project", "year": "2045"})
        for _ in range(100):
            status = manager.status(first["id"])
            if status["state"] not in {"waiting", "running"}:
                break
            time.sleep(.01)
        self.assertEqual(status["state"], "succeeded")
        self.assertEqual(calls[0]["aggregation"], "median")
        second = manager.start({"projectId": "project", "year": "2045", "aggregation": "median"})
        self.assertEqual(second["id"], first["id"])
        self.assertTrue(second["cached"])
        self.assertEqual(len(calls), 1)
        restored = manager.cached({"projectId": "project", "year": "2045"})
        self.assertEqual(restored["state"], "succeeded")
        self.assertTrue(restored["cached"])

    def test_discovery_cache_ignores_response_matrix_fields(self):
        manager = HypercubeDiscoveryManager(self.service)
        canonical = manager._fingerprint({"projectId": "project", "year": "2045", "aggregation": "median"})
        coupled = manager._fingerprint({
            "projectId": "project", "year": "2045", "aggregation": "median",
            "table": "Bzone", "variable": "Population", "metric": "percent_change",
            "filterField": "County", "filterValues": ["one"], "caseIds": ["variation-1"],
        })
        missing_aggregation = manager._fingerprint({"projectId": "project", "year": "2045"})
        self.assertEqual(canonical, coupled)
        self.assertEqual(canonical, missing_aggregation)

    def test_discovery_background_failure_is_recorded_for_diagnostics(self):
        errors = []
        manager = HypercubeDiscoveryManager(self.service, errors.append)
        self.service.discover = lambda *_args, **_kwargs: (_ for _ in ()).throw(WorkspaceError("discovery exploded"))
        operation = manager.start({"projectId": "project", "year": "2045"})
        for _ in range(100):
            status = manager.status(operation["id"])
            if status["state"] not in {"waiting", "running"}:
                break
            time.sleep(.01)
        self.assertEqual(status["state"], "failed")
        self.assertEqual(errors[0]["source"], "hypercube-discovery")
        self.assertEqual(errors[0]["message"], "discovery exploded")
        self.assertEqual(errors[0]["context"]["operationId"], operation["id"])
        self.assertEqual(errors[0]["context"]["projectId"], "project")

    def test_discovery_decorates_legacy_results_with_scenario_rankings(self):
        result = self.service._decorate_discovery({"results": [{
            "table": "Bzone", "variable": "Population", "geographicSpread": 100,
            "cells": [
                {"variationId": "variation-1", "referenceValue": 100, "scenarioValue": 110, "absoluteChange": 10, "percentChange": 10},
                {"variationId": "variation-2", "referenceValue": 100, "scenarioValue": 95, "absoluteChange": -5, "percentChange": -5},
            ],
        }]}, self.service.inventory("project"))
        self.assertNotIn("geographicSpread", result["results"][0])
        first = result["scenarioSummaries"][0]
        self.assertEqual(first["typicalAbsoluteChange"], 10)
        self.assertEqual(first["changedOutputs"], 1)
        self.assertEqual(first["positiveOutputs"], 1)
        self.assertEqual(first["values"][0]["column"], "A")

    def test_scenario_rankings_include_unchanged_eligible_outputs(self):
        result = self.service._decorate_discovery({
            "results": [{"table": "Bzone", "variable": "Changed", "cells": []}],
            "scenarioOutputs": [
                {"table": "Bzone", "variable": "Changed", "cells": [{"variationId": "variation-1", "referenceValue": 100, "scenarioValue": 110, "percentChange": 10}]},
                {"table": "Bzone", "variable": "Stable", "cells": [{"variationId": "variation-1", "referenceValue": 50, "scenarioValue": 50, "percentChange": 0}]},
            ],
        }, self.service.inventory("project"))
        first = result["scenarioSummaries"][0]
        self.assertEqual(first["totalOutputs"], 2)
        self.assertEqual(first["eligibleOutputs"], 2)
        self.assertEqual(first["changedOutputs"], 1)
        self.assertEqual(first["typicalAbsoluteChange"], 5)

    def test_discovery_helper_skips_key_value_length_mismatches(self):
        helper = (Path(__file__).parents[1] / "backend" / "hypercube_summary.R").read_text(encoding="utf-8")
        self.assertIn("length(value)!=length(keys)", helper)
        self.assertIn("if(!is.null(left_map)&&!is.null(right_map))", helper)

    @unittest.skipUnless(shutil.which("Rscript"), "Rscript is not installed")
    def test_discovery_r_helper_survives_mismatched_key_and_value_lengths(self):
        helper = Path(__file__).parents[1] / "backend" / "hypercube_summary.R"
        root = Path(self.temp.name)
        baseline = root / "r-baseline" / "2045" / "Azone"
        case = root / "r-case" / "2045" / "Azone"
        baseline.mkdir(parents=True); case.mkdir(parents=True)
        setup = (
            f"key<-c('1','2');save(key,file={str(baseline / 'Azone.Rda')!r});"
            f"key<-c('1','2');save(key,file={str(case / 'Azone.Rda')!r});"
            f"value<-10;save(value,file={str(baseline / 'Metric.Rda')!r});"
            f"value<-12;save(value,file={str(case / 'Metric.Rda')!r})"
        )
        subprocess.run(["Rscript", "-e", setup], check=True, capture_output=True, text=True)
        request = root / "request.json"; output = root / "output.json"; progress = root / "progress.json"
        request.write_text(json.dumps({
            "projectId": "project", "year": "2045", "sourceFingerprint": "source", "datastoreFingerprint": "data",
            "baseline": {"path": str(root / "r-baseline")},
            "cases": [{"id": "case", "name": "Case", "path": str(root / "r-case")}],
            "tables": [{"table": "Azone", "key": "Azone", "variables": [{"name": "Metric", "units": "", "description": "", "aggregation": "mean"}]}],
        }), encoding="utf-8")
        completed = subprocess.run(["Rscript", str(helper), str(request), str(output), str(progress)], capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(result["results"][0]["availableCases"], 1)
        self.assertIsNone(result["results"][0]["cells"][0]["typicalRowChange"])

    def test_case_export_contains_inputs_outputs_and_manifest_but_no_datastore(self):
        manager = HypercubeCaseExportManager(self.service)
        option = manager.options("project")["items"][1]
        operation = manager.start({"projectId": "project", "itemId": option["id"], "datastoreId": option["datastoreId"], "executionFingerprint": option["executionFingerprint"]})
        for _ in range(100):
            status = manager.status(operation["id"])
            if status["state"] not in {"waiting", "running", "cancelling"}:
                break
            time.sleep(.01)
        self.assertEqual(status["state"], "succeeded", status.get("message"))
        artifact, filename = manager.artifact(operation["id"])
        self.assertTrue(filename.endswith(".zip"))
        with zipfile.ZipFile(artifact) as archive:
            names = set(archive.namelist())
        self.assertIn("manifest.json", names)
        self.assertIn("inputs/resolved.csv", names)
        self.assertIn("outputs/Bzone.csv", names)
        self.assertFalse(any("Datastore" in name for name in names))
        self.assertFalse(manager._staging_path(operation["id"]).exists())

    def test_case_export_rejects_a_stale_result_snapshot(self):
        manager = HypercubeCaseExportManager(self.service)
        with self.assertRaisesRegex(WorkspaceError, "changed before export"):
            manager.start({"projectId": "project", "itemId": "variation-1", "datastoreId": "case-1", "executionFingerprint": "stale"})


if __name__ == "__main__":
    unittest.main()
