import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.workbench.runtime import RuntimeManager
from backend.workbench.copy_operations import CopyOperationManager
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


def pair_assets(workspace: Workspace, library_id: str, template_id: str, registration_id: str = "test-model-bundle") -> None:
    workspace.record_asset_registration({
        "id": f"{registration_id}:{library_id}", "type": "model-bundle", "version": "test",
        "assets": [
            {"kind": "input-library", "id": library_id},
            {"kind": "model-template", "id": template_id},
        ],
    })


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
        self.assertFalse(self.workspace.settings()["updateChecks"]["automatic"])
        self.assertEqual(
            self.workspace.settings()["updateChecks"]["sources"],
            {"visioneval": True, "runtimeImage": True, "workbench": True},
        )
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
        self.assertEqual(report["defaultResultEstimateBytes"], 1_700_000_000)

    def test_legacy_model_bundle_ids_use_current_display_names(self):
        library = self.workspace.input_library / "PlanRVA MM"
        write(library / "input.csv", "Geo,Value\n1,2\n")
        template = self.workspace.templates / "template-planrva-mm-v1"
        write(template / "workbench_template.json", json.dumps({
            "id": "template-planrva-mm-v1", "name": "PlanRVA MM", "fingerprint": "legacy",
        }))
        pair_assets(self.workspace, "PlanRVA MM", "template-planrva-mm-v1", "planrva-mm-v1")
        self.assertEqual(self.workspace.list_input_libraries()[0]["name"], "PlanRVA")
        self.assertEqual(self.workspace.list_templates()[0]["name"], "PlanRVA")

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

    def test_hypercube_metadata_migrates_active_archived_and_mixed_projects(self):
        active = self.workspace.projects / "legacy-active" / "project.json"
        archived = self.workspace.removed_projects / "legacy-archived" / "project.json"
        base = {
            "id": "legacy-active", "name": "Legacy", "updatedAt": "before",
            "variations": [{
                "id": "variation-one", "name": "Case", "overlays": [],
                "parameterSweep": {"sweepId": "legacy-group", "caseIndex": 1, "values": []},
            }],
            "parameterSweeps": [
                {"id": "existing-group", "name": "Legacy duplicate", "scenarioIds": ["variation-one"]},
                {"id": "legacy-group", "name": "Legacy group", "scenarioIds": ["variation-one"]},
            ],
            "hypercubes": [
                {"id": "existing-group", "name": "Current wins", "scenarioIds": ["variation-one"]},
            ],
            "resultLinks": [{"datastoreId": "result-one", "variationId": "variation-one"}],
        }
        write(active, json.dumps(base))
        archived_project = {**base, "id": "legacy-archived", "archivedAt": "2026-01-01T00:00:00+00:00", "purgeAfter": "2099-01-01T00:00:00+00:00"}
        write(archived, json.dumps(archived_project))

        Workspace(self.workspace.root)

        for path in (active, archived):
            migrated = read_json(path, {})
            self.assertNotIn("parameterSweeps", migrated)
            self.assertEqual([item["id"] for item in migrated["hypercubes"]], ["existing-group", "legacy-group"])
            self.assertEqual(migrated["hypercubes"][0]["name"], "Current wins")
            metadata = migrated["variations"][0]
            self.assertNotIn("parameterSweep", metadata)
            self.assertEqual(metadata["hypercube"]["hypercubeId"], "legacy-group")
            self.assertNotIn("sweepId", metadata["hypercube"])
            self.assertEqual(migrated["resultLinks"][0]["datastoreId"], "result-one")
    def test_completed_v2_workspace_keeps_regenerated_root_runtime_files(self):
        workspace_root = self.root / "v2-runtime-files"
        first = Workspace(workspace_root)
        legacy_profile = first.internal / "legacy" / ".Rprofile"
        write(legacy_profile, "# archived pre-migration profile\n")
        root_profile = workspace_root / ".Rprofile"
        write(root_profile, "# current runtime profile\n")
        write(first.internal / "migration-v2.json", json.dumps({"version": 2, "state": "running"}))

        reopened = Workspace(workspace_root)

        self.assertEqual(root_profile.read_text(encoding="utf-8"), "# current runtime profile\n")
        self.assertEqual(legacy_profile.read_text(encoding="utf-8"), "# archived pre-migration profile\n")
        self.assertEqual(read_json(reopened.internal / "migration-v2.json", {})["state"], "complete")

    def test_workspace_defaults_must_reference_installed_assets(self):
        with self.assertRaises(WorkspaceError):
            self.workspace.update_settings({"defaultTemplateId": "missing"})
        self.workspace.copy_input_library(self.library_source)
        template = self.workspace.import_template(self.model_source, "Test MM")
        with self.assertRaisesRegex(WorkspaceError, "not linked"):
            self.workspace.update_settings({"defaultInputLibraryId": "Plan"})
        pair_assets(self.workspace, "Plan", template["id"])
        settings = self.workspace.update_settings({"defaultTemplateId": template["id"], "defaultInputLibraryId": "Plan"})
        self.assertEqual(settings["defaultTemplateId"], template["id"])
        settings = self.workspace.update_settings({"checkVisionEvalUpdates": False})
        self.assertFalse(settings["updateChecks"]["automatic"])
        self.assertNotIn("checkVisionEvalUpdates", settings)

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
        template = self.workspace.import_template(self.model_source, "Test MM")
        pair_assets(self.workspace, "Plan", template["id"])
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
        pair_assets(self.workspace, "Plan", template["id"])
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

    def test_project_resolves_paired_template_and_rejects_legacy_mismatch(self):
        self.workspace.copy_input_library(self.library_source)
        template = self.workspace.import_template(self.model_source, "Test MM")
        pair_assets(self.workspace, "Plan", template["id"])
        project = self.workspace.create_project({
            "name": "Automatic template", "inputLibraryId": "Plan",
            "baseline": {"strategy": "fresh"}, "variations": [],
        })
        self.assertEqual(project["template"]["id"], template["id"])
        with self.assertRaisesRegex(WorkspaceError, "not paired"):
            self.workspace.create_project({
                "name": "Wrong template", "inputLibraryId": "Plan", "templateId": "template-wrong",
                "baseline": {"strategy": "fresh"}, "variations": [],
            })

    def test_project_types_are_stored_and_hypercube_projects_reject_manual_edits(self):
        self.workspace.copy_input_library(self.library_source)
        template = self.workspace.import_template(self.model_source, "Test MM")
        pair_assets(self.workspace, "Plan", template["id"])
        standard = self.workspace.create_project({
            "name": "Standard", "inputLibraryId": "Plan", "projectType": "standard",
            "baseline": {"strategy": "fresh"}, "variations": [],
        })
        hypercube = self.workspace.create_project({
            "name": "Matrix", "inputLibraryId": "Plan", "projectType": "hypercube",
            "baseline": {"strategy": "fresh"}, "variations": [],
        })
        self.assertEqual(standard["projectType"], "standard")
        self.assertEqual(hypercube["projectType"], "hypercube")
        with self.assertRaisesRegex(WorkspaceError, "only generated matrix cases"):
            self.workspace.add_variation(hypercube["id"], "Manual")
        with self.assertRaisesRegex(WorkspaceError, "without ordinary scenarios"):
            self.workspace.create_project({
                "name": "Invalid matrix", "inputLibraryId": "Plan", "projectType": "hypercube",
                "baseline": {"strategy": "fresh"}, "variations": [{"name": "Manual"}],
            })

    def test_scenario_copy_rejects_hypercube_destination_and_exports_cases_as_standard(self):
        template, source = self.setup_project()
        target = self.workspace.create_project({
            "name": "Matrix target", "inputLibraryId": "Plan", "projectType": "hypercube",
            "baseline": {"strategy": "fresh"}, "variations": [],
        })
        with self.assertRaisesRegex(WorkspaceError, "only generated matrix cases"):
            self.workspace.copy_variations(
                source["id"], [source["variations"][0]["id"]], target_project_id=target["id"],
            )
        exported = self.workspace.copy_variations(
            source["id"], [source["variations"][0]["id"]], new_project_name="Exported case",
        )
        self.assertEqual(exported["project"]["projectType"], "standard")

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
        pair_assets(self.workspace, "Plan", template["id"])
        project = self.workspace.create_project({
            "name": "Empty editor project", "templateId": template["id"], "inputLibraryId": "Plan",
            "baseline": {"strategy": "fresh"}, "variations": [],
        })
        self.assertEqual(project["variations"], [])
        scenario = self.workspace.add_variation(project["id"], "Scenario 1")
        self.workspace.delete_variation(project["id"], scenario["id"])
        _, updated = self.workspace.project(project["id"])
        self.assertEqual(updated["variations"], [])

    def test_scenario_removal_cascades_owned_terminal_artifacts(self):
        _, project = self.setup_project()
        scenario = project["variations"][0]
        self.workspace.save_overlay(
            project["id"], scenario["id"], "bzone_network_design.csv",
            "Geo,Year,D3\n101,2024,30\n101,2045,40\n",
        )
        run_id = "run-remove-scenario"
        model_path = self.workspace.models / run_id
        result_path = model_path / "results" / "Datastore"
        write(result_path / "DatastoreListing.Rda", "result fixture")
        write(self.workspace.runs / run_id / "run.log", "completed log")
        write(self.workspace.runs / run_id / "job.json", json.dumps({
            "id": run_id, "projectId": project["id"], "variationId": scenario["id"],
            "state": "succeeded", "modelPath": str(model_path), "batchId": "batch-remove",
        }))
        write(self.workspace.runs / "batch-remove.json", json.dumps({"id": "batch-remove", "jobIds": [run_id]}))
        record = self.workspace.register_datastore({
            "id": "result-remove-scenario", "path": str(result_path), "projectId": project["id"],
            "variationId": scenario["id"], "runId": run_id, "role": "scenario", "verification": "verified",
        })
        _, stored = self.workspace.project(project["id"])
        stored["runIds"] = [run_id]
        self.workspace.save_project(stored)

        impact = self.workspace.variation_deletion_impact(project["id"], scenario["id"])
        self.assertEqual((impact["files"], impact["terminalRuns"], impact["logs"], impact["results"]), (1, 1, 1, 1))
        self.assertGreater(impact["removableBytes"], 0)
        removed = self.workspace.delete_variation(project["id"], scenario["id"])

        self.assertEqual(removed["runsRemoved"], 1)
        self.assertEqual(removed["resultsRemoved"], 1)
        self.assertFalse((self.workspace.runs / run_id).exists())
        self.assertFalse(model_path.exists())
        self.assertFalse((self.workspace.runs / "batch-remove.json").exists())
        self.assertNotIn(record["id"], [item["id"] for item in self.workspace.catalog()["datastores"]])
        _, updated = self.workspace.project(project["id"])
        self.assertNotIn(run_id, updated["runIds"])
        self.assertNotIn(record["id"], updated["datastoreIds"])

    def test_scenario_removal_blocks_active_runs(self):
        _, project = self.setup_project()
        scenario = project["variations"][0]
        write(self.workspace.runs / "run-active-scenario" / "job.json", json.dumps({
            "id": "run-active-scenario", "projectId": project["id"],
            "variationId": scenario["id"], "state": "running",
        }))
        impact = self.workspace.variation_deletion_impact(project["id"], scenario["id"])
        self.assertTrue(impact["blocked"])
        with self.assertRaisesRegex(WorkspaceError, "active runs"):
            self.workspace.delete_variation(project["id"], scenario["id"])
        self.assertIn(scenario["id"], [item["id"] for item in self.workspace.project(project["id"])[1]["variations"]])

    def test_scenario_removal_retains_results_linked_by_another_project(self):
        template, project = self.setup_project()
        scenario = project["variations"][0]
        result_path = self.workspace.models / "run-shared-scenario" / "results" / "Datastore"
        write(result_path / "DatastoreListing.Rda", "shared fixture")
        record = self.workspace.register_datastore({
            "id": "result-shared-scenario", "path": str(result_path), "projectId": project["id"],
            "variationId": scenario["id"], "runId": "run-shared-scenario", "role": "scenario",
            "verification": "verified",
        })
        target = self.workspace.create_project({
            "name": "Linked result project", "templateId": template["id"], "inputLibraryId": "Plan",
            "baseline": {"strategy": "fresh"}, "variations": [{"name": "Linked scenario"}],
        })
        target["resultLinks"] = [{
            "datastoreId": record["id"], "variationId": target["variations"][0]["id"],
            "sourceProjectId": project["id"], "sourceVariationId": scenario["id"], "role": "scenario",
        }]
        self.workspace.save_project(target)

        impact = self.workspace.variation_deletion_impact(project["id"], scenario["id"])
        self.assertEqual(impact["retainedResults"], 1)
        removed = self.workspace.delete_variation(project["id"], scenario["id"])
        self.assertEqual(removed["resultsRetained"], 1)
        self.assertTrue(result_path.exists())
        retained = next(item for item in self.workspace.catalog()["datastores"] if item["id"] == record["id"])
        self.assertTrue(retained["sourceScenarioRemoved"])
        self.assertEqual(retained["sourceScenarioId"], scenario["id"])

    def test_project_copy_duplicates_design_but_not_runs_or_results(self):
        _, project = self.setup_project()
        source_variation = project["variations"][0]
        edited = "Geo,Year,D3\n101,2024,30\n101,2045,40\n"
        self.workspace.save_overlay(project["id"], source_variation["id"], "bzone_network_design.csv", edited)
        self.workspace.update_variation(
            project["id"], source_variation["id"],
            notes={"bzone_network_design.csv": "Hypercube source"}, scenario_note="Source note",
        )
        _, source = self.workspace.project(project["id"])
        source["runIds"] = ["run-source"]
        source["datastoreIds"] = ["result-source"]
        source["hypercubes"] = [{
            "id": "hypercube-source", "name": "Housing", "scenarioIds": [source_variation["id"]],
            "axes": [{"filename": "bzone_network_design.csv", "column": "D3"}],
        }]
        source["variations"][0]["hypercube"] = {"hypercubeId": "hypercube-source", "caseIndex": 1, "values": []}
        self.workspace.save_project(source)

        copied = self.workspace.copy_project(project["id"], "Policy test copy")
        self.assertNotEqual(copied["id"], project["id"])
        self.assertEqual(copied["runIds"], [])
        self.assertEqual(copied["datastoreIds"], [])
        self.assertEqual(copied["copiedFrom"]["projectId"], project["id"])
        self.assertNotEqual(copied["variations"][0]["id"], source_variation["id"])
        self.assertEqual(copied["hypercubes"][0]["scenarioIds"], [copied["variations"][0]["id"]])
        self.assertNotEqual(copied["hypercubes"][0]["id"], "hypercube-source")
        self.assertEqual(copied["variations"][0]["hypercube"]["hypercubeId"], copied["hypercubes"][0]["id"])

        copied_path, copied_overlay = self.workspace.input_file(
            "Plan", "bzone_network_design.csv", copied["id"], copied["variations"][0]["id"]
        )
        source_path, source_overlay = self.workspace.input_file(
            "Plan", "bzone_network_design.csv", project["id"], source_variation["id"]
        )
        self.assertTrue(copied_overlay and source_overlay)
        self.assertEqual(copied_path.read_text(encoding="utf-8"), edited)
        self.assertNotEqual(copied_path, source_path)
        copied_path.write_text(edited.replace("40", "99"), encoding="utf-8")
        self.assertIn("40", source_path.read_text(encoding="utf-8"))

    def test_project_copy_failure_leaves_no_partial_project(self):
        _, project = self.setup_project()
        variation = project["variations"][0]
        _, source = self.workspace.project(project["id"])
        source["variations"][0]["overlays"] = [{
            "fileName": "bzone_network_design.csv",
            "path": str(self.workspace.projects / project["id"] / "overlays" / variation["id"] / "missing.csv"),
        }]
        self.workspace.save_project(source)
        before = {item["id"] for item in self.workspace.list_projects()}
        with self.assertRaisesRegex(WorkspaceError, "missing"):
            self.workspace.copy_project(project["id"], "Broken copy")
        self.assertEqual({item["id"] for item in self.workspace.list_projects()}, before)

    def test_project_copy_rejects_unfinished_runs_and_reserves_source(self):
        _, project = self.setup_project()
        variation = project["variations"][0]
        job_path = self.workspace.runs / "run-busy-project-copy" / "job.json"
        for run_state in ("waiting", "preparing", "running", "exporting", "stopping"):
            with self.subTest(run_state=run_state):
                write(job_path, json.dumps({
                    "id": "run-busy-project-copy", "projectId": project["id"],
                    "variationId": variation["id"], "variationName": variation["name"], "state": run_state,
                }))
                with self.assertRaisesRegex(WorkspaceError, "Please wait until every run"):
                    self.workspace.copy_project(project["id"], "Busy project copy")

        write(job_path, json.dumps({
            "id": "run-busy-project-copy", "projectId": project["id"],
            "variationId": variation["id"], "variationName": variation["name"], "state": "succeeded",
        }))
        reservation = self.workspace.reserve_project_copy(project["id"])
        try:
            with self.assertRaisesRegex(WorkspaceError, "project copy"):
                self.workspace.assert_run_start_allowed(project["id"], [variation["id"]])
        finally:
            self.workspace.release_copy_reservation(reservation)

    def test_project_copy_creates_independent_results_without_copying_runs(self):
        _, project = self.setup_project()
        variation = project["variations"][0]
        result_root = self.workspace.models / "run-shared-copy" / "results" / "Datastore"
        write(result_root / "DatastoreListing.Rda", "fixture")
        datastore = self.workspace.register_datastore({
            "id": "result-shared-copy", "label": "Transit result", "path": str(result_root),
            "projectId": project["id"], "variationId": variation["id"], "variationName": variation["name"],
            "role": "scenario", "verification": "verified", "runId": "run-shared-copy",
        })
        copied = self.workspace.copy_project(project["id"], "Result-linked copy", True)
        self.assertEqual(copied["runIds"], [])
        self.assertEqual(len(copied["datastoreIds"]), 1)
        self.assertNotIn("resultLinks", copied)
        copied_record = next(item for item in self.workspace.catalog()["datastores"] if item["id"] == copied["datastoreIds"][0])
        self.assertNotEqual(copied_record["id"], datastore["id"])
        self.assertEqual(copied_record["variationId"], copied["variations"][0]["id"])
        self.assertEqual(copied_record["copiedFrom"]["datastoreId"], datastore["id"])
        self.assertTrue(Path(copied_record["path"]).is_dir())
        self.assertTrue(result_root.is_dir())
        copied_path = Path(copied_record["path"])
        self.workspace.remove_project(project["id"])
        self.workspace.purge_project(project["id"])
        self.assertFalse(result_root.exists())
        self.assertTrue(copied_path.is_dir())
        self.assertIn(copied_record["id"], [item["id"] for item in self.workspace.catalog()["datastores"]])

    def test_atomic_file_note_update_is_independent_of_overlays(self):
        _, project = self.setup_project()
        variation = project["variations"][0]
        self.workspace.update_variation(
            project["id"], variation["id"], notes={"existing.csv": "Keep me"},
            file_note={"filename": "bzone_network_design.csv", "text": "Autosaved note"},
        )
        _, saved = self.workspace.project(project["id"])
        updated = next(item for item in saved["variations"] if item["id"] == variation["id"])
        self.assertEqual(updated["notes"], {"existing.csv": "Keep me", "bzone_network_design.csv": "Autosaved note"})
        self.assertEqual(updated["overlays"], [])

        self.workspace.update_variation(
            project["id"], variation["id"],
            file_note={"filename": "bzone_network_design.csv", "text": ""},
        )
        updated = next(item for item in self.workspace.project(project["id"])[1]["variations"] if item["id"] == variation["id"])
        self.assertEqual(updated["notes"], {"existing.csv": "Keep me"})
        with self.assertRaisesRegex(WorkspaceError, "basename"):
            self.workspace.update_variation(
                project["id"], variation["id"], file_note={"filename": "../outside.csv", "text": "No"},
            )

    def test_result_copy_cancellation_removes_staging_and_does_not_publish_project(self):
        _, project = self.setup_project()
        variation = project["variations"][0]
        result_root = self.workspace.models / "run-cancel-copy" / "results" / "Datastore"
        write(result_root / "DatastoreListing.Rda", "fixture")
        self.workspace.register_datastore({
            "id": "result-cancel-copy", "path": str(result_root), "projectId": project["id"],
            "variationId": variation["id"], "role": "scenario", "verification": "verified",
        })
        before = {item["id"] for item in self.workspace.list_projects()}
        with self.assertRaisesRegex(Exception, "cancelled"):
            self.workspace.copy_project(project["id"], "Cancelled copy", cancelled=lambda: True)
        self.assertEqual(before, {item["id"] for item in self.workspace.list_projects()})
        self.assertFalse(any(path.name.startswith("project-copy-") for path in (self.workspace.internal / "staging").iterdir()))

    def test_scenarios_copy_to_existing_or_new_projects_with_optional_results(self):
        template, source = self.setup_project()
        variation = source["variations"][0]
        edited = "Geo,Year,D3\n101,2024,30\n101,2045,40\n"
        self.workspace.save_overlay(source["id"], variation["id"], "bzone_network_design.csv", edited)
        self.workspace.update_variation(
            source["id"], variation["id"], scenario_note="Copied policy",
            file_note={"filename": "bzone_network_design.csv", "text": "Copied file note"},
        )
        result_root = self.workspace.models / "run-scenario-copy" / "results" / "Datastore"
        write(result_root / "DatastoreListing.Rda", "fixture")
        self.workspace.register_datastore({
            "id": "result-scenario-copy", "label": "Scenario result", "path": str(result_root),
            "projectId": source["id"], "variationId": variation["id"], "variationName": variation["name"],
            "role": "scenario", "verification": "verified", "runId": "run-scenario-copy",
        })
        target = self.workspace.create_project({
            "name": "Existing target", "templateId": template["id"], "inputLibraryId": "Plan",
            "baseline": {"strategy": "fresh"}, "variations": [{"name": variation["name"]}],
        })
        result = self.workspace.copy_variations(
            source["id"], [variation["id"]], target_project_id=target["id"], include_results=True,
        )
        copied = result["variations"][0]
        self.assertEqual(copied["name"], f"{variation['name']} (copy)")
        self.assertNotIn("hypercube", copied)
        copied_path, overlay = self.workspace.input_file("Plan", "bzone_network_design.csv", target["id"], copied["id"])
        self.assertTrue(overlay)
        self.assertEqual(copied_path.read_text(encoding="utf-8"), edited)
        self.assertEqual(copied["scenarioNote"], "Copied policy")
        self.assertEqual(copied["notes"]["bzone_network_design.csv"], "Copied file note")
        self.workspace.update_variation(
            target["id"], copied["id"], file_note={"filename": "bzone_network_design.csv", "text": "Independent copy"},
        )
        source_variation = next(item for item in self.workspace.project(source["id"])[1]["variations"] if item["id"] == variation["id"])
        self.assertEqual(source_variation["notes"]["bzone_network_design.csv"], "Copied file note")
        copied_record = next(item for item in self.workspace.catalog()["datastores"] if item["id"] in result["project"]["datastoreIds"])
        self.assertEqual(copied_record["variationId"], copied["id"])
        self.assertEqual(copied_record["variationName"], copied["name"])
        self.assertEqual(copied_record["label"], f"Existing target — {copied['name']}")
        self.assertNotEqual(Path(copied_record["path"]), result_root)

        second = self.workspace.copy_variations(
            source["id"], [variation["id"]], target_project_id=target["id"], include_results=False,
        )
        self.assertEqual(second["variations"][0]["name"], f"{variation['name']} (copy 2)")

        created = self.workspace.copy_variations(source["id"], [variation["id"]], new_project_name="Selected scenarios")
        self.assertTrue(created["createdProject"])
        self.assertEqual(created["project"]["template"]["fingerprint"], source["template"]["fingerprint"])
        self.assertEqual(created["project"]["baseline"], source["baseline"])
        self.assertNotIn("resultLinks", created["project"])
        self.assertEqual(created["variations"][0]["name"], variation["name"])
        self.assertEqual(created["variations"][0]["scenarioNote"], "Copied policy")
        self.assertEqual(created["variations"][0]["notes"]["bzone_network_design.csv"], "Copied file note")

    def test_edit_provenance_survives_scenario_duplication(self):
        _, project = self.setup_project()
        source = project["variations"][0]
        operations = [
            {
                "operationId": "first-preserved",
                "columns": ["D3"], "operation": "percent", "value": 25,
                "year": "2045", "allLocations": True,
                "source": "batch", "batchId": "batch-preserved",
            },
            {
                "operationId": "second-preserved",
                "columns": ["D3"], "operation": "add", "value": 1,
                "year": "2045", "allLocations": True,
                "source": "single_file",
            },
        ]
        self.workspace.save_overlay(
            project["id"], source["id"], "bzone_network_design.csv",
            "Geo,Year,D3\n101,2024,3\n101,2045,5\n", operations,
        )
        duplicate = self.workspace.add_variation(project["id"], "Duplicated", source["id"])
        self.assertEqual(duplicate["overlays"][0]["editOperations"], operations)

        target = self.workspace.create_project({
            "name": "Copy target", "templateId": project["template"]["id"],
            "inputLibraryId": project["inputLibrary"]["id"],
            "baseline": {"strategy": "fresh"}, "variations": [],
        })
        copied = self.workspace.copy_variations(
            project["id"], [source["id"]], target_project_id=target["id"], include_results=False,
        )["variations"][0]
        self.assertEqual(copied["overlays"][0]["editOperations"], operations)

    def test_scenario_copy_blocks_selected_active_runs_atomically(self):
        template, source = self.setup_project()
        first = source["variations"][0]
        second = self.workspace.add_variation(source["id"], "Running scenario")
        target = self.workspace.create_project({
            "name": "Idle target", "templateId": template["id"], "inputLibraryId": "Plan",
            "baseline": {"strategy": "fresh"}, "variations": [],
        })
        job_path = self.workspace.runs / "run-copy-guard" / "job.json"
        for run_state in ("waiting", "preparing", "running", "exporting", "stopping"):
            with self.subTest(run_state=run_state):
                write(job_path, json.dumps({
                    "id": "run-copy-guard", "projectId": source["id"],
                    "variationId": second["id"], "variationName": second["name"], "state": run_state,
                }))
                with self.assertRaisesRegex(WorkspaceError, rf"Running scenario \({run_state}\)"):
                    self.workspace.copy_variations(
                        source["id"], [first["id"], second["id"]], target_project_id=target["id"],
                    )
                self.assertEqual(self.workspace.project(target["id"])[1]["variations"], [])

        manager = CopyOperationManager(self.workspace)
        with self.assertRaisesRegex(WorkspaceError, "Running scenario"):
            manager.start_variations({
                "sourceProjectId": source["id"], "variationIds": [first["id"], second["id"]],
                "destination": {"projectId": target["id"]},
            })
        self.assertEqual(manager.operations, {})

    def test_scenario_copy_allows_terminal_run_states(self):
        _, source = self.setup_project()
        variation = source["variations"][0]
        job_path = self.workspace.runs / "run-copy-terminal" / "job.json"
        for run_state in ("completed", "failed", "cancelled", "stopped"):
            with self.subTest(run_state=run_state):
                write(job_path, json.dumps({
                    "id": "run-copy-terminal", "projectId": source["id"],
                    "variationId": variation["id"], "variationName": variation["name"], "state": run_state,
                }))
                self.workspace.assert_variations_copyable(source["id"], [variation["id"]])

    def test_scenario_copy_rejects_busy_destination_project_atomically(self):
        template, source = self.setup_project()
        variation = source["variations"][0]
        target = self.workspace.create_project({
            "name": "Busy target", "templateId": template["id"], "inputLibraryId": "Plan",
            "baseline": {"strategy": "fresh"}, "variations": [],
        })
        job_path = self.workspace.runs / "run-busy-target" / "job.json"
        for run_state in ("waiting", "preparing", "running", "exporting", "stopping"):
            with self.subTest(run_state=run_state):
                write(job_path, json.dumps({
                    "id": "run-busy-target", "projectId": target["id"],
                    "variationId": "other", "variationName": "Other", "state": run_state,
                }))
                with self.assertRaisesRegex(WorkspaceError, "Please wait until every run"):
                    self.workspace.copy_variations(
                        source["id"], [variation["id"]], target_project_id=target["id"],
                    )
                self.assertEqual(self.workspace.project(target["id"])[1]["variations"], [])

    def test_copy_reservation_blocks_conflicting_run_start(self):
        template, source = self.setup_project()
        variation = source["variations"][0]
        target = self.workspace.create_project({
            "name": "Reserved target", "templateId": template["id"], "inputLibraryId": "Plan",
            "baseline": {"strategy": "fresh"}, "variations": [],
        })
        reservation = self.workspace.reserve_variation_copy(source["id"], [variation["id"]], target["id"])
        try:
            with self.assertRaisesRegex(WorkspaceError, "selected scenario copy"):
                self.workspace.assert_run_start_allowed(source["id"], [variation["id"]])
            with self.assertRaisesRegex(WorkspaceError, "copy into this project"):
                self.workspace.assert_run_start_allowed(target["id"], [])
        finally:
            self.workspace.release_copy_reservation(reservation)

    def test_scenario_copy_rejects_incompatible_target_without_partial_changes(self):
        template, source = self.setup_project()
        variation = source["variations"][0]
        other_library = self.root / "other-library" / "Other"
        write(other_library / "bzone_network_design.csv", "Geo,Year,D3\n101,2024,8\n")
        write(other_library / "model_parameters.json", "[]\n")
        self.workspace.copy_input_library(other_library)
        pair_assets(self.workspace, "Other", template["id"], "other-model-bundle")
        target = self.workspace.create_project({
            "name": "Incompatible target", "templateId": template["id"], "inputLibraryId": "Other",
            "baseline": {"strategy": "fresh"}, "variations": [],
        })
        with self.assertRaisesRegex(WorkspaceError, "Input Library"):
            self.workspace.copy_variations(source["id"], [variation["id"]], target_project_id=target["id"])
        self.assertEqual(self.workspace.project(target["id"])[1]["variations"], [])

    def test_scenario_copy_missing_overlay_leaves_target_unchanged(self):
        template, source = self.setup_project()
        variation = source["variations"][0]
        _, source_state = self.workspace.project(source["id"])
        source_state["variations"][0]["overlays"] = [{
            "fileName": "bzone_network_design.csv",
            "path": str(self.workspace.projects / source["id"] / "overlays" / variation["id"] / "missing.csv"),
        }]
        self.workspace.save_project(source_state)
        target = self.workspace.create_project({
            "name": "Atomic target", "templateId": template["id"], "inputLibraryId": "Plan",
            "baseline": {"strategy": "fresh"}, "variations": [],
        })
        with self.assertRaisesRegex(WorkspaceError, "missing"):
            self.workspace.copy_variations(source["id"], [variation["id"]], target_project_id=target["id"])
        self.assertEqual(self.workspace.project(target["id"])[1]["variations"], [])
        self.assertFalse(any(path.name.startswith(f".{target['id']}.") for path in self.workspace.projects.iterdir()))

    def test_linked_result_survives_source_purge_then_cleans_up_after_unlink(self):
        _, source = self.setup_project()
        variation = source["variations"][0]
        result_root = self.workspace.models / "run-retained-link" / "results" / "Datastore"
        write(result_root / "DatastoreListing.Rda", "fixture")
        datastore = self.workspace.register_datastore({
            "id": "result-retained-link", "label": "Retained result", "path": str(result_root),
            "projectId": source["id"], "variationId": variation["id"], "role": "scenario",
            "verification": "verified", "runId": "run-retained-link",
        })
        _, template = self.workspace.template(source["template"]["id"])
        copied = self.workspace.create_project({
            "name": "Retains result", "templateId": template["id"], "inputLibraryId": "Plan",
            "baseline": {"strategy": "fresh"}, "variations": [{"name": "Linked"}],
        })
        copied["resultLinks"] = [{
            "datastoreId": datastore["id"], "variationId": copied["variations"][0]["id"],
            "sourceProjectId": source["id"], "sourceVariationId": variation["id"], "role": "scenario",
        }]
        self.workspace.save_project(copied)
        self.workspace.remove_project(source["id"])
        purged = self.workspace.purge_project(source["id"])
        self.assertIn(datastore["id"], purged["retainedDatastoreIds"])
        self.assertIn(datastore["id"], [item["id"] for item in self.workspace.catalog(False)["datastores"]])
        self.workspace.unlink_result(copied["id"], datastore["id"])
        self.assertNotIn(datastore["id"], [item["id"] for item in self.workspace.catalog()["datastores"]])
        self.assertFalse((self.workspace.models / "run-retained-link").exists())

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

    def test_project_names_are_unique_across_active_and_archived_projects(self):
        template, project = self.setup_project()
        payload = {
            "name": "  policy   TEST ", "templateId": template["id"], "inputLibraryId": "Plan",
            "baseline": {"strategy": "fresh"}, "variations": [],
        }
        with self.assertRaisesRegex(WorkspaceError, "unique"):
            self.workspace.create_project(payload)
        self.workspace.remove_project(project["id"])
        with self.assertRaisesRegex(WorkspaceError, "unique"):
            self.workspace.create_project(payload)

    def test_reset_actions_block_active_runs_and_wipe_preserves_imported_results(self):
        _, project = self.setup_project()
        write(self.workspace.runs / "run-active" / "job.json", json.dumps({"id": "run-active", "state": "waiting"}))
        with self.assertRaisesRegex(WorkspaceError, "active and waiting"):
            self.workspace.archive_all_projects()
        (self.workspace.runs / "run-active" / "job.json").unlink()

        imported_root = self.workspace.models / "imported-result" / "Datastore"
        write(imported_root / "DatastoreListing.Rda", "fixture")
        imported = self.workspace.register_datastore({
            "id": "standalone-import", "label": "Standalone", "path": str(imported_root),
            "role": "imported", "verification": "verified",
        })
        with self.assertRaisesRegex(WorkspaceError, "DELETE ALL PROJECTS"):
            self.workspace.wipe_project_data("wrong")
        result = self.workspace.wipe_project_data("DELETE ALL PROJECTS")
        self.assertIn(project["id"], result["wipedProjects"])
        self.assertTrue(imported_root.is_dir())
        self.assertIn(imported["id"], [item["id"] for item in self.workspace.catalog()["datastores"]])

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
            "templateFingerprint": source_project["template"]["fingerprint"],
            "inputLibraryFingerprint": source_project["inputLibrary"]["fingerprint"],
            "role": "baseline", "verification": "verified",
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

    def test_display_catalog_resolves_current_names_without_rewriting_provenance(self):
        template, project = self.setup_project()
        variation = project["variations"][0]
        result_root = self.workspace.models / "run-display-names" / "results" / "Datastore"
        write(result_root / "DatastoreListing.Rda", "fixture")
        self.workspace.register_datastore({
            "id": "result-display-names", "label": "Policy test — Transit",
            "projectId": project["id"], "projectName": project["name"],
            "variationId": variation["id"], "variationName": variation["name"],
            "templateId": template["id"], "path": str(result_root),
            "role": "scenario", "verification": "verified",
        })
        self.workspace.update_project(project["id"], "Current project")
        self.workspace.update_variation(project["id"], variation["id"], name="Current scenario")

        stored = self.workspace.catalog()["datastores"][0]
        displayed = self.workspace.display_catalog()["datastores"][0]
        self.assertEqual(stored["label"], "Policy test — Transit")
        self.assertEqual(stored["projectName"], "Policy test")
        self.assertEqual(stored["variationName"], "Transit")
        self.assertEqual(displayed["displayProjectName"], "Current project")
        self.assertEqual(displayed["displayVariationName"], "Current scenario")
        self.assertEqual(displayed["displayLabel"], "Current project — Current scenario")
        self.assertEqual(displayed["packageDisplayName"], "Plan")

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
        self.assertEqual(file_review["auditColumns"], ["D3"])
        self.assertEqual(file_review["auditRowsShown"], 1)
        self.assertFalse(file_review["auditTruncated"])
        self.assertEqual(file_review["auditRows"][0]["row"], 2)
        self.assertEqual(file_review["auditRows"][0]["cells"], [{"column": "D3", "before": "3", "after": "30"}])

    def test_review_changed_row_audit_keeps_multi_cell_rows_together(self):
        _, project = self.setup_project()
        scenario = project["variations"][0]
        library = self.workspace.input_library / "Plan"
        write(library / "azone_audit.csv", "Geo,Year,Jobs,Cost\nRichmond City,2045,100,8\nHenrico County,2045,50,4\n")
        self.workspace.save_overlay(
            project["id"], scenario["id"], "azone_audit.csv",
            "Geo,Year,Jobs,Cost\nRichmond City,2045,125,10\nHenrico County,2045,50,5\n",
        )

        file_review = self.workspace.review_project(project["id"], change_limit=1)["scenarios"][0]["files"][0]

        self.assertEqual(file_review["changedRows"], 2)
        self.assertEqual(file_review["changedCells"], 3)
        self.assertEqual(file_review["auditRowsShown"], 1)
        self.assertTrue(file_review["auditTruncated"])
        self.assertEqual(file_review["auditColumns"], ["Jobs", "Cost"])
        self.assertEqual(len(file_review["auditRows"][0]["cells"]), 2)

    def test_review_generates_structured_and_fallback_automatic_summaries(self):
        _, project = self.setup_project()
        scenario = project["variations"][0]
        edited = "Geo,Year,D3\n101,2024,3\n101,2045,5\n"
        self.workspace.save_overlay(
            project["id"], scenario["id"], "bzone_network_design.csv", edited,
            [{"columns": ["D3"], "operation": "percent", "value": 25, "year": "2045", "allLocations": True}],
        )
        review = self.workspace.review_project(project["id"])
        summary = review["scenarios"][0]["automaticSummary"]
        self.assertIn("bzone_network_design.csv — all variables: increased 25%", summary)
        self.assertIn("All Bzone (1)", summary)
        self.assertEqual(
            review["scenarios"][0]["automaticSummaryHeadline"],
            "Increased 25% across 1 file · all locations",
        )
        details = review["scenarios"][0]["files"][0]["automaticSummaryDetails"]
        self.assertTrue(details["validated"])
        self.assertTrue(details["allVariables"])
        self.assertEqual(details["groups"][0]["change"], "Increased 25%")
        self.assertNotIn("2045", details["groups"][0]["locations"]["text"])

        self.workspace.save_overlay(
            project["id"], scenario["id"], "bzone_network_design.csv",
            "Geo,Year,D3\n101,2024,3\n101,2045,6\n",
        )
        stale_operation = self.workspace.review_project(project["id"])["scenarios"][0]["automaticSummary"]
        self.assertNotIn("increased 25%", stale_operation)
        self.assertIn("1 value changed", stale_operation)

        self.workspace.save_overlay(project["id"], scenario["id"], "bzone_network_design.csv", edited, [])
        fallback = self.workspace.review_project(project["id"])["scenarios"][0]["automaticSummary"]
        self.assertIn("1 value changed", fallback)
        self.assertIn("All Bzone (1)", fallback)

    def test_review_validates_categorical_and_linked_share_operations(self):
        _, project = self.setup_project()
        scenario = project["variations"][0]
        library = self.workspace.input_library / "Plan"
        write(library / "bzone_carsvc_availability.csv", "Geo,Year,CarSvcLevel\n101,2024,High\n101,2045,High\n")
        self.workspace.save_overlay(project["id"], scenario["id"], "bzone_carsvc_availability.csv", "Geo,Year,CarSvcLevel\n101,2024,High\n101,2045,Low\n", [{"columns": ["CarSvcLevel"], "operation": "set", "value": "Low", "valueType": "categorical", "year": "2045", "allLocations": True}])
        categorical = self.workspace.review_project(project["id"])["scenarios"][0]["files"][0]
        self.assertIn("CarSvcLevel: set to Low", categorical["automaticSummary"])
        write(library / "shares.csv", "Geo,Year,ShareA,ShareB\n101,2045,0.5,0.5\n")
        operation = {"columns": ["ShareA", "ShareB"], "operation": "set", "valueType": "share_group", "groupId": "shares", "groupValues": {"ShareA": "0.25", "ShareB": "0.75"}, "value": {"ShareA": "0.25", "ShareB": "0.75"}, "year": "2045", "allLocations": True}
        self.workspace.save_overlay(project["id"], scenario["id"], "shares.csv", "Geo,Year,ShareA,ShareB\n101,2045,0.25,0.75\n", [operation])
        linked = next(item for item in self.workspace.review_project(project["id"])["scenarios"][0]["files"] if item["filename"] == "shares.csv")
        self.assertIn("set linked shares to", linked["automaticSummary"])

    def test_atomic_overlay_batch_rolls_back_every_file_on_commit_failure(self):
        _, project = self.setup_project()
        scenario = project["variations"][0]
        library = self.workspace.input_library / "Plan"
        write(library / "first.csv", "Geo,Year,Value\n101,2045,1\n")
        write(library / "second.csv", "Geo,Year,Value\n101,2045,2\n")
        real_replace = __import__("os").replace
        calls = 0
        def fail_second(source, target):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated commit failure")
            return real_replace(source, target)
        with patch("backend.workbench.workspace.os.replace", side_effect=fail_second):
            with self.assertRaisesRegex(OSError, "simulated commit failure"):
                self.workspace.save_overlays_atomic(project["id"], scenario["id"], [{"filename": "first.csv", "content": "Geo,Year,Value\n101,2045,3\n"}, {"filename": "second.csv", "content": "Geo,Year,Value\n101,2045,4\n"}])
        overlay_root = self.workspace.projects / project["id"] / "overlays" / scenario["id"]
        self.assertFalse((overlay_root / "first.csv").exists())
        self.assertFalse((overlay_root / "second.csv").exists())

    def test_review_rejects_structured_summary_with_wrong_location_metadata(self):
        _, project = self.setup_project()
        scenario = project["variations"][0]
        self.workspace.save_overlay(
            project["id"], scenario["id"], "bzone_network_design.csv",
            "Geo,Year,D3\n101,2024,3\n101,2045,5\n",
            [{"columns": ["D3"], "operation": "percent", "value": 25, "year": "2045", "allLocations": False, "locations": ["999"]}],
        )
        summary = self.workspace.review_project(project["id"])["scenarios"][0]["automaticSummary"]
        self.assertNotIn("increased 25%", summary)
        self.assertIn("1 value changed", summary)

    def test_review_summary_distinguishes_all_locations_from_richmond(self):
        _, project = self.setup_project()
        scenario = project["variations"][0]
        names = ["Charles City County", "Chesterfield County", "Goochland County", "Hanover County", "Henrico County", "New Kent County", "Powhatan County", "Richmond City"]
        library = self.workspace.input_library / "Plan"
        fuel_before = "Geo,Year,FuelCost.2024\n" + "".join(f"{name},2045,4\n" for name in names)
        fuel_after = "Geo,Year,FuelCost.2024\n" + "".join(f"{name},2045,5\n" for name in names)
        write(library / "azone_fuel_power_cost.csv", fuel_before)
        tax_before = "Geo,Year,FuelTax.2024\n" + "".join(f"{name},2045,8\n" for name in names)
        tax_after = "Geo,Year,FuelTax.2024\n" + "".join(f"{name},2045,{'10' if name == 'Richmond City' else '8'}\n" for name in names)
        write(library / "azone_veh_use_taxes.csv", tax_before)
        self.workspace.save_overlay(
            project["id"], scenario["id"], "azone_fuel_power_cost.csv", fuel_after,
            [{"columns": ["FuelCost.2024"], "operation": "percent", "value": 25, "year": "2045", "allLocations": False, "locations": names}],
        )
        self.workspace.save_overlay(
            project["id"], scenario["id"], "azone_veh_use_taxes.csv", tax_after,
            [{"columns": ["FuelTax.2024"], "operation": "percent", "value": 25, "year": "2045", "allLocations": False, "locations": ["Richmond City"]}],
        )
        review = self.workspace.review_project(project["id"])["scenarios"][0]
        self.assertEqual(review["automaticSummaryHeadline"], "Increased 25% across 2 files · location scope varies")
        details = [item["automaticSummary"] for item in review["files"]]
        self.assertTrue(any("All locations (8)" in item for item in details))
        self.assertTrue(any("Richmond City" in item for item in details))

    def test_review_all_variables_includes_validated_no_op_columns(self):
        _, project = self.setup_project()
        scenario = project["variations"][0]
        library = self.workspace.input_library / "Plan"
        write(library / "azone_counts.csv", "Geo,Year,Adults,Children\nRichmond City,2045,4,0\n")
        self.workspace.save_overlay(
            project["id"], scenario["id"], "azone_counts.csv",
            "Geo,Year,Adults,Children\nRichmond City,2045,5,0\n",
            [{"columns": ["Adults", "Children"], "operation": "percent", "value": 25, "year": "2045", "allLocations": True}],
        )
        file_review = self.workspace.review_project(project["id"])["scenarios"][0]["files"][0]
        details = file_review["automaticSummaryDetails"]
        self.assertTrue(details["validated"])
        self.assertTrue(details["allVariables"])
        self.assertTrue(details["groups"][0]["allVariables"])
        self.assertIn("all variables", file_review["automaticSummary"])
        self.assertNotIn("2045", file_review["automaticSummary"])

    def test_review_groups_different_variable_operations_and_lists_azone_names(self):
        _, project = self.setup_project()
        scenario = project["variations"][0]
        library = self.workspace.input_library / "Plan"
        before = "Geo,Year,Jobs,Cost\nHenrico County,2045,100,100\nRichmond City,2045,100,100\n"
        after = "Geo,Year,Jobs,Cost\nHenrico County,2045,100,125\nRichmond City,2045,110,100\n"
        write(library / "azone_policy.csv", before)
        self.workspace.save_overlay(
            project["id"], scenario["id"], "azone_policy.csv", after,
            [
                {"columns": ["Jobs"], "operation": "percent", "value": 10, "year": "2045", "allLocations": False, "locations": ["Richmond City"]},
                {"columns": ["Cost"], "operation": "percent", "value": 25, "year": "2045", "allLocations": False, "locations": ["Henrico County"]},
            ],
        )
        details = self.workspace.review_project(project["id"])["scenarios"][0]["files"][0]["automaticSummaryDetails"]
        self.assertTrue(details["validated"])
        self.assertEqual(len(details["groups"]), 2)
        groups = {group["variables"][0]: group for group in details["groups"]}
        self.assertEqual(groups["Jobs"]["change"], "Increased 10%")
        self.assertEqual(groups["Jobs"]["locations"]["text"], "Richmond City")
        self.assertEqual(groups["Cost"]["change"], "Increased 25%")
        self.assertEqual(groups["Cost"]["locations"]["text"], "Henrico County")

    def test_review_reports_batch_single_file_and_mixed_edit_provenance(self):
        _, project = self.setup_project()
        scenario = project["variations"][0]
        library = self.workspace.input_library / "Plan"
        write(library / "azone_policy.csv", "Geo,Year,Jobs,Cost\nRichmond City,2045,100,100\n")
        self.workspace.save_overlay(
            project["id"], scenario["id"], "bzone_network_design.csv",
            "Geo,Year,D3\n101,2024,3\n101,2045,5\n",
            [{
                "columns": ["D3"], "operation": "percent", "value": 25,
                "year": "2045", "allLocations": True,
                "source": "batch", "batchId": "batch-one",
            }],
        )
        self.workspace.save_overlay(
            project["id"], scenario["id"], "azone_policy.csv",
            "Geo,Year,Jobs,Cost\nRichmond City,2045,110,125\n",
            [
                {
                    "columns": ["Jobs"], "operation": "percent", "value": 10,
                    "year": "2045", "allLocations": True,
                    "source": "batch", "batchId": "batch-one",
                },
                {
                    "columns": ["Cost"], "operation": "percent", "value": 25,
                    "year": "2045", "allLocations": True,
                    "source": "single_file",
                },
            ],
        )

        review = self.workspace.review_project(project["id"])["scenarios"][0]
        by_name = {item["filename"]: item for item in review["files"]}
        self.assertEqual(by_name["bzone_network_design.csv"]["editSource"], "batch")
        self.assertEqual(by_name["azone_policy.csv"]["editSource"], "mixed")
        self.assertEqual(review["editSource"], "mixed")
        self.assertEqual(len(by_name["azone_policy.csv"]["automaticSummaryDetails"]["groups"]), 2)

    def test_review_does_not_guess_legacy_edit_provenance(self):
        _, project = self.setup_project()
        scenario = project["variations"][0]
        self.workspace.save_overlay(
            project["id"], scenario["id"], "bzone_network_design.csv",
            "Geo,Year,D3\n101,2024,3\n101,2045,5\n",
            [{"columns": ["D3"], "operation": "percent", "value": 25, "year": "2045", "allLocations": True}],
        )
        review = self.workspace.review_project(project["id"])["scenarios"][0]
        self.assertEqual(review["files"][0]["editSource"], "unavailable")
        self.assertEqual(review["editSource"], "unavailable")

    def test_review_uses_counts_instead_of_raw_ids_for_partial_bzones(self):
        _, project = self.setup_project()
        scenario = project["variations"][0]
        library = self.workspace.input_library / "Plan"
        before = "Geo,Year,Units\n101,2045,4\n102,2045,4\n103,2045,4\n104,2045,4\n"
        after = "Geo,Year,Units\n101,2045,5\n102,2045,5\n103,2045,5\n104,2045,4\n"
        write(library / "bzone_units.csv", before)
        self.workspace.save_overlay(
            project["id"], scenario["id"], "bzone_units.csv", after,
            [{"columns": ["Units"], "operation": "percent", "value": 25, "year": "2045", "allLocations": False, "locations": ["101", "102", "103"]}],
        )
        locations = self.workspace.review_project(project["id"])["scenarios"][0]["files"][0]["automaticSummaryDetails"]["groups"][0]["locations"]
        self.assertEqual(locations["text"], "3 of 4 Bzones")
        self.assertEqual(locations["names"], [])

    def test_review_preserves_all_location_scope_when_rounding_creates_a_no_op(self):
        _, project = self.setup_project()
        scenario = project["variations"][0]
        library = self.workspace.input_library / "Plan"
        before = "Geo,Year,Units\n101,2045,4\n102,2045,4\n103,2045,4\n104,2045,1\n"
        after = "Geo,Year,Units\n101,2045,5\n102,2045,5\n103,2045,5\n104,2045,1\n"
        write(library / "bzone_units.csv", before)
        self.workspace.save_overlay(
            project["id"], scenario["id"], "bzone_units.csv", after,
            [{"columns": ["Units"], "operation": "percent", "value": 25, "year": "2045", "allLocations": True}],
        )
        file_review = self.workspace.review_project(project["id"])["scenarios"][0]["files"][0]
        locations = file_review["automaticSummaryDetails"]["groups"][0]["locations"]
        self.assertEqual(locations["text"], "All Bzones (4)")
        self.assertEqual(locations["effectiveCount"], 3)
        self.assertEqual(locations["unchangedCount"], 1)
        self.assertEqual(locations["effectiveText"], "3 Bzones; 1 unchanged after rounding")
        self.assertIn("All Bzones (4)", file_review["automaticSummary"])
        self.assertIn("1 unchanged after rounding", file_review["automaticSummary"])

    def test_review_lists_repeated_rounded_operations_in_saved_order(self):
        _, project = self.setup_project()
        scenario = project["variations"][0]
        library = self.workspace.input_library / "Plan"
        write(library / "bzone_units.csv", "Geo,Year,Units\n101,2045,610\n")
        operations = [
            {
                "operationId": "first", "source": "batch", "batchId": "batch-one",
                "columns": ["Units"], "operation": "percent", "value": 25,
                "year": "2045", "allLocations": True,
                "rounding": {"precision": 2, "integerColumns": ["Units"]},
            },
            {
                "operationId": "second", "source": "single_file",
                "columns": ["Units"], "operation": "percent", "value": 25,
                "year": "2045", "allLocations": True,
                "rounding": {"precision": 2, "integerColumns": ["Units"]},
            },
        ]
        self.workspace.save_overlay(
            project["id"], scenario["id"], "bzone_units.csv",
            "Geo,Year,Units\n101,2045,954\n", operations,
        )

        file_review = self.workspace.review_project(project["id"])["scenarios"][0]["files"][0]
        details = file_review["automaticSummaryDetails"]
        self.assertTrue(details["validated"])
        self.assertTrue(details["ordered"])
        self.assertEqual([group["operationIndex"] for group in details["groups"]], [1, 2])
        self.assertEqual([group["change"] for group in details["groups"]], ["Increased 25%", "Increased 25%"])
        self.assertIn("applied in order", file_review["automaticSummary"])

    def test_review_baseline_operation_supersedes_same_scope_history(self):
        _, project = self.setup_project()
        scenario = project["variations"][0]
        library = self.workspace.input_library / "Plan"
        write(library / "bzone_units.csv", "Geo,Year,Units\n101,2045,100\n")
        operations = [
            {
                "operationId": "source-ten", "source": "batch", "batchId": "source-batch",
                "columns": ["Units"], "operation": "percent", "value": 10,
                "year": "2045", "allLocations": True, "basis": "current",
            },
            {
                "operationId": "replacement-twenty", "source": "batch", "batchId": "replacement-batch",
                "columns": ["Units"], "operation": "percent", "value": 20,
                "year": "2045", "allLocations": True, "basis": "baseline",
            },
        ]
        self.workspace.save_overlay(
            project["id"], scenario["id"], "bzone_units.csv",
            "Geo,Year,Units\n101,2045,120\n", operations,
        )

        details = self.workspace.review_project(project["id"])["scenarios"][0]["files"][0]["automaticSummaryDetails"]
        self.assertTrue(details["validated"])
        self.assertEqual(len(details["groups"]), 1)
        self.assertEqual(details["groups"][0]["change"], "Increased 20%")
        self.assertEqual(details["groups"][0]["basis"], "baseline")

    def test_review_baseline_operation_only_supersedes_its_effective_scope(self):
        _, project = self.setup_project()
        scenario = project["variations"][0]
        library = self.workspace.input_library / "Plan"
        write(library / "bzone_units.csv", "Geo,Year,Units\n101,2045,100\n102,2045,100\n")
        operations = [
            {
                "operationId": "source-ten", "source": "batch", "batchId": "source-batch",
                "columns": ["Units"], "operation": "percent", "value": 10,
                "year": "2045", "allLocations": True,
            },
            {
                "operationId": "replacement-twenty", "source": "single_file",
                "columns": ["Units"], "operation": "percent", "value": 20,
                "year": "2045", "allLocations": False, "locations": ["101"], "basis": "baseline",
            },
        ]
        self.workspace.save_overlay(
            project["id"], scenario["id"], "bzone_units.csv",
            "Geo,Year,Units\n101,2045,120\n102,2045,110\n", operations,
        )

        details = self.workspace.review_project(project["id"])["scenarios"][0]["files"][0]["automaticSummaryDetails"]
        self.assertTrue(details["validated"])
        self.assertEqual([group["change"] for group in details["groups"]], ["Increased 10%", "Increased 20%"])
        self.assertEqual(details["groups"][0]["locations"]["text"], "1 of 2 Bzones")
        self.assertEqual(details["groups"][1]["locations"]["text"], "1 of 2 Bzones")

    def test_review_keeps_valid_operations_before_other_saved_changes(self):
        _, project = self.setup_project()
        scenario = project["variations"][0]
        library = self.workspace.input_library / "Plan"
        write(library / "azone_policy.csv", "Geo,Year,Jobs,Cost\nRichmond City,2045,100,100\n")
        self.workspace.save_overlay(
            project["id"], scenario["id"], "azone_policy.csv",
            "Geo,Year,Jobs,Cost\nRichmond City,2045,125,130\n",
            [{
                "operationId": "jobs", "source": "single_file",
                "columns": ["Jobs"], "operation": "percent", "value": 25,
                "year": "2045", "allLocations": True,
                "rounding": {"precision": 2, "integerColumns": ["Jobs"]},
            }],
        )

        details = self.workspace.review_project(project["id"])["scenarios"][0]["files"][0]["automaticSummaryDetails"]
        self.assertFalse(details["validated"])
        self.assertEqual(details["groups"][0]["change"], "Increased 25%")
        self.assertTrue(details["groups"][1]["otherChanges"])
        self.assertEqual(details["groups"][1]["variables"], ["Cost"])

    def test_save_overlay_deduplicates_operation_ids_without_reordering(self):
        _, project = self.setup_project()
        scenario = project["variations"][0]
        operation = {
            "operationId": "same-submission", "source": "single_file",
            "columns": ["D3"], "operation": "percent", "value": 25,
            "year": "2045", "allLocations": True,
        }
        saved = self.workspace.save_overlay(
            project["id"], scenario["id"], "bzone_network_design.csv",
            "Geo,Year,D3\n101,2024,3\n101,2045,5\n", [operation, operation],
        )
        self.assertEqual([item["operationId"] for item in saved["editOperations"]], ["same-submission"])

    def test_execution_fingerprint_changes_with_inputs_but_not_notes_or_names(self):
        _, project = self.setup_project()
        scenario = project["variations"][0]
        original = self.workspace.scenario_input_fingerprint(project, scenario["id"])
        self.workspace.update_variation(project["id"], scenario["id"], scenario_note="Documentation only", name="Renamed")
        _, renamed = self.workspace.project(project["id"])
        self.assertEqual(original, self.workspace.scenario_input_fingerprint(renamed, scenario["id"]))
        self.workspace.save_overlay(
            project["id"], scenario["id"], "bzone_network_design.csv",
            "Geo,Year,D3\n101,2024,30\n101,2045,40\n",
        )
        _, edited = self.workspace.project(project["id"])
        self.assertNotEqual(original, self.workspace.scenario_input_fingerprint(edited, scenario["id"]))

    def test_legacy_result_backfills_fingerprints_from_preserved_prepared_inputs(self):
        _, project = self.setup_project()
        scenario = project["variations"][0]
        run_id = "run-legacy-fingerprint"
        prepared, _ = self.workspace.prepare_model(project["id"], scenario["id"], run_id)
        result_path = prepared / "results" / "Datastore"
        write(result_path / "DatastoreListing.Rda", "fixture")
        runtime_digest = "sha256:legacy-runtime"
        write(self.workspace.runs / run_id / "job.json", json.dumps({"id": run_id, "imageDigest": runtime_digest}))
        record = self.workspace.register_datastore({
            "id": "legacy-fingerprint-result", "path": str(result_path), "projectId": project["id"],
            "variationId": scenario["id"], "role": "scenario", "verification": "verified", "runId": run_id,
        })
        _, current = self.workspace.project(project["id"])
        self.assertEqual(self.workspace.result_reuse_status(current, record, scenario["id"], runtime_digest), "current")

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

    def test_existing_baseline_must_be_verified_and_exactly_compatible(self):
        self.workspace.copy_input_library(self.library_source)
        template = self.workspace.import_template(self.model_source, "Test MM")
        pair_assets(self.workspace, "Plan", template["id"])
        source = self.workspace.models / "legacy-import" / "results" / "Datastore"
        write(source / "DatastoreListing.Rda", "fixture")
        imported = self.workspace.register_datastore({
            "id": "legacy-imported-baseline",
            "label": "Old baseline",
            "path": str(source),
            "role": "imported",
            "source": "legacy",
        })
        with self.assertRaisesRegex(WorkspaceError, "verified completed baseline"):
            self.workspace.create_project({
                "name": "Imported baseline project", "templateId": template["id"], "inputLibraryId": "Plan",
                "baseline": {"strategy": "existing", "datastoreId": imported["id"]}, "variations": [{"name": "Change"}],
            })

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
