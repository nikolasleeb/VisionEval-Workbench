from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from .region_packages import RegionPackageService, SAFE_PACKAGE_ID, file_sha256, safe_package_path
from .workspace import Workspace, WorkspaceError, fingerprint_tree, now_iso, read_json, write_json


class ModelPackageService:
    """Install a checked model template and InputLibrary as one optional package."""

    def __init__(self, workspace: Workspace):
        self.workspace = workspace

    def _manifest(self, root: Path) -> dict[str, Any]:
        manifest = read_json(root / "workbench-package.json", {})
        if manifest.get("type") != "model-bundle":
            raise WorkspaceError("Package manifest type must be model-bundle")
        package_id = str(manifest.get("id", "")).strip()
        if not SAFE_PACKAGE_ID.match(package_id):
            raise WorkspaceError("Model package id must use lowercase letters, numbers, dots, hyphens, or underscores")
        for key in ("name", "version"):
            if not str(manifest.get(key, "")).strip():
                raise WorkspaceError(f"Model package {key} is required")
        library = manifest.get("inputLibrary") or {}
        template = manifest.get("modelTemplate") or {}
        for label, record in (("InputLibrary", library), ("model template", template)):
            if not str(record.get("id", "")).strip() or not str(record.get("path", "")).strip():
                raise WorkspaceError(f"Model package {label} id and path are required")
        files = manifest.get("files")
        if not isinstance(files, list) or not files:
            raise WorkspaceError("Model package must contain a checked file inventory")
        seen: set[str] = set()
        for record in files:
            relative = str(record.get("path", "")) if isinstance(record, dict) else ""
            if relative in seen:
                raise WorkspaceError("Model package lists a file more than once")
            seen.add(relative)
            path = safe_package_path(root, relative)
            if not path.is_file():
                raise WorkspaceError(f"Model package file is missing: {relative}")
            if path.stat().st_size != int(record.get("size", -1)) or file_sha256(path) != record.get("sha256"):
                raise WorkspaceError(f"Model package verification failed for {relative}")
        actual = {
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
            if path.is_file() and path.name != "workbench-package.json"
        }
        if actual != seen:
            raise WorkspaceError("Model package file inventory does not match its contents")
        library_path = safe_package_path(root, str(library["path"]))
        template_path = safe_package_path(root, str(template["path"]))
        if not library_path.is_dir() or not any(library_path.glob("*.csv")):
            raise WorkspaceError("Model package InputLibrary contains no CSV files")
        validation = self.workspace.validate_template(template_path)
        if not validation["valid"]:
            raise WorkspaceError("Model package template is invalid: " + "; ".join(validation["errors"]))
        map_record = manifest.get("comparisonMap") or {}
        if map_record:
            context_path = safe_package_path(root, str(map_record.get("path", "")))
            context_manifest = read_json(context_path / "workbench-map-context.json", {})
            if (
                context_manifest.get("type") != "map-context"
                or not SAFE_PACKAGE_ID.match(str(context_manifest.get("id", "")))
                or not context_manifest.get("comparisonMap", {}).get("enabled")
            ):
                raise WorkspaceError("Model package map context is missing or invalid")
        return manifest

    def install(self, source: str | Path) -> dict[str, Any]:
        package_root, temp = RegionPackageService._package_source(source)
        try:
            manifest = self._manifest(package_root)
            library = manifest["inputLibrary"]
            template = manifest["modelTemplate"]
            library_target = self.workspace.input_library / str(library["id"])
            template_target = self.workspace.templates / str(template["id"])
            map_record = manifest.get("comparisonMap") or {}
            map_source = safe_package_path(package_root, str(map_record["path"])) if map_record else None
            map_manifest = read_json(map_source / "workbench-map-context.json", {}) if map_source else {}
            map_target = self.workspace.map_contexts / str(map_manifest.get("id", "")) if map_source else None
            existing = [path.name for path in (library_target, template_target) if path.exists()]
            if existing:
                raise WorkspaceError("PlanRVA assets are already installed: " + ", ".join(existing))

            library_stage = Path(tempfile.mkdtemp(prefix=f".{library_target.name}.", dir=library_target.parent))
            template_stage = Path(tempfile.mkdtemp(prefix=f".{template_target.name}.", dir=template_target.parent))
            map_stage = Path(tempfile.mkdtemp(prefix=".map-context.", dir=self.workspace.map_contexts)) if map_source and map_target and not map_target.exists() else None
            moved: list[Path] = []
            try:
                shutil.copytree(safe_package_path(package_root, str(library["path"])), library_stage / "payload")
                shutil.copytree(safe_package_path(package_root, str(template["path"])), template_stage / "payload")
                if map_stage and map_source:
                    shutil.copytree(map_source, map_stage / "payload")
                os.replace(library_stage / "payload", library_target)
                moved.append(library_target)
                os.replace(template_stage / "payload", template_target)
                moved.append(template_target)
                if map_stage and map_target:
                    os.replace(map_stage / "payload", map_target)
                    moved.append(map_target)
            except Exception:
                for path in reversed(moved):
                    shutil.rmtree(path, ignore_errors=True)
                raise
            finally:
                shutil.rmtree(library_stage, ignore_errors=True)
                shutil.rmtree(template_stage, ignore_errors=True)
                if map_stage:
                    shutil.rmtree(map_stage, ignore_errors=True)

            settings = self.workspace.settings()
            if not settings.get("defaultInputLibraryId"):
                settings["defaultInputLibraryId"] = library["id"]
            if not settings.get("defaultTemplateId"):
                settings["defaultTemplateId"] = template["id"]
            write_json(self.workspace.settings_path, settings)
            installed_at = now_iso()
            self.workspace.record_asset_registration({
                "id": manifest["id"],
                "type": "model-bundle",
                "version": manifest["version"],
                "installedAt": installed_at,
                "assets": [
                    {"kind": "input-library", "id": library["id"]},
                    {"kind": "model-template", "id": template["id"]},
                ],
            })
            return {
                "id": manifest["id"],
                "name": manifest["name"],
                "version": manifest["version"],
                "installedAt": installed_at,
                "fingerprint": fingerprint_tree(package_root),
                "inputLibrary": {"id": library["id"], "name": library.get("name", library["id"])},
                "modelTemplate": {"id": template["id"], "name": template.get("name", template["id"])},
            }
        finally:
            if temp:
                temp.cleanup()
