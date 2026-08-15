from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from .workspace import Workspace, WorkspaceError, fingerprint_tree, now_iso, read_json, write_json


SAFE_PACKAGE_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{0,79}$")


def package_root(source: str | Path) -> Path:
    """Resolve an unpacked package root without accepting ambiguous trees."""
    root = Path(source).expanduser().resolve()
    if not root.is_dir():
        raise WorkspaceError("Choose a Workbench package folder or .zip file")
    manifests = [item for item in root.rglob("workbench-package.json") if item.is_file()]
    if len(manifests) != 1:
        raise WorkspaceError("Package folder must contain exactly one workbench-package.json")
    manifest = manifests[0]
    try:
        relative = manifest.relative_to(root)
    except ValueError as exc:
        raise WorkspaceError("Package folder contains an unsafe manifest path") from exc
    if manifest.is_symlink() or len(relative.parts) > 2:
        raise WorkspaceError("Package manifest must be at the selected folder root or in one wrapper folder")
    return manifest.parent


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def safe_package_path(root: Path, value: str) -> Path:
    pure = PurePosixPath(value)
    if not value or pure.is_absolute() or ".." in pure.parts:
        raise WorkspaceError("Regional package manifest contains an unsafe file path")
    path = root.joinpath(*pure.parts).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise WorkspaceError("Regional package manifest contains an unsafe file path") from exc
    return path


def package_manifest_type(source: str | Path) -> str:
    path = Path(source).expanduser().resolve()
    if path.is_dir():
        return str(read_json(package_root(path) / "workbench-package.json", {}).get("type", ""))
    if path.is_file() and path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            manifests = [name for name in archive.namelist() if PurePosixPath(name).name == "workbench-package.json"]
            if len(manifests) != 1:
                raise WorkspaceError("Package zip must contain one workbench-package.json")
            pure = PurePosixPath(manifests[0])
            if pure.is_absolute() or ".." in pure.parts:
                raise WorkspaceError("Package zip contains an unsafe file path")
            return str(json.loads(archive.read(manifests[0])).get("type", ""))
    raise WorkspaceError("Choose a Workbench package folder or .zip file")


class RegionPackageService:
    def __init__(self, workspace: Workspace):
        self.workspace = workspace
        self._migrate_template_map_contexts()

    def _migrate_template_map_contexts(self) -> None:
        """Move legacy map metadata out of model templates before VisionEval sees it."""
        for template in self.workspace.templates.iterdir():
            legacy = template / ".workbench-map-context"
            if not legacy.is_dir():
                continue
            manifest = read_json(legacy / "workbench-map-context.json", {})
            context_id = str(manifest.get("id", "")).strip()
            if manifest.get("type") != "map-context" or not SAFE_PACKAGE_ID.match(context_id):
                continue
            target = self.workspace.map_contexts / context_id
            if not target.exists():
                os.replace(legacy, target)
            else:
                shutil.rmtree(legacy)

    @staticmethod
    def _package_source(source: str | Path) -> tuple[Path, tempfile.TemporaryDirectory[str] | None]:
        path = Path(source).expanduser().resolve()
        if path.is_dir():
            return package_root(path), None
        if path.is_file() and path.suffix.lower() == ".zip":
            temp = tempfile.TemporaryDirectory()
            with zipfile.ZipFile(path) as archive:
                for info in archive.infolist():
                    pure = PurePosixPath(info.filename)
                    if pure.is_absolute() or ".." in pure.parts:
                        raise WorkspaceError("Package zip contains an unsafe file path")
                archive.extractall(temp.name)
            return package_root(Path(temp.name)), temp
        raise WorkspaceError("Choose a regional package folder or .zip file")

    def _manifest(self, root: Path) -> dict[str, Any]:
        manifest = read_json(root / "workbench-package.json", {})
        if manifest.get("type") != "region-builder":
            raise WorkspaceError("Package manifest type must be region-builder")
        package_id = str(manifest.get("id", "")).strip()
        if not SAFE_PACKAGE_ID.match(package_id):
            raise WorkspaceError("Regional package id must use lowercase letters, numbers, dots, hyphens, or underscores")
        for key in ("name", "version", "coverage"):
            if not str(manifest.get(key, "")).strip():
                raise WorkspaceError(f"Regional package {key} is required")
        builder = manifest.get("builder") or {}
        if builder.get("kind") != "mpo-bzone-crosswalk":
            raise WorkspaceError("Unsupported regional package builder kind")
        required = {
            str(manifest.get("inputLibrary", {}).get("path", "")),
            str(builder.get("regionsPath", "")),
            str(builder.get("crosswalkPath", "")),
            str(manifest.get("sourcesDocument", "")),
        }
        model_template_path = str(builder.get("modelTemplatePath", "")).strip()
        if model_template_path:
            required.add(model_template_path)
        if "" in required:
            raise WorkspaceError("Regional package must define its InputLibrary, regions, crosswalk, and sources document")
        files = manifest.get("files")
        if not isinstance(files, list) or not files:
            raise WorkspaceError("Regional package must contain a checked file inventory")
        seen: set[str] = set()
        for record in files:
            relative = str(record.get("path", "")) if isinstance(record, dict) else ""
            if relative in seen:
                raise WorkspaceError("Regional package lists a file more than once")
            seen.add(relative)
            path = safe_package_path(root, relative)
            if not path.is_file():
                raise WorkspaceError(f"Regional package file is missing: {relative}")
            if path.stat().st_size != int(record.get("size", -1)):
                raise WorkspaceError(f"Regional package file size does not match: {relative}")
            if file_sha256(path) != record.get("sha256"):
                raise WorkspaceError(f"Regional package file checksum does not match: {relative}")
        for relative in required:
            path = safe_package_path(root, relative)
            if not path.exists():
                raise WorkspaceError(f"Regional package resource is missing: {relative}")
        input_path = safe_package_path(root, str(manifest["inputLibrary"]["path"]))
        for filename in manifest["inputLibrary"].get("requiredFiles", []):
            if not (input_path / str(filename)).is_file():
                raise WorkspaceError(f"Regional package InputLibrary is missing {filename}")
        if model_template_path:
            template_path = safe_package_path(root, model_template_path)
            for relative in ("visioneval.cnf", "scripts/run_model.R", "defs/units.csv", "defs/deflators.csv"):
                if not (template_path / relative).is_file():
                    raise WorkspaceError(f"Regional package model template is missing {relative}")
        return manifest

    def install(self, source: str | Path) -> dict[str, Any]:
        package_root, temp = self._package_source(source)
        try:
            manifest = self._manifest(package_root)
            target = self.workspace.region_packages / manifest["id"]
            if target.exists():
                raise WorkspaceError(f"Regional package is already installed: {manifest['name']}")
            staging = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=self.workspace.region_packages))
            try:
                shutil.copytree(package_root, staging / "payload")
                installed = {
                    "schemaVersion": 1,
                    "id": manifest["id"],
                    "name": manifest["name"],
                    "type": "region-builder",
                    "packageVersion": manifest["version"],
                    "coverage": manifest["coverage"],
                    "description": manifest.get("description", ""),
                    "retrievedAt": manifest.get("retrievedAt", ""),
                    "installedAt": now_iso(),
                    "source": str(Path(source).expanduser()),
                    "fingerprint": fingerprint_tree(staging / "payload"),
                }
                write_json(staging / "payload" / "installed-package.json", installed)
                os.replace(staging / "payload", target)
            finally:
                shutil.rmtree(staging, ignore_errors=True)
            self.workspace.record_asset_registration({
                "id": manifest["id"], "type": "region-builder", "version": manifest["version"], "installedAt": now_iso(),
            })
            return self.record(manifest["id"])
        finally:
            if temp:
                temp.cleanup()

    def list(self) -> list[dict[str, Any]]:
        records = []
        for path in sorted((item for item in self.workspace.region_packages.iterdir() if item.is_dir()), key=lambda item: item.name.lower()):
            manifest = read_json(path / "workbench-package.json", {})
            installed = read_json(path / "installed-package.json", {})
            if manifest.get("type") == "region-builder":
                records.append({
                    "id": manifest.get("id", path.name),
                    "name": manifest.get("name", path.name),
                    "version": manifest.get("version", ""),
                    "coverage": manifest.get("coverage", ""),
                    "description": manifest.get("description", ""),
                    "retrievedAt": manifest.get("retrievedAt", ""),
                    "installedAt": installed.get("installedAt", ""),
                    "comparisonMap": manifest.get("comparisonMap", {}),
                })
        return records

    def comparison_map_providers(self) -> list[dict[str, Any]]:
        """Return regional packages and model-package map contexts."""
        providers: list[dict[str, Any]] = []
        installed_templates = {item.name for item in self.workspace.templates.iterdir() if item.is_dir()}
        for context_root in sorted((item for item in self.workspace.map_contexts.iterdir() if item.is_dir()), key=lambda item: item.name.lower()):
            manifest = read_json(context_root / "workbench-map-context.json", {})
            comparison_map = manifest.get("comparisonMap", {})
            if manifest.get("type") != "map-context" or not comparison_map.get("enabled"):
                continue
            compatible_templates = manifest.get("compatibleTemplateIds", [])
            if compatible_templates and not installed_templates.intersection(compatible_templates):
                continue
            providers.append({
                "id": manifest.get("id", context_root.name),
                "name": manifest.get("name", "Model map context"),
                "version": manifest.get("version", ""),
                "coverage": manifest.get("coverage", ""),
                "description": manifest.get("description", ""),
                "comparisonMap": comparison_map,
                "compatibleTemplateIds": compatible_templates,
                "componentOf": manifest.get("componentOf", ""),
                "embedded": True,
            })
        providers.extend(record for record in self.list() if record.get("comparisonMap", {}).get("enabled"))
        return providers

    def comparison_map_context(self, package_id: str) -> tuple[Path, dict[str, Any]]:
        for context_root in self.workspace.map_contexts.iterdir():
            if not context_root.is_dir():
                continue
            manifest = read_json(context_root / "workbench-map-context.json", {})
            if manifest.get("type") == "map-context" and manifest.get("id") == package_id:
                return context_root, manifest
        root = self.root(package_id)
        return root, self.manifest(package_id)

    def root(self, package_id: str) -> Path:
        path = self.workspace.within(self.workspace.region_packages / package_id, self.workspace.region_packages)
        if read_json(path / "workbench-package.json", {}).get("id") != package_id:
            raise WorkspaceError("Unknown regional package")
        return path

    def manifest(self, package_id: str) -> dict[str, Any]:
        return self._manifest(self.root(package_id))

    def record(self, package_id: str) -> dict[str, Any]:
        return next((item for item in self.list() if item["id"] == package_id), {})

    def remove(self, package_id: str) -> dict[str, Any]:
        record = self.record(package_id)
        if not record:
            raise WorkspaceError("Unknown regional package")
        shutil.rmtree(self.root(package_id))
        return {"removed": record}
