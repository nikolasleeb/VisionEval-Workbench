#!/usr/bin/env python3
"""Build the separately installable Virginia MPO regional data package."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.workbench.transit_inputs import TRANSIT_NORMALIZATION_RULE, normalize_virginia_transit_inputs


PACKAGE_ID = "virginia-mpo-regions"
PACKAGE_VERSION = "2026.08.12.3"
RETRIEVED_AT = "2026-08-05"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def validate_input_library_coverage(input_library: Path, crosswalk_path: Path) -> dict[str, int]:
    """Refuse to label a partial example library as statewide Virginia data."""
    with (input_library / "bzone_lat_lon.csv").open(encoding="utf-8-sig", newline="") as handle:
        available = {str(row.get("Geo") or "").strip() for row in csv.DictReader(handle)}
    crosswalk = json.loads(crosswalk_path.read_text(encoding="utf-8"))
    required = {
        str(geoid)
        for region in crosswalk.get("regions", {}).values()
        for geoid in region.get("bzones", [])
    }
    missing = required - available
    if missing:
        raise SystemExit(
            f"Virginia InputLibrary is not statewide: {len(missing)} of {len(required)} "
            "MPO crosswalk Bzones are absent"
        )
    return {"availableBzones": len(available), "crosswalkBzones": len(required)}


def sources_markdown() -> str:
    return """# Virginia MPO Regional Data Sources

Package data was assembled and checked on **August 5, 2026**.

## VisionEval Azone and Bzone geography

- **Title:** AzonesBzonesVa
- **Publisher/owner:** UVA Library ArcGIS organization (`jsm3f_uvalibrary`)
- **Web map:** https://www.arcgis.com/apps/mapviewer/index.html?webmap=bf7d33b13f074ae3b8f5f6e278c6dd62
- **Feature service:** https://services2.arcgis.com/8k2PygHqghVevhzy/arcgis/rest/services/AzonesBzonesVa_WFL1/FeatureServer
- **Layers:** Bzones (layer 0) and Azones (layer 1)

The package includes the Virginia VisionEval InputLibrary and identifiers derived from this map. It does not redistribute the ArcGIS polygon geometry because the item does not publish license terms authorizing redistribution.

## Official MPO boundaries

- **Title:** VDOT MPO Study Areas
- **Publisher:** Virginia Department of Transportation, Transportation and Mobility Planning Division
- **Virginia Roads page:** https://www.virginiaroads.org/datasets/VDOT::vdot-mpo-study-areas/explore
- **Feature service:** https://services.arcgis.com/p5v98VHDX9Atv3l7/arcgis/rest/services/VDOT_MPO_STUDY_AREA_BOUNDARY/FeatureServer/1
- **VDOT MPO listing (September 1, 2023):** https://www.vdot.virginia.gov/media/vdotvirginiagov/doing-business/for-localities/funding-programs/transportation-alternatives/MPO_Listing_2023-09-01_acc110623_PM.pdf

VDOT describes the service as the current official boundary source and reports 15 Virginia MPOs. The listing PDF is retained as a human-readable membership reference.

The package does not redistribute VDOT's raw boundary polygons. VDOT's service metadata restricts duplication or distribution without written permission. Instead, the package contains a reproducible, versioned Bzone membership crosswalk derived from the official polygons. Users must credit VDOT and validate policy decisions against the current official source.

## Crosswalk method

Every Bzone with at least 1% of its projected area inside an MPO is included in that MPO. Smaller geometry slivers and boundary-only contact are not included. Overlaps below 99% are retained as included boundary information. The package records source timestamps, response checksums, and included boundary cases.

## Virginia locality identifiers

- **Source:** U.S. Census Bureau, 2020 Census Codes for Counties and County Equivalent Entities
- **Virginia table:** https://www2.census.gov/geo/docs/reference/codes2020/cou/st51_va_cou2020.txt

The package includes this 133-row identifier table so statewide Azone and Bzone features can be described by both their model identifier and Virginia county-equivalent name while offline.

## Runnable model scaffold

The package includes a Workbench-compatible, model-neutral VisionEval scaffold used to turn a regional selection into a runnable model. Region building therefore does not depend on optional example packages bundled with the application. Generated inputs still come from the package's statewide Virginia InputLibrary and the selected MPO or statewide geography.

## Transit compatibility assumptions

VisionEval requires each Van, Bus, and Rail fuel or powertrain field group to be populated for every Marea or set to NA for every Marea. The source statewide library mixes populated localities with localities where these groups are absent.

Workbench preserves complete source rows and applies the versioned `virginia-transit-service-v1` compatibility rule to missing groups. Zero-service Van rows use gasoline and conventional powertrain defaults; zero-service Bus rows use diesel and conventional powertrain defaults. Rail electric share is derived from monorail/automated-guideway, streetcar/trolleybus, and light/heavy-rail revenue miles. Rail conventional share is derived from commuter/hybrid/cable/aerial revenue miles and uses diesel for its hydrocarbon fuel share. These are Workbench modeling assumptions, not values reported by VDOT or the source publishers.
"""


def build(input_library: Path, output: Path) -> Path:
    if not (input_library / "bzone_lat_lon.csv").is_file():
        raise SystemExit(f"Virginia InputLibrary not found: {input_library}")
    reference_root = ROOT / "docs" / "developer" / "reference-data"
    required_sources = {
        "data/regions.json": reference_root / "virginia_mpo_regions.json",
        "data/mpo_bzone_crosswalk.json": reference_root / "virginia_mpo_bzone_crosswalk.json",
        "data/zone_reference.json": reference_root / "virginia-visioneval-zones.arcgis.json",
        "data/virginia_county_equivalents_2020.txt": reference_root / "virginia_county_equivalents_2020.txt",
    }
    coverage = validate_input_library_coverage(input_library, required_sources["data/mpo_bzone_crosswalk.json"])
    with tempfile.TemporaryDirectory() as temporary:
        package = Path(temporary) / f"{PACKAGE_ID}-{PACKAGE_VERSION}"
        data = package / "data"
        shutil.copytree(input_library, data / "input-library", ignore=shutil.ignore_patterns(".DS_Store"))
        transit_normalization = normalize_virginia_transit_inputs(data / "input-library")
        scaffold = ROOT / "resources" / "region-builder" / "model-template"
        if not (scaffold / "visioneval.cnf").is_file():
            raise SystemExit(f"Generic VisionEval model template scaffold not found: {scaffold}")
        shutil.copytree(
            scaffold,
            data / "model-template",
            ignore=shutil.ignore_patterns("inputs", "results", ".DS_Store", ".workbench-*"),
        )
        for relative, source in required_sources.items():
            target = package / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        (package / "SOURCES.md").write_text(sources_markdown(), encoding="utf-8")
        inventory = []
        for path in sorted(item for item in package.rglob("*") if item.is_file()):
            relative = path.relative_to(package).as_posix()
            inventory.append({"path": relative, "size": path.stat().st_size, "sha256": sha256(path)})
        manifest = {
            "schemaVersion": 1,
            "type": "region-builder",
            "id": PACKAGE_ID,
            "name": "Virginia MPO Regional Data",
            "version": PACKAGE_VERSION,
            "coverage": "Virginia",
            "state": "VA",
            "retrievedAt": RETRIEVED_AT,
            "description": "Official VDOT MPO boundaries joined to Virginia VisionEval Bzones, with a statewide InputLibrary.",
            "terminology": {"regionSingular": "MPO", "regionPlural": "MPOs", "regionSelector": "Virginia MPO"},
            "inputLibrary": {
                "name": "Virginia InputLibrary",
                "path": "data/input-library",
                "requiredFiles": ["bzone_lat_lon.csv", "azone_hh_pop_by_age.csv"],
            },
            "builder": {
                "kind": "mpo-bzone-crosswalk",
                "modelTemplatePath": "data/model-template",
                "regionsPath": "data/regions.json",
                "crosswalkPath": "data/mpo_bzone_crosswalk.json",
                "zoneReferencePath": "data/zone_reference.json",
                "localitiesPath": "data/virginia_county_equivalents_2020.txt",
                "localityPrefixLength": 5,
                "boundaryAuthority": "Official VDOT MPO geometry",
                "statewideRegion": {
                    "enabled": True,
                    "id": "virginia-statewide",
                    "name": "Virginia statewide",
                    "shortName": "Statewide",
                    "defaultRegionCode": "virginia_statewide",
                },
                "defaultFiles": [
                    "azone_carsvc_characteristics.csv",
                    "azone_lttrk_prop.csv",
                    "azone_relative_employment.csv",
                ],
                "transitNormalization": TRANSIT_NORMALIZATION_RULE,
            },
            "transitNormalization": transit_normalization,
            "coverageValidation": coverage,
            "comparisonMap": {
                "enabled": True,
                "jurisdictionLabel": "Virginia",
                "fullExtentLabel": "Virginia",
                "geographies": [
                    {"id": "county", "label": "County / locality", "geometry": "azone", "identifier": "FIPS", "technicalLevel": "Azone"},
                    {"id": "bzone", "label": "Bzone", "geometry": "bzone", "identifier": "GEOID", "technicalLevel": "Bzone"},
                ],
            },
            "sourcesDocument": "SOURCES.md",
            "sources": [
                {
                    "label": "U.S. Census Virginia county-equivalent codes",
                    "publisher": "U.S. Census Bureau",
                    "url": "https://www2.census.gov/geo/docs/reference/codes2020/cou/st51_va_cou2020.txt",
                    "publishedAt": "2020",
                    "retrievedAt": RETRIEVED_AT,
                },
                {
                    "label": "VisionEval Azone/Bzone map",
                    "publisher": "UVA Library ArcGIS organization",
                    "url": "https://www.arcgis.com/apps/mapviewer/index.html?webmap=bf7d33b13f074ae3b8f5f6e278c6dd62",
                    "retrievedAt": RETRIEVED_AT,
                },
                {
                    "label": "VDOT MPO Study Areas",
                    "publisher": "Virginia Department of Transportation",
                    "url": "https://www.virginiaroads.org/datasets/VDOT::vdot-mpo-study-areas/explore",
                    "retrievedAt": RETRIEVED_AT,
                },
                {
                    "label": "VDOT MPO Listing",
                    "publisher": "Virginia Department of Transportation",
                    "url": "https://www.vdot.virginia.gov/media/vdotvirginiagov/doing-business/for-localities/funding-programs/transportation-alternatives/MPO_Listing_2023-09-01_acc110623_PM.pdf",
                    "publishedAt": "2023-09-01",
                    "retrievedAt": RETRIEVED_AT,
                },
            ],
            "files": inventory,
        }
        (package / "workbench-package.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(item for item in package.rglob("*") if item.is_file()):
                archive.write(path, f"{package.name}/{path.relative_to(package).as_posix()}")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-library", type=Path, default=ROOT.parent / "VisionEvalEditorTool" / "InputLibrary" / "VA")
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / "packages" / f"{PACKAGE_ID}.zip")
    args = parser.parse_args()
    print(build(args.input_library.resolve(), args.output.resolve()))


if __name__ == "__main__":
    main()
