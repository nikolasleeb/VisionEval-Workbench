from __future__ import annotations

import copy
import csv
import itertools
import math
import re
import shutil
import tempfile
import threading
from decimal import Decimal, InvalidOperation, ROUND_FLOOR, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Callable

from .explore import ExploreService, InputValidationError
from .workspace import Workspace, WorkspaceError, make_id, now_iso, read_json, write_json


OPERATIONS = {"set", "add", "subtract", "multiply", "percent", "decrease_percent"}
PROTECTED_COLUMNS = {"geo", "year", "county", "bzone", "azone", "marea", "zone", "taz", "id"}


class HypercubeCancelled(Exception):
    pass


def protected_column(name: str) -> bool:
    value = str(name).lower()
    compact = re.sub(r"[^a-z0-9]+", "", value)
    return value in PROTECTED_COLUMNS or value.endswith("_id") or compact in {"hhid", "vehid", "wkrid"} or compact.endswith("code")


def decimal_text(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def range_values(start: Decimal, end: Decimal, interval: Decimal) -> list[Decimal]:
    if start > end:
        raise WorkspaceError("Hypercube start must be less than or equal to the end")
    if interval < 2:
        raise WorkspaceError("Hypercube interval must be at least 2")
    values: list[Decimal] = []
    value = start
    while value <= end:
        values.append(value)
        value += interval
    if not values or values[-1] != end:
        values.append(end)
    if len(values) > 20:
        raise WorkspaceError("A Hypercube parameter may contain no more than 20 values")
    return values


class HypercubeService:
    def __init__(self, workspace: Workspace, explore: ExploreService):
        self.workspace = workspace
        self.explore = explore
        self.commit_lock = threading.RLock()

    @staticmethod
    def _decimal(value: Any, label: str) -> Decimal:
        try:
            number = Decimal(str(value).strip())
        except (InvalidOperation, AttributeError):
            raise WorkspaceError(f"{label} must be numeric") from None
        if not number.is_finite():
            raise WorkspaceError(f"{label} must be finite")
        return number

    def save_draft(self, payload: dict[str, Any]) -> dict[str, Any]:
        project_id = str(payload.get("projectId", ""))
        with self.workspace.activity_lock:
            _, project = self.workspace.project(project_id)
            if self.workspace.project_type(project) != "hypercube":
                raise WorkspaceError("Choose a dedicated Hypercube project")
            expected = str(payload.get("expectedProjectUpdatedAt", ""))
            if expected and expected != str(project.get("updatedAt", "")):
                raise WorkspaceError("This Hypercube project changed. Refresh it before saving the setup.")
            if project.get("hypercubes") and not self.workspace.hypercube_replacement_allowed(project):
                raise WorkspaceError("This matrix is read-only after a case has been submitted to Run or produced a result")

            raw_axes = payload.get("axes") or []
            if not isinstance(raw_axes, list):
                raise WorkspaceError("Hypercube parameters must be a list")
            if len(raw_axes) > 2:
                raise WorkspaceError("A Hypercube setup may contain no more than two parameter axes")
            axes = []
            library_id = str(project.get("inputLibrary", {}).get("id", ""))
            for index, raw in enumerate(raw_axes, 1):
                if not isinstance(raw, dict):
                    raise WorkspaceError(f"Parameter {index} must be an object")
                filename = str(raw.get("filename", ""))
                if filename:
                    if Path(filename).name != filename or not filename.lower().endswith(".csv"):
                        raise WorkspaceError(f"Parameter {index} has an invalid input filename")
                    self.workspace.input_file(library_id, filename)
                operation = str(raw.get("operation") or "percent")
                if operation not in OPERATIONS:
                    raise WorkspaceError(f"Parameter {index} has an invalid operation")
                axes.append({
                    "filename": filename,
                    "column": str(raw.get("column", "")),
                    "operation": operation,
                    "start": str(raw.get("start", "")),
                    "end": str(raw.get("end", "")),
                    "interval": str(raw.get("interval", "")),
                })
            raw_locations = payload.get("locations") or []
            if not isinstance(raw_locations, list):
                raise WorkspaceError("Hypercube locations must be a list")
            draft = {
                "schemaVersion": 1,
                "revision": make_id("hypercube-draft", str(project.get("name", ""))),
                "savedAt": now_iso(),
                "year": str(payload.get("year", "")),
                "geographyType": str(payload.get("geographyType") or "all"),
                "locations": [str(item) for item in raw_locations if str(item)],
                "axes": axes,
            }
            complete = True
            try:
                self._normalize({
                    "projectId": project_id,
                    "replaceExisting": bool(project.get("hypercubes")),
                    **draft,
                })
            except WorkspaceError:
                complete = False
            draft["complete"] = complete
            project["hypercubeDraft"] = draft
            self.workspace.save_project(project)
            return {
                "projectId": project_id,
                "projectUpdatedAt": project.get("updatedAt", ""),
                "draft": copy.deepcopy(draft),
                "complete": complete,
            }

    def _saved_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        revision = str(payload.get("draftRevision", ""))
        if not revision:
            return payload
        project_id = str(payload.get("projectId", ""))
        _, project = self.workspace.project(project_id)
        draft = project.get("hypercubeDraft")
        if not isinstance(draft, dict) or str(draft.get("revision", "")) != revision:
            raise WorkspaceError("The saved Hypercube setup changed. Save and preview it again before generating.")
        return {
            "projectId": project_id,
            "replaceExisting": bool(project.get("hypercubes")),
            "draftRevision": revision,
            "axes": copy.deepcopy(draft.get("axes") or []),
            "year": str(draft.get("year", "")),
            "geographyType": str(draft.get("geographyType") or "all"),
            "locations": copy.deepcopy(draft.get("locations") or []),
            "acknowledgeLargeMatrix": bool(payload.get("acknowledgeLargeMatrix")),
        }

    def _normalize(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload = self._saved_payload(payload)
        project_id = str(payload.get("projectId", ""))
        _, project = self.workspace.project(project_id)
        if self.workspace.project_type(project) != "hypercube":
            raise WorkspaceError("Choose a dedicated Hypercube project")
        existing_hypercubes = list(project.get("hypercubes") or [])
        if len(existing_hypercubes) > 1:
            raise WorkspaceError("This project contains more than one matrix and must be repaired before continuing")
        ordinary_variations = [
            item for item in project.get("variations", [])
            if not isinstance(item.get("hypercube"), dict)
        ]
        if ordinary_variations:
            raise WorkspaceError("Hypercube projects cannot contain ordinary scenarios")
        replace_existing = bool(payload.get("replaceExisting"))
        if existing_hypercubes and not replace_existing:
            raise WorkspaceError("This Hypercube project already has a matrix. Choose Replace matrix to revise it.")
        if existing_hypercubes and not self.workspace.hypercube_replacement_allowed(project):
            raise WorkspaceError("This matrix cannot be replaced after a case has been submitted to Run or produced a result")
        # A dedicated Hypercube project contains exactly one matrix, so its
        # project name is also the matrix's user-facing name.  Continue
        # accepting legacy payload names, but do not require or persist them
        # for newly generated matrices.
        name = str(project.get("name", "")).strip()
        raw_axes = payload.get("axes")
        if not isinstance(raw_axes, list) or not raw_axes:
            raise WorkspaceError("Choose at least one hypercube parameter")
        if len(raw_axes) > 2:
            raise WorkspaceError("A Hypercube matrix may contain no more than two parameter axes")
        geography_type = str(payload.get("geographyType") or "all")
        raw_locations = payload.get("locations") or []
        if not isinstance(raw_locations, list):
            raise WorkspaceError("Hypercube locations must be a list")
        locations = [str(item) for item in raw_locations if str(item)]
        if geography_type != "all" and not locations:
            raise WorkspaceError("Choose at least one location or use All matching rows")
        year = str(payload.get("year", ""))

        seen: set[tuple[str, str]] = set()
        axes = []
        library_id = str(project.get("inputLibrary", {}).get("id", ""))
        for index, raw in enumerate(raw_axes, 1):
            if not isinstance(raw, dict):
                raise WorkspaceError("Every hypercube parameter must be an object")
            filename = Path(str(raw.get("filename", ""))).name
            if not filename or filename != raw.get("filename") or not filename.lower().endswith(".csv"):
                raise WorkspaceError(f"Parameter {index} has an invalid input filename")
            path, _ = self.workspace.input_file(library_id, filename)
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                columns = list(reader.fieldnames or [])
                source_rows = [list(row.values()) for row in reader]
            column = str(raw.get("column", ""))
            if column not in columns:
                raise WorkspaceError(f"{column or 'Selected column'} was not found in {filename}")
            metadata = self.explore.input_column_metadata(filename, columns, source_rows)
            details = metadata.get(column, {})
            if protected_column(column) or details.get("kind") != "numeric":
                raise WorkspaceError(f"{column} is not a numeric scenario input")
            if not details.get("bulkEditable"):
                reason = details.get("reason") or details.get("protectionReason") or "This field supports direct correction only."
                raise WorkspaceError(f"{filename} / {column} cannot be used as a Hypercube axis. {reason}")
            if details.get("group"):
                raise WorkspaceError(f"{filename} / {column} is part of linked shares and cannot be varied alone. Edit the complete share composition together.")
            key = (filename.lower(), column.lower())
            if key in seen:
                raise WorkspaceError(f"{filename} / {column} is selected more than once")
            seen.add(key)
            operation = str(raw.get("operation", ""))
            if operation not in OPERATIONS:
                raise WorkspaceError(f"Choose a valid operation for {filename} / {column}")
            start = self._decimal(raw.get("start"), f"{column} start")
            end = self._decimal(raw.get("end"), f"{column} end")
            interval = self._decimal(raw.get("interval"), f"{column} interval")
            values = range_values(start, end, interval)
            axes.append({
                "id": make_id("axis", column),
                "filename": filename,
                "column": column,
                "operation": operation,
                "start": decimal_text(start),
                "end": decimal_text(end),
                "interval": decimal_text(interval),
                "values": values,
                "columnType": self.explore.input_column_types(filename, columns).get(column, "number"),
                "columnMetadata": details,
            })
        case_count = math.prod(len(axis["values"]) for axis in axes)
        if case_count > 400:
            raise WorkspaceError("A Hypercube matrix may contain no more than 400 cases")
        return {
            "project": project,
            "projectId": project_id,
            "sourceUpdatedAt": project.get("updatedAt", ""),
            "name": name,
            "year": year,
            "geographyType": geography_type,
            "locations": locations,
            "axes": axes,
            "replaceExisting": bool(existing_hypercubes),
            "existingHypercube": copy.deepcopy(existing_hypercubes[0]) if existing_hypercubes else None,
            "draftRevision": str(payload.get("draftRevision", "")),
        }

    def _matched_rows(self, project_id: str, filename: str, columns: list[str], rows: list[dict[str, str]], year: str, geography_type: str, locations: list[str]) -> list[int]:
        allowed: set[str] | None = None
        target_field = "Geo"
        if geography_type != "all":
            geography = self.workspace.geography_options(project_id, filename)
            level = next((item for item in geography.get("levels", []) if item.get("id") == geography_type and item.get("compatible")), None)
            if not level:
                raise WorkspaceError(f"{filename} is not compatible with the selected geography level")
            selected = [item for item in level.get("values", []) if str(item.get("value")) in locations]
            allowed = {str(value) for item in selected for value in (item.get("targetValues") or [item.get("value")])}
            target_field = str(geography.get("targetField") or "Geo")
        matched = []
        for index, row in enumerate(rows):
            if year and "Year" in row and str(row.get("Year", "")) != year:
                continue
            if allowed is not None and str(row.get(target_field, "")) not in allowed:
                continue
            if any(self._finite_decimal(row.get(column, "")) is not None for column in columns):
                matched.append(index)
        return matched

    @staticmethod
    def _finite_decimal(value: Any) -> Decimal | None:
        try:
            number = Decimal(str(value).strip())
        except (InvalidOperation, AttributeError):
            return None
        return number if number.is_finite() else None

    @staticmethod
    def _calculate(current: Decimal, operation: str, value: Decimal) -> Decimal:
        if operation == "set":
            return value
        if operation == "add":
            return current + value
        if operation == "subtract":
            return current - value
        if operation == "multiply":
            return current * value
        if operation == "percent":
            return current * (Decimal(1) + value / Decimal(100))
        return current * (Decimal(1) - value / Decimal(100))

    def _format_value(self, value: Decimal, column: str, column_type: str, metadata: dict[str, Any] | None = None) -> str:
        if column_type == "integer":
            return decimal_text((value + Decimal("0.5")).to_integral_value(rounding=ROUND_FLOOR))
        settings = self.workspace.settings().get("numericPrecision", {})
        precision = settings.get("batch")
        if not isinstance(precision, int):
            precision = settings.get("default", 2)
        precision = max(int(precision), int((metadata or {}).get("precision") or 0))
        quantizer = Decimal(1).scaleb(-precision)
        return decimal_text(value.quantize(quantizer, rounding=ROUND_HALF_UP))

    def _prepared(self, normalized: dict[str, Any]) -> dict[str, Any]:
        project = normalized["project"]
        library_id = project["inputLibrary"]["id"]
        by_file: dict[str, dict[str, Any]] = {}
        for axis in normalized["axes"]:
            file_record = by_file.get(axis["filename"])
            if file_record is None:
                path, _ = self.workspace.input_file(library_id, axis["filename"])
                with path.open("r", encoding="utf-8-sig", newline="") as handle:
                    reader = csv.DictReader(handle)
                    file_record = {"columns": list(reader.fieldnames or []), "rows": [dict(row) for row in reader]}
                by_file[axis["filename"]] = file_record
            file_record.setdefault("axes", []).append(axis)
        affected_cells = 0
        scope_details = []
        for filename, record in by_file.items():
            axis_columns = [axis["column"] for axis in record["axes"]]
            matched = self._matched_rows(
                normalized["projectId"], filename, axis_columns, record["rows"], normalized["year"],
                normalized["geographyType"], normalized["locations"],
            )
            record["matchedRows"] = matched
            for axis in record["axes"]:
                count = sum(self._finite_decimal(record["rows"][index].get(axis["column"], "")) is not None for index in matched)
                if not count:
                    raise WorkspaceError(f"{filename} / {axis['column']} has no numeric cells in the selected scope")
                axis["matchedCells"] = count
                affected_cells += count
                original_lists = [[row.get(column, "") for column in record["columns"]] for row in record["rows"]]
                metadata = self.explore.input_column_metadata(filename, record["columns"], original_lists)
                for axis_value in axis["values"]:
                    candidate = [dict(row) for row in record["rows"]]
                    for row_index in matched:
                        current = self._finite_decimal(candidate[row_index].get(axis["column"], ""))
                        if current is None:
                            continue
                        next_value = self._calculate(current, axis["operation"], axis_value)
                        candidate[row_index][axis["column"]] = self._format_value(
                            next_value, axis["column"], axis["columnType"], axis.get("columnMetadata")
                        )
                    candidate_lists = [[row.get(column, "") for column in record["columns"]] for row in candidate]
                    try:
                        self.explore.validate_input_rows(filename, record["columns"], candidate_lists, original_lists, metadata)
                    except InputValidationError as error:
                        raise WorkspaceError(
                            f"Hypercube value {decimal_text(axis_value)} is invalid for {filename} / {axis['column']}. {error}"
                        ) from error
            geography = self.workspace.geography_options(normalized["projectId"], filename)
            scope_details.append({
                "filename": filename,
                "targetLevel": str(geography.get("targetLevel") or "location"),
                "matchedRows": len(matched),
                "matchedCells": sum(int(axis.get("matchedCells", 0)) for axis in record["axes"]),
            })
        return {
            **normalized,
            "files": by_file,
            "affectedCellsPerCase": affected_cells,
            "scopeDetails": scope_details,
        }

    @staticmethod
    def _public_axis(axis: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value for key, value in axis.items()
            if key != "values"
        } | {"values": [decimal_text(value) for value in axis["values"]]}

    def preview(self, payload: dict[str, Any]) -> dict[str, Any]:
        prepared = self._prepared(self._normalize(payload))
        count = math.prod(len(axis["values"]) for axis in prepared["axes"])
        examples = []
        for index, combination in enumerate(itertools.product(*(axis["values"] for axis in prepared["axes"]))):
            if index >= 3:
                break
            examples.append([
                {"axisId": axis["id"], "filename": axis["filename"], "column": axis["column"], "value": decimal_text(value)}
                for axis, value in zip(prepared["axes"], combination)
            ])
        return {
            "projectId": prepared["projectId"],
            "name": prepared["name"],
            "year": prepared["year"],
            "geographyType": prepared["geographyType"],
            "locations": prepared["locations"],
            "axes": [self._public_axis(axis) for axis in prepared["axes"]],
            "caseCount": count,
            "affectedCellsPerCase": prepared["affectedCellsPerCase"],
            "scopeDetails": prepared["scopeDetails"],
            "examples": examples,
            "largeMatrix": count > 100,
            "replacingExisting": prepared["replaceExisting"],
            "draftRevision": prepared["draftRevision"],
        }

    def generate(self, payload: dict[str, Any], cancelled: threading.Event, progress: Callable[[int, int], None]) -> dict[str, Any]:
        prepared = self._prepared(self._normalize(payload))
        combinations = itertools.product(*(axis["values"] for axis in prepared["axes"]))
        total = math.prod(len(axis["values"]) for axis in prepared["axes"])
        hypercube_id = make_id("hypercube", prepared["name"])
        project_directory, _ = self.workspace.project(prepared["projectId"])
        staging_root = self.workspace.internal / "staging"
        staging_root.mkdir(parents=True, exist_ok=True)
        operation_staging = Path(tempfile.mkdtemp(prefix="hypercube-", dir=staging_root))
        staged_project = operation_staging / prepared["projectId"]
        backup = operation_staging / "original"
        try:
            shutil.copytree(project_directory, staged_project)
            staged_manifest = copy.deepcopy(prepared["project"])
            if prepared["replaceExisting"]:
                replaced_ids = set(prepared["existingHypercube"].get("scenarioIds") or [])
                staged_manifest["variations"] = [
                    item for item in staged_manifest.get("variations", [])
                    if item.get("id") not in replaced_ids
                ]
                staged_manifest["hypercubes"] = []
                for variation_id in replaced_ids:
                    overlay_directory = staged_project / "overlays" / str(variation_id)
                    if overlay_directory.exists():
                        shutil.rmtree(overlay_directory)
            generated = []
            width = max(3, len(str(total)))
            created_at = now_iso()
            for case_index, combination in enumerate(combinations, 1):
                if cancelled.is_set():
                    raise HypercubeCancelled()
                variation_id = make_id("variation", f"{prepared['name']}-case-{case_index}")
                values = [
                    {"axisId": axis["id"], "filename": axis["filename"], "column": axis["column"], "operation": axis["operation"], "value": decimal_text(value)}
                    for axis, value in zip(prepared["axes"], combination)
                ]
                value_map = {item["axisId"]: value for item, value in zip(values, combination)}
                variation = {
                    "id": variation_id,
                    "name": f"{prepared['name']} · Case {case_index:0{width}d}",
                    "overlays": [],
                    "notes": {},
                    "scenarioNote": "Hypercube values: " + "; ".join(
                        f"{item['filename']} / {item['column']} = {item['value']} ({item['operation']})" for item in values
                    ),
                    "hypercube": {"hypercubeId": hypercube_id, "caseIndex": case_index, "values": values},
                }
                for filename, record in prepared["files"].items():
                    rows = [dict(row) for row in record["rows"]]
                    for axis in record["axes"]:
                        hypercube_value = value_map[axis["id"]]
                        for row_index in record["matchedRows"]:
                            current = self._finite_decimal(rows[row_index].get(axis["column"], ""))
                            if current is None:
                                continue
                            next_value = self._calculate(current, axis["operation"], hypercube_value)
                            rows[row_index][axis["column"]] = self._format_value(next_value, axis["column"], axis["columnType"], axis.get("columnMetadata"))
                    row_lists = [[row.get(column, "") for column in record["columns"]] for row in rows]
                    original_lists = [[row.get(column, "") for column in record["columns"]] for row in record["rows"]]
                    metadata = self.explore.input_column_metadata(filename, record["columns"], original_lists, row_lists)
                    try:
                        self.explore.validate_input_rows(filename, record["columns"], row_lists, original_lists, metadata)
                    except InputValidationError as error:
                        raise WorkspaceError(str(error)) from error
                    overlay = staged_project / "overlays" / variation_id / filename
                    overlay.parent.mkdir(parents=True, exist_ok=True)
                    with overlay.open("w", encoding="utf-8", newline="") as handle:
                        writer = csv.DictWriter(handle, fieldnames=record["columns"], lineterminator="\n")
                        writer.writeheader()
                        writer.writerows(rows)
                    variation["overlays"].append({
                        "fileName": filename,
                        "path": str(project_directory / "overlays" / variation_id / filename),
                        "updatedAt": created_at,
                    })
                staged_manifest.setdefault("variations", []).append(variation)
                generated.append(variation_id)
                progress(case_index, total)
            hypercube = {
                "id": hypercube_id,
                "name": prepared["name"],
                "createdAt": created_at,
                "year": prepared["year"],
                "geographyType": prepared["geographyType"],
                "locations": prepared["locations"],
                "axes": [self._public_axis(axis) for axis in prepared["axes"]],
                "scenarioIds": generated,
            }
            staged_manifest.setdefault("hypercubes", []).append(hypercube)
            staged_manifest.pop("hypercubeDraft", None)
            staged_manifest["updatedAt"] = now_iso()
            write_json(staged_project / "project.json", staged_manifest)
            if cancelled.is_set():
                raise HypercubeCancelled()
            with self.commit_lock:
                current = read_json(project_directory / "project.json", {})
                if current.get("updatedAt", "") != prepared["sourceUpdatedAt"]:
                    raise WorkspaceError("The project changed while the hypercube was being generated. Review it and try again.")
                project_directory.rename(backup)
                try:
                    staged_project.rename(project_directory)
                except Exception:
                    backup.rename(project_directory)
                    raise
                shutil.rmtree(backup)
            return {"projectId": prepared["projectId"], "hypercube": hypercube, "scenarioIds": generated, "caseCount": total}
        finally:
            if operation_staging.exists():
                shutil.rmtree(operation_staging, ignore_errors=True)


class HypercubeOperationManager:
    def __init__(self, service: HypercubeService):
        self.service = service
        self.lock = threading.RLock()
        self.operations: dict[str, dict[str, Any]] = {}
        self.cancel_events: dict[str, threading.Event] = {}
        self.previews: dict[str, dict[str, str]] = {}

    def preview(self, payload: dict[str, Any]) -> dict[str, Any]:
        preview = self.service.preview(payload)
        token = make_id("hypercube-preview", preview["name"])
        with self.lock:
            self.previews[token] = {
                "projectId": str(preview.get("projectId", "")),
                "draftRevision": str(preview.get("draftRevision", "")),
            }
        return {**preview, "previewToken": token}

    def start(self, payload: dict[str, Any]) -> dict[str, Any]:
        draft_revision = str(payload.get("draftRevision", ""))
        if draft_revision:
            token = str(payload.get("previewToken", ""))
            with self.lock:
                record = self.previews.pop(token, None)
            if not record or record != {"projectId": str(payload.get("projectId", "")), "draftRevision": draft_revision}:
                raise WorkspaceError("Preview the current saved Hypercube setup before generating scenarios")
        preview = self.service.preview(payload)
        operation_id = make_id("hypercube-operation", preview["name"])
        operation = {
            "id": operation_id,
            "state": "waiting",
            "phase": "starting",
            "createdAt": now_iso(),
            "startedAt": "",
            "finishedAt": "",
            "message": f"Preparing {preview['caseCount']} hypercube scenarios.",
            "completedCases": 0,
            "totalCases": preview["caseCount"],
            "preview": preview,
            "result": None,
        }
        event = threading.Event()
        with self.lock:
            self.operations[operation_id] = operation
            self.cancel_events[operation_id] = event
        threading.Thread(target=self._run, args=(operation_id, copy.deepcopy(payload)), daemon=True).start()
        return self.status(operation_id)

    def _run(self, operation_id: str, payload: dict[str, Any]) -> None:
        with self.lock:
            operation = self.operations[operation_id]
            operation.update({"state": "running", "phase": "generating", "startedAt": now_iso()})

        def progress(completed: int, total: int) -> None:
            with self.lock:
                operation.update({
                    "completedCases": completed,
                    "totalCases": total,
                    "message": f"Generated {completed} of {total} scenarios in staging.",
                })

        try:
            result = self.service.generate(payload, self.cancel_events[operation_id], progress)
            with self.lock:
                operation.update({
                    "state": "succeeded",
                    "phase": "complete",
                    "finishedAt": now_iso(),
                    "message": f"Created {result['caseCount']} hypercube scenarios.",
                    "result": result,
                })
        except HypercubeCancelled:
            with self.lock:
                operation.update({
                    "state": "cancelled",
                    "phase": "cancelled",
                    "finishedAt": now_iso(),
                    "message": "Hypercube cancelled; no scenarios were created.",
                })
        except Exception as exc:
            with self.lock:
                operation.update({
                    "state": "failed",
                    "phase": "failed",
                    "finishedAt": now_iso(),
                    "message": str(exc),
                })

    def status(self, operation_id: str) -> dict[str, Any]:
        with self.lock:
            operation = self.operations.get(operation_id)
            if not operation:
                raise WorkspaceError("Unknown hypercube operation")
            return copy.deepcopy(operation)

    def cancel(self, operation_id: str) -> dict[str, Any]:
        with self.lock:
            operation = self.operations.get(operation_id)
            if not operation:
                raise WorkspaceError("Unknown hypercube operation")
            if operation.get("state") not in {"waiting", "running", "cancelling"}:
                return copy.deepcopy(operation)
            self.cancel_events[operation_id].set()
            operation.update({"state": "cancelling", "phase": "cancelling", "message": "Cancelling hypercube…"})
            return copy.deepcopy(operation)
