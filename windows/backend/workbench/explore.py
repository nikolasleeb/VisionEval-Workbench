from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

from .workspace import Workspace, WorkspaceError


IDENTIFIER_FIELDS = {"geo", "azone", "bzone", "czone", "marea", "region", "hhid", "vehid", "wkrid", "year"}
EXPLANATION_DATE_RE = re.compile(r"^(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}$", re.IGNORECASE)
EXPLANATION_TITLE_RE = re.compile(r"^(Optional\s+)?File\s+\d{1,3}[\s_.-].+|^\d{1,3}[_\s.-].+", re.IGNORECASE)
EXPLANATION_CHUNK_RE = re.compile(r"^<(p|h3)>(.*)</\1>$", re.DOTALL)


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

    def validate_input_rows(self, filename: str, columns: list[str], rows: list[list[Any]]) -> None:
        column_types = self.input_column_types(filename, columns)
        invalid: set[str] = set()
        for column, value_type in column_types.items():
            if value_type != "integer" or column not in columns:
                continue
            index = columns.index(column)
            for row in rows:
                value = str(row[index]).strip() if index < len(row) else ""
                if not value or value.upper() == "NA":
                    continue
                try:
                    numeric = float(value)
                except ValueError:
                    continue
                if not numeric.is_integer():
                    invalid.add(column)
                    break
        if invalid:
            names = ", ".join(sorted(invalid))
            raise WorkspaceError(
                f"VisionEval requires whole numbers in {names}. Change these count fields to integers before saving."
            )

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
            raise WorkspaceError("Unknown InputLibrary")
        path = self.workspace.within(self.workspace.input_library / library_id, self.workspace.input_library)
        if not path.is_dir():
            raise WorkspaceError("Unknown InputLibrary")
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
                "source": "catalog", "installed": False, "columnsAvailable": False,
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
                    "source": "installed", "installed": True, "columnsAvailable": True,
                }
        files = sorted(by_name.values(), key=lambda item: str(item["filename"]).lower())
        return {"libraryId": library_id, "explanationPackage": catalog.get("package", {}), "files": files}

    def file(self, library_id: str, filename: str, template_id: str = "", explanation_catalog_path: Path | None = None) -> dict[str, Any]:
        catalog = self.catalog_for(explanation_catalog_path)
        safe_name = Path(filename).name
        if safe_name != filename or not safe_name.lower().endswith(".csv"):
            raise WorkspaceError("Invalid input filename")
        columns: list[str] = []
        if library_id:
            path = self.workspace.within(self.library(library_id) / safe_name, self.workspace.input_library)
            if not path.is_file():
                raise WorkspaceError("Input file was not found")
            columns = self.columns(path)
        table = self.table_for(safe_name)
        catalog_names = {
            *(f"{key}.csv" for key in catalog.get("explanations", {})),
            *(Path(key).name for key in catalog.get("inputFields", {})),
            *(Path(key).name for key in self.spec_files),
        }
        if not library_id and safe_name.lower() not in {name.lower() for name in catalog_names}:
            raise WorkspaceError("Input definition was not found")
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
            "source": "installed" if library_id else "catalog", "installed": bool(library_id),
            "columnsAvailable": bool(library_id),
            "explanationHtml": _strip_explanation_header(explanation.get("html", "")), "explanationDocument": explanation.get("document", ""),
            "templateId": template_id,
            "mapping": {"status": "available", "inputId": f"input:{safe_name}", "dependencyNodeId": f"file:{safe_name}"},
        }
