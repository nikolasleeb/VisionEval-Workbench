from __future__ import annotations

import csv
import json
import re
import shutil
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from .region_packages import RegionPackageService, safe_package_path
from .transit_inputs import TRANSIT_NORMALIZATION_RULE, normalize_virginia_transit_inputs
from .workspace import Workspace, WorkspaceError, fingerprint_tree, make_id, now_iso, read_json, write_json


SAFE_ASSET_NAME = re.compile(r"[^A-Za-z0-9 _.-]+")
DEFAULT_FAMPO_ID = "fredericksburg-area-mpo"
def clean_asset_name(value: str) -> str:
    name = SAFE_ASSET_NAME.sub("-", value.strip()).strip(" .-_")
    if not name:
        raise WorkspaceError("Region name is required")
    return name[:80]


def custom_region_identity(payload: dict[str, Any]) -> tuple[str, str] | None:
    if str(payload.get("geographyMode", "official")).strip().lower() != "custom":
        return None
    raw_name = str(payload.get("regionName", "")).strip()
    if not raw_name:
        raise WorkspaceError("Region name is required")
    name = clean_asset_name(raw_name)
    raw_code = str(payload.get("regionCode", "")).strip().lower()
    code = re.sub(r"[^a-z0-9_]+", "_", raw_code).strip("_")
    if not raw_code or not code:
        raise WorkspaceError("Custom region code is required")
    return name, code


def read_csv_dicts(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), [dict(row) for row in reader]


def write_csv_dicts(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


class RegionBuilderService:
    def __init__(self, workspace: Workspace, resource_root: str | Path, packages: RegionPackageService | None = None):
        self.workspace = workspace
        self.resource_root = Path(resource_root).resolve()
        self.packages = packages or RegionPackageService(workspace)

    def catalog(self) -> dict[str, Any]:
        return {"packages": self.packages.list()}

    @staticmethod
    def _normalize_crosswalk(crosswalk: dict[str, Any]) -> dict[str, Any]:
        """Treat legacy boundary exclusions as inclusions without rewriting installed packages."""
        regions = crosswalk.get("regions", {})
        if not isinstance(regions, dict):
            return crosswalk
        for spatial in regions.values():
            if not isinstance(spatial, dict):
                continue
            legacy = [item for item in spatial.get("excludedBoundaryBzones", []) if isinstance(item, dict) and item.get("geoid")]
            boundary_by_id = {
                str(item.get("geoid")): item
                for item in [*spatial.get("boundaryBzones", []), *legacy]
                if isinstance(item, dict) and item.get("geoid")
            }
            selected = {str(value) for value in spatial.get("bzones", []) if str(value)}
            selected.update(boundary_by_id)
            spatial["bzones"] = sorted(selected)
            spatial["boundaryBzones"] = [boundary_by_id[key] for key in sorted(boundary_by_id)]
            spatial["excludedBoundaryBzones"] = []
            spatial["selectedCount"] = len(selected)
            spatial["boundaryCount"] = len(boundary_by_id)
            spatial["excludedBoundaryCount"] = 0
        return crosswalk

    @staticmethod
    def _transit_normalization_rule(package_id: str, manifest: dict[str, Any]) -> str:
        declared = str(manifest.get("builder", {}).get("transitNormalization", "")).strip()
        if declared:
            return declared
        return TRANSIT_NORMALIZATION_RULE if package_id == "virginia-mpo-regions" else ""

    def _package_context(self, package_id: str) -> tuple[Path, dict[str, Any], dict[str, Any], dict[str, Any]]:
        if not package_id:
            raise WorkspaceError("Choose an installed regional package")
        root = self.packages.root(package_id)
        manifest = self.packages.manifest(package_id)
        builder = manifest["builder"]
        registry = read_json(safe_package_path(root, str(builder["regionsPath"])), {})
        crosswalk = self._normalize_crosswalk(read_json(safe_package_path(root, str(builder["crosswalkPath"])), {}))
        if not isinstance(registry.get("regions"), list) or not registry["regions"]:
            raise WorkspaceError("Regional package contains no region definitions")
        if crosswalk.get("schemaVersion") != 1 or not isinstance(crosswalk.get("regions"), dict):
            raise WorkspaceError("Regional package crosswalk is missing or invalid")
        return root, manifest, registry, crosswalk

    def _map_package_context(self, package_id: str) -> tuple[Path, dict[str, Any], dict[str, Any], dict[str, Any]]:
        if not package_id:
            raise WorkspaceError("Install a model or regional package that provides map geometry")
        root, manifest = self.packages.comparison_map_context(package_id)
        builder = manifest.get("builder", {})
        registry = read_json(safe_package_path(root, str(builder.get("regionsPath", ""))), {})
        crosswalk = self._normalize_crosswalk(read_json(safe_package_path(root, str(builder.get("crosswalkPath", ""))), {}))
        if not isinstance(registry.get("regions"), list) or not registry["regions"]:
            raise WorkspaceError("The map context contains no region definitions")
        if crosswalk.get("schemaVersion") != 1 or not isinstance(crosswalk.get("regions"), dict):
            raise WorkspaceError("The map context crosswalk is missing or invalid")
        return root, manifest, registry, crosswalk

    def reference(self, package_id: str) -> dict[str, Any]:
        root, manifest, _, crosswalk = self._package_context(package_id)
        source_path = safe_package_path(root, str(manifest["sourcesDocument"]))
        return {
            "package": {key: manifest.get(key, "") for key in ("id", "name", "version", "coverage", "description", "retrievedAt")},
            "terminology": manifest.get("terminology", {}),
            "sources": manifest.get("sources", []),
            "sourcesDocument": source_path.read_text(encoding="utf-8", errors="replace"),
            "crosswalk": {
                "generatedAt": crosswalk.get("generatedAt", ""),
                "assignmentRule": crosswalk.get("assignmentRule", ""),
                "sources": crosswalk.get("sources", {}),
            },
        }

    @staticmethod
    def _package_localities(root: Path, manifest: dict[str, Any]) -> dict[str, str]:
        relative = str(manifest.get("builder", {}).get("localitiesPath", ""))
        if not relative:
            return {}
        localities: dict[str, str] = {}
        with safe_package_path(root, relative).open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle, delimiter="|"):
                code = f"{str(row.get('STATEFP', '')).strip()}{str(row.get('COUNTYFP', '')).strip()}"
                name = str(row.get("COUNTYNAME", "")).strip()
                if code and name:
                    localities[code] = re.sub(r" city$", " City", name)
        return localities

    def regions(self, package_id: str) -> dict[str, Any]:
        root, manifest, registry, crosswalk = self._package_context(package_id)
        regions = registry["regions"]
        spatial_regions = crosswalk.get("regions", {}) if isinstance(crosswalk.get("regions"), dict) else {}
        enriched = []
        for source_region in regions:
            region = dict(source_region)
            spatial = spatial_regions.get(str(region.get("id", "")))
            if isinstance(spatial, dict):
                region["selectionMethod"] = "official-boundary-bzone-crosswalk"
                region["definitionQuality"] = "official-boundary-at-bzone-resolution"
                region["officialMpoId"] = spatial.get("officialMpoId", "")
                region["boundarySelection"] = {
                    "selectedCount": spatial.get("selectedCount", len(spatial.get("bzones", []))),
                    "boundaryCount": spatial.get("boundaryCount", len(spatial.get("boundaryBzones", []))),
                    "excludedBoundaryCount": spatial.get("excludedBoundaryCount", len(spatial.get("excludedBoundaryBzones", []))),
                }
            enriched.append(region)
        return {
            "regions": enriched,
            "package": {"id": manifest["id"], "name": manifest["name"], "coverage": manifest["coverage"]},
            "source": registry.get("source", {}),
            "boundarySource": crosswalk.get("sources", {}).get("mpo", {}),
            "boundaryGeneratedAt": crosswalk.get("generatedAt", ""),
        }

    @staticmethod
    def _validate_arcgis_url(layer_url: str) -> None:
        parsed = urllib.parse.urlparse(layer_url)
        if parsed.scheme != "https" or parsed.hostname not in {"services.arcgis.com", "services2.arcgis.com"}:
            raise WorkspaceError("The regional package map source is not an approved ArcGIS service")

    @classmethod
    def _arcgis_query(cls, layer_url: str, parameters: dict[str, str], *, limit: int = 50 * 1024 * 1024) -> dict[str, Any]:
        cls._validate_arcgis_url(layer_url)
        payload = urllib.parse.urlencode(parameters).encode("utf-8")
        request = urllib.request.Request(
            f"{layer_url.rstrip('/')}/query",
            data=payload,
            headers={"User-Agent": "VisionEvalWorkbench-region-map/1"},
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                raw = response.read(limit + 1)
        except Exception as exc:
            raise WorkspaceError("The official map services could not be reached. Region preview and build remain available offline.") from exc
        if len(raw) > limit:
            raise WorkspaceError("The official map response was larger than Workbench can display")
        result = json.loads(raw)
        if "error" in result:
            raise WorkspaceError("The official map service returned an invalid response")
        return result

    @classmethod
    def _arcgis_geojson(
        cls,
        layer_url: str,
        where: str,
        out_fields: str,
        *,
        max_allowable_offset: str = "0.00012",
    ) -> dict[str, Any]:
        parameters = {
            "where": where,
            "outFields": out_fields,
            "returnGeometry": "true",
            "outSR": "4326",
            "geometryPrecision": "5",
            "maxAllowableOffset": max_allowable_offset,
            "f": "geojson",
        }
        result = cls._arcgis_query(layer_url, parameters)
        if result.get("type") != "FeatureCollection":
            raise WorkspaceError("The official map service returned an invalid response")
        return result

    @classmethod
    def _arcgis_object_ids(cls, layer_url: str) -> tuple[str, list[int]]:
        result = cls._arcgis_query(layer_url, {
            "where": "1=1",
            "returnIdsOnly": "true",
            "returnGeometry": "false",
            "f": "json",
        })
        object_id_field = str(result.get("objectIdFieldName", ""))
        object_ids = result.get("objectIds")
        if not object_id_field or not isinstance(object_ids, list):
            raise WorkspaceError("The official map service did not provide feature identifiers")
        return object_id_field, sorted(int(value) for value in object_ids)

    @classmethod
    def _arcgis_all_geojson(cls, layer_url: str, out_fields: str, *, page_size: int = 500) -> dict[str, Any]:
        object_id_field, object_ids = cls._arcgis_object_ids(layer_url)
        features: list[dict[str, Any]] = []
        for offset in range(0, len(object_ids), page_size):
            page_ids = object_ids[offset:offset + page_size]
            page = cls._arcgis_geojson(
                layer_url,
                f"{object_id_field} IN ({','.join(str(value) for value in page_ids)})",
                out_fields,
                max_allowable_offset="0.00035",
            )
            features.extend(page.get("features", []))
        return {"type": "FeatureCollection", "features": features}

    def statewide_map_data(self, package_id: str) -> dict[str, Any]:
        root, manifest, registry, crosswalk = self._map_package_context(package_id)
        sources = crosswalk.get("sources", {})
        mpo_source = sources.get("mpo", {}) if isinstance(sources.get("mpo"), dict) else {}
        bzone_source = sources.get("bzone", {}) if isinstance(sources.get("bzone"), dict) else {}
        mpo_url = str(mpo_source.get("layerUrl", ""))
        bzone_url = str(bzone_source.get("layerUrl", ""))
        if not mpo_url or not bzone_url or not bzone_url.endswith("/0"):
            raise WorkspaceError("The regional package does not define compatible statewide map sources")
        azone_url = bzone_url[:-1] + "1"
        fingerprint = {
            "statewideSchemaVersion": 3,
            "packageVersion": str(manifest.get("version", "")),
            "crosswalkGeneratedAt": str(crosswalk.get("generatedAt", "")),
            "mpoModified": str(mpo_source.get("modified", "")),
            "zoneModified": str(bzone_source.get("modified", "")),
            "mpoLayerUrl": mpo_url,
            "zoneLayerUrl": bzone_url,
        }
        cache_root = self.workspace.exchange / "system" / "region-maps" / str(manifest["id"])
        cache_root.mkdir(parents=True, exist_ok=True)
        cache_path = cache_root / "statewide.json"
        cached = read_json(cache_path, {})
        if cached.get("sourceFingerprint") == fingerprint:
            cached["cached"] = True
            return cached

        mpo = self._arcgis_all_geojson(mpo_url, "MPO_ID,MPO_NAME")
        azones = self._arcgis_all_geojson(azone_url, "Azones")
        bzones = self._arcgis_all_geojson(bzone_url, "GEOID")

        fips_names: dict[str, str] = {}
        localities_path = str(manifest.get("builder", {}).get("localitiesPath", ""))
        if localities_path:
            with safe_package_path(root, localities_path).open("r", encoding="utf-8-sig", newline="") as handle:
                for row in csv.DictReader(handle, delimiter="|"):
                    code = f"{str(row.get('STATEFP', '')).strip()}{str(row.get('COUNTYFP', '')).strip()}"
                    name = str(row.get("COUNTYNAME", "")).strip()
                    if code and name:
                        fips_names[code] = re.sub(r" city$", " City", name)
        registry_by_official_id: dict[str, str] = {}
        spatial_regions = crosswalk.get("regions", {})
        regions: list[dict[str, Any]] = []
        for region in registry["regions"]:
            region_id = str(region.get("id", ""))
            spatial = spatial_regions.get(region_id, {}) if isinstance(spatial_regions, dict) else {}
            official_id = str(spatial.get("officialMpoId", ""))
            if official_id:
                registry_by_official_id[official_id] = region_id
            for code, name in region.get("fips", {}).items():
                fips_names[str(code)] = str(name)
            regions.append({
                "id": region_id,
                "name": str(region.get("name", region_id)),
                "shortName": str(region.get("shortName", region.get("name", region_id))),
                "officialMpoId": official_id,
                "azoneFips": sorted(str(value) for value in region.get("fips", {}).keys()),
                "selectedBzones": [str(value) for value in spatial.get("bzones", [])],
                "includedBoundaryBzones": [str(item.get("geoid", "")) for item in spatial.get("boundaryBzones", [])],
                "excludedBoundaryBzones": [str(item.get("geoid", "")) for item in spatial.get("excludedBoundaryBzones", [])],
                "includedBoundaryCases": spatial.get("boundaryBzones", []),
                "excludedBoundaryCases": spatial.get("excludedBoundaryBzones", []),
            })

        for feature in mpo.get("features", []):
            properties = feature.setdefault("properties", {})
            official_id = str(properties.get("MPO_ID", ""))
            region_id = registry_by_official_id.get(official_id, "")
            region = next((item for item in regions if item["id"] == region_id), None)
            properties.update({
                "regionId": region_id,
                "officialMpoId": official_id,
                "name": str(properties.get("MPO_NAME", "") or (region or {}).get("name", "MPO boundary")),
            })
        for feature in azones.get("features", []):
            properties = feature.setdefault("properties", {})
            code = str(properties.get("Azones", ""))
            properties.update({"azoneId": code, "localityName": fips_names.get(code, code), "name": fips_names.get(code, code)})
        for feature in bzones.get("features", []):
            properties = feature.setdefault("properties", {})
            bzone_id = str(properties.get("GEOID", ""))
            azone_id = bzone_id[:5]
            properties.update({"bzoneId": bzone_id, "azoneId": azone_id, "localityName": fips_names.get(azone_id, azone_id)})

        result = {
            "schemaVersion": 3,
            "packageId": package_id,
            "cached": False,
            "onlineGeometry": True,
            "sourceFingerprint": fingerprint,
            "assignmentRule": str(crosswalk.get("assignmentRule", "")),
            "summary": {
                "mpos": len(mpo.get("features", [])),
                "azones": len(azones.get("features", [])),
                "bzones": len(bzones.get("features", [])),
            },
            "localities": [{"azoneId": code, "localityName": name} for code, name in sorted(fips_names.items())],
            "regions": regions,
            "mpos": mpo,
            "azones": azones,
            "bzones": bzones,
            "sources": {
                "mpo": {"label": "VDOT MPO Study Areas", "url": mpo_url},
                "zones": {"label": "VisionEval Azone/Bzone geography", "url": bzone_url.rsplit("/", 1)[0]},
            },
        }
        write_json(cache_path, result)
        return result

    def map_data(self, package_id: str, region_id: str) -> dict[str, Any]:
        _, manifest, registry, crosswalk = self._package_context(package_id)
        region = next((item for item in registry["regions"] if item.get("id") == region_id), None)
        spatial = crosswalk.get("regions", {}).get(region_id)
        if not region or not isinstance(spatial, dict):
            raise WorkspaceError("Choose a region supported by the installed package")
        cache_root = self.workspace.exchange / "system" / "region-maps" / str(manifest["id"])
        cache_root.mkdir(parents=True, exist_ok=True)
        cache_path = cache_root / f"{re.sub(r'[^a-z0-9_-]+', '-', region_id.lower())}.json"
        cached = read_json(cache_path, {})
        if cached.get("crosswalkGeneratedAt") == crosswalk.get("generatedAt"):
            cached["cached"] = True
            return cached

        sources = crosswalk.get("sources", {})
        mpo_url = str(sources.get("mpo", {}).get("layerUrl", ""))
        bzone_url = str(sources.get("bzone", {}).get("layerUrl", ""))
        if not mpo_url or not bzone_url or not bzone_url.endswith("/0"):
            raise WorkspaceError("The regional package does not define compatible map sources")
        azone_url = bzone_url[:-1] + "1"
        official_id = str(spatial.get("officialMpoId", "")).replace("'", "''")
        mpo = self._arcgis_geojson(mpo_url, f"MPO_ID = '{official_id}'", "MPO_ID,MPO_NAME")
        fips = [str(value).replace("'", "''") for value in region.get("fips", {}).keys()]
        azone_where = "Azones IN (" + ",".join(f"'{value}'" for value in fips) + ")"
        azones = self._arcgis_geojson(azone_url, azone_where, "Azones")
        fips_names = {str(key): str(value) for key, value in region.get("fips", {}).items()}
        for feature in azones.get("features", []):
            code = str(feature.get("properties", {}).get("Azones", ""))
            feature.setdefault("properties", {})["name"] = fips_names.get(code, code)

        included_boundary = {str(item.get("geoid", "")) for item in spatial.get("boundaryBzones", [])}
        identifiers = sorted({str(value) for value in spatial.get("bzones", [])})
        bzone_features: list[dict[str, Any]] = []
        for offset in range(0, len(identifiers), 125):
            values = [value.replace("'", "''") for value in identifiers[offset:offset + 125]]
            where = "GEOID IN (" + ",".join(f"'{value}'" for value in values) + ")"
            page = self._arcgis_geojson(bzone_url, where, "GEOID")
            bzone_features.extend(page.get("features", []))
        for feature in bzone_features:
            geoid = str(feature.get("properties", {}).get("GEOID", ""))
            feature.setdefault("properties", {})["selection"] = "boundary" if geoid in included_boundary else "selected"

        result = {
            "schemaVersion": 1,
            "packageId": package_id,
            "regionId": region_id,
            "regionName": region.get("name", region_id),
            "crosswalkGeneratedAt": crosswalk.get("generatedAt", ""),
            "cached": False,
            "onlineGeometry": True,
            "summary": {
                "selectedBzones": len(spatial.get("bzones", [])),
                "includedBoundaryBzones": len(included_boundary),
                "excludedBoundaryBzones": 0,
                "azones": len(azones.get("features", [])),
            },
            "mpo": mpo,
            "azones": azones,
            "bzones": {"type": "FeatureCollection", "features": bzone_features},
            "sources": {
                "mpo": {"label": "VDOT MPO Study Areas", "url": mpo_url},
                "zones": {"label": "VisionEval Azone/Bzone geography", "url": bzone_url.rsplit("/", 1)[0]},
            },
        }
        write_json(cache_path, result)
        return result

    def sources(self, package_id: str) -> dict[str, Any]:
        root, manifest, _, _ = self._package_context(package_id)
        input_config = manifest["inputLibrary"]
        packaged = safe_package_path(root, str(input_config["path"]))
        required = {str(item) for item in input_config.get("requiredFiles", [])}
        sources: list[dict[str, Any]] = [{
            "id": f"package:{package_id}",
            "name": str(input_config.get("name") or f"{manifest['coverage']} InputLibrary"),
            "kind": "package",
            "fileCount": len([path for path in packaged.iterdir() if path.is_file()]),
        }]
        for item in self.workspace.list_input_libraries():
            library_path = self.workspace.input_library / item["id"]
            if all((library_path / filename).is_file() for filename in required):
                sources.append({
                    "id": f"workspace:{item['id']}",
                    "name": f"{item['name']} (workspace)",
                    "kind": "workspace",
                    "fileCount": item["fileCount"],
                })
        return {"packageId": package_id, "sources": sources}

    def _source_library_path(self, package_id: str, source_library_id: str) -> tuple[Path, dict[str, Any]]:
        root, manifest, _, _ = self._package_context(package_id)
        if source_library_id == f"package:{package_id}":
            config = manifest["inputLibrary"]
            path = safe_package_path(root, str(config["path"]))
            return path, {"id": source_library_id, "name": str(config.get("name") or manifest["name"]), "kind": "package"}
        if source_library_id.startswith("workspace:"):
            library_id = source_library_id.split(":", 1)[1]
            path = self.workspace.within(self.workspace.input_library / library_id, self.workspace.input_library)
            return path, {"id": source_library_id, "name": library_id, "kind": "workspace"}
        raise WorkspaceError("Choose a compatible source InputLibrary")

    def _region(self, package_id: str, region_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        _, manifest, _, crosswalk = self._package_context(package_id)
        region = next((item for item in self.regions(package_id)["regions"] if item.get("id") == region_id), None)
        if not region:
            raise WorkspaceError("Choose a region supported by the installed package")
        return region, crosswalk, manifest

    @staticmethod
    def _package_locality_names(package_root: Path, manifest: dict[str, Any]) -> dict[str, str]:
        relative = str(manifest.get("builder", {}).get("localitiesPath", "")).strip()
        if not relative:
            return {}
        path = safe_package_path(package_root, relative)
        if not path.is_file():
            return {}
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = csv.DictReader(handle, delimiter="|")
            return {
                f"{str(row.get('STATEFP') or '').strip()}{str(row.get('COUNTYFP') or '').strip()}":
                    str(row.get("COUNTYNAME") or "").strip()
                for row in rows
                if str(row.get("STATEFP") or "").strip()
                and str(row.get("COUNTYFP") or "").strip()
                and str(row.get("COUNTYNAME") or "").strip()
            }

    def geography_options(self, package_id: str, source_library_id: str, region_id: str) -> dict[str, Any]:
        package_root, package_manifest, _, _ = self._package_context(package_id)
        input_path, _ = self._source_library_path(package_id, source_library_id)
        region, crosswalk, manifest = self._region(package_id, region_id)
        bzone_path = input_path / "bzone_lat_lon.csv"
        if not bzone_path.is_file():
            raise WorkspaceError("The regional InputLibrary must contain bzone_lat_lon.csv")
        fields, rows = read_csv_dicts(bzone_path)
        if "Geo" not in fields:
            raise WorkspaceError("bzone_lat_lon.csv must contain Geo")
        prefix_length = int(manifest.get("builder", {}).get("localityPrefixLength", 5))
        fips_to_azone = {str(key): str(value) for key, value in dict(region.get("fips") or {}).items()}
        spatial = crosswalk.get("regions", {}).get(region_id, {})
        official = {str(value) for value in spatial.get("bzones", [])} if isinstance(spatial, dict) else set()
        locality_names = self._package_locality_names(package_root, manifest)
        available_fips = {
            str(row.get("Geo", "")).strip()[:prefix_length]
            for row in rows if str(row.get("Geo", "")).strip()
        }
        # Custom regions are allowed to span any locality that has Bzones in
        # the installed InputLibrary. The selected MPO remains a convenient
        # starting selection, not a boundary on planner-defined geography.
        for fips, name in locality_names.items():
            if fips in available_fips:
                fips_to_azone.setdefault(fips, name)
        by_fips: dict[str, set[str]] = {fips: set() for fips in fips_to_azone}
        for row in rows:
            bzone = str(row.get("Geo", "")).strip()
            fips = bzone[:prefix_length]
            if bzone and fips in by_fips:
                by_fips[fips].add(bzone)
        if not official:
            official = {value for values in by_fips.values() for value in values}
        azones = [
            {"fips": fips, "name": name, "bzoneCount": len(by_fips.get(fips, []))}
            for fips, name in sorted(fips_to_azone.items(), key=lambda item: item[1].lower())
        ]
        bzones = [
            {"id": bzone, "fips": fips, "azone": fips_to_azone[fips], "official": bzone in official}
            for fips in sorted(by_fips, key=lambda value: fips_to_azone[value].lower())
            for bzone in sorted(by_fips[fips])
        ]
        available_bzones = {item["id"] for item in bzones}
        # Geography options are also an API contract for map-driven custom
        # selection, so return MPO boundaries even before the separate map
        # endpoint has happened to populate its cache.
        try:
            statewide_cache = self.statewide_map_data(package_id)
        except WorkspaceError:
            # Boundary geometry is an enhancement for the custom-region map,
            # not a reason to make the underlying membership choices fail
            # when the package's remote boundary source is unavailable.
            statewide_cache = read_json(
                self.workspace.exchange / "region-builder" / package_id / "statewide.json",
                {},
            )
        cached_boundaries: dict[str, Any] = {}
        for feature in statewide_cache.get("mpos", {}).get("features", []):
            properties = feature.get("properties", {})
            for identifier in (
                properties.get("regionId"),
                properties.get("officialMpoId"),
                properties.get("MPO_ID"),
            ):
                if identifier:
                    cached_boundaries[str(identifier)] = feature.get("geometry")
        mpo_options = []
        for candidate in self.regions(package_id).get("regions", []):
            if candidate.get("regionType") == "statewide":
                continue
            candidate_id = str(candidate.get("id") or "")
            candidate_spatial = crosswalk.get("regions", {}).get(candidate_id, {})
            candidate_bzones = {
                str(value) for value in candidate_spatial.get("bzones", [])
            } if isinstance(candidate_spatial, dict) else set()
            mpo_options.append({
                "id": candidate_id,
                "name": str(candidate.get("name") or candidate_id),
                "officialMpoId": str(candidate.get("officialMpoId") or ""),
                "boundary": cached_boundaries.get(candidate_id)
                    or cached_boundaries.get(str(candidate.get("officialMpoId") or "")),
                "bzones": sorted(candidate_bzones & available_bzones),
            })
        return {
            "region": {"id": region_id, "name": region.get("name", "")},
            "azones": azones,
            "bzones": bzones,
            "officialBzones": sorted(official),
            "mpos": sorted(mpo_options, key=lambda item: item["name"].lower()),
            "counts": {"azones": len(azones), "bzones": len(bzones), "officialBzones": len(official)},
        }

    @staticmethod
    def _selected_values(payload: dict[str, Any], key: str) -> set[str]:
        raw = payload.get(key, [])
        if isinstance(raw, str):
            parts = re.split(r"[\n,]+", raw)
        elif isinstance(raw, list):
            parts = raw
        else:
            parts = []
        return {str(item).strip() for item in parts if str(item).strip()}

    def _source(self, template_id: str) -> tuple[Path, dict[str, Any], list[str], list[dict[str, str]]]:
        template_path, template = self.workspace.template(template_id)
        geo_path = template_path / "defs" / "geo.csv"
        if not geo_path.is_file():
            raise WorkspaceError("The source template is missing defs/geo.csv")
        fields, rows = read_csv_dicts(geo_path)
        for field in ("Azone", "Bzone", "Marea"):
            if field not in fields:
                raise WorkspaceError(f"defs/geo.csv must contain {field}")
        if not rows:
            raise WorkspaceError("defs/geo.csv has no geography rows")
        return template_path, template, fields, rows

    def _selection(self, geo_rows: list[dict[str, str]], payload: dict[str, Any]) -> dict[str, Any]:
        selected_bzones = self._selected_values(payload, "selectedBzones")
        selected_azones = self._selected_values(payload, "selectedAzones")
        all_bzones = {str(row.get("Bzone", "")).strip() for row in geo_rows if str(row.get("Bzone", "")).strip() not in {"", "NA"}}
        all_azones = {str(row.get("Azone", "")).strip() for row in geo_rows if str(row.get("Azone", "")).strip() not in {"", "NA"}}
        missing_bzones = sorted(selected_bzones - all_bzones)
        missing_azones = sorted(selected_azones - all_azones)
        if missing_bzones:
            raise WorkspaceError(f"Selected Bzones are not in defs/geo.csv: {', '.join(missing_bzones[:8])}")
        if missing_azones:
            raise WorkspaceError(f"Selected Azones are not in defs/geo.csv: {', '.join(missing_azones[:8])}")
        if not selected_bzones and not selected_azones:
            raise WorkspaceError("Select at least one Azone or Bzone")
        selected_geo_rows = [
            row for row in geo_rows
            if str(row.get("Bzone", "")).strip() in selected_bzones
            or str(row.get("Azone", "")).strip() in selected_azones
        ]
        if not selected_geo_rows:
            raise WorkspaceError("The selected geography did not match any Bzones")
        bzones = {str(row.get("Bzone", "")).strip() for row in selected_geo_rows if str(row.get("Bzone", "")).strip() not in {"", "NA"}}
        azones = {str(row.get("Azone", "")).strip() for row in selected_geo_rows if str(row.get("Azone", "")).strip() not in {"", "NA"}}
        mareas = {str(row.get("Marea", "")).strip() for row in selected_geo_rows if str(row.get("Marea", "")).strip() not in {"", "NA"}}
        return {
            "geoRows": selected_geo_rows,
            "bzones": bzones,
            "azones": azones,
            "mareas": mareas,
        }

    @staticmethod
    def _level_for_input(name: str) -> str:
        lower = name.lower()
        for prefix, level in (("bzone_", "bzone"), ("azone_", "azone"), ("marea_", "marea")):
            if lower.startswith(prefix):
                return level
        return ""

    def _input_plan(self, template_path: Path, selection: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
        inputs = template_path / "inputs"
        if not inputs.is_dir():
            raise WorkspaceError("The source template is missing inputs/")
        plan: list[dict[str, Any]] = []
        errors: list[str] = []
        selected_by_level = {
            "bzone": selection["bzones"],
            "azone": selection["azones"],
            "marea": selection["mareas"],
        }
        for source in sorted((path for path in inputs.iterdir() if path.is_file()), key=lambda path: path.name.lower()):
            if not source.name.lower().endswith(".csv"):
                plan.append({"file": source.name, "action": "copy", "rowsBefore": None, "rowsAfter": None, "level": ""})
                continue
            level = self._level_for_input(source.name)
            fields, rows = read_csv_dicts(source)
            if level:
                if "Geo" not in fields:
                    errors.append(f"{source.name} is a {level} file but has no Geo column")
                    continue
                selected = selected_by_level[level]
                kept = [row for row in rows if str(row.get("Geo", "")).strip() in selected]
                if level == "marea":
                    available = {str(row.get("Geo", "")).strip() for row in rows}
                    missing = sorted(selected - available)
                    if missing:
                        errors.append(f"{source.name} is missing selected Marea rows: {', '.join(missing[:8])}")
                plan.append({"file": source.name, "action": "filter", "rowsBefore": len(rows), "rowsAfter": len(kept), "level": level})
            else:
                plan.append({"file": source.name, "action": "copy", "rowsBefore": len(rows), "rowsAfter": len(rows), "level": ""})
        if errors:
            raise WorkspaceError("; ".join(errors))
        return plan, errors

    def _input_plan_for_library(self, input_path: Path, selection: dict[str, Any], default_files: set[str] | None = None) -> list[dict[str, Any]]:
        plan, _ = self._input_plan_from_path(input_path, selection, default_files)
        return plan

    def _input_plan_from_path(self, inputs: Path, selection: dict[str, Any], default_files: set[str] | None = None) -> tuple[list[dict[str, Any]], list[str]]:
        if not inputs.is_dir():
            raise WorkspaceError("The source InputLibrary is missing")
        plan: list[dict[str, Any]] = []
        errors: list[str] = []
        selected_by_level = {"bzone": selection["bzones"], "azone": selection["azones"], "marea": selection["mareas"]}
        for source in sorted((path for path in inputs.iterdir() if path.is_file()), key=lambda path: path.name.lower()):
            if source.name == "region_builder_manifest.json":
                continue
            if not source.name.lower().endswith(".csv"):
                plan.append({"file": source.name, "action": "copy", "rowsBefore": None, "rowsAfter": None, "level": ""})
                continue
            level = self._level_for_input(source.name)
            fields, rows = read_csv_dicts(source)
            if level:
                if "Geo" not in fields:
                    errors.append(f"{source.name} is a {level} file but has no Geo column")
                    continue
                selected = selected_by_level[level]
                kept = [row for row in rows if str(row.get("Geo", "")).strip() in selected]
                if level == "marea":
                    available = {str(row.get("Geo", "")).strip() for row in rows}
                    missing = sorted(selected - available)
                    if missing:
                        errors.append(f"{source.name} is missing selected Marea rows: {', '.join(missing[:8])}")
                plan.append({"file": source.name, "action": "filter", "rowsBefore": len(rows), "rowsAfter": len(kept), "level": level})
            else:
                plan.append({"file": source.name, "action": "copy", "rowsBefore": len(rows), "rowsAfter": len(rows), "level": ""})
        present = {item["file"] for item in plan}
        years = sorted(selection["years"])
        for missing in sorted((default_files or set()) - present):
            plan.append({
                "file": missing,
                "action": "default",
                "rowsBefore": 0,
                "rowsAfter": len(selection["azones"]) * len(years),
                "level": "azone",
            })
        if errors:
            raise WorkspaceError("; ".join(errors))
        return sorted(plan, key=lambda item: item["file"].lower()), errors

    @staticmethod
    def _years_from_library(input_path: Path) -> set[str]:
        years: set[str] = set()
        for path in input_path.glob("*.csv"):
            fields, rows = read_csv_dicts(path)
            if "Year" in fields:
                years.update(str(row.get("Year", "")).strip() for row in rows if str(row.get("Year", "")).strip())
        return years or {"2024", "2045"}

    def _package_selection(self, input_path: Path, region: dict[str, Any], crosswalk: dict[str, Any], manifest: dict[str, Any], payload: dict[str, Any] | None = None, locality_names: dict[str, str] | None = None) -> dict[str, Any]:
        bzone_path = input_path / "bzone_lat_lon.csv"
        if not bzone_path.is_file():
            raise WorkspaceError("The regional InputLibrary must contain bzone_lat_lon.csv")
        fips_to_azone = {str(key): str(value) for key, value in dict(region.get("fips") or {}).items()}
        if not fips_to_azone:
            raise WorkspaceError("The selected region does not define locality-to-Azone mappings")
        fields, rows = read_csv_dicts(bzone_path)
        if "Geo" not in fields:
            raise WorkspaceError("bzone_lat_lon.csv must contain Geo")
        available_bzones = {str(row.get("Geo", "")).strip() for row in rows if str(row.get("Geo", "")).strip()}
        spatial = crosswalk.get("regions", {}).get(str(region.get("id", "")), {}) if crosswalk else {}
        spatial_bzones = {str(value) for value in spatial.get("bzones", [])} if isinstance(spatial, dict) else set()
        geography_mode = str((payload or {}).get("geographyMode", "official")).strip().lower()
        custom_bzones = self._selected_values(payload or {}, "selectedBzones")
        prefix_length = int(manifest.get("builder", {}).get("localityPrefixLength", 5))
        official_fips = set(fips_to_azone)
        if locality_names:
            available_fips = {value[:prefix_length] for value in available_bzones}
            for fips, name in locality_names.items():
                if fips in available_fips:
                    fips_to_azone.setdefault(fips, name)
        eligible_bzones = {value for value in available_bzones if value[:prefix_length] in official_fips}
        statewide = region.get("regionType") == "statewide"
        if statewide:
            raise WorkspaceError("Virginia statewide model creation is not supported. Choose an MPO study area.")
        elif geography_mode == "custom":
            if not custom_bzones:
                raise WorkspaceError("Custom geography must include at least one Bzone")
            ineligible = sorted(custom_bzones - available_bzones)
            if ineligible:
                raise WorkspaceError(
                    "Custom Bzones are not available in the selected regional InputLibrary: " + ", ".join(ineligible[:8])
                )
            bzones = sorted(custom_bzones)
            selection_method = "custom-bzone-selection"
        elif spatial_bzones:
            missing = sorted(spatial_bzones - available_bzones)
            if missing:
                raise WorkspaceError(
                    f"The regional boundary crosswalk contains {len(missing)} Bzones absent from this InputLibrary; install or choose the matching data vintage"
                )
            bzones = sorted(spatial_bzones)
            selection_method = "official-boundary-bzone-crosswalk"
        else:
            bzones = sorted(eligible_bzones)
            selection_method = "whole-jurisdiction-fips-fallback"
        if not bzones:
            raise WorkspaceError("The selected region did not match any Bzones")
        years = self._years_from_library(input_path)
        selected_fips = {bzone[:prefix_length] for bzone in bzones}
        missing_fips = sorted(selected_fips - set(fips_to_azone))
        if missing_fips:
            raise WorkspaceError("Selected region Bzones have unmapped locality identifiers: " + ", ".join(missing_fips))
        azones = {fips_to_azone[fips] for fips in selected_fips}
        mareas = set(azones)
        geo_rows = [
            {"Azone": fips_to_azone[bzone[:prefix_length]], "Bzone": bzone, "Czone": "NA", "Marea": fips_to_azone[bzone[:prefix_length]]}
            for bzone in bzones
        ]
        added_bzones = sorted(set(bzones) - spatial_bzones) if geography_mode == "custom" else []
        removed_bzones = sorted(spatial_bzones - set(bzones)) if geography_mode == "custom" else []
        return {
            "geoRows": geo_rows,
            "bzones": set(bzones),
            "azones": azones,
            "mareas": mareas,
            "years": years,
            "selectionMethod": selection_method,
            "boundary": {
                "generatedAt": crosswalk.get("generatedAt", "") if spatial_bzones else "",
                "assignmentRule": crosswalk.get("assignmentRule", "") if spatial_bzones else "",
                "sources": crosswalk.get("sources", {}) if spatial_bzones else {},
                "selectedCount": len(bzones),
                "boundaryCount": int(spatial.get("boundaryCount", len(spatial.get("boundaryBzones", [])))) if spatial_bzones else 0,
                "excludedBoundaryCount": int(spatial.get("excludedBoundaryCount", len(spatial.get("excludedBoundaryBzones", [])))) if spatial_bzones else 0,
                "boundaryBzones": spatial.get("boundaryBzones", []) if spatial_bzones else [],
                "excludedBoundaryBzones": spatial.get("excludedBoundaryBzones", []) if spatial_bzones else [],
                "officialSelectedCount": len(spatial_bzones),
                "customized": geography_mode == "custom",
                "addedBzones": added_bzones,
                "removedBzones": removed_bzones,
            },
        }

    def _preview_package_region(self, payload: dict[str, Any]) -> dict[str, Any]:
        identity = custom_region_identity(payload)
        package_id = str(payload.get("packageId", "")).strip()
        package_root, _, _, _ = self._package_context(package_id)
        input_path, source = self._source_library_path(package_id, str(payload.get("sourceLibraryId", "")).strip())
        region, crosswalk, manifest = self._region(package_id, str(payload.get("regionId", "")).strip())
        selection = self._package_selection(
            input_path, region, crosswalk, manifest, payload,
            self._package_locality_names(package_root, manifest),
        )
        default_files = {str(item) for item in manifest.get("builder", {}).get("defaultFiles", [])}
        input_plan = self._input_plan_for_library(input_path, selection, default_files)
        warnings = self._boundary_warnings(manifest, selection) + self._warnings_for_plan(input_plan, manifest)
        if self._transit_normalization_rule(package_id, manifest):
            warnings.append("Missing Virginia transit technology fields will be completed with documented service-derived compatibility assumptions during build.")
        preview_region = dict(region)
        if identity:
            preview_region["name"], preview_region["defaultRegionCode"] = identity
        return {
            "package": {"id": manifest["id"], "name": manifest["name"], "version": manifest["version"], "coverage": manifest["coverage"]},
            "sourceLibrary": source,
            "region": preview_region,
            "selection": {
                "geoRows": len(selection["geoRows"]),
                "azones": sorted(selection["azones"], key=str.lower),
                "bzones": sorted(selection["bzones"]),
                "mareas": sorted(selection["mareas"], key=str.lower),
                "method": selection["selectionMethod"],
                "boundary": selection["boundary"],
            },
            "files": input_plan,
            "geoFields": ["Azone", "Bzone", "Czone", "Marea"],
            "warnings": warnings,
        }

    @staticmethod
    def _warnings_for_plan(input_plan: list[dict[str, Any]], manifest: dict[str, Any]) -> list[str]:
        warnings = ["Region and non-spatial files are copied unchanged from the installed regional package."]
        defaulted = [item["file"] for item in input_plan if item["action"] == "default"]
        if defaulted:
            warnings.append("Defaulted missing package inputs: " + ", ".join(defaulted))
        return warnings

    @staticmethod
    def _boundary_warnings(manifest: dict[str, Any], selection: dict[str, Any] | None = None) -> list[str]:
        if selection and selection.get("selectionMethod") == "package-statewide":
            return [
                f"This build includes the complete packaged geography: {len(selection.get('azones', [])):,} localities and {len(selection.get('bzones', [])):,} Bzones.",
                "Statewide model generation and execution can require substantial memory, disk space, and runtime. Review Docker resources before running.",
            ]
        if selection and selection.get("selectionMethod") == "official-boundary-bzone-crosswalk":
            boundary = selection.get("boundary", {})
            authority = str(manifest.get("builder", {}).get("boundaryAuthority") or "official boundary geometry")
            return [
                f"{authority} selected {boundary.get('selectedCount', 0):,} Bzones, including "
                f"{boundary.get('boundaryCount', 0):,} boundary overlaps of at least 1%.",
                "The boundary is represented at complete-Bzone resolution. Azone and Marea inputs remain whole-locality values and require review before policy use.",
            ]
        if selection and selection.get("selectionMethod") == "custom-bzone-selection":
            boundary = selection.get("boundary", {})
            return [
                f"Custom geography includes {boundary.get('selectedCount', 0):,} Bzones: "
                f"{len(boundary.get('addedBzones', [])):,} added and {len(boundary.get('removedBzones', [])):,} removed versus the official MPO selection.",
                "Custom geography is planner-defined. Review the selected Azones and Bzones before policy use.",
            ]
        return ["The installed package has no usable boundary crosswalk; this build uses its whole-locality fallback."]

    def preview(self, payload: dict[str, Any]) -> dict[str, Any]:
        if payload.get("packageId"):
            return self._preview_package_region(payload)
        source_template_id = str(payload.get("sourceTemplateId", "")).strip()
        template_path, template, geo_fields, geo_rows = self._source(source_template_id)
        selection = self._selection(geo_rows, payload)
        input_plan, _ = self._input_plan(template_path, selection)
        return {
            "sourceTemplate": {"id": template["id"], "name": template["name"], "fingerprint": template.get("fingerprint", "")},
            "selection": {
                "geoRows": len(selection["geoRows"]),
                "azones": sorted(selection["azones"], key=str.lower),
                "bzones": sorted(selection["bzones"]),
                "mareas": sorted(selection["mareas"], key=str.lower),
            },
            "files": input_plan,
            "geoFields": geo_fields,
            "warnings": [
                "Region and non-spatial files are copied unchanged for this VA-first MVP.",
            ],
        }

    @staticmethod
    def _replace_config_value(text: str, field: str, value: str) -> str:
        pattern = re.compile(rf"(?m)^(\s*{re.escape(field)}\s*:\s*).*$")
        replacement = rf"\g<1>{value}"
        return pattern.sub(replacement, text) if pattern.search(text) else f"{text.rstrip()}\n{field}: {value}\n"

    def build(self, payload: dict[str, Any]) -> dict[str, Any]:
        if payload.get("packageId"):
            return self._build_package_region(payload)
        region_name = clean_asset_name(str(payload.get("regionName", "")))
        source_template_id = str(payload.get("sourceTemplateId", "")).strip()
        state_abbr = str(payload.get("stateAbbr", "VA")).strip().upper()[:8] or "VA"
        region_code = re.sub(r"[^a-z0-9_]+", "_", str(payload.get("regionCode", region_name)).strip().lower()).strip("_") or region_name.lower().replace(" ", "_")
        template_path, template, geo_fields, geo_rows = self._source(source_template_id)
        selection = self._selection(geo_rows, payload)
        input_plan, _ = self._input_plan(template_path, selection)

        library_id = region_name
        library_target = self.workspace.input_library / library_id
        if library_target.exists():
            raise WorkspaceError(f"Input library already exists: {library_id}")
        template_id = make_id("template", region_name)
        template_target = self.workspace.templates / template_id
        if template_target.exists():
            raise WorkspaceError("Generated template already exists; choose a different region name")

        staging_root = self.workspace.internal / "staging"; staging_root.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix="region-builder.", dir=staging_root))
        try:
            library_stage = staging / "InputLibrary" / library_id
            template_stage = staging / "ModelTemplates" / template_id
            shutil.copytree(template_path, template_stage, ignore=shutil.ignore_patterns("results", "workbench_template.json", ".DS_Store", ".workbench-*"))
            shutil.rmtree(template_stage / "inputs", ignore_errors=True)
            (template_stage / "inputs").mkdir(parents=True, exist_ok=True)
            library_stage.mkdir(parents=True, exist_ok=True)
            write_csv_dicts(template_stage / "defs" / "geo.csv", geo_fields, selection["geoRows"])

            plan_by_file = {item["file"]: item for item in input_plan}
            for source in sorted((path for path in (template_path / "inputs").iterdir() if path.is_file()), key=lambda path: path.name.lower()):
                library_output = library_stage / source.name
                template_output = template_stage / "inputs" / source.name
                item = plan_by_file[source.name]
                if item["action"] == "filter":
                    fields, rows = read_csv_dicts(source)
                    selected = {"bzone": selection["bzones"], "azone": selection["azones"], "marea": selection["mareas"]}[item["level"]]
                    kept = [row for row in rows if str(row.get("Geo", "")).strip() in selected]
                    write_csv_dicts(library_output, fields, kept)
                    write_csv_dicts(template_output, fields, kept)
                else:
                    shutil.copy2(source, library_output)
                    shutil.copy2(source, template_output)

            config_path = template_stage / "visioneval.cnf"
            config = config_path.read_text(encoding="utf-8", errors="replace")
            config = self._replace_config_value(config, "Region", region_code)
            config = self._replace_config_value(config, "State", state_abbr)
            config = self._replace_config_value(config, "Description", f"Region Builder generated region for {region_name}")
            config_path.write_text(config, encoding="utf-8")

            validation = self.workspace.validate_template(template_stage)
            if not validation["valid"]:
                raise WorkspaceError("Generated model template is invalid: " + "; ".join(validation["errors"]))
            template_record = {
                "version": 1,
                "id": template_id,
                "name": region_name,
                "source": f"Region Builder from {template.get('name', source_template_id)}",
                "sourceTemplateId": template["id"],
                "importedAt": now_iso(),
                "fingerprint": validation["fingerprint"],
                "inputFiles": validation["inputFiles"],
                "regionBuilder": True,
            }
            manifest = {
                "version": 1,
                "regionName": region_name,
                "regionCode": region_code,
                "state": state_abbr,
                "sourceTemplate": {"id": template["id"], "name": template["name"], "fingerprint": template.get("fingerprint", "")},
                "builtAt": now_iso(),
                "selection": {
                    "geoRows": len(selection["geoRows"]),
                    "azones": sorted(selection["azones"], key=str.lower),
                    "bzones": sorted(selection["bzones"]),
                    "mareas": sorted(selection["mareas"], key=str.lower),
                },
                "files": input_plan,
                "warnings": ["Region and non-spatial files were copied unchanged."],
            }
            write_json(template_stage / "workbench_template.json", template_record)
            write_json(template_stage / "region_builder_manifest.json", manifest)
            write_json(library_stage / "region_builder_manifest.json", manifest)
            template_record["fingerprint"] = fingerprint_tree(template_stage, ["visioneval.cnf", "scripts/run_model.R", *[f"defs/{p.name}" for p in (template_stage / "defs").glob("*") if p.is_file()]])
            write_json(template_stage / "workbench_template.json", template_record)

            shutil.move(str(library_stage), str(library_target))
            shutil.move(str(template_stage), str(template_target))
            settings = self.workspace.settings()
            settings["defaultInputLibraryId"] = library_id
            settings["defaultTemplateId"] = template_id
            write_json(self.workspace.settings_path, settings)
        finally:
            shutil.rmtree(staging, ignore_errors=True)

        return {
            "inputLibrary": {"id": library_id, "name": library_id},
            "modelTemplate": {"id": template_id, "name": region_name},
            "selection": self.preview({**payload, "sourceTemplateId": template_id})["selection"],
        }

    def _default_rows(self, filename: str, input_path: Path, selection: dict[str, Any]) -> tuple[list[str], list[dict[str, str]], str]:
        azones = sorted(selection["azones"], key=str.lower)
        years = sorted(selection["years"])
        if filename == "azone_lttrk_prop.csv" and (input_path / "azone_hh_lttrk_prop.csv").is_file():
            fields, rows = read_csv_dicts(input_path / "azone_hh_lttrk_prop.csv")
            return fields, [row for row in rows if str(row.get("Geo", "")).strip() in selection["azones"]], "copied from azone_hh_lttrk_prop.csv"
        if filename == "azone_relative_employment.csv":
            fields = ["Geo", "Year", "RelEmp15to19", "RelEmp20to29", "RelEmp30to54", "RelEmp55to64", "RelEmp65Plus"]
            return fields, [{"Geo": geo, "Year": year, **{field: "1" for field in fields[2:]}} for geo in azones for year in years], "neutral relative employment defaults"
        if filename == "azone_carsvc_characteristics.csv":
            fields = ["Geo", "Year", "HighCarSvcCost.2024", "LowCarSvcCost.2024", "AveCarSvcVehicleAge", "LtTrkCarSvcSubProp", "AutoCarSvcSubProp"]
            defaults = {"HighCarSvcCost.2024": "2.16", "LowCarSvcCost.2024": "3.73", "AveCarSvcVehicleAge": "5", "LtTrkCarSvcSubProp": "0.45", "AutoCarSvcSubProp": "0.55"}
            return fields, [{"Geo": geo, "Year": year, **defaults} for geo in azones for year in years], "regional package car-service defaults replicated to selected Azones"
        raise WorkspaceError(f"No default rule is defined for {filename}")

    def _write_filtered_or_default(self, source: Path, filename: str, target_paths: list[Path], selection: dict[str, Any], input_path: Path, manifest_defaults: list[dict[str, str]]) -> None:
        if source.is_file():
            if filename.lower().endswith(".csv"):
                level = self._level_for_input(filename)
                fields, rows = read_csv_dicts(source)
                if level:
                    selected = {"bzone": selection["bzones"], "azone": selection["azones"], "marea": selection["mareas"]}[level]
                    rows = [row for row in rows if str(row.get("Geo", "")).strip() in selected]
                for target in target_paths:
                    write_csv_dicts(target, fields, rows)
            else:
                for target in target_paths:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
            return
        fields, rows, rule = self._default_rows(filename, input_path, selection)
        manifest_defaults.append({"file": filename, "rule": rule})
        for target in target_paths:
            write_csv_dicts(target, fields, rows)

    def _build_package_region(self, payload: dict[str, Any]) -> dict[str, Any]:
        custom_region_identity(payload)
        package_id = str(payload.get("packageId", "")).strip()
        package_root, package_manifest, _, _ = self._package_context(package_id)
        input_path, source = self._source_library_path(package_id, str(payload.get("sourceLibraryId", "")).strip())
        region, crosswalk, package_manifest = self._region(package_id, str(payload.get("regionId", "")).strip())
        region_name = clean_asset_name(str(payload.get("regionName", "")).strip() or str(region.get("name", "")))
        region_code = re.sub(r"[^a-z0-9_]+", "_", str(payload.get("regionCode", "") or region.get("defaultRegionCode") or region_name).strip().lower()).strip("_")
        state_abbr = str(payload.get("stateAbbr", "") or region.get("state") or package_manifest.get("state") or "").strip().upper()[:8]
        selection = self._package_selection(
            input_path, region, crosswalk, package_manifest, payload,
            self._package_locality_names(package_root, package_manifest),
        )
        default_files = {str(item) for item in package_manifest.get("builder", {}).get("defaultFiles", [])}
        input_plan = self._input_plan_for_library(input_path, selection, default_files)
        packaged_template = str(package_manifest.get("builder", {}).get("modelTemplatePath", "")).strip()
        if not packaged_template:
            raise WorkspaceError("The regional package does not declare a model template scaffold")
        base_template = safe_package_path(package_root, packaged_template)
        if not (base_template / "visioneval.cnf").is_file():
            raise WorkspaceError("The regional package model template scaffold is unavailable")

        library_id = region_name
        library_target = self.workspace.input_library / library_id
        if library_target.exists():
            raise WorkspaceError(f"Input library already exists: {library_id}")
        template_id = make_id("template", region_name)
        template_target = self.workspace.templates / template_id
        if template_target.exists():
            raise WorkspaceError("Generated template already exists; choose a different region name")
        staging_root = self.workspace.internal / "staging"; staging_root.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix="region-builder.", dir=staging_root))
        manifest_defaults: list[dict[str, str]] = []
        try:
            library_stage = staging / "InputLibrary" / library_id
            template_stage = staging / "ModelTemplates" / template_id
            shutil.copytree(base_template, template_stage, ignore=shutil.ignore_patterns("results", "workbench_template.json", ".DS_Store", ".workbench-*"))
            shutil.rmtree(template_stage / "inputs", ignore_errors=True)
            (template_stage / "inputs").mkdir(parents=True, exist_ok=True)
            library_stage.mkdir(parents=True, exist_ok=True)
            write_csv_dicts(template_stage / "defs" / "geo.csv", ["Azone", "Bzone", "Czone", "Marea"], selection["geoRows"])

            output_files = sorted({path.name for path in input_path.iterdir() if path.is_file() and path.name != "region_builder_manifest.json"} | default_files, key=str.lower)
            for filename in output_files:
                source_file = input_path / filename
                self._write_filtered_or_default(source_file, filename, [library_stage / filename, template_stage / "inputs" / filename], selection, input_path, manifest_defaults)

            transit_normalization = {"rule": "", "applied": False, "adjustments": []}
            normalization_rule = self._transit_normalization_rule(package_id, package_manifest)
            if normalization_rule:
                if normalization_rule != TRANSIT_NORMALIZATION_RULE:
                    raise WorkspaceError(f"Unsupported transit normalization rule: {normalization_rule}")
                try:
                    transit_normalization = normalize_virginia_transit_inputs(library_stage)
                except (OSError, csv.Error, ValueError) as exc:
                    raise WorkspaceError(f"Virginia transit inputs could not be completed: {exc}") from exc
                for filename in ("marea_transit_fuel.csv", "marea_transit_powertrain_prop.csv"):
                    normalized = library_stage / filename
                    if normalized.is_file():
                        shutil.copy2(normalized, template_stage / "inputs" / filename)

            config_path = template_stage / "visioneval.cnf"
            config = config_path.read_text(encoding="utf-8", errors="replace")
            config = self._replace_config_value(config, "Region", region_code)
            config = self._replace_config_value(config, "State", state_abbr)
            config = self._replace_config_value(config, "Description", f"Region Builder generated {package_manifest['coverage']} region for {region_name}")
            config_path.write_text(config, encoding="utf-8")

            validation = self.workspace.validate_template(template_stage)
            if not validation["valid"]:
                raise WorkspaceError("Generated model template is invalid: " + "; ".join(validation["errors"]))
            template_record = {
                "version": 1,
                "id": template_id,
                "name": region_name,
                "source": f"Region Builder from {source['name']}",
                "sourceLibraryId": source["id"],
                "regionPackageId": package_id,
                "regionId": region["id"],
                "importedAt": now_iso(),
                "fingerprint": validation["fingerprint"],
                "inputFiles": validation["inputFiles"],
                "regionBuilder": True,
            }
            manifest = {
                "version": 1,
                "regionName": region_name,
                "regionCode": region_code,
                "state": state_abbr,
                "sourceLibrary": source,
                "regionPackage": {"id": package_id, "name": package_manifest["name"], "version": package_manifest["version"]},
                "region": region,
                "builtAt": now_iso(),
                "selection": {
                    "geoRows": len(selection["geoRows"]),
                    "azones": sorted(selection["azones"], key=str.lower),
                    "bzones": sorted(selection["bzones"]),
                    "mareas": sorted(selection["mareas"], key=str.lower),
                    "method": selection["selectionMethod"],
                    "boundary": selection["boundary"],
                },
                "files": input_plan,
                "defaultedFiles": manifest_defaults,
                "transitNormalization": transit_normalization,
                "warnings": self._boundary_warnings(package_manifest, selection) + self._warnings_for_plan(input_plan, package_manifest),
            }
            write_json(template_stage / "workbench_template.json", template_record)
            write_json(template_stage / "region_builder_manifest.json", manifest)
            write_json(library_stage / "region_builder_manifest.json", manifest)
            template_record["fingerprint"] = fingerprint_tree(template_stage, ["visioneval.cnf", "scripts/run_model.R", *[f"defs/{p.name}" for p in (template_stage / "defs").glob("*") if p.is_file()]])
            write_json(template_stage / "workbench_template.json", template_record)

            shutil.move(str(library_stage), str(library_target))
            shutil.move(str(template_stage), str(template_target))
            settings = self.workspace.settings()
            settings["defaultInputLibraryId"] = library_id
            settings["defaultTemplateId"] = template_id
            write_json(self.workspace.settings_path, settings)
        finally:
            shutil.rmtree(staging, ignore_errors=True)
        return {
            "inputLibrary": {"id": library_id, "name": library_id},
            "modelTemplate": {"id": template_id, "name": region_name},
            "selection": self.preview({**payload, "packageId": package_id, "sourceLibraryId": source["id"], "regionId": region["id"]})["selection"],
        }
