from __future__ import annotations

import os, shutil, tempfile
from pathlib import Path, PurePosixPath
from typing import Any
from .workspace import Workspace, WorkspaceError, now_iso, read_json, write_json


def _component(package_root: Path, manifest: dict[str, Any]) -> dict[str, Any] | None:
    item = manifest.get("inputExplanations") or {}
    if not item: return None
    for key in ("id", "name", "version", "path"):
        if not str(item.get(key, "")).strip(): raise WorkspaceError(f"Embedded input explanations {key} is required")
    pure = PurePosixPath(str(item["path"]))
    if pure.is_absolute() or ".." in pure.parts: raise WorkspaceError("Embedded input explanations use an unsafe catalog path")
    path = package_root.joinpath(*pure.parts).resolve()
    try: path.relative_to(package_root.resolve())
    except ValueError as exc: raise WorkspaceError("Embedded input explanations use an unsafe catalog path") from exc
    catalog = read_json(path, {})
    if not path.is_file() or not isinstance(catalog.get("explanations"), dict) or not catalog["explanations"]: raise WorkspaceError("Embedded input explanation catalog is missing or empty")
    if int(item.get("fileCount", 0)) != len(catalog.get("coveredFiles") or []): raise WorkspaceError("Embedded input explanation file count does not match its catalog")
    return {**item, "catalogPath": path, "catalog": catalog}


def validate_embedded_explanations(package_root: Path, manifest: dict[str, Any]) -> dict[str, Any] | None:
    return _component(package_root, manifest)


def install_embedded_explanations(workspace: Workspace, package_root: Path, manifest: dict[str, Any], source: str | Path) -> dict[str, Any] | None:
    item = _component(package_root, manifest)
    if not item: return None
    target = workspace.input_explanations / str(item["id"])
    if target.exists():
        if read_json(target / "catalog.json", {}) != item["catalog"]: raise WorkspaceError(f"Different input explanations are already installed: {item['name']}")
        return read_json(target / "workbench-package.json", {})
    stage = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=workspace.input_explanations))
    try:
        shutil.copy2(item["catalogPath"], stage / "catalog.json")
        record = {"version": 1, "type": "input-explanations", "id": item["id"], "name": item["name"], "packageVersion": item["version"], "description": item["catalog"].get("package", {}).get("description", ""), "appliesTo": item.get("appliesTo", {}), "source": str(Path(source).expanduser()), "componentOf": manifest.get("id", ""), "installedAt": now_iso(), "fileCount": int(item["fileCount"])}
        write_json(stage / "workbench-package.json", record); os.replace(stage, target)
    finally:
        if stage.exists(): shutil.rmtree(stage, ignore_errors=True)
    workspace.record_asset_registration({"id": item["id"], "type": "input-explanations", "version": item["version"], "installedAt": now_iso(), "componentOf": manifest.get("id", "")})
    return record
