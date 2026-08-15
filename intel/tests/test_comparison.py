import tempfile
import unittest
import time
import zipfile
from pathlib import Path
from unittest.mock import patch

from backend.workbench.comparison import ComparisonOperationManager, ComparisonService
from backend.workbench.excel_exports import ComparisonExportManager, WorkbookWriter
from backend.workbench.workspace import Workspace, WorkspaceError


class FakeComparison(ComparisonService):
    def __init__(self, root):
        workspace = Workspace(root)
        super().__init__(workspace, "unused", Path(root) / "reader.R")
        self.records = {
            "reference": {"id": "reference", "label": "Reference", "path": str(Path(root) / "reference")},
            "comparison": {"id": "comparison", "label": "Comparison", "path": str(Path(root) / "comparison")},
        }
        self.columns = {}

    def _record(self, datastore_id):
        return self.records[datastore_id]

    def _column(self, root, year, table, variable):
        return self.columns.get((Path(root).name, year, table, variable), [])

    def _metadata(self, record):
        return {}


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.service = FakeComparison(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_rows_align_by_stable_key_not_position(self):
        self.service.columns.update({
            ("reference", "2045", "Household", "HhId"): ["a", "b"],
            ("reference", "2045", "Household", "Dvmt"): [10, 20],
            ("comparison", "2045", "Household", "HhId"): ["b", "a"],
            ("comparison", "2045", "Household", "Dvmt"): [25, 10],
        })
        result = self.service.compare("reference", ["comparison"], "Household", "Dvmt", "2045", mode="records")
        self.assertEqual([row["id"] for row in result["rows"]], ["a", "b"])
        self.assertEqual(result["rows"][0]["deltas"], [0.0])
        self.assertEqual(result["rows"][1]["deltas"], [5.0])
        self.assertEqual(result["changedRows"], 1)

    def test_change_density_counts_changed_assignable_variables(self):
        variables = [
            {"table": "Bzone", "name": "Pop", "type": "double", "years": ["2045"]},
            {"table": "Bzone", "name": "Income", "type": "double", "years": ["2045"]},
        ]
        aggregates = {
            ("reference", "Pop"): {"values": {"001": {"sum": 10}, "002": {"sum": 5}}, "assignment": "direct"},
            ("comparison", "Pop"): {"values": {"001": {"sum": 12}, "002": {"sum": 5}}, "assignment": "direct"},
            ("reference", "Income"): {"values": {"001": {"sum": 7}}, "assignment": "direct"},
            ("comparison", "Income"): {"values": {"001": {"sum": 7}}, "assignment": "direct"},
        }
        def aggregate(record, year, table, variable, geography, cancelled):
            return {**aggregates[(record["id"], variable)], "numericRows": 2, "matchedRows": 2, "unmatchedRows": 0}
        with patch.object(self.service, "variables", return_value=variables), \
             patch.object(self.service, "_aggregate_map_record", side_effect=aggregate), \
             patch.object(self.service, "_map_geography", return_value={"bzone": {"001": "001", "002": "002"}, "azone": {}, "names": {"001": "One", "002": "Two"}}):
            result = self.service.change_density("reference", "comparison", "2045", "bzone")
        rows = {row["geographyId"]: row for row in result["geographyRows"]}
        self.assertEqual(rows["001"]["changedVariableCount"], 1)
        self.assertEqual(rows["001"]["scannedVariableCount"], 2)
        self.assertEqual(rows["002"]["changedVariableCount"], 0)
        self.assertEqual(result["operationKind"], "change-density")
        self.assertNotIn("path", result["reference"])

    def test_synthetic_microdata_defaults_to_independent_aggregate_summaries(self):
        self.service.columns.update({
            ("reference", "2045", "Household", "HhId"): ["a", "b"],
            ("reference", "2045", "Household", "Dvmt"): [10, 20],
            ("comparison", "2045", "Household", "HhId"): ["x", "y", "z"],
            ("comparison", "2045", "Household", "Dvmt"): [5, 15, 40],
        })
        result = self.service.compare("reference", ["comparison"], "Household", "Dvmt", "2045")
        self.assertEqual(result["mode"], "aggregate")
        self.assertEqual(result["identitySemantics"], "run_local_synthetic")
        self.assertEqual(result["referenceSummary"]["recordCount"], 2)
        self.assertEqual(result["comparisonSummaries"][0]["recordCount"], 3)
        self.assertEqual(result["aggregateChanges"][0]["measures"]["sum"]["change"], 30)
        self.assertAlmostEqual(result["aggregateChanges"][0]["measures"]["mean"]["percentChange"], 100 / 3)
        self.assertEqual(result["rows"], [])

        headers, rows, delta_columns = WorkbookWriter._comparison_table(result)
        self.assertEqual(headers[:2], ["Measure", "Reference"])
        self.assertIn("Change Comparison", headers)
        self.assertIn(headers.index("Change Comparison"), delta_columns)
        exported = {row[0]: row for row in rows}
        self.assertEqual(exported["recordCount"][1:4], [2, 3, 1])
        self.assertEqual(exported["sum"][1:4], [30, 60, 30])

    def test_unknown_multirow_table_is_rejected(self):
        self.service.columns[("reference", "2045", "Unknown", "Value")] = [1, 2]
        self.service.columns[("comparison", "2045", "Unknown", "Value")] = [1, 2]
        with self.assertRaises(WorkspaceError):
            self.service.compare("reference", ["comparison"], "Unknown", "Value", "2045")

    def test_categorical_statistics_and_selected_year(self):
        self.service.columns.update({
            ("reference", "2035", "Azone", "Azone"): ["x", "y"],
            ("reference", "2035", "Azone", "LocType"): ["Urban", "Rural"],
            ("comparison", "2035", "Azone", "Azone"): ["x", "y"],
            ("comparison", "2035", "Azone", "LocType"): ["Urban", "Town"],
        })
        result = self.service.compare("reference", ["comparison"], "Azone", "LocType", "2035")
        self.assertEqual(result["comparisonSummaries"][0]["kind"], "categorical")
        self.assertEqual(result["changedRows"], 1)

    def test_total_percent_change_and_original_sort(self):
        self.service.columns.update({
            ("reference", "2045", "Azone", "Azone"): ["b", "a"],
            ("reference", "2045", "Azone", "Value"): [10, 30],
            ("comparison", "2045", "Azone", "Azone"): ["a", "b"],
            ("comparison", "2045", "Azone", "Value"): [45, 15],
        })
        original = self.service.compare("reference", ["comparison"], "Azone", "Value", "2045", sort_direction="original")
        ascending = self.service.compare("reference", ["comparison"], "Azone", "Value", "2045", sort_column="reference", sort_direction="asc")
        self.assertEqual([row["id"] for row in original["rows"]], ["b", "a"])
        self.assertEqual([row["id"] for row in ascending["rows"]], ["b", "a"])
        self.assertAlmostEqual(original["stats"][0]["totalPercentChange"], 50.0)

    def test_percent_changes_quartiles_and_matched_row_total(self):
        self.service.columns.update({
            ("reference", "2045", "Azone", "Azone"): ["positive", "negative", "zero", "both-zero", "missing"],
            ("reference", "2045", "Azone", "Value"): [10, -10, 0, 0, 50],
            ("comparison", "2045", "Azone", "Azone"): ["positive", "negative", "zero", "both-zero"],
            ("comparison", "2045", "Azone", "Value"): [15, -5, 4, 0],
        })
        result = self.service.compare("reference", ["comparison"], "Azone", "Value", "2045")
        rows = {row["id"]: row for row in result["rows"]}
        self.assertEqual(rows["positive"]["percentChanges"], [50.0])
        self.assertEqual(rows["negative"]["percentChanges"], [50.0])
        self.assertEqual(rows["both-zero"]["percentChanges"], [0.0])
        self.assertIsNone(rows["zero"]["percentChanges"][0])
        self.assertIsNone(rows["missing"]["percentChanges"][0])
        stats = result["stats"][0]
        self.assertEqual(stats["matchedRows"], 4)
        self.assertEqual(stats["unmatchedRows"], 1)
        self.assertEqual(stats["reference"]["q1"], -2.5)
        self.assertEqual(stats["reference"]["median"], 0.0)
        self.assertEqual(stats["reference"]["q3"], 2.5)

    def test_snapshot_sort_reuses_token_and_keeps_undefined_percentages_last(self):
        self.service.columns.update({
            ("reference", "2045", "Azone", "Azone"): ["a", "b", "c"],
            ("reference", "2045", "Azone", "Value"): [10, 0, 20],
            ("comparison", "2045", "Azone", "Azone"): ["a", "b", "c"],
            ("comparison", "2045", "Azone", "Value"): [12, 4, 10],
        })
        initial = self.service.compare("reference", ["comparison"], "Azone", "Value", "2045")
        token = initial["comparisonToken"]
        ascending = self.service.comparison_snapshot_page(token, False, 100, 0, "percent:0", "asc")
        descending = self.service.comparison_snapshot_page(token, False, 100, 0, "percent:0", "desc")
        original = self.service.comparison_snapshot_page(token, False, 100, 0, "id", "original")
        self.assertEqual([row["id"] for row in ascending["rows"]], ["c", "a", "b"])
        self.assertEqual([row["id"] for row in descending["rows"]], ["a", "c", "b"])
        self.assertEqual([row["id"] for row in original["rows"]], ["a", "b", "c"])
        self.assertEqual(ascending["comparisonToken"], token)

    def test_find_all_changes_isolates_cache_variable_failure(self):
        variables = [
            {"table": "Marea", "name": "Good", "years": ["2045"], "units": "", "description": ""},
            {"table": "Marea", "name": "OthSpd", "years": ["2045"], "units": "MI/HR", "description": ""},
        ]
        self.service.variables = lambda datastore_ids: variables

        class PartialCache:
            def ensure(self, root, year, table, names):
                if len(names) > 1:
                    raise WorkspaceError("Batch contains a non-row-aligned variable")
                if names == ["OthSpd"]:
                    raise WorkspaceError("Marea/OthSpd cannot be aligned safely: 1 values for 2 Marea keys")
                return {"cacheHit": False}

        self.service.cache = PartialCache()
        self.service.compare = lambda *args, **kwargs: {
            "changedRows": 1,
            "totalRows": 2,
            "stats": [{"label": "Comparison"}],
        }

        progress_updates = []
        result = self.service.changes(
            "reference", ["comparison"], "2045",
            progress=lambda done, total, table, variable, **details: progress_updates.append({"done": done, "total": total, "table": table, "variable": variable, **details}),
        )

        self.assertEqual(result["changedVariables"], 1)
        self.assertEqual(result["results"][0]["variable"], "Good")
        self.assertEqual(result["skipped"], [{
            "table": "Marea",
            "variable": "OthSpd",
            "reason": "Marea/OthSpd cannot be aligned safely: 1 values for 2 Marea keys",
        }])
        cache_updates = [item for item in progress_updates if item.get("phase") == "preparing_cache"]
        scan_updates = [item for item in progress_updates if item.get("phase") == "scanning"]
        self.assertTrue(cache_updates)
        self.assertEqual(cache_updates[0]["done"], 0)
        self.assertEqual(cache_updates[-1]["done"], cache_updates[-1]["total"])
        self.assertEqual(cache_updates[-1]["cacheMisses"], 2)
        self.assertTrue(scan_updates)

    def test_find_all_changes_reports_total_percent_change(self):
        self.service.variables = lambda datastore_ids: [{
            "table": "Azone", "name": "Value", "years": ["2045"], "units": "PRSN", "description": "Test value",
        }]
        self.service.columns.update({
            ("reference", "2045", "Azone", "Azone"): ["a", "b"],
            ("reference", "2045", "Azone", "Value"): [10, 30],
            ("comparison", "2045", "Azone", "Azone"): ["a", "b"],
            ("comparison", "2045", "Azone", "Value"): [15, 45],
        })

        result = self.service.changes("reference", ["comparison"], "2045")

        self.assertEqual(result["changedVariables"], 1)
        self.assertAlmostEqual(result["results"][0]["totalPercentChanges"][0]["value"], 50.0)
        self.assertAlmostEqual(result["results"][0]["pairStats"][0]["totalPercentChange"], 50.0)

    def test_single_datastore_view_supports_sorting_paging_and_statistics(self):
        self.service.columns.update({
            ("reference", "2045", "Azone", "Azone"): ["b", "a"],
            ("reference", "2045", "Azone", "Value"): [10, 30],
        })
        result = self.service.compare("reference", [], "Azone", "Value", "2045", changed_only=True, limit=1, sort_column="reference", sort_direction="desc")
        self.assertEqual(result["comparisons"], [])
        self.assertEqual(result["changedRows"], 0)
        self.assertEqual(result["displayRows"], 2)
        self.assertEqual(result["rows"][0]["id"], "a")
        self.assertEqual(result["referenceSummary"]["mean"], 20)

    def test_county_filter_maps_vehicle_azone(self):
        for root in (Path(self.temp.name) / "reference", Path(self.temp.name) / "comparison"):
            (root / "2045" / "Vehicle").mkdir(parents=True)
            (root / "2045" / "Vehicle" / "Azone.Rda").touch()
        self.service._county_mapping = lambda record: {"counties": {"Alpha County", "Beta County"}, "azone": {"alpha county": "Alpha County", "beta county": "Beta County"}, "bzone": {}}
        self.service.columns.update({
            ("reference", "2045", "Vehicle", "VehId"): ["v1", "v2"],
            ("reference", "2045", "Vehicle", "Azone"): ["Alpha County", "Beta County"],
            ("reference", "2045", "Vehicle", "Value"): [1, 2],
            ("comparison", "2045", "Vehicle", "VehId"): ["v1", "v2"],
            ("comparison", "2045", "Vehicle", "Azone"): ["Alpha County", "Beta County"],
            ("comparison", "2045", "Vehicle", "Value"): [3, 4],
        })
        result = self.service.compare("reference", ["comparison"], "Vehicle", "Value", "2045", filter_field="County", filter_values=["Alpha County"], mode="records")
        self.assertEqual([row["id"] for row in result["rows"]], ["v1"])

    def test_cross_output_geography_only_exposes_safe_counties(self):
        self.service._county_mapping = lambda record: {"counties": {"Beta County", "Alpha County"}, "azone": {}, "bzone": {}}
        result = self.service.cross_output_geo_options("reference", "2045")
        self.assertEqual(result["levels"], [{"field": "County", "label": "County", "values": ["Alpha County", "Beta County"], "derived": True}])

    def test_cross_output_geography_exposes_project_bzones_with_locality_labels(self):
        self.service._county_mapping = lambda record: {"counties": {"Alpha County"}, "azone": {}, "bzone": {}}
        self.service._map_geography = lambda record: {
            "azone": {}, "bzone": {"510010001001": "510010001001"},
            "names": {"510010001001": "Alpha County"},
        }
        result = self.service.cross_output_geo_options("reference", "2045")
        bzone = next(level for level in result["levels"] if level["field"] == "Bzone")
        self.assertEqual(bzone["values"], ["510010001001"])
        self.assertEqual(bzone["options"], [{"value": "510010001001", "label": "Alpha County · 510010001001"}])

    def test_dashboard_filters_household_and_worker_outputs_by_bzone(self):
        variables = [
            {"table": "Household", "name": "Income", "years": ["2045"], "units": "USD"},
            {"table": "Worker", "name": "Dvmt", "years": ["2045"], "units": "miles"},
        ]
        self.service.variables = lambda datastore_ids: variables
        self.service._map_geography = lambda record: {
            "azone": {},
            "bzone": {"510010001001": "510010001001", "510010001002": "510010001002"},
            "names": {"510010001001": "Alpha County", "510010001002": "Alpha County"},
        }
        self.service._variable_files = lambda root: [
            {"year": "2045", "table": "Household", "name": name}
            for name in ("HhId", "Bzone", "Income")
        ] + [
            {"year": "2045", "table": "Worker", "name": name}
            for name in ("HhId", "Dvmt")
        ]
        for record, household_values, worker_values in (
            ("reference", [100, 200], [10, 20, 30]),
            ("comparison", [150, 250], [15, 25, 35]),
        ):
            self.service.columns[(record, "2045", "Household", "HhId")] = ["h1", "h2"]
            self.service.columns[(record, "2045", "Household", "Bzone")] = ["510010001001", "510010001002"]
            self.service.columns[(record, "2045", "Household", "Income")] = household_values
            self.service.columns[(record, "2045", "Worker", "HhId")] = ["h1", "h1", "h2"]
            self.service.columns[(record, "2045", "Worker", "Dvmt")] = worker_values
        result = self.service.dashboard(
            "reference", "comparison", "2045", filter_field="Bzone", filter_values=["510010001001"]
        )
        rows = {row["variable"]: row for row in result["rows"]}
        self.assertEqual(rows["Income"]["referenceSum"], 100)
        self.assertEqual(rows["Dvmt"]["referenceSum"], 30)
        self.assertEqual(rows["Dvmt"]["geographyAssignments"][0]["method"], "Worker.HhId -> Household.HhId -> Household.Bzone")
        self.assertEqual(result["scopeLabel"], "Bzone: Alpha County · 510010001001")

    def test_dashboard_snapshot_filters_and_sorts_without_recomparing(self):
        variables = [
            {"table": "Azone", "name": "Increase", "years": ["2045"], "units": "%", "description": "Increase"},
            {"table": "Azone", "name": "Decrease", "years": ["2045"], "units": "%", "description": "Decrease"},
            {"table": "Azone", "name": "Small", "years": ["2045"], "units": "%", "description": "Small"},
            {"table": "Azone", "name": "Zero", "years": ["2045"], "units": "%", "description": "Zero"},
        ]
        self.service.variables = lambda datastore_ids: variables
        for root in ("reference", "comparison"):
            self.service.columns[(root, "2045", "Azone", "Azone")] = ["a"]
        self.service.columns.update({
            ("reference", "2045", "Azone", "Increase"): [100], ("comparison", "2045", "Azone", "Increase"): [140],
            ("reference", "2045", "Azone", "Decrease"): [100], ("comparison", "2045", "Azone", "Decrease"): [70],
            ("reference", "2045", "Azone", "Small"): [100], ("comparison", "2045", "Azone", "Small"): [102],
            ("reference", "2045", "Azone", "Zero"): [100], ("comparison", "2045", "Azone", "Zero"): [100],
        })
        generated = self.service.dashboard("reference", "comparison", "2045")
        with patch.object(self.service, "compare", side_effect=AssertionError("display changes must not compare")):
            threshold = self.service.dashboard_display(generated["dashboardToken"], "magnitude", "threshold", 5, 5)
            extremes = self.service.dashboard_display(generated["dashboardToken"], "value_asc", "extremes", 0, 1)
            without_zero = self.service.dashboard_display(generated["dashboardToken"], "name", "all", 0, 5, True)
        self.assertEqual([row["variable"] for row in threshold["rows"]], ["Increase", "Decrease"])
        self.assertEqual([row["variable"] for row in extremes["rows"]], ["Decrease", "Increase"])
        self.assertEqual([row["variable"] for row in without_zero["rows"]], ["Decrease", "Increase", "Small"])
        self.assertTrue(without_zero["hideZero"])
        self.assertEqual(len(extremes["sourceRows"]), 4)
        self.assertEqual(len(without_zero["sourceRows"]), 4)

    def test_comparison_map_uses_independent_all_row_geographic_means(self):
        self.service._variable_files = lambda root: [
            {"year": "2045", "table": "Household", "name": "Azone"},
            {"year": "2045", "table": "Household", "name": "Value"},
        ]
        self.service.columns.update({
            ("reference", "2045", "Household", "Azone"): ["51001", "51001", "51003"],
            ("reference", "2045", "Household", "Value"): [10, 30, 0],
            ("comparison", "2045", "Household", "Azone"): ["51001", "51003", "51003"],
            ("comparison", "2045", "Household", "Value"): [30, 0, 5],
        })
        result = self.service.comparison_map("reference", "comparison", "2045", "Household", "Value", "azone")
        rows = {row["geographyId"]: row for row in result["geographyRows"]}
        self.assertEqual(rows["51001"]["referenceCount"], 2)
        self.assertEqual(rows["51001"]["comparisonCount"], 1)
        self.assertEqual(rows["51001"]["referenceValue"], 20)
        self.assertEqual(rows["51001"]["comparisonValue"], 30)
        self.assertEqual(rows["51001"]["percentChange"], 50)
        self.assertEqual(rows["51003"]["referenceValue"], 0)
        self.assertIsNone(rows["51003"]["percentChange"])
        self.assertEqual(self.service.comparison_map_snapshot(result["mapToken"])["aggregation"], "mean")
        summed = self.service.comparison_map("reference", "comparison", "2045", "Household", "Value", "azone", "sum")
        counted = self.service.comparison_map("reference", "comparison", "2045", "Household", "Value", "azone", "count")
        self.assertEqual({row["geographyId"]: row for row in summed["geographyRows"]}["51001"]["referenceValue"], 40)
        self.assertEqual({row["geographyId"]: row for row in counted["geographyRows"]}["51001"]["referenceValue"], 2)

    def test_vehicle_bzone_map_derives_household_geography_independently(self):
        self.service._variable_files = lambda root: [
            {"year": "2045", "table": "Vehicle", "name": "HhId"},
            {"year": "2045", "table": "Vehicle", "name": "OwnCostPerMile"},
            {"year": "2045", "table": "Household", "name": "HhId"},
            {"year": "2045", "table": "Household", "name": "Bzone"},
        ]
        self.service.columns.update({
            ("reference", "2045", "Vehicle", "HhId"): ["h1", "h1", "h2", "missing"],
            ("reference", "2045", "Vehicle", "OwnCostPerMile"): [1, 3, 5, 100],
            ("reference", "2045", "Household", "HhId"): ["h1", "h2"],
            ("reference", "2045", "Household", "Bzone"): ["510010001001", "510010001002"],
            ("comparison", "2045", "Vehicle", "HhId"): ["h2", "h1", "h1"],
            ("comparison", "2045", "Vehicle", "OwnCostPerMile"): [7, 2, 4],
            ("comparison", "2045", "Household", "HhId"): ["h2", "h1"],
            ("comparison", "2045", "Household", "Bzone"): ["510010001002", "510010001001"],
        })
        result = self.service.comparison_map("reference", "comparison", "2045", "Vehicle", "OwnCostPerMile", "bzone")
        rows = {row["geographyId"]: row for row in result["geographyRows"]}
        self.assertEqual(rows["510010001001"]["referenceValue"], 2)
        self.assertEqual(rows["510010001001"]["comparisonValue"], 3)
        self.assertEqual(rows["510010001001"]["referenceCount"], 2)
        self.assertEqual(rows["510010001002"]["comparisonValue"], 7)
        self.assertEqual(result["assignments"][0]["unmatchedRows"], 1)
        self.assertIn("Household.Bzone", result["assignments"][0]["assignment"])

    def test_comparison_map_operation_is_cached_by_snapshot_inputs(self):
        self.service.columns.update({
            ("reference", "2045", "Bzone", "Bzone"): ["510010001001"],
            ("reference", "2045", "Bzone", "Value"): [10],
            ("comparison", "2045", "Bzone", "Bzone"): ["510010001001"],
            ("comparison", "2045", "Bzone", "Value"): [12],
        })
        manager = ComparisonOperationManager(self.service)
        request = {"operationKind":"map", "reference":"reference", "comparison":"comparison", "table":"Bzone", "variable":"Value", "year":"2045", "geographyLevel":"bzone"}
        operation = manager.start(request)
        deadline = time.monotonic() + 2
        while operation["state"] in {"waiting", "running"} and time.monotonic() < deadline:
            time.sleep(.01); operation = manager.status(operation["id"])
        self.assertEqual(operation["state"], "succeeded", operation.get("message"))
        self.assertEqual(operation["result"]["geographyRows"][0]["percentChange"], 20)
        repeated = manager.start(request)
        self.assertEqual(repeated["state"], "succeeded")
        self.assertTrue(repeated["cached"])

    def test_worker_bzone_map_cache_fingerprints_household_assignments(self):
        for record in self.service.records.values():
            root = Path(record["path"]) / "2045"
            (root / "Worker").mkdir(parents=True)
            (root / "Household").mkdir(parents=True)
            for relative, content in (
                (Path("Worker/Dvmt.Rda"), b"value"),
                (Path("Worker/HhId.Rda"), b"worker-households"),
                (Path("Household/HhId.Rda"), b"household-ids"),
                (Path("Household/Bzone.Rda"), b"household-bzones"),
            ):
                (root / relative).write_bytes(content)
        manager = ComparisonOperationManager(self.service)
        request = {"operationKind":"map", "reference":"reference", "comparison":"comparison", "table":"Worker", "variable":"Dvmt", "year":"2045", "geographyLevel":"bzone"}
        first = manager._cache_key(request)
        household_bzones = Path(self.service.records["comparison"]["path"]) / "2045/Household/Bzone.Rda"
        household_bzones.write_bytes(b"changed-household-bzones")
        self.assertNotEqual(first, manager._cache_key(request))

    def test_new_operation_status_survives_transient_operation_file_visibility(self):
        manager = ComparisonOperationManager(self.service)
        request = {"reference":"reference", "comparisons":["comparison"], "table":"Azone", "variable":"Value", "year":"2045"}
        with patch.object(manager, "_run"):
            operation = manager.start(request)
        operation_path = manager.root / operation["id"] / "operation.json"
        operation_path.unlink()
        recovered = manager.status(operation["id"])
        self.assertEqual(recovered["id"], operation["id"])
        self.assertEqual(recovered["state"], "waiting")
    def test_dashboard_workbook_contains_view_source_chart_and_provenance(self):
        try:
            import xlsxwriter  # noqa: F401
        except ImportError:
            self.skipTest("XlsxWriter is not installed")
        output = Path(self.temp.name) / "dashboard.xlsx"
        row = {"table":"Azone","variable":"Value","label":"Azone / Value","percentChange":10.0,"referenceSum":100,"comparisonSum":110,"changedRows":1,"totalRows":1,"units":"PRSN","description":"Value"}
        payload = {"year":"2045","reference":self.service.records["reference"],"comparison":self.service.records["comparison"],"rows":[row],"sourceRows":[row],"filterField":"County","filterValues":["Alpha County"]}
        WorkbookWriter(output).dashboard(payload, lambda: False)
        with zipfile.ZipFile(output) as archive:
            workbook_xml = archive.read("xl/workbook.xml").decode("utf-8")
            chart_names = [name for name in archive.namelist() if name.startswith("xl/charts/chart")]
        for name in ("Chart", "Displayed Data", "Source Data", "Provenance"):
            self.assertIn(name, workbook_xml)
        self.assertTrue(chart_names)

    def test_persistent_operation_exposes_page_then_full_statistics(self):
        self.service.columns.update({
            ("reference", "2045", "Azone", "Azone"): ["a", "b"],
            ("reference", "2045", "Azone", "Value"): [1, 2],
            ("comparison", "2045", "Azone", "Azone"): ["a", "b"],
            ("comparison", "2045", "Azone", "Value"): [1, 3],
        })
        manager = ComparisonOperationManager(self.service)
        operation = manager.start({"reference":"reference","comparisons":["comparison"],"table":"Azone","variable":"Value","year":"2045","limit":1})
        deadline = time.monotonic() + 2
        while operation["state"] in {"waiting", "running"} and time.monotonic() < deadline:
            time.sleep(.01); operation = manager.status(operation["id"])
        self.assertEqual(operation["state"], "succeeded")
        self.assertEqual(len(operation["page"]["rows"]), 1)
        self.assertTrue(operation["page"]["statsPending"])
        self.assertEqual(operation["result"]["changedRows"], 1)
        repeated = manager.start({"reference":"reference","comparisons":["comparison"],"table":"Azone","variable":"Value","year":"2045","limit":1})
        self.assertEqual(repeated["state"], "succeeded")
        self.assertTrue(repeated["cached"])

    def test_persistent_excel_export_preserves_values_provenance_and_text_safety(self):
        try:
            import xlsxwriter  # noqa: F401
        except ImportError:
            self.skipTest("XlsxWriter is not installed")
        self.service.columns.update({
            ("reference", "2045", "Azone", "Azone"): ["a", "b"],
            ("reference", "2045", "Azone", "Value"): ["=not-a-formula", 2.1234567],
            ("comparison", "2045", "Azone", "Azone"): ["a", "b"],
            ("comparison", "2045", "Azone", "Value"): ["=not-a-formula", 3.1234567],
        })
        manager = ComparisonExportManager(self.service)
        with patch("backend.workbench.excel_exports.EXCEL_MAX_DATA_ROWS", 1):
            operation = manager.start({"kind":"current","reference":"reference","comparisons":["comparison"],"table":"Azone","variable":"Value","year":"2045","filterValues":[]})
            deadline = time.monotonic() + 3
            while operation["state"] in {"waiting", "running"} and time.monotonic() < deadline:
                time.sleep(.01); operation = manager.status(operation["id"])
        self.assertEqual(operation["state"], "succeeded", operation.get("message"))
        workbook, filename, mime_type = manager.download(operation["id"])
        self.assertTrue(filename.endswith(".xlsx"))
        self.assertEqual(mime_type, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        with zipfile.ZipFile(workbook) as archive:
            workbook_xml = archive.read("xl/workbook.xml").decode("utf-8")
            sheets = "".join(archive.read(name).decode("utf-8") for name in archive.namelist() if name.startswith("xl/worksheets/sheet"))
        self.assertIn("Comparison", workbook_xml)
        self.assertIn("Comparison 2", workbook_xml)
        self.assertIn("Statistics", workbook_xml)
        self.assertIn("Provenance", workbook_xml)
        self.assertIn("=not-a-formula", sheets)
        self.assertNotIn("<f>", sheets)
        self.assertNotIn(str(self.service.workspace.root), sheets)

    def test_change_summary_workbook_uses_total_percent_change(self):
        try:
            import xlsxwriter  # noqa: F401
        except ImportError:
            self.skipTest("XlsxWriter is not installed")
        output = Path(self.temp.name) / "change-summary.xlsx"
        payload = {
            "year": "2045",
            "results": [{
                "table": "Azone", "variable": "Value", "changedRows": 1, "totalRows": 2,
                "percentRowsChanged": 50.0, "units": "PRSN", "description": "Test value",
                "pairStats": [{"label": "Scenario", "totalPercentChange": 25.0}],
            }],
        }
        records = [self.service.records["reference"], {**self.service.records["comparison"], "label": "Scenario"}]

        WorkbookWriter(output).change_summary(payload, records, lambda: False)

        with zipfile.ZipFile(output) as archive:
            sheets = "".join(archive.read(name).decode("utf-8") for name in archive.namelist() if name.startswith("xl/worksheets/sheet"))
        self.assertIn("Scenario Change %", sheets)
        self.assertIn("Azone / Value", sheets)
        self.assertNotIn("Percent rows changed", sheets)
        self.assertNotIn("Changed rows", sheets)
        self.assertNotIn("Total rows", sheets)

    def test_full_variable_csv_zip_contains_one_comparison_file_per_output(self):
        self.service.variables = lambda datastore_ids: [
            {"table": "Azone", "name": "Value", "years": ["2045"], "units": "PRSN", "description": "Value"},
        ]
        self.service.columns.update({
            ("reference", "2045", "Azone", "Azone"): ["a", "b"],
            ("reference", "2045", "Azone", "Value"): [10, 0],
            ("comparison", "2045", "Azone", "Azone"): ["a", "b"],
            ("comparison", "2045", "Azone", "Value"): [15, 0],
        })
        manager = ComparisonExportManager(self.service)
        operation = manager.start({"kind": "full-variables", "format": "csv-zip", "reference": "reference", "comparisons": ["comparison"], "year": "2045", "variableKeys": ["Azone/Value"]})
        deadline = time.monotonic() + 3
        while operation["state"] in {"waiting", "running"} and time.monotonic() < deadline:
            time.sleep(.01); operation = manager.status(operation["id"])
        self.assertEqual(operation["state"], "succeeded", operation.get("message"))
        artifact, filename, mime_type = manager.download(operation["id"])
        self.assertTrue(filename.endswith(".zip"))
        self.assertEqual(mime_type, "application/zip")
        with zipfile.ZipFile(artifact) as archive:
            self.assertIn("Azone_Value.csv", archive.namelist())
            csv_text = archive.read("Azone_Value.csv").decode("utf-8")
            self.assertIn("Change % Comparison", csv_text)
            self.assertIn("a,10,15,50.0", csv_text)
            self.assertIn("manifest.json", archive.namelist())

    def test_full_variable_workbook_splits_large_outputs_and_has_index(self):
        try:
            import xlsxwriter  # noqa: F401
        except ImportError:
            self.skipTest("XlsxWriter is not installed")
        self.service.variables = lambda datastore_ids: [
            {"table": "Azone", "name": "Value", "years": ["2045"], "units": "PRSN", "description": "Value"},
        ]
        self.service.columns.update({
            ("reference", "2045", "Azone", "Azone"): ["a", "b"],
            ("reference", "2045", "Azone", "Value"): [10, 20],
            ("comparison", "2045", "Azone", "Azone"): ["a", "b"],
            ("comparison", "2045", "Azone", "Value"): [15, 25],
        })
        manager = ComparisonExportManager(self.service)
        with patch("backend.workbench.excel_exports.EXCEL_MAX_DATA_ROWS", 1):
            operation = manager.start({"kind": "full-variables", "format": "xlsx", "reference": "reference", "comparisons": ["comparison"], "year": "2045", "variableKeys": ["Azone/Value"]})
            deadline = time.monotonic() + 3
            while operation["state"] in {"waiting", "running"} and time.monotonic() < deadline:
                time.sleep(.01); operation = manager.status(operation["id"])
        self.assertEqual(operation["state"], "succeeded", operation.get("message"))
        artifact, _, _ = manager.download(operation["id"])
        with zipfile.ZipFile(artifact) as archive:
            workbook_xml = archive.read("xl/workbook.xml").decode("utf-8")
        for sheet_name in ("Index", "Azone-Value", "Azone-Value 2", "Provenance"):
            self.assertIn(sheet_name, workbook_xml)


if __name__ == "__main__":
    unittest.main()
