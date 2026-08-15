from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

from .workspace import Workspace, WorkspaceError, now_iso, read_json, write_json


PLANRVA_ASSET_ID = "planrva-mm-v1"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


class BundledAssetService:
    def __init__(self, workspace: Workspace, resource_root: str | Path):
        self.workspace = workspace
        resource_root = Path(resource_root).resolve()
        candidates = (
            resource_root / "bundled_assets" / "planrva-mm",
            resource_root.parent / "resources" / "examples" / "planrva-mm",
        )
        self.root = next((candidate for candidate in candidates if (candidate / "manifest.json").is_file()), candidates[0])
        self._status: dict[str, Any] = self.status()

    @property
    def manifest_path(self) -> Path:
        return self.root / "manifest.json"

    def manifest(self) -> dict[str, Any]:
        manifest = read_json(self.manifest_path, {})
        if manifest.get("id") != PLANRVA_ASSET_ID:
            raise WorkspaceError("The bundled PlanRVA example manifest is missing or invalid")
        return manifest

    def verify(self) -> dict[str, Any]:
        manifest = self.manifest()
        seen: set[str] = set()
        for record in manifest.get("files", []):
            relative = str(record.get("path", ""))
            pure = PurePosixPath(relative)
            if not relative or pure.is_absolute() or ".." in pure.parts or relative in seen:
                raise WorkspaceError("The bundled PlanRVA example contains an unsafe file path")
            seen.add(relative)
            path = self.root.joinpath(*pure.parts).resolve()
            try:
                path.relative_to(self.root.resolve())
            except ValueError as exc:
                raise WorkspaceError("The bundled PlanRVA example contains an unsafe file path") from exc
            if not path.is_file() or path.stat().st_size != int(record.get("size", -1)) or file_sha256(path) != record.get("sha256"):
                raise WorkspaceError(f"Bundled PlanRVA example verification failed for {relative}")
        actual = {
            path.relative_to(self.root).as_posix()
            for path in self.root.rglob("*") if path.is_file() and path != self.manifest_path
        }
        if actual != seen:
            raise WorkspaceError("The bundled PlanRVA example file inventory does not match its manifest")
        return manifest

    def status(self) -> dict[str, Any]:
        manifest = read_json(self.manifest_path, {})
        template_id = manifest.get("modelTemplate", {}).get("id", "template-planrva-mm-8f140cd4cb")
        library_id = manifest.get("inputLibrary", {}).get("id", "PlanRVA MM")
        return {
            "id": PLANRVA_ASSET_ID,
            "name": manifest.get("name", "PlanRVA MM Example"),
            "available": self.manifest_path.is_file(),
            "inputLibraryInstalled": (self.workspace.input_library / library_id).is_dir(),
            "modelTemplateInstalled": (self.workspace.templates / template_id).is_dir(),
            "manifestSha256": file_sha256(self.manifest_path) if self.manifest_path.is_file() else "",
            "message": self._status.get("message", "") if hasattr(self, "_status") else "",
        }

    @staticmethod
    def _copy_transactionally(source: Path, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=target.parent))
        try:
            shutil.copytree(source, temporary / "payload")
            os.replace(temporary / "payload", target)
        finally:
            shutil.rmtree(temporary, ignore_errors=True)

    def install_planrva(self, automatic: bool = False) -> dict[str, Any]:
        manifest = self.verify()
        library_id = manifest["inputLibrary"]["id"]
        template_id = manifest["modelTemplate"]["id"]
        targets = (
            ("InputLibrary", self.root / "input-library", self.workspace.input_library / library_id),
            ("ModelTemplate", self.root / "model-template", self.workspace.templates / template_id),
        )
        installed: list[str] = []
        preserved: list[str] = []
        for label, source, target in targets:
            if target.exists():
                preserved.append(label)
                continue
            self._copy_transactionally(source, target)
            installed.append(label)
        validation = self.workspace.validate_template(self.workspace.templates / template_id)
        if not validation["valid"]:
            raise WorkspaceError("The bundled PlanRVA model failed validation: " + "; ".join(validation["errors"]))
        map_record = manifest.get("comparisonMap") or {}
        map_source = self.root / str(map_record.get("path", ""))
        map_manifest = read_json(map_source / "workbench-map-context.json", {}) if map_source.is_dir() else {}
        map_target = self.workspace.map_contexts / str(map_manifest.get("id", ""))
        if map_record and map_source.is_dir() and not map_target.exists():
            self._copy_transactionally(map_source, map_target)
        settings = self.workspace.settings()
        if not settings.get("defaultTemplateId"):
            settings["defaultTemplateId"] = template_id
        if not settings.get("defaultInputLibraryId"):
            settings["defaultInputLibraryId"] = library_id
        write_json(self.workspace.settings_path, settings)
        self.workspace.record_asset_registration({
            "id": PLANRVA_ASSET_ID,
            "version": manifest["version"],
            "manifestSha256": file_sha256(self.manifest_path),
            "installedAt": now_iso(),
            "automatic": automatic,
        })
        result = {
            **self.status(),
            "installed": installed,
            "preserved": preserved,
            "message": "PlanRVA example is ready." if installed else "Existing PlanRVA assets were preserved.",
        }
        self._status = result
        return result

    def seed_new_workspace(self) -> dict[str, Any]:
        return self.status()
