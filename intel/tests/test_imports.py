import json
import tempfile
import unittest
from pathlib import Path

from backend.workbench.server import WorkbenchApplication, handler_class


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class LegacyImportTests(unittest.TestCase):
    def test_v1_manifest_and_changed_inputs_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            resource_root = Path(__file__).resolve().parents[1] / "backend"
            public_root = Path(__file__).resolve().parents[1] / "public"
            app = WorkbenchApplication(root / "workspace", public_root, resource_root)
            library = root / "old-library" / "Plan"
            write(library / "input.csv", "Geo,Year,Value\n1,2045,10\n")
            app.workspace.copy_input_library(library.parent)
            model = root / "model"
            write(model / "visioneval.cnf", "ScriptsDir: scripts\nInputDir: inputs\nParamDir: defs\nGeoFile: geo.csv\nModelParamFile: model_parameters.json\nYears: [2045]\n")
            write(model / "scripts" / "run_model.R", "# run\n")
            write(model / "defs" / "geo.csv", "Azone,Bzone,Czone,Marea\nA,1,NA,M\n")
            write(model / "defs" / "units.csv", "Unit\n")
            write(model / "defs" / "deflators.csv", "Year\n2045\n")
            write(model / "inputs" / "input.csv", "Geo,Year,Value\n1,2045,10\n")
            template = app.workspace.import_template(model)
            legacy = root / "V1 Scenario"
            write(legacy / "Scenario A" / "inputs" / "input.csv", "Geo,Year,Value\n1,2045,25\n")
            write(legacy / "scenario_manifest.json", json.dumps({"version": 2, "projectName": "Legacy", "sims": [{"name": "Scenario A"}]}))
            handler = handler_class(app)
            project = handler._import_v1({"source": str(legacy), "templateId": template["id"], "inputLibraryId": "Plan", "baseline": {"strategy": "fresh"}})
            project_dir = app.workspace.projects / project["id"]
            self.assertTrue((project_dir / "legacy_scenario_manifest.json").is_file())
            self.assertEqual(project["legacyImport"]["manifestVersion"], 2)
            overlay = Path(project["variations"][0]["overlays"][0]["path"])
            self.assertIn(",25", overlay.read_text(encoding="utf-8"))

    def test_legacy_imported_result_remains_in_application_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            resource_root = Path(__file__).resolve().parents[1] / "backend"
            public_root = Path(__file__).resolve().parents[1] / "public"
            app = WorkbenchApplication(root / "workspace", public_root, resource_root)
            source = app.workspace.models / "legacy-import" / "Datastore"
            write(source / "DatastoreListing.Rda", "legacy source")
            imported = app.workspace.register_datastore({
                "id": "legacy-imported-result",
                "label": "Legacy result",
                "path": str(source),
                "role": "imported",
                "source": "legacy",
            })
            state = app.state()
            visible = next(item for item in state["catalog"] if item["id"] == imported["id"])
            self.assertEqual(visible["role"], "imported")
            self.assertFalse(hasattr(app, "remove_imported_datastore"))
            self.assertFalse(hasattr(app, "set_imported_datastore_hidden"))


if __name__ == "__main__":
    unittest.main()
