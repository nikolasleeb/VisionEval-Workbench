from __future__ import annotations

import csv
import copy
import hashlib
import io
import json
import math
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
import threading
import time
import zipfile
from pathlib import Path
from typing import Any, Callable

from .comparison import MICRODATA_TABLES, TABLE_KEYS, ComparisonService, _changed, _number
from .workspace import ACTIVE_RUN_STATES, Workspace, WorkspaceError, make_id, now_iso, read_json, write_json


AGGREGATIONS = {"auto", "sum", "mean", "median", "min", "max"}
METRICS = {"value", "absolute_change", "percent_change", "typical_row_change", "breadth", "pair_difference"}
ADDITIVE_HINTS = (
    "count", "number", "population", "persons", "households", "workers", "jobs", "vehicles",
    "miles", "vmt", "dvmt", "trips", "energy", "fuel", "emission", "co2", "cost", "revenue",
)
NON_ADDITIVE_HINTS = (
    "rate", "ratio", "share", "proportion", "percent", "percentage", "per ", "/", "price",
    "average", "mean", "median", "density", "mpg", "mpkwh",
)


def _quantile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * fraction
    lower, upper = math.floor(position), math.ceil(position)
    return ordered[lower] if lower == upper else ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


class HypercubeAnalysisService:
    """Read-only response-surface analysis over registered Hypercube datastores."""

    def __init__(self, workspace: Workspace, comparison: ComparisonService, summary_helper: Path | None = None):
        self.workspace = workspace
        self.comparison = comparison
        self.summary_helper = (summary_helper or workspace.exchange / "system" / "hypercube_summary.R").resolve()
        cache_root = getattr(getattr(comparison, "cache", None), "root", workspace.exchange / "comparison-cache")
        self.summary_root = Path(cache_root) / "summaries" / "hypercube-index"
        self.summary_root.mkdir(parents=True, exist_ok=True)

    def _project(self, project_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        _, project = self.workspace.project(project_id)
        if project.get("projectType") != "hypercube" or not project.get("hypercubes"):
            raise WorkspaceError("Choose a generated Hypercube project")
        return project, project["hypercubes"][0]

    def _records(self, project: dict[str, Any]) -> dict[str, dict[str, Any]]:
        allowed = set(project.get("datastoreIds") or [])
        records = [
            item for item in self.workspace.display_catalog(False).get("datastores", [])
            if item.get("id") in allowed and item.get("verification") == "verified"
        ]
        output: dict[str, dict[str, Any]] = {}
        for item in sorted(records, key=lambda value: str(value.get("completedAt", ""))):
            variation_id = str(item.get("variationId") or ("baseline" if item.get("role") == "baseline" else ""))
            if variation_id:
                output[variation_id] = item
        return output

    @staticmethod
    def _public_record(record: dict[str, Any] | None) -> dict[str, Any] | None:
        if not record:
            return None
        return {key: value for key, value in record.items() if key not in {"path", "source"}}

    def inventory(self, project_id: str) -> dict[str, Any]:
        project, hypercube = self._project(project_id)
        records = self._records(project)
        variations = {item.get("id"): item for item in project.get("variations", [])}
        latest_jobs: dict[str, dict[str, Any]] = {}
        for path in self.workspace.runs.glob("*/job.json"):
            job = read_json(path, {})
            if job.get("projectId") != project_id:
                continue
            variation_id = str(job.get("variationId", ""))
            if variation_id and str(job.get("createdAt", "")) >= str(latest_jobs.get(variation_id, {}).get("createdAt", "")):
                latest_jobs[variation_id] = job
        baseline = records.get("baseline")
        baseline_template = str((baseline or {}).get("templateFingerprint", ""))
        cases = []
        for variation_id in hypercube.get("scenarioIds") or []:
            variation = variations.get(variation_id, {})
            record = records.get(variation_id)
            job_state = str(latest_jobs.get(variation_id, {}).get("state", ""))
            compatible = not record or not baseline_template or str(record.get("templateFingerprint", "")) == baseline_template
            status = "complete" if record and compatible else "incompatible" if record else job_state if job_state in {"failed", "cancelled"} else "missing"
            cases.append({
                "variationId": variation_id,
                "name": variation.get("name", variation_id),
                "caseIndex": (variation.get("hypercube") or {}).get("caseIndex"),
                "values": (variation.get("hypercube") or {}).get("values") or [],
                "status": status,
                "compatible": compatible,
                "datastore": self._public_record(record),
            })
        complete = [item for item in cases if item["status"] == "complete"]
        digests = sorted({str(item["datastore"].get("runtimeImageDigest", "")) for item in complete if item.get("datastore")})
        templates = sorted({str(item["datastore"].get("templateFingerprint", "")) for item in complete if item.get("datastore")})
        warnings = []
        if not baseline:
            warnings.append("No verified baseline result is registered for this Hypercube project.")
        if len(digests) > 1:
            warnings.append("Cases were produced by more than one runtime image digest.")
        if len(templates) > 1:
            warnings.append("Cases were produced from more than one model-package fingerprint.")
        incompatible = sum(item["status"] == "incompatible" for item in cases)
        failed = sum(item["status"] == "failed" for item in cases)
        cancelled = sum(item["status"] == "cancelled" for item in cases)
        if incompatible:
            warnings.append(f"{incompatible} case result(s) use an incompatible model-package fingerprint and are excluded.")
        return {
            "project": {"id": project["id"], "name": project["name"]},
            "hypercube": hypercube,
            "baseline": self._public_record(baseline),
            "cases": cases,
            "caseCount": len(cases),
            "completedCases": len(complete),
            "missingCases": len(cases) - len(complete),
            "failedCases": failed,
            "cancelledCases": cancelled,
            "incompatibleCases": incompatible,
            "runtimeDigests": digests,
            "templateFingerprints": templates,
            "warnings": warnings,
        }

    @staticmethod
    def _datastore_fingerprint(inventory: dict[str, Any]) -> str:
        identity = {
            "baseline": ((inventory.get("baseline") or {}).get("id", ""), (inventory.get("baseline") or {}).get("executionFingerprint", "")),
            "cases": [
                ((case.get("datastore") or {}).get("id", ""), (case.get("datastore") or {}).get("executionFingerprint", ""))
                for case in inventory.get("cases") or []
            ],
        }
        return hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()

    def _summary_matrix(
        self,
        inventory: dict[str, Any],
        table: str,
        variable: str,
        year: str,
        metric: str,
        selected_case_ids: list[str],
    ) -> dict[str, Any] | None:
        """Return an aggregate matrix from a fingerprinted discovery summary when possible."""
        expected = self._datastore_fingerprint(inventory)
        for database in sorted(self.summary_root.glob("*.sqlite"), key=lambda path: path.stat().st_mtime_ns, reverse=True):
            try:
                with sqlite3.connect(database) as connection:
                    row = connection.execute("SELECT payload FROM discovery WHERE id=1").fetchone()
                payload = json.loads(row[0]) if row else {}
            except (OSError, sqlite3.Error, ValueError, TypeError):
                continue
            if (
                str(payload.get("projectId", "")) != str(inventory["project"]["id"])
                or str(payload.get("year", "")) != year
                or str(payload.get("datastoreFingerprint", "")) != expected
            ):
                continue
            summary = next((item for item in payload.get("results") or [] if item.get("table") == table and item.get("variable") == variable), None)
            if not summary:
                continue
            cached_cells = {str(item.get("variationId", "")): item for item in summary.get("cells") or []}
            if not all(case_id in cached_cells for case_id in selected_case_ids):
                continue
            case_by_id = {item["variationId"]: item for item in inventory["cases"]}
            key = {
                "value": "scenarioValue", "absolute_change": "absoluteChange", "percent_change": "percentChange",
                "typical_row_change": "typicalRowChange", "breadth": "breadth",
            }.get(metric)
            if not key:
                return None
            cells = []
            for case_id in selected_case_ids:
                cached, case = cached_cells[case_id], case_by_id[case_id]
                cells.append({
                    **case, "value": cached.get(key), "scenarioValue": cached.get("scenarioValue"),
                    "referenceValue": cached.get("referenceValue"), "absoluteChange": cached.get("absoluteChange"),
                    "percentChange": cached.get("percentChange"), "typicalRowChange": cached.get("typicalRowChange"),
                    "breadth": cached.get("breadth"), "extremeRowChange": cached.get("extremeRowChange"),
                    "aggregation": cached.get("aggregation", "mean"),
                    "aggregationLabel": f"{str(cached.get('aggregation', 'mean')).title()} (summary cache)",
                    "matchedRows": None, "referenceRows": None, "comparisonRows": None, "unmatchedRows": None,
                    "warning": "Aggregate loaded from the fingerprinted Hypercube summary cache.",
                })
            try:
                database.touch()
            except OSError:
                pass
            return {"cells": cells, "summaryBacked": True, "summaryGeneratedAt": payload.get("generatedAt", "")}
        return None

    @staticmethod
    def _tree_size(path: Path) -> int:
        total = 0
        if not path.exists():
            return 0
        for item in path.rglob("*"):
            try:
                if item.is_file():
                    total += item.stat().st_size
            except OSError:
                pass
        return total

    def storage(self, project_id: str) -> dict[str, Any]:
        inventory = self.inventory(project_id)
        paths: set[Path] = set()
        for item in [inventory.get("baseline"), *[case.get("datastore") for case in inventory["cases"]]]:
            if not item or not item.get("id"):
                continue
            record = self.comparison._record(str(item["id"]))
            paths.add(Path(record["path"]).parent)
        datastore_bytes = export_bytes = 0
        export_directories = 0
        for results in paths:
            datastore_bytes += self._tree_size(results / "Datastore")
            size = self._tree_size(results / "output")
            export_bytes += size
            export_directories += int(size > 0)
        cache = self.comparison.cache.report() if self.comparison.cache else {"bytes": 0, "entries": 0, "limitBytes": 0}
        return {
            "projectId": project_id,
            "caseCount": inventory["caseCount"],
            "completedCases": inventory["completedCases"],
            "datastoreBytes": datastore_bytes,
            "exportBytes": export_bytes,
            "reclaimableBytes": export_bytes,
            "exportDirectories": export_directories,
            "comparisonCache": cache,
        }

    def run_plan(self, project_id: str) -> dict[str, Any]:
        project, hypercube = self._project(project_id)
        image_digest = self.comparison.runtime.image_digest()
        latest: dict[str, dict[str, Any]] = {}
        for job in self.comparison.runtime.list_jobs(include_archived=True):
            if job.get("projectId") != project_id:
                continue
            key = "baseline" if job.get("baseline") else str(job.get("variationId", ""))
            if key and str(job.get("createdAt", "")) >= str(latest.get(key, {}).get("createdAt", "")):
                latest[key] = job
        names = {str(item.get("id", "")): str(item.get("name", "")) for item in project.get("variations") or []}

        def classify(variation_id: str) -> str:
            job = latest.get(variation_id, {})
            state = str(job.get("state", ""))
            if state in ACTIVE_RUN_STATES or state == "waiting":
                return state
            if self.workspace.current_result(project, variation_id, image_digest, getattr(self.comparison.runtime, "native_home", None)):
                return "successful"
            if state in {"failed", "cleanup_failed"}:
                return "failed"
            return "missing"

        entries = [{"id": "baseline", "name": "Baseline", "baseline": True, "status": classify("baseline")}]
        entries.extend({"id": item, "name": names.get(item, item), "baseline": False, "status": classify(item)} for item in hypercube.get("scenarioIds") or [])
        counts: dict[str, int] = {}
        for item in entries:
            counts[item["status"]] = counts.get(item["status"], 0) + 1
        return {"project": {"id": project["id"], "name": project["name"]}, "entries": entries, "counts": counts, "total": len(entries)}

    def start_run_plan(self, payload: dict[str, Any]) -> dict[str, Any]:
        project_id, selection = str(payload.get("projectId", "")), str(payload.get("selection", ""))
        if selection not in {"missing", "failed"}:
            raise WorkspaceError("Hypercube run selection must be missing or failed")
        plan = self.run_plan(project_id)
        wanted = [item for item in plan["entries"] if item["status"] == selection]
        if not wanted:
            raise WorkspaceError(f"This Hypercube project has no {selection} work to run")
        include_baseline = any(item["baseline"] for item in wanted)
        variation_ids = [item["id"] for item in wanted if not item["baseline"]]
        mode = str(payload.get("mode", "parallel"))
        return self.comparison.runtime.create_batch(project_id, variation_ids, include_baseline, mode, [item["id"] for item in wanted])

    def cleanup_exports(self, project_id: str) -> dict[str, Any]:
        project, _ = self._project(project_id)
        if any(job.get("projectId") == project_id and job.get("state") in ACTIVE_RUN_STATES for job in self.workspace.active_run_records()):
            raise WorkspaceError("Wait for every run in this Hypercube project to finish or stop before removing exports")
        records = self._records(project)
        removed_directories = removed_bytes = 0
        for record in records.values():
            resolved = Path(self.comparison._record(record["id"])["path"]).resolve()
            results = resolved.parent
            self.workspace.within(results, self.workspace.models)
            output = results / "output"
            if not output.is_dir():
                continue
            removed_bytes += self._tree_size(output)
            shutil.rmtree(output)
            removed_directories += 1
        return {"projectId": project_id, "removedDirectories": removed_directories, "removedBytes": removed_bytes, **self.storage(project_id)}

    def options(self, project_id: str) -> dict[str, Any]:
        inventory = self.inventory(project_id)
        ids = [item["id"] for item in [inventory.get("baseline"), *[case.get("datastore") for case in inventory["cases"]]] if item]
        if not ids:
            return {**inventory, "variables": [], "years": []}
        # Baseline plus one completed case establishes the output catalog without
        # repeatedly intersecting 82 directory trees. Matrix calculation reports
        # individual missing values explicitly.
        variables = self.comparison.variables(ids[:2] if len(ids) > 1 else ids)
        years = sorted({year for item in variables for year in item.get("years", [])})
        return {**inventory, "variables": variables, "years": years}

    @staticmethod
    def _auto_aggregation(table: str, variable: str, metadata: dict[str, Any], count: int) -> tuple[str, str]:
        if count <= 1:
            return "direct", "Stored scalar"
        text = " ".join(str(metadata.get(key, "")) for key in ("units", "description", "type")) + " " + variable
        lowered = text.lower()
        if any(hint in lowered for hint in NON_ADDITIVE_HINTS):
            return "mean", "Unweighted mean inferred from rate/proportion metadata"
        if any(hint in lowered for hint in ADDITIVE_HINTS):
            return "sum", "Total inferred from additive output metadata"
        if table in MICRODATA_TABLES:
            return "mean", "Unweighted mean across run-local records"
        return "mean", "Unweighted mean; no authoritative aggregation metadata was available"

    @staticmethod
    def _aggregate(values: list[Any], method: str) -> float | None:
        numeric = [number for value in values if (number := _number(value)) is not None]
        if not numeric:
            return None
        if method in {"direct", "mean"}:
            return numeric[0] if method == "direct" else sum(numeric) / len(numeric)
        if method == "sum":
            return sum(numeric)
        if method == "median":
            return _quantile(numeric, .5)
        if method == "min":
            return min(numeric)
        if method == "max":
            return max(numeric)
        raise WorkspaceError("Unknown Hypercube aggregation")

    def _scoped(self, record: dict[str, Any], year: str, table: str, variable: str, field: str, values: list[str]) -> dict[str, Any]:
        root = Path(record["path"])
        column = self.comparison._keyed(root, year, table, variable)
        keys = column["order"]
        if field and values:
            allowed = self.comparison._matching_location_keys(record, root, year, table, keys, field, values)
            keys = [key for key in keys if key in allowed]
        return {"keys": keys, "values": {key: column["values"].get(key) for key in keys}, "keyName": column["keyName"]}

    def _case_measure(
        self, baseline: dict[str, Any], comparison: dict[str, Any], year: str, table: str, variable: str,
        aggregation: str, metric: str, filter_field: str, filter_values: list[str], metadata: dict[str, Any],
    ) -> dict[str, Any]:
        left = self._scoped(baseline, year, table, variable, filter_field, filter_values)
        right = self._scoped(comparison, year, table, variable, filter_field, filter_values)
        resolved, label = self._auto_aggregation(table, variable, metadata, len(left["keys"])) if aggregation == "auto" else (aggregation, aggregation.title())
        left_value = self._aggregate(list(left["values"].values()), resolved)
        right_value = self._aggregate(list(right["values"].values()), resolved)
        common = [key for key in left["keys"] if key in right["values"]]
        numeric_pairs = [
            (a, b) for key in common
            if (a := _number(left["values"].get(key))) is not None and (b := _number(right["values"].get(key))) is not None
        ]
        stable = table not in MICRODATA_TABLES
        symmetric = [200 * abs(b - a) / (abs(a) + abs(b)) for a, b in numeric_pairs if abs(a) + abs(b) > 0] if stable else []
        row_absolute = [abs(b - a) for a, b in numeric_pairs] if stable else []
        changed = sum(_changed(a, b) for a, b in numeric_pairs) if stable else None
        absolute = right_value - left_value if left_value is not None and right_value is not None else None
        percent = self.comparison._percent_change(left_value, right_value)
        metrics = {
            "value": right_value,
            "absolute_change": absolute,
            "percent_change": percent,
            "typical_row_change": sum(symmetric) / len(symmetric) if symmetric else None,
            "breadth": changed / len(numeric_pairs) * 100 if changed is not None and numeric_pairs else None,
            "pair_difference": absolute,
        }
        warning = ""
        if metric in {"typical_row_change", "breadth"} and not stable:
            warning = "Run-local record identifiers cannot be matched safely; use an aggregate metric."
        return {
            "value": metrics[metric], "scenarioValue": right_value, "referenceValue": left_value,
            "absoluteChange": absolute, "percentChange": percent,
            "typicalRowChange": metrics["typical_row_change"], "breadth": metrics["breadth"],
            "extremeRowChange": max(row_absolute, default=None),
            "aggregation": resolved, "aggregationLabel": label, "matchedRows": len(numeric_pairs),
            "referenceRows": len(left["keys"]), "comparisonRows": len(right["keys"]),
            "unmatchedRows": len(set(left["keys"]) ^ set(right["keys"])), "warning": warning,
        }

    def matrix(
        self,
        payload: dict[str, Any],
        progress: Callable[[int, int, str], None] | None = None,
        cancelled: Callable[[], bool] | None = None,
    ) -> dict[str, Any]:
        project_id = str(payload.get("projectId", "")); inventory = self.inventory(project_id)
        baseline_public = inventory.get("baseline")
        if not baseline_public:
            raise WorkspaceError("Run and verify this Hypercube project's baseline first")
        baseline = self.comparison._record(str(baseline_public["id"]))
        table, variable, year = str(payload.get("table", "")), str(payload.get("variable", "")), str(payload.get("year", ""))
        if not table or not variable or not year:
            raise WorkspaceError("Choose an output table, variable, and year")
        aggregation = str(payload.get("aggregation", "auto")); metric = str(payload.get("metric", "percent_change"))
        if aggregation not in AGGREGATIONS or metric not in METRICS:
            raise WorkspaceError("Unknown Hypercube analysis calculation")
        filter_field = str(payload.get("filterField", "")); filter_values = [str(item) for item in payload.get("filterValues") or []]
        metadata = self.comparison._metadata(baseline).get(f"{table}/{variable}", {})
        case_by_id = {item["variationId"]: item for item in inventory["cases"]}
        selected_case_ids = [str(item) for item in payload.get("caseIds") or []] or list(case_by_id)
        summary = None
        if aggregation == "auto" and not filter_field and not filter_values and not payload.get("pairCaseIds"):
            summary = self._summary_matrix(inventory, table, variable, year, metric, selected_case_ids)
        if summary:
            return {
                "project": inventory["project"], "hypercube": inventory["hypercube"], "baseline": baseline_public,
                "table": table, "variable": variable, "year": year, "metric": metric, "aggregationRequested": aggregation,
                "metadata": metadata, "filterField": filter_field, "filterValues": filter_values,
                "cells": summary["cells"], "unavailable": [], "pairComparison": None, "generatedAt": now_iso(),
                "summaryBacked": True, "summaryGeneratedAt": summary.get("summaryGeneratedAt", ""),
            }
        cells, unavailable = [], []
        total_cases = len(selected_case_ids)
        for index, case_id in enumerate(selected_case_ids, 1):
            if cancelled and cancelled():
                raise WorkspaceError("Hypercube analysis cancelled")
            case = case_by_id.get(case_id)
            if not case or not case.get("datastore"):
                unavailable.append({"variationId": case_id, "reason": "No verified result"})
                continue
            try:
                result = self._case_measure(
                    baseline, self.comparison._record(case["datastore"]["id"]), year, table, variable,
                    aggregation, metric, filter_field, filter_values, metadata,
                )
                cells.append({**case, "datastore": case["datastore"], **result})
            except WorkspaceError as exc:
                unavailable.append({"variationId": case_id, "reason": str(exc)})
            if progress:
                progress(index, total_cases, str((case or {}).get("name") or case_id))
        pair = None
        pair_ids = [str(item) for item in payload.get("pairCaseIds") or []]
        if len(pair_ids) == 2 and all(case_by_id.get(item, {}).get("datastore") for item in pair_ids):
            first, second = (case_by_id[item] for item in pair_ids)
            result = self._case_measure(
                self.comparison._record(first["datastore"]["id"]), self.comparison._record(second["datastore"]["id"]),
                year, table, variable, aggregation, "pair_difference", filter_field, filter_values, metadata,
            )
            pair = {"first": first, "second": second, **result}
        return {
            "project": inventory["project"], "hypercube": inventory["hypercube"], "baseline": baseline_public,
            "table": table, "variable": variable, "year": year, "metric": metric, "aggregationRequested": aggregation,
            "metadata": metadata, "filterField": filter_field, "filterValues": filter_values,
            "cells": cells, "unavailable": unavailable, "pairComparison": pair, "generatedAt": now_iso(),
        }

    @staticmethod
    def csv_bytes(payload: dict[str, Any]) -> bytes:
        output = io.StringIO(newline="")
        fields = ["caseIndex", "scenario", *[axis.get("column", "axis") for axis in payload.get("hypercube", {}).get("axes", [])], "value", "scenarioValue", "referenceValue", "absoluteChange", "percentChange", "aggregation", "matchedRows", "unmatchedRows", "units"]
        writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n"); writer.writeheader()
        for cell in payload.get("cells") or []:
            axis_values = {item.get("column"): item.get("value") for item in cell.get("values") or []}
            writer.writerow({
                "caseIndex": cell.get("caseIndex"), "scenario": cell.get("name"), **axis_values,
                "value": cell.get("value"), "scenarioValue": cell.get("scenarioValue"), "referenceValue": cell.get("referenceValue"),
                "absoluteChange": cell.get("absoluteChange"), "percentChange": cell.get("percentChange"),
                "aggregation": cell.get("aggregationLabel"), "matchedRows": cell.get("matchedRows"), "unmatchedRows": cell.get("unmatchedRows"),
                "units": (payload.get("metadata") or {}).get("units", ""),
            })
        return output.getvalue().encode("utf-8")

    def discover(self, payload: dict[str, Any], progress: Callable[..., None], cancelled: Callable[[], bool]) -> dict[str, Any]:
        project_id, year = str(payload.get("projectId", "")), str(payload.get("year", ""))
        requested_aggregation = str(payload.get("aggregation") or "median")
        if requested_aggregation not in {"sum", "mean", "median", "min", "max", "auto"}:
            raise WorkspaceError("Choose an aggregation before finding changes")
        options = self.options(project_id)
        baseline_public = options.get("baseline")
        if not baseline_public:
            raise WorkspaceError("Run and verify the Hypercube baseline before indexing outputs")
        fingerprint = str(payload.get("_sourceFingerprint", ""))
        database = self.summary_root / f"{fingerprint}.sqlite" if fingerprint else None
        if database and database.is_file():
            with sqlite3.connect(database) as connection:
                row = connection.execute("SELECT payload FROM discovery WHERE id=1").fetchone()
            if row:
                return self._decorate_discovery(json.loads(row[0]), self.inventory(project_id))
        variables = [item for item in options.get("variables", []) if year in item.get("years", []) and item.get("name") != TABLE_KEYS.get(item.get("table", ""))]
        tables: dict[str, list[dict[str, Any]]] = {}
        for item in variables:
            if requested_aggregation == "auto":
                method, _ = self._auto_aggregation(str(item.get("table", "")), str(item.get("name", "")), item, 2)
            else:
                method = requested_aggregation
            tables.setdefault(str(item["table"]), []).append({
                "name": item["name"], "units": item.get("units", ""), "description": item.get("description", ""),
                "aggregation": "mean" if method == "direct" else method,
            })
        cases = [case for case in options.get("cases", []) if case.get("status") == "complete" and case.get("datastore")]
        baseline = self.comparison._record(str(baseline_public["id"]))
        request_payload = {
            "projectId": project_id, "year": year, "baseline": {"id": baseline["id"], "path": baseline["path"]},
            "cases": [{"id": case["variationId"], "name": case["name"], "caseIndex": case.get("caseIndex"), "values": case.get("values") or [], "path": self.comparison._record(str(case["datastore"]["id"]))["path"]} for case in cases],
            "tables": [{"table": table, "key": TABLE_KEYS.get(table, ""), "variables": items} for table, items in sorted(tables.items())],
            "sourceFingerprint": fingerprint,
            "datastoreFingerprint": self._datastore_fingerprint(self.inventory(project_id)),
        }
        directory = Path(tempfile.mkdtemp(prefix="hypercube-index-", dir=self.workspace.exchange))
        try:
            request_path, output_path, progress_path = directory / "request.json", directory / "result.json", directory / "progress.json"
            if self.comparison.runtime.adapter == "docker":
                request_payload["baseline"]["path"] = self.comparison.runtime.runtime_path(request_payload["baseline"]["path"])
                for case in request_payload["cases"]:
                    case["path"] = self.comparison.runtime.runtime_path(case["path"])
            write_json(request_path, request_payload)
            command, environment = self.comparison.runtime.r_command(self.summary_helper, str(request_path), str(output_path), str(progress_path))
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=environment)
            last = None
            while process.poll() is None:
                if cancelled():
                    process.terminate()
                    try: process.wait(timeout=5)
                    except subprocess.TimeoutExpired: process.kill()
                    raise WorkspaceError("Find All Changes cancelled")
                current = read_json(progress_path, {})
                if current and current != last:
                    progress(
                        int(current.get("completed", 0)), int(current.get("total", 0)),
                        str(current.get("table", "")), str(current.get("current", "")),
                        phase=str(current.get("phase", "indexing")), bytes_read=int(current.get("bytesRead", 0)),
                        summaries_written=int(current.get("summariesWritten", 0)), heartbeat_at=str(current.get("heartbeatAt", now_iso())),
                    )
                    last = current
                time.sleep(.25)
            stdout, stderr = process.communicate()
            if process.returncode:
                raise WorkspaceError((stderr or stdout).strip() or "Hypercube summary indexing failed")
            result = read_json(output_path, None)
            if not result:
                raise WorkspaceError("Hypercube summary indexing produced no result")
            result = self._decorate_discovery(result, self.inventory(project_id))
            if database:
                with sqlite3.connect(database) as connection:
                    connection.execute("CREATE TABLE IF NOT EXISTS discovery (id INTEGER PRIMARY KEY, payload TEXT NOT NULL)")
                    connection.execute("INSERT OR REPLACE INTO discovery(id,payload) VALUES(1,?)", (json.dumps(result, separators=(",", ":")),))
                    connection.commit()
            return result
        finally:
            shutil.rmtree(directory, ignore_errors=True)

    @staticmethod
    def _decorate_discovery(result: dict[str, Any], inventory: dict[str, Any]) -> dict[str, Any]:
        """Normalize legacy summaries and derive transparent per-scenario measures."""
        cases = {str(item.get("variationId", "")): item for item in inventory.get("cases") or []}
        measures: dict[str, list[dict[str, Any]]] = {case_id: [] for case_id in cases}
        for output in result.get("results") or []:
            output.pop("geographicSpread", None)
            for cell in output.get("cells") or []:
                case = cases.get(str(cell.get("variationId", "")), {})
                cell.setdefault("caseIndex", case.get("caseIndex")); cell.setdefault("values", copy.deepcopy(case.get("values") or []))
        for output in result.get("scenarioOutputs") or result.get("results") or []:
            for cell in output.get("cells") or []:
                case_id = str(cell.get("variationId", "")); case = cases.get(case_id, {})
                cell.setdefault("caseIndex", case.get("caseIndex")); cell.setdefault("values", copy.deepcopy(case.get("values") or []))
                left, right, percent = _number(cell.get("referenceValue")), _number(cell.get("scenarioValue")), _number(cell.get("percentChange"))
                changed = left is not None and right is not None and round(left, 5) != round(right, 5)
                if case_id in measures:
                    measures[case_id].append({"table": output.get("table"), "variable": output.get("variable"), "percentChange": percent, "absoluteChange": _number(cell.get("absoluteChange")), "changed": changed})
        summaries = []
        for case_id, case in cases.items():
            entries = measures.get(case_id) or []; usable = [item for item in entries if item["percentChange"] is not None]
            magnitudes = [abs(float(item["percentChange"])) for item in usable]; ordered = sorted(magnitudes); middle = len(ordered) // 2
            median = None if not ordered else ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2
            changed_count = sum(1 for item in entries if item["changed"])
            summaries.append({
                "variationId": case_id, "name": case.get("name", case_id), "caseIndex": case.get("caseIndex"), "values": copy.deepcopy(case.get("values") or []),
                "typicalAbsoluteChange": median, "largestAbsoluteChange": max(magnitudes, default=None),
                "changedOutputs": changed_count, "changedOutputPercent": (changed_count / len(entries) * 100) if entries else None,
                "positiveOutputs": sum(1 for item in usable if float(item["percentChange"]) > 0), "negativeOutputs": sum(1 for item in usable if float(item["percentChange"]) < 0),
                "eligibleOutputs": len(usable), "totalOutputs": len(entries), "excludedOutputs": len(entries) - len(usable),
                "topOutputs": sorted(usable, key=lambda item: abs(float(item["percentChange"])), reverse=True)[:5],
            })
        result["scenarioSummaries"] = summaries
        return result


class HypercubeAnalysisOperationManager:
    """Cancellable matrix work with fingerprinted, disposable result caching."""

    def __init__(self, service: HypercubeAnalysisService):
        self.service = service
        cache_root = getattr(getattr(service.comparison, "cache", None), "root", service.workspace.exchange / "comparison-cache")
        self.root = Path(cache_root) / "summaries" / "hypercube-matrices"
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.operations: dict[str, dict[str, Any]] = {}
        self.cancel_events: dict[str, threading.Event] = {}

    def _identity(self, request: dict[str, Any], inventory: dict[str, Any]) -> str:
        source = {
            "request": request,
            "baseline": (
                (inventory.get("baseline") or {}).get("id", ""),
                (inventory.get("baseline") or {}).get("executionFingerprint", ""),
            ),
            "cases": [
                (
                    str(case.get("variationId", "")),
                    (case.get("datastore") or {}).get("id", ""),
                    (case.get("datastore") or {}).get("executionFingerprint", ""),
                )
                for case in inventory.get("cases") or []
            ],
        }
        return hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest()

    def start(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload = {key: copy.deepcopy(value) for key, value in payload.items() if key != "_automaticIndex"}
        # Validate the immutable request before returning an operation id.
        project_id = str(payload.get("projectId", ""))
        inventory = self.service.inventory(project_id)
        request = copy.deepcopy(payload)
        request_identity = self._identity(request, inventory)
        cache_path = self.root / f"{request_identity}.json"
        with self.lock:
            existing = next((item for item in self.operations.values() if item.get("requestIdentity") == request_identity and item.get("state") in {"waiting", "running", "cancelling", "succeeded"}), None)
            if existing:
                return copy.deepcopy(existing)
        cached_result = read_json(cache_path, None)
        operation_id = make_id("hypercube-analysis", project_id)
        operation = {
            "id": operation_id,
            "kind": "hypercube_pair" if len(request.get("pairCaseIds") or []) == 2 else "hypercube_matrix",
            "requestIdentity": request_identity,
            "request": request,
            "state": "waiting",
            "phase": "starting",
            "createdAt": now_iso(),
            "startedAt": "",
            "finishedAt": "",
            "heartbeatAt": now_iso(),
            "message": "Waiting to calculate the response matrix",
            "progress": {"completed": 0, "total": 0, "current": ""},
            "bytesRead": 0,
            "summariesWritten": 0,
            "cacheBytesAdded": 0,
            "cached": bool(cached_result),
            "result": cached_result,
        }
        if cached_result:
            operation.update({
                "state": "succeeded", "phase": "complete", "startedAt": now_iso(), "finishedAt": now_iso(),
                "message": f"Loaded {len(cached_result.get('cells') or [])} cached cases",
            })
        with self.lock:
            self.operations[operation_id] = operation
            if not cached_result:
                self.cancel_events[operation_id] = threading.Event()
        if cached_result:
            try:
                os.utime(cache_path, None)
            except OSError:
                pass
            return self.status(operation_id)
        threading.Thread(target=self._run, args=(operation_id, request), daemon=True).start()
        return self.status(operation_id)

    def _run(self, operation_id: str, payload: dict[str, Any]) -> None:
        before = self.service.comparison.cache.report().get("bytes", 0) if self.service.comparison.cache else 0
        with self.lock:
            operation = self.operations[operation_id]
            operation.update({"state": "running", "phase": "reading", "startedAt": now_iso(), "heartbeatAt": now_iso(), "message": "Reading baseline and case Datastores"})

        def progress(completed: int, total: int, current: str) -> None:
            with self.lock:
                current_operation = self.operations.get(operation_id)
                if not current_operation or current_operation.get("state") == "cancelled":
                    return
                current_operation.update({
                    "phase": "calculating",
                    "heartbeatAt": now_iso(),
                    "message": f"Calculating case {completed} of {total}: {current}",
                    "progress": {"completed": completed, "total": total, "current": current},
                })

        try:
            result = self.service.matrix(payload, progress, self.cancel_events[operation_id].is_set)
            if self.cancel_events[operation_id].is_set():
                raise WorkspaceError("Hypercube analysis cancelled")
            result["cacheReused"] = False
            cache_path = self.root / f"{self.operations[operation_id]['requestIdentity']}.json"
            write_json(cache_path, result)
            enforce_limit = getattr(self.service.comparison.cache, "enforce_limit", None)
            if callable(enforce_limit):
                enforce_limit()
            after = self.service.comparison.cache.report().get("bytes", 0) if self.service.comparison.cache else before
            with self.lock:
                operation = self.operations[operation_id]
                operation.update({
                    "state": "succeeded", "phase": "complete", "finishedAt": now_iso(), "heartbeatAt": now_iso(),
                    "message": f"Calculated {len(result.get('cells') or [])} cases",
                    "cacheBytesAdded": max(0, int(after) - int(before)), "result": result,
                })
        except Exception as exc:
            with self.lock:
                operation = self.operations[operation_id]
                cancelled = self.cancel_events[operation_id].is_set()
                operation.update({
                    "state": "cancelled" if cancelled else "failed",
                    "phase": "cancelled" if cancelled else "failed",
                    "finishedAt": now_iso(), "heartbeatAt": now_iso(),
                    "message": "Hypercube analysis cancelled" if cancelled else str(exc),
                })

    def status(self, operation_id: str) -> dict[str, Any]:
        with self.lock:
            operation = self.operations.get(operation_id)
            if not operation:
                raise WorkspaceError("Unknown Hypercube analysis operation")
            return copy.deepcopy(operation)

    def cancel(self, operation_id: str) -> dict[str, Any]:
        with self.lock:
            operation = self.operations.get(operation_id)
            if not operation:
                raise WorkspaceError("Unknown Hypercube analysis operation")
            if operation.get("state") in {"waiting", "running", "cancelling"}:
                self.cancel_events[operation_id].set()
                operation.update({"state": "cancelling", "phase": "cancelling", "heartbeatAt": now_iso(), "message": "Cancelling Hypercube analysis…"})
            return copy.deepcopy(operation)

    def active(self) -> list[dict[str, Any]]:
        with self.lock:
            return [copy.deepcopy(item) for item in self.operations.values() if item.get("state") in {"waiting", "running", "cancelling"}]

class HypercubeDiscoveryManager:
    def __init__(self, service: HypercubeAnalysisService, error_recorder: Callable[[dict[str, Any]], Any] | None = None):
        self.service = service
        self.error_recorder = error_recorder
        cache_root = getattr(getattr(service.comparison, "cache", None), "root", service.workspace.exchange / "comparison-cache")
        self.root = Path(cache_root) / "summaries" / "hypercube-analysis"
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        for path in self.root.glob("*/operation.json"):
            operation = read_json(path, {})
            if operation.get("state") in {"waiting", "running"}:
                operation.update({"state": "waiting", "message": "Resuming Find All Changes"}); write_json(path, operation)
                threading.Thread(target=self._run, args=(path.parent.name,), daemon=True).start()

    def start(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            return self._start_locked(payload)

    @staticmethod
    def _normalize_request(payload: dict[str, Any]) -> dict[str, Any]:
        """Canonical discovery scope; Response Matrix controls never affect this cache."""
        return {
            "projectId": str(payload.get("projectId", "")),
            "year": str(payload.get("year", "")),
            "aggregation": str(payload.get("aggregation") or "median"),
        }

    def _fingerprint(self, payload: dict[str, Any]) -> str:
        payload = self._normalize_request(payload)
        inventory = self.service.inventory(str(payload.get("projectId", "")))
        fingerprint_payload = {
            "request": payload,
            "baseline": (inventory.get("baseline") or {}).get("executionFingerprint", ""),
            "cases": [
                ((case.get("datastore") or {}).get("id", ""), (case.get("datastore") or {}).get("executionFingerprint", ""))
                for case in inventory.get("cases") or []
            ],
        }
        return hashlib.sha256(json.dumps(fingerprint_payload, sort_keys=True).encode()).hexdigest()

    def cached(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload = self._normalize_request(payload)
        source_fingerprint = self._fingerprint(payload)
        for operation_path in sorted(self.root.glob("*/operation.json"), reverse=True):
            existing = read_json(operation_path, {})
            saved_request = self._normalize_request(read_json(operation_path.parent / "request.json", {}))
            compatible = existing.get("sourceFingerprint") == source_fingerprint or self._fingerprint(saved_request) == source_fingerprint
            if compatible and existing.get("state") == "succeeded" and (operation_path.parent / "result.json").is_file():
                existing["cached"] = True
                write_json(operation_path, existing)
                return {**self.status(operation_path.parent.name), "cached": True, "reconnected": False}
        return {"state": "missing", "cached": False, "result": None}

    def _start_locked(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload = self._normalize_request(payload)
        source_fingerprint = self._fingerprint(payload)
        for operation_path in sorted(self.root.glob("*/operation.json"), reverse=True):
            existing = read_json(operation_path, {})
            saved_request = self._normalize_request(read_json(operation_path.parent / "request.json", {}))
            compatible = existing.get("sourceFingerprint") == source_fingerprint or self._fingerprint(saved_request) == source_fingerprint
            if compatible and existing.get("state") in {"waiting", "running", "cancelling", "succeeded"}:
                if existing.get("state") == "succeeded":
                    existing["cached"] = True; write_json(operation_path, existing)
                return {**self.status(operation_path.parent.name), "cached": existing.get("state") == "succeeded", "reconnected": existing.get("state") != "succeeded"}
        operation_id = make_id("hypercube-discovery", str(payload.get("projectId", "")))
        directory = self.root / operation_id; directory.mkdir()
        operation = {"id": operation_id, "kind": "hypercube_discovery", "state": "waiting", "phase": "starting", "createdAt": now_iso(), "startedAt": "", "finishedAt": "", "message": "Waiting to find all changes", "progress": {"completed": 0, "total": 0}, "sourceFingerprint": source_fingerprint, "cached": False}
        write_json(directory / "request.json", {**payload, "_sourceFingerprint": source_fingerprint}); write_json(directory / "operation.json", operation)
        threading.Thread(target=self._run, args=(operation_id,), daemon=True).start()
        completed = sorted((path for path in self.root.glob("*/operation.json") if read_json(path, {}).get("state") in {"succeeded", "failed", "cancelled"}), key=lambda path: path.stat().st_mtime, reverse=True)
        for stale in completed[10:]:
            shutil.rmtree(stale.parent, ignore_errors=True)
        return self.status(operation_id)

    def _run(self, operation_id: str) -> None:
        directory = self.root / operation_id; path = directory / "operation.json"
        operation = read_json(path, {}); operation.update({"state": "running", "phase": "scanning", "startedAt": operation.get("startedAt") or now_iso(), "message": "Scanning Hypercube outputs"}); write_json(path, operation)
        cancelled = lambda: read_json(path, {}).get("state") == "cancelled"
        def progress(completed: int, total: int, table: str, variable: str, **details: Any) -> None:
            current = read_json(path, operation)
            if current.get("state") == "cancelled": return
            phase = str(details.get("phase", "indexing"))
            current.update({
                "phase": phase, "heartbeatAt": details.get("heartbeat_at") or now_iso(),
                "bytesRead": int(details.get("bytes_read", current.get("bytesRead", 0))),
                "summariesWritten": int(details.get("summaries_written", current.get("summariesWritten", 0))),
                "message": f"Indexing {completed} of {total}" + (f": {table} / {variable}" if table else ""),
                "progress": {"completed": completed, "total": total, "table": table, "current": variable, "phase": phase},
            }); write_json(path, current)
        try:
            result = self.service.discover(read_json(directory / "request.json", {}), progress, cancelled)
            if cancelled(): return
            result["cacheReused"] = False
            write_json(directory / "result.json", result)
            operation = read_json(path, operation); operation.update({"state": "succeeded", "phase": "complete", "finishedAt": now_iso(), "message": f"Found {len(result['results'])} changed outputs"}); write_json(path, operation)
        except Exception as exc:
            if not cancelled():
                operation = read_json(path, operation); operation.update({"state": "failed", "phase": "failed", "finishedAt": now_iso(), "message": str(exc)}); write_json(path, operation)
                if self.error_recorder:
                    request = read_json(directory / "request.json", {})
                    self.error_recorder({
                        "source": "hypercube-discovery",
                        "message": str(exc),
                        "path": "/api/hypercube-analysis/discovery/start",
                        "context": {
                            "operationId": operation_id,
                            "projectId": str(request.get("projectId", "")),
                            "year": str(request.get("year", "")),
                            "phase": str(operation.get("phase", "failed")),
                            "progress": operation.get("progress") or {},
                        },
                    })

    def status(self, operation_id: str) -> dict[str, Any]:
        directory = self.service.workspace.within(self.root / operation_id, self.root)
        operation = read_json(directory / "operation.json", {})
        if not operation: raise WorkspaceError("Unknown Hypercube discovery operation")
        result = read_json(directory / "result.json", None) if operation.get("state") == "succeeded" else None
        if result:
            request = read_json(directory / "request.json", {})
            result = self.service._decorate_discovery(result, self.service.inventory(str(request.get("projectId", ""))))
        return {**operation, "result": result}

    def cancel(self, operation_id: str) -> dict[str, Any]:
        directory = self.service.workspace.within(self.root / operation_id, self.root); path = directory / "operation.json"
        operation = read_json(path, {})
        if operation.get("state") in {"waiting", "running"}:
            operation.update({"state": "cancelled", "phase": "cancelled", "finishedAt": now_iso(), "message": "Find All Changes cancelled"}); write_json(path, operation)
        return self.status(operation_id)

    def active(self) -> list[dict[str, Any]]:
        return [read_json(path, {}) for path in self.root.glob("*/operation.json") if read_json(path, {}).get("state") in {"waiting", "running", "cancelling"}]


class HypercubeCaseExportManager:
    """Prepare disposable, external CSV packages for verified Hypercube results."""

    TERMINAL = {"succeeded", "failed", "cancelled"}

    def __init__(self, service: HypercubeAnalysisService):
        self.service = service
        self.workspace = service.workspace
        self.runtime = service.comparison.runtime
        self.root = self.workspace.exchange / "hypercube-case-exports"
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        for operation_path in self.root.glob("*/operation.json"):
            operation = read_json(operation_path, {})
            if operation.get("state") not in self.TERMINAL:
                operation.update({
                    "state": "failed", "phase": "interrupted", "finishedAt": now_iso(),
                    "message": "Workbench closed before this export finished; queue it again.",
                })
                write_json(operation_path, operation)
            staging = self._staging_path(operation_path.parent.name)
            shutil.rmtree(staging, ignore_errors=True)

    @staticmethod
    def _filename(value: str) -> str:
        safe = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-.")
        return safe or "hypercube-case"

    @staticmethod
    def _directory_size(path: Path) -> int:
        return sum(item.stat().st_size for item in path.rglob("*") if item.is_file()) if path.is_dir() else 0

    def options(self, project_id: str) -> dict[str, Any]:
        inventory = self.service.inventory(project_id)
        items: list[dict[str, Any]] = []
        baseline = inventory.get("baseline")
        if baseline and baseline.get("id"):
            items.append({
                "id": "baseline", "name": "Baseline", "baseline": True, "caseIndex": None,
                "values": [], "status": "complete", "datastoreId": baseline["id"],
                "executionFingerprint": baseline.get("executionFingerprint", ""),
                "completedAt": baseline.get("completedAt", ""),
            })
        for case in inventory.get("cases") or []:
            datastore = case.get("datastore") or {}
            if case.get("status") != "complete" or not datastore.get("id"):
                continue
            items.append({
                "id": case["variationId"], "name": case["name"], "baseline": False,
                "caseIndex": case.get("caseIndex"), "values": copy.deepcopy(case.get("values") or []),
                "status": "complete", "datastoreId": datastore["id"],
                "executionFingerprint": datastore.get("executionFingerprint", ""),
                "completedAt": datastore.get("completedAt", ""),
            })
        return {"project": inventory["project"], "maxSelection": 3, "items": items}

    def _validated_snapshot(self, payload: dict[str, Any]) -> dict[str, Any]:
        project_id, item_id = str(payload.get("projectId", "")), str(payload.get("itemId") or payload.get("id") or "")
        current = next((item for item in self.options(project_id)["items"] if item["id"] == item_id), None)
        if not current:
            raise WorkspaceError("This Hypercube result is missing, incomplete, or no longer verified")
        supplied_datastore = str(payload.get("datastoreId", ""))
        supplied_fingerprint = str(payload.get("executionFingerprint", ""))
        if supplied_datastore and supplied_datastore != current["datastoreId"]:
            raise WorkspaceError("This Hypercube result changed before export; refresh and select it again")
        if supplied_fingerprint and supplied_fingerprint != str(current.get("executionFingerprint", "")):
            raise WorkspaceError("This Hypercube result changed before export; refresh and select it again")
        record = self.service.comparison._record(str(current["datastoreId"]))
        if record.get("verification") != "verified":
            raise WorkspaceError("Only verified completed Hypercube results can be exported")
        changing_id = "baseline" if current.get("baseline") else current["id"]
        if any(
            str(job.get("projectId", "")) == project_id
            and str(job.get("variationId", "")) == changing_id
            for job in self.workspace.active_run_records()
        ):
            raise WorkspaceError("This Hypercube result is actively changing; wait for its run to finish")
        return {**current, "projectId": project_id, "projectName": self.options(project_id)["project"]["name"]}

    def start(self, payload: dict[str, Any]) -> dict[str, Any]:
        snapshot = self._validated_snapshot(payload)
        operation_id = make_id("hypercube-case-export", snapshot["id"])
        directory = self.root / operation_id
        directory.mkdir()
        operation = {
            "id": operation_id, "kind": "hypercube_case_export", "state": "waiting", "phase": "waiting",
            "createdAt": now_iso(), "startedAt": "", "finishedAt": "", "heartbeatAt": now_iso(),
            "message": f"Waiting to prepare {snapshot['name']}", "progress": {"completed": 0, "total": 4},
            "item": snapshot, "filename": f"{self._filename(snapshot['projectName'])}-{self._filename(snapshot['name'])}.zip",
        }
        write_json(directory / "request.json", snapshot)
        write_json(directory / "operation.json", operation)
        threading.Thread(target=self._run, args=(operation_id,), daemon=True).start()
        return self.status(operation_id)

    def _update(self, operation_id: str, **values: Any) -> dict[str, Any]:
        with self.lock:
            path = self.root / operation_id / "operation.json"
            operation = read_json(path, {})
            operation.update(values)
            operation["heartbeatAt"] = now_iso()
            write_json(path, operation)
            return operation

    def _cancelled(self, operation_id: str) -> bool:
        return read_json(self.root / operation_id / "operation.json", {}).get("state") in {"cancelling", "cancelled"}

    def _copy_model(self, source: Path, staging: Path) -> None:
        def clone(source_file: str, target_file: str) -> str:
            try:
                os.link(source_file, target_file)
            except OSError:
                shutil.copy2(source_file, target_file)
            return target_file
        shutil.copytree(source, staging, copy_function=clone)
        shutil.rmtree(staging / "results" / "output", ignore_errors=True)

    def _staging_path(self, operation_id: str) -> Path:
        # VisionEval appends another generated CSV directory below this path.
        # Keep the private staging component fixed and short so exports remain
        # below legacy Windows MAX_PATH limits even for deeply nested workspaces.
        suffix = hashlib.sha256(operation_id.encode("utf-8")).hexdigest()[:12]
        return self.workspace.models / f".hce-{suffix}"

    def _run(self, operation_id: str) -> None:
        directory = self.root / operation_id
        staging = self._staging_path(operation_id)
        heartbeat_stop = threading.Event()
        terminal_update: dict[str, Any] = {}
        def keep_heartbeat() -> None:
            while not heartbeat_stop.wait(1):
                with self.lock:
                    path = directory / "operation.json"; operation = read_json(path, {})
                    if operation.get("state") not in {"waiting", "running", "cancelling"}: return
                    operation["heartbeatAt"] = now_iso(); write_json(path, operation)
        threading.Thread(target=keep_heartbeat, daemon=True).start()
        try:
            snapshot = self._validated_snapshot(read_json(directory / "request.json", {}))
            record = self.service.comparison._record(snapshot["datastoreId"])
            datastore = self.workspace.within(record["path"])
            source_model = self.workspace.within(datastore.parent.parent, self.workspace.models)
            required = max(512 * 1024 * 1024, self._directory_size(datastore) * 2)
            free = shutil.disk_usage(self.workspace.models).free
            if free < required:
                raise WorkspaceError(f"Not enough temporary disk space. Free at least {required - free} more bytes and try again.")
            self._update(operation_id, state="running", phase="preparing", startedAt=now_iso(), message=f"Preparing {snapshot['name']}", progress={"completed": 1, "total": 4})
            self._copy_model(source_model, staging)
            if self._cancelled(operation_id):
                raise WorkspaceError("Hypercube case export cancelled")
            self._update(operation_id, phase="generating", message="Generating output CSVs from the Datastore", progress={"completed": 2, "total": 4})
            self.runtime.export_model_results(staging, directory / "export.log", lambda: self._cancelled(operation_id))
            if self._cancelled(operation_id):
                raise WorkspaceError("Hypercube case export cancelled")
            self._update(operation_id, phase="compressing", message="Compressing inputs and outputs", progress={"completed": 3, "total": 4})
            manifest = {
                "format": "VisionEval Workbench Hypercube case CSV export", "version": 1,
                "project": {"id": snapshot["projectId"], "name": snapshot["projectName"]},
                "case": {key: snapshot.get(key) for key in ("id", "name", "baseline", "caseIndex", "values")},
                "runtime": {"image": record.get("runtimeImage", ""), "digest": record.get("runtimeImageDigest", ""), "runId": record.get("runId", "")},
                "fingerprints": {"execution": snapshot.get("executionFingerprint", ""), "template": record.get("templateFingerprint", ""), "inputs": record.get("inputStateFingerprint", "")},
                "completedAt": snapshot.get("completedAt", ""), "createdAt": now_iso(),
            }
            if record.get("runId"):
                try:
                    job = self.runtime.job(str(record["runId"]))
                    manifest["runtime"].update({key: job.get(key) for key in ("startedAt", "finishedAt", "durationSeconds", "resultRetentionMode")})
                except WorkspaceError:
                    pass
            artifact = directory / "export.zip"
            with zipfile.ZipFile(artifact, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
                archive.writestr("manifest.json", json.dumps(manifest, indent=2, sort_keys=True))
                files = [(path, prefix, root) for root, prefix in ((staging / "inputs", "inputs"), (staging / "results" / "output", "outputs")) if root.is_dir() for path in sorted(root.rglob("*.csv"))]
                for index, (path, prefix, root) in enumerate(files, 1):
                    if self._cancelled(operation_id): raise WorkspaceError("Hypercube case export cancelled")
                    archive.write(path, f"{prefix}/{path.relative_to(root).as_posix()}")
                    self._update(operation_id, detail=f"Compressed {index} of {len(files)} CSV files", filesCompleted=index, filesTotal=len(files))
            terminal_update = {"state": "succeeded", "phase": "complete", "finishedAt": now_iso(), "message": f"Prepared {snapshot['name']}", "progress": {"completed": 4, "total": 4}, "artifactBytes": artifact.stat().st_size}
        except Exception as exc:
            cancelled = self._cancelled(operation_id)
            terminal_update = {"state": "cancelled" if cancelled else "failed", "phase": "cancelled" if cancelled else "failed", "finishedAt": now_iso(), "message": "Hypercube case export cancelled" if cancelled else str(exc)}
        finally:
            heartbeat_stop.set()
            shutil.rmtree(staging, ignore_errors=True)
            if terminal_update:
                self._update(operation_id, **terminal_update)

    def status(self, operation_id: str) -> dict[str, Any]:
        directory = self.workspace.within(self.root / operation_id, self.root)
        operation = read_json(directory / "operation.json", {})
        if not operation:
            raise WorkspaceError("Unknown Hypercube case export")
        return operation

    def cancel(self, operation_id: str) -> dict[str, Any]:
        operation = self.status(operation_id)
        if operation.get("state") in {"waiting", "running", "cancelling"}:
            operation.update({"state": "cancelling", "phase": "cancelling", "message": "Cancelling Hypercube case export…", "heartbeatAt": now_iso()})
            write_json(self.root / operation_id / "operation.json", operation)
        return operation

    def artifact(self, operation_id: str) -> tuple[Path, str]:
        operation = self.status(operation_id)
        path = self.root / operation_id / "export.zip"
        if operation.get("state") != "succeeded" or not path.is_file():
            raise WorkspaceError("This Hypercube case export is not ready")
        return path, str(operation.get("filename") or "hypercube-case.zip")

    def active(self) -> list[dict[str, Any]]:
        return [read_json(path, {}) for path in self.root.glob("*/operation.json") if read_json(path, {}).get("state") in {"waiting", "running", "cancelling"}]
