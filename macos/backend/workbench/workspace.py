from __future__ import annotations

import hashlib
import copy
import csv
import json
import math
import os
import re
import shutil
import tempfile
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable


PROJECT_VERSION = 1
RUN_VERSION = 1
WORKSPACE_FORMAT_VERSION = 2
WORKSPACE_MARKER = ".visioneval-workspace.json"
WORKSPACE_SETTINGS = ".workbench/settings.json"
ARCHIVE_DAYS = 30
SAFE_ID = re.compile(r"[^a-z0-9_-]+")
ACTIVE_RUN_STATES = {"waiting", "preparing", "running", "exporting", "stopping"}
PROJECT_TYPES = {"standard", "hypercube"}
LEGACY_ASSET_DISPLAY_NAMES = {
    "PlanRVA MM": "PlanRVA",
    "PlanRVA MM Example": "PlanRVA",
    "WPPDC MM": "WPPDC",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_id(prefix: str, label: str = "") -> str:
    slug = SAFE_ID.sub("-", label.strip().lower()).strip("-")[:36]
    token = uuid.uuid4().hex[:10]
    return f"{prefix}-{slug}-{token}" if slug else f"{prefix}-{token}"


def normalized_name(value: str) -> str:
    """Normalize a user-facing name for workspace-wide uniqueness checks."""
    return " ".join(str(value).split()).casefold()


def asset_display_name(value: Any) -> str:
    """Return the current label for a stable legacy asset identity."""
    text = str(value or "")
    return LEGACY_ASSET_DISPLAY_NAMES.get(text, text)


def is_workspace_data(path: Path) -> bool:
    """Exclude macOS housekeeping sidecars without hiding real dotfiles."""
    return not any(part.startswith("._") or part == ".DS_Store" for part in path.parts)


def read_json(path: Path, default: Any = None) -> Any:
    # AppleDouble sidecars on external drives are binary metadata, not JSON.
    if not is_workspace_data(path):
        return default
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
        if not path.is_file() or not is_workspace_data(path):
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


def directory_size(path: Path) -> int:
    """Return the size of regular files below path without following symlinks."""
    if path.is_file():
        return path.stat().st_size
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file() and not item.is_symlink())


class WorkspaceError(ValueError):
    pass


class CopyCancelled(Exception):
    def __init__(self) -> None:
        super().__init__("Copy cancelled")


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
        self.activity_lock = threading.RLock()
        self.copy_reservations: dict[str, dict[str, Any]] = {}
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
        self.migrate_hypercube_metadata()
        self._normalize_managed_paths()
        self.purge_expired_assets()

    def _migrate_managed_layout(self) -> None:
        """Move the v1 workspace into the managed v2 layout using resumable renames."""
        journal_path = self.internal / "migration-v2.json"
        marker = read_json(self.root / WORKSPACE_MARKER, {})
        if marker.get("formatVersion") == WORKSPACE_FORMAT_VERSION:
            # A v2 workspace may legitimately regenerate R support files at
            # its root after migration. Never interpret those files as stale
            # v1 content on later launches. Older builds rewrote the journal
            # to "running" before discovering such a conflict, so repair that
            # journal state without moving or deleting any current files.
            journal = read_json(journal_path, {})
            if journal.get("state") != "complete":
                write_json(journal_path, {
                    **journal,
                    "version": 2,
                    "state": "complete",
                    "recoveredAt": now_iso(),
                    "updatedAt": now_iso(),
                })
            return

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

        candidates = [path for path in self.internal.rglob("*.json") if not path.name.startswith("._")]
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
            "updateChecks": {
                "automatic": False,
                "sources": {
                    "visioneval": True,
                    "runtimeImage": True,
                    "workbench": True,
                },
                "lastCheckedAt": "",
                "statuses": {},
            },
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
        stored_updates = (current if isinstance(current, dict) else {}).get("updateChecks")
        if not isinstance(stored_updates, dict):
            stored_updates = {}
        # Older workspaces used one hidden VisionEval-only preference. Read it
        # once for compatibility, but expose and persist only the new shape.
        legacy_enabled = bool((current if isinstance(current, dict) else {}).get("checkVisionEvalUpdates", False))
        stored_sources = stored_updates.get("sources")
        merged["updateChecks"] = {
            **defaults["updateChecks"],
            **stored_updates,
            "automatic": bool(stored_updates.get("automatic", legacy_enabled)),
            "sources": {
                **defaults["updateChecks"]["sources"],
                **(stored_sources if isinstance(stored_sources, dict) else {}),
            },
            "statuses": stored_updates.get("statuses") if isinstance(stored_updates.get("statuses"), dict) else {},
        }
        merged.pop("checkVisionEvalUpdates", None)
        return merged

    def update_settings(self, payload: dict[str, Any]) -> dict[str, Any]:
        settings = self.settings()
        for key in ("defaultTemplateId", "defaultInputLibraryId", "defaultInputExplanationId", "retainFullExports"):
            if key in payload:
                settings[key] = payload[key]
        if "updateChecks" in payload:
            incoming_updates = payload["updateChecks"]
            if not isinstance(incoming_updates, dict):
                raise WorkspaceError("Update check settings must be an object")
            sources = incoming_updates.get("sources", settings["updateChecks"]["sources"])
            if not isinstance(sources, dict):
                raise WorkspaceError("Update check sources must be an object")
            allowed_sources = {"visioneval", "runtimeImage", "workbench"}
            if set(sources) - allowed_sources:
                raise WorkspaceError("Unknown update check source")
            settings["updateChecks"] = {
                **settings["updateChecks"],
                "automatic": bool(incoming_updates.get("automatic", settings["updateChecks"]["automatic"])),
                "sources": {
                    key: bool(sources.get(key, settings["updateChecks"]["sources"].get(key, True)))
                    for key in sorted(allowed_sources)
                },
            }
        elif "checkVisionEvalUpdates" in payload:
            # Backward-compatible API input. It is normalized into the new
            # settings object and the legacy key is never written again.
            settings["updateChecks"] = {
                **settings["updateChecks"],
                "automatic": bool(payload["checkVisionEvalUpdates"]),
            }
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
        if "defaultInputLibraryId" in payload and settings["defaultInputLibraryId"]:
            pairing = self.input_library_pairing(str(settings["defaultInputLibraryId"]))
            if pairing["status"] != "paired":
                raise WorkspaceError(pairing["error"] or "The default Input Library has no verified model package")
            requested_template = str(payload.get("defaultTemplateId", ""))
            if requested_template and requested_template != pairing["templateId"]:
                raise WorkspaceError("The selected model package is not paired with the default Input Library")
            settings["defaultTemplateId"] = pairing["templateId"]
        elif "defaultInputLibraryId" in payload and not settings["defaultInputLibraryId"]:
            settings["defaultTemplateId"] = ""
        if settings["defaultTemplateId"] and settings["defaultTemplateId"] not in template_ids:
            raise WorkspaceError("The default model package is not installed in this workspace")
        if settings["defaultInputLibraryId"] and settings["defaultInputLibraryId"] not in library_ids:
            raise WorkspaceError("The default Input Library is not installed in this workspace")
        explanation_ids = {item["id"] for item in self.list_input_explanations()}
        if settings["defaultInputExplanationId"] and settings["defaultInputExplanationId"] not in explanation_ids:
            raise WorkspaceError("The default input explanations package is not installed in this workspace")
        settings["retainFullExports"] = bool(settings["retainFullExports"])
        settings.pop("checkVisionEvalUpdates", None)
        write_json(self.settings_path, settings)
        return settings

    def update_check_cache(self, *, checked_at: str, statuses: dict[str, Any]) -> dict[str, Any]:
        """Persist advisory update results without changing user selections."""
        settings = self.settings()
        update_checks = dict(settings["updateChecks"])
        update_checks["lastCheckedAt"] = str(checked_at or "")
        update_checks["statuses"] = statuses if isinstance(statuses, dict) else {}
        settings["updateChecks"] = update_checks
        settings.pop("checkVisionEvalUpdates", None)
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
            "defaultResultEstimateBytes": 1_700_000_000,
            "planRvaEstimateBytes": 1_700_000_000,
        }

    def active_run_records(self) -> list[dict[str, Any]]:
        records = []
        for path in self.runs.glob("*/job.json"):
            record = read_json(path, {})
            if record.get("state") in ACTIVE_RUN_STATES:
                records.append(record)
        return records

    def assert_variations_copyable(
        self, project_id: str, variation_ids: list[str], reservation_id: str = "",
    ) -> None:
        """Reject scenario copies whose source inputs may still be in use by a run."""
        with self.activity_lock:
            _, project = self.project(project_id)
            requested = [str(item) for item in variation_ids if item]
            available = {str(item.get("id", "")): item for item in project.get("variations", [])}
            if not requested or len(requested) != len(set(requested)):
                raise WorkspaceError("Choose one or more unique scenarios to copy")
            if any(item not in available for item in requested):
                raise WorkspaceError("A selected source scenario no longer exists")

            requested_ids = set(requested)
            active = [
                item for item in self.active_run_records()
                if item.get("projectId") == project_id and str(item.get("variationId", "")) in requested_ids
            ]
            by_variation: dict[str, set[str]] = {}
            for item in active:
                by_variation.setdefault(str(item.get("variationId", "")), set()).add(str(item.get("state", "active")))
            descriptions = []
            for variation_id in requested:
                states = by_variation.get(variation_id)
                if states:
                    name = str(available[variation_id].get("name") or variation_id)
                    descriptions.append(f"{name} ({', '.join(sorted(states))})")
            if descriptions:
                raise WorkspaceError(
                    "Wait for or stop active scenario runs before copying: " + ", ".join(descriptions)
                )
            for token, reservation in self.copy_reservations.items():
                if token == reservation_id:
                    continue
                if reservation.get("sourceProjectId") == project_id and requested_ids.intersection(reservation.get("variationIds", set())):
                    raise WorkspaceError("A selected scenario is already being copied. Wait for that copy to finish.")

    def assert_copy_destination_idle(self, project_id: str, reservation_id: str = "") -> None:
        if not project_id:
            return
        with self.activity_lock:
            _, project = self.project(project_id)
            self.require_standard_project(project)
            active = [item for item in self.active_run_records() if item.get("projectId") == project_id]
            if active:
                states = ", ".join(sorted({str(item.get("state", "active")) for item in active}))
                raise WorkspaceError(
                    f"{project.get('name', 'The destination project')} has unfinished runs ({states}). "
                    "Please wait until every run in this project has finished or been stopped."
                )
            for token, reservation in self.copy_reservations.items():
                if token != reservation_id and reservation.get("targetProjectId") == project_id:
                    raise WorkspaceError("That destination project is already receiving copied scenarios. Wait for that copy to finish.")

    def reserve_variation_copy(self, source_project_id: str, variation_ids: list[str], target_project_id: str = "") -> str:
        with self.activity_lock:
            self.assert_variations_copyable(source_project_id, variation_ids)
            self.assert_copy_destination_idle(target_project_id)
            token = make_id("copy-reservation")
            self.copy_reservations[token] = {
                "sourceProjectId": source_project_id,
                "variationIds": {str(item) for item in variation_ids if item},
                "targetProjectId": target_project_id,
            }
            return token

    def assert_project_copyable(self, project_id: str, reservation_id: str = "") -> None:
        """Reject full-project copies while any source run can still mutate project state."""
        with self.activity_lock:
            _, project = self.project(project_id)
            active = [item for item in self.active_run_records() if item.get("projectId") == project_id]
            if active:
                states = ", ".join(sorted({str(item.get("state", "active")) for item in active}))
                raise WorkspaceError(
                    f"{project.get('name', 'This project')} has unfinished runs ({states}). "
                    "Please wait until every run in this project has finished or been stopped."
                )
            for token, reservation in self.copy_reservations.items():
                if token != reservation_id and reservation.get("sourceProjectId") == project_id:
                    raise WorkspaceError("That project is already being copied. Wait for the copy to finish.")

    def reserve_project_copy(self, project_id: str) -> str:
        with self.activity_lock:
            self.assert_project_copyable(project_id)
            token = make_id("copy-reservation")
            self.copy_reservations[token] = {
                "sourceProjectId": project_id,
                "variationIds": set(),
                "targetProjectId": "",
                "wholeProject": True,
            }
            return token

    def release_copy_reservation(self, reservation_id: str) -> None:
        if reservation_id:
            with self.activity_lock:
                self.copy_reservations.pop(reservation_id, None)

    def assert_run_start_allowed(self, project_id: str, variation_ids: list[str]) -> None:
        with self.activity_lock:
            selected = {str(item) for item in variation_ids if item}
            for reservation in self.copy_reservations.values():
                if reservation.get("targetProjectId") == project_id:
                    raise WorkspaceError("Wait for the scenario copy into this project to finish before starting runs")
                if reservation.get("sourceProjectId") == project_id and reservation.get("wholeProject"):
                    raise WorkspaceError("Wait for the project copy to finish before starting runs in this project")
                if reservation.get("sourceProjectId") == project_id and selected.intersection(reservation.get("variationIds", set())):
                    raise WorkspaceError("Wait for the selected scenario copy to finish before starting those runs")

    def _require_idle_workspace(self) -> None:
        active = self.active_run_records()
        if active:
            names = ", ".join(str(item.get("variationName") or item.get("id")) for item in active[:5])
            raise WorkspaceError(f"Stop or finish active and waiting runs before resetting the workspace: {names}")

    def repair_workspace(self) -> dict[str, Any]:
        self._require_idle_workspace()
        recreated = []
        for name in self.directory_names:
            path = self.root / name
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
                recreated.append(name)
        staging = self.internal / "staging"
        abandoned = 0
        if staging.exists():
            for child in list(staging.iterdir()):
                if child.is_dir():
                    shutil.rmtree(child, ignore_errors=True)
                else:
                    child.unlink(missing_ok=True)
                abandoned += 1
        staging.mkdir(parents=True, exist_ok=True)
        removed_datastores = self._cleanup_orphaned_datastores()
        path_warnings = []
        for path in (self.projects, self.models, self.runs, self.input_library, self.templates):
            for item in path.rglob("*"):
                try:
                    self.validate_managed_path(item)
                except WorkspaceError as exc:
                    path_warnings.append({"path": str(item), "message": str(exc)})
        return {
            "ok": True, "recreated": recreated, "abandonedStagingRemoved": abandoned,
            "orphanedDatastoresRemoved": removed_datastores, "pathWarnings": path_warnings,
        }

    def archive_all_projects(self) -> dict[str, Any]:
        self._require_idle_workspace()
        archived = []
        for project in list(self.list_projects()):
            self.remove_project(str(project["id"]))
            archived.append(project["id"])
        return {"archived": archived, "recoverableDays": ARCHIVE_DAYS}

    def wipe_project_data(self, confirmation: str) -> dict[str, Any]:
        self._require_idle_workspace()
        if confirmation != "DELETE ALL PROJECTS":
            raise WorkspaceError('Type "DELETE ALL PROJECTS" to permanently wipe project data')
        project_ids = {item.get("id") for item in self.list_projects() + self.list_archived_projects() if item.get("id")}
        catalog = self.catalog()
        removed_records = [item for item in catalog.get("datastores", []) if item.get("projectId") in project_ids]
        catalog["datastores"] = [item for item in catalog.get("datastores", []) if item.get("projectId") not in project_ids]
        write_json(self.catalog_path, catalog)
        retained_paths = []
        for record in catalog.get("datastores", []):
            try:
                retained_paths.append(Path(str(record.get("path", ""))).resolve())
            except (OSError, RuntimeError):
                continue
        for root in (self.projects, self.removed_projects, self.runs):
            for child in list(root.iterdir()):
                if child.is_dir():
                    shutil.rmtree(child, ignore_errors=True)
                else:
                    child.unlink(missing_ok=True)
        for child in list(self.models.iterdir()):
            resolved = child.resolve()
            if any(path == resolved or resolved in path.parents for path in retained_paths):
                continue
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
            else:
                child.unlink(missing_ok=True)
        for cache in (self.internal / "comparison-cache", self.internal / "comparison_csv_cache"):
            if cache.exists():
                shutil.rmtree(cache, ignore_errors=True)
        for name in self.directory_names:
            (self.root / name).mkdir(parents=True, exist_ok=True)
        return {
            "wipedProjects": sorted(project_ids),
            "removedDatastoreIds": [item.get("id") for item in removed_records if item.get("id")],
            "preservedStandaloneResults": len(catalog.get("datastores", [])),
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

    def validate_managed_path(self, value: str | Path) -> Path:
        """Fail before writes that would leave too little filesystem path headroom."""
        path = Path(value).absolute()
        try:
            name_max = int(os.pathconf(str(path.parent if path.parent.exists() else self.root), "PC_NAME_MAX"))
            path_max = int(os.pathconf(str(self.root), "PC_PATH_MAX"))
        except (OSError, ValueError):
            name_max, path_max = 255, 1024
        oversized = next((part for part in path.parts if len(part.encode("utf-8")) > max(1, name_max - 32)), "")
        if oversized:
            raise WorkspaceError(f"A managed path component is too long: {oversized[:48]}")
        if len(os.fsencode(str(path))) > max(1, path_max - 128):
            raise WorkspaceError("The workspace path is too long for safe VisionEval file creation. Move the workspace closer to your home folder.")
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
        registered_names: dict[str, str] = {}
        for registration in self.settings().get("assetRegistrations", []):
            for asset in registration.get("assets", []) if isinstance(registration, dict) else []:
                if isinstance(asset, dict) and asset.get("kind") == "input-library" and asset.get("id"):
                    registered_names[str(asset["id"])] = str(asset.get("name") or asset["id"])
        for path in sorted((p for p in self.input_library.iterdir() if p.is_dir()), key=lambda p: p.name.lower()):
            files = sorted(p.name for p in path.glob("*.csv") if is_workspace_data(p))
            manifest = read_json(path / "region_builder_manifest.json", {})
            pairing = self.input_library_pairing(path.name)
            output.append({
                "id": path.name,
                "name": asset_display_name(manifest.get("regionName") or registered_names.get(path.name) or path.name),
                "fileCount": len(files),
                "files": files,
                "fingerprint": fingerprint_tree(path),
                "pairedTemplateId": pairing["templateId"],
                "pairingStatus": pairing["status"],
                "pairingError": pairing["error"],
            })
        return output

    def input_library_pairing(self, library_id: str) -> dict[str, str]:
        """Resolve one server-authoritative template for an installed InputLibrary."""
        library = self.within(self.input_library / library_id, self.input_library)
        if not library.is_dir():
            raise WorkspaceError("Unknown Input Library")
        candidates: set[str] = set()
        declared = False
        settings = self.settings()
        for registration in settings.get("assetRegistrations", []):
            assets = registration.get("assets", []) if isinstance(registration, dict) else []
            if not any(isinstance(item, dict) and item.get("kind") == "input-library" and item.get("id") == library_id for item in assets):
                continue
            declared = True
            candidates.update(
                str(item.get("id")) for item in assets
                if isinstance(item, dict) and item.get("kind") == "model-template" and item.get("id")
            )

        library_manifest = read_json(library / "region_builder_manifest.json", {})
        if library_manifest:
            declared = True
            identity = (
                str(library_manifest.get("regionName", "")),
                str(library_manifest.get("regionCode", "")),
                str(library_manifest.get("builtAt", "")),
                str((library_manifest.get("regionPackage") or {}).get("id", "")),
            )
            for template_path in self.templates.iterdir():
                if not template_path.is_dir():
                    continue
                template_manifest = read_json(template_path / "region_builder_manifest.json", {})
                template_identity = (
                    str(template_manifest.get("regionName", "")),
                    str(template_manifest.get("regionCode", "")),
                    str(template_manifest.get("builtAt", "")),
                    str((template_manifest.get("regionPackage") or {}).get("id", "")),
                )
                if any(identity) and template_identity == identity:
                    candidates.add(template_path.name)

        installed = {path.name for path in self.templates.iterdir() if path.is_dir()}
        present = sorted(candidates & installed)
        missing = sorted(candidates - installed)
        if len(present) == 1 and not missing:
            return {"status": "paired", "templateId": present[0], "error": ""}
        if len(present) > 1:
            return {"status": "ambiguous", "templateId": "", "error": "This Input Library is linked to more than one model package. Repair or reinstall its asset package."}
        if missing:
            return {"status": "missing", "templateId": "", "error": "The model package paired with this Input Library is missing. Repair or reinstall its asset package."}
        if declared:
            return {"status": "missing", "templateId": "", "error": "This Input Library's asset package does not contain a usable model definition."}
        return {"status": "unpaired", "templateId": "", "error": "This Input Library is not linked to a verified model package. Install or repair its asset package."}

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
        csv_files = sorted(p.name for p in (path / "inputs").glob("*.csv") if is_workspace_data(p)) if (path / "inputs").is_dir() else []
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
                    records.append({**record, "name": asset_display_name(record.get("name") or record.get("id"))})
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
            "name": asset_display_name(manifest.get("name") or manifest.get("regionName") or asset_id),
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
            raise WorkspaceError("Unknown model package")
        return path, {**record, "name": asset_display_name(record.get("name") or template_id)}

    def _assert_unique_project_name(self, name: str, excluding: str = "") -> str:
        clean = " ".join(str(name).split())
        if not clean:
            raise WorkspaceError("Project name is required")
        key = normalized_name(clean)
        if any(normalized_name(item.get("name", "")) == key for item in self._known_projects(excluding)):
            raise WorkspaceError("Project names must be unique, including archived projects")
        return clean

    def suggest_project_name(self, source_name: str) -> str:
        existing = {normalized_name(item.get("name", "")) for item in self._known_projects()}
        base = f"{' '.join(str(source_name).split())} Copy".strip()
        candidate, number = base, 2
        while normalized_name(candidate) in existing:
            candidate = f"{base} {number}"
            number += 1
        return candidate

    def _library_fingerprint(self, library_id: str) -> str:
        library = self.within(self.input_library / library_id, self.input_library)
        return fingerprint_tree(library)

    @staticmethod
    def _input_tree_fingerprint(
        root: Path, template_fingerprint: str = "", library_fingerprint: str = "",
        relative_paths: list[str] | None = None,
    ) -> str:
        digest = hashlib.sha256()
        digest.update(str(template_fingerprint).encode())
        digest.update(str(library_fingerprint).encode())
        paths = (
            [root / relative for relative in relative_paths]
            if relative_paths is not None
            else sorted(item for item in root.rglob("*") if item.is_file() and not item.is_symlink())
        )
        for path in paths:
            if not path.is_file() or path.is_symlink():
                return ""
            digest.update(str(path.relative_to(root)).encode())
            with path.open("rb") as handle:
                while block := handle.read(1024 * 1024):
                    digest.update(block)
        return digest.hexdigest()

    def scenario_input_fingerprint(self, project: dict[str, Any], variation_id: str = "baseline") -> str:
        """Fingerprint the effective inputs that VisionEval will receive."""
        project_directory = self.projects / str(project.get("id", ""))
        library_candidate = self.input_library / str(project["inputLibrary"]["id"])
        variation = None if variation_id == "baseline" else next(
            (item for item in project.get("variations", []) if item.get("id") == variation_id), None
        )
        if variation_id != "baseline" and not variation:
            raise WorkspaceError("Unknown project variation")
        overlays = {str(item.get("fileName", "")): item for item in (variation or {}).get("overlays", [])}
        digest = hashlib.sha256()
        digest.update(str(project.get("template", {}).get("fingerprint", "")).encode())
        digest.update(str(project.get("inputLibrary", {}).get("fingerprint", "")).encode())
        if not library_candidate.is_dir():
            for name, overlay in sorted(overlays.items()):
                digest.update(name.encode())
                path = Path(str(overlay.get("path", "")))
                if path.is_file():
                    digest.update(fingerprint_file(path).encode())
            return digest.hexdigest()
        library = self.within(library_candidate, self.input_library)
        for library_path in sorted(item for item in library.rglob("*") if item.is_file() and not item.is_symlink()):
            relative = str(library_path.relative_to(library))
            selected = library_path
            overlay = overlays.get(relative)
            if overlay:
                selected = self.within(str(overlay.get("path", "")), project_directory)
            digest.update(relative.encode())
            with selected.open("rb") as handle:
                while block := handle.read(1024 * 1024):
                    digest.update(block)
        return digest.hexdigest()

    @staticmethod
    def execution_fingerprint(input_fingerprint: str, runtime_digest: str) -> str:
        return hashlib.sha256(f"{input_fingerprint}|{runtime_digest}".encode()).hexdigest()

    def _record_input_fingerprint(self, record: dict[str, Any], project: dict[str, Any]) -> str:
        existing = str(record.get("inputStateFingerprint", ""))
        if existing:
            return existing
        run_id = str(record.get("runId", ""))
        prepared_inputs = self.models / run_id / "inputs" if run_id else Path()
        if run_id and prepared_inputs.is_dir():
            library = self.input_library / str(project.get("inputLibrary", {}).get("id", ""))
            if not library.is_dir():
                return ""
            relative_paths = sorted(
                str(path.relative_to(library))
                for path in library.rglob("*") if path.is_file() and not path.is_symlink()
            )
            return self._input_tree_fingerprint(
                prepared_inputs,
                str(project.get("template", {}).get("fingerprint", "")),
                str(project.get("inputLibrary", {}).get("fingerprint", "")),
                relative_paths,
            )
        return ""

    def _record_runtime_digest(self, record: dict[str, Any]) -> str:
        existing = str(record.get("runtimeImageDigest", ""))
        if existing:
            return existing
        run_id = str(record.get("runId", ""))
        if not run_id:
            return ""
        job = read_json(self.runs / run_id / "job.json", {})
        return str(job.get("imageDigest", ""))

    def result_reuse_status(
        self, project: dict[str, Any], record: dict[str, Any], variation_id: str, runtime_digest: str,
    ) -> str:
        if record.get("verification") != "verified":
            return "unproven"
        recorded_input = self._record_input_fingerprint(record, project)
        if not recorded_input:
            return "unproven"
        current_input = self.scenario_input_fingerprint(project, variation_id or "baseline")
        if recorded_input != current_input:
            return "previous"
        recorded_runtime = self._record_runtime_digest(record)
        if not recorded_runtime or not runtime_digest or recorded_runtime != runtime_digest:
            return "runtime_differs"
        recorded_execution = str(record.get("executionFingerprint", ""))
        expected = self.execution_fingerprint(current_input, runtime_digest)
        return "current" if not recorded_execution or recorded_execution == expected else "previous"

    def current_result(
        self, project: dict[str, Any], variation_id: str, runtime_digest: str,
    ) -> dict[str, Any] | None:
        candidates = []
        for record, link in self._completed_result_records(project):
            linked_variation = str((link or {}).get("variationId") or record.get("variationId", ""))
            role = str((link or {}).get("role") or record.get("role", ""))
            matches = role == "baseline" if variation_id == "baseline" else linked_variation == variation_id
            if matches and self.result_reuse_status(project, record, variation_id, runtime_digest) == "current":
                candidates.append(record)
        return max(candidates, key=lambda item: str(item.get("completedAt", "")), default=None)

    def result_statuses(self, project: dict[str, Any], runtime_digest: str) -> dict[str, Any]:
        catalog = {item.get("id"): item for item in self.catalog().get("datastores", [])}
        results: dict[str, list[dict[str, Any]]] = {}
        links = {item.get("datastoreId"): item for item in project.get("resultLinks", [])}
        for datastore_id in self.project_result_ids(project):
            record = catalog.get(datastore_id)
            if not record:
                continue
            link = links.get(datastore_id)
            variation_id = str((link or {}).get("variationId") or record.get("variationId", ""))
            role = str((link or {}).get("role") or record.get("role", ""))
            key = "baseline" if role == "baseline" else variation_id
            status = self.result_reuse_status(project, record, key, runtime_digest)
            results.setdefault(key, []).append({"datastoreId": datastore_id, "status": status})
        return results

    def _compatible_baselines(self, template_fingerprint: str, library_fingerprint: str) -> list[dict[str, Any]]:
        return sorted((
            item for item in self.catalog(False, False).get("datastores", [])
            if item.get("role") == "baseline"
            and item.get("verification") == "verified"
            and item.get("templateFingerprint") == template_fingerprint
            and item.get("inputLibraryFingerprint") == library_fingerprint
        ), key=lambda item: item.get("completedAt", ""), reverse=True)

    def project_has_compatible_baseline(self, project: dict[str, Any]) -> bool:
        # Legacy projects created before exact asset provenance was recorded keep
        # their historical run behavior. New and migrated projects with complete
        # fingerprints use the strict baseline gate below.
        if not project.get("template", {}).get("fingerprint") or not project.get("inputLibrary", {}).get("fingerprint"):
            return True
        baseline_id = str((project.get("baseline") or {}).get("datastoreId", ""))
        if not baseline_id:
            baseline_link = next((item for item in project.get("resultLinks", []) if item.get("role") == "baseline"), None)
            baseline_id = str((baseline_link or {}).get("datastoreId", ""))
        compatible = self._compatible_baselines(
            str(project.get("template", {}).get("fingerprint", "")),
            str(project.get("inputLibrary", {}).get("fingerprint", "")),
        )
        return any(item.get("id") == baseline_id for item in compatible)

    def create_project(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = self._assert_unique_project_name(str(payload.get("name", "")))
        project_type = str(payload.get("projectType") or "standard")
        if project_type not in PROJECT_TYPES:
            raise WorkspaceError("Project type must be standard or hypercube")
        library_id = str(payload.get("inputLibraryId", ""))
        pairing = self.input_library_pairing(library_id)
        if pairing["status"] != "paired":
            raise WorkspaceError(pairing["error"] or "The selected Input Library has no verified model package")
        template_id = pairing["templateId"]
        requested_template_id = str(payload.get("templateId", ""))
        if requested_template_id and requested_template_id != template_id:
            raise WorkspaceError("The requested model package is not paired with the selected Input Library")
        _, template = self.template(template_id)
        library = self.within(self.input_library / library_id, self.input_library)
        library_fingerprint = fingerprint_tree(library)
        baseline = dict(payload.get("baseline") or {"strategy": "fresh"})
        baseline_name = str(baseline.get("displayName", "Baseline")).strip() or "Baseline"
        if baseline.get("strategy") not in {"fresh", "existing"}:
            raise WorkspaceError("Baseline strategy must be fresh or existing")
        if baseline.get("strategy") == "existing":
            datastore_id = str(baseline.get("datastoreId", ""))
            existing = next((item for item in self.catalog(False)["datastores"] if item.get("id") == datastore_id), None)
            if not existing:
                raise WorkspaceError("Choose a registered existing baseline")
            compatible = (
                existing.get("templateFingerprint") == template.get("fingerprint")
                and existing.get("inputLibraryFingerprint") == library_fingerprint
                and existing.get("verification") == "verified"
                and existing.get("role") == "baseline"
            )
            if not compatible:
                raise WorkspaceError(
                    "Choose a verified completed baseline produced by this exact Model package and Input Library"
                )
            baseline = {
                "strategy": "existing",
                "datastoreId": datastore_id,
                "displayName": baseline_name,
                "compatibility": "verified",
                "warning": "",
            }
        else:
            compatible = self._compatible_baselines(template.get("fingerprint", ""), library_fingerprint)
            if compatible and payload.get("baseline") is None:
                baseline = {
                    "strategy": "existing", "datastoreId": compatible[0]["id"],
                    "displayName": baseline_name, "compatibility": "verified", "warning": "",
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
        if project_type == "hypercube" and variants:
            raise WorkspaceError("Hypercube projects must be created without ordinary scenarios")
        project_id = make_id("project", name)
        project = {
            "version": PROJECT_VERSION,
            "id": project_id,
            "name": name,
            "createdAt": now_iso(),
            "updatedAt": now_iso(),
            "projectType": project_type,
            "template": {"id": template_id, "name": template["name"], "fingerprint": template["fingerprint"]},
            "inputLibrary": {"id": library_id, "path": str(library), "fingerprint": library_fingerprint},
            "baseline": baseline,
            "variations": variants,
            "runIds": [],
            "datastoreIds": [],
            "understandRefs": {"inputIds": [], "intermediaryIds": [], "outputIds": []},
        }
        directory = self.projects / project_id
        self.validate_managed_path(directory / "overlays" / "variation-placeholder" / "input-placeholder.csv")
        directory.mkdir()
        write_json(directory / "project.json", project)
        return project

    @staticmethod
    def _project_display_names(project: dict[str, Any]) -> dict[str, Any]:
        displayed = copy.deepcopy(project)
        displayed["projectType"] = Workspace.project_type(displayed)
        template = displayed.get("template")
        if isinstance(template, dict) and template.get("name"):
            template["name"] = asset_display_name(template["name"])
        library = displayed.get("inputLibrary")
        if isinstance(library, dict):
            if library.get("name"):
                library["name"] = asset_display_name(library["name"])
            library["displayName"] = asset_display_name(library.get("name") or library.get("id"))
        return displayed

    @staticmethod
    def project_type(project: dict[str, Any]) -> str:
        value = str(project.get("projectType") or "")
        if value in PROJECT_TYPES:
            return value
        return "hypercube" if project.get("hypercubes") else "standard"

    @classmethod
    def require_standard_project(cls, project: dict[str, Any]) -> None:
        if cls.project_type(project) != "standard":
            raise WorkspaceError("Hypercube projects can contain only generated matrix cases")

    def list_projects(self) -> list[dict[str, Any]]:
        projects = [read_json(path, {}) for path in self.projects.glob("*/project.json")]
        return sorted((self._project_display_names(p) for p in projects if p), key=lambda p: p.get("updatedAt", ""), reverse=True)

    @property
    def removed_projects(self) -> Path:
        return self.internal / "archive" / "projects"

    def active_project_ids(self) -> set[str]:
        return {item.get("id", "") for item in self.list_projects() if item.get("id")}

    @staticmethod
    def project_result_ids(project: dict[str, Any]) -> list[str]:
        """Return owned and linked datastore IDs without counting a result twice."""
        values = [str(item) for item in project.get("datastoreIds", []) if item]
        values.extend(str(item.get("datastoreId", "")) for item in project.get("resultLinks", []) if item.get("datastoreId"))
        return list(dict.fromkeys(values))

    def _known_projects(self, excluding: str = "") -> list[dict[str, Any]]:
        projects = self.list_projects() + self.list_archived_projects()
        return [item for item in projects if item.get("id") and item.get("id") != excluding]

    @staticmethod
    def _result_references(projects: list[dict[str, Any]]) -> dict[str, list[str]]:
        references: dict[str, list[str]] = {}
        for project in projects:
            project_id = str(project.get("id", ""))
            baseline_id = str((project.get("baseline") or {}).get("datastoreId", ""))
            if baseline_id:
                references.setdefault(baseline_id, []).append(project_id)
            for link in project.get("resultLinks", []):
                datastore_id = str(link.get("datastoreId", ""))
                if datastore_id:
                    references.setdefault(datastore_id, []).append(project_id)
        return {key: list(dict.fromkeys(value)) for key, value in references.items()}

    def _completed_result_records(self, project: dict[str, Any]) -> list[tuple[dict[str, Any], dict[str, Any] | None]]:
        catalog = {item.get("id"): item for item in self.catalog().get("datastores", [])}
        associations: list[tuple[dict[str, Any], dict[str, Any] | None]] = []
        seen: set[str] = set()
        for datastore_id in project.get("datastoreIds", []):
            record = catalog.get(datastore_id)
            if record and record.get("verification") == "verified" and datastore_id not in seen:
                associations.append((record, None)); seen.add(datastore_id)
        for link in project.get("resultLinks", []):
            datastore_id = str(link.get("datastoreId", ""))
            record = catalog.get(datastore_id)
            if record and record.get("verification") == "verified" and datastore_id not in seen:
                associations.append((record, link)); seen.add(datastore_id)
        baseline_id = str((project.get("baseline") or {}).get("datastoreId", ""))
        record = catalog.get(baseline_id)
        if record and record.get("verification") == "verified" and baseline_id not in seen:
            associations.append((record, {"datastoreId": baseline_id, "variationId": "", "role": "baseline"}))
        return associations

    def hypercube_replacement_allowed(self, project: dict[str, Any]) -> bool:
        """A generated matrix may be replaced only before any case was submitted or completed."""
        if project.get("runIds"):
            return False
        return not any(
            str((link or {}).get("role") or record.get("role", "scenario")) != "baseline"
            for record, link in self._completed_result_records(project)
        )

    def copy_result_estimate(self, project_id: str, variation_ids: list[str] | None = None) -> dict[str, Any]:
        _, project = self.project(project_id)
        selected = {str(item) for item in variation_ids or [] if item}
        records: list[dict[str, Any]] = []
        total = 0
        for record, link in self._completed_result_records(project):
            role = str((link or {}).get("role") or record.get("role", "scenario"))
            variation_id = str((link or {}).get("variationId") or record.get("variationId", ""))
            if selected and role != "baseline" and variation_id not in selected:
                continue
            path = Path(str(record.get("path", ""))).expanduser()
            size = directory_size(path) if path.is_dir() else 0
            total += size
            records.append({"id": record.get("id", ""), "role": role, "variationId": variation_id, "bytes": size})
        return {"resultCount": len(records), "bytes": total, "results": records}

    @staticmethod
    def _make_result_link(
        record: dict[str, Any], source_project: dict[str, Any], target_variation_id: str,
        source_variation_id: str, linked_at: str,
    ) -> dict[str, Any]:
        return {
            "datastoreId": record["id"], "variationId": target_variation_id,
            "sourceProjectId": source_project.get("id", ""), "sourceVariationId": source_variation_id,
            "role": record.get("role", "scenario"), "linkedAt": linked_at,
        }

    def _copy_result_records(
        self, source_project: dict[str, Any], target_project: dict[str, Any],
        variation_ids: dict[str, str], staging_project: Path, target_directory: Path,
        *, include_baseline: bool,
        cancelled: Callable[[], bool] | None = None,
        progress: Callable[[int, int], None] | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Copy verified datastores into staged project-owned storage."""
        copied_at = now_iso()
        selected: list[tuple[dict[str, Any], str, str]] = []
        total_bytes = 0
        for record, link in self._completed_result_records(source_project):
            role = str((link or {}).get("role") or record.get("role", "scenario"))
            source_variation_id = str((link or {}).get("variationId") or record.get("variationId", ""))
            target_variation_id = "" if role == "baseline" else variation_ids.get(source_variation_id, "")
            if role == "baseline" and not include_baseline:
                continue
            if role != "baseline" and not target_variation_id:
                continue
            source_path = Path(str(record.get("path", ""))).expanduser().resolve()
            if not source_path.is_dir():
                raise WorkspaceError(f"Completed result is missing: {record.get('label') or record.get('id')}")
            total_bytes += directory_size(source_path)
            selected.append((record, source_variation_id, target_variation_id))

        if total_bytes:
            free = shutil.disk_usage(staging_project).free
            headroom = max(256 * 1024 * 1024, total_bytes // 10)
            if free < total_bytes + headroom:
                raise WorkspaceError(
                    f"Copying these results requires approximately {total_bytes + headroom:,} bytes including safety headroom"
                )

        target_names = {item.get("id"): item.get("name", "Scenario") for item in target_project.get("variations", [])}
        copied_records: list[dict[str, Any]] = []
        copied_bytes = 0
        for record, source_variation_id, target_variation_id in selected:
            if cancelled and cancelled():
                raise CopyCancelled()
            role = str(record.get("role", "scenario"))
            datastore_id = make_id("datastore", str(record.get("variationName") or role))
            staged_datastore = staging_project / "results" / datastore_id / "Datastore"
            final_datastore = target_directory / "results" / datastore_id / "Datastore"
            self.validate_managed_path(final_datastore / "DatastoreListing.Rda")
            staged_datastore.parent.mkdir(parents=True, exist_ok=True)
            source_datastore = Path(str(record["path"])).expanduser().resolve()
            for source_file in sorted(item for item in source_datastore.rglob("*") if item.is_file() and not item.is_symlink()):
                if cancelled and cancelled():
                    raise CopyCancelled()
                destination = staged_datastore / source_file.relative_to(source_datastore)
                destination.parent.mkdir(parents=True, exist_ok=True)
                with source_file.open("rb") as reader, destination.open("wb") as writer:
                    while block := reader.read(4 * 1024 * 1024):
                        if cancelled and cancelled():
                            raise CopyCancelled()
                        writer.write(block)
                        copied_bytes += len(block)
                        if progress:
                            progress(copied_bytes, total_bytes)
                shutil.copystat(source_file, destination)
            input_fingerprint = self._record_input_fingerprint(record, source_project)
            runtime_digest = self._record_runtime_digest(record)
            copied = copy.deepcopy(record)
            copied.update({
                "id": datastore_id,
                "path": str(final_datastore),
                "projectId": target_project["id"],
                "projectName": target_project["name"],
                "variationId": target_variation_id,
                "variationName": "Baseline" if role == "baseline" else target_names.get(target_variation_id, "Scenario"),
                "label": f"{target_project['name']} — {'Baseline' if role == 'baseline' else target_names.get(target_variation_id, 'Scenario')}",
                "registeredAt": copied_at,
                "runId": "",
                "resultVersion": int(record.get("resultVersion", 0) or 0) + 1,
                "copiedFrom": {
                    "projectId": source_project.get("id", ""),
                    "projectName": source_project.get("name", ""),
                    "variationId": source_variation_id,
                    "datastoreId": record.get("id", ""),
                    "runId": record.get("runId", ""),
                    "copiedAt": copied_at,
                },
            })
            if input_fingerprint:
                copied["inputStateFingerprint"] = input_fingerprint
                if runtime_digest:
                    copied["runtimeImageDigest"] = runtime_digest
                    copied["executionFingerprint"] = self.execution_fingerprint(input_fingerprint, runtime_digest)
            copied_records.append(copied)
            target_project.setdefault("datastoreIds", []).append(datastore_id)
            if role == "baseline":
                target_project["baseline"] = {
                    "strategy": "existing", "datastoreId": datastore_id,
                    "displayName": str((target_project.get("baseline") or {}).get("displayName", "Baseline")),
                    "compatibility": "verified", "warning": "",
                }
        return copied_records, total_bytes

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

    @staticmethod
    def _migrated_hypercube_project(project: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        """Convert legacy parameter-sweep metadata without changing group identities."""
        migrated = copy.deepcopy(project)
        changed = False

        current_groups = migrated.get("hypercubes")
        legacy_groups = migrated.pop("parameterSweeps", None)
        if legacy_groups is not None:
            changed = True
            merged = []
            seen: set[str] = set()
            for group in list(current_groups or []) + list(legacy_groups or []):
                if not isinstance(group, dict):
                    continue
                group_copy = copy.deepcopy(group)
                key = str(group_copy.get("id") or json.dumps(group_copy, sort_keys=True))
                if key in seen:
                    continue
                seen.add(key)
                merged.append(group_copy)
            migrated["hypercubes"] = merged

        for variation in migrated.get("variations", []):
            if not isinstance(variation, dict):
                continue
            legacy = variation.pop("parameterSweep", None)
            if legacy is not None:
                changed = True
                if "hypercube" not in variation and isinstance(legacy, dict):
                    variation["hypercube"] = copy.deepcopy(legacy)
            metadata = variation.get("hypercube")
            if isinstance(metadata, dict) and "sweepId" in metadata:
                changed = True
                if "hypercubeId" not in metadata:
                    metadata["hypercubeId"] = metadata["sweepId"]
                metadata.pop("sweepId", None)
        inferred_type = "hypercube" if migrated.get("hypercubes") else "standard"
        if migrated.get("projectType") not in PROJECT_TYPES:
            migrated["projectType"] = inferred_type
            changed = True
        return migrated, changed

    def migrate_hypercube_metadata(self) -> None:
        """Atomically migrate active and archived projects to Hypercube metadata."""
        paths = list(self.projects.glob("*/project.json")) + list(self.removed_projects.glob("*/project.json"))
        for path in paths:
            project = read_json(path, {})
            if not project:
                continue
            migrated, changed = self._migrated_hypercube_project(project)
            if changed:
                write_json(path, migrated)

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
            output.append({**self._project_display_names(project), "archiveDirectory": path.parent.name, "daysRemaining": days})
        return sorted(output, key=lambda item: item.get("archivedAt", ""), reverse=True)

    def project(self, project_id: str) -> tuple[Path, dict[str, Any]]:
        directory = self.within(self.projects / project_id, self.projects)
        project = read_json(directory / "project.json", {})
        if project.get("id") != project_id:
            raise WorkspaceError("Unknown project")
        project = self._project_display_names(project)
        library = project.setdefault("inputLibrary", {})
        if library.get("id") and not library.get("fingerprint"):
            try:
                library["fingerprint"] = self._library_fingerprint(str(library["id"]))
                write_json(directory / "project.json", project)
            except WorkspaceError:
                pass
        return directory, project

    def save_project(self, project: dict[str, Any]) -> None:
        directory, _ = self.project(project["id"])
        project["updatedAt"] = now_iso()
        write_json(directory / "project.json", project)

    def update_project(self, project_id: str, name: str) -> dict[str, Any]:
        _, project = self.project(project_id)
        clean_name = self._assert_unique_project_name(name, project_id)
        project["name"] = clean_name
        self.save_project(project)
        return project

    def copy_project(
        self, project_id: str, name: str, include_results: bool = True,
        *, cancelled: Callable[[], bool] | None = None,
        progress: Callable[[int, int], None] | None = None, reservation_id: str = "",
    ) -> dict[str, Any]:
        owned_reservation = ""
        if not reservation_id:
            owned_reservation = self.reserve_project_copy(project_id)
            reservation_id = owned_reservation
        try:
            self.assert_project_copyable(project_id, reservation_id)
            return self._copy_project_reserved(
                project_id, name, include_results, cancelled=cancelled, progress=progress,
            )
        finally:
            self.release_copy_reservation(owned_reservation)

    def _copy_project_reserved(
        self, project_id: str, name: str, include_results: bool = True,
        *, cancelled: Callable[[], bool] | None = None,
        progress: Callable[[int, int], None] | None = None,
    ) -> dict[str, Any]:
        source_directory, source_project = self.project(project_id)
        clean_name = self._assert_unique_project_name(name)

        copied_at = now_iso()
        copied_project = copy.deepcopy(source_project)
        copied_project_id = make_id("project", clean_name)
        copied_project.update({
            "id": copied_project_id,
            "name": clean_name,
            "createdAt": copied_at,
            "updatedAt": copied_at,
            "runIds": [],
            "datastoreIds": [],
            "copiedFrom": {
                "projectId": source_project.get("id", ""),
                "projectName": source_project.get("name", ""),
                "copiedAt": copied_at,
            },
        })
        if isinstance(copied_project.get("hypercubeDraft"), dict):
            copied_project["hypercubeDraft"]["revision"] = make_id("hypercube-draft", clean_name)
            copied_project["hypercubeDraft"]["savedAt"] = copied_at

        variation_ids: dict[str, str] = {}
        copied_variations = []
        for source_variation in source_project.get("variations", []):
            copied_variation = copy.deepcopy(source_variation)
            source_variation_id = str(source_variation.get("id", ""))
            copied_variation_id = make_id("variation", str(source_variation.get("name", "scenario")))
            variation_ids[source_variation_id] = copied_variation_id
            copied_variation["id"] = copied_variation_id
            copied_variation["overlays"] = []
            copied_variations.append(copied_variation)
        copied_project["variations"] = copied_variations

        copied_hypercubes = []
        hypercube_ids: dict[str, str] = {}
        for source_hypercube in source_project.get("hypercubes", []):
            copied_hypercube = copy.deepcopy(source_hypercube)
            source_hypercube_id = str(source_hypercube.get("id", ""))
            copied_hypercube_id = make_id("hypercube", str(source_hypercube.get("name", "hypercube")))
            copied_hypercube["id"] = copied_hypercube_id
            if source_hypercube_id:
                hypercube_ids[source_hypercube_id] = copied_hypercube_id
            copied_hypercube["scenarioIds"] = [
                variation_ids[item]
                for item in source_hypercube.get("scenarioIds", [])
                if item in variation_ids
            ]
            copied_hypercubes.append(copied_hypercube)
        if copied_hypercubes or "hypercubes" in source_project:
            copied_project["hypercubes"] = copied_hypercubes
        for copied_variation in copied_variations:
            metadata = copied_variation.get("hypercube")
            if isinstance(metadata, dict) and metadata.get("hypercubeId") in hypercube_ids:
                metadata["hypercubeId"] = hypercube_ids[metadata["hypercubeId"]]
        copied_project.pop("resultLinks", None)
        copied_project["baseline"] = {
            "strategy": "fresh",
            "displayName": str((source_project.get("baseline") or {}).get("displayName", "Baseline")),
        }

        target = self.projects / copied_project_id
        self.validate_managed_path(target / "overlays" / "variation-placeholder" / "input-placeholder.csv")
        staging_root = self.internal / "staging"
        staging_root.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix="project-copy-", dir=staging_root))
        copied_records: list[dict[str, Any]] = []
        copied_bytes = 0
        try:
            for source_variation in source_project.get("variations", []):
                if cancelled and cancelled():
                    raise CopyCancelled()
                copied_variation_id = variation_ids.get(str(source_variation.get("id", "")), "")
                copied_variation = next(item for item in copied_variations if item["id"] == copied_variation_id)
                for source_overlay in source_variation.get("overlays", []):
                    filename = Path(str(source_overlay.get("fileName", ""))).name
                    if not filename or filename != source_overlay.get("fileName"):
                        raise WorkspaceError("Copied project contains an invalid overlay filename")
                    source_path = self.within(str(source_overlay.get("path", "")), source_directory)
                    if not source_path.is_file():
                        raise WorkspaceError(f"Copied project overlay is missing: {filename}")
                    staged_overlay = staging / "overlays" / copied_variation_id / filename
                    staged_overlay.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_path, staged_overlay)
                    copied_variation["overlays"].append({
                        "fileName": filename,
                        "path": str(target / "overlays" / copied_variation_id / filename),
                        "updatedAt": copied_at,
                        **({"editOperations": copy.deepcopy(source_overlay.get("editOperations"))} if source_overlay.get("editOperations") else {}),
                    })
            copied_records, copied_bytes = self._copy_result_records(
                source_project, copied_project, variation_ids, staging, target, include_baseline=True,
                cancelled=cancelled, progress=progress,
            )
            if cancelled and cancelled():
                raise CopyCancelled()
            write_json(staging / "project.json", copied_project)
            if target.exists():
                raise WorkspaceError("A project already uses the generated ID")
            staging.rename(target)
            if copied_records:
                catalog = self.catalog()
                catalog["datastores"].extend(copied_records)
                try:
                    write_json(self.catalog_path, catalog)
                except Exception:
                    shutil.rmtree(target, ignore_errors=True)
                    raise
        except Exception:
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)
            raise
        copied_project["copySummary"] = {
            "resultsCopied": len(copied_records), "bytesCopied": copied_bytes,
            "scenariosCopied": len(copied_variations),
        }
        return copied_project

    @staticmethod
    def _unique_variation_name(preferred: str, existing: set[str]) -> str:
        base = str(preferred).strip() or "Scenario"
        candidate = base
        number = 1
        while candidate.lower() in existing:
            candidate = f"{base} (copy)" if number == 1 else f"{base} (copy {number})"
            number += 1
        existing.add(candidate.lower())
        return candidate

    def copy_variations(
        self, source_project_id: str, variation_ids: list[str], *,
        target_project_id: str = "", new_project_name: str = "", include_results: bool = True,
        cancelled: Callable[[], bool] | None = None,
        progress: Callable[[int, int], None] | None = None,
        reservation_id: str = "",
    ) -> dict[str, Any]:
        owned_reservation = ""
        if not reservation_id:
            owned_reservation = self.reserve_variation_copy(
                source_project_id, variation_ids, target_project_id,
            )
            reservation_id = owned_reservation
        try:
            return self._copy_variations_reserved(
                source_project_id, variation_ids,
                target_project_id=target_project_id, new_project_name=new_project_name,
                include_results=include_results, cancelled=cancelled, progress=progress,
                reservation_id=reservation_id,
            )
        finally:
            self.release_copy_reservation(owned_reservation)

    def _copy_variations_reserved(
        self, source_project_id: str, variation_ids: list[str], *,
        target_project_id: str = "", new_project_name: str = "", include_results: bool = True,
        cancelled: Callable[[], bool] | None = None,
        progress: Callable[[int, int], None] | None = None,
        reservation_id: str = "",
    ) -> dict[str, Any]:
        source_directory, source = self.project(source_project_id)
        requested = [str(item) for item in variation_ids if item]
        if not requested or len(requested) != len(set(requested)):
            raise WorkspaceError("Choose one or more unique scenarios to copy")
        available = {item.get("id"): item for item in source.get("variations", [])}
        if any(item not in available for item in requested):
            raise WorkspaceError("A selected source scenario no longer exists")
        # Recheck in the worker immediately before it reads source files. The
        # synchronous copy-operation preflight may have happened before a run
        # was queued or started.
        self.assert_variations_copyable(source_project_id, requested, reservation_id)
        if bool(target_project_id) == bool(str(new_project_name).strip()):
            raise WorkspaceError("Choose either an existing project or a new project name")

        copied_at = now_iso()
        new_project = not target_project_id
        if new_project:
            clean_name = self._assert_unique_project_name(new_project_name)
            target_id = make_id("project", clean_name)
            target = {
                "version": PROJECT_VERSION, "id": target_id, "name": clean_name,
                "createdAt": copied_at, "updatedAt": copied_at,
                "projectType": "standard",
                "template": copy.deepcopy(source["template"]),
                "inputLibrary": copy.deepcopy(source["inputLibrary"]),
                "baseline": {
                    "strategy": "fresh",
                    "displayName": str((source.get("baseline") or {}).get("displayName", "Baseline")),
                },
                "variations": [], "runIds": [], "datastoreIds": [],
                "understandRefs": copy.deepcopy(source.get("understandRefs") or {"inputIds": [], "intermediaryIds": [], "outputIds": []}),
                "copiedFrom": {"projectId": source["id"], "projectName": source["name"], "copiedAt": copied_at},
            }
            target_directory = self.projects / target_id
            target_updated_at = ""
        else:
            self.assert_copy_destination_idle(target_project_id, reservation_id)
            target_directory, target = self.project(target_project_id)
            self.require_standard_project(target)
            target_id = target["id"]
            target_updated_at = str(target.get("updatedAt", ""))
            if (
                target["template"].get("fingerprint") != source["template"].get("fingerprint")
                or target["inputLibrary"].get("fingerprint") != source["inputLibrary"].get("fingerprint")
            ):
                raise WorkspaceError("Scenario copies require the same model package and Input Library")
            target = copy.deepcopy(target)

        staging_root = self.internal / "staging"
        staging_root.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix="scenario-copy-", dir=staging_root))
        staged_project = staging / "project"
        copied_records: list[dict[str, Any]] = []
        copied_bytes = 0
        try:
            if new_project:
                staged_project.mkdir()
            else:
                shutil.copytree(target_directory, staged_project)
            existing_names = {str(item.get("name", "")).lower() for item in target.get("variations", [])}
            id_map: dict[str, str] = {}
            copied_variations = []
            for source_id in requested:
                if cancelled and cancelled():
                    raise CopyCancelled()
                source_variation = available[source_id]
                copied_id = make_id("variation", str(source_variation.get("name", "scenario")))
                id_map[source_id] = copied_id
                copied_variation = copy.deepcopy(source_variation)
                copied_variation.update({
                    "id": copied_id,
                    "name": self._unique_variation_name(
                        str(source_variation.get("name", "Scenario")), existing_names,
                    ),
                    "overlays": [],
                    "copiedFrom": {"projectId": source["id"], "variationId": source_id, "copiedAt": copied_at},
                })
                copied_variation.pop("hypercube", None)
                for overlay in source_variation.get("overlays", []):
                    filename = Path(str(overlay.get("fileName", ""))).name
                    source_path = self.within(str(overlay.get("path", "")), source_directory)
                    if not filename or filename != overlay.get("fileName") or not source_path.is_file():
                        raise WorkspaceError("A selected scenario contains a missing or invalid saved file")
                    staged_overlay = staged_project / "overlays" / copied_id / filename
                    staged_overlay.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_path, staged_overlay)
                    copied_variation["overlays"].append({
                        "fileName": filename,
                        "path": str(target_directory / "overlays" / copied_id / filename),
                        "updatedAt": copied_at,
                        **({"editOperations": copy.deepcopy(overlay.get("editOperations"))} if overlay.get("editOperations") else {}),
                    })
                target.setdefault("variations", []).append(copied_variation)
                copied_variations.append(copied_variation)

            include_baseline = new_project or not self.project_has_compatible_baseline(target)
            copied_records, copied_bytes = self._copy_result_records(
                source, target, id_map, staged_project, target_directory, include_baseline=include_baseline,
                cancelled=cancelled, progress=progress,
            )
            if cancelled and cancelled():
                raise CopyCancelled()
            target["updatedAt"] = copied_at
            write_json(staged_project / "project.json", target)

            with self.activity_lock:
                self.assert_variations_copyable(source_project_id, requested, reservation_id)
                if new_project:
                    self.validate_managed_path(target_directory / "overlays" / "variation-placeholder" / "input-placeholder.csv")
                    if target_directory.exists():
                        raise WorkspaceError("A project already uses the generated ID")
                    staged_project.rename(target_directory)
                else:
                    self.assert_copy_destination_idle(target_project_id, reservation_id)
                    current = read_json(target_directory / "project.json", {})
                    if current.get("updatedAt", "") != target_updated_at:
                        raise WorkspaceError("The target project changed while scenarios were being copied")
                    backup = staging / "original"
                    target_directory.rename(backup)
                    try:
                        staged_project.rename(target_directory)
                    except Exception:
                        backup.rename(target_directory)
                        raise
            if copied_records:
                catalog = self.catalog()
                catalog["datastores"].extend(copied_records)
                try:
                    write_json(self.catalog_path, catalog)
                except Exception:
                    if new_project:
                        shutil.rmtree(target_directory, ignore_errors=True)
                    else:
                        shutil.rmtree(target_directory, ignore_errors=True)
                        backup.rename(target_directory)
                    raise
            if not new_project:
                shutil.rmtree(backup)
            result_statuses = self.result_statuses(target, "")
            reusable = [item["id"] for item in copied_variations if any(
                result.get("status") == "current" for result in result_statuses.get(item["id"], [])
            )]
            pending = [item["id"] for item in copied_variations if item["id"] not in reusable]
            return {
                "project": target, "variations": copied_variations, "createdProject": new_project,
                "copySummary": {
                    "resultsCopied": len(copied_records), "bytesCopied": copied_bytes,
                    "scenariosCopied": len(copied_variations),
                    "reusableVariationIds": reusable, "pendingVariationIds": pending,
                },
            }
        finally:
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)

    def unlink_result(self, project_id: str, datastore_id: str) -> dict[str, Any]:
        _, project = self.project(project_id)
        before = list(project.get("resultLinks", []))
        project["resultLinks"] = [item for item in before if item.get("datastoreId") != datastore_id]
        if len(project["resultLinks"]) == len(before):
            raise WorkspaceError("That project does not link to the selected result")
        if not project["resultLinks"]:
            project.pop("resultLinks", None)
        self.save_project(project)
        self._cleanup_orphaned_datastores()
        return {"projectId": project_id, "datastoreId": datastore_id, "unlinked": True}

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
        self._rebase_project_result_paths(project_id, directory, target)
        return {"removed": project_id, "recoverable": True, "purgeAfter": project["purgeAfter"]}

    def _rebase_project_result_paths(self, project_id: str, source: Path, target: Path) -> None:
        catalog = self.catalog()
        changed = False
        source = source.resolve()
        for record in catalog.get("datastores", []):
            if record.get("projectId") != project_id or not record.get("path"):
                continue
            candidate = Path(str(record["path"])).expanduser().resolve()
            try:
                relative = candidate.relative_to(source)
            except ValueError:
                continue
            record["path"] = str(target / relative)
            changed = True
        if changed:
            write_json(self.catalog_path, catalog)

    def _archived(self, project_id: str) -> tuple[Path, dict[str, Any]]:
        for path in self.removed_projects.glob("*/project.json"):
            project = read_json(path, {})
            if project.get("id") == project_id:
                return path.parent, project
        raise WorkspaceError("Unknown archived project")

    def restore_project(self, project_id: str) -> dict[str, Any]:
        directory, project = self._archived(project_id)
        self._assert_unique_project_name(project.get("name", ""), project_id)
        target = self.projects / project_id
        if target.exists():
            raise WorkspaceError("An active project already uses this ID")
        project.pop("archivedAt", None)
        project.pop("purgeAfter", None)
        write_json(directory / "project.json", project)
        shutil.move(str(directory), str(target))
        self._rebase_project_result_paths(project_id, directory, target)
        return project

    def _active_datastore_references(self) -> dict[str, list[str]]:
        return self._result_references(self.list_projects())

    def _cleanup_orphaned_datastores(self) -> list[str]:
        projects = self._known_projects()
        known = {item.get("id") for item in projects}
        references = self._result_references(projects)
        catalog = self.catalog()
        kept, removed = [], []
        for item in catalog.get("datastores", []):
            datastore_id = str(item.get("id", ""))
            owner = str(item.get("projectId", ""))
            if not owner or owner in known or references.get(datastore_id):
                kept.append(item)
                continue
            removed.append(datastore_id)
            run_id = str(item.get("runId", ""))
            candidate = self.models / run_id if run_id else Path(str(item.get("path", "")))
            try:
                candidate = self.within(candidate, self.models)
                if candidate.exists():
                    shutil.rmtree(candidate)
            except WorkspaceError:
                pass
        if removed:
            catalog["datastores"] = kept
            write_json(self.catalog_path, catalog)
        return removed

    def purge_project(self, project_id: str) -> dict[str, Any]:
        directory, project = self._archived(project_id)
        references = self._result_references(self._known_projects(excluding=project_id))
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
        self._cleanup_orphaned_datastores()
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
        self.require_standard_project(project)
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
                self.save_overlay(
                    project_id,
                    variation["id"],
                    overlay["fileName"],
                    source_path.read_text(encoding="utf-8"),
                    copy.deepcopy(overlay.get("editOperations")) if overlay.get("editOperations") else None,
                )
            _, project = self.project(project_id)
            variation = next(item for item in project["variations"] if item["id"] == variation["id"])
        return variation

    def update_variation(self, project_id: str, variation_id: str, name: str | None = None, notes: dict[str, str] | None = None, scenario_note: str | None = None, file_note: dict[str, Any] | None = None) -> dict[str, Any]:
        _, project = self.project(project_id)
        self.require_standard_project(project)
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
        if file_note is not None:
            if not isinstance(file_note, dict):
                raise WorkspaceError("File note must be an object")
            filename = str(file_note.get("filename", ""))
            if not filename or Path(filename).name != filename:
                raise WorkspaceError("File note filename must be a basename")
            text = str(file_note.get("text", ""))
            file_notes = variation.setdefault("notes", {})
            if text:
                file_notes[filename] = text
            else:
                file_notes.pop(filename, None)
        self.save_project(project)
        return variation

    def delete_variation(self, project_id: str, variation_id: str) -> dict[str, Any]:
        with self.activity_lock:
            impact = self.variation_deletion_impact(project_id, variation_id)
            if impact["blocked"]:
                raise WorkspaceError("Stop or finish this scenario's active runs before removing it")
            directory, project = self.project(project_id)
            original_project = copy.deepcopy(project)
            catalog = self.catalog()
            original_catalog = copy.deepcopy(catalog)
            job_ids = set(impact["jobIds"])
            result_ids = set(impact["resultIds"])
            retained_ids = set(impact["retainedResultIds"])
            removed_result_ids = result_ids - retained_ids
            retained_paths = {
                Path(str(item.get("path", ""))).expanduser().resolve()
                for item in catalog.get("datastores", [])
                if item.get("id") in retained_ids and item.get("path")
            }
            batches: dict[Path, dict[str, Any]] = {}
            for batch_path in self.runs.glob("batch-*.json"):
                batch = read_json(batch_path, {})
                if job_ids.intersection(map(str, batch.get("jobIds", []))):
                    batches[batch_path] = copy.deepcopy(batch)

            paths: set[Path] = set()
            overlay_directory = directory / "overlays" / variation_id
            if overlay_directory.exists():
                paths.add(overlay_directory.resolve())
            for job_id in job_ids:
                run_directory = self.runs / job_id
                job = read_json(run_directory / "job.json", {})
                if run_directory.exists():
                    paths.add(run_directory.resolve())
                model_value = str(job.get("modelPath", "")).strip()
                model_path = Path(model_value).expanduser() if model_value else None
                if model_path is not None and model_path.exists():
                    resolved = model_path.resolve()
                    if not any(path == resolved or resolved in path.parents for path in retained_paths):
                        paths.add(resolved)
            for item in catalog.get("datastores", []):
                if item.get("id") not in removed_result_ids or not item.get("path"):
                    continue
                candidate = Path(str(item["path"])).expanduser()
                if candidate.exists():
                    paths.add(candidate.resolve())
            paths = {
                path for path in paths
                if not any(other != path and other in path.parents for other in paths)
            }

            staging_root = self.internal / "staging"
            staging_root.mkdir(parents=True, exist_ok=True)
            staging = Path(tempfile.mkdtemp(prefix="scenario-delete-", dir=staging_root))
            moved: list[tuple[Path, Path]] = []
            try:
                for index, source in enumerate(sorted(paths, key=lambda item: len(item.parts))):
                    self.within(source)
                    target = staging / f"item-{index}"
                    source.rename(target)
                    moved.append((source, target))

                project["variations"] = [item for item in project.get("variations", []) if item.get("id") != variation_id]
                project["runIds"] = [item for item in project.get("runIds", []) if item not in job_ids]
                project["datastoreIds"] = [item for item in project.get("datastoreIds", []) if item not in result_ids]
                project["resultLinks"] = [
                    item for item in project.get("resultLinks", [])
                    if str(item.get("variationId", "")) != variation_id
                ]
                if not project["resultLinks"]:
                    project.pop("resultLinks", None)
                self.save_project(project)

                next_records = []
                for item in catalog.get("datastores", []):
                    if item.get("id") in removed_result_ids:
                        continue
                    if item.get("id") in retained_ids:
                        item = {
                            **item,
                            "sourceScenarioRemoved": True,
                            "sourceScenarioRemovedAt": now_iso(),
                            "sourceScenarioId": variation_id,
                        }
                    next_records.append(item)
                catalog["datastores"] = next_records
                write_json(self.catalog_path, catalog)

                for batch_path, batch in batches.items():
                    batch["jobIds"] = [item for item in batch.get("jobIds", []) if item not in job_ids]
                    if batch["jobIds"]:
                        write_json(batch_path, batch)
                    else:
                        batch_path.unlink(missing_ok=True)
            except Exception:
                write_json(directory / "project.json", original_project)
                write_json(self.catalog_path, original_catalog)
                for batch_path, batch in batches.items():
                    write_json(batch_path, batch)
                for source, target in reversed(moved):
                    if target.exists() and not source.exists():
                        source.parent.mkdir(parents=True, exist_ok=True)
                        target.rename(source)
                raise
            finally:
                shutil.rmtree(staging, ignore_errors=True)
            return {
                "deleted": variation_id,
                "filesRemoved": impact["files"],
                "runsRemoved": impact["terminalRuns"],
                "logsRemoved": impact["logs"],
                "resultsRemoved": len(removed_result_ids),
                "resultsRetained": len(retained_ids),
                "bytesRemoved": impact["removableBytes"],
            }

    def variation_deletion_impact(self, project_id: str, variation_id: str) -> dict[str, Any]:
        directory, project = self.project(project_id)
        self.require_standard_project(project)
        variation = next((item for item in project.get("variations", []) if item.get("id") == variation_id), None)
        if not variation:
            raise WorkspaceError("Unknown project variation")
        jobs = []
        for path in self.runs.glob("*/job.json"):
            job = read_json(path, {})
            if job.get("projectId") == project_id and job.get("variationId") == variation_id:
                jobs.append(job)
        active = [item for item in jobs if item.get("state") in ACTIVE_RUN_STATES]
        terminal = [item for item in jobs if item.get("state") not in ACTIVE_RUN_STATES]
        records = []
        links = {str(item.get("datastoreId", "")): item for item in project.get("resultLinks", [])}
        for item in self.catalog().get("datastores", []):
            datastore_id = str(item.get("id", ""))
            link = links.get(datastore_id)
            linked_variation = str((link or {}).get("variationId") or item.get("variationId", ""))
            associated = datastore_id in project.get("datastoreIds", []) or link is not None
            if associated and linked_variation == variation_id:
                records.append(item)
        other_references = self._result_references(self._known_projects(excluding=project_id))
        retained = [
            item for item in records
            if item.get("projectId") != project_id or other_references.get(str(item.get("id", "")))
        ]
        retained_ids = {str(item.get("id", "")) for item in retained}
        removable = [
            item for item in records
            if str(item.get("id", "")) not in retained_ids and item.get("projectId") == project_id
        ]
        size_paths: set[Path] = set()
        overlay_directory = directory / "overlays" / variation_id
        if overlay_directory.exists():
            size_paths.add(overlay_directory)
        for job in terminal:
            run_directory = self.runs / str(job.get("id", ""))
            if run_directory.exists():
                size_paths.add(run_directory)
            model_value = str(job.get("modelPath", "")).strip()
            model_path = Path(model_value).expanduser() if model_value else None
            if model_path is not None and model_path.exists() and not any(
                str(item.get("path", "")).startswith(str(model_path)) for item in retained
            ):
                size_paths.add(model_path)
        for item in removable:
            path_value = str(item.get("path", "")).strip()
            path = Path(path_value).expanduser() if path_value else None
            if path is not None and path.exists():
                size_paths.add(path)
        unique_paths = {
            path for path in size_paths
            if not any(other != path and other in path.parents for other in size_paths)
        }
        return {
            "projectId": project_id,
            "variationId": variation_id,
            "scenarioName": variation.get("name", "Scenario"),
            "files": len(variation.get("overlays", [])),
            "activeRuns": len(active),
            "activeStates": sorted({str(item.get("state", "")) for item in active}),
            "terminalRuns": len(terminal),
            "logs": sum((self.runs / str(item.get("id", "")) / "run.log").is_file() for item in terminal),
            "results": len(records),
            "retainedResults": len(retained),
            "removableBytes": sum(directory_size(path) for path in unique_paths if path.exists()),
            "blocked": bool(active),
            "jobIds": [str(item.get("id", "")) for item in terminal],
            "resultIds": [str(item.get("id", "")) for item in records],
            "retainedResultIds": [str(item.get("id", "")) for item in retained],
        }

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

    def save_overlay(
        self, project_id: str, variation_id: str, filename: str, content: str,
        edit_operations: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        directory, project = self.project(project_id)
        self.require_standard_project(project)
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
        self.validate_managed_path(overlay)
        overlay.parent.mkdir(parents=True, exist_ok=True)
        overlay.write_text(content, encoding="utf-8")
        prior = next((entry for entry in variant.get("overlays", []) if entry.get("fileName") == safe_name), {})
        item = {"fileName": safe_name, "path": str(overlay), "updatedAt": now_iso()}
        operations = edit_operations if edit_operations is not None else prior.get("editOperations")
        if operations:
            deduplicated: list[dict[str, Any]] = []
            operation_ids: set[str] = set()
            for operation in operations:
                if not isinstance(operation, dict):
                    continue
                operation_id = str(operation.get("operationId", "")).strip()
                if operation_id and operation_id in operation_ids:
                    continue
                if operation_id:
                    operation_ids.add(operation_id)
                deduplicated.append(copy.deepcopy(operation))
            if deduplicated:
                item["editOperations"] = deduplicated
        variant["overlays"] = [entry for entry in variant.get("overlays", []) if entry["fileName"] != safe_name] + [item]
        self.save_project(project)
        return item

    def save_overlays_atomic(
        self, project_id: str, variation_id: str, changes: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Stage and commit a validated overlay batch without partial file updates."""
        directory, project = self.project(project_id)
        self.require_standard_project(project)
        variant = next((item for item in project["variations"] if item["id"] == variation_id), None)
        if not variant:
            raise WorkspaceError("Unknown project variation")
        if not changes:
            raise WorkspaceError("Choose at least one file to change")
        names = [str(item.get("filename", "")) for item in changes]
        if len(names) != len(set(names)):
            raise WorkspaceError("A batch may include each input file only once")
        overlay_root = directory / "overlays" / variation_id
        self.validate_managed_path(overlay_root)
        overlay_root.mkdir(parents=True, exist_ok=True)
        staging = overlay_root / f".batch-{uuid.uuid4().hex}"
        self.validate_managed_path(staging)
        staging.mkdir()
        backups: dict[Path, bytes | None] = {}
        committed: list[Path] = []
        next_items: list[dict[str, Any]] = []
        prior_by_name = {str(item.get("fileName", "")): item for item in variant.get("overlays", [])}
        try:
            for change in changes:
                safe_name = Path(str(change.get("filename", ""))).name
                if safe_name != change.get("filename") or not safe_name.lower().endswith(".csv"):
                    raise WorkspaceError("Only CSV input files may be edited")
                library_file = self.within(self.input_library / project["inputLibrary"]["id"] / safe_name, self.input_library)
                if not library_file.is_file():
                    raise WorkspaceError(f"{safe_name} is not in the selected library")
                (staging / safe_name).write_text(str(change.get("content", "")), encoding="utf-8")
                target = overlay_root / safe_name
                self.validate_managed_path(target)
                backups[target] = target.read_bytes() if target.is_file() else None
                prior = prior_by_name.get(safe_name, {})
                item = {"fileName": safe_name, "path": str(target), "updatedAt": now_iso()}
                operations = change.get("editOperations") if change.get("editOperations") is not None else prior.get("editOperations")
                if operations:
                    deduplicated: list[dict[str, Any]] = []
                    operation_ids: set[str] = set()
                    for operation in operations:
                        if not isinstance(operation, dict):
                            continue
                        operation_id = str(operation.get("operationId", "")).strip()
                        if operation_id and operation_id in operation_ids:
                            continue
                        if operation_id:
                            operation_ids.add(operation_id)
                        deduplicated.append(copy.deepcopy(operation))
                    if deduplicated:
                        item["editOperations"] = deduplicated
                next_items.append(item)
            for item in next_items:
                target = Path(item["path"])
                os.replace(staging / item["fileName"], target)
                committed.append(target)
            changed_names = {item["fileName"] for item in next_items}
            variant["overlays"] = [item for item in variant.get("overlays", []) if item.get("fileName") not in changed_names] + next_items
            self.save_project(project)
            return {"saved": next_items, "count": len(next_items)}
        except Exception:
            for target in reversed(committed):
                original = backups.get(target)
                if original is None:
                    target.unlink(missing_ok=True)
                else:
                    target.write_bytes(original)
            raise
        finally:
            shutil.rmtree(staging, ignore_errors=True)

    def delete_overlay(self, project_id: str, variation_id: str, filename: str) -> dict[str, Any]:
        directory, project = self.project(project_id)
        self.require_standard_project(project)
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
    def _summary_protected_column(name: str) -> bool:
        value = str(name).lower()
        return value in {"geo", "year", "county", "bzone", "azone", "marea", "zone", "taz", "id"} or value.endswith("id") or value.endswith("_id") or value.endswith("code")

    @classmethod
    def _summary_numeric_columns(cls, columns: list[str], rows: list[dict[str, str]]) -> set[str]:
        numeric: set[str] = set()
        for column in columns:
            if cls._summary_protected_column(column):
                continue
            for row in rows:
                value = str(row.get(column, "")).strip()
                if not value:
                    continue
                try:
                    float(value)
                except ValueError:
                    continue
                numeric.add(column)
                break
        return numeric

    @staticmethod
    def _summary_geography_details(filename: str, geographies: set[str], available: set[str]) -> dict[str, Any]:
        lower = filename.lower()
        unit = "Bzones" if lower.startswith("bzone_") else "Mareas" if lower.startswith("marea_") else "locations"
        values = sorted((str(item) for item in geographies if str(item)), key=str.lower)
        total = len({str(item) for item in available if str(item)})
        complete = bool(values and total and set(values) == {str(item) for item in available if str(item)})
        singular = {"Bzones": "Bzone", "Mareas": "Marea", "locations": "location"}[unit]
        if unit == "locations":
            if complete:
                label = f"All locations ({len(values):,})"
                if values:
                    label += f": {', '.join(values)}"
            elif len(values) == 1:
                label = values[0]
            else:
                label = ", ".join(values)
        elif complete:
            label = f"All {singular if len(values) == 1 else unit} ({len(values):,})"
        elif total:
            label = f"{len(values):,} of {total:,} {singular if total == 1 else unit}"
        else:
            label = f"{len(values):,} {singular if len(values) == 1 else unit}"
        return {
            "text": label or "No changed locations",
            "scope": "all" if complete else "partial",
            "kind": singular,
            "count": len(values),
            "total": total,
            "names": values if unit == "locations" else [],
        }

    @classmethod
    def _summary_geography(cls, filename: str, geographies: set[str], available: set[str]) -> tuple[str, str]:
        details = cls._summary_geography_details(filename, geographies, available)
        return str(details["text"]), str(details["scope"])

    @staticmethod
    def _summary_action(operation: dict[str, Any]) -> tuple[str, str]:
        if operation.get("valueType") == "share_group":
            values = operation.get("groupValues") or operation.get("value") or {}
            if isinstance(values, dict):
                return "set linked shares to", ", ".join(f"{key}={value}" for key, value in values.items())
        kind = str(operation.get("operation", ""))
        action = {
            "set": "set to", "add": "increased by", "subtract": "decreased by",
            "multiply": "multiplied by", "percent": "increased", "decrease_percent": "decreased",
        }.get(kind, "changed by")
        value = operation.get("value", "")
        amount = f"{value}%" if kind in {"percent", "decrease_percent"} else str(value)
        return action, amount

    @staticmethod
    def _edit_source(operations: list[dict[str, Any]]) -> str:
        """Classify exact edit provenance without guessing for legacy metadata."""
        if not operations or any(item.get("source") not in {"batch", "single_file"} for item in operations):
            return "unavailable"
        sources = {str(item.get("source")) for item in operations}
        return "mixed" if len(sources) > 1 else next(iter(sources))

    def _automatic_file_summary(
        self, filename: str, overlay: dict[str, Any], changed_columns: set[str],
        changed_cells: int, geographies: set[str], years: set[str],
        original_rows: list[dict[str, str]], edited_rows: list[dict[str, str]],
        available_geographies: set[str], editable_columns: set[str],
        operation_targets: list[set[str]] | None = None,
    ) -> dict[str, Any]:
        operations = [item for item in overlay.get("editOperations", []) if isinstance(item, dict)]
        resolved_targets = operation_targets or [
            {str(item) for item in operation.get("locations", []) if str(item)} for operation in operations
        ]
        expected_rows: list[dict[str, float | str]] = [dict(row) for row in original_rows]
        operation_targeted_geographies = [set() for _ in operations]
        operation_cells: list[set[tuple[int, str]]] = [set() for _ in operations]
        valid_operations = [False] * len(operations)

        def legacy_integer_column(column: str) -> bool:
            values = [
                str(row.get(column, "")).strip()
                for row in [*original_rows, *edited_rows]
                if str(row.get(column, "")).strip()
            ]
            return bool(values) and all(re.fullmatch(r"[-+]?\d+", value) for value in values)

        def rounded(operation: dict[str, Any], column: str, value: float) -> float:
            rounding = operation.get("rounding") if isinstance(operation.get("rounding"), dict) else {}
            integer_columns = {str(item) for item in rounding.get("integerColumns", [])}
            if column in integer_columns or (not rounding and legacy_integer_column(column)):
                return float(math.floor(value + 0.5))
            precision = rounding.get("precision")
            if isinstance(precision, int) and 0 <= precision <= 8:
                scale = 10 ** precision
                return math.floor(value * scale + 0.5) / scale
            return value

        for index, operation in enumerate(operations):
            columns = {str(item) for item in operation.get("columns", [])} & editable_columns
            kind = str(operation.get("operation", ""))
            categorical = operation.get("valueType") == "categorical"
            share_group = operation.get("valueType") == "share_group"
            if share_group:
                values = operation.get("groupValues") or operation.get("value") or {}
                if kind != "set" or not columns or not isinstance(values, dict) or not columns.issubset(values):
                    continue
                valid_operations[index] = True
                allowed = resolved_targets[index] if index < len(resolved_targets) else set()
                for row_index, row in enumerate(expected_rows):
                    year, geo = str(row.get("Year", "")), str(row.get("Geo", ""))
                    if operation.get("year") and str(operation.get("year")) != year:
                        continue
                    if not operation.get("allLocations") and (not allowed or geo not in allowed):
                        continue
                    if geo:
                        operation_targeted_geographies[index].add(geo)
                    for column in columns:
                        row[column] = str(values[column])
                        operation_cells[index].add((row_index, column))
                continue
            if categorical:
                if kind != "set" or len(columns) != 1:
                    continue
                value = str(operation.get("value", ""))
                valid_operations[index] = True
                allowed = resolved_targets[index] if index < len(resolved_targets) else set()
                for row_index, row in enumerate(expected_rows):
                    year = str(row.get("Year", ""))
                    geo = str(row.get("Geo", ""))
                    if operation.get("year") and str(operation.get("year")) != year:
                        continue
                    if not operation.get("allLocations") and (not allowed or geo not in allowed):
                        continue
                    column = next(iter(columns))
                    if geo:
                        operation_targeted_geographies[index].add(geo)
                    row[column] = value
                    operation_cells[index].add((row_index, column))
                continue
            try:
                value = float(operation.get("value", 0))
            except (TypeError, ValueError):
                structured_valid = False
                continue
            calculator = {
                "set": lambda current: value,
                "add": lambda current: current + value,
                "subtract": lambda current: current - value,
                "multiply": lambda current: current * value,
                "percent": lambda current: current * (1 + value / 100),
                "decrease_percent": lambda current: current * (1 - value / 100),
            }.get(kind)
            if not columns or calculator is None:
                continue
            valid_operations[index] = True
            allowed = resolved_targets[index] if index < len(resolved_targets) else set()
            for row_index, row in enumerate(expected_rows):
                year = str(row.get("Year", ""))
                geo = str(row.get("Geo", ""))
                if operation.get("year") and str(operation.get("year")) != year:
                    continue
                if not operation.get("allLocations") and (not allowed or geo not in allowed):
                    continue
                for column in columns:
                    try:
                        source_row = original_rows[row_index] if operation.get("basis") == "baseline" else row
                        current = float(source_row.get(column, ""))
                    except (TypeError, ValueError):
                        continue
                    if geo:
                        operation_targeted_geographies[index].add(geo)
                    next_value = calculator(current)
                    row[column] = rounded(operation, column, next_value)
                    operation_cells[index].add((row_index, column))

        # A baseline-relative operation is a reset barrier for its targeted
        # cells. Earlier operations remain stored as provenance, but no longer
        # describe the effective final change for those cells.
        effective_operation_cells = [set(cells) for cells in operation_cells]
        for index, operation in enumerate(operations):
            if operation.get("basis") != "baseline":
                continue
            for prior_index in range(index):
                effective_operation_cells[prior_index].difference_update(operation_cells[index])

        comparison_columns = set(editable_columns) | set(changed_columns)
        actual_changed: set[tuple[int, str]] = set()
        explained: set[tuple[int, str]] = set()
        unexplained: set[tuple[int, str]] = set()
        for row_index in range(max(len(original_rows), len(edited_rows))):
            before_row = original_rows[row_index] if row_index < len(original_rows) else {}
            expected_row = expected_rows[row_index] if row_index < len(expected_rows) else {}
            after_row = edited_rows[row_index] if row_index < len(edited_rows) else {}
            for column in comparison_columns:
                before_text, after_text = str(before_row.get(column, "")), str(after_row.get(column, ""))
                if before_text == after_text:
                    continue
                cell = (row_index, column)
                actual_changed.add(cell)
                expected_value = expected_row.get(column, before_text)
                try:
                    expected, actual = float(expected_value), float(after_text)
                except (TypeError, ValueError):
                    if str(expected_value) == after_text:
                        explained.add(cell)
                    else:
                        unexplained.add(cell)
                    continue
                decimals = len(after_text.split(".", 1)[1]) if "." in after_text else 0
                tolerance = max(1e-9, 0.5 * (10 ** -max(0, decimals)))
                if math.isclose(expected, actual, rel_tol=1e-9, abs_tol=tolerance):
                    explained.add(cell)
                else:
                    unexplained.add(cell)
        used_indexes = [
            index for index, cells in enumerate(effective_operation_cells)
            if valid_operations[index] and bool(cells & explained)
        ]
        geography_details = self._summary_geography_details(filename, geographies, available_geographies)
        geography, scope = str(geography_details["text"]), str(geography_details["scope"])
        actual_all_variables = bool(editable_columns and changed_columns == editable_columns)
        selected_columns = {column for index in used_indexes for _, column in effective_operation_cells[index] if column in editable_columns}
        all_variables = bool(editable_columns and selected_columns == editable_columns) if used_indexes else actual_all_variables
        if any(operations[index].get("valueType") == "categorical" for index in used_indexes):
            all_variables = False
        variable_text = "all variables" if all_variables else ", ".join(sorted(changed_columns, key=str.lower)) or "values"
        groups: list[dict[str, Any]] = []
        signatures: list[tuple[str, str, str, str]] = []
        parts: list[str] = []
        if used_indexes:
            for index in used_indexes:
                operation = operations[index]
                action, amount = self._summary_action(operation)
                year = str(operation.get("year") or "all years")
                effective_cells = effective_operation_cells[index]
                group_geographies = {
                    str(edited_rows[row_index].get("Geo", ""))
                    for row_index, _ in effective_cells
                    if row_index < len(edited_rows) and str(edited_rows[row_index].get("Geo", ""))
                } or operation_targeted_geographies[index]
                effective_geographies = {
                    str(edited_rows[row_index].get("Geo", ""))
                    for row_index, _ in effective_cells & explained
                    if row_index < len(edited_rows) and str(edited_rows[row_index].get("Geo", ""))
                }
                group_geo = self._summary_geography_details(filename, group_geographies, available_geographies)
                effective_geo = self._summary_geography_details(filename, effective_geographies, available_geographies)
                unchanged_count = max(0, len(group_geographies) - len(effective_geographies))
                if unchanged_count:
                    effective_unit = effective_geo["kind"] if len(effective_geographies) == 1 else {
                        "Bzone": "Bzones", "Marea": "Mareas", "location": "locations",
                    }[str(effective_geo["kind"])]
                    group_geo["effectiveCount"] = len(effective_geographies)
                    group_geo["unchangedCount"] = unchanged_count
                    group_geo["effectiveText"] = (
                        f"{len(effective_geographies):,} {effective_unit}; "
                        f"{unchanged_count:,} unchanged after rounding"
                    )
                variables = sorted({column for _,column in effective_cells if column in editable_columns},key=str.lower)
                group_all = bool(editable_columns and set(variables) == editable_columns and operation.get("valueType") != "categorical")
                group = {
                    "variables": variables, "allVariables": group_all,
                    "action": action, "amount": amount,
                    "change": f"{action.capitalize()} {amount}", "locations": group_geo,
                    "years": [year], "operationIndex": index + 1,
                    "source": operation.get("source", ""),
                    "basis": operation.get("basis", "current"),
                }
                groups.append(group)
                signatures.append((action, amount, year, str(group_geo["scope"])))
                label = "all variables" if group_all else ", ".join(variables)
                effective_suffix = (
                    f" ({group_geo['effectiveText']})"
                    if group_geo.get("effectiveText") else ""
                )
                parts.append(
                    f"{label}: {action} {amount} for {group_geo['text']}{effective_suffix}"
                )
        if unexplained:
            other_columns = sorted({column for _, column in unexplained}, key=str.lower)
            other_geographies = {
                str(edited_rows[row_index].get("Geo", ""))
                for row_index, _ in unexplained
                if row_index < len(edited_rows) and str(edited_rows[row_index].get("Geo", ""))
            }
            other_geo = self._summary_geography_details(filename, other_geographies, available_geographies)
            other_count = len(unexplained)
            other_all = bool(editable_columns and set(other_columns) == editable_columns)
            groups.append({
                "variables": other_columns, "allVariables": other_all,
                "action": "changed", "amount": "",
                "change": f"Changed {other_count:,} value{'s' if other_count != 1 else ''}",
                "locations": other_geo, "years": sorted(years), "otherChanges": True,
            })
            other_label = "all variables" if other_all else ", ".join(other_columns) or "values"
            parts.append(f"{other_label}: {other_count:,} value{'s' if other_count != 1 else ''} changed outside validated operations for {other_geo['text']}")
        if groups:
            ordered = len(used_indexes) > 1
            text_prefix = f"{filename} — applied in order: " if ordered else f"{filename} — "
            signature = signatures[0] if len(signatures) == 1 and not unexplained else None
            return {
                "text": f"{text_prefix}{'; '.join(parts)}.", "signature": signature,
                "details": {
                    "filename": filename, "allVariables": all_variables,
                    "validated": bool(used_indexes) and not unexplained,
                    "ordered": ordered, "groups": groups,
                },
            }
        location_text = f" across {geography}" if geographies else ""
        changed_value_text = f"{changed_cells:,} value{'s' if changed_cells != 1 else ''} changed"
        change = f"Changed {changed_cells:,} value{'s' if changed_cells != 1 else ''}"
        return {
            "text": f"{filename} — {variable_text}: {changed_value_text}{location_text}.", "signature": None,
            "details": {
                "filename": filename, "allVariables": actual_all_variables, "validated": False,
                "groups": [{
                    "variables": sorted(changed_columns, key=str.lower), "allVariables": actual_all_variables,
                    "action": "changed", "amount": "", "change": change,
                    "locations": geography_details, "years": sorted(years),
                }],
            },
        }

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

    def review_project(self, project_id: str, change_limit: int = 2000, variation_ids: set[str] | None = None) -> dict[str, Any]:
        _, project = self.project(project_id)
        library = self.input_library / project["inputLibrary"]["id"]
        scenarios = []
        for variation in project.get("variations", []):
            if variation_ids is not None and variation.get("id") not in variation_ids:
                continue
            scenario = {"id": variation["id"], "name": variation["name"], "scenarioNote": variation.get("scenarioNote", ""), "automaticSummary": "", "automaticSummaryHeadline": "", "automaticSummaryDetails": [], "fileCount": 0, "changedRows": 0, "changedCells": 0, "files": []}
            summary_signatures: list[tuple[str, str, str, str] | None] = []
            remaining = change_limit
            remaining_audit_rows = change_limit
            for overlay in variation.get("overlays", []):
                filename = overlay["fileName"]
                original_path = library / filename
                edited_path = self.within(overlay["path"], self.projects / project_id)
                original_columns, original_rows = self._csv_dicts(original_path)
                edited_columns, edited_rows = self._csv_dicts(edited_path)
                changes, audit_rows, audit_columns = [], [], set()
                row_numbers, geographies, years, changed_columns = set(), set(), set(), set()
                columns = edited_columns if edited_columns == original_columns else sorted(set(original_columns + edited_columns))
                row_count = max(len(original_rows), len(edited_rows))
                for row_index in range(row_count):
                    before_row = original_rows[row_index] if row_index < len(original_rows) else {}
                    after_row = edited_rows[row_index] if row_index < len(edited_rows) else {}
                    row_changes = []
                    for column in columns:
                        before, after = str(before_row.get(column, "")), str(after_row.get(column, ""))
                        if before == after:
                            continue
                        changed_columns.add(column)
                        row_numbers.add(row_index + 2)
                        geo = str(after_row.get("Geo", before_row.get("Geo", "")))
                        year = str(after_row.get("Year", before_row.get("Year", "")))
                        if geo: geographies.add(geo)
                        if year: years.add(year)
                        if remaining > 0:
                            changes.append({"row": row_index + 2, "column": column, "geo": geo, "year": year, "before": before, "after": after})
                            remaining -= 1
                        row_changes.append({"column": column, "before": before, "after": after})
                    if row_changes and remaining_audit_rows > 0:
                        audit_rows.append({
                            "row": row_index + 2,
                            "geo": str(after_row.get("Geo", before_row.get("Geo", ""))),
                            "year": str(after_row.get("Year", before_row.get("Year", ""))),
                            "cells": row_changes,
                        })
                        audit_columns.update(item["column"] for item in row_changes if item["column"] not in {"Geo", "Year"})
                        remaining_audit_rows -= 1
                changed_cells = sum(1 for row_index in range(row_count) for column in columns if str((original_rows[row_index] if row_index < len(original_rows) else {}).get(column, "")) != str((edited_rows[row_index] if row_index < len(edited_rows) else {}).get(column, "")))
                file_record = {
                    "filename": filename,
                    "changedRows": len(row_numbers),
                    "changedCells": changed_cells,
                    "geographies": sorted(geographies, key=str.lower),
                    "years": sorted(years),
                    "notes": variation.get("notes", {}).get(filename, ""),
                    "changes": changes,
                    "auditRows": audit_rows,
                    "auditColumns": [column for column in columns if column in audit_columns],
                    "auditRowsShown": len(audit_rows),
                    "auditTruncated": len(audit_rows) < len(row_numbers),
                }
                editable_columns = self._summary_numeric_columns(original_columns, original_rows)
                relevant_years = years or {str(row.get("Year", "")) for row in original_rows if str(row.get("Year", ""))}
                available_geographies = {
                    str(row.get("Geo", "")) for row in original_rows
                    if str(row.get("Geo", "")) and (not relevant_years or str(row.get("Year", "")) in relevant_years)
                }
                operations = [item for item in overlay.get("editOperations", []) if isinstance(item, dict)]
                editable_columns |= {
                    str(column)
                    for operation in operations if operation.get("valueType") in {"categorical", "share_group"}
                    for column in operation.get("columns", [])
                    if str(column) in original_columns and not self._summary_protected_column(str(column))
                }
                file_record["editSource"] = self._edit_source(operations)
                operation_targets = []
                try:
                    geography = self.geography_options(project_id, filename)
                    geography_levels = {str(level.get("id", "")): level for level in geography.get("levels", [])}
                except (OSError, WorkspaceError):
                    geography_levels = {}
                for operation in operations:
                    selected = {str(item) for item in operation.get("locations", []) if str(item)}
                    level = geography_levels.get(str(operation.get("geographyType", "")), {})
                    mapped = {
                        str(target)
                        for item in level.get("values", []) if str(item.get("value", "")) in selected
                        for target in item.get("targetValues", []) if str(target)
                    }
                    operation_targets.append(selected | mapped)
                automatic = self._automatic_file_summary(
                    filename, overlay, changed_columns, changed_cells, geographies, years,
                    original_rows, edited_rows, available_geographies, editable_columns,
                    operation_targets,
                )
                file_record["automaticSummary"] = automatic["text"]
                file_record["automaticSummaryDetails"] = automatic["details"]
                summary_signatures.append(automatic["signature"])
                scenario["files"].append(file_record)
                scenario["changedRows"] += file_record["changedRows"]
                scenario["changedCells"] += file_record["changedCells"]
            scenario["fileCount"] = len(scenario["files"])
            edit_sources = {item.get("editSource", "unavailable") for item in scenario["files"]}
            scenario["editSource"] = (
                "unavailable" if not edit_sources or "unavailable" in edit_sources
                else "mixed" if len(edit_sources) > 1 or "mixed" in edit_sources
                else next(iter(edit_sources))
            )
            scenario["automaticSummary"] = " ".join(
                item.get("automaticSummary", "") for item in scenario["files"] if item.get("automaticSummary")
            )
            scenario["automaticSummaryDetails"] = [
                item["automaticSummaryDetails"] for item in scenario["files"] if item.get("automaticSummaryDetails")
            ]
            signatures = [item for item in summary_signatures if item]
            if signatures and len(signatures) == len(summary_signatures) and len({item[:3] for item in signatures}) == 1:
                action, amount = signatures[0][:2]
                scope = "all locations" if all(item[3] == "all" for item in signatures) else "location scope varies"
                scenario["automaticSummaryHeadline"] = f"{action.capitalize()} {amount} across {scenario['fileCount']} file{'s' if scenario['fileCount'] != 1 else ''} · {scope}"
            else:
                scenario["automaticSummaryHeadline"] = f"{scenario['fileCount']} file{'s' if scenario['fileCount'] != 1 else ''} changed · {scenario['changedCells']:,} values"
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
            "inputLibraryId": project["inputLibrary"]["id"],
            "inputLibraryFingerprint": project["inputLibrary"].get("fingerprint") or self._library_fingerprint(project["inputLibrary"]["id"]),
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

    def display_catalog(self, include_archived: bool = False, include_hidden: bool = False) -> dict[str, Any]:
        """Return catalog records with current, user-facing project identities.

        Stored catalog names remain immutable run/copy provenance. These
        optional display fields resolve live names by stable ids so renaming a
        project or scenario does not leave stale labels in the interface.
        """
        catalog = copy.deepcopy(self.catalog(include_archived, include_hidden))
        projects = self.list_projects()
        if include_archived:
            projects += self.list_archived_projects()
        project_by_id = {str(item.get("id", "")): item for item in projects if item.get("id")}
        template_names = {
            str(item.get("id", "")): asset_display_name(item.get("name") or item.get("id"))
            for item in self.list_templates()
        }
        for record in catalog.get("datastores", []):
            project = project_by_id.get(str(record.get("projectId", "")))
            if project:
                record["projectType"] = self.project_type(project)
                project_name = str(project.get("name") or record.get("projectName") or "Project")
                role = str(record.get("role", ""))
                variation_id = str(record.get("variationId", ""))
                if role == "baseline":
                    variation_name = str(project.get("baseline", {}).get("displayName") or "Baseline")
                else:
                    variation = next(
                        (item for item in project.get("variations", []) if str(item.get("id", "")) == variation_id),
                        None,
                    )
                    variation_name = str((variation or {}).get("name") or record.get("variationName") or role or "Result")
                record["displayProjectName"] = project_name
                record["displayVariationName"] = variation_name
                record["displayLabel"] = f"{project_name} — {variation_name}"
                record["packageDisplayName"] = asset_display_name(
                    project.get("inputLibrary", {}).get("displayName")
                    or project.get("inputLibrary", {}).get("name")
                    or project.get("template", {}).get("name")
                    or template_names.get(str(record.get("templateId", "")), "")
                )
            else:
                record["projectType"] = "imported"
                record["displayProjectName"] = str(record.get("projectName") or "Previously registered")
                record["displayVariationName"] = str(record.get("variationName") or record.get("role") or "Result")
                record["displayLabel"] = str(record.get("label") or record["displayVariationName"])
                record["packageDisplayName"] = template_names.get(str(record.get("templateId", "")), "VisionEval model")
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
                if datastore.get("role") == "baseline" and datastore.get("verification") == "verified":
                    project.setdefault("baseline", {"strategy": "fresh"}).update({
                        "strategy": "existing", "datastoreId": datastore["id"],
                        "compatibility": "verified", "warning": "",
                    })
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
