import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from backend.workbench.bundled_assets import BundledAssetService
from backend.workbench.explore import ExploreService
from backend.workbench.input_explanations import InputExplanationPackageService
from backend.workbench.model_packages import ModelPackageService
from backend.workbench.region_packages import RegionPackageService
from backend.workbench.region_builder import RegionBuilderService
from backend.workbench.server import WorkbenchApplication
from backend.workbench.workspace import Workspace, WorkspaceError


ROOT = Path(__file__).resolve().parents[1]


def file_sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def make_shared_map_package(path: Path) -> Path:
    source = ROOT / "resources/examples/planrva-mm/map-context"
    manifest = {"schemaVersion": 1, "type": "region-builder", "id": "virginia-mpo-regions", "name": "Virginia MPO Regional Data", "version": "2026.08.12.3", "coverage": "Virginia", "builder": {"kind": "mpo-bzone-crosswalk", "regionsPath": "data/regions.json", "crosswalkPath": "data/mpo_bzone_crosswalk.json", "localitiesPath": "data/virginia_county_equivalents_2020.txt"}, "comparisonMap": {"enabled": True, "jurisdictionLabel": "Virginia", "fullExtentLabel": "Virginia", "geographies": [{"id": "county", "label": "County / locality", "geometry": "azone", "identifier": "FIPS", "technicalLevel": "Azone"}, {"id": "bzone", "label": "Bzone", "geometry": "bzone", "identifier": "GEOID", "technicalLevel": "Bzone"}]}, "sourcesDocument": "SOURCES.md"}
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        prefix = "virginia-mpo-regions-2026.08.12.3"
        archive.writestr(f"{prefix}/workbench-package.json", json.dumps(manifest))
        archive.write(source / "virginia_mpo_regions.json", f"{prefix}/data/regions.json")
        archive.write(source / "virginia_mpo_bzone_crosswalk.json", f"{prefix}/data/mpo_bzone_crosswalk.json")
        archive.write(source / "virginia_county_equivalents_2020.txt", f"{prefix}/data/virginia_county_equivalents_2020.txt")
        archive.write(source / "SOURCES.md", f"{prefix}/SOURCES.md")
    return path


class BundledAssetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Workspace(Path(self.temp.name) / "workspace")
        self.service = BundledAssetService(self.workspace, ROOT / "backend")

    def tearDown(self):
        self.temp.cleanup()

    def make_explanation_package(self, package_id: str = "NC Explanations") -> Path:
        package = Path(self.temp.name) / package_id
        docs = package / "docs"
        docs.mkdir(parents=True)
        people = docs / "01_azone_people.csv.md"
        jobs = docs / "bzone_jobs.html"
        people.write_text(
            "# File 01_azone_people.csv\nMay 21, 2026\n## Definition\nNC guide text",
            encoding="utf-8",
        )
        jobs.write_text(
            "<script>alert('x')</script><h3>Jobs</h3><p onclick=\"bad()\">Job guide</p>",
            encoding="utf-8",
        )
        manifest = {
            "type": "input-explanations",
            "id": package_id,
            "name": "NC Input Explanations",
            "version": "1.0.0",
            "description": "North Carolina guide text.",
            "appliesTo": {"regionLabels": ["NC"]},
            "files": [
                {"path": "docs/01_azone_people.csv.md", "size": people.stat().st_size, "sha256": file_sha256(people)},
                {"path": "docs/bzone_jobs.html", "size": jobs.stat().st_size, "sha256": file_sha256(jobs)},
            ],
        }
        (package / "workbench-package.json").write_text(json.dumps(manifest), encoding="utf-8")
        return package

    def test_new_workspace_starts_empty_without_planrva_seed(self):
        result = self.service.seed_new_workspace()
        self.assertFalse(result["inputLibraryInstalled"])
        self.assertFalse(result["modelTemplateInstalled"])
        self.assertFalse((self.workspace.input_library / "PlanRVA MM").exists())
        self.assertFalse((self.workspace.templates / "template-planrva-mm-8f140cd4cb").exists())
        settings = self.workspace.settings()
        self.assertEqual(settings["defaultInputLibraryId"], "")
        self.assertEqual(settings["defaultTemplateId"], "")
        self.assertEqual(settings["defaultInputExplanationId"], "")

    def test_install_preserves_existing_assets_and_restores_only_missing_asset(self):
        self.service.install_planrva()
        library_file = self.workspace.input_library / "PlanRVA MM" / "bzone_employment.csv"
        library_file.write_text("user-modified\n", encoding="utf-8")
        template = self.workspace.templates / "template-planrva-mm-8f140cd4cb"
        shutil.rmtree(template)
        result = self.service.install_planrva()
        self.assertEqual(result["installed"], ["ModelTemplate"])
        self.assertEqual(result["preserved"], ["InputLibrary"])
        self.assertEqual(library_file.read_text(encoding="utf-8"), "user-modified\n")
        self.assertTrue((template / "visioneval.cnf").is_file())

    def test_existing_workspace_is_not_seeded_automatically(self):
        existing = Workspace(Path(self.temp.name) / "existing")
        reopened = Workspace(existing.root)
        service = BundledAssetService(reopened, ROOT / "backend")
        result = service.seed_new_workspace()
        self.assertFalse(result["inputLibraryInstalled"])
        self.assertFalse(result["modelTemplateInstalled"])

    def test_manifest_rejects_tampered_bundled_file(self):
        resource_root = Path(self.temp.name) / "resources"
        bundled = resource_root / "bundled_assets" / "planrva-mm"
        shutil.copytree(ROOT / "resources" / "examples" / "planrva-mm", bundled)
        (bundled / "input-library" / "bzone_employment.csv").write_text("tampered\n", encoding="utf-8")
        service = BundledAssetService(self.workspace, resource_root)
        with self.assertRaises(WorkspaceError):
            service.verify()

    def test_separate_planrva_package_installs_linked_assets(self):
        archive = Path(self.temp.name) / "planrva.zip"
        subprocess.run(
            [sys.executable, str(ROOT / "packaging/build_planrva_package.py"), "--shared-map-package", str(make_shared_map_package(Path(self.temp.name) / "virginia.zip")), "--output", str(archive)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        record = ModelPackageService(self.workspace).install(archive)
        self.assertEqual(record["name"], "PlanRVA MM")
        self.assertEqual(record["version"], "2.0.0")
        self.assertTrue((self.workspace.input_library / "PlanRVA MM" / "bzone_employment.csv").is_file())
        self.assertTrue((self.workspace.templates / "template-planrva-mm-8f140cd4cb" / "visioneval.cnf").is_file())
        self.assertTrue((self.workspace.map_contexts / "virginia-mpo-regions" / "workbench-map-context.json").is_file())
        providers = RegionPackageService(self.workspace).comparison_map_providers()
        self.assertEqual(providers[0]["id"], "virginia-mpo-regions")
        self.assertEqual(providers[0]["compatibleTemplateIds"], ["template-planrva-mm-8f140cd4cb"])
        _, context, regions, crosswalk = RegionBuilderService(
            self.workspace, ROOT / "backend", RegionPackageService(self.workspace)
        )._map_package_context("virginia-mpo-regions")
        self.assertEqual(context["componentOf"], "planrva-mm-v1")
        self.assertEqual(context["version"], "2026.08.12.3")
        self.assertNotIn("geometryPath", context["builder"])
        self.assertEqual(len(regions["regions"]), 15)
        self.assertEqual(len(crosswalk["regions"]), 15)
        self.assertEqual(self.workspace.settings()["defaultInputLibraryId"], "PlanRVA MM")
        dependencies = self.workspace.asset_dependencies("input-library", "PlanRVA MM")
        self.assertEqual(dependencies["related"][0]["id"], "template-planrva-mm-8f140cd4cb")
        context_root = self.workspace.map_contexts / "virginia-mpo-regions"
        legacy_root = self.workspace.templates / "template-planrva-mm-8f140cd4cb" / ".workbench-map-context"
        context_root.rename(legacy_root)
        RegionPackageService(self.workspace)
        self.assertFalse(legacy_root.exists())
        self.assertTrue((context_root / "workbench-map-context.json").is_file())

    def test_separate_planrva_package_rejects_tampering(self):
        archive = Path(self.temp.name) / "planrva.zip"
        subprocess.run(
            [sys.executable, str(ROOT / "packaging/build_planrva_package.py"), "--shared-map-package", str(make_shared_map_package(Path(self.temp.name) / "virginia.zip")), "--output", str(archive)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        extracted = Path(self.temp.name) / "tampered"
        with zipfile.ZipFile(archive) as handle:
            handle.extractall(extracted)
        package_root = next(extracted.iterdir())
        (package_root / "data/input-library/bzone_employment.csv").write_text("tampered\n", encoding="utf-8")
        with self.assertRaises(WorkspaceError):
            ModelPackageService(self.workspace).install(package_root)

    def test_input_explanation_package_folder_installs_and_sanitizes_guides(self):
        package = self.make_explanation_package()
        service = InputExplanationPackageService(self.workspace)
        record = service.install(package)
        self.assertEqual(record["id"], "NC Explanations")
        self.assertEqual(record["fileCount"], 2)
        self.assertEqual(self.workspace.list_input_explanations()[0]["name"], "NC Input Explanations")
        catalog = json.loads(service.catalog_path("NC Explanations").read_text(encoding="utf-8"))
        html = catalog["explanations"]["azone_people"]["html"]
        self.assertNotIn("File 01_azone_people.csv", html)
        self.assertNotIn("May 21, 2026", html)
        self.assertIn("NC guide text", html)
        self.assertNotIn("<script", catalog["explanations"]["bzone_jobs"]["html"])
        self.assertNotIn("onclick", catalog["explanations"]["bzone_jobs"]["html"])

    def test_input_explanation_package_zip_installs(self):
        package = self.make_explanation_package("NC Zip Explanations")
        archive = Path(self.temp.name) / "nc-explanations.zip"
        with zipfile.ZipFile(archive, "w") as handle:
            for path in package.rglob("*"):
                if path.is_file():
                    handle.write(path, path.relative_to(package.parent).as_posix())
        record = InputExplanationPackageService(self.workspace).install(archive)
        self.assertEqual(record["id"], "NC Zip Explanations")
        self.assertTrue((self.workspace.input_explanations / "NC Zip Explanations" / "catalog.json").is_file())

    def test_input_explanation_package_rejects_unsafe_manifest_paths(self):
        package = self.make_explanation_package("Unsafe Explanations")
        manifest = json.loads((package / "workbench-package.json").read_text(encoding="utf-8"))
        manifest["files"] = [{"path": "../outside.md"}]
        (package / "workbench-package.json").write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(WorkspaceError):
            InputExplanationPackageService(self.workspace).install(package)

    def test_explore_uses_selected_input_explanation_package(self):
        package = self.make_explanation_package()
        package_service = InputExplanationPackageService(self.workspace)
        package_service.install(package)
        library = self.workspace.input_library / "Example"
        library.mkdir()
        (library / "azone_people.csv").write_text("Geo,Year,Population\nA,2045,10\n", encoding="utf-8")
        catalog = Path(self.temp.name) / "empty-catalog.json"
        catalog.write_text(json.dumps({"variables": {}, "inputFields": {}, "explanations": {}}), encoding="utf-8")
        result = ExploreService(self.workspace, catalog).file(
            "Example",
            "azone_people.csv",
            explanation_catalog_path=package_service.catalog_path("NC Explanations"),
        )
        self.assertIn("NC guide text", result["explanationHtml"])
        self.assertNotIn("File 01_azone_people.csv", result["explanationHtml"])

    def test_application_state_lists_installed_input_explanations(self):
        app = WorkbenchApplication(Path(self.temp.name) / "app-workspace", ROOT / "public", ROOT / "backend")
        app.input_explanations.install(self.make_explanation_package())
        state = app.state()
        self.assertEqual(state["inputExplanations"][0]["name"], "NC Input Explanations")


if __name__ == "__main__":
    unittest.main()
