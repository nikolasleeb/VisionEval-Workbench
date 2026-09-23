from __future__ import annotations

import csv
import json
import math
import re
from pathlib import Path
from typing import Any

from .workspace import Workspace, WorkspaceError


IDENTIFIER_FIELDS = {"geo", "azone", "bzone", "czone", "marea", "region", "hhid", "vehid", "wkrid", "year"}
EXPLANATION_DATE_RE = re.compile(r"^(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}$", re.IGNORECASE)
EXPLANATION_TITLE_RE = re.compile(r"^(Optional\s+)?File\s+\d{1,3}[\s_.-].+|^\d{1,3}[_\s.-].+", re.IGNORECASE)
EXPLANATION_CHUNK_RE = re.compile(r"^<(p|h3)>(.*)</\1>$", re.DOTALL)


class InputValidationError(WorkspaceError):
    def __init__(self, message: str, errors: list[dict[str, Any]]):
        super().__init__(message)
        self.errors = errors


def _strip_explanation_header(html: str) -> str:
    chunks = html.splitlines()
    while chunks:
        match = EXPLANATION_CHUNK_RE.match(chunks[0].strip())
        if not match:
            break
        value = re.sub(r"<[^>]+>", "", match.group(2)).strip()
        if EXPLANATION_TITLE_RE.match(value) or EXPLANATION_DATE_RE.match(value):
            chunks.pop(0)
            continue
        break
    return "\n".join(chunks)


class ExploreService:
    def __init__(self, workspace: Workspace, catalog_path: Path, conflicts_path: Path | None = None, dependency_path: Path | None = None):
        self.workspace = workspace
        self.catalog_path = Path(catalog_path)
        try:
            self.catalog = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            self.catalog = {"variables": {}, "explanations": {}}
        try:
            self.conflicts = json.loads((conflicts_path or catalog_path.with_name("unit_conflicts.json")).read_text(encoding="utf-8")).get("conflicts", [])
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            self.conflicts = []
        validation_path = catalog_path.with_name("input_validation_rules.json")
        if not validation_path.is_file():
            validation_path = Path(__file__).resolve().parents[1] / "input_validation_rules.json"
        try:
            self.validation_rules = json.loads(validation_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            self.validation_rules = {"defaults": {"numericMinimum": 0, "fractionPrecision": 6, "groupTolerance": 0.000001}, "files": {}}
        self.spec_inputs: dict[tuple[str, str], dict[str, Any]] = {}
        self.spec_files: set[str] = set()
        try:
            dependency = json.loads((dependency_path or catalog_path.with_name("dependency_catalog.json")).read_text(encoding="utf-8"))
            for module in dependency.get("modules", {}).values():
                for item in module.get("Inp", []):
                    for filename in str(item.get("file", "")).split("|"):
                        if filename:
                            safe_name = Path(filename).name.lower()
                            self.spec_files.add(safe_name)
                            self.spec_inputs.setdefault((safe_name, str(item.get("name", "")).lower()), {**item, "module": module.get("id", "")})
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            pass

    def catalog_for(self, explanation_catalog_path: Path | None = None) -> dict[str, Any]:
        if not explanation_catalog_path:
            return self.catalog
        try:
            package = json.loads(explanation_catalog_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return self.catalog
        return {
            **self.catalog,
            "variables": {**self.catalog.get("variables", {}), **package.get("variables", {})},
            "inputFields": {**self.catalog.get("inputFields", {}), **package.get("inputFields", {})},
            "explanations": {**self.catalog.get("explanations", {}), **package.get("explanations", {})},
            "package": package.get("package", {}),
        }

    def input_column_types(self, filename: str, columns: list[str]) -> dict[str, str]:
        """Return storage-sensitive types for editable VisionEval input fields."""
        fields = self.catalog.get("inputFields", {}).get(Path(filename).name.lower(), {})
        variables = self.catalog.get("variables", {})
        output: dict[str, str] = {}
        for column in columns:
            base = str(column).split(".", 1)[0]
            key = re.sub(r"[^a-z0-9]+", "", base.lower())
            field = next((item for item in fields.values() if str(item.get("field", "")).split(".", 1)[0].lower() == base.lower()), {})
            candidates = variables.get(key, [])
            variable = next((item for item in candidates if str(item.get("name", "")).lower() == base.lower()), {})
            value_type = str(field.get("type") or variable.get("type") or "").lower()
            units = str(field.get("units") or variable.get("units") or "").upper()
            if value_type in {"integer", "people"} or units in {"PRSN", "HH", "JOB", "DU", "VEH"}:
                output[column] = "integer"
            elif value_type:
                output[column] = value_type
            else:
                output[column] = "number"
        return output

    def input_column_metadata(
        self,
        filename: str,
        columns: list[str],
        source_rows: list[list[Any]],
        current_rows: list[list[Any]] | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Describe safe editor behavior for numeric and low-cardinality fields."""
        declared = self.input_column_types(filename, columns)
        file_rules = self.validation_rules.get("files", {}).get(Path(filename).name.lower(), {})
        column_rules = file_rules.get("columns", {})
        groups = file_rules.get("groups", [])
        group_by_column = {
            member: group for group in groups for member in group.get("members", [])
        }
        defaults = self.validation_rules.get("defaults", {})
        fraction_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.validation_rules.get("fractionPatterns", [])]
        output: dict[str, dict[str, Any]] = {}
        rows = [*source_rows, *(current_rows or [])]
        for index, column in enumerate(columns):
            normalized = re.sub(r"[^a-z0-9]+", "", str(column).lower())
            rule = column_rules.get(column, {})
            protected = (
                rule.get("kind") == "protected"
                or normalized in (IDENTIFIER_FIELDS | {"county", "zone", "taz", "id"})
                or str(column).lower().endswith("_id") or normalized.endswith("code")
            )
            values: list[str] = []
            seen: set[str] = set()
            for row in rows:
                value = str(row[index]) if index < len(row) else ""
                if value not in seen:
                    seen.add(value)
                    values.append(value)
            nonblank = [value for value in values if value.strip()]
            all_numeric = bool(nonblank) and all(self._is_number(value) for value in nonblank)
            if protected:
                kind, bulk_editable = "protected", False
            elif all_numeric or group_by_column.get(column):
                kind, bulk_editable = "numeric", True
            elif 2 <= len(nonblank) <= 50:
                kind, bulk_editable = "categorical", True
            else:
                kind, bulk_editable = "text", False
            direct_editable = kind in {"numeric", "categorical"}
            bulk_editable = bool(bulk_editable and rule.get("bulkEditable", True))
            if "directEditable" in rule:
                direct_editable = bool(rule["directEditable"])
            item: dict[str, Any] = {
                "type": declared.get(column, "number"),
                "kind": kind,
                "bulkEditable": bulk_editable,
                "directEditable": direct_editable,
            }
            if protected:
                item["protectionReason"] = str(rule.get("reason") or "Identifier or structural field")
            if kind == "categorical":
                item["options"] = values
                item["editingModes"] = ["direct", "set"]
                item["guidance"] = "Category · choose an existing value"
            elif kind == "numeric":
                numeric_type = declared.get(column, "number")
                integer = numeric_type == "integer"
                fraction = any(pattern.search(column) for pattern in fraction_patterns)
                minimum = rule.get("minimum", defaults.get("numericMinimum", 0))
                maximum = rule.get("maximum", 1 if fraction else None)
                source_precision = max((self._decimal_places(value) for value in nonblank), default=0)
                precision = int(rule.get("precision", max(source_precision, int(defaults.get("fractionPrecision", 6))) if fraction else source_precision))
                item.update({
                    "minimum": minimum,
                    "maximum": maximum,
                    "integer": integer,
                    "precision": precision,
                    "editingModes": ["direct"] + ([] if not bulk_editable else ["set", "add", "subtract", "multiply", "percent", "decrease_percent"]),
                })
                if group_by_column.get(column):
                    group = dict(group_by_column[column])
                    group["tolerance"] = float(group.get("tolerance", defaults.get("groupTolerance", 0.000001)))
                    item["group"] = group
                    item["editingModes"] = ["direct", "group_set"]
                    item["guidance"] = "Linked shares · edit together"
                elif maximum == 1 and minimum == 0:
                    item["guidance"] = "Proportion · valid range 0–1"
                elif integer:
                    item["guidance"] = "Whole-number count · minimum 0"
                elif minimum is not None or maximum is not None:
                    limits = []
                    if minimum is not None:
                        limits.append(f"minimum {minimum}")
                    if maximum is not None:
                        limits.append(f"maximum {maximum}")
                    item["guidance"] = "Number · " + ", ".join(limits)
                if rule.get("reason"):
                    item["reason"] = str(rule["reason"])
            else:
                item["guidance"] = "Read-only text field"
            output[column] = item
        return output

    @staticmethod
    def _is_number(value: Any) -> bool:
        try:
            float(str(value).strip())
        except (TypeError, ValueError):
            return False
        return True

    @staticmethod
    def _decimal_places(value: Any) -> int:
        text = str(value).strip().lower()
        if "e" in text:
            try:
                return max(0, -int(text.split("e", 1)[1]))
            except ValueError:
                return 0
        return len(text.rsplit(".", 1)[1]) if "." in text else 0

    def validation_groups(self, filename: str) -> list[dict[str, Any]]:
        defaults = self.validation_rules.get("defaults", {})
        groups = self.validation_rules.get("files", {}).get(Path(filename).name.lower(), {}).get("groups", [])
        return [{**group, "tolerance": float(group.get("tolerance", defaults.get("groupTolerance", 0.000001)))} for group in groups]

    @staticmethod
    def validate_categorical_operations(
        metadata: dict[str, dict[str, Any]], operations: list[dict[str, Any]] | None,
    ) -> None:
        for operation in operations or []:
            if not isinstance(operation, dict) or operation.get("valueType") not in {"categorical", "share_group"}:
                continue
            if operation.get("valueType") == "share_group":
                columns = [str(item) for item in operation.get("columns", [])]
                groups = [metadata.get(column, {}).get("group") for column in columns]
                group = groups[0] if groups else None
                values = operation.get("groupValues") or operation.get("value")
                if operation.get("operation") != "set" or not group or any(item != group for item in groups) or set(columns) != set(group.get("members", [])) or not isinstance(values, dict) or not set(columns).issubset(values):
                    raise WorkspaceError("Linked shares must be saved as one complete Set to operation.")
                continue
            if operation.get("operation") != "set":
                raise WorkspaceError("Categorical fields support only Set to.")
            columns = [str(item) for item in operation.get("columns", [])]
            if len(columns) != 1:
                raise WorkspaceError("Choose one categorical column per change.")
            details = metadata.get(columns[0], {})
            allowed = [str(item) for item in details.get("options", [])]
            if details.get("kind") != "categorical" or str(operation.get("value", "")) not in allowed:
                raise WorkspaceError(f"Choose an existing value for {columns[0]}.")

    def validate_input_rows(
        self, filename: str, columns: list[str], rows: list[list[Any]],
        current_rows: list[list[Any]] | None = None, metadata: dict[str, dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Validate changed cells while grandfathering unchanged legacy values."""
        metadata = metadata or self.input_column_metadata(filename, columns, current_rows or rows, current_rows)
        # When a caller supplies current_rows we validate only newly changed
        # values, preserving legacy source values that predate this catalog.
        # Callers without a comparison set are asking for full validation.
        compare_supplied = current_rows is not None
        prior = current_rows if compare_supplied else [[] for _ in rows]
        errors: list[dict[str, Any]] = []

        def changed(row_index: int, column_index: int) -> bool:
            return str(rows[row_index][column_index] if column_index < len(rows[row_index]) else "") != str(prior[row_index][column_index] if row_index < len(prior) and column_index < len(prior[row_index]) else "")

        for row_index, row in enumerate(rows):
            identity = self._row_identity(columns, row, row_index)
            for column_index, column in enumerate(columns):
                if not changed(row_index, column_index):
                    continue
                details = metadata.get(column, {})
                value = str(row[column_index] if column_index < len(row) else "").strip()
                kind = details.get("kind")
                if kind in {"protected", "text"} or not details.get("directEditable", False):
                    if not compare_supplied:
                        continue
                    errors.append(self._validation_error(filename, column, identity, value, details.get("protectionReason") or details.get("guidance") or "This field is read-only."))
                    continue
                if kind == "categorical":
                    if value not in [str(item) for item in details.get("options", [])]:
                        errors.append(self._validation_error(filename, column, identity, value, "Choose one of the recognized category values."))
                    continue
                if not value or value.upper() == "NA":
                    errors.append(self._validation_error(filename, column, identity, value, "A changed numeric value cannot be blank or NA."))
                    continue
                try:
                    numeric = float(value)
                except ValueError:
                    errors.append(self._validation_error(filename, column, identity, value, "Enter a finite numeric value."))
                    continue
                if not math.isfinite(numeric):
                    errors.append(self._validation_error(filename, column, identity, value, "Enter a finite numeric value."))
                elif details.get("integer") and not numeric.is_integer():
                    errors.append(self._validation_error(filename, column, identity, value, "Enter a nonnegative whole number."))
                elif details.get("minimum") is not None and numeric < float(details["minimum"]):
                    errors.append(self._validation_error(filename, column, identity, value, f"The minimum is {details['minimum']}."))
                elif details.get("maximum") is not None and numeric > float(details["maximum"]):
                    errors.append(self._validation_error(filename, column, identity, value, f"The maximum is {details['maximum']}."))

        for group in self.validation_groups(filename):
            indexes = [columns.index(member) for member in group.get("members", []) if member in columns]
            if len(indexes) != len(group.get("members", [])):
                continue
            for row_index, row in enumerate(rows):
                if not any(changed(row_index, index) for index in indexes):
                    continue
                identity = self._row_identity(columns, row, row_index)
                raw = [str(row[index] if index < len(row) else "").strip() for index in indexes]
                blank = [not value or value.upper() == "NA" for value in raw]
                if all(blank) and group.get("optional"):
                    continue
                if any(blank):
                    errors.append(self._validation_error(filename, ", ".join(group["members"]), identity, "", "Linked shares must either all contain values or, for an optional group, all remain blank."))
                    continue
                try:
                    total = sum(float(value) for value in raw)
                except ValueError:
                    continue
                target = float(group.get("target", 1))
                tolerance = float(group.get("tolerance", 0.000001))
                invalid = group.get("rule") == "sum_equals" and abs(total - target) > tolerance
                invalid = invalid or group.get("rule") == "sum_at_most" and total - target > tolerance
                if invalid:
                    relation = "equal" if group.get("rule") == "sum_equals" else "be at most"
                    errors.append(self._validation_error(filename, ", ".join(group["members"]), identity, f"{total:.9g}", f"Linked shares must {relation} {target:g}; the current total is {total:.9g}."))
        if errors:
            first = errors[0]
            raise InputValidationError(f"{first['file']} · {first['field']} · {first['row']}: {first['message']} Attempted value: {first['value'] or 'blank'}.", errors)
        return errors

    @staticmethod
    def _row_identity(columns: list[str], row: list[Any], row_index: int) -> str:
        pieces = []
        for name in ("Geo", "Year", "Level"):
            if name in columns:
                value = str(row[columns.index(name)] if columns.index(name) < len(row) else "").strip()
                if value:
                    pieces.append(f"{name} {value}")
        return " · ".join(pieces) or f"row {row_index + 2}"

    @staticmethod
    def _validation_error(filename: str, field: str, row: str, value: str, message: str) -> dict[str, Any]:
        return {"file": filename, "field": field, "row": row, "value": value, "message": message}

    def conflict_for(self, filename: str, field: str) -> dict[str, Any] | None:
        base = field.split(".", 1)[0].lower()
        for item in self.conflicts:
            if item.get("scope") != "input" or item.get("file", "").lower() != filename.lower():
                continue
            names = [part.strip().split(".", 1)[0].lower() for part in str(item.get("field", "")).split(" / ")]
            if base in names:
                return item
        return None

    @staticmethod
    def display_unit(field: str, unit: str) -> str:
        if field.lower() in IDENTIFIER_FIELDS:
            return ""
        parts = field.split(".")
        currency_year = next((part for part in parts[1:] if part.isdigit() and len(part) == 4), "")
        magnitude = next((part for part in parts[1:] if part.lower().startswith("1e")), "")
        label = str(unit or "").strip()
        if currency_year and ("usd" in label.lower() or not label):
            label = f"{currency_year} USD"
        if magnitude:
            label = f"{label} × {magnitude}".strip()
        return "" if label.upper() in {"NA", "ID", "NONE"} else label

    def unit_details(self, field: str, item: dict[str, Any], template_id: str = "") -> dict[str, str]:
        if field.lower() in IDENTIFIER_FIELDS:
            return {"unit": "", "source": "Identifier", "warning": ""}
        definitions: dict[str, str] = {}
        if template_id:
            try:
                template_path, _ = self.workspace.template(template_id)
                with (template_path / "defs" / "units.csv").open("r", encoding="utf-8-sig", newline="") as handle:
                    definitions = {str(row.get("Type", "")).strip().lower(): str(row.get("Units", "")).strip() for row in csv.DictReader(handle)}
            except (WorkspaceError, OSError, csv.Error):
                definitions = {}
        module_unit = str(item.get("units") or item.get("unitLabel") or "").strip()
        defined = definitions.get(str(item.get("type", "")).strip().lower(), "")
        effective = defined or module_unit
        source = "Model defs/units.csv" if defined else (item.get("module") or ("VisionEval module metadata" if item else ""))
        parts = field.split(".")[1:]
        currency_year = next((part for part in parts if part.isdigit() and len(part) == 4), "")
        magnitude = next((part for part in parts if part.lower().startswith("1e")), "")
        if currency_year:
            effective = f"{currency_year} {effective or 'USD'}"
            source = f"CSV header + {source}"
        if magnitude:
            effective = f"{effective} × {magnitude}".strip()
            if not source.startswith("CSV header"):
                source = f"CSV header + {source}"
        warning = ""
        if defined and module_unit and defined.lower() != module_unit.lower() and module_unit.upper() not in {"NA", "NONE"}:
            warning = f"This model defines {defined}, while the executing module declares {module_unit}."
        return {"unit": self.display_unit(field, effective), "source": source, "warning": warning}

    @staticmethod
    def table_for(filename: str) -> str:
        prefix = Path(filename).stem.lower().split("_", 1)[0]
        return {"azone": "Azone", "bzone": "Bzone", "czone": "Czone", "marea": "Marea", "region": "Region"}.get(prefix, "")

    def library(self, library_id: str) -> Path:
        if not library_id or Path(library_id).name != library_id:
            raise WorkspaceError("Unknown Input Library")
        path = self.workspace.within(self.workspace.input_library / library_id, self.workspace.input_library)
        if not path.is_dir():
            raise WorkspaceError("Unknown Input Library")
        return path

    def metadata_for(self, column: str, table: str, catalog: dict[str, Any] | None = None) -> dict[str, Any]:
        catalog = catalog or self.catalog
        entries = catalog.get("variables", {}).get(column.lower(), [])
        return next((item for item in entries if item.get("table") == table), None) or (entries[0] if entries else {})

    def input_metadata_for(self, filename: str, column: str, table: str, catalog: dict[str, Any] | None = None) -> dict[str, Any]:
        catalog = catalog or self.catalog
        key = column.split(".", 1)[0].lower()
        authoritative = catalog.get("inputFields", {}).get(filename.lower(), {}).get(key)
        specification = self.spec_inputs.get((filename.lower(), key), {})
        fallback = self.metadata_for(column, table, catalog)
        return {**fallback, **{name: value for name, value in (authoritative or {}).items() if value not in {"", None}}, **{name: value for name, value in specification.items() if value not in {"", None}}}

    def columns(self, path: Path) -> list[str]:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return next(csv.reader(handle), [])

    def summary(self, filename: str, columns: list[str], catalog: dict[str, Any] | None = None) -> str:
        catalog = catalog or self.catalog
        table = self.table_for(filename)
        descriptions = []
        for column in columns:
            description = str(self.metadata_for(column, table, catalog).get("description") or "").strip()
            if description and description not in descriptions:
                descriptions.append(description)
            if len(descriptions) == 2:
                break
        return " ".join(descriptions) or "Input values used by the VisionEval model."

    def files(self, library_id: str = "", explanation_catalog_path: Path | None = None) -> dict[str, Any]:
        catalog = self.catalog_for(explanation_catalog_path)
        by_name: dict[str, dict[str, Any]] = {}
        catalog_names = {
            *(f"{key}.csv" for key in catalog.get("explanations", {})),
            *(Path(key).name for key in catalog.get("inputFields", {})),
            *(Path(key).name for key in self.spec_files),
        }
        for filename in sorted(catalog_names, key=str.lower):
            key = Path(filename).stem.lower()
            by_name[filename.lower()] = {
                "id": f"input:{filename}", "filename": filename,
                "level": self.table_for(filename) or "Other", "columns": [], "columnCount": 0,
                "description": "Built-in VisionEval input definition.",
                "hasExplanation": key in catalog.get("explanations", {}),
                "source": "catalog", "availability": "catalog_only",
                "installed": False, "columnsAvailable": False,
            }
        if library_id:
            root = self.library(library_id)
            for path in sorted(root.glob("*.csv"), key=lambda item: item.name.lower()):
                columns = self.columns(path)
                key = path.stem.lower()
                by_name[path.name.lower()] = {
                    "id": f"input:{path.name}", "filename": path.name, "level": self.table_for(path.name) or "Other",
                    "columns": columns, "columnCount": len(columns), "description": self.summary(path.name, columns, catalog),
                    "hasExplanation": key in catalog.get("explanations", {}),
                    "source": "installed", "availability": "installed",
                    "installed": True, "columnsAvailable": True,
                }
        files = sorted(by_name.values(), key=lambda item: str(item["filename"]).lower())
        return {"libraryId": library_id, "explanationPackage": catalog.get("package", {}), "files": files}

    def file(self, library_id: str, filename: str, template_id: str = "", explanation_catalog_path: Path | None = None) -> dict[str, Any]:
        catalog = self.catalog_for(explanation_catalog_path)
        safe_name = Path(filename).name
        if safe_name != filename or not safe_name.lower().endswith(".csv"):
            raise WorkspaceError("Invalid input filename")
        catalog_names = {
            *(f"{key}.csv" for key in catalog.get("explanations", {})),
            *(Path(key).name for key in catalog.get("inputFields", {})),
            *(Path(key).name for key in self.spec_files),
        }
        known_catalog = safe_name.lower() in {name.lower() for name in catalog_names}
        columns: list[str] = []
        installed = False
        if library_id:
            library_root = self.library(library_id)
            path = self.workspace.within(library_root / safe_name, self.workspace.input_library, must_exist=False)
            installed = path.is_file()
            if installed:
                columns = self.columns(path)
            elif not known_catalog:
                raise WorkspaceError("This input file is not available in the selected Input Library.")
        elif not known_catalog:
            raise WorkspaceError("Input definition was not found")
        table = self.table_for(safe_name)
        fields = []
        for name in columns:
            item = self.input_metadata_for(safe_name, name, table, catalog)
            conflict = self.conflict_for(safe_name, name)
            identifier = name.lower() in IDENTIFIER_FIELDS
            unit_details = self.unit_details(name, item, template_id)
            unit = unit_details["unit"]
            source = unit_details["source"]
            specification_warnings = list(item.get("warnings", []))
            conflict_warning = conflict.get("reason", "") if conflict and conflict.get("status") != "approved" else ""
            warnings = [warning for warning in [*specification_warnings, unit_details["warning"], conflict_warning] if warning]
            description = item.get("description") or "Description not available in the packaged guide."
            source_available = bool(source)
            fields.append({
                "name": name, "display": (f"{name} ({unit})" if item.get("authoritative") and unit else item.get("display") or name), "type": item.get("type") or "",
                "units": unit, "description": description, "descriptionAvailable": bool(item.get("description")),
                "source": source or "Not recorded", "sourceAvailable": source_available, "identifier": identifier,
                "unitStatus": conflict.get("status", "verified" if item else "unknown") if conflict else ("identifier" if identifier else "verified" if item else "unknown"),
                "unitWarning": " ".join(warnings),
            })
        explanation = catalog.get("explanations", {}).get(Path(safe_name).stem.lower(), {})
        return {
            "id": f"input:{safe_name}", "libraryId": library_id, "filename": safe_name, "level": table or "Other",
            "description": self.summary(safe_name, columns, catalog), "fields": fields,
            "source": "installed" if installed else "catalog",
            "availability": "installed" if installed else "catalog_only",
            "installed": installed, "columnsAvailable": installed,
            "explanationHtml": _strip_explanation_header(explanation.get("html", "")), "explanationDocument": explanation.get("document", ""),
            "templateId": template_id,
            "mapping": {"status": "available", "inputId": f"input:{safe_name}", "dependencyNodeId": f"file:{safe_name}"},
        }
