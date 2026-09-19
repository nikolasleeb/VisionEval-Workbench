from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

from .workspace import Workspace, WorkspaceError, now_iso, read_json, write_json


def _catalog_path(package_root: Path, component: dict[str, Any]) -> Path:
    relative = str(component.get("path", "")).strip()
    pure = PurePosixPath(relative)
    if not relative or pure.is_absolute() or ".." in pure.parts:
        raise WorkspaceError("Embedded input explanations use an unsafe catalog path")
    path = package_root.joinpath(*pure.parts).resolve()
    try:
        path.relative_to(package_root.resolve())
    except ValueError as exc:
        raise WorkspaceError("Embedded input explanations use an unsafe catalog path") from exc
    return path


def validate_embedded_explanations(package_root: Path, manifest: dict[str, Any]) -> dict[str, Any] | None:
    component = manifest.get("inputExplanations") or {}
    if not component:
        return None
    for key in ("id", "name", "version", "path"):
        if not str(component.get(key, "")).strip():
            raise WorkspaceError(f"Embedded input explanations {key} is required")
    catalog_path = _catalog_path(package_root, component)
    catalog = read_json(catalog_path, {})
    explanations = catalog.get("explanations")
    if not catalog_path.is_file() or not isinstance(explanations, dict) or not explanations:
        raise WorkspaceError("Embedded input explanation catalog is missing or empty")
    declared = int(component.get("fileCount", len(explanations)))
    covered = catalog.get("coveredFiles") or []
    if declared != len(covered):
        raise WorkspaceError("Embedded input explanation file count does not match its catalog")
    return {**component, "catalogPath": catalog_path, "catalog": catalog}


def install_embedded_explanations(
    workspace: Workspace,
    package_root: Path,
    manifest: dict[str, Any],
    source: str | Path,
) -> dict[str, Any] | None:
    component = validate_embedded_explanations(package_root, manifest)
    if not component:
        return None
    package_id = str(component["id"])
    target = workspace.input_explanations / package_id
    catalog = component["catalog"]
    if target.exists():
        existing = read_json(target / "catalog.json", {})
        if existing != catalog:
            raise WorkspaceError(f"Different input explanations are already installed: {component['name']}")
        return read_json(target / "workbench-package.json", {})

    staging = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=workspace.input_explanations))
    try:
        shutil.copy2(component["catalogPath"], staging / "catalog.json")
        record = {
            "version": 1,
            "type": "input-explanations",
            "id": package_id,
            "name": component["name"],
            "packageVersion": component["version"],
            "description": catalog.get("package", {}).get("description", ""),
            "appliesTo": component.get("appliesTo", {}),
            "source": str(Path(source).expanduser()),
            "componentOf": manifest.get("id", ""),
            "installedAt": now_iso(),
            "fileCount": int(component["fileCount"]),
        }
        write_json(staging / "workbench-package.json", record)
        os.replace(staging, target)
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
    workspace.record_asset_registration({
        "id": package_id,
        "type": "input-explanations",
        "version": component["version"],
        "installedAt": now_iso(),
        "componentOf": manifest.get("id", ""),
    })
    return record
