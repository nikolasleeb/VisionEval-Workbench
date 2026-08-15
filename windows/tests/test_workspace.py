import json
import tempfile
import unittest
from pathlib import Path

from backend.workbench.runtime import RuntimeManager
from backend.workbench.workspace import Workspace, WorkspaceError, read_json


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_model(root: Path) -> Path:
    model = root / "source-model"
    write(model / "visioneval.cnf", "ScriptsDir: scripts\nInputDir: inputs\nParamDir: defs\nGeoFile: geo.csv\nModelParamFile: model_parameters.json\nYears: [2024, 2045]\n")
    write(model / "scripts" / "run_model.R", "# runnable\n")
    write(model / "defs" / "geo.csv", "Azone,Bzone,Czone,Marea\nTest County,101,NA,metro\n")
    write(model / "defs" / "units.csv", "Unit\n")
    write(model / "defs" / "deflators.csv", "Year\n2024\n")
    write(model / "inputs" / "bzone_network_design.csv", "Geo,Year,D3\n101,2024,1\n101,2045,2\n")
    write(model / "inputs" / "model_parameters.json", "[]\n")
    return model


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.workspace = Workspace(self.root / "workspace")
        source_library = self.root / "old" / "InputLibrary" / "Plan"
        write(source_library / "bzone_network_design.csv", "Geo,Year,D3\n101,2024,3\n101,2045,4\n")
        write(source_library / "model_parameters.json", "[]\n")
        self.library_source = source_library.parent
        self.model_source = make_model(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_workspace_marker_settings_and_storage_contract(self):
        marker = read_json(self.workspace.root / ".visioneval-workspace.json", {})
        self.assertEqual(marker["formatVersion"], 2)
        self.assertTrue((self.workspace.root / "Assets" / "InputLibraries").is_dir())
        self.assertTrue((self.workspace.root / "Results" / "Models").is_dir())
        self.assertTrue((self.workspace.internal / "settings.json").is_file())
        self.assertTrue(marker["id"].startswith("workspace-"))
        self.assertTrue(self.workspace.settings()["retainFullExports"])
        self.assertFalse(self.workspace.settings()["checkVisionEvalUpdates"])
        self.assertEqual(
            self.workspace.settings()["numericPrecision"],
            {"default": 2, "singleFile": None, "batch": None, "output": None, "percentage": None},
        )
        write(self.workspace.models / "run-size" / "results" / "Datastore" / "data.bin", "12345")
        write(self.workspace.models / "run-size" / "results" / "output" / "table.csv", "1234567890")
        report = self.workspace.storage_report()
        run = next(item for item in report["runs"] if item["id"] == "run-size")
        self.assertEqual(run["datastoreBytes"], 5)
        self.assertEqual(run["exportBytes"], 10)

    def test_legacy_workspace_layout_migrates_without_losing_files(self):
        legacy_root = self.root / "legacy-workspace"
        write(legacy_root / "InputLibrary" / "Legacy" / "input.csv", "Geo,Year,Value\n1,2045,2\n")
        write(legacy_root / "models" / "run-one" / "result.txt", "complete")
        write(legacy_root / "exchange" / "cache" / "entry.json", "{}")
        write(legacy_root / "Projects" / "legacy-project" / "project.json", json.dumps({
            "id": "legacy-project",
            "inputLibrary": {"id": "Legacy", "path": str(legacy_root / "InputLibrary" / "Legacy")},
        }))
        write(legacy_root / "runs" / "run-one" / "job.json", json.dumps({
            "id": "run-one", "modelPath": str(legacy_root / "models" / "run-one"),
        }))
        write(legacy_root / "exchange" / "comparison-cache" / "nested" / "request.json", json.dumps({
            "records": [{"path": str(legacy_root / "models" / "run-one" / "Datastore")}],
        }))
        write(legacy_root / "workspace-settings.json", json.dumps(Workspace.default_settings()))
        write(legacy_root / "datastore_catalog.json", json.dumps({
            "version": 1,
            "datastores": [{"id": "legacy", "path": str(legacy_root / "models" / "run-one" / "Datastore")}],
        }))
        write(legacy_root / "VisionEval.Rproj", "Version: 1.0\n")
        migrated = Workspace(legacy_root)
        self.assertTrue((migrated.input_library / "Legacy" / "input.csv").is_file())
        self.assertTrue((migrated.models / "run-one" / "result.txt").is_file())
        self.assertTrue((migrated.exchange / "cache" / "entry.json").is_file())
        self.assertTrue((migrated.internal / "legacy" / "VisionEval.Rproj").is_file())
        self.assertFalse((legacy_root / "InputLibrary").exists())
        project = read_json(migrated.projects / "legacy-project" / "project.json", {})
        job = read_json(migrated.runs / "run-one" / "job.json", {})
        self.assertEqual(project["inputLibrary"]["path"], str(migrated.input_library / "Legacy"))
        self.assertEqual(job["modelPath"], str(migrated.models / "run-one"))
        self.assertEqual(migrated.catalog()["datastores"][0]["path"], str(migrated.models / "run-one" / "Datastore"))
        cache = read_json(migrated.exchange / "comparison-cache" / "nested" / "request.json", {})
        self.assertEqual(cache["records"][0]["path"], str(migrated.models / "run-one" / "Datastore"))
        Workspace(legacy_root)

    def test_workspace_defaults_must_reference_installed_assets(self):
        with self.assertRaises(WorkspaceError):
            self.workspace.update_settings({"defaultTemplateId": "missing"})
        self.workspace.copy_input_library(self.library_source)
        template = self.workspace.import_template(self.model_source, "Test MM")
        settings = self.workspace.update_settings({"defaultTemplateId": template["id"], "defaultInputLibraryId": "Plan"})
        self.assertEqual(settings["defaultTemplateId"], template["id"])
        settings = self.workspace.update_settings({"checkVisionEvalUpdates": False})
        self.assertFalse(settings["checkVisionEvalUpdates"])

    def test_unused_asset_is_archived_restored_and_purged(self):
        self.workspace.copy_input_library(self.library_source)
        result = self.workspace.archive_asset("input-library", "Plan")
        archived = result["archived"][0]
        self.assertFalse((self.workspace.input_library / "Plan").exists())
        self.assertEqual(self.workspace.list_archived_assets()[0]["daysRemaining"], 30)
        self.workspace.restore_asset(archived["archiveId"])
        self.assertTrue((self.workspace.input_library / "Plan").is_dir())
        second = self.workspace.archive_asset("input-library", "Plan")["archived"][0]
        self.workspace.purge_asset(second["archiveId"])
        self.assertEqual(self.workspace.list_archived_assets(), [])

    def test_asset_removal_is_blocked_by_active_and_archived_projects(self):
        _, project = self.setup_project()
        dependency = self.workspace.asset_dependencies("input-library", "Plan")
        self.assertEqual(dependency["projects"][0]["status"], "active")
        with self.assertRaisesRegex(WorkspaceError, project["name"]):
            self.workspace.archive_asset("input-library", "Plan")
        self.workspace.remove_project(project["id"])
        dependency = self.workspace.asset_dependencies("input-library", "Plan")
        self.assertEqual(dependency["projects"][0]["status"], "archived")
        with self.assertRaises(WorkspaceError):
            self.workspace.archive_asset("input-library", "Plan")

    def test_archiving_default_asset_clears_default(self):
        self.workspace.copy_input_library(self.library_source)
        self.workspace.update_settings({"defaultInputLibraryId": "Plan"})
        self.workspace.archive_asset("input-library", "Plan")
        self.assertEqual(self.workspace.settings()["defaultInputLibraryId"], "")

    def test_numeric_precision_settings_validate_and_merge(self):
        settings = self.workspace.update_settings({
            "numericPrecision": {
                "default": 5,
                "singleFile": 8,
                "batch": 0,
                "output": None,
                "percentage": 3,
            }
        })
        self.assertEqual(settings["numericPrecision"]["default"], 5)
        self.assertEqual(settings["numericPrecision"]["singleFile"], 8)
        self.assertEqual(settings["numericPrecision"]["batch"], 0)
        self.assertIsNone(settings["numericPrecision"]["output"])
        self.assertEqual(settings["numericPrecision"]["percentage"], 3)

        settings = self.workspace.update_settings({"numericPrecision": {"default": 2}})
        self.assertEqual(settings["numericPrecision"]["singleFile"], 8)
        self.assertEqual(settings["numericPrecision"]["batch"], 0)
        self.assertEqual(settings["numericPrecision"]["percentage"], 3)

        for invalid in (-1, 9, 2.5, True, "2"):
            with self.subTest(invalid=invalid), self.assertRaises(WorkspaceError):
                self.workspace.update_settings({"numericPrecision": {"default": invalid}})

        with self.assertRaises(WorkspaceError):
            self.workspace.update_settings({"numericPrecision": []})

    def setup_project(self):
        self.workspace.copy_input_library(self.library_source)
        template = self.workspace.import_template(self.model_source, "Test MM")
        project = self.workspace.create_project({
            "name": "Policy test",
            "templateId": template["id"],
            "inputLibraryId": "Plan",
            "baseline": {"strategy": "fresh"},
            "variations": [{"name": "Transit"}, {"name": "Compact"}],
        })
        return template, project

    def test_template_import_is_a_copy_and_has_provenance(self):
        original = (self.model_source / "visioneval.cnf").read_bytes()
        template = self.workspace.import_template(self.model_source, "Test MM")
        imported = self.workspace.templates / template["id"]
        self.assertTrue((imported / "workbench_template.json").is_file())
        (imported / "visioneval.cnf").write_text("changed", encoding="utf-8")
        self.assertEqual((self.model_source / "visioneval.cnf").read_bytes(), original)

    def test_single_input_library_folder_can_be_imported_directly(self):
        result = self.workspace.copy_input_library(self.library_source / "Plan")
        self.assertEqual(result["copied"], ["Plan"])
        self.assertTrue((self.workspace.input_library / "Plan" / "bzone_network_design.csv").is_file())

    def test_invalid_template_is_rejected(self):
        invalid = self.root / "invalid"
        invalid.mkdir()
        with self.assertRaises(WorkspaceError):
            self.workspace.import_template(invalid)

    def test_overlay_only_changes_prepared_variation(self):
        template, project = self.setup_project()
        hidden_metadata = self.workspace.templates / template["id"] / ".workbench-map-context"
        hidden_metadata.mkdir()
        (hidden_metadata / "metadata.json").write_text("{}", encoding="utf-8")
        transit, compact = project["variations"]
        edited = "Geo,Year,D3\n101,2024,30\n101,2045,40\n"
        self.workspace.save_overlay(project["id"], transit["id"], "bzone_network_design.csv", edited)
        transit_model, provenance = self.workspace.prepare_model(project["id"], transit["id"], "run-transit")
        compact_model, _ = self.workspace.prepare_model(project["id"], compact["id"], "run-compact")
        self.assertEqual((transit_model / "inputs" / "bzone_network_design.csv").read_text(), edited)
        self.assertFalse((transit_model / ".workbench-map-context").exists())
        self.assertIn("101,2045,4", (compact_model / "inputs" / "bzone_network_design.csv").read_text())
        self.assertEqual(provenance["variationName"], "Transit")
        self.assertIn("101,2045,2", (self.model_source / "inputs" / "bzone_network_design.csv").read_text())

    def test_scenario_sidebar_operations_preserve_and_remove_file_edits(self):
        _, project = self.setup_project()
        transit = project["variations"][0]
        edited = "Geo,Year,D3\n101,2024,30\n101,2045,40\n"
        self.workspace.save_overlay(project["id"], transit["id"], "bzone_network_design.csv", edited)
        self.workspace.update_variation(
            project["id"], transit["id"], notes={"bzone_network_design.csv": "Transit policy assumption"}, scenario_note="Expand transit service"
        )

        duplicate = self.workspace.add_variation(project["id"], "Transit copy", transit["id"])
        copied_path, is_overlay = self.workspace.input_file(
            "Plan", "bzone_network_design.csv", project["id"], duplicate["id"]
        )
        self.assertTrue(is_overlay)
        self.assertEqual(copied_path.read_text(encoding="utf-8"), edited)
        self.assertEqual(duplicate["notes"]["bzone_network_design.csv"], "Transit policy assumption")
        self.assertEqual(duplicate["scenarioNote"], "Expand transit service")
        review = self.workspace.review_project(project["id"])
        original = next(item for item in review["scenarios"] if item["id"] == transit["id"])
        self.assertEqual(original["scenarioNote"], "Expand transit service")
        _, provenance = self.workspace.prepare_model(project["id"], transit["id"], "run-transit-note")
        self.assertEqual(provenance["scenarioNote"], "Expand transit service")

        self.workspace.delete_overlay(project["id"], duplicate["id"], "bzone_network_design.csv")
        base_path, is_overlay = self.workspace.input_file(
            "Plan", "bzone_network_design.csv", project["id"], duplicate["id"]
        )
        self.assertFalse(is_overlay)
        self.assertIn("101,2045,4", base_path.read_text(encoding="utf-8"))

        self.workspace.delete_variation(project["id"], duplicate["id"])
        _, updated = self.workspace.project(project["id"])
        self.assertNotIn(duplicate["id"], [item["id"] for item in updated["variations"]])

    def test_project_can_start_without_scenarios(self):
        self.workspace.copy_input_library(self.library_source)
        template = self.workspace.import_template(self.model_source, "Test MM")
        project = self.workspace.create_project({
            "name": "Empty editor project", "templateId": template["id"], "inputLibraryId": "Plan",
            "baseline": {"strategy": "fresh"}, "variations": [],
        })
        self.assertEqual(project["variations"], [])
        scenario = self.workspace.add_variation(project["id"], "Scenario 1")
        self.workspace.delete_variation(project["id"], scenario["id"])
        _, updated = self.workspace.project(project["id"])
        self.assertEqual(updated["variations"], [])

    def test_project_can_be_renamed_and_removed_recoverably(self):
        _, project = self.setup_project()
        updated = self.workspace.update_project(project["id"], "Renamed policy test")
        self.assertEqual(updated["name"], "Renamed policy test")
        self.assertEqual(self.workspace.project(project["id"])[1]["name"], "Renamed policy test")

        result = self.workspace.remove_project(project["id"])
        self.assertTrue(result["recoverable"])
        self.assertNotIn(project["id"], [item["id"] for item in self.workspace.list_projects()])
        self.assertTrue(any((path / "project.json").is_file() for path in self.workspace.removed_projects.iterdir()))
        with self.assertRaises(WorkspaceError):
            self.workspace.project(project["id"])
        archived = self.workspace.list_archived_projects()
        self.assertEqual(archived[0]["id"], project["id"])
        self.assertLessEqual(archived[0]["daysRemaining"], 30)
        restored = self.workspace.restore_project(project["id"])
        self.assertEqual(restored["id"], project["id"])
        self.assertEqual(self.workspace.project(project["id"])[1]["name"], "Renamed policy test")

    def test_archived_project_jobs_and_datastores_are_hidden_then_purged(self):
        _, project = self.setup_project()
        result_root = self.workspace.models / "run-test" / "results" / "Datastore"
        write(result_root / "DatastoreListing.Rda", "fixture")
        datastore = self.workspace.register_datastore({"id": "result-1", "label": "Result", "path": str(result_root), "projectId": project["id"]})
        job_dir = self.workspace.runs / "run-test"
        write(job_dir / "job.json", json.dumps({"id":"run-test", "projectId":project["id"], "state":"succeeded", "modelPath":str(self.workspace.models / "run-test")}))
        self.workspace.remove_project(project["id"])
        self.assertNotIn(datastore["id"], [item["id"] for item in self.workspace.catalog(False)["datastores"]])
        purged = self.workspace.purge_project(project["id"])
        self.assertIn(datastore["id"], purged["removedDatastoreIds"])
        self.assertFalse(job_dir.exists())
        self.assertFalse((self.workspace.models / "run-test").exists())

    def test_project_with_active_job_cannot_be_archived(self):
        _, project = self.setup_project()
        write(self.workspace.runs / "run-active" / "job.json", json.dumps({"id":"run-active", "projectId":project["id"], "state":"running"}))
        with self.assertRaises(WorkspaceError):
            self.workspace.remove_project(project["id"])

    def test_purge_retains_datastore_used_by_an_active_baseline(self):
        template, source_project = self.setup_project()
        result_root = self.workspace.models / "run-shared" / "results" / "Datastore"
        write(result_root / "DatastoreListing.Rda", "fixture")
        datastore = self.workspace.register_datastore({
            "id": "shared-result", "label": "Shared baseline", "path": str(result_root),
            "projectId": source_project["id"], "templateId": template["id"],
        })
        active = self.workspace.create_project({
            "name": "Uses shared baseline", "templateId": template["id"], "inputLibraryId": "Plan",
            "baseline": {"strategy": "existing", "datastoreId": datastore["id"]}, "variations": [],
        })
        self.workspace.remove_project(source_project["id"])
        result = self.workspace.purge_project(source_project["id"])
        self.assertIn(datastore["id"], result["retainedDatastoreIds"])
        retained = next(item for item in self.workspace.catalog(False)["datastores"] if item["id"] == datastore["id"])
        self.assertIn(active["id"], retained["retainedForProjectIds"])

    def test_existing_removed_project_gets_a_fresh_recovery_period(self):
        removed = self.workspace.projects / ".Removed" / "old-project"
        write(removed / "project.json", json.dumps({"id": "project-old", "name": "Old", "variations": []}))
        migrated = Workspace(self.workspace.root)
        archived = migrated.list_archived_projects()
        self.assertEqual(archived[0]["id"], "project-old")
        self.assertEqual(archived[0]["daysRemaining"], 30)

    def test_baseline_display_name_is_project_specific(self):
        _, project = self.setup_project()
        self.assertEqual(project["baseline"]["displayName"], "Baseline")
        updated = self.workspace.update_baseline_name(project["id"], "Current Policies")
        self.assertEqual(updated["baseline"]["displayName"], "Current Policies")
        self.assertEqual(self.workspace.catalog()["datastores"], [])
        with self.assertRaises(WorkspaceError):
            self.workspace.update_baseline_name(project["id"], "  ")

    def test_geography_options_map_county_to_file_zone(self):
        _, project = self.setup_project()
        geography = self.workspace.geography_options(project["id"], "bzone_network_design.csv")
        county = next(level for level in geography["levels"] if level["id"] == "county")
        self.assertEqual(geography["targetLevel"], "Bzone")
        self.assertEqual(county["values"][0]["label"], "Test County")
        self.assertEqual(county["values"][0]["targetValues"], ["101"])

    def test_review_reports_saved_before_and_after_values(self):
        _, project = self.setup_project()
        scenario = project["variations"][0]
        edited = "Geo,Year,D3\n101,2024,30\n101,2045,4\n"
        self.workspace.save_overlay(project["id"], scenario["id"], "bzone_network_design.csv", edited)
        review = self.workspace.review_project(project["id"])
        file_review = review["scenarios"][0]["files"][0]
        self.assertEqual(file_review["changedRows"], 1)
        self.assertEqual(file_review["changedCells"], 1)
        self.assertEqual(file_review["changes"][0]["before"], "3")
        self.assertEqual(file_review["changes"][0]["after"], "30")

    def test_project_validation_checks_years_and_geography(self):
        _, project = self.setup_project()
        runtime = RuntimeManager(self.workspace)
        self.assertTrue(runtime.validate_project(project["id"])["valid"])
        library_file = self.workspace.input_library / "Plan" / "bzone_network_design.csv"
        library_file.write_text("Geo,Year,D3\n999,2050,1\n", encoding="utf-8")
        result = runtime.validate_project(project["id"])
        self.assertFalse(result["valid"])
        self.assertTrue(any("years" in error for error in result["errors"]))
        self.assertTrue(any("geography" in error for error in result["errors"]))

    def test_existing_baseline_is_marked_unverified_without_matching_template(self):
        self.workspace.copy_input_library(self.library_source)
        template = self.workspace.import_template(self.model_source, "Test MM")
        source = self.workspace.models / "legacy-import" / "results" / "Datastore"
        write(source / "DatastoreListing.Rda", "fixture")
        imported = self.workspace.register_datastore({
            "id": "legacy-imported-baseline",
            "label": "Old baseline",
            "path": str(source),
            "role": "imported",
            "source": "legacy",
        })
        project = self.workspace.create_project({
            "name": "Imported baseline project", "templateId": template["id"], "inputLibraryId": "Plan",
            "baseline": {"strategy": "existing", "datastoreId": imported["id"]}, "variations": [{"name": "Change"}],
        })
        self.assertEqual(project["baseline"]["compatibility"], "unverified")

    def test_legacy_imported_datastore_remains_visible_and_read_only(self):
        source = self.workspace.models / "legacy-import" / "results" / "Datastore"
        write(source / "DatastoreListing.Rda", "legacy result")
        record = self.workspace.register_datastore({
            "id": "legacy-imported-result",
            "label": "Legacy result",
            "path": str(source),
            "role": "imported",
            "source": "legacy",
        })
        visible = next(item for item in self.workspace.catalog()["datastores"] if item["id"] == record["id"])
        self.assertEqual(visible["role"], "imported")
        self.assertEqual(visible["label"], "Legacy result")


if __name__ == "__main__":
    unittest.main()
