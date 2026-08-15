from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import re
import shutil
import subprocess
import threading
import time
from collections import Counter, OrderedDict
from functools import lru_cache
from pathlib import Path
from typing import Any

from .runtime import RuntimeManager
from .comparison_cache import ComparisonCache
from .workspace import Workspace, WorkspaceError, make_id, now_iso, read_json, write_json


TABLE_KEYS = {
    "Household": "HhId", "Vehicle": "VehId", "Worker": "WkrId",
    "Azone": "Azone", "Bzone": "Bzone", "Marea": "Marea",
}
MICRODATA_TABLES = {"Household", "Vehicle", "Worker"}


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _changed(left: Any, right: Any) -> bool:
    left_number, right_number = _number(left), _number(right)
    if left_number is not None and right_number is not None:
        return round(left_number, 5) != round(right_number, 5)
    return left != right


def _natural(value: str) -> tuple:
    import re
    return tuple(int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", str(value)))


class ComparisonService:
    def __init__(self, workspace: Workspace, runtime: RuntimeManager, helper: Path, scan_helper: Path | None = None, conflicts_path: Path | None = None, cache_extractor: Path | None = None):
        self.workspace = workspace
        self.runtime = runtime
        self.helper = helper.resolve()
        self.scan_helper = (scan_helper or helper).resolve()
        extractor = (cache_extractor or helper.with_name("comparison_cache_extract.R")).resolve()
        self.cache = ComparisonCache(workspace, runtime, extractor) if extractor.is_file() else None
        self.compare_summaries: dict[str, dict[str, Any]] = {}
        self.comparison_snapshots: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self.dashboard_snapshots: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self.map_snapshots: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self.density_snapshots: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self.snapshot_lock = threading.RLock()
        try:
            self.unit_conflicts = read_json(conflicts_path or helper.with_name("unit_conflicts.json"), {}).get("conflicts", [])
        except (AttributeError, OSError):
            self.unit_conflicts = []

    def _metadata_warning(self, table: str, variable: str) -> dict[str, Any] | None:
        key = f"{table}/{variable}".lower()
        return next((item for item in self.unit_conflicts if item.get("scope") == "output" and str(item.get("field", "")).lower() == key and item.get("status") != "approved"), None)

    def clear_cache(self) -> dict[str, Any]:
        self.compare_summaries.clear(); self.comparison_snapshots.clear(); self.dashboard_snapshots.clear(); self.map_snapshots.clear(); self.density_snapshots.clear(); self._read_rda.cache_clear()
        return self.cache.clear() if self.cache else {"cleared":True,"removed":0,"bytes":0,"entries":0}

    def _record(self, datastore_id: str) -> dict[str, Any]:
        record = next((item for item in self.workspace.catalog(False)["datastores"] if item.get("id") == datastore_id), None)
        if not record:
            raise WorkspaceError("Unknown datastore")
        path = self.workspace.within(record["path"])
        if not (path / "DatastoreListing.Rda").is_file():
            raise WorkspaceError("Datastore is incomplete")
        return {**record, "path": str(path)}

    @lru_cache(maxsize=4096)
    def _read_rda(self, path_text: str, metadata: bool = False) -> dict[str, Any]:
        path = self.workspace.within(path_text)
        extra = ["--metadata"] if metadata else []
        command, environment = self.runtime.r_command(self.helper, str(path), *extra)
        result = subprocess.run(command, capture_output=True, text=True, env=environment)
        if result.returncode:
            raise WorkspaceError((result.stderr or result.stdout).strip() or f"Could not read {path.name}")
        return json.loads(result.stdout)

    def _metadata(self, record: dict[str, Any]) -> dict[str, Any]:
        return self._read_rda(str(Path(record["path"]) / "DatastoreListing.Rda"), True)

    @staticmethod
    def _variable_files(root: Path) -> list[dict[str, str]]:
        items = []
        for path in root.rglob("*.Rda"):
            if path.name == "DatastoreListing.Rda":
                continue
            rel = path.relative_to(root)
            if len(rel.parts) >= 3 and rel.parts[0].isdigit():
                items.append({"year": rel.parts[0], "table": rel.parts[1], "name": path.stem})
        return items

    def variables(self, datastore_ids: list[str]) -> list[dict[str, Any]]:
        records = [self._record(item) for item in datastore_ids]
        by_key: dict[tuple[str, str], dict[str, set[str]]] = {}
        for record in records:
            for item in self._variable_files(Path(record["path"])):
                by_key.setdefault((item["table"], item["name"]), {}).setdefault(record["id"], set()).add(item["year"])
        metadata = self._metadata(records[0]) if records else {}
        output = []
        for (table, name), per_record in sorted(by_key.items()):
            common = set.intersection(*(per_record.get(record["id"], set()) for record in records)) if records else set()
            if not common:
                continue
            meta = metadata.get(f"{table}/{name}", {})
            conflict = self._metadata_warning(table, name)
            output.append({"table": table, "name": name, "years": sorted(common), "description": meta.get("description") or "", "units": meta.get("units") or "", "type": meta.get("type") or "", "module": meta.get("module") or "", "metadataWarning": conflict.get("reason", "") if conflict else "", "proposedUnit": conflict.get("proposedLabel", "") if conflict else ""})
        return output

    def _column(self, root: Path, year: str, table: str, variable: str) -> list[Any]:
        path = root / year / table / f"{variable}.Rda"
        if self.cache and path.is_file():
            return self.cache.column(root, year, table, variable)["list"]
        return self._read_rda(str(path)).get("values", []) if path.is_file() else []

    def _keyed(self, root: Path, year: str, table: str, variable: str) -> dict[str, Any]:
        path = root / year / table / f"{variable}.Rda"
        if self.cache and path.is_file():
            cached = self.cache.column(root, year, table, variable)
            return {key: cached[key] for key in ("keyName", "order", "values")}
        values = self._column(root, year, table, variable)
        key_name = TABLE_KEYS.get(table)
        if table == "Region":
            if len(values) > 1:
                raise WorkspaceError(f"{table}/{variable} has multiple rows but no stable key")
            return {"keyName": "Region", "order": ["Region"] if values else [], "values": {"Region": values[0]} if values else {}}
        if not key_name:
            if len(values) <= 1:
                return {"keyName": "Row", "order": ["1"] if values else [], "values": {"1": values[0]} if values else {}}
            raise WorkspaceError(f"{table}/{variable} cannot be compared safely because {table} has no configured stable key")
        keys = values if variable == key_name else self._column(root, year, table, key_name)
        if len(keys) != len(values):
            raise WorkspaceError(f"Key/value length mismatch for {year}/{table}/{variable}")
        order, mapped = [], {}
        for index, raw in enumerate(keys):
            key = str(raw).strip() if raw is not None else ""
            if not key:
                raise WorkspaceError(f"Blank {key_name} key in {year}/{table}/{variable}")
            if key in mapped:
                raise WorkspaceError(f"Duplicate {key_name} key {key} in {year}/{table}/{variable}")
            order.append(key); mapped[key] = values[index]
        return {"keyName": key_name, "order": order, "values": mapped}

    @staticmethod
    def _union_order(columns: list[dict[str, Any]]) -> list[str]:
        if not columns:
            return []
        order, seen = [], set()
        for key in columns[0]["order"]:
            order.append(key); seen.add(key)
        extras = {key for column in columns[1:] for key in column["order"] if key not in seen}
        return order + sorted(extras, key=_natural)

    def geo_options(self, reference_id: str, table: str, year: str) -> dict[str, Any]:
        record, fields = self._record(reference_id), []
        root = Path(record["path"])
        names = {item["name"] for item in self._variable_files(root) if item["year"] == year and item["table"] == table}
        key_name = TABLE_KEYS.get(table)
        county = self._county_mapping(record)
        if county and ("Azone" in names or "Bzone" in names or table in {"Azone", "Bzone"}):
            fields.append({"field": "County", "label": "County", "values": sorted(county["counties"], key=_natural), "derived": True})
        for field in ("Marea", "Azone", "Bzone", key_name):
            if not field or field in {item["field"] for item in fields} or (field not in names and field != key_name):
                continue
            values = self._column(root, year, table, field)
            fields.append({"field": field, "label": field, "values": sorted({str(value) for value in values if value is not None and str(value).strip()}, key=_natural)})
        message = "" if fields else "This output does not contain a geography that can be filtered safely."
        if county and not any(item["field"] == "County" for item in fields):
            message = "County filtering is unavailable because this output contains only regional geography."
        return {"table": table, "year": year, "levels": fields, "message": message}

    def cross_output_geo_options(self, reference_id: str, year: str) -> dict[str, Any]:
        """Return geography levels that can be resolved consistently across output tables."""
        record = self._record(reference_id)
        county = self._county_mapping(record)
        geography = self._map_geography(record)
        levels = []
        if county:
            levels.append({
                "field": "County", "label": "County",
                "values": sorted(county["counties"], key=_natural), "derived": True,
            })
        bzones = sorted(geography.get("bzone", {}).values(), key=_natural)
        if bzones:
            names = geography.get("names", {})
            levels.append({
                "field": "Bzone", "label": "Bzone", "values": bzones, "derived": True,
                "options": [
                    {"value": bzone, "label": f"{names.get(bzone, 'Unknown locality')} · {bzone}"}
                    for bzone in bzones
                ],
            })
        message = "" if levels else "This result does not include a safe cross-output geography filter."
        return {"year": year, "levels": levels, "message": message}

    def _county_mapping(self, record: dict[str, Any]) -> dict[str, Any] | None:
        template_id = record.get("templateId")
        if not template_id:
            return None
        try:
            template_path, _ = self.workspace.template(template_id)
        except WorkspaceError:
            return None
        path = template_path / "defs" / "geo.csv"
        if not path.is_file():
            return None
        azone, bzone, counties = {}, {}, set()
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                county = str(row.get("Azone", "")).strip()
                if not county or county.upper() == "NA":
                    continue
                counties.add(county); azone[county.lower()] = county
                zone = str(row.get("Bzone", "")).strip()
                if zone and zone.upper() != "NA":
                    bzone[zone.lower()] = county
        return {"counties": counties, "azone": azone, "bzone": bzone} if counties else None

    def _filter_keys(self, root: Path, year: str, table: str, keys: list[str], field: str, values: list[str]) -> list[str]:
        if not field or not values:
            return keys
        allowed = {str(value).lower() for value in values}
        if field == TABLE_KEYS.get(table) or (table == "Region" and field == "Region"):
            return [key for key in keys if key.lower() in allowed]
        location = self._keyed(root, year, table, field)["values"]
        return [key for key in keys if str(location.get(key, "")).lower() in allowed]

    def _matching_location_keys(self, record: dict[str, Any], root: Path, year: str, table: str, keys: list[str], field: str, values: list[str]) -> set[str]:
        if not field or not values:
            return set(keys)
        if field != "County":
            try:
                return set(self._filter_keys(root, year, table, keys, field, values))
            except WorkspaceError:
                return set()
        mapping = self._county_mapping(record)
        if not mapping:
            return set()
        allowed = {str(value).lower() for value in values}
        names = {item["name"] for item in self._variable_files(root) if item["year"] == year and item["table"] == table}
        location_field = "Azone" if "Azone" in names or table == "Azone" else "Bzone" if "Bzone" in names or table == "Bzone" else ""
        if not location_field:
            return set()
        try:
            locations = self._keyed(root, year, table, location_field)["values"]
        except WorkspaceError:
            return set()
        lookup = mapping["azone" if location_field == "Azone" else "bzone"]
        return {key for key in keys if str(lookup.get(str(locations.get(key, "")).lower(), "")).lower() in allowed}

    @staticmethod
    def _summary(values: list[Any]) -> dict[str, Any]:
        numeric = [number for value in values if (number := _number(value)) is not None]
        if numeric:
            ordered = sorted(numeric)
            def quantile(fraction: float) -> float:
                if len(ordered) == 1:
                    return ordered[0]
                position = (len(ordered) - 1) * fraction
                lower, upper = math.floor(position), math.ceil(position)
                return ordered[lower] if lower == upper else ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)
            return {"kind": "numeric", "count": len(values), "recordCount": len(values), "numericCount": len(numeric), "missingCount": len(values) - len(numeric), "sum": sum(numeric), "mean": sum(numeric) / len(numeric), "min": ordered[0], "q1": quantile(.25), "median": quantile(.5), "q3": quantile(.75), "max": ordered[-1]}
        categories = Counter(str(value) for value in values if value is not None)
        present = sum(categories.values())
        return {"kind": "categorical", "count": len(values), "recordCount": len(values), "numericCount": 0, "missingCount": len(values) - present, "categories": [{"label": key, "count": count, "share": count / present * 100 if present else 0} for key, count in categories.most_common()], "topCategories": [{"label": key, "count": count} for key, count in categories.most_common(10)]}

    @staticmethod
    def _percent_change(left_value: Any, right_value: Any) -> float | None:
        left, right = _number(left_value), _number(right_value)
        if left is None or right is None:
            return None
        if left == 0:
            return 0.0 if right == 0 else None
        return (right - left) / abs(left) * 100

    @staticmethod
    def _map_numeric_type(value: str) -> bool:
        kind = str(value or "").strip().lower()
        return kind not in {"character", "category", "categorical", "factor", "logical", "string", "id"}

    def _map_geography(self, record: dict[str, Any]) -> dict[str, Any]:
        """Resolve datastore geography labels to package-compatible FIPS and GEOIDs."""
        mapping = self._county_mapping(record)
        if not mapping:
            return {"azone": {}, "bzone": {}, "names": {}}
        azone_ids: dict[str, str] = {}
        bzone_ids: dict[str, str] = {}
        names: dict[str, str] = {}
        template_id = record.get("templateId")
        if not template_id:
            return {"azone": azone_ids, "bzone": bzone_ids, "names": names}
        try:
            template_path, _ = self.workspace.template(template_id)
        except WorkspaceError:
            return {"azone": azone_ids, "bzone": bzone_ids, "names": names}
        path = template_path / "defs" / "geo.csv"
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                name = str(row.get("Azone", "")).strip()
                bzone = re.sub(r"\.0$", "", str(row.get("Bzone", "")).strip())
                if not name or name.upper() == "NA" or not bzone or bzone.upper() == "NA":
                    continue
                bzone = bzone.zfill(12) if bzone.isdigit() else bzone
                azone = bzone[:5] if len(bzone) >= 5 and bzone[:5].isdigit() else ""
                if not azone:
                    continue
                azone_ids[name.casefold()] = azone
                azone_ids[azone] = azone
                bzone_ids[bzone.casefold()] = bzone
                names[azone] = name
                names[bzone] = name
        return {"azone": azone_ids, "bzone": bzone_ids, "names": names}

    def map_options(self, datastore_ids: list[str]) -> dict[str, Any]:
        variables = self.variables(datastore_ids)
        if not datastore_ids:
            return {"variables": [], "message": "Load at least two datastore results to create a map."}
        reference = self._record(datastore_ids[0])
        root = Path(reference["path"])
        output = []
        for item in variables:
            if item["name"] == TABLE_KEYS.get(item["table"]) or not self._map_numeric_type(item.get("type", "")):
                continue
            levels = set()
            for year in item.get("years", []):
                names = {entry["name"] for entry in self._variable_files(root) if entry["year"] == year and entry["table"] == item["table"]}
                if item["table"] == "Azone" or "Azone" in names or item["table"] == "Bzone" or "Bzone" in names:
                    levels.add("county")
                if item["table"] == "Bzone" or "Bzone" in names or (
                    item["table"] in {"Vehicle", "Worker"} and "HhId" in names
                ):
                    levels.add("bzone")
            if levels:
                descriptors = {
                    "county": {
                        "id": "county", "label": "County / locality", "identifier": "FIPS",
                        "geometry": "azone", "technicalLevel": "Azone",
                    },
                    "bzone": {
                        "id": "bzone", "label": "Bzone", "identifier": "GEOID",
                        "geometry": "bzone", "technicalLevel": "Bzone",
                    },
                }
                output.append({
                    **item,
                    "geographyLevels": [descriptors[level] for level in ("county", "bzone") if level in levels],
                })
        return {
            "variables": output,
            "message": "" if output else "The loaded results do not contain numeric outputs with supported county/locality or Bzone identifiers.",
        }

    def _map_source_signature(self, records: list[dict[str, Any]], year: str, table: str, variable: str, geography: str) -> list[Any]:
        signature = []
        for record in records:
            root = Path(record["path"])
            names = {variable, "Bzone" if geography == "bzone" else "Azone", "Bzone"}
            if table in {"Vehicle", "Worker"} and geography == "bzone":
                names.add("HhId")
            files = []
            for name in sorted(names):
                path = root / year / table / f"{name}.Rda"
                if path.is_file():
                    stat = path.stat(); files.append([name, stat.st_size, stat.st_mtime_ns])
            auxiliary = []
            if table in {"Vehicle", "Worker"} and geography == "bzone":
                for name in ("HhId", "Bzone"):
                    path = root / year / "Household" / f"{name}.Rda"
                    if path.is_file():
                        stat = path.stat(); auxiliary.append(["Household", name, stat.st_size, stat.st_mtime_ns])
            signature.append([record.get("id"), record.get("registrationFingerprint", ""), files, auxiliary])
        return signature

    def _aggregate_map_record(self, record: dict[str, Any], year: str, table: str, variable: str, geography: str, cancelled=None) -> dict[str, Any]:
        root = Path(record["path"])
        values = self._column(root, year, table, variable)
        available = {item["name"] for item in self._variable_files(root) if item["year"] == year and item["table"] == table}
        assignment = "direct"
        if geography == "bzone":
            field = "Bzone" if table == "Bzone" or "Bzone" in available else ""
        else:
            field = "Azone" if table == "Azone" or "Azone" in available else "Bzone" if table == "Bzone" or "Bzone" in available else ""
        locations: list[Any]
        if field:
            locations = self._column(root, year, table, field)
        elif geography == "bzone" and table in {"Vehicle", "Worker"} and "HhId" in available:
            household_available = {
                item["name"] for item in self._variable_files(root)
                if item["year"] == year and item["table"] == "Household"
            }
            if not {"HhId", "Bzone"}.issubset(household_available):
                raise WorkspaceError(f"{table} Bzone aggregation requires Household/HhId and Household/Bzone")
            source_households = self._column(root, year, table, "HhId")
            household_ids = self._column(root, year, "Household", "HhId")
            household_bzones = self._column(root, year, "Household", "Bzone")
            if len(household_ids) != len(household_bzones):
                raise WorkspaceError(f"Household geography/key length mismatch for {year}")
            household_lookup: dict[str, Any] = {}
            ambiguous: set[str] = set()
            for household_id, bzone in zip(household_ids, household_bzones):
                key = str(household_id)
                if key in household_lookup and household_lookup[key] != bzone:
                    ambiguous.add(key)
                else:
                    household_lookup[key] = bzone
            for key in ambiguous:
                household_lookup.pop(key, None)
            locations = [household_lookup.get(str(household_id)) for household_id in source_households]
            assignment = f"{table}.HhId -> Household.HhId -> Household.Bzone"
        else:
            raise WorkspaceError(f"{table}/{variable} does not contain {geography.capitalize()} geography")
        if len(values) != len(locations):
            raise WorkspaceError(f"Geography/value length mismatch for {year}/{table}/{variable}")
        lookup = self._map_geography(record)
        totals: dict[str, list[float]] = {}
        numeric_rows = 0
        unmatched_rows = 0
        for index, (location, value) in enumerate(zip(locations, values)):
            if cancelled and index % 10_000 == 0 and cancelled():
                raise WorkspaceError("Comparison map generation cancelled")
            number = _number(value)
            if number is None:
                continue
            numeric_rows += 1
            if location is None:
                unmatched_rows += 1
                continue
            raw = re.sub(r"\.0$", "", str(location).strip())
            if field == "Bzone" or geography == "bzone" and assignment != "direct":
                bzone = raw.zfill(12) if raw.isdigit() else raw
                geography_id = lookup["bzone"].get(bzone.casefold(), bzone)
                if geography in {"azone", "county"}: geography_id = lookup["azone"].get(geography_id[:5], geography_id[:5])
            else:
                geography_id = lookup["azone"].get(raw.casefold(), raw if len(raw) == 5 and raw.isdigit() else "")
            if not geography_id:
                unmatched_rows += 1
                continue
            bucket = totals.setdefault(str(geography_id), [0.0, 0.0])
            bucket[0] += number; bucket[1] += 1
        return {
            "values": {key: {"mean": total / count, "sum": total, "count": int(count)} for key, (total, count) in totals.items() if count},
            "assignment": assignment,
            "numericRows": numeric_rows,
            "matchedRows": numeric_rows - unmatched_rows,
            "unmatchedRows": unmatched_rows,
        }

    def comparison_map(self, reference_id: str, comparison_id: str, year: str, table: str, variable: str, geography: str, aggregation: str = "mean", cancelled=None) -> dict[str, Any]:
        if geography == "azone":
            geography = "county"
        if geography not in {"county", "bzone"}:
            raise WorkspaceError("Map geography must be County/locality or Bzone")
        if aggregation not in {"mean", "sum", "count"}:
            raise WorkspaceError("Map aggregation must be mean, sum, or count")
        records = [self._record(reference_id), self._record(comparison_id)]
        if reference_id == comparison_id:
            raise WorkspaceError("Choose different reference and comparison results")
        signature = self._map_source_signature(records, year, table, variable, geography)
        token = hashlib.sha256(json.dumps({"schema": 3, "records": [reference_id, comparison_id], "year": year, "table": table, "variable": variable, "geography": geography, "aggregation": aggregation, "sources": signature}, sort_keys=True).encode()).hexdigest()
        with self.snapshot_lock:
            if token in self.map_snapshots:
                self.map_snapshots.move_to_end(token)
                return self.map_snapshots[token]
        aggregate_results = [self._aggregate_map_record(record, year, table, variable, geography, cancelled) for record in records]
        aggregates = [item["values"] for item in aggregate_results]
        geography_lookup = self._map_geography(records[0])
        names = geography_lookup.get("names", {})
        packaged_ids = {
            value
            for value in geography_lookup.get("azone" if geography == "county" else geography, {}).values()
            if value
        }
        rows = []
        geography_ids = packaged_ids | set(aggregates[0]) | set(aggregates[1])
        for geography_id in sorted(geography_ids, key=_natural):
            left_item, right_item = aggregates[0].get(geography_id), aggregates[1].get(geography_id)
            left = left_item.get(aggregation) if left_item else None
            right = right_item.get(aggregation) if right_item else None
            rows.append({
                "geographyId": geography_id,
                "name": names.get(geography_id, geography_id),
                "referenceValue": left,
                "comparisonValue": right,
                "referenceCount": left_item.get("count", 0) if left_item else 0,
                "comparisonCount": right_item.get("count", 0) if right_item else 0,
                "absoluteChange": (right - left) if left is not None and right is not None else None,
                "percentChange": self._percent_change(left, right),
            })
        metadata = self._metadata(records[0]).get(f"{table}/{variable}", {})
        public_records = [
            {
                key: record.get(key)
                for key in ("id", "label", "projectId", "templateId", "inputLibraryId", "fingerprint", "registrationFingerprint")
                if record.get(key) is not None
            }
            for record in records
        ]
        payload = {
            "mapToken": token, "reference": public_records[0], "comparison": public_records[1], "year": year,
            "table": table, "variable": variable, "geographyLevel": geography,
            "geographyLabel": "County / locality" if geography == "county" else "Bzone",
            "units": metadata.get("units") or "", "description": metadata.get("description") or "",
            "geographyRows": rows, "mappedGeographies": len(rows),
            "unavailableGeographies": sum(item["referenceValue"] is None or item["comparisonValue"] is None for item in rows),
            "aggregation": aggregation,
            "assignments": [
                {"resultId": record.get("id"), **{key: aggregate.get(key) for key in ("assignment", "numericRows", "matchedRows", "unmatchedRows")}}
                for record, aggregate in zip(records, aggregate_results)
            ],
            "unmatchedRows": sum(item["unmatchedRows"] for item in aggregate_results),
            "generatedAt": now_iso(),
        }
        with self.snapshot_lock:
            self.map_snapshots[token] = payload; self.map_snapshots.move_to_end(token)
            while len(self.map_snapshots) > 8: self.map_snapshots.popitem(last=False)
        return payload

    def comparison_map_snapshot(self, token: str) -> dict[str, Any]:
        with self.snapshot_lock:
            payload = self.map_snapshots.get(token)
            if not payload: raise WorkspaceError("Comparison map snapshot expired; generate the map again")
            self.map_snapshots.move_to_end(token)
            return payload

    def change_density(self, reference_id: str, comparison_id: str, year: str, geography: str,
                       progress=None, cancelled=None) -> dict[str, Any]:
        """Count changed, safely assignable variables for every project geography."""
        if geography == "county":
            geography = "azone"
        if geography not in {"azone", "bzone"}:
            raise WorkspaceError("Change density geography must be Bzone or Azone")
        if reference_id == comparison_id:
            raise WorkspaceError("Choose different reference and comparison results")
        records = [self._record(reference_id), self._record(comparison_id)]
        variables = [
            item for item in self.variables([reference_id, comparison_id])
            if year in item.get("years", [])
            and item.get("name") != TABLE_KEYS.get(item.get("table", ""))
            and self._map_numeric_type(item.get("type", ""))
        ]
        if progress:
            progress(phase="cache_validation", message="Validating saved results", completed=0, total=len(variables))
        if cancelled and cancelled():
            raise WorkspaceError("Change-density calculation cancelled")

        cache_hits = cache_misses = 0
        by_table: dict[str, set[str]] = {}
        for item in variables:
            table = item["table"]
            names = by_table.setdefault(table, set())
            names.add(item["name"])
            names.add("Bzone" if geography == "bzone" else "Azone")
            if geography == "azone":
                names.add("Bzone")
            if table in {"Vehicle", "Worker"} and geography == "bzone":
                names.add("HhId")
        cache_total = len(records) * len(by_table)
        cache_completed = 0
        if progress:
            progress(phase="preparing_cache", message="Preparing comparison caches", completed=0,
                     total=cache_total, cacheHits=0, cacheMisses=0)
        if self.cache:
            for record in records:
                root = Path(record["path"])
                available_by_table = {
                    table: {entry["name"] for entry in self._variable_files(root)
                            if entry["year"] == year and entry["table"] == table}
                    for table in by_table
                }
                for table, requested in by_table.items():
                    if cancelled and cancelled():
                        raise WorkspaceError("Change-density calculation cancelled")
                    available = available_by_table.get(table, set())
                    names = sorted(name for name in requested if name in available)
                    metrics = self.cache.ensure(root, year, table, names)
                    cache_hits += int(bool(metrics.get("cacheHit")))
                    cache_misses += int(not metrics.get("cacheHit"))
                    cache_completed += 1
                    if progress:
                        progress(phase="preparing_cache", message="Preparing comparison caches",
                                 recordLabel=record.get("label", record.get("id", "Result")), table=table,
                                 completed=cache_completed, total=cache_total,
                                 cacheHits=cache_hits, cacheMisses=cache_misses)

            if geography == "bzone" and any(item["table"] in {"Vehicle", "Worker"} for item in variables):
                for record in records:
                    root = Path(record["path"])
                    available = {entry["name"] for entry in self._variable_files(root)
                                 if entry["year"] == year and entry["table"] == "Household"}
                    names = [name for name in ("HhId", "Bzone") if name in available]
                    self.cache.ensure(root, year, "Household", names)

        counts: Counter[str] = Counter()
        scanned_counts: Counter[str] = Counter()
        unavailable: list[dict[str, Any]] = []
        assignments: list[dict[str, Any]] = []
        normalized_geography = "county" if geography == "azone" else "bzone"
        for index, item in enumerate(variables, 1):
            if cancelled and cancelled():
                raise WorkspaceError("Change-density calculation cancelled")
            if progress:
                progress(phase="scanning_variables", message="Evaluating changes by geography",
                         table=item["table"], variable=item["name"], completed=index - 1,
                         total=len(variables), cacheHits=cache_hits, cacheMisses=cache_misses)
            try:
                aggregates = [
                    self._aggregate_map_record(record, year, item["table"], item["name"], normalized_geography, cancelled)
                    for record in records
                ]
                measure = "mean" if item["table"] in MICRODATA_TABLES else "sum"
                geography_ids = set(aggregates[0]["values"]) | set(aggregates[1]["values"])
                changed_geographies = 0
                for geography_id in geography_ids:
                    left = aggregates[0]["values"].get(geography_id, {}).get(measure)
                    right = aggregates[1]["values"].get(geography_id, {}).get(measure)
                    if left is None or right is None:
                        continue
                    scanned_counts[geography_id] += 1
                    if _changed(left, right):
                        counts[geography_id] += 1
                        changed_geographies += 1
                assignments.append({
                    "table": item["table"], "variable": item["name"], "status": "assigned",
                    "semantics": "aggregate mean" if measure == "mean" else "stable-table geographic total",
                    "changedGeographies": changed_geographies,
                    "methods": [aggregate["assignment"] for aggregate in aggregates],
                })
            except WorkspaceError as exc:
                if cancelled and cancelled():
                    raise
                unavailable.append({"table": item["table"], "variable": item["name"], "reason": str(exc)})
            except Exception as exc:
                unavailable.append({"table": item["table"], "variable": item["name"], "reason": str(exc)})
            if progress:
                progress(phase="scanning_variables", message="Evaluating changes by geography",
                         table=item["table"], variable=item["name"], completed=index,
                         total=len(variables), cacheHits=cache_hits, cacheMisses=cache_misses)

        if progress:
            progress(phase="finalizing", message="Finalizing change-density map", completed=len(variables),
                     total=len(variables), cacheHits=cache_hits, cacheMisses=cache_misses)
        lookup = self._map_geography(records[0])
        project_ids = set(lookup["bzone" if geography == "bzone" else "azone"].values())
        rows = [{
            "geographyId": geography_id,
            "name": lookup.get("names", {}).get(geography_id, geography_id),
            "changedVariableCount": int(counts.get(geography_id, 0)),
            "scannedVariableCount": int(scanned_counts.get(geography_id, 0)),
            "unavailableVariableCount": len(unavailable),
        } for geography_id in sorted(project_ids | set(scanned_counts), key=_natural)]
        token = hashlib.sha256(json.dumps({
            "schema": 1, "reference": reference_id, "comparison": comparison_id, "year": year,
            "geography": geography, "rows": rows, "unavailable": unavailable,
        }, sort_keys=True).encode()).hexdigest()
        public_records = [{key: record.get(key) for key in (
            "id", "label", "projectId", "templateId", "inputLibraryId", "fingerprint", "registrationFingerprint"
        ) if record.get(key) is not None} for record in records]
        payload = {
            "densityToken": token, "operationKind": "change-density", "reference": public_records[0],
            "comparison": public_records[1], "year": year, "geographyLevel": geography,
            "geographyLabel": "Bzone" if geography == "bzone" else "Azone / locality",
            "geographyRows": rows, "scannedVariables": len(variables) - len(unavailable),
            "unavailableVariables": unavailable, "assignments": assignments,
            "cacheHits": cache_hits, "cacheMisses": cache_misses, "generatedAt": now_iso(),
        }
        with self.snapshot_lock:
            self.density_snapshots[token] = payload
            while len(self.density_snapshots) > 8:
                self.density_snapshots.popitem(last=False)
        return payload

    def restore_map_snapshot(self, payload: dict[str, Any]) -> None:
        token = str(payload.get("mapToken", ""))
        if not token: return
        with self.snapshot_lock:
            self.map_snapshots[token] = payload; self.map_snapshots.move_to_end(token)
            while len(self.map_snapshots) > 8: self.map_snapshots.popitem(last=False)

    def comparison_map_rows(self, token: str, region_id: str = "", regions: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        payload = self.comparison_map_snapshot(token)
        rows = list(payload.get("geographyRows") or [])
        if not region_id or not regions:
            return rows
        region = next((item for item in regions if item.get("id") == region_id), None)
        if not region: raise WorkspaceError("Unknown MPO map scope")
        allowed = set(region.get("azoneFips") if payload.get("geographyLevel") in {"azone", "county"} else region.get("selectedBzones") or [])
        return [row for row in rows if str(row.get("geographyId")) in allowed]

    def comparison_map_scope_rows(self, token: str, scope_ids: list[str] | set[str], names: dict[str, str] | None = None) -> list[dict[str, Any]]:
        """Return one export row per polygon, including unavailable geography."""
        payload = self.comparison_map_snapshot(token)
        by_id = {str(item.get("geographyId")): item for item in payload.get("geographyRows") or []}
        name_lookup = names or {}
        rows = []
        for geography_id in sorted({str(value) for value in scope_ids if value}, key=_natural):
            rows.append(by_id.get(geography_id) or {
                "geographyId": geography_id,
                "name": name_lookup.get(geography_id, geography_id),
                "referenceValue": None,
                "comparisonValue": None,
                "referenceCount": 0,
                "comparisonCount": 0,
                "absoluteChange": None,
                "percentChange": None,
            })
        return rows

    def _snapshot_page(self, token: str, changed_only: bool, limit: int, offset: int, sort_column: str, sort_direction: str) -> dict[str, Any]:
        with self.snapshot_lock:
            snapshot = self.comparison_snapshots.get(token)
            if not snapshot:
                raise WorkspaceError("Comparison snapshot expired; update the comparison to continue")
            self.comparison_snapshots.move_to_end(token)
            cache_key = (bool(changed_only), sort_column, sort_direction)
            indexes = snapshot["sortIndexes"].get(cache_key)
            if indexes is None:
                indexes = [index for index, changed in enumerate(snapshot["changed"]) if not changed_only or changed]
                if sort_direction in {"asc", "desc"}:
                    if sort_column == "id":
                        value_for = lambda index: snapshot["keys"][index]
                        key_for = lambda value: _natural(value)
                    elif sort_column == "reference":
                        value_for = lambda index: snapshot["referenceValues"][index]
                        key_for = lambda value: (0, float(value)) if isinstance(value, (int, float)) else (1, str(value).lower())
                    elif sort_column.startswith("comparison:"):
                        column = int(sort_column.split(":", 1)[1])
                        value_for = lambda index: snapshot["comparisonValues"][column][index]
                        key_for = lambda value: (0, float(value)) if isinstance(value, (int, float)) else (1, str(value).lower())
                    elif sort_column.startswith(("percent:", "delta:")):
                        column = int(sort_column.split(":", 1)[1])
                        value_for = lambda index: snapshot["percentChanges"][column][index]
                        key_for = lambda value: value
                    else:
                        value_for = lambda index: snapshot["keys"][index]
                        key_for = lambda value: _natural(value)
                    defined, undefined = [], []
                    for index in indexes:
                        value = value_for(index)
                        (undefined if value is None else defined).append(index)
                    defined.sort(key=lambda index: key_for(value_for(index)), reverse=sort_direction == "desc")
                    indexes = defined + undefined
                snapshot["sortIndexes"][cache_key] = indexes
            requested_limit = int(limit)
            offset = max(0, int(offset))
            page_limit = len(indexes) if requested_limit <= 0 else max(1, min(requested_limit, 5000))
            selected = indexes[offset:offset + page_limit]
            rows = []
            for index in selected:
                values = [column[index] for column in snapshot["comparisonValues"]]
                rows.append({
                    "id": snapshot["keys"][index],
                    "reference": snapshot["referenceValues"][index],
                    "comparisons": values,
                    "deltas": [column[index] for column in snapshot["deltas"]],
                    "percentChanges": [column[index] for column in snapshot["percentChanges"]],
                    "changedFlags": [column[index] for column in snapshot["changedFlags"]],
                    "changed": bool(snapshot["changed"][index]),
                })
            return {**snapshot["payload"], "comparisonToken": token, "rows": rows, "displayRows": len(indexes), "offset": offset, "limit": page_limit, "sortColumn": sort_column, "sortDirection": sort_direction}

    def comparison_snapshot_page(self, token: str, changed_only: bool = False, limit: int = 100, offset: int = 0, sort_column: str = "id", sort_direction: str = "original") -> dict[str, Any]:
        return self._snapshot_page(token, changed_only, limit, offset, sort_column, sort_direction)

    def _aggregate_compare(self, reference_id: str, comparison_ids: list[str], table: str, variable: str, year: str, filter_field: str = "", filter_values: list[str] | None = None) -> dict[str, Any]:
        records = [self._record(reference_id), *[self._record(item) for item in comparison_ids]]
        summaries = []
        for record in records:
            root = Path(record["path"])
            values = self._column(root, year, table, variable)
            if filter_field and filter_values:
                key_name = TABLE_KEYS.get(table, "")
                keys = [str(value).strip() for value in self._column(root, year, table, key_name)]
                allowed = self._matching_location_keys(record, root, year, table, keys, filter_field, filter_values)
                values = [value for key, value in zip(keys, values) if key in allowed]
            summaries.append(self._summary(values))
        reference_summary, comparison_summaries = summaries[0], summaries[1:]
        changes, stats = [], []
        for record, summary in zip(records[1:], comparison_summaries):
            measures = {}
            for name in ("recordCount", "numericCount", "missingCount", "sum", "mean"):
                left, right = reference_summary.get(name), summary.get(name)
                delta = right - left if isinstance(left, (int, float)) and isinstance(right, (int, float)) else None
                measures[name] = {"reference": left, "comparison": right, "change": delta, "percentChange": self._percent_change(left, right)}
            categorical_changed = reference_summary.get("categories", []) != summary.get("categories", [])
            changes.append({"label": record.get("label", record["id"]), "measures": measures, "categoriesChanged": categorical_changed})
            stats.append({
                "label": record.get("label", record["id"]), "rowsCompared": None, "matchedRows": None,
                "unmatchedRows": None, "rowsChanged": None, "rowsIncreased": None, "rowsDecreased": None,
                "rowsUnchanged": None, "netChange": measures["sum"]["change"],
                "totalPercentChange": measures["sum"]["percentChange"], "rowsChangedPercent": None,
                "averageRowPercentChange": None, "reference": reference_summary, "comparison": summary,
                "identitySemantics": "run_local_synthetic",
            })
        meta = self._metadata(records[0]).get(f"{table}/{variable}", {})
        return {
            "mode": "aggregate", "identitySemantics": "run_local_synthetic", "advancedRecordsAvailable": True,
            "table": table, "variable": variable, "year": year, "key": TABLE_KEYS.get(table, "Record"),
            "reference": records[0], "comparisons": records[1:], "aggregateSummaries": summaries,
            "aggregateChanges": changes, "referenceSummary": reference_summary,
            "comparisonSummaries": comparison_summaries, "stats": stats, "metadata": meta,
            "rows": [], "totalRows": max((item.get("recordCount", 0) for item in summaries), default=0),
            "displayRows": 0, "changedRows": 1 if any(any(value.get("change") not in {None, 0} for value in change["measures"].values()) or change["categoriesChanged"] for change in changes) else 0,
            "offset": 0, "limit": 0, "filterField": filter_field, "filterValues": filter_values or [],
            "sortColumn": "aggregate", "sortDirection": "original",
        }

    def compare(self, reference_id: str, comparison_ids: list[str], table: str, variable: str, year: str, changed_only: bool = False, limit: int = 100, offset: int = 0, filter_field: str = "", filter_values: list[str] | None = None, sort_column: str = "id", sort_direction: str = "original", mode: str = "auto") -> dict[str, Any]:
        if mode not in {"auto", "aggregate", "records"}:
            raise WorkspaceError("Comparison mode must be aggregate or records")
        if table in MICRODATA_TABLES and mode != "records":
            return self._aggregate_compare(reference_id, comparison_ids, table, variable, year, filter_field, filter_values)
        reference, comparisons = self._record(reference_id), [self._record(item) for item in comparison_ids]
        if not comparisons:
            changed_only = False
        roots = [Path(reference["path"]), *[Path(item["path"]) for item in comparisons]]
        columns = [self._keyed(root, year, table, variable) for root in roots]
        keys = self._union_order(columns)
        if filter_field and filter_values:
            matching = set()
            for record, root in zip([reference, *comparisons], roots):
                matching.update(self._matching_location_keys(record, root, year, table, keys, filter_field, filter_values))
            keys = [key for key in keys if key in matching]
        source_signature=[]
        for root in roots:
            names=[variable,TABLE_KEYS.get(table,""),filter_field if filter_field not in {"County",""} else "Azone", "Bzone" if filter_field=="County" else ""]
            source_signature.append([(name,(root/year/table/f"{name}.Rda").stat().st_mtime_ns,(root/year/table/f"{name}.Rda").stat().st_size) for name in names if name and (root/year/table/f"{name}.Rda").is_file()])
        summary_token=hashlib.sha256(json.dumps({"records":[item["id"] for item in [reference,*comparisons]],"year":year,"table":table,"variable":variable,"filterField":filter_field,"filterValues":filter_values or [],"sources":source_signature},sort_keys=True).encode()).hexdigest()
        with self.snapshot_lock:
            if summary_token in self.comparison_snapshots:
                return self._snapshot_page(summary_token, changed_only, limit, offset, sort_column, sort_direction)
        comparison_values = [[] for _ in comparisons]
        reference_values, changed = [], bytearray()
        changed_flags = [[] for _ in comparisons]
        deltas = [[] for _ in comparisons]
        percentages = [[] for _ in comparisons]
        for key in keys:
            base = columns[0]["values"].get(key)
            values = [column["values"].get(key) for column in columns[1:]]
            flags = [_changed(base, value) for value in values]
            reference_values.append(base)
            changed.append(any(flags))
            for index, value in enumerate(values):
                left, right = _number(base), _number(value)
                comparison_values[index].append(value)
                changed_flags[index].append(flags[index])
                deltas[index].append((right - left) if left is not None and right is not None else None)
                percentages[index].append(self._percent_change(base, value))
        meta = self._metadata(reference).get(f"{table}/{variable}", {})
        conflict = self._metadata_warning(table, variable)
        if conflict:
            meta = {**meta, "metadataWarning": conflict.get("reason", ""), "proposedUnit": conflict.get("proposedLabel", ""), "unitReviewStatus": conflict.get("status", "unresolved")}
        pair_stats = []
        for index, values in enumerate(comparison_values):
            numeric_pairs = [(left, right) for base, value in zip(reference_values, values) if (left := _number(base)) is not None and (right := _number(value)) is not None]
            pair_deltas = [right - left for left, right in numeric_pairs]
            matched_reference = self._summary([left for left, _ in numeric_pairs])
            matched_comparison = self._summary([right for _, right in numeric_pairs])
            left_sum, right_sum = matched_reference.get("sum"), matched_comparison.get("sum")
            rows_changed = sum(_changed(base, value) for base, value in zip(reference_values, values))
            pair_stats.append({"label": comparisons[index].get("label", f"Comparison {index + 1}"), "rowsCompared": len(reference_values), "matchedRows": len(numeric_pairs), "unmatchedRows": len(reference_values) - len(numeric_pairs), "rowsChanged": rows_changed, "rowsIncreased": sum(delta > 0 for delta in pair_deltas), "rowsDecreased": sum(delta < 0 for delta in pair_deltas), "rowsUnchanged": sum(delta == 0 for delta in pair_deltas), "netChange": sum(pair_deltas) if pair_deltas else None, "totalPercentChange": ((right_sum-left_sum)/left_sum*100) if left_sum not in {None, 0} and right_sum is not None else None, "rowsChangedPercent": (rows_changed/len(reference_values)*100) if reference_values else None, "averageRowPercentChange": (sum((right-left)/abs(left)*100 for left,right in numeric_pairs if left != 0) / sum(left != 0 for left,_ in numeric_pairs)) if any(left != 0 for left,_ in numeric_pairs) else None, "reference": matched_reference, "comparison": matched_comparison})
        base_payload={"mode":"records", "identitySemantics":"run_local_synthetic" if table in MICRODATA_TABLES else "stable_key", "table": table, "variable": variable, "year": year, "key": columns[0]["keyName"], "reference": reference, "comparisons": comparisons, "totalRows": len(keys), "changedRows": sum(changed), "metadata": meta, "referenceSummary": self._summary(reference_values), "comparisonSummaries": [self._summary(values) for values in comparison_values], "stats": pair_stats, "filterField": filter_field, "filterValues": filter_values or []}
        snapshot={"payload":base_payload,"keys":keys,"referenceValues":reference_values,"comparisonValues":comparison_values,"changed":changed,"changedFlags":changed_flags,"deltas":deltas,"percentChanges":percentages,"sortIndexes":{}}
        with self.snapshot_lock:
            self.comparison_snapshots[summary_token]=snapshot
            self.comparison_snapshots.move_to_end(summary_token)
            while len(self.comparison_snapshots)>4:
                self.comparison_snapshots.popitem(last=False)
        return self._snapshot_page(summary_token, changed_only, limit, offset, sort_column, sort_direction)

    def comparison_page(self, reference_id: str, comparison_ids: list[str], table: str, variable: str, year: str, changed_only: bool = False, limit: int = 100, offset: int = 0, filter_field: str = "", filter_values: list[str] | None = None, sort_column: str = "id", sort_direction: str = "original") -> dict[str, Any]:
        """Return an original-order page without waiting for whole-table statistics."""
        if changed_only or sort_direction != "original":
            return self.compare(reference_id, comparison_ids, table, variable, year, changed_only, limit, offset, filter_field, filter_values, sort_column, sort_direction)
        reference, comparisons = self._record(reference_id), [self._record(item) for item in comparison_ids]
        records = [reference, *comparisons]
        roots = [Path(item["path"]) for item in records]
        columns = [self._keyed(root, year, table, variable) for root in roots]
        keys = self._union_order(columns)
        if filter_field and filter_values:
            matching: set[str] = set()
            for record, root in zip(records, roots):
                matching.update(self._matching_location_keys(record, root, year, table, keys, filter_field, filter_values))
            keys = [key for key in keys if key in matching]
        page_limit = max(1, min(int(limit or 100), 5000)); offset = max(0, int(offset))
        rows = []
        for key in keys[offset:offset + page_limit]:
            base = columns[0]["values"].get(key)
            values = [column["values"].get(key) for column in columns[1:]]
            flags = [_changed(base, value) for value in values]
            rows.append({"id": key, "reference": base, "comparisons": values, "deltas": [(right-left) if (left:=_number(base)) is not None and (right:=_number(value)) is not None else None for value in values], "percentChanges": [self._percent_change(base, value) for value in values], "changedFlags": flags, "changed": any(flags)})
        meta = self._metadata(reference).get(f"{table}/{variable}", {})
        return {"mode":"records","identitySemantics":"run_local_synthetic" if table in MICRODATA_TABLES else "stable_key","table":table,"variable":variable,"year":year,"key":columns[0]["keyName"],"reference":reference,"comparisons":comparisons,"rows":rows,"totalRows":len(keys),"displayRows":len(keys),"changedRows":None,"offset":offset,"limit":page_limit,"metadata":meta,"referenceSummary":{},"comparisonSummaries":[],"stats":[],"filterField":filter_field,"filterValues":filter_values or [],"sortColumn":sort_column,"sortDirection":sort_direction,"statsPending":True}

    def changes(self, reference_id: str, comparison_ids: list[str], year: str, filter_field: str = "", filter_values: list[str] | None = None, progress=None, cancelled=None) -> dict[str, Any]:
        variables = [item for item in self.variables([reference_id, *comparison_ids]) if year in item["years"] and item["name"] != TABLE_KEYS.get(item["table"])]
        records = [self._record(reference_id), *[self._record(item) for item in comparison_ids]]
        cache_skipped: dict[tuple[str, str], str] = {}
        if self.cache:
            by_table: dict[str, list[str]] = {}
            for item in variables: by_table.setdefault(item["table"], []).append(item["name"])
            cache_total = len(by_table) * len(records)
            cache_completed = cache_hits = cache_misses = 0
            for table, names in by_table.items():
                if cancelled and cancelled(): raise WorkspaceError("Change scan cancelled")
                for record in records:
                    if progress:
                        progress(cache_completed, cache_total, table, "", phase="preparing_cache", recordLabel=record.get("label", record["id"]), cacheHits=cache_hits, cacheMisses=cache_misses)
                    try:
                        metrics = self.cache.ensure(Path(record["path"]), year, table, names)
                        if metrics.get("cacheHit"): cache_hits += 1
                        else: cache_misses += 1
                    except WorkspaceError:
                        cache_misses += 1
                        # Preserve the fast table-wide extraction path, but isolate a malformed or
                        # non-row-aligned variable instead of allowing it to abort the global scan.
                        for name in names:
                            if cancelled and cancelled(): raise WorkspaceError("Change scan cancelled")
                            try:
                                self.cache.ensure(Path(record["path"]), year, table, [name])
                            except WorkspaceError as exc:
                                cache_skipped[(table, name)] = str(exc)
                    cache_completed += 1
                    if progress:
                        progress(cache_completed, cache_total, table, "", phase="preparing_cache", recordLabel=record.get("label", record["id"]), cacheHits=cache_hits, cacheMisses=cache_misses)
        results, skipped = [], []
        for index, item in enumerate(variables):
            if cancelled and cancelled(): raise WorkspaceError("Change scan cancelled")
            if progress: progress(index, len(variables), item["table"], item["name"], phase="scanning")
            cache_reason = cache_skipped.get((item["table"], item["name"]))
            if cache_reason:
                skipped.append({"table": item["table"], "variable": item["name"], "reason": cache_reason})
                continue
            try:
                payload = self.compare(reference_id, comparison_ids, item["table"], item["name"], year, False, 1, 0, filter_field, filter_values)
                if payload["changedRows"]:
                    pair_stats = payload["stats"]
                    results.append({"table": item["table"], "variable": item["name"], "changedRows": payload["changedRows"], "totalRows": payload["totalRows"], "percentRowsChanged": payload["changedRows"] / payload["totalRows"] * 100 if payload["totalRows"] else 0, "totalPercentChanges": [{"label": pair.get("label", f"Comparison {index + 1}"), "value": pair.get("totalPercentChange")} for index, pair in enumerate(pair_stats)], "units": item.get("units", ""), "description": item.get("description", ""), "pairStats": pair_stats})
            except WorkspaceError as exc:
                skipped.append({"table": item["table"], "variable": item["name"], "reason": str(exc)})
        if progress: progress(len(variables), len(variables), "", "", phase="scanning")
        return {"year": year, "scanned": len(variables), "changedVariables": len(results), "results": results, "skipped": skipped, "filterField": filter_field, "filterValues": filter_values or []}

    def scan_request(self, reference_id: str, comparison_ids: list[str], year: str, filter_field: str = "", filter_values: list[str] | None = None) -> dict[str, Any]:
        records = [self._record(reference_id), *[self._record(item) for item in comparison_ids]]
        if len(records) < 2:
            raise WorkspaceError("Choose at least one comparison datastore")
        variables = [item for item in self.variables([item["id"] for item in records]) if year in item["years"] and item["name"] != TABLE_KEYS.get(item["table"])]
        def scan_record(item: dict[str, Any]) -> dict[str, Any]:
            mapping = self._county_mapping(item) or {"azone": {}, "bzone": {}}
            return {
                "id": item["id"], "label": item.get("label", item["id"]), "path": item["path"],
                "county": {"azone": mapping["azone"], "bzone": mapping["bzone"]},
                "registrationFingerprint": hashlib.sha256(json.dumps(
                    {key: value for key, value in item.items() if key != "path"}, sort_keys=True, default=str
                ).encode()).hexdigest(),
            }
        return {
            "year": year, "filterField": filter_field, "filterValues": filter_values or [],
            "records": [scan_record(item) for item in records],
            "variables": variables,
        }

    def scan_command(self, request_path: Path, output_path: Path, progress_path: Path, container_name: str) -> tuple[list[str], dict[str, str]]:
        if self.runtime.adapter == "docker":
            request = read_json(request_path, {})
            request["records"] = [{**item, "path": self.runtime.runtime_path(item["path"])} for item in request.get("records", [])]
            write_json(request_path, request)
        return self.runtime.r_command(self.scan_helper, str(request_path), str(output_path), str(progress_path))

    def dashboard(self, reference_id: str, comparison_id: str, year: str, variable_keys: list[str] | None = None, filter_field: str = "", filter_values: list[str] | None = None, sort_by: str = "name") -> dict[str, Any]:
        selected = set(variable_keys or [])
        variables = [item for item in self.variables([reference_id, comparison_id]) if year in item["years"] and (not selected or f"{item['table']}/{item['name']}" in selected) and item["name"] != TABLE_KEYS.get(item["table"])]
        records = [self._record(reference_id), self._record(comparison_id)]
        if self.cache:
            by_table: dict[str,list[str]]={}
            for item in variables: by_table.setdefault(item["table"],[]).append(item["name"])
            for table,names in by_table.items():
                for record in records: self.cache.ensure(Path(record["path"]),year,table,names)
        rows, unavailable = [], []
        for item in variables:
            try:
                assignments = []
                if filter_field == "Bzone" and filter_values:
                    selected_bzones = {str(value) for value in filter_values}
                    aggregates = [
                        self._aggregate_map_record(record, year, item["table"], item["name"], "bzone")
                        for record in records
                    ]
                    scoped = [
                        [value for bzone, value in aggregate["values"].items() if bzone in selected_bzones]
                        for aggregate in aggregates
                    ]
                    left = sum(value["sum"] for value in scoped[0]) if scoped[0] else None
                    right = sum(value["sum"] for value in scoped[1]) if scoped[1] else None
                    total_rows = max(sum(value["count"] for value in values) for values in scoped)
                    changed_rows = None
                    assignments = [
                        {"resultId": record["id"], "status": "assigned", "method": aggregate["assignment"],
                         "matchedRows": aggregate["matchedRows"], "unmatchedRows": aggregate["unmatchedRows"]}
                        for record, aggregate in zip(records, aggregates)
                    ]
                else:
                    payload = self.compare(reference_id, [comparison_id], item["table"], item["name"], year, False, 1, 0, filter_field, filter_values)
                    left, right = payload["referenceSummary"].get("sum"), payload["comparisonSummaries"][0].get("sum")
                    total_rows, changed_rows = payload["totalRows"], payload["changedRows"]
                if left is None or right is None or left == 0:
                    unavailable.append({"table": item["table"], "variable": item["name"], "reason": "No numeric values in the selected geography or zero reference total", "geographyAssignments": assignments}); continue
                rows.append({"table": item["table"], "variable": item["name"], "label": f"{item['table']} / {item['name']}", "units": item.get("units", ""), "description": item.get("description", ""), "referenceSum": left, "comparisonSum": right, "percentChange": (right-left)/abs(left)*100, "changedRows": changed_rows, "totalRows": total_rows, "geographyAssignments": assignments})
            except WorkspaceError as exc:
                unavailable.append({"table": item["table"], "variable": item["name"], "reason": str(exc), "geographyAssignments": [{"status": "unavailable", "reason": str(exc)}]})
        rows.sort(key=lambda row: row["label"].lower())
        token = make_id("dashboard", year)
        geography = self._map_geography(records[0]) if filter_field == "Bzone" else {"names": {}}
        filter_labels = [f"{geography['names'].get(str(value), 'Unknown locality')} · {value}" for value in (filter_values or [])] if filter_field == "Bzone" else list(filter_values or [])
        scope_label = "All locations" if not filter_field or not filter_values else f"{filter_field}: {', '.join(filter_labels)}"
        payload = {
            "dashboardToken": token,
            "reference": self._record(reference_id), "comparison": self._record(comparison_id),
            "year": year, "rows": rows, "unavailable": unavailable, "scanned": len(variables),
            "availableRows": len(rows), "unavailableRows": len(unavailable),
            "filterField": filter_field, "filterValues": filter_values or [],
            "filterLabels": filter_labels, "scopeLabel": scope_label,
            "variableKeys": sorted(selected),
        }
        with self.snapshot_lock:
            self.dashboard_snapshots[token] = payload
            while len(self.dashboard_snapshots) > 8:
                self.dashboard_snapshots.popitem(last=False)
        return {**payload, "sortBy": sort_by}

    def dashboard_snapshot(self, token: str) -> dict[str, Any]:
        with self.snapshot_lock:
            payload = self.dashboard_snapshots.get(token)
            if not payload:
                raise WorkspaceError("Dashboard data expired; generate the dashboard again")
            self.dashboard_snapshots.move_to_end(token)
            return payload

    def dashboard_display(self, token: str, sort_by: str = "name", display_mode: str = "all", threshold: float = 0, count: int = 5, hide_zero: bool = False) -> dict[str, Any]:
        payload = self.dashboard_snapshot(token)
        source = list(payload.get("rows") or [])
        if display_mode == "threshold":
            rows = [row for row in source if abs(float(row.get("percentChange") or 0)) >= max(0, float(threshold or 0))]
        elif display_mode == "extremes":
            limit = max(1, min(int(count or 5), 100))
            increases = sorted((row for row in source if row.get("percentChange", 0) > 0), key=lambda row: -row["percentChange"])[:limit]
            decreases = sorted((row for row in source if row.get("percentChange", 0) < 0), key=lambda row: row["percentChange"])[:limit]
            selected = {f"{row['table']}/{row['variable']}" for row in [*increases, *decreases]}
            rows = [row for row in source if f"{row['table']}/{row['variable']}" in selected]
        else:
            display_mode, rows = "all", source
        if hide_zero:
            rows = [row for row in rows if float(row.get("percentChange") or 0) != 0]
        if sort_by == "value_desc": rows.sort(key=lambda row: -row["percentChange"])
        elif sort_by == "value_asc": rows.sort(key=lambda row: row["percentChange"])
        elif sort_by == "magnitude": rows.sort(key=lambda row: -abs(row["percentChange"]))
        else: rows.sort(key=lambda row: row["label"].lower())
        return {**payload, "rows": rows, "sourceRows": source, "sortBy": sort_by, "displayMode": display_mode, "threshold": threshold, "count": count, "hideZero": hide_zero, "displayedRows": len(rows)}

    @staticmethod
    def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
        output = io.StringIO(newline="")
        fields = list(dict.fromkeys(key for row in rows for key in row.keys())) or ["message"]
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore"); writer.writeheader(); writer.writerows(rows)
        return output.getvalue().encode("utf-8")

    @staticmethod
    def dashboard_pdf(payload: dict[str, Any], increase_color: str = "#2274a7", decrease_color: str = "#be3742") -> bytes:
        def escaped(value: Any) -> str:
            return str(value if value is not None else "").replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        def pdf_color(value: str, fallback: str) -> str:
            color = value if re.fullmatch(r"#[0-9a-fA-F]{6}", str(value or "")) else fallback
            channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
            return " ".join(f"{channel:.3f}" for channel in channels) + " rg"
        increase_pdf = pdf_color(increase_color, "#2274a7")
        decrease_pdf = pdf_color(decrease_color, "#be3742")
        rows = payload.get("rows", [])
        pages = [rows[index:index + 18] for index in range(0, len(rows), 18)] or [[]]
        max_change = max((abs(float(row.get("percentChange") or 0)) for row in rows), default=1) or 1
        objects: list[str] = ["<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
        content_ids = []
        for page_number, page in enumerate(pages, 1):
            title = f"{payload['reference'].get('label','Reference')} to {payload['comparison'].get('label','Comparison')} - {payload.get('year','')}"
            scope = payload.get("scopeLabel") or payload.get("filterField") or "All locations"
            commands = [
                "BT /F1 17 Tf 1 0 0 1 42 576 Tm (VisionEval Workbench Percent-Change Dashboard) Tj ET",
                f"BT /F1 10 Tf 1 0 0 1 42 556 Tm ({escaped(title)}) Tj ET",
                f"BT /F1 8 Tf 1 0 0 1 42 541 Tm ({escaped(scope[:105])}) Tj ET",
                "0.72 G 512 64 m 512 526 l S",
                "BT /F1 8 Tf 1 0 0 1 491 529 Tm (0%) Tj ET",
            ]
            for index, row in enumerate(page):
                y = 510 - index * 24
                value = float(row.get("percentChange") or 0)
                width = min(175, abs(value) / max_change * 175)
                x = 512 if value >= 0 else 512 - width
                color = increase_pdf if value >= 0 else decrease_pdf
                label = str(row.get("label") or "")
                if len(label) > 43:
                    label = f"{label[:42]}..."
                commands.extend([
                    f"BT /F1 9 Tf 0 g 1 0 0 1 42 {y} Tm ({escaped(label)}) Tj ET",
                    f"{color} {x:.2f} {y - 5} {width:.2f} 10 re f",
                    f"BT /F1 8 Tf 0 g 1 0 0 1 702 {y} Tm ({escaped(f'{value:.2f}%')}) Tj ET",
                ])
            if not page:
                commands.append("BT /F1 12 Tf 0 g 1 0 0 1 280 310 Tm (No dashboard values match the current display.) Tj ET")
            commands.append(f"BT /F1 8 Tf 0.35 g 1 0 0 1 704 30 Tm (Page {page_number} of {len(pages)}) Tj ET")
            stream = "\n".join(commands); data = stream.encode("latin-1", "replace")
            objects.append(f"<< /Length {len(data)} >>\nstream\n{data.decode('latin-1')}\nendstream"); content_ids.append(len(objects))
        page_ids = []
        pages_id = len(objects) + len(content_ids) + 1
        for content_id in content_ids:
            objects.append(f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 792 612] /Resources << /Font << /F1 1 0 R >> >> /Contents {content_id} 0 R >>"); page_ids.append(len(objects))
        objects.append(f"<< /Type /Pages /Kids [{' '.join(f'{item} 0 R' for item in page_ids)}] /Count {len(page_ids)} >>"); actual_pages_id = len(objects)
        objects.append(f"<< /Type /Catalog /Pages {actual_pages_id} 0 R >>"); catalog_id = len(objects)
        output = [b"%PDF-1.4\n"]; offsets = [0]
        for index, body in enumerate(objects, 1):
            offsets.append(sum(map(len, output))); output.append(f"{index} 0 obj\n{body}\nendobj\n".encode("latin-1", "replace"))
        xref = sum(map(len, output)); output.append(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
        output.extend(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])
        output.append(f"trailer\n<< /Size {len(objects)+1} /Root {catalog_id} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
        return b"".join(output)


class ComparisonOperationManager:
    """Persistent comparison requests that survive UI reconnects."""
    def __init__(self, service: ComparisonService):
        self.service = service
        self._active: dict[str, dict[str, Any]] = {}
        self.root = service.workspace.exchange / "comparison-operations"
        self.root.mkdir(parents=True, exist_ok=True)
        self.completed = (service.cache.root / "summaries") if service.cache else (self.root / "cache")
        self.completed.mkdir(parents=True, exist_ok=True)
        for operation_path in self.root.glob("*/operation.json"):
            operation = read_json(operation_path, {})
            if operation.get("state") in {"waiting", "running"}:
                operation.update({"state":"waiting","message":"Resuming comparison after restart"}); write_json(operation_path, operation)
                threading.Thread(target=self._run, args=(operation.get("id", operation_path.parent.name),), daemon=True).start()

    def _cache_key(self, payload: dict[str, Any]) -> str:
        table, year, variable = payload.get("table", ""), str(payload.get("year", "2045")), payload.get("variable", "")
        if payload.get("operationKind") == "change-density":
            sources = []
            for datastore_id in (payload.get("reference", ""), payload.get("comparison", "")):
                record = self.service._record(datastore_id); root = Path(record["path"])
                files = []
                for path in sorted((root / year).rglob("*.Rda")):
                    stat = path.stat(); files.append([path.relative_to(root).as_posix(), stat.st_size, stat.st_mtime_ns])
                sources.append([record.get("id"), record.get("registrationFingerprint", ""), files])
            return hashlib.sha256(json.dumps({"schema":1,"request":payload,"sources":sources}, sort_keys=True, default=str).encode()).hexdigest()
        if payload.get("operationKind") == "map":
            datastore_ids = [payload.get("reference", ""), payload.get("comparison", "")]
            records = [self.service._record(datastore_id) for datastore_id in datastore_ids]
            geography = "bzone" if payload.get("geographyLevel") == "bzone" else "azone"
            sources = self.service._map_source_signature(records, year, table, variable, geography)
            return hashlib.sha256(json.dumps({"schema":3,"request":payload,"sources":sources}, sort_keys=True, default=str).encode()).hexdigest()
        names = {variable, TABLE_KEYS.get(table, "")}
        filter_field = payload.get("filterField", "")
        if filter_field == "County": names.update({"Azone", "Bzone"})
        elif filter_field: names.add(filter_field)
        sources = []
        comparison_ids = payload.get("comparisons") or ([payload.get("comparison")] if payload.get("comparison") else [])
        for datastore_id in [payload.get("reference", ""), *comparison_ids]:
            record = self.service._record(datastore_id); root = Path(record["path"])
            files = []
            for name in sorted(names):
                path = root / year / table / f"{name}.Rda"
                if path.is_file():
                    stat = path.stat(); files.append([name, stat.st_size, stat.st_mtime_ns])
            sources.append([record.get("id"), record.get("registeredAt", ""), files])
        return hashlib.sha256(json.dumps({"schema":2,"request":payload,"sources":sources}, sort_keys=True, default=str).encode()).hexdigest()

    def start(self, payload: dict[str, Any]) -> dict[str, Any]:
        operation_id = make_id("comparison", str(payload.get("year", "2045")))
        directory = self.root / operation_id; directory.mkdir()
        cache_key = self._cache_key(payload); cache_path = self.completed / f"{cache_key}.json"
        operation = {"id":operation_id,"state":"waiting","phase":"cache_validation","createdAt":now_iso(),"startedAt":"","finishedAt":"","message":"Waiting to compare","pageReady":False,"cacheKey":cache_key,"cached":cache_path.is_file()}
        write_json(directory / "request.json", payload); write_json(directory / "operation.json", operation)
        # Keep a process-local copy as a guard against transient filesystem
        # visibility delays in packaged Windows WebView sessions.
        self._active[operation_id] = dict(operation)
        if cache_path.is_file():
            shutil.copy2(cache_path, directory / "result.json"); shutil.copy2(cache_path, directory / "page.json")
            cached_result = read_json(directory / "result.json", {})
            if payload.get("operationKind") == "map": self.service.restore_map_snapshot(cached_result)
            elif payload.get("operationKind") == "change-density" and cached_result.get("densityToken"):
                self.service.density_snapshots[cached_result["densityToken"]] = cached_result
            operation.update({"state":"succeeded","phase":"complete","startedAt":now_iso(),"finishedAt":now_iso(),"message":"Loaded cached comparison","pageReady":True}); write_json(directory / "operation.json", operation)
            return self.status(operation_id)
        threading.Thread(target=self._run, args=(operation_id,), daemon=True).start()
        return self.status(operation_id)

    def _run(self, operation_id: str) -> None:
        directory = self.root / operation_id; operation_path = directory / "operation.json"
        operation = read_json(operation_path, {}); operation.update({"state":"running","startedAt":operation.get("startedAt") or now_iso(),"phase":"cache_validation","message":"Validating comparison cache"}); write_json(operation_path, operation)
        try:
            request = read_json(directory / "request.json", {})
            if request.get("operationKind") == "change-density":
                cancelled = lambda: read_json(operation_path, {}).get("state") == "cancelled"
                def progress(**fields):
                    current = read_json(operation_path, {})
                    if current.get("state") == "cancelled":
                        return
                    current.update(fields); write_json(operation_path, current)
                result = self.service.change_density(
                    request.get("reference", ""), request.get("comparison", ""), str(request.get("year", "2045")),
                    request.get("geographyLevel", "bzone"), progress, cancelled,
                )
                if cancelled(): return
                write_json(directory / "result.json", result); write_json(directory / "page.json", result)
                cache_key = operation.get("cacheKey")
                if cache_key: shutil.copy2(directory / "result.json", self.completed / f"{cache_key}.json")
                operation = read_json(operation_path, operation)
                operation.update({"state":"succeeded","phase":"complete","finishedAt":now_iso(),
                                  "message":"Change-density map complete","pageReady":True})
                return
            if request.get("operationKind") == "map":
                operation.update({"phase":"aggregation","message":"Aggregating numeric rows by geography","pageReady":False}); write_json(operation_path, operation)
                cancelled = lambda: read_json(operation_path, {}).get("state") == "cancelled"
                result = self.service.comparison_map(
                    request.get("reference", ""), request.get("comparison", ""), str(request.get("year", "2045")),
                    request.get("table", ""), request.get("variable", ""), request.get("geographyLevel", "azone"), request.get("aggregation", "mean"), cancelled,
                )
                if cancelled(): return
                write_json(directory / "result.json", result); write_json(directory / "page.json", result)
                cache_key = operation.get("cacheKey")
                if cache_key: shutil.copy2(directory / "result.json", self.completed / f"{cache_key}.json")
                operation.update({"state":"succeeded","phase":"complete","finishedAt":now_iso(),"message":"Comparison map complete","pageReady":True})
                return
            args = (request.get("reference", ""), request.get("comparisons") or [], request.get("table", ""), request.get("variable", ""), str(request.get("year", "2045")), bool(request.get("changedOnly")), int(request.get("limit", 100)), int(request.get("offset", 0)), request.get("filterField", ""), request.get("filterValues") or [], request.get("sortColumn", "id"), request.get("sortDirection", "original"))
            mode = request.get("mode", "auto")
            page = self.service.compare(*args, mode=mode) if mode == "aggregate" else self.service.comparison_page(*args)
            if read_json(operation_path, {}).get("state") == "cancelled": return
            write_json(directory / "page.json", page)
            operation.update({"phase":"statistics","message":"First page ready; calculating full statistics","pageReady":True}); write_json(operation_path, operation)
            result = self.service.compare(*args, mode=mode)
            if read_json(operation_path, {}).get("state") == "cancelled": return
            write_json(directory / "result.json", result)
            cache_key = operation.get("cacheKey")
            if cache_key: shutil.copy2(directory / "result.json", self.completed / f"{cache_key}.json")
            operation.update({"state":"succeeded","phase":"complete","finishedAt":now_iso(),"message":"Comparison complete","pageReady":True})
        except Exception as exc:
            if read_json(operation_path, {}).get("state") != "cancelled":
                operation.update({"state":"failed","finishedAt":now_iso(),"message":str(exc)})
        finally:
            if read_json(operation_path, {}).get("state") != "cancelled": write_json(operation_path, operation)

    def status(self, operation_id: str) -> dict[str, Any]:
        directory = self.service.workspace.within(self.root / operation_id, self.root, must_exist=False)
        operation = read_json(directory / "operation.json", {}) if directory.exists() else {}
        if not operation:
            operation = dict(self._active.get(operation_id, {}))
        if not operation: raise WorkspaceError("Unknown comparison operation")
        else: self._active[operation_id] = dict(operation)
        page = read_json(directory / "page.json", None) if operation.get("pageReady") else None
        result = read_json(directory / "result.json", None) if operation.get("state") == "succeeded" else None
        return {**operation,"page":page,"result":result}

    def cancel(self, operation_id: str) -> dict[str, Any]:
        directory = self.service.workspace.within(self.root / operation_id, self.root); path = directory / "operation.json"
        operation = read_json(path, {})
        if operation.get("state") in {"waiting","running"}:
            operation.update({"state":"cancelled","finishedAt":now_iso(),"message":"Comparison cancelled"}); write_json(path, operation)
        return self.status(operation_id)


class ComparisonScanManager:
    def __init__(self, service: ComparisonService):
        self.service = service
        self.root = service.workspace.exchange / "comparison-scans"
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "cache").mkdir(exist_ok=True)
        self.lock = threading.RLock()
        self.processes: dict[str, subprocess.Popen] = {}

    def _cache_key(self, request: dict[str, Any]) -> str:
        fingerprint = []
        for record in request.get("records", []):
            root = Path(record["path"])
            files = []
            for path in sorted((root / str(request.get("year", ""))).rglob("*.Rda")):
                stat = path.stat()
                files.append([path.relative_to(root).as_posix(), stat.st_size, stat.st_mtime_ns])
            listing = root / "DatastoreListing.Rda"
            if listing.is_file():
                stat = listing.stat()
                files.append([listing.name, stat.st_size, stat.st_mtime_ns])
            fingerprint.append([record["id"], record.get("registrationFingerprint", ""), files])
        payload = {"records": fingerprint, "year": request.get("year"), "filterField": request.get("filterField"), "filterValues": request.get("filterValues")}
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def start(self, reference_id: str, comparison_ids: list[str], year: str, filter_field: str = "", filter_values: list[str] | None = None) -> dict[str, Any]:
        request = self.service.scan_request(reference_id, comparison_ids, year, filter_field, filter_values)
        operation_id = make_id("comparison-scan", year)
        directory = self.root / operation_id; directory.mkdir()
        cache_key = self._cache_key(request); cache = self.root / "cache" / f"{cache_key}.json"
        operation = {"id": operation_id, "state": "waiting", "phase": "cache_validation", "createdAt": now_iso(), "startedAt": "", "finishedAt": "", "cacheKey": cache_key, "cached": cache.is_file(), "message": "Validating scan cache", "containerName": f"ve-{operation_id}"[:63]}
        write_json(directory / "request.json", request)
        if cache.is_file():
            shutil.copy2(cache, directory / "result.json")
            operation.update({"state": "succeeded", "phase": "complete", "startedAt": now_iso(), "finishedAt": now_iso(), "message": "Loaded cached change scan"})
            write_json(directory / "operation.json", operation)
            return self.status(operation_id)
        write_json(directory / "operation.json", operation)
        threading.Thread(target=self._run, args=(operation_id, cache), daemon=True).start()
        return self.status(operation_id)

    def _run(self, operation_id: str, cache: Path) -> None:
        directory = self.root / operation_id; operation_path = directory / "operation.json"
        native = self.service.runtime.adapter == "native"
        operation = read_json(operation_path, {}); operation.update({"state": "running", "phase": "preparing_cache" if native else "starting_runtime", "startedAt": now_iso(), "message": "Preparing comparison caches" if native else "Starting batch scanner"}); write_json(operation_path, operation)
        try:
            request = read_json(directory / "request.json", {})
            records = request.get("records", [])
            progress_path, output_path = directory / "progress.json", directory / "result.json"
            write_json(progress_path, {"completed": 0, "total": 0 if native else len(request.get("variables") or []), "table": "", "variable": "", "phase": "preparing_cache" if native else "starting_runtime", "cacheHits": 0, "cacheMisses": 0})
            if native:
                command, environment = None, None
            else:
                try:
                    invocation = self.service.scan_command(directory / "request.json", output_path, progress_path, operation.get("containerName", ""))
                    command, environment = invocation if isinstance(invocation, tuple) else (invocation, None)
                except (FileNotFoundError, OSError, WorkspaceError):
                    command, environment = None, None
            if command:
                process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=environment)
                with self.lock: self.processes[operation_id] = process
                operation.update({"phase": "scanning", "message": "Scanning comparable outputs"}); write_json(operation_path, operation)
                stdout, stderr = process.communicate()
                with self.lock: self.processes.pop(operation_id, None)
                if read_json(operation_path, {}).get("state") == "cancelled": return
                if process.returncode:
                    raise WorkspaceError((stderr or stdout).strip() or "Batch change scan failed")
                result = read_json(output_path, None)
                if not result:
                    raise WorkspaceError("Batch scanner did not produce a result")
            else:
                operation.update({"phase": "preparing_cache", "message": "Preparing comparison caches"}); write_json(operation_path, operation)
                def is_cancelled(): return read_json(operation_path, {}).get("state") == "cancelled"
                def progress(done, total, table, variable, phase="scanning", **details):
                    write_json(progress_path, {"completed":done,"total":total,"table":table,"variable":variable,"phase":phase,**details})
                result = self.service.changes(records[0]["id"], [item["id"] for item in records[1:]], str(request.get("year", "2045")), request.get("filterField", ""), request.get("filterValues") or [], progress, is_cancelled)
                if is_cancelled(): return
                write_json(output_path, result)
            operation.update({"phase": "finalizing", "message": "Finalizing changed outputs"}); write_json(operation_path, operation)
            write_json(progress_path, {"completed": 1, "total": 1, "table": "", "variable": "", "phase": "finalizing"})
            shutil.copy2(directory / "result.json", cache)
            operation.update({"state": "succeeded", "phase": "complete", "finishedAt": now_iso(), "message": "Change scan complete"})
        except Exception as exc:
            if read_json(operation_path, {}).get("state") != "cancelled":
                operation.update({"state": "failed", "finishedAt": now_iso(), "message": str(exc)})
        finally:
            if read_json(operation_path, {}).get("state") != "cancelled": write_json(operation_path, operation)

    def status(self, operation_id: str) -> dict[str, Any]:
        directory = self.service.workspace.within(self.root / operation_id, self.root)
        operation = read_json(directory / "operation.json", {})
        if not operation:
            raise WorkspaceError("Unknown comparison scan")
        progress = read_json(directory / "progress.json", {})
        result = read_json(directory / "result.json", None) if operation.get("state") == "succeeded" else None
        return {**operation, "progress": progress, "result": result}

    def cancel(self, operation_id: str) -> dict[str, Any]:
        directory = self.service.workspace.within(self.root / operation_id, self.root)
        operation_path = directory / "operation.json"; operation = read_json(operation_path, {})
        if operation.get("state") not in {"waiting", "running"}:
            return self.status(operation_id)
        operation.update({"state": "cancelled", "finishedAt": now_iso(), "message": "Change scan cancelled"}); write_json(operation_path, operation)
        with self.lock: process = self.processes.get(operation_id)
        if process and process.poll() is None:
            process.terminate()
        return self.status(operation_id)
