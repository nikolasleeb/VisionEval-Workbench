import json
import tempfile
import threading
import time
import unittest
from decimal import Decimal
from pathlib import Path

from backend.workbench.explore import ExploreService
from backend.workbench.hypercube import (
    HypercubeOperationManager,
    HypercubeService,
    HypercubeCancelled,
    range_values,
)
from backend.workbench.workspace import Workspace, WorkspaceError
from tests.test_workspace import make_model, pair_assets, write


ROOT = Path(__file__).resolve().parents[1]


class HypercubeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.workspace = Workspace(self.root / "workspace")
        source_library = self.root / "source" / "InputLibrary" / "Plan"
        write(source_library / "bzone_network_design.csv", "Geo,Year,D3,D4\n101,2024,3,8\n101,2045,4,10\n")
        write(source_library / "azone_hh_pop_by_age.csv", "Geo,Year,Age0to14,PropTest\nTest County,2045,10,0.5\nOther County,2045,20,0.6\n")
        write(source_library / "model_parameters.json", "[]\n")
        self.workspace.copy_input_library(source_library.parent)
        template = self.workspace.import_template(make_model(self.root), "Test MM")
        pair_assets(self.workspace, "Plan", template["id"])
        self.project = self.workspace.create_project({
            "name": "Hypercube project", "templateId": template["id"], "inputLibraryId": "Plan",
            "baseline": {"strategy": "fresh"}, "variations": [], "projectType": "hypercube",
        })
        explore = ExploreService(
            self.workspace, ROOT / "backend" / "explore_catalog.json",
            ROOT / "backend" / "unit_conflicts.json", ROOT / "backend" / "dependency_catalog.json",
        )
        self.service = HypercubeService(self.workspace, explore)

    def tearDown(self):
        self.temp.cleanup()

    def payload(self):
        return {
            "projectId": self.project["id"], "name": "Land use matrix", "year": "2045",
            "geographyType": "county", "locations": ["Test County"],
            "axes": [
                {"filename": "bzone_network_design.csv", "column": "D3", "operation": "percent", "start": "10", "end": "20", "interval": "6"},
                {"filename": "bzone_network_design.csv", "column": "D4", "operation": "add", "start": "1", "end": "2", "interval": "2"},
            ],
        }

    def test_decimal_range_always_includes_endpoint(self):
        self.assertEqual(range_values(Decimal("10"), Decimal("20"), Decimal("6")), [Decimal("10"), Decimal("16"), Decimal("20")])
        self.assertEqual(range_values(Decimal("10"), Decimal("15"), Decimal("2.5")), [Decimal("10"), Decimal("12.5"), Decimal("15.0")])
        with self.assertRaises(WorkspaceError):
            range_values(Decimal("20"), Decimal("10"), Decimal("2"))
        with self.assertRaisesRegex(WorkspaceError, "at least 2"):
            range_values(Decimal("1"), Decimal("2"), Decimal("1"))

    def test_preview_reports_full_cartesian_matrix(self):
        preview = self.service.preview(self.payload())
        self.assertEqual(preview["caseCount"], 6)
        self.assertEqual(preview["axes"][0]["values"], ["10", "16", "20"])
        self.assertEqual(preview["axes"][1]["values"], ["1", "2"])
        self.assertEqual(len(preview["examples"]), 3)
        self.assertEqual(preview["affectedCellsPerCase"], 2)
        self.assertEqual(preview["name"], "Hypercube project")
        self.assertEqual(preview["scopeDetails"][0]["targetLevel"], "Bzone")
        self.assertEqual(preview["scopeDetails"][0]["matchedRows"], 1)

    def test_incomplete_draft_saves_without_creating_cases(self):
        result = self.service.save_draft({
            "projectId": self.project["id"], "expectedProjectUpdatedAt": self.project["updatedAt"],
            "axes": [{"filename": "", "column": "", "operation": "percent", "start": "10", "end": "", "interval": ""}],
            "year": "", "geographyType": "all", "locations": [],
        })
        self.assertFalse(result["complete"])
        _, project = self.workspace.project(self.project["id"])
        self.assertEqual(project["variations"], [])
        self.assertEqual(project["hypercubeDraft"]["revision"], result["draft"]["revision"])

    def test_generation_uses_saved_revision_and_clears_draft(self):
        saved = self.service.save_draft({**self.payload(), "expectedProjectUpdatedAt": self.project["updatedAt"]})
        revision = saved["draft"]["revision"]
        preview = self.service.preview({"projectId": self.project["id"], "draftRevision": revision})
        self.assertEqual(preview["caseCount"], 6)
        self.assertEqual(preview["draftRevision"], revision)
        result = self.service.generate(
            {"projectId": self.project["id"], "draftRevision": revision},
            threading.Event(), lambda _completed, _total: None,
        )
        self.assertEqual(result["caseCount"], 6)
        _, project = self.workspace.project(self.project["id"])
        self.assertNotIn("hypercubeDraft", project)

    def test_stale_saved_revision_is_rejected(self):
        first = self.service.save_draft({**self.payload(), "expectedProjectUpdatedAt": self.project["updatedAt"]})
        _, current = self.workspace.project(self.project["id"])
        self.service.save_draft({**self.payload(), "expectedProjectUpdatedAt": current["updatedAt"]})
        with self.assertRaisesRegex(WorkspaceError, "saved Hypercube setup changed"):
            self.service.preview({"projectId": self.project["id"], "draftRevision": first["draft"]["revision"]})

    def test_project_copy_preserves_draft_with_fresh_revision(self):
        saved = self.service.save_draft({**self.payload(), "expectedProjectUpdatedAt": self.project["updatedAt"]})
        copied = self.workspace.copy_project(self.project["id"], "Copied draft")
        self.assertEqual(copied["hypercubeDraft"]["axes"], saved["draft"]["axes"])
        self.assertNotEqual(copied["hypercubeDraft"]["revision"], saved["draft"]["revision"])

    def test_manager_requires_current_preview_token_for_saved_draft(self):
        saved = self.service.save_draft({**self.payload(), "expectedProjectUpdatedAt": self.project["updatedAt"]})
        manager = HypercubeOperationManager(self.service)
        request = {"projectId": self.project["id"], "draftRevision": saved["draft"]["revision"]}
        with self.assertRaisesRegex(WorkspaceError, "Preview the current saved"):
            manager.start(request)
        preview = manager.preview(request)
        operation = manager.start({**request, "previewToken": preview["previewToken"]})
        # Small fixtures may complete before start() returns on a fast host.
        self.assertIn(operation["state"], {"waiting", "running", "succeeded"})
        deadline = time.time() + 5
        while time.time() < deadline and manager.status(operation["id"])["state"] in {"waiting", "running"}:
            time.sleep(0.01)
        self.assertEqual(manager.status(operation["id"])["state"], "succeeded")

    def test_generation_creates_matrix_from_baseline_and_persists_group(self):
        progress = []
        result = self.service.generate(self.payload(), threading.Event(), lambda completed, total: progress.append((completed, total)))
        self.assertEqual(result["caseCount"], 6)
        self.assertEqual(progress[-1], (6, 6))
        _, project = self.workspace.project(self.project["id"])
        self.assertEqual(len(project["variations"]), 6)
        self.assertEqual(project["hypercubes"][0]["scenarioIds"], result["scenarioIds"])
        first = project["variations"][0]
        path, overlay = self.workspace.input_file("Plan", "bzone_network_design.csv", project["id"], first["id"])
        self.assertTrue(overlay)
        rows = path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(rows[1], "101,2024,3,8")
        self.assertEqual(rows[2], "101,2045,4.4,11")
        self.assertEqual(first["hypercube"]["values"][0]["value"], "10")

    def test_all_matching_rows_updates_every_azone_without_adding_cases(self):
        payload = {
            "projectId": self.project["id"], "year": "2045", "geographyType": "all", "locations": [],
            "axes": [{
                "filename": "azone_hh_pop_by_age.csv", "column": "Age0to14", "operation": "percent",
                "start": "10", "end": "10", "interval": "2",
            }],
        }
        preview = self.service.preview(payload)
        self.assertEqual(preview["caseCount"], 1)
        self.assertEqual(preview["scopeDetails"][0]["targetLevel"], "Azone")
        self.assertEqual(preview["scopeDetails"][0]["matchedRows"], 2)
        result = self.service.generate(payload, threading.Event(), lambda _completed, _total: None)
        path, overlay = self.workspace.input_file(
            "Plan", "azone_hh_pop_by_age.csv", self.project["id"], result["scenarioIds"][0],
        )
        self.assertTrue(overlay)
        self.assertIn("Test County,2045,11,0.5", path.read_text(encoding="utf-8"))
        self.assertIn("Other County,2045,22,0.6", path.read_text(encoding="utf-8"))

    def test_standard_project_cannot_generate_a_hypercube(self):
        _, project = self.workspace.project(self.project["id"])
        project["projectType"] = "standard"
        self.workspace.save_project(project)
        with self.assertRaisesRegex(WorkspaceError, "dedicated Hypercube project"):
            self.service.preview(self.payload())

    def test_existing_matrix_requires_explicit_atomic_replacement(self):
        first = self.service.generate(self.payload(), threading.Event(), lambda _completed, _total: None)
        with self.assertRaisesRegex(WorkspaceError, "already has a matrix"):
            self.service.preview(self.payload())
        replacement = self.payload()
        replacement.update({"replaceExisting": True, "name": "Replacement matrix"})
        preview = self.service.preview(replacement)
        self.assertTrue(preview["replacingExisting"])
        second = self.service.generate(replacement, threading.Event(), lambda _completed, _total: None)
        _, project = self.workspace.project(self.project["id"])
        self.assertEqual([item["name"] for item in project["hypercubes"]], ["Hypercube project"])
        self.assertEqual(len(project["variations"]), second["caseCount"])
        self.assertFalse(set(first["scenarioIds"]) & {item["id"] for item in project["variations"]})

    def test_matrix_replacement_is_blocked_after_run_submission(self):
        self.service.generate(self.payload(), threading.Event(), lambda _completed, _total: None)
        _, project = self.workspace.project(self.project["id"])
        project["runIds"] = ["run-case"]
        self.workspace.save_project(project)
        replacement = self.payload()
        replacement["replaceExisting"] = True
        with self.assertRaisesRegex(WorkspaceError, "cannot be replaced"):
            self.service.preview(replacement)

    def test_generated_case_exports_to_standard_project_without_matrix_management_metadata(self):
        generated = self.service.generate(
            self.payload(), threading.Event(), lambda _completed, _total: None,
        )
        copied = self.workspace.copy_variations(
            self.project["id"], [generated["scenarioIds"][0]], new_project_name="Standalone case",
        )

        self.assertEqual(copied["project"]["projectType"], "standard")
        self.assertNotIn("hypercube", copied["variations"][0])
        self.assertEqual(len(copied["variations"][0]["overlays"]), 1)

        full_copy = self.workspace.copy_project(self.project["id"], "Matrix project copy")
        self.assertEqual(full_copy["projectType"], "hypercube")
        self.assertEqual(len(full_copy["hypercubes"]), 1)
        self.assertEqual(
            set(full_copy["hypercubes"][0]["scenarioIds"]),
            {item["id"] for item in full_copy["variations"]},
        )

    def test_cancelled_generation_leaves_project_unchanged(self):
        cancelled = threading.Event()
        cancelled.set()
        with self.assertRaises(HypercubeCancelled):
            self.service.generate(self.payload(), cancelled, lambda _completed, _total: None)
        _, project = self.workspace.project(self.project["id"])
        self.assertEqual(project["variations"], [])
        self.assertNotIn("hypercubes", project)

    def test_generation_rounds_integer_fields_and_caps_proportions(self):
        payload = {
            "projectId": self.project["id"], "name": "Types", "year": "2045",
            "geographyType": "all", "locations": [],
            "axes": [
                {"filename": "azone_hh_pop_by_age.csv", "column": "Age0to14", "operation": "set", "start": "2.5", "end": "2.5", "interval": "2"},
                {"filename": "azone_hh_pop_by_age.csv", "column": "PropTest", "operation": "add", "start": "2", "end": "2", "interval": "2"},
            ],
        }
        result = self.service.generate(payload, threading.Event(), lambda _completed, _total: None)
        _, project = self.workspace.project(self.project["id"])
        variation = next(item for item in project["variations"] if item["id"] == result["scenarioIds"][0])
        path, _ = self.workspace.input_file("Plan", "azone_hh_pop_by_age.csv", project["id"], variation["id"])
        self.assertIn("Test County,2045,3,1", path.read_text(encoding="utf-8"))

    def test_concurrent_project_change_prevents_partial_commit(self):
        changed = False

        def progress(completed, _total):
            nonlocal changed
            if completed == 1 and not changed:
                changed = True
                self.workspace.update_project(self.project["id"], "Changed during hypercube")

        with self.assertRaisesRegex(WorkspaceError, "changed while"):
            self.service.generate(self.payload(), threading.Event(), progress)
        _, project = self.workspace.project(self.project["id"])
        self.assertEqual(project["name"], "Changed during hypercube")
        self.assertEqual(project["variations"], [])

    def test_builder_limits_axis_values_and_total_cases(self):
        payload = self.payload()
        payload["geographyType"] = "all"
        payload["locations"] = []
        payload["axes"] = [
            {"filename": "bzone_network_design.csv", "column": "D3", "operation": "percent", "start": "0", "end": "100", "interval": "2"},
            {"filename": "bzone_network_design.csv", "column": "D4", "operation": "add", "start": "0", "end": "2", "interval": "2"},
        ]
        with self.assertRaisesRegex(WorkspaceError, "20 values"):
            self.service.preview(payload)

    def test_duplicate_axis_and_empty_scope_are_rejected(self):
        payload = self.payload()
        payload["axes"][1] = dict(payload["axes"][0])
        with self.assertRaisesRegex(WorkspaceError, "selected more than once"):
            self.service.preview(payload)
        payload = self.payload()
        payload["axes"].append({**payload["axes"][0], "column": "Other"})
        with self.assertRaisesRegex(WorkspaceError, "no more than two"):
            self.service.preview(payload)
        payload = self.payload()
        payload["year"] = "2099"
        with self.assertRaisesRegex(WorkspaceError, "no numeric cells"):
            self.service.preview(payload)


if __name__ == "__main__":
    unittest.main()
