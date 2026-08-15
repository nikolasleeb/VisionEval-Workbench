#!/usr/bin/env python3
"""Build the versioned Virginia MPO-to-Bzone spatial crosswalk.

This maintenance command intentionally keeps geometry dependencies out of the
Workbench runtime. Run it with Shapely available, review the reported boundary
cases, and commit the resulting JSON artifact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shapely.geometry import shape
from shapely.ops import transform
from shapely.strtree import STRtree


MPO_ITEM_ID = "d1bf64ec02114346aea498b51f1d9594"
MPO_LAYER_URL = "https://services.arcgis.com/p5v98VHDX9Atv3l7/arcgis/rest/services/VDOT_MPO_STUDY_AREA_BOUNDARY/FeatureServer/1"
BZONE_ITEM_ID = "bfdfaabcb59845fbb6bd51ef392ddbc5"
BZONE_LAYER_URL = "https://services2.arcgis.com/8k2PygHqghVevhzy/arcgis/rest/services/AzonesBzonesVa_WFL1/FeatureServer/0"
MPO_ID_TO_REGION_ID = {
    "BRIS": "bristol-mpo",
    "CVIL": "charlottesville-albemarle-mpo",
    "DAN": "danville-pittsylvania-mpo",
    "FRED": "fredericksburg-area-mpo",
    "HAMP": "hampton-roads-tpo",
    "HAR": "harrisonburg-rockingham-mpo",
    "KING": "kingsport-mpo",
    "LYN": "central-virginia-tpo",
    "NOVA": "national-capital-region-tpb",
    "NRV": "new-river-valley-mpo",
    "RICH": "richmond-regional-tpo",
    "ROAN": "roanoke-valley-tpo",
    "SAW": "staunton-augusta-waynesboro-mpo",
    "TCAT": "tri-cities-area-mpo",
    "WINC": "winchester-frederick-county-mpo",
}
MIN_OVERLAP_RATIO = 0.01
SUBSTANTIALLY_INSIDE_RATIO = 0.99


def fetch_json(url: str, params: dict[str, Any] | None = None) -> tuple[dict[str, Any], bytes]:
    target = url
    if params:
        target += "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(target, headers={"User-Agent": "VisionEvalWorkbench-reference-builder/1"})
    with urllib.request.urlopen(request, timeout=120) as response:
        raw = response.read()
    payload = json.loads(raw)
    if "error" in payload:
        raise RuntimeError(f"ArcGIS request failed: {payload['error']}")
    return payload, raw


def fetch_geojson_pages(layer_url: str, out_fields: str, page_size: int = 2000) -> tuple[list[dict[str, Any]], str]:
    features: list[dict[str, Any]] = []
    digest = hashlib.sha256()
    offset = 0
    while True:
        payload, raw = fetch_json(
            f"{layer_url}/query",
            {
                "where": "1=1",
                "outFields": out_fields,
                "returnGeometry": "true",
                "outSR": "4326",
                "resultOffset": offset,
                "resultRecordCount": page_size,
                "orderByFields": "OBJECTID",
                "f": "geojson",
            },
        )
        page = payload.get("features", [])
        digest.update(raw)
        features.extend(page)
        if len(page) < page_size:
            break
        offset += len(page)
    return features, digest.hexdigest()


def projected(geometry):
    """Project locally to metres; ratios remain stable over Virginia-sized Bzones."""
    radius = 6_371_008.8
    latitude_origin = math.radians(37.5)
    return transform(
        lambda x, y, z=None: (
            radius * math.radians(x) * math.cos(latitude_origin),
            radius * math.radians(y),
        ),
        geometry,
    )


def source_metadata(layer_url: str, item_id: str) -> dict[str, Any]:
    payload, _ = fetch_json(layer_url, {"f": "json"})
    item, _ = fetch_json(f"https://www.arcgis.com/sharing/rest/content/items/{item_id}", {"f": "json"})
    editing = payload.get("editingInfo", {})
    modified_ms = editing.get("dataLastEditDate") or editing.get("lastEditDate")
    modified = ""
    if modified_ms:
        modified = datetime.fromtimestamp(modified_ms / 1000, timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "modified": modified,
        "featureCount": None,
        "owner": item.get("owner", ""),
        "attribution": item.get("accessInformation", ""),
        "license": item.get("licenseInfo", ""),
    }


def assign_positive_area_overlaps(
    mpo_rows: list[tuple[str, str, str, Any]],
    bzone_features: list[dict[str, Any]],
    fips_names: dict[str, str],
) -> tuple[dict[str, dict[str, Any]], set[str]]:
    """Assign each Bzone to every MPO covering at least 1% of its area."""
    tree = STRtree([row[3] for row in mpo_rows])
    output = {
        region_id: {
            "officialMpoId": official_id,
            "officialName": official_name,
            "bzones": [],
            "boundaryBzones": [],
        }
        for official_id, region_id, official_name, _ in mpo_rows
    }
    unmatched_localities: set[str] = set()
    for feature in bzone_features:
        geoid = str(feature["properties"].get("GEOID", "")).strip()
        if not geoid or not feature.get("geometry"):
            continue
        geometry = projected(shape(feature["geometry"]).buffer(0))
        if geometry.is_empty or geometry.area <= 0:
            continue
        for index in tree.query(geometry):
            _, region_id, _, mpo_geometry = mpo_rows[int(index)]
            if not geometry.intersects(mpo_geometry):
                continue
            intersection_area = geometry.intersection(mpo_geometry).area
            if intersection_area <= 0:
                continue
            ratio = intersection_area / geometry.area
            if ratio < MIN_OVERLAP_RATIO:
                continue
            fips = geoid[:5]
            if fips not in fips_names:
                unmatched_localities.add(fips)
            output[region_id]["bzones"].append(geoid)
            if ratio < SUBSTANTIALLY_INSIDE_RATIO:
                output[region_id]["boundaryBzones"].append({"geoid": geoid, "overlapRatio": round(ratio, 6)})
    return output, unmatched_localities


def build(registry_path: Path) -> dict[str, Any]:
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    regions = {item["id"]: item for item in registry["regions"]}
    fips_names = {
        str(fips): str(name)
        for region in regions.values()
        for fips, name in region.get("fips", {}).items()
    }
    mpo_features, mpo_hash = fetch_geojson_pages(MPO_LAYER_URL, "MPO_ID,MPO_NAME")
    bzone_features, bzone_hash = fetch_geojson_pages(BZONE_LAYER_URL, "GEOID")
    if len(mpo_features) != 15:
        raise RuntimeError(f"Expected 15 VDOT MPO polygons; received {len(mpo_features)}")
    if len(bzone_features) < 5_000:
        raise RuntimeError(f"Expected statewide Bzones; received only {len(bzone_features)}")

    mpo_rows = []
    for feature in mpo_features:
        official_id = str(feature["properties"].get("MPO_ID", "")).strip()
        region_id = MPO_ID_TO_REGION_ID.get(official_id)
        if not region_id or region_id not in regions:
            raise RuntimeError(f"No registry mapping for VDOT MPO_ID {official_id!r}")
        geometry = projected(shape(feature["geometry"]).buffer(0))
        mpo_rows.append((official_id, region_id, str(feature["properties"].get("MPO_NAME", "")), geometry))

    output, unmatched_localities = assign_positive_area_overlaps(mpo_rows, bzone_features, fips_names)

    # Positive-area boundary overlaps may legitimately reach localities outside
    # an MPO registry entry's primary FIPS list. The statewide zone reference
    # supplies their names when the package is assembled.
    for region in output.values():
        region["bzones"].sort()
        region["boundaryBzones"].sort(key=lambda item: item["geoid"])
        region["selectedCount"] = len(region["bzones"])
        region["boundaryCount"] = len(region["boundaryBzones"])

    mpo_meta = source_metadata(MPO_LAYER_URL, MPO_ITEM_ID)
    bzone_meta = source_metadata(BZONE_LAYER_URL, BZONE_ITEM_ID)
    mpo_meta["featureCount"] = len(mpo_features)
    bzone_meta["featureCount"] = len(bzone_features)
    return {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "assignmentRule": "Include a Bzone in every MPO covering at least 1% of its projected area. Records below 99% overlap are reported as included boundary Bzones; smaller overlaps and boundary-only contact are not included.",
        "sources": {
            "mpo": {"provider": "Virginia Department of Transportation", "itemId": MPO_ITEM_ID, "layerUrl": MPO_LAYER_URL, "sha256": mpo_hash, **mpo_meta},
            "bzone": {"provider": "ArcGIS Online / UVA Library", "itemId": BZONE_ITEM_ID, "layerUrl": BZONE_LAYER_URL, "sha256": bzone_hash, **bzone_meta},
        },
        "regions": output,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, default=Path("docs/developer/reference-data/virginia_mpo_regions.json"))
    parser.add_argument("--output", type=Path, default=Path("docs/developer/reference-data/virginia_mpo_bzone_crosswalk.json"))
    args = parser.parse_args()
    payload = build(args.registry)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for region_id, region in sorted(payload["regions"].items()):
        print(f"{region_id}: {region['selectedCount']} selected, {region['boundaryCount']} included boundary")


if __name__ == "__main__":
    main()
