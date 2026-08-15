from __future__ import annotations

import hashlib
import csv
import json
import math
import os
import re
import shutil
import tempfile
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


PROJECT_VERSION = 1
RUN_VERSION = 1
WORKSPACE_FORMAT_VERSION = 2
WORKSPACE_MARKER = ".visioneval-workspace.json"
WORKSPACE_SETTINGS = ".workbench/settings.json"
ARCHIVE_DAYS = 30
SAFE_ID = re.compile(r"[^a-z0-9_-]+")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_id(prefix: str, label: str = "") -> str:
    slug = SAFE_ID.sub("-", label.strip().lower()).strip("-")[:36]
    token = uuid.uuid4().hex[:10]
    return f"{prefix}-{slug}-{token}" if slug else f"{prefix}-{token}"


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        # Windows readers do not always open files with delete sharing enabled.
        # Briefly retry the atomic replacement when a status poll overlaps a write.
        for attempt in range(20):
            try:
                os.replace(temporary, path)
                break
            except PermissionError:
                if attempt == 19:
                    raise
                time.sleep(0.01 * (attempt + 1))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def fingerprint_tree(root: Path, relative_paths: list[str] | None = None) -> str:
    digest = hashlib.sha256()
    paths = [root / item for item in relative_paths] if relative_paths else sorted(p for p in root.rglob("*") if p.is_file())
    for path in paths:
        if not path.is_file():
            continue
        digest.update(str(path.relative_to(root)).encode())
        with path.open("rb") as handle:
            while block := handle.read(1024 * 1024):
                digest.update(block)
    return digest.hexdigest()


def fingerprint_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


class WorkspaceError(ValueError):
    pass


class Workspace:
    directory_names = (
        "Assets/InputLibraries",
        "Assets/ModelTemplates",
        "Assets/InputExplanations",
        "Assets/RegionalData",
        "Projects",
        "Results/Models",
        "Documentation/User Notes",
        ".workbench/runs",
        ".workbench/exchange/inbox",
        ".workbench/exchange/outbox",
        ".workbench/exchange/system",
        ".workbench/archive/assets",
        ".workbench/archive/projects",
        ".workbench/map-contexts",
        ".workbench/legacy",
    )

    def __init__(self, root: str | Path):
        requested_root = Path(root).expanduser().absolute()
        self.root = requested_root.resolve()
        self.root_aliases = {requested_root, self.root}
        self.root.mkdir(parents=True, exist_ok=True)
        self.internal = self.root / ".workbench"
        self.internal.mkdir(parents=True, exist_ok=True)
        self._migrate_managed_layout()
        self.marker_path = self.root / WORKSPACE_MARKER
        self.created = not self.marker_path.exists()
        if not self.marker_path.exists():
            write_json(self.marker_path, {
                "formatVersion": WORKSPACE_FORMAT_VERSION,
                "id": make_id("workspace"),
                "createdAt": now_iso(),
            })
        else:
            marker = read_json(self.marker_path, {})
            if marker.get("formatVersion") != WORKSPACE_FORMAT_VERSION:
                marker["formatVersion"] = WORKSPACE_FORMAT_VERSION
                marker["migratedAt"] = now_iso()
                write_json(self.marker_path, marker)
        self.settings_path = self.root / WORKSPACE_SETTINGS
        if not self.settings_path.exists():
            write_json(self.settings_path, self.default_settings())
        for name in self.directory_names:
            (self.root / name).mkdir(parents=True, exist_ok=True)
        self.catalog_path = self.internal / "datastore_catalog.json"
        if not self.catalog_path.exists():
            write_json(self.catalog_path, {"version": 1, "datastores": []})
        self.migrate_removed_projects()
        self._normalize_managed_paths()
        self.purge_expired_assets()

    def _migrate_managed_layout(self) -> None:
        """Move the v1 workspace into the managed v2 layout using resumable renames."""
        def merge_move(source: Path, target: Path) -> None:
            if not target.exists():
                source.rename(target)
                return
            if source.is_dir() and target.is_dir():
                for child in list(source.iterdir()):
                    merge_move(child, target / child.name)
                source.rmdir()
                return
            if source.is_file() and target.is_file() and fingerprint_file(source) == fingerprint_file(target):
                source.unlink()
                return
            raise WorkspaceError(f"Workspace migration conflict: both {source} and {target} exist")

        journal_path = self.internal / "migration-v2.json"
        moves = [
            ("InputLibrary", "Assets/InputLibraries"),
            ("ModelTemplates", "Assets/ModelTemplates"),
            ("InputExplanations", "Assets/InputExplanations"),
            ("RegionPackages", "Assets/RegionalData"),
            ("models", "Results/Models"),
            ("runs", ".workbench/runs"),
            ("exchange", ".workbench/exchange"),
            ("workspace-settings.json", ".workbench/settings.json"),
            ("datastore_catalog.json", ".workbench/datastore_catalog.json"),
        ]
        legacy_names = (
            ".Rdata", ".Renviron", ".Rprofile", "VisionEval.Rproj", "launch_R4.5.1.bat",
            "r.version", "ve-build-config-default.yml", "visioneval.cnf.sample",
        )
        pending = [{"source": source, "target": target} for source, target in moves]
        pending.extend({"source": name, "target": f".workbench/legacy/{name}"} for name in legacy_names)
        write_json(journal_path, {"version": 2, "state": "running", "moves": pending, "updatedAt": now_iso()})
        for item in pending:
            source, target = self.root / item["source"], self.root / item["target"]
            if not source.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            merge_move(source, target)
        old_removed = self.root / "Projects" / ".Removed"
        archived_projects = self.internal / "archive" / "projects"
        if old_removed.exists() and not archived_projects.exists():
            archived_projects.parent.mkdir(parents=True, exist_ok=True)
            old_removed.rename(archived_projects)
        write_json(journal_path, {"version": 2, "state": "complete", "moves": pending, "updatedAt": now_iso()})
        readme = self.root / "README.txt"
        if not readme.exists():
            readme.write_text(
                "VisionEval Workbench manages this folder. Use the app to install, remove, or restore assets.\n"
                "Projects, Assets, Results, and Documentation contain user-facing data.\n"
                "Technical state and recoverable archives are stored in the hidden .workbench folder.\n",
                encoding="utf-8",
            )

    def _normalize_managed_paths(self) -> None:
        """Rewrite host paths persisted before the managed-layout migration."""
        replacements = {}
        for alias in self.root_aliases:
            replacements.update({
                str(alias / "InputLibrary"): str(self.input_library),
                str(alias / "ModelTemplates"): str(self.templates),
                str(alias / "InputExplanations"): str(self.input_explanations),
                str(alias / "RegionPackages"): str(self.region_packages),
                str(alias / "models"): str(self.models),
                str(alias / "runs"): str(self.runs),
                str(alias / "exchange"): str(self.exchange),
            })

        def replace(value: Any) -> Any:
            if isinstance(value, dict):
                return {key: replace(item) for key, item in value.items()}
            if isinstance(value, list):
                return [replace(item) for item in value]
            if isinstance(value, str):
                for old, new in replacements.items():
                    if value == old or value.startswith(old + os.sep):
                        return new + value[len(old):]
            return value

        candidates = list(self.internal.rglob("*.json"))
        candidates.append(self.catalog_path)
        candidates.extend(self.projects.glob("*/project.json"))
        candidates.extend(self.removed_projects.glob("*/project.json"))
        for path in dict.fromkeys(candidates):
            payload = read_json(path, None)
            if payload is None:
                continue
            normalized = replace(payload)
            if normalized != payload:
                write_json(path, normalized)

    @staticmethod
    def default_settings() -> dict[str, Any]:
        return {
            "version": 1,
            "defaultTemplateId": "",
            "defaultInputLibraryId": "",
            "defaultInputExplanationId": "",
            "retainFullExports": True,
            "checkVisionEvalUpdates": False,
            "numericPrecision": {
                "default": 2,
                "singleFile": None,
                "batch": None,
                "output": None,
                "percentage": None,
            },
            "assetRegistrations": [],
        }

    def settings(self) -> dict[str, Any]:
        current = read_json(self.settings_path, self.default_settings())
        defaults = self.default_settings()
        merged = {**defaults, **(current if isinstance(current, dict) else {})}
        stored_precision = merged.get("numericPrecision")
        merged["numericPrecision"] = {
            **defaults["numericPrecision"],
            **(stored_precision if isinstance(stored_precision, dict) else {}),
        }
        return merged

    def update_settings(self, payload: dict[str, Any]) -> dict[str, Any]:
        settings = self.settings()
        for key in ("defaultTemplateId", "defaultInputLibraryId", "defaultInputExplanationId", "retainFullExports", "checkVisionEvalUpdates"):
            if key in payload:
                settings[key] = payload[key]
        if "numericPrecision" in payload:
            incoming = payload["numericPrecision"]
            if not isinstance(incoming, dict):
                raise WorkspaceError("Numeric precision settings must be an object")
            precision = {**settings["numericPrecision"], **incoming}
            for key in ("default", "singleFile", "batch", "output", "percentage"):
                value = precision.get(key)
                if key != "default" and value is None:
                    continue
                if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 8:
                    raise WorkspaceError("Numeric precision must use whole numbers from 0 through 8")
            settings["numericPrecision"] = precision
        template_ids = {item["id"] for item in self.list_templates()}
        library_ids = {item["id"] for item in self.list_input_libraries()}
        if settings["defaultTemplateId"] and settings["defaultTemplateId"] not in template_ids:
            raise WorkspaceError("The default model template is not installed in this workspace")
        if settings["defaultInputLibraryId"] and settings["defaultInputLibraryId"] not in library_ids:
            raise WorkspaceError("The default InputLibrary is not installed in this workspace")
        explanation_ids = {item["id"] for item in self.list_input_explanations()}
        if settings["defaultInputExplanationId"] and settings["defaultInputExplanationId"] not in explanation_ids:
            raise WorkspaceError("The default input explanations package is not installed in this workspace")
        settings["retainFullExports"] = bool(settings["retainFullExports"])
        settings["checkVisionEvalUpdates"] = bool(settings["checkVisionEvalUpdates"])
        write_json(self.settings_path, settings)
        return settings

    def record_asset_registration(self, record: dict[str, Any]) -> dict[str, Any]:
        settings = self.settings()
        registrations = [
            item for item in settings.get("assetRegistrations", [])
            if isinstance(item, dict) and item.get("id") != record.get("id")
        ]
        registrations.append(record)
        settings["assetRegistrations"] = registrations
        write_json(self.settings_path, settings)
        return settings

    def storage_report(self) -> dict[str, Any]:
        def size(path: Path) -> int:
            total = 0
            if not path.exists():
                return total
            for item in path.rglob("*"):
                try:
                    if item.is_file():
                        total += item.stat().st_size
                except OSError:
                    continue
            return total

        model_runs = []
        for model in sorted((item for item in self.models.iterdir() if item.is_dir()), key=lambda item: item.name.lower()):
            datastore = size(model / "results" / "Datastore")
            exports = size(model / "results" / "output")
            model_runs.append({"id": model.name, "datastoreBytes": datastore, "exportBytes": exports, "totalBytes": size(model)})
        categories = {
            "InputLibrary": size(self.input_library), "ModelTemplates": size(self.templates),
            "Projects": size(self.projects), "models": size(self.models),
            "runs": size(self.runs), "exchange": size(self.exchange),
        }
        return {
            "workspaceBytes": sum(categories.values()),
            "categories": categories,
            "runs": model_runs,
            "retainFullExports": self.settings()["retainFullExports"],
            "planRvaEstimateBytes": 1_700_000_000,
        }

    def within(self, value: str | Path, parent: str | Path | None = None, must_exist: bool = True) -> Path:
        path = Path(value).expanduser().resolve()
        allowed = Path(parent).resolve() if parent else self.root
        try:
            path.relative_to(allowed)
        except ValueError as exc:
            raise WorkspaceError(f"Path is outside the allowed workspace: {path}") from exc
        if must_exist and not path.exists():
            raise WorkspaceError(f"Path does not exist: {path}")
        return path

    def external_directory(self, value: str | Path) -> Path:
        path = Path(value).expanduser().resolve()
        if not path.is_dir():
            raise WorkspaceError(f"Folder does not exist: {path}")
        return path

    @property
    def input_library(self) -> Path:
        return self.root / "Assets" / "InputLibraries"

    @property
    def input_explanations(self) -> Path:
        return self.root / "Assets" / "InputExplanations"

    @property
    def region_packages(self) -> Path:
        return self.root / "Assets" / "RegionalData"

    @property
    def templates(self) -> Path:
        return self.root / "Assets" / "ModelTemplates"

    @property
    def map_contexts(self) -> Path:
        return self.internal / "map-contexts"

    @property
    def projects(self) -> Path:
        return self.root / "Projects"

    @property
    def models(self) -> Path:
        return self.root / "Results" / "Models"

    @property
    def runs(self) -> Path:
        return self.internal / "runs"

    @property
    def exchange(self) -> Path:
        return self.internal / "exchange"

    def copy_input_library(self, source: str | Path) -> dict[str, Any]:
        source_path = self.external_directory(source)
        copied = []
        candidates = [source_path] if any(source_path.glob("*.csv")) else list(source_path.iterdir())
        for child in candidates:
            if not child.is_dir():
                continue
            target = self.input_library / child.name
            if target.exists():
                raise WorkspaceError(f"Input library already exists: {child.name}")
            shutil.copytree(child, target)
            copied.append(child.name)
        return {"source": str(source_path), "copied": copied}

    def list_input_libraries(self) -> list[dict[str, Any]]:
        output = []
        for path in sorted((p for p in self.input_library.iterdir() if p.is_dir()), key=lambda p: p.name.lower()):
            files = sorted(p.name for p in path.glob("*.csv"))
            output.append({"id": path.name, "name": path.name, "fileCount": len(files), "files": files})
        return output

    def list_input_explanations(self) -> list[dict[str, Any]]:
        records = []
        for path in sorted((p for p in self.input_explanations.iterdir() if p.is_dir()), key=lambda p: p.name.lower()):
            record = read_json(path / "workbench-package.json", {})
            if record:
                records.append(record)
        return records

    @staticmethod
    def validate_template(path: Path) -> dict[str, Any]:
        required = ["visioneval.cnf", "scripts/run_model.R", "defs", "inputs"]
        missing = [name for name in required if not (path / name).exists()]
        csv_files = sorted(p.name for p in (path / "inputs").glob("*.csv")) if (path / "inputs").is_dir() else []
        errors = ([f"Missing {name}" for name in missing] + ([] if csv_files else ["No input CSV files found"]))
        config = (path / "visioneval.cnf").read_text(encoding="utf-8", errors="replace") if (path / "visioneval.cnf").is_file() else ""
        for field in ("ScriptsDir", "InputDir", "ParamDir", "GeoFile", "ModelParamFile", "Years"):
            if not re.search(rf"(?m)^\s*{field}\s*:", config):
                errors.append(f"visioneval.cnf does not define {field}")
        for definition in ("geo.csv", "units.csv", "deflators.csv"):
            if not (path / "defs" / definition).is_file():
                errors.append(f"Missing defs/{definition}")
        return {
            "valid": not errors,
            "errors": errors,
            "inputFiles": csv_files,
            "fingerprint": fingerprint_tree(path, ["visioneval.cnf", "scripts/run_model.R", *[f"defs/{p.name}" for p in (path / "defs").glob("*") if p.is_file()]]) if not missing else "",
        }

    def import_template(self, source: str | Path, name: str = "") -> dict[str, Any]:
        source_path = self.external_directory(source)
        validation = self.validate_template(source_path)
        if not validation["valid"]:
            raise WorkspaceError("Invalid VisionEval model: " + "; ".join(validation["errors"]))
        template_id = make_id("template", name or source_path.name)
        target = self.templates / template_id
        shutil.copytree(source_path, target, ignore=shutil.ignore_patterns("results", ".DS_Store", ".comparison_csv_cache"))
        record = {
            "version": 1,
            "id": template_id,
            "name": name.strip() or source_path.name,
            "source": str(source_path),
            "importedAt": now_iso(),
            "fingerprint": validation["fingerprint"],
            "inputFiles": validation["inputFiles"],
        }
        write_json(target / "workbench_template.json", record)
        return record

    def list_templates(self) -> list[dict[str, Any]]:
        records = []
        for path in self.templates.iterdir():
            if path.is_dir():
                record = read_json(path / "workbench_template.json", {})
                if record:
                    records.append(record)
        return sorted(records, key=lambda item: item.get("name", "").lower())

    def _asset_root(self, kind: str) -> Path:
        roots = {
            "input-library": self.input_library,
            "model-template": self.templates,
            "input-explanations": self.input_explanations,
            "regional-data": self.region_packages,
        }
        if kind not in roots:
            raise WorkspaceError("Unknown asset type")
        return roots[kind]

    def _asset_record(self, kind: str, asset_id: str) -> dict[str, Any]:
        root = self._asset_root(kind)
        path = self.within(root / asset_id, root)
        if not path.is_dir() or path.name != asset_id:
            raise WorkspaceError("Unknown asset")
        manifest_name = {
            "model-template": "workbench_template.json",
            "input-explanations": "workbench-package.json",
            "regional-data": "workbench-package.json",
        }.get(kind, "region_builder_manifest.json")
        manifest = read_json(path / manifest_name, {})
        return {
            "kind": kind,
            "id": asset_id,
            "name": manifest.get("name") or manifest.get("regionName") or asset_id,
            "path": path,
            "manifest": manifest,
        }

    def _all_project_records(self) -> list[tuple[str, dict[str, Any]]]:
        return [("active", project) for project in self.list_projects()] + [("archived", project) for project in self.list_archived_projects()]

    def asset_dependencies(self, kind: str, asset_id: str) -> dict[str, Any]:
        asset = self._asset_record(kind, asset_id)
        projects = []
        for status, project in self._all_project_records():
            uses = (
                kind == "input-library" and project.get("inputLibrary", {}).get("id") == asset_id
            ) or (
                kind == "model-template" and project.get("template", {}).get("id") == asset_id
            )
            if uses:
                projects.append({"id": project.get("id", ""), "name": project.get("name", "Project"), "status": status})
        settings = self.settings()
        default_key = {
            "input-library": "defaultInputLibraryId",
            "model-template": "defaultTemplateId",
            "input-explanations": "defaultInputExplanationId",
        }.get(kind)
        related = []
        for registration in settings.get("assetRegistrations", []):
            assets = registration.get("assets", []) if isinstance(registration, dict) else []
            if not any(item.get("kind") == kind and item.get("id") == asset_id for item in assets if isinstance(item, dict)):
                continue
            for item in assets:
                if not isinstance(item, dict) or (item.get("kind") == kind and item.get("id") == asset_id):
                    continue
                try:
                    companion = self._asset_record(str(item.get("kind", "")), str(item.get("id", "")))
                except WorkspaceError:
                    continue
                related.append({"kind": companion["kind"], "id": companion["id"], "name": companion["name"]})
        region_manifest = read_json(asset["path"] / "region_builder_manifest.json", {})
        if region_manifest:
            region_name = region_manifest.get("regionName")
            package_id = region_manifest.get("regionPackage", {}).get("id")
            for candidate_kind, root in (("input-library", self.input_library), ("model-template", self.templates)):
                for candidate in root.iterdir():
                    if not candidate.is_dir() or (candidate_kind == kind and candidate.name == asset_id):
                        continue
                    candidate_manifest = read_json(candidate / "region_builder_manifest.json", {})
                    if candidate_manifest.get("regionName") == region_name and candidate_manifest.get("regionPackage", {}).get("id") == package_id:
                        relation = {"kind": candidate_kind, "id": candidate.name, "name": candidate_manifest.get("regionName") or candidate.name}
                        if relation not in related:
                            related.append(relation)
        return {
            "asset": {key: value for key, value in asset.items() if key not in {"path", "manifest"}},
            "projects": projects,
            "isDefault": bool(default_key and settings.get(default_key) == asset_id),
            "defaultKey": default_key or "",
            "related": related,
            "removable": not projects,
        }

    def asset_inventory(self) -> dict[str, Any]:
        installed = []
        for kind, root in (
            ("input-library", self.input_library), ("model-template", self.templates),
            ("input-explanations", self.input_explanations), ("regional-data", self.region_packages),
        ):
            for path in sorted((item for item in root.iterdir() if item.is_dir()), key=lambda item: item.name.lower()):
                installed.append(self.asset_dependencies(kind, path.name))
        return {"installed": installed, "archived": self.list_archived_assets()}

    @property
    def removed_assets(self) -> Path:
        return self.internal / "archive" / "assets"

    def archive_asset(self, kind: str, asset_id: str, include_related: bool = False) -> dict[str, Any]:
        requested = [(kind, asset_id)]
        dependencies = self.asset_dependencies(kind, asset_id)
        if include_related:
            requested.extend((item["kind"], item["id"]) for item in dependencies["related"])
        checks = [self.asset_dependencies(item_kind, item_id) for item_kind, item_id in requested]
        blocked = [project for check in checks for project in check["projects"]]
        if blocked:
            names = ", ".join(sorted({f'{item["name"]} ({item["status"]})' for item in blocked}))
            raise WorkspaceError(f"This asset is used by: {names}")
        archived_at = datetime.now(timezone.utc)
        purge_after = archived_at + timedelta(days=ARCHIVE_DAYS)
        operations = []
        for (item_kind, item_id), check in zip(requested, checks):
            record = self._asset_record(item_kind, item_id)
            archive_id = make_id("asset", f"{item_kind}-{item_id}")
            metadata = {
                "version": 1, "archiveId": archive_id, "kind": item_kind, "id": item_id,
                "name": record["name"], "archivedAt": archived_at.isoformat(),
                "purgeAfter": purge_after.isoformat(), "wasDefault": check["isDefault"],
            }
            operations.append({
                "source": record["path"], "target": self.removed_assets / archive_id,
                "metadata": metadata, "check": check,
            })
        self.removed_assets.mkdir(parents=True, exist_ok=True)
        moved = []
        try:
            for operation in operations:
                operation["source"].rename(operation["target"])
                moved.append(operation)
                write_json(operation["target"] / ".asset-archive.json", operation["metadata"])
        except Exception:
            for operation in reversed(moved):
                (operation["target"] / ".asset-archive.json").unlink(missing_ok=True)
                if operation["target"].exists() and not operation["source"].exists():
                    operation["target"].rename(operation["source"])
            raise
        settings = self.settings()
        for operation in operations:
            check = operation["check"]
            if check["defaultKey"] and check["isDefault"]:
                settings[check["defaultKey"]] = ""
        write_json(self.settings_path, settings)
        archived = [operation["metadata"] for operation in operations]
        return {"archived": archived}

    def list_archived_assets(self) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        output = []
        if not self.removed_assets.exists():
            return output
        for directory in self.removed_assets.iterdir():
            record = read_json(directory / ".asset-archive.json", {}) if directory.is_dir() else {}
            if not record:
                continue
            try:
                purge = datetime.fromisoformat(record["purgeAfter"])
                days = max(0, math.ceil((purge - now).total_seconds() / 86400))
            except (KeyError, TypeError, ValueError):
                days = ARCHIVE_DAYS
            output.append({**record, "daysRemaining": days})
        return sorted(output, key=lambda item: item.get("archivedAt", ""), reverse=True)

    def restore_asset(self, archive_id: str) -> dict[str, Any]:
        directory = self.within(self.removed_assets / archive_id, self.removed_assets)
        record = read_json(directory / ".asset-archive.json", {})
        if not record:
            raise WorkspaceError("Unknown archived asset")
        target = self._asset_root(record["kind"]) / record["id"]
        if target.exists():
            raise WorkspaceError("An installed asset already uses this ID")
        (directory / ".asset-archive.json").unlink(missing_ok=True)
        directory.rename(target)
        return {"restored": record}

    def purge_asset(self, archive_id: str) -> dict[str, Any]:
        directory = self.within(self.removed_assets / archive_id, self.removed_assets)
        record = read_json(directory / ".asset-archive.json", {})
        if not record:
            raise WorkspaceError("Unknown archived asset")
        shutil.rmtree(directory)
        return {"purged": archive_id}

    def purge_expired_assets(self) -> None:
        now = datetime.now(timezone.utc)
        for record in self.list_archived_assets():
            try:
                if datetime.fromisoformat(record["purgeAfter"]) <= now:
                    self.purge_asset(record["archiveId"])
            except (KeyError, TypeError, ValueError):
                continue

    def template(self, template_id: str) -> tuple[Path, dict[str, Any]]:
        path = self.within(self.templates / template_id, self.templates)
        record = read_json(path / "workbench_template.json", {})
        if not record or record.get("id") != template_id:
            raise WorkspaceError("Unknown model template")
        return path, record

    def create_project(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = str(payload.get("name", "")).strip()
        if not name:
            raise WorkspaceError("Project name is required")
        template_id = str(payload.get("templateId", ""))
        _, template = self.template(template_id)
        library_id = str(payload.get("inputLibraryId", ""))
        library = self.within(self.input_library / library_id, self.input_library)
        baseline = dict(payload.get("baseline") or {"strategy": "fresh"})
        baseline_name = str(baseline.get("displayName", "Baseline")).strip() or "Baseline"
        if baseline.get("strategy") not in {"fresh", "existing"}:
            raise WorkspaceError("Baseline strategy must be fresh or existing")
        if baseline.get("strategy") == "existing":
            datastore_id = str(baseline.get("datastoreId", ""))
            existing = next((item for item in self.catalog(False)["datastores"] if item.get("id") == datastore_id), None)
            if not existing:
                raise WorkspaceError("Choose a registered existing baseline")
            compatible = existing.get("templateFingerprint") == template.get("fingerprint")
            baseline = {
                "strategy": "existing",
                "datastoreId": datastore_id,
                "displayName": baseline_name,
                "compatibility": "verified" if compatible else "unverified",
                "warning": "" if compatible else "This baseline does not have matching model-template provenance.",
            }
        else:
            baseline["displayName"] = baseline_name
        variants = []
        names = set()
        for raw in payload.get("variations") or []:
            variant_name = str(raw.get("name", "")).strip()
            if not variant_name or variant_name.lower() in names:
                raise WorkspaceError("Variation names must be present and unique")
            names.add(variant_name.lower())
            variants.append({"id": make_id("variation", variant_name), "name": variant_name, "overlays": []})
        project_id = make_id("project", name)
        project = {
            "version": PROJECT_VERSION,
            "id": project_id,
            "name": name,
            "createdAt": now_iso(),
            "updatedAt": now_iso(),
            "template": {"id": template_id, "name": template["name"], "fingerprint": template["fingerprint"]},
            "inputLibrary": {"id": library_id, "path": str(library)},
            "baseline": baseline,
            "variations": variants,
            "runIds": [],
            "datastoreIds": [],
            "understandRefs": {"inputIds": [], "intermediaryIds": [], "outputIds": []},
        }
        directory = self.projects / project_id
        directory.mkdir()
        write_json(directory / "project.json", project)
        return project

    def list_projects(self) -> list[dict[str, Any]]:
        projects = [read_json(path, {}) for path in self.projects.glob("*/project.json")]
        return sorted((p for p in projects if p), key=lambda p: p.get("updatedAt", ""), reverse=True)

    @property
    def removed_projects(self) -> Path:
        return self.internal / "archive" / "projects"

    def active_project_ids(self) -> set[str]:
        return {item.get("id", "") for item in self.list_projects() if item.get("id")}

    def migrate_removed_projects(self) -> None:
        self.removed_projects.mkdir(exist_ok=True)
        legacy = self.projects / ".Removed"
        if legacy.is_dir():
            for directory in list(legacy.iterdir()):
                target = self.removed_projects / directory.name
                if target.exists():
                    raise WorkspaceError(f"Archived project migration conflict: {directory.name}")
                directory.rename(target)
            legacy.rmdir()
        for path in self.removed_projects.glob("*/project.json"):
            project = read_json(path, {})
            if not project or project.get("archivedAt"):
                continue
            archived = datetime.now(timezone.utc)
            project["archivedAt"] = archived.isoformat()
            project["purgeAfter"] = (archived + timedelta(days=ARCHIVE_DAYS)).isoformat()
            write_json(path, project)

    def list_archived_projects(self) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        output = []
        for path in self.removed_projects.glob("*/project.json"):
            project = read_json(path, {})
            if not project:
                continue
            try:
                purge = datetime.fromisoformat(project["purgeAfter"])
                days = max(0, math.ceil((purge - now).total_seconds() / 86400))
            except (KeyError, TypeError, ValueError):
                days = ARCHIVE_DAYS
            output.append({**project, "archiveDirectory": path.parent.name, "daysRemaining": days})
        return sorted(output, key=lambda item: item.get("archivedAt", ""), reverse=True)

    def project(self, project_id: str) -> tuple[Path, dict[str, Any]]:
        directory = self.within(self.projects / project_id, self.projects)
        project = read_json(directory / "project.json", {})
        if project.get("id") != project_id:
            raise WorkspaceError("Unknown project")
        return directory, project

    def save_project(self, project: dict[str, Any]) -> None:
        directory, _ = self.project(project["id"])
        project["updatedAt"] = now_iso()
        write_json(directory / "project.json", project)

    def update_project(self, project_id: str, name: str) -> dict[str, Any]:
        _, project = self.project(project_id)
        clean_name = str(name).strip()
        if not clean_name:
            raise WorkspaceError("Project name is required")
        project["name"] = clean_name
        self.save_project(project)
        return project

    def update_baseline_name(self, project_id: str, display_name: str) -> dict[str, Any]:
        _, project = self.project(project_id)
        clean_name = str(display_name).strip()
        if not clean_name:
            raise WorkspaceError("Baseline name is required")
        project.setdefault("baseline", {"strategy": "fresh"})["displayName"] = clean_name
        self.save_project(project)
        return project

    def remove_project(self, project_id: str) -> dict[str, Any]:
        directory, project = self.project(project_id)
        active_states = {"waiting", "preparing", "running", "exporting", "stopping"}
        for path in self.runs.glob("*/job.json"):
            job = read_json(path, {})
            if job.get("projectId") == project_id and job.get("state") in active_states:
                raise WorkspaceError("Stop or finish this project's active runs before archiving it")
        archived = datetime.now(timezone.utc)
        project["archivedAt"] = archived.isoformat()
        project["purgeAfter"] = (archived + timedelta(days=ARCHIVE_DAYS)).isoformat()
        write_json(directory / "project.json", project)
        target = self.removed_projects / make_id("removed", project.get("name", "project"))
        shutil.move(str(directory), str(target))
        return {"removed": project_id, "recoverable": True, "purgeAfter": project["purgeAfter"]}

    def _archived(self, project_id: str) -> tuple[Path, dict[str, Any]]:
        for path in self.removed_projects.glob("*/project.json"):
            project = read_json(path, {})
            if project.get("id") == project_id:
                return path.parent, project
        raise WorkspaceError("Unknown archived project")

    def restore_project(self, project_id: str) -> dict[str, Any]:
        directory, project = self._archived(project_id)
        target = self.projects / project_id
        if target.exists():
            raise WorkspaceError("An active project already uses this ID")
        project.pop("archivedAt", None)
        project.pop("purgeAfter", None)
        write_json(directory / "project.json", project)
        shutil.move(str(directory), str(target))
        return project

    def _active_datastore_references(self) -> dict[str, list[str]]:
        references: dict[str, list[str]] = {}
        for project in self.list_projects():
            datastore_id = (project.get("baseline") or {}).get("datastoreId")
            if datastore_id:
                references.setdefault(datastore_id, []).append(project.get("id", ""))
        return references

    def purge_project(self, project_id: str) -> dict[str, Any]:
        directory, project = self._archived(project_id)
        references = self._active_datastore_references()
        catalog = self.catalog()
        retained, removed_datastores, removed_paths = [], [], []
        kept_records = []
        for item in catalog.get("datastores", []):
            if item.get("projectId") != project_id:
                kept_records.append(item)
                continue
            datastore_id = item.get("id", "")
            if references.get(datastore_id):
                kept_records.append({**item, "sourceProjectArchived": True, "retainedForProjectIds": references[datastore_id]})
                retained.append(datastore_id)
                continue
            removed_datastores.append(datastore_id)
            if item.get("path"):
                removed_paths.append(item["path"])
        catalog["datastores"] = kept_records
        write_json(self.catalog_path, catalog)
        for path in list(self.runs.glob("*/job.json")):
            job = read_json(path, {})
            if job.get("projectId") != project_id:
                continue
            model_path = job.get("modelPath")
            if model_path:
                candidate = Path(model_path)
                try:
                    self.within(candidate, self.models)
                    if candidate.exists() and not any(str(candidate) in str(item.get("path", "")) for item in kept_records):
                        shutil.rmtree(candidate)
                except WorkspaceError:
                    pass
            shutil.rmtree(path.parent)
        for path in self.runs.glob("batch-*.json"):
            batch = read_json(path, {})
            if batch.get("projectId") == project_id or any(job.get("projectId") == project_id for job in batch.get("jobs", []) if isinstance(job, dict)):
                path.unlink(missing_ok=True)
        for value in removed_paths:
            try:
                candidate = self.within(value)
                if candidate.is_dir():
                    shutil.rmtree(candidate)
            except WorkspaceError:
                pass
        shutil.rmtree(directory)
        return {"purged": project_id, "retainedDatastoreIds": retained, "removedDatastoreIds": removed_datastores}

    def cleanup_archives(self) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        purged = []
        for item in list(self.list_archived_projects()):
            try:
                if datetime.fromisoformat(item["purgeAfter"]) <= now:
                    self.purge_project(item["id"])
                    purged.append(item["id"])
            except (KeyError, TypeError, ValueError):
                continue
        return {"purged": purged}

    def add_variation(self, project_id: str, name: str, duplicate_from: str = "") -> dict[str, Any]:
        directory, project = self.project(project_id)
        clean_name = name.strip()
        if not clean_name:
            raise WorkspaceError("Scenario name is required")
        if any(item.get("name", "").lower() == clean_name.lower() for item in project["variations"]):
            raise WorkspaceError("Scenario names must be unique")
        source = next((item for item in project["variations"] if item["id"] == duplicate_from), None) if duplicate_from else None
        variation = {"id": make_id("variation", clean_name), "name": clean_name, "overlays": [], "notes": dict(source.get("notes", {})) if source else {}, "scenarioNote": str(source.get("scenarioNote", "")) if source else ""}
        project["variations"].append(variation)
        self.save_project(project)
        if source:
            for overlay in source.get("overlays", []):
                source_path = self.within(overlay["path"], directory)
                self.save_overlay(project_id, variation["id"], overlay["fileName"], source_path.read_text(encoding="utf-8"))
            _, project = self.project(project_id)
            variation = next(item for item in project["variations"] if item["id"] == variation["id"])
        return variation

    def update_variation(self, project_id: str, variation_id: str, name: str | None = None, notes: dict[str, str] | None = None, scenario_note: str | None = None) -> dict[str, Any]:
        _, project = self.project(project_id)
        variation = next((item for item in project["variations"] if item["id"] == variation_id), None)
        if not variation:
            raise WorkspaceError("Unknown project variation")
        if name is not None:
            clean_name = name.strip()
            if not clean_name:
                raise WorkspaceError("Scenario name is required")
            if any(item["id"] != variation_id and item.get("name", "").lower() == clean_name.lower() for item in project["variations"]):
                raise WorkspaceError("Scenario names must be unique")
            variation["name"] = clean_name
        if notes is not None:
            variation["notes"] = {Path(key).name: str(value) for key, value in notes.items() if Path(key).name == key}
        if scenario_note is not None:
            variation["scenarioNote"] = str(scenario_note)
        self.save_project(project)
        return variation

    def delete_variation(self, project_id: str, variation_id: str) -> dict[str, Any]:
        directory, project = self.project(project_id)
        variation = next((item for item in project["variations"] if item["id"] == variation_id), None)
        if not variation:
            raise WorkspaceError("Unknown project variation")
        project["variations"] = [item for item in project["variations"] if item["id"] != variation_id]
        overlay_directory = directory / "overlays" / variation_id
        if overlay_directory.exists():
            shutil.rmtree(overlay_directory)
        self.save_project(project)
        return {"deleted": variation_id}

    def input_file(self, library_id: str, filename: str, project_id: str = "", variation_id: str = "") -> tuple[Path, bool]:
        safe_name = Path(filename).name
        if safe_name != filename:
            raise WorkspaceError("Invalid input filename")
        if project_id and variation_id:
            directory, project = self.project(project_id)
            variation = next((item for item in project["variations"] if item["id"] == variation_id), None)
            overlay = next((item for item in variation.get("overlays", []) if item["fileName"] == safe_name), None) if variation else None
            if overlay:
                return self.within(overlay["path"], directory), True
        path = self.within(self.input_library / library_id / safe_name, self.input_library)
        if not path.is_file():
            raise WorkspaceError("Input file was not found")
        return path, False

    def save_overlay(self, project_id: str, variation_id: str, filename: str, content: str) -> dict[str, Any]:
        directory, project = self.project(project_id)
        variant = next((v for v in project["variations"] if v["id"] == variation_id), None)
        if not variant:
            raise WorkspaceError("Unknown project variation")
        safe_name = Path(filename).name
        if safe_name != filename or not safe_name.lower().endswith(".csv"):
            raise WorkspaceError("Only CSV input files may be edited")
        library_file = self.within(self.input_library / project["inputLibrary"]["id"] / safe_name, self.input_library)
        if not library_file.is_file():
            raise WorkspaceError("Input file is not in the selected library")
        overlay = directory / "overlays" / variation_id / safe_name
        overlay.parent.mkdir(parents=True, exist_ok=True)
        overlay.write_text(content, encoding="utf-8")
        item = {"fileName": safe_name, "path": str(overlay), "updatedAt": now_iso()}
        variant["overlays"] = [entry for entry in variant.get("overlays", []) if entry["fileName"] != safe_name] + [item]
        self.save_project(project)
        return item

    def delete_overlay(self, project_id: str, variation_id: str, filename: str) -> dict[str, Any]:
        directory, project = self.project(project_id)
        variation = next((item for item in project["variations"] if item["id"] == variation_id), None)
        if not variation:
            raise WorkspaceError("Unknown project variation")
        safe_name = Path(filename).name
        overlay = next((item for item in variation.get("overlays", []) if item["fileName"] == safe_name), None)
        if not overlay:
            raise WorkspaceError("Unknown saved file edit")
        self.within(overlay["path"], directory).unlink(missing_ok=True)
        variation["overlays"] = [item for item in variation.get("overlays", []) if item["fileName"] != safe_name]
        variation.setdefault("notes", {}).pop(safe_name, None)
        self.save_project(project)
        return {"deleted": safe_name}

    @staticmethod
    def _csv_dicts(path: Path) -> tuple[list[str], list[dict[str, str]]]:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            return list(reader.fieldnames or []), [dict(row) for row in reader]

    @staticmethod
    def _file_geo_level(filename: str) -> str:
        lower = filename.lower()
        for level in ("Azone", "Bzone", "Czone", "Marea"):
            if lower.startswith(level.lower() + "_"):
                return level
        return ""

    def geography_options(self, project_id: str, filename: str = "") -> dict[str, Any]:
        _, project = self.project(project_id)
        template_path, _ = self.template(project["template"]["id"])
        geo_path = template_path / "defs" / "geo.csv"
        target_level = self._file_geo_level(filename) if filename else ""
        levels: list[dict[str, Any]] = [{"id": "all", "label": "All locations", "type": "all", "values": []}]
        if not geo_path.is_file():
            return {"targetField": "Geo", "targetLevel": target_level, "levels": levels, "mapped": False}
        fields, rows = self._csv_dicts(geo_path)
        geo_fields = [field for field in ("Azone", "Bzone", "Czone", "Marea") if field in fields]
        if not target_level and filename:
            library_file = self.input_library / project["inputLibrary"]["id"] / Path(filename).name
            if library_file.is_file():
                columns, input_rows = self._csv_dicts(library_file)
                if "Geo" in columns:
                    input_values = {str(row.get("Geo", "")).strip() for row in input_rows}
                    target_level = next((field for field in geo_fields if input_values and input_values <= {str(row.get(field, "")).strip() for row in rows}), "")

        def build_level(level_id: str, label: str, source_field: str) -> dict[str, Any] | None:
            values = sorted({str(row.get(source_field, "")).strip() for row in rows if str(row.get(source_field, "")).strip() not in {"", "NA"}}, key=str.lower)
            if not values:
                return None
            items = []
            for value in values:
                targets = sorted({str(row.get(target_level, "")).strip() for row in rows if str(row.get(source_field, "")).strip() == value and str(row.get(target_level, "")).strip() not in {"", "NA"}}) if target_level else []
                items.append({"value": value, "label": value, "targetValues": targets})
            return {"id": level_id, "label": label, "type": "geo", "sourceField": source_field, "values": items, "compatible": bool(target_level)}

        azone_values = {str(row.get("Azone", "")).strip() for row in rows if str(row.get("Azone", "")).strip() not in {"", "NA"}}
        looks_like_counties = bool(azone_values) and sum(value.lower().endswith((" county", " city")) for value in azone_values) >= max(1, len(azone_values) // 2)
        if looks_like_counties:
            county = build_level("county", "County", "Azone")
            if county:
                levels.append(county)
        for field in geo_fields:
            item = build_level(field.lower(), field, field)
            if item:
                levels.append(item)

        if filename:
            library_file = self.input_library / project["inputLibrary"]["id"] / Path(filename).name
            if library_file.is_file():
                columns, input_rows = self._csv_dicts(library_file)
                if "Geo" in columns and not target_level:
                    raw_values = sorted({str(row.get("Geo", "")).strip() for row in input_rows if str(row.get("Geo", "")).strip() not in {"", "NA"}}, key=str.lower)
                    if raw_values:
                        levels.append({"id": "geo", "label": "Geo", "type": "raw", "sourceField": "Geo", "compatible": True, "values": [{"value": value, "label": value, "targetValues": [value]} for value in raw_values]})
        return {"targetField": "Geo", "targetLevel": target_level, "levels": levels, "mapped": len(levels) > 1}

    def review_project(self, project_id: str, change_limit: int = 2000) -> dict[str, Any]:
        _, project = self.project(project_id)
        library = self.input_library / project["inputLibrary"]["id"]
        scenarios = []
        for variation in project.get("variations", []):
            scenario = {"id": variation["id"], "name": variation["name"], "scenarioNote": variation.get("scenarioNote", ""), "fileCount": 0, "changedRows": 0, "changedCells": 0, "files": []}
            remaining = change_limit
            for overlay in variation.get("overlays", []):
                filename = overlay["fileName"]
                original_path = library / filename
                edited_path = self.within(overlay["path"], self.projects / project_id)
                original_columns, original_rows = self._csv_dicts(original_path)
                edited_columns, edited_rows = self._csv_dicts(edited_path)
                changes, row_numbers, geographies, years = [], set(), set(), set()
                columns = edited_columns if edited_columns == original_columns else sorted(set(original_columns + edited_columns))
                row_count = max(len(original_rows), len(edited_rows))
                for row_index in range(row_count):
                    before_row = original_rows[row_index] if row_index < len(original_rows) else {}
                    after_row = edited_rows[row_index] if row_index < len(edited_rows) else {}
                    for column in columns:
                        before, after = str(before_row.get(column, "")), str(after_row.get(column, ""))
                        if before == after:
                            continue
                        row_numbers.add(row_index + 2)
                        geo = str(after_row.get("Geo", before_row.get("Geo", "")))
                        year = str(after_row.get("Year", before_row.get("Year", "")))
                        if geo: geographies.add(geo)
                        if year: years.add(year)
                        if remaining > 0:
                            changes.append({"row": row_index + 2, "column": column, "geo": geo, "year": year, "before": before, "after": after})
                            remaining -= 1
                file_record = {
                    "filename": filename,
                    "changedRows": len(row_numbers),
                    "changedCells": sum(1 for row_index in range(row_count) for column in columns if str((original_rows[row_index] if row_index < len(original_rows) else {}).get(column, "")) != str((edited_rows[row_index] if row_index < len(edited_rows) else {}).get(column, ""))),
                    "geographies": sorted(geographies, key=str.lower),
                    "years": sorted(years),
                    "notes": variation.get("notes", {}).get(filename, ""),
                    "changes": changes,
                }
                scenario["files"].append(file_record)
                scenario["changedRows"] += file_record["changedRows"]
                scenario["changedCells"] += file_record["changedCells"]
            scenario["fileCount"] = len(scenario["files"])
            scenarios.append(scenario)
        return {"projectId": project_id, "projectName": project["name"], "scenarios": scenarios, "truncated": any(sum(len(file["changes"]) for file in scenario["files"]) >= change_limit for scenario in scenarios)}

    def prepare_model(self, project_id: str, variation_id: str, run_id: str, baseline: bool = False) -> tuple[Path, dict[str, Any]]:
        project_dir, project = self.project(project_id)
        template_path, template = self.template(project["template"]["id"])
        if baseline:
            variation = {"id": "baseline", "name": "Baseline", "overlays": []}
        else:
            variation = next((v for v in project["variations"] if v["id"] == variation_id), None)
            if not variation:
                raise WorkspaceError("Unknown variation")
        target = self.models / run_id
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(
            template_path,
            target,
            ignore=shutil.ignore_patterns("results", "workbench_template.json", ".DS_Store", ".workbench-*"),
        )
        library = self.input_library / project["inputLibrary"]["id"]
        for source in library.iterdir():
            if source.is_file():
                shutil.copy2(source, target / "inputs" / source.name)
        for overlay in variation.get("overlays", []):
            source = self.within(overlay["path"], project_dir)
            shutil.copy2(source, target / "inputs" / overlay["fileName"])
        provenance = {
            "version": 1,
            "projectId": project_id,
            "projectName": project["name"],
            "variationId": variation["id"],
            "variationName": variation["name"],
            "scenarioNote": variation.get("scenarioNote", ""),
            "templateId": template["id"],
            "templateFingerprint": template["fingerprint"],
            "preparedAt": now_iso(),
        }
        write_json(target / "workbench_provenance.json", provenance)
        return target, provenance

    def catalog(self, include_archived: bool = True, include_hidden: bool = True) -> dict[str, Any]:
        catalog = read_json(self.catalog_path, {"version": 1, "datastores": []})
        datastores = list(catalog.get("datastores", []))
        if not include_archived:
            active = self.active_project_ids()
            retained = set(self._active_datastore_references())
            datastores = [
                item for item in datastores
                if not item.get("projectId") or item.get("projectId") in active or item.get("id") in retained
            ]
        if not include_hidden:
            datastores = [item for item in datastores if not item.get("hidden")]
        catalog["datastores"] = datastores
        return catalog

    def register_datastore(self, record: dict[str, Any]) -> dict[str, Any]:
        datastore = dict(record)
        datastore.setdefault("id", make_id("datastore", datastore.get("variationName", "result")))
        datastore.setdefault("registeredAt", now_iso())
        catalog = self.catalog()
        catalog["datastores"] = [item for item in catalog["datastores"] if item.get("id") != datastore["id"]] + [datastore]
        write_json(self.catalog_path, catalog)
        project_id = datastore.get("projectId")
        if project_id:
            try:
                _, project = self.project(project_id)
                if datastore["id"] not in project["datastoreIds"]:
                    project["datastoreIds"].append(datastore["id"])
                    self.save_project(project)
            except WorkspaceError:
                pass
        return datastore

    def unregister_run_datastores(self, run_id: str) -> list[str]:
        """Remove catalog entries created by a run that did not complete safely."""
        catalog = self.catalog()
        removed = [item for item in catalog.get("datastores", []) if item.get("runId") == run_id]
        if not removed:
            return []
        removed_ids = {item.get("id", "") for item in removed}
        catalog["datastores"] = [item for item in catalog.get("datastores", []) if item.get("runId") != run_id]
        write_json(self.catalog_path, catalog)
        for project in self.list_projects():
            before = list(project.get("datastoreIds", []))
            project["datastoreIds"] = [item for item in before if item not in removed_ids]
            if project["datastoreIds"] != before:
                self.save_project(project)
        return sorted(item for item in removed_ids if item)
