import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.workbench.region_builder import DEFAULT_FAMPO_ID, RegionBuilderService
from backend.workbench.region_packages import RegionPackageService, file_sha256, package_manifest_type, package_root
from backend.workbench.workspace import Workspace, WorkspaceError, read_json

ROOT = Path(__file__).resolve().parents[1]

def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_source_model(root: Path, *, missing_marea: bool = False) -> Path:
    model = root / ("source-missing-marea" if missing_marea else "source-model")
    write(model / "visioneval.cnf", "ScriptsDir: scripts\nInputDir: inputs\nParamDir: defs\nGeoFile: geo.csv\nModelParamFile: model_parameters.json\nRegion: statewide\nState: VA\nDescription: source\nYears: [2024, 2045]\n")
    write(model / "scripts" / "run_model.R", "# runnable\n")
    write(model / "defs" / "geo.csv", "Azone,Bzone,Czone,Marea\nAlpha County,101,NA,metro\nAlpha County,102,NA,metro\nBeta County,201,NA,non_uza\n")
    write(model / "defs" / "units.csv", "Unit\n")
    write(model / "defs" / "deflators.csv", "Year\n2024\n")
    write(model / "inputs" / "bzone_network_design.csv", "Geo,Year,D3\n101,2024,1\n102,2024,2\n201,2024,3\n")
    write(model / "inputs" / "azone_hh_pop_by_age.csv", "Geo,Year,Age0to14\nAlpha County,2024,10\nBeta County,2024,20\n")
    marea_rows = "metro,2024,100\n" if missing_marea else "metro,2024,100\nnon_uza,2024,200\n"
    write(model / "inputs" / "marea_lane_miles.csv", f"Geo,Year,FwyLaneMi\n{marea_rows}")
    write(model / "inputs" / "region_road_cost.csv", "Year,RoadBaseModCost\n2024,50\n")
    write(model / "inputs" / "other_ops_effectiveness.csv", "Level,Art_Rcr\nBase,1\n")
    write(model / "inputs" / "model_parameters.json", "[]\n")
    return model


def make_planrva_scaffold(root: Path) -> Path:
    model = root / "bundled_assets" / "planrva-mm" / "model-template"
    write(model / "visioneval.cnf", "ScriptsDir: scripts\nInputDir: inputs\nParamDir: defs\nGeoFile: geo.csv\nModelParamFile: model_parameters.json\nRegion: planrva\nState: VA\nDescription: scaffold\nYears: [2024, 2045]\n")
    write(model / "scripts" / "run_model.R", "# runnable\n")
    write(model / "defs" / "geo.csv", "Azone,Bzone,Czone,Marea\nRichmond City,517600001001,NA,Richmond City\n")
    write(model / "defs" / "units.csv", "Unit\n")
    write(model / "defs" / "deflators.csv", "Year\n2024\n")
    write(model / "inputs" / "model_parameters.json", "[]\n")
    write(model / "inputs" / "region_road_cost.csv", "Year,RoadBaseModCost\n2024,50\n")
    return model


def make_packaged_va_library(root: Path) -> Path:
    library = root / "va_input_library" / "VA"
    write(library / "bzone_lat_lon.csv", "Geo,Year,Latitude,Longitude\n511770001001,2024,38,-77\n511770001001,2045,38,-77\n516300001001,2024,38,-77\n511790001001,2024,38,-77\n510010001001,2024,37,-76\n515500001001,2024,37,-76\n")
    write(library / "bzone_network_design.csv", "Geo,Year,D3\n511770001001,2024,1\n516300001001,2024,2\n511790001001,2024,3\n510010001001,2024,4\n515500001001,2024,5\n")
    write(library / "azone_hh_pop_by_age.csv", "Geo,Year,Age0to14\nFredericksburg City,2024,10\nSpotsylvania County,2024,20\nStafford County,2024,30\nAccomack County,2024,40\nChesapeake City,2024,50\n")
    write(library / "azone_hh_lttrk_prop.csv", "Geo,Year,LtTrkProp\nFredericksburg City,2024,0.1\nSpotsylvania County,2024,0.2\nStafford County,2024,0.3\nAccomack County,2024,0.4\nChesapeake City,2024,0.5\n")
    write(library / "marea_lane_miles.csv", "Geo,Year,FwyLaneMi\nFredericksburg City,2024,100\nSpotsylvania County,2024,200\nStafford County,2024,300\nAccomack County,2024,400\nChesapeake City,2024,500\n")
    write(library / "marea_transit_service.csv", "Geo,Year,DRRevMi,VPRevMi,MBRevMi,RBRevMi,MGRevMi,SRRevMi,HRRevMi,CRRevMi\nFredericksburg City,2024,0,0,0,0,10,0,0,10\nSpotsylvania County,2024,0,0,0,0,0,0,0,0\nStafford County,2024,0,0,0,0,0,0,0,0\nAccomack County,2024,0,0,0,0,0,0,0,0\nChesapeake City,2024,0,0,0,0,0,0,0,0\n")
    write(library / "marea_transit_fuel.csv", "Geo,Year,VanPropDiesel,VanPropGasoline,VanPropCng,BusPropDiesel,BusPropGasoline,BusPropCng,RailPropDiesel,RailPropGasoline\nFredericksburg City,2024,0,1,0,1,0,0,NA,NA\nSpotsylvania County,2024,0,1,0,1,0,0,NA,NA\nStafford County,2024,0,1,0,1,0,0,NA,NA\nAccomack County,2024,0,1,0,1,0,0,NA,NA\nChesapeake City,2024,0,1,0,1,0,0,NA,NA\n")
    write(library / "marea_transit_powertrain_prop.csv", "Geo,Year,VanPropIcev,VanPropHev,VanPropBev,BusPropIcev,BusPropHev,BusPropBev,RailPropIcev,RailPropHev,RailPropEv\nFredericksburg City,2024,1,0,0,1,0,0,NA,NA,NA\nSpotsylvania County,2024,1,0,0,1,0,0,NA,NA,NA\nStafford County,2024,1,0,0,1,0,0,NA,NA,NA\nAccomack County,2024,1,0,0,1,0,0,NA,NA,NA\nChesapeake City,2024,1,0,0,1,0,0,NA,NA,NA\n")
    write(library / "region_road_cost.csv", "Year,RoadBaseModCost\n2024,50\n")
    write(library / "other_ops_effectiveness.csv", "Level,Art_Rcr\nBase,1\n")
    write(library / "model_parameters.json", "[]\n")
    return library


def make_mpo_crosswalk(root: Path, *, missing_bzone: bool = False) -> Path:
    path = root / "docs" / "developer" / "reference-data" / "virginia_mpo_bzone_crosswalk.json"
    selected_bzones = ["511770001001", "516300001001"]
    if missing_bzone:
        selected_bzones.append("519990001001")
    payload = {
        "schemaVersion": 1,
        "generatedAt": "2026-08-05T18:00:00Z",
        "assignmentRule": "test representative-point and majority-overlap rule",
        "sources": {
            "mpo": {"provider": "Virginia Department of Transportation", "modified": "2026-05-06T00:00:00Z", "layerUrl": "https://services.arcgis.com/example/FeatureServer/1"},
            "bzone": {"provider": "ArcGIS Online / UVA Library", "modified": "2026-05-06T00:00:00Z", "layerUrl": "https://services2.arcgis.com/example/FeatureServer/0"},
        },
        "regions": {
            DEFAULT_FAMPO_ID: {
                "officialMpoId": "FRED",
                "officialName": "Fredericksburg Area Metropolitan Planning Organization",
                "bzones": selected_bzones,
                "boundaryBzones": [{"geoid": "511770001001", "overlapRatio": 0.75}],
                "excludedBoundaryBzones": [{"geoid": "511790001001", "overlapRatio": 0.25}],
                "selectedCount": 2 + int(missing_bzone),
                "boundaryCount": 1,
                "excludedBoundaryCount": 1,
            }
        },
    }
    write(path, json.dumps(payload))
    return path


def install_va_package(root: Path, workspace: Workspace, *, spatial: bool = False, missing_bzone: bool = False) -> tuple[RegionPackageService, str, str]:
    package = root / "package-source"
    library = make_packaged_va_library(root)
    shutil.copytree(library, package / "data" / "input-library")
    shutil.copytree(make_planrva_scaffold(root), package / "data" / "model-template")
    registry = root / "docs" / "developer" / "reference-data" / "virginia_mpo_regions.json"
    target_registry = package / "data" / "regions.json"
    target_registry.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(registry, target_registry)
    shutil.copy2(ROOT / "docs" / "developer" / "reference-data" / "virginia_county_equivalents_2020.txt", package / "data" / "localities.txt")
    if spatial:
        crosswalk_source = make_mpo_crosswalk(root, missing_bzone=missing_bzone)
        shutil.copy2(crosswalk_source, package / "data" / "crosswalk.json")
    else:
        write(package / "data" / "crosswalk.json", json.dumps({"schemaVersion": 1, "regions": {}, "sources": {}}))
    write(package / "SOURCES.md", "# Sources\n\nChecked 2026-08-05.\n")
    files = []
    for path in sorted(item for item in package.rglob("*") if item.is_file()):
        files.append({"path": path.relative_to(package).as_posix(), "size": path.stat().st_size, "sha256": file_sha256(path)})
    manifest = {
        "schemaVersion": 1,
        "type": "region-builder",
        "id": "virginia-test",
        "name": "Virginia Test Regions",
        "version": "2026.08.05",
        "coverage": "Virginia",
        "state": "VA",
        "retrievedAt": "2026-08-05",
        "terminology": {"regionSelector": "Virginia MPO"},
        "inputLibrary": {"name": "Virginia InputLibrary", "path": "data/input-library", "requiredFiles": ["bzone_lat_lon.csv"]},
        "builder": {
            "kind": "mpo-bzone-crosswalk",
            "modelTemplatePath": "data/model-template",
            "regionsPath": "data/regions.json",
            "crosswalkPath": "data/crosswalk.json",
            "localitiesPath": "data/localities.txt",
            "localityPrefixLength": 5,
            "boundaryAuthority": "Official VDOT MPO geometry",
            "statewideRegion": {"enabled": True, "id": "virginia-statewide", "name": "Virginia statewide", "defaultRegionCode": "virginia_statewide"},
            "defaultFiles": ["azone_carsvc_characteristics.csv", "azone_lttrk_prop.csv", "azone_relative_employment.csv"],
            "transitNormalization": "virginia-transit-service-v1",
        },
        "comparisonMap": {"enabled": True, "geographies": [{"id": "county", "label": "County / locality", "geometry": "azone"}, {"id": "bzone", "label": "Bzone", "geometry": "bzone"}]},
        "sourcesDocument": "SOURCES.md",
        "sources": [{"label": "VDOT MPO Study Areas", "url": "https://www.virginiaroads.org/", "retrievedAt": "2026-08-05"}],
        "files": files,
    }
    write(package / "workbench-package.json", json.dumps(manifest))
    packages = RegionPackageService(workspace)
    packages.install(package)
    return packages, "virginia-test", "package:virginia-test"


class UnpackedPackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def make_installable_package(self, root: Path) -> Path:
        write(root / "data" / "input-library" / "library.csv", "Geo,Year,Value\n1,2024,1\n")
        write(root / "data" / "regions.json", "{}\n")
        write(root / "data" / "crosswalk.json", "{}\n")
        write(root / "SOURCES.md", "# Sources\n")
        files = []
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            files.append({"path": path.relative_to(root).as_posix(), "size": path.stat().st_size, "sha256": file_sha256(path)})
        manifest = {
            "schemaVersion": 1,
            "type": "region-builder",
            "id": "folder-test",
            "name": "Folder test",
            "version": "1.0.0",
            "coverage": "Fixture",
            "sourcesDocument": "SOURCES.md",
            "inputLibrary": {"path": "data/input-library", "requiredFiles": []},
            "builder": {"kind": "mpo-bzone-crosswalk", "regionsPath": "data/regions.json", "crosswalkPath": "data/crosswalk.json"},
            "files": files,
        }
        write(root / "workbench-package.json", json.dumps(manifest))
        return root

    def test_accepts_manifest_at_selected_root(self):
        write(self.root / "workbench-package.json", json.dumps({"type": "region-builder"}))
        self.assertEqual(package_root(self.root), self.root.resolve())
        self.assertEqual(package_manifest_type(self.root), "region-builder")

    def test_accepts_one_download_wrapper_folder(self):
        wrapper = self.root / "virginia-package-main"
        write(wrapper / "workbench-package.json", json.dumps({"type": "region-builder"}))
        self.assertEqual(package_root(self.root), wrapper.resolve())

    def test_installs_from_one_download_wrapper_folder(self):
        wrapper = self.make_installable_package(self.root / "virginia-package-main")
        self.assertEqual(package_root(self.root), wrapper.resolve())
        service = RegionPackageService(Workspace(self.root / "workspace"))
        installed = service.install(self.root)
        self.assertEqual(installed["id"], "folder-test")
        self.assertTrue((service.workspace.region_packages / "folder-test" / "data" / "regions.json").is_file())

    def test_rejects_folder_checksum_failure(self):
        package = self.make_installable_package(self.root / "package")
        write(package / "data" / "regions.json", '{"changed": true}\n')
        with self.assertRaisesRegex(WorkspaceError, "size does not match|checksum does not match"):
            RegionPackageService(Workspace(self.root / "workspace")).install(package)

    def test_rejects_inventory_symlink_that_escapes_folder(self):
        package = self.make_installable_package(self.root / "package")
        outside = self.root / "outside.json"
        write(outside, "{}\n")
        target = package / "data" / "regions.json"
        target.unlink()
        target.symlink_to(outside)
        with self.assertRaisesRegex(WorkspaceError, "unsafe file path"):
            RegionPackageService(Workspace(self.root / "workspace")).install(package)

    def test_rejects_missing_ambiguous_and_deep_manifests(self):
        with self.assertRaisesRegex(WorkspaceError, "exactly one"):
            package_root(self.root)
        write(self.root / "one" / "workbench-package.json", "{}")
        write(self.root / "two" / "workbench-package.json", "{}")
        with self.assertRaisesRegex(WorkspaceError, "exactly one"):
            package_root(self.root)
        shutil.rmtree(self.root / "two")
        deep = self.root / "one" / "nested"
        (deep).mkdir()
        shutil.move(self.root / "one" / "workbench-package.json", deep / "workbench-package.json")
        with self.assertRaisesRegex(WorkspaceError, "root or in one wrapper"):
            package_root(self.root)

    def test_rejects_symlinked_manifest(self):
        outside = self.root.parent / f"{self.root.name}-manifest.json"
        write(outside, json.dumps({"type": "region-builder"}))
        try:
            (self.root / "workbench-package.json").symlink_to(outside)
            with self.assertRaisesRegex(WorkspaceError, "unsafe|exactly one|root or in one wrapper"):
                package_root(self.root)
        finally:
            outside.unlink(missing_ok=True)


class RegionBuilderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        write(
            self.root / "docs" / "developer" / "reference-data" / "virginia_mpo_regions.json",
            (ROOT / "docs" / "developer" / "reference-data" / "virginia_mpo_regions.json").read_text(encoding="utf-8"),
        )
        self.workspace = Workspace(self.root / "workspace")
        self.service = RegionBuilderService(self.workspace, self.root)
        self.template = self.workspace.import_template(make_source_model(self.root), "VA Source")

    def tearDown(self):
        self.temp.cleanup()

    def test_preview_filters_geo_and_counts_by_zone_level(self):
        preview = self.service.preview({
            "sourceTemplateId": self.template["id"],
            "selectedAzones": ["Alpha County"],
        })
        self.assertEqual(preview["selection"]["azones"], ["Alpha County"])
        self.assertEqual(preview["selection"]["bzones"], ["101", "102"])
        self.assertEqual(preview["selection"]["mareas"], ["metro"])
        files = {item["file"]: item for item in preview["files"]}
        self.assertEqual(files["bzone_network_design.csv"]["rowsAfter"], 2)
        self.assertEqual(files["azone_hh_pop_by_age.csv"]["rowsAfter"], 1)
        self.assertEqual(files["marea_lane_miles.csv"]["rowsAfter"], 1)
        self.assertEqual(files["region_road_cost.csv"]["action"], "copy")

    def test_build_writes_input_library_template_geo_and_manifest(self):
        result = self.service.build({
            "sourceTemplateId": self.template["id"],
            "regionName": "Alpha Region",
            "regionCode": "alpha_region",
            "stateAbbr": "VA",
            "selectedBzones": ["101"],
        })
        library = self.workspace.input_library / result["inputLibrary"]["id"]
        template = self.workspace.templates / result["modelTemplate"]["id"]
        self.assertTrue((library / "region_builder_manifest.json").is_file())
        self.assertTrue((template / "region_builder_manifest.json").is_file())
        self.assertEqual((template / "defs" / "geo.csv").read_text(encoding="utf-8").strip(), "Azone,Bzone,Czone,Marea\nAlpha County,101,NA,metro")
        self.assertIn("101,2024,1", (library / "bzone_network_design.csv").read_text(encoding="utf-8"))
        self.assertNotIn("102,2024,2", (library / "bzone_network_design.csv").read_text(encoding="utf-8"))
        self.assertEqual((library / "region_road_cost.csv").read_text(encoding="utf-8"), "Year,RoadBaseModCost\n2024,50\n")
        self.assertTrue(self.workspace.validate_template(template)["valid"])
        manifest = read_json(template / "region_builder_manifest.json", {})
        self.assertEqual(manifest["selection"]["bzones"], ["101"])

    def test_unmatched_bzone_is_rejected(self):
        with self.assertRaisesRegex(WorkspaceError, "not in defs/geo.csv"):
            self.service.preview({"sourceTemplateId": self.template["id"], "selectedBzones": ["999"]})

    def test_missing_marea_rows_block_build(self):
        missing = self.workspace.import_template(make_source_model(self.root, missing_marea=True), "VA Missing Marea")
        with self.assertRaisesRegex(WorkspaceError, "missing selected Marea rows"):
            self.service.preview({"sourceTemplateId": missing["id"], "selectedAzones": ["Beta County"]})

    def test_installed_package_exposes_sources_regions_and_reference(self):
        packages, package_id, source_id = install_va_package(self.root, self.workspace)
        service = RegionBuilderService(self.workspace, self.root, packages)
        sources = service.sources(package_id)["sources"]
        registry = service.regions(package_id)
        regions = registry["regions"]
        reference = service.reference(package_id)
        self.assertEqual(sources[0]["id"], source_id)
        self.assertIn(DEFAULT_FAMPO_ID, {item["id"] for item in regions})
        self.assertEqual(len(regions), 15)
        self.assertNotIn("virginia-statewide", {item["id"] for item in regions})
        self.assertEqual(registry["source"]["publisher"], "Virginia Department of Transportation")
        self.assertEqual(reference["package"]["retrievedAt"], "2026-08-05")
        self.assertIn("Checked 2026-08-05", reference["sourcesDocument"])

    def test_package_statewide_region_is_context_only(self):
        packages, package_id, source_id = install_va_package(self.root, self.workspace, spatial=True)
        service = RegionBuilderService(self.workspace, self.root, packages)
        self.assertNotIn("virginia-statewide", {item["id"] for item in service.regions(package_id)["regions"]})
        with self.assertRaisesRegex(WorkspaceError, "Choose a region supported"):
            service.preview({"packageId": package_id, "sourceLibraryId": source_id, "regionId": "virginia-statewide"})

    def test_packaged_boundary_crosswalk_covers_all_official_mpos(self):
        crosswalk = read_json(ROOT / "docs" / "developer" / "reference-data" / "virginia_mpo_bzone_crosswalk.json", {})
        self.assertEqual(crosswalk["schemaVersion"], 1)
        self.assertEqual(crosswalk["sources"]["mpo"]["provider"], "Virginia Department of Transportation")
        self.assertEqual(crosswalk["sources"]["mpo"]["featureCount"], 15)
        self.assertEqual(crosswalk["sources"]["bzone"]["featureCount"], 5963)
        registry = read_json(ROOT / "docs" / "developer" / "reference-data" / "virginia_mpo_regions.json", {})
        self.assertEqual(set(crosswalk["regions"]), {item["id"] for item in registry["regions"]})
        self.assertEqual(crosswalk["regions"][DEFAULT_FAMPO_ID]["selectedCount"], 189)
        self.assertEqual(crosswalk["regions"][DEFAULT_FAMPO_ID]["boundaryCount"], 7)
        charlottesville = crosswalk["regions"]["charlottesville-albemarle-mpo"]
        self.assertEqual(charlottesville["selectedCount"], 110)
        self.assertEqual(charlottesville["boundaryCount"], 6)
        self.assertTrue(all(item["overlapRatio"] >= 0.01 for item in charlottesville["boundaryBzones"]))
        self.assertTrue(all(region["selectedCount"] == len(region["bzones"]) for region in crosswalk["regions"].values()))

    def test_spatial_crosswalk_is_preferred_and_reports_boundary_quality(self):
        packages, package_id, source_id = install_va_package(self.root, self.workspace, spatial=True)
        service = RegionBuilderService(self.workspace, self.root, packages)
        preview = service.preview({"packageId": package_id, "sourceLibraryId": source_id, "regionId": DEFAULT_FAMPO_ID})
        self.assertEqual(preview["selection"]["method"], "official-boundary-bzone-crosswalk")
        self.assertEqual(preview["selection"]["bzones"], ["511770001001", "511790001001", "516300001001"])
        self.assertEqual(preview["selection"]["azones"], ["Fredericksburg City", "Spotsylvania County", "Stafford County"])
        self.assertEqual(preview["selection"]["boundary"]["boundaryCount"], 2)
        self.assertEqual(preview["selection"]["boundary"]["excludedBoundaryCount"], 0)
        self.assertEqual(preview["selection"]["boundary"]["excludedBoundaryBzones"], [])
        self.assertIn("Official VDOT MPO geometry", preview["warnings"][0])
        region = next(item for item in service.regions(package_id)["regions"] if item["id"] == DEFAULT_FAMPO_ID)
        self.assertEqual(region["officialMpoId"], "FRED")
        self.assertEqual(region["definitionQuality"], "official-boundary-at-bzone-resolution")

    def test_package_geography_options_and_custom_selection(self):
        packages, package_id, source_id = install_va_package(self.root, self.workspace, spatial=True)
        service = RegionBuilderService(self.workspace, self.root, packages)
        options = service.geography_options(package_id, source_id, DEFAULT_FAMPO_ID)
        self.assertEqual(options["counts"], {"azones": 5, "bzones": 5, "officialBzones": 3})
        self.assertEqual(options["officialBzones"], ["511770001001", "511790001001", "516300001001"])
        preview = service.preview({
            "packageId": package_id,
            "sourceLibraryId": source_id,
            "regionId": DEFAULT_FAMPO_ID,
            "geographyMode": "custom",
            "selectedBzones": ["511770001001", "511790001001"],
        })
        self.assertEqual(preview["selection"]["method"], "custom-bzone-selection")
        self.assertEqual(preview["selection"]["azones"], ["Spotsylvania County", "Stafford County"])
        boundary = preview["selection"]["boundary"]
        self.assertEqual(boundary["addedBzones"], [])
        self.assertEqual(boundary["removedBzones"], ["516300001001"])

    def test_custom_package_selection_accepts_bzone_outside_mpo_localities(self):
        packages, package_id, source_id = install_va_package(self.root, self.workspace, spatial=True)
        service = RegionBuilderService(self.workspace, self.root, packages)
        preview = service.preview({
            "packageId": package_id,
            "sourceLibraryId": source_id,
            "regionId": DEFAULT_FAMPO_ID,
            "geographyMode": "custom",
            "selectedBzones": ["510010001001"],
        })
        self.assertEqual(preview["selection"]["method"], "custom-bzone-selection")
        self.assertEqual(preview["selection"]["bzones"], ["510010001001"])
        self.assertEqual(preview["selection"]["azones"], ["Accomack County"])

    def test_region_map_reuses_local_geometry_cache(self):
        packages, package_id, _ = install_va_package(self.root, self.workspace, spatial=True)
        service = RegionBuilderService(self.workspace, self.root, packages)
        cache_path = self.workspace.exchange / "system" / "region-maps" / package_id / f"{DEFAULT_FAMPO_ID}.json"
        cached = {
            "schemaVersion": 1,
            "regionId": DEFAULT_FAMPO_ID,
            "regionName": "Fredericksburg Area MPO",
            "crosswalkGeneratedAt": "2026-08-05T18:00:00Z",
            "cached": False,
            "mpo": {"type": "FeatureCollection", "features": []},
            "azones": {"type": "FeatureCollection", "features": []},
            "bzones": {"type": "FeatureCollection", "features": []},
        }
        write(cache_path, json.dumps(cached))
        result = service.map_data(package_id, DEFAULT_FAMPO_ID)
        self.assertTrue(result["cached"])
        self.assertEqual(result["regionName"], "Fredericksburg Area MPO")

    def test_arcgis_all_geojson_pages_by_object_id(self):
        pages = []
        def fake_page(_url, where, _fields, **_kwargs):
            ids = where.split("(", 1)[1].rstrip(")").split(",")
            pages.append(ids)
            return {"type": "FeatureCollection", "features": [{"id": int(value)} for value in ids]}
        with patch.object(RegionBuilderService, "_arcgis_object_ids", return_value=("OBJECTID", list(range(1, 1202)))), patch.object(RegionBuilderService, "_arcgis_geojson", side_effect=fake_page):
            result = RegionBuilderService._arcgis_all_geojson("https://services.arcgis.com/example/FeatureServer/0", "NAME")
        self.assertEqual([len(page) for page in pages], [500, 500, 201])
        self.assertEqual(len(result["features"]), 1201)

    def test_statewide_map_returns_membership_and_reuses_fingerprinted_cache(self):
        packages, package_id, _ = install_va_package(self.root, self.workspace, spatial=True)
        service = RegionBuilderService(self.workspace, self.root, packages)
        mpo_features = [
            {"type": "Feature", "properties": {"MPO_ID": f"MPO-{index}", "MPO_NAME": f"MPO {index}"}, "geometry": {"type": "Polygon", "coordinates": []}}
            for index in range(15)
        ]
        mpo_features[0]["properties"]["MPO_ID"] = "FRED"
        bzone_features = [
            {"type": "Feature", "properties": {"GEOID": str(index)}, "geometry": {"type": "Polygon", "coordinates": []}}
            for index in range(5963)
        ]
        azone_features = [{"type": "Feature", "properties": {"Azones": "51630"}, "geometry": {"type": "Polygon", "coordinates": []}}]

        def all_features(url, _fields):
            if "services.arcgis.com" in url:
                return {"type": "FeatureCollection", "features": mpo_features}
            if url.endswith("/1"):
                return {"type": "FeatureCollection", "features": azone_features}
            return {"type": "FeatureCollection", "features": bzone_features}

        with patch.object(RegionBuilderService, "_arcgis_all_geojson", side_effect=all_features) as fetch:
            result = service.statewide_map_data(package_id)
        self.assertEqual(result["summary"], {"mpos": 15, "azones": 1, "bzones": 5963})
        focused = next(item for item in result["regions"] if item["id"] == DEFAULT_FAMPO_ID)
        self.assertEqual(focused["selectedBzones"], ["511770001001", "511790001001", "516300001001"])
        self.assertEqual(focused["includedBoundaryCases"], [
            {"geoid": "511770001001", "overlapRatio": 0.75},
            {"geoid": "511790001001", "overlapRatio": 0.25},
        ])
        self.assertEqual(focused["excludedBoundaryCases"], [])
        self.assertEqual(result["assignmentRule"], "test representative-point and majority-overlap rule")
        self.assertEqual(result["schemaVersion"], 3)
        self.assertEqual(len(result["localities"]), 133)
        self.assertEqual(result["localities"][0], {"azoneId": "51001", "localityName": "Accomack County"})
        mpo_properties = result["mpos"]["features"][0]["properties"]
        self.assertEqual(mpo_properties["regionId"], DEFAULT_FAMPO_ID)
        self.assertEqual(mpo_properties["officialMpoId"], "FRED")
        self.assertEqual(mpo_properties["name"], "MPO 0")
        self.assertEqual(result["azones"]["features"][0]["properties"]["azoneId"], "51630")
        self.assertEqual(result["azones"]["features"][0]["properties"]["localityName"], "Fredericksburg City")
        self.assertEqual(result["bzones"]["features"][0]["properties"]["bzoneId"], "0")
        self.assertEqual(fetch.call_count, 3)
        with patch.object(RegionBuilderService, "_arcgis_all_geojson", side_effect=AssertionError("network should not be used")):
            cached = service.statewide_map_data(package_id)
        self.assertTrue(cached["cached"])
        self.assertEqual(cached["summary"]["bzones"], 5963)

    def test_spatial_crosswalk_rejects_a_mismatched_input_library(self):
        packages, package_id, source_id = install_va_package(self.root, self.workspace, spatial=True, missing_bzone=True)
        service = RegionBuilderService(self.workspace, self.root, packages)
        with self.assertRaisesRegex(WorkspaceError, "absent from this InputLibrary"):
            service.preview({"packageId": package_id, "sourceLibraryId": source_id, "regionId": DEFAULT_FAMPO_ID})

    def test_fampo_preview_resolves_whole_jurisdiction_membership(self):
        packages, package_id, source_id = install_va_package(self.root, self.workspace)
        service = RegionBuilderService(self.workspace, self.root, packages)
        preview = service.preview({"packageId": package_id, "sourceLibraryId": source_id, "regionId": DEFAULT_FAMPO_ID})
        self.assertEqual(
            preview["selection"]["azones"],
            ["Fredericksburg City", "Spotsylvania County", "Stafford County"],
        )
        self.assertEqual(preview["selection"]["geoRows"], 3)
        self.assertEqual(preview["selection"]["bzones"], ["511770001001", "511790001001", "516300001001"])
        files = {item["file"]: item for item in preview["files"]}
        self.assertEqual(files["bzone_network_design.csv"]["rowsAfter"], 3)
        self.assertEqual(files["azone_hh_pop_by_age.csv"]["rowsAfter"], 3)
        self.assertEqual(files["marea_lane_miles.csv"]["rowsAfter"], 3)
        self.assertEqual(files["azone_carsvc_characteristics.csv"]["action"], "default")

    def test_fampo_build_filters_va_library_and_defaults_missing_required_files(self):
        packages, package_id, source_id = install_va_package(self.root, self.workspace)
        service = RegionBuilderService(self.workspace, self.root, packages)
        result = service.build({"packageId": package_id, "sourceLibraryId": source_id, "regionId": DEFAULT_FAMPO_ID})
        library = self.workspace.input_library / result["inputLibrary"]["id"]
        template = self.workspace.templates / result["modelTemplate"]["id"]
        geo_text = (template / "defs" / "geo.csv").read_text(encoding="utf-8")
        self.assertIn("Fredericksburg City,516300001001,NA,Fredericksburg City", geo_text)
        self.assertIn("Spotsylvania County,511770001001,NA,Spotsylvania County", geo_text)
        self.assertIn("Stafford County,511790001001,NA,Stafford County", geo_text)
        self.assertNotIn("510010001001", geo_text)
        self.assertNotIn("510010001001", (library / "bzone_network_design.csv").read_text(encoding="utf-8"))
        self.assertTrue((library / "azone_carsvc_characteristics.csv").is_file())
        self.assertTrue((template / "inputs" / "azone_relative_employment.csv").is_file())
        self.assertTrue(self.workspace.validate_template(template)["valid"])
        manifest = read_json(template / "region_builder_manifest.json", {})
        self.assertEqual(manifest["region"]["id"], DEFAULT_FAMPO_ID)
        self.assertEqual(manifest["regionPackage"]["id"], package_id)
        self.assertEqual({item["file"] for item in manifest["defaultedFiles"]}, {
            "azone_carsvc_characteristics.csv",
            "azone_lttrk_prop.csv",
            "azone_relative_employment.csv",
        })
        self.assertEqual(manifest["transitNormalization"]["rule"], "virginia-transit-service-v1")
        self.assertTrue(manifest["transitNormalization"]["applied"])
        self.assertIn("Fredericksburg City,2024,1,0,0,1,0,0,0.5,0,0.5", (library / "marea_transit_powertrain_prop.csv").read_text(encoding="utf-8"))

    def test_spatial_build_records_boundary_provenance(self):
        packages, package_id, source_id = install_va_package(self.root, self.workspace, spatial=True)
        service = RegionBuilderService(self.workspace, self.root, packages)
        result = service.build({"packageId": package_id, "sourceLibraryId": source_id, "regionId": DEFAULT_FAMPO_ID})
        template = self.workspace.templates / result["modelTemplate"]["id"]
        manifest = read_json(template / "region_builder_manifest.json", {})
        self.assertEqual(manifest["selection"]["method"], "official-boundary-bzone-crosswalk")
        self.assertEqual(manifest["selection"]["boundary"]["sources"]["mpo"]["provider"], "Virginia Department of Transportation")
        self.assertEqual(manifest["selection"]["boundary"]["boundaryCount"], 2)


if __name__ == "__main__":
    unittest.main()
