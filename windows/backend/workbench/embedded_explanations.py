from __future__ import annotations

import hashlib, json, os, shutil, tempfile
from pathlib import Path, PurePosixPath
from typing import Any
from .workspace import Workspace, WorkspaceError, now_iso, read_json, write_json


def _catalog_fingerprint(catalog: dict[str, Any]) -> str:
    explanations = {
        str(key): {"html": str(value.get("html", ""))} if isinstance(value, dict) else value
        for key, value in (catalog.get("explanations") or {}).items()
    }
    content = {"variables": catalog.get("variables") or {}, "inputFields": catalog.get("inputFields") or {}, "explanations": explanations}
    return hashlib.sha256(json.dumps(content, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _component(package_root: Path, manifest: dict[str, Any]) -> dict[str, Any] | None:
    item = manifest.get("inputExplanations") or {}
    if not item:
        return None
    for key in ("id", "name", "version", "path"):
        if not str(item.get(key, "")).strip():
            raise WorkspaceError(f"Embedded input explanations {key} is required")
    pure = PurePosixPath(str(item["path"]))
    if pure.is_absolute() or ".." in pure.parts:
        raise WorkspaceError("Embedded input explanations use an unsafe catalog path")
    path = package_root.joinpath(*pure.parts).resolve()
    try:
        path.relative_to(package_root.resolve())
    except ValueError as exc:
        raise WorkspaceError("Embedded input explanations use an unsafe catalog path") from exc
    catalog = read_json(path, {})
    if not path.is_file() or not isinstance(catalog.get("explanations"), dict) or not catalog["explanations"]:
        raise WorkspaceError("Embedded input explanation catalog is missing or empty")
    if int(item.get("fileCount", 0)) != len(catalog.get("coveredFiles") or []):
        raise WorkspaceError("Embedded input explanation file count does not match its catalog")
    return {**item, "catalogPath": path, "catalog": catalog}


def validate_embedded_explanations(package_root: Path, manifest: dict[str, Any]) -> dict[str, Any] | None:
    return _component(package_root, manifest)


def install_embedded_explanations(workspace: Workspace, package_root: Path, manifest: dict[str, Any], source: str | Path) -> dict[str, Any] | None:
    item = _component(package_root, manifest)
    if not item:
        return None
    target = workspace.input_explanations / str(item["id"])
    catalog_fingerprint = _catalog_fingerprint(item["catalog"])
    family_id = str(item.get("familyId") or ("virginia-visioneval-input-explanations" if item.get("appliesTo", {}).get("state") == "VA" else item["id"]))
    provider = {
        "packageId": str(manifest.get("id", "")), "packageName": str(manifest.get("name", "")),
        "packageType": str(manifest.get("type", "")), "coverage": str(manifest.get("coverage") or manifest.get("state") or ""),
        "precedence": 100 if manifest.get("id") == "virginia-mpo-regions" else 50,
        "installedAt": now_iso(), "explanationName": str(item["name"]), "source": str(Path(source).expanduser()),
    }
    if target.exists():
        record = read_json(target / "workbench-package.json", {})
        existing_fingerprint = record.get("catalogFingerprint") or _catalog_fingerprint(read_json(target / "catalog.json", {}))
        if existing_fingerprint != catalog_fingerprint or (record.get("familyId") or family_id) != family_id:
            target = workspace.input_explanations / f"{item['id']}--{catalog_fingerprint[:10]}"
            if target.exists():
                raise WorkspaceError(f"Different input explanations are already installed: {item['name']}")
        else:
            providers = [value for value in record.get("providers", []) if value.get("packageId") != provider["packageId"]]
            providers.append(provider)
            preferred = max(providers, key=lambda value: int(value.get("precedence", 0)))
            record.update({"familyId": family_id, "catalogFingerprint": catalog_fingerprint, "providers": providers, "preferredProvider": preferred})
            if preferred["packageId"] == provider["packageId"]:
                record.update({"name": item["name"], "source": str(Path(source).expanduser()), "componentOf": manifest.get("id", "")})
            write_json(target / "workbench-package.json", record)
            return record
    stage = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=workspace.input_explanations))
    try:
        shutil.copy2(item["catalogPath"], stage / "catalog.json")
        record = {"version": 1, "type": "input-explanations", "id": target.name, "name": item["name"], "packageVersion": item["version"], "description": item["catalog"].get("package", {}).get("description", ""), "appliesTo": item.get("appliesTo", {}), "source": str(Path(source).expanduser()), "componentOf": manifest.get("id", ""), "installedAt": now_iso(), "fileCount": int(item["fileCount"]), "familyId": family_id, "catalogFingerprint": catalog_fingerprint, "providers": [provider], "preferredProvider": provider}
        write_json(stage / "workbench-package.json", record)
        os.replace(stage, target)
    finally:
        if stage.exists(): shutil.rmtree(stage, ignore_errors=True)
    workspace.record_asset_registration({"id": item["id"], "type": "input-explanations", "version": item["version"], "installedAt": now_iso(), "componentOf": manifest.get("id", "")})
    return record
