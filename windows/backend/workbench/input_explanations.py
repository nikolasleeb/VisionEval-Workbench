from __future__ import annotations

import html
import json
import os
import re
import shutil
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath
from typing import Any

from .explore import _strip_explanation_header
from .region_packages import RegionPackageService
from .workspace import Workspace, WorkspaceError, fingerprint_tree, now_iso, read_json, write_json


W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
SAFE_PACKAGE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_. -]{0,79}$")


def _file_sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _text(element: ET.Element) -> str:
    return "".join(node.text or "" for node in element.iter(f"{W_NS}t")).strip()


def _render_docx(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    body = root.find(f"{W_NS}body")
    chunks: list[str] = []
    for child in body or []:
        if child.tag == f"{W_NS}p":
            value = _text(child)
            if not value:
                continue
            style = child.find(f".//{W_NS}pStyle")
            style_name = style.attrib.get(f"{W_NS}val", "") if style is not None else ""
            tag = "h3" if style_name.lower().startswith("heading") else "p"
            chunks.append(f"<{tag}>{html.escape(value)}</{tag}>")
        elif child.tag == f"{W_NS}tbl":
            rows = []
            for row in child.findall(f"{W_NS}tr"):
                cells = [f"<td>{html.escape(_text(cell))}</td>" for cell in row.findall(f"{W_NS}tc")]
                if cells:
                    rows.append(f"<tr>{''.join(cells)}</tr>")
            if rows:
                chunks.append(f"<table>{''.join(rows)}</table>")
    return _strip_explanation_header("\n".join(chunks))


def _render_markdown(path: Path) -> str:
    chunks: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("### "):
            chunks.append(f"<h3>{html.escape(line[4:].strip())}</h3>")
        elif line.startswith("## "):
            chunks.append(f"<h3>{html.escape(line[3:].strip())}</h3>")
        elif line.startswith("# "):
            chunks.append(f"<h3>{html.escape(line[2:].strip())}</h3>")
        else:
            chunks.append(f"<p>{html.escape(line)}</p>")
    return _strip_explanation_header("\n".join(chunks))


def _render_html(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    # Keep the current renderer simple and deterministic: package authors may
    # use basic HTML, but scripts and inline event handlers are not preserved.
    raw = re.sub(r"(?is)<script\b.*?</script>", "", raw)
    raw = re.sub(r"\s+on[a-z]+\s*=\s*(['\"]).*?\1", "", raw)
    return _strip_explanation_header(raw.strip())


def _document_key(path: Path) -> str:
    stem = re.sub(r"^\d+_\s*", "", path.stem).strip().lower()
    if stem.endswith(".csv"):
        stem = stem[:-4]
    return stem


def _safe_manifest_path(root: Path, value: str) -> Path:
    pure = PurePosixPath(value)
    if not value or pure.is_absolute() or ".." in pure.parts:
        raise WorkspaceError("Package manifest contains an unsafe file path")
    path = root.joinpath(*pure.parts).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise WorkspaceError("Package manifest contains an unsafe file path") from exc
    return path


class InputExplanationPackageService:
    def __init__(self, workspace: Workspace):
        self.workspace = workspace

    @staticmethod
    def _package_source(source: str | Path):
        return RegionPackageService._package_source(source)

    def _manifest(self, root: Path) -> dict[str, Any]:
        manifest = read_json(root / "workbench-package.json", {})
        if manifest.get("type") != "input-explanations":
            raise WorkspaceError("Package manifest type must be input-explanations")
        package_id = str(manifest.get("id", "")).strip()
        if not SAFE_PACKAGE_ID.match(package_id):
            raise WorkspaceError("Package manifest id must be a simple name")
        if not str(manifest.get("name", "")).strip():
            raise WorkspaceError("Package manifest name is required")
        files = manifest.get("files")
        if not isinstance(files, list) or not files:
            raise WorkspaceError("Package manifest must list explanation files")
        seen: set[str] = set()
        for record in files:
            if not isinstance(record, dict):
                raise WorkspaceError("Package file entries must be objects")
            relative = str(record.get("path", ""))
            if relative in seen:
                raise WorkspaceError("Package manifest lists a file more than once")
            seen.add(relative)
            path = _safe_manifest_path(root, relative)
            if not path.is_file():
                raise WorkspaceError(f"Package file is missing: {relative}")
            expected_size = record.get("size")
            expected_hash = record.get("sha256")
            if expected_size is not None and path.stat().st_size != int(expected_size):
                raise WorkspaceError(f"Package file size does not match: {relative}")
            if expected_hash and _file_sha256(path) != expected_hash:
                raise WorkspaceError(f"Package file checksum does not match: {relative}")
        return manifest

    def _catalog(self, root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
        explanations: dict[str, dict[str, str]] = {}
        for record in manifest["files"]:
            relative = str(record["path"])
            path = _safe_manifest_path(root, relative)
            suffix = path.suffix.lower()
            if suffix == ".docx":
                rendered = _render_docx(path)
            elif suffix in {".md", ".markdown"}:
                rendered = _render_markdown(path)
            elif suffix in {".html", ".htm"}:
                rendered = _render_html(path)
            elif suffix == ".json":
                payload = read_json(path, {})
                if isinstance(payload, dict) and payload.get("explanations"):
                    explanations.update(payload.get("explanations") or {})
                continue
            else:
                raise WorkspaceError(f"Unsupported explanation file type: {relative}")
            key = str(record.get("key") or _document_key(path)).strip().lower()
            explanations[key] = {"document": relative, "html": rendered}
        return {
            "version": 1,
            "package": {
                "id": manifest["id"],
                "name": manifest["name"],
                "version": manifest.get("version", ""),
                "description": manifest.get("description", ""),
                "appliesTo": manifest.get("appliesTo", {}),
            },
            "variables": manifest.get("variables", {}),
            "inputFields": manifest.get("inputFields", {}),
            "explanations": explanations,
        }

    def install(self, source: str | Path) -> dict[str, Any]:
        package_root, temp = self._package_source(source)
        try:
            manifest = self._manifest(package_root)
            catalog = self._catalog(package_root, manifest)
            target = self.workspace.input_explanations / manifest["id"]
            if target.exists():
                raise WorkspaceError(f"Input explanations are already installed: {manifest['name']}")
            staging = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=self.workspace.input_explanations))
            try:
                shutil.copytree(package_root, staging / "source")
                write_json(staging / "catalog.json", catalog)
                record = {
                    "version": 1,
                    "type": "input-explanations",
                    "id": manifest["id"],
                    "name": manifest["name"],
                    "packageVersion": manifest.get("version", ""),
                    "description": manifest.get("description", ""),
                    "appliesTo": manifest.get("appliesTo", {}),
                    "source": str(Path(source).expanduser()),
                    "installedAt": now_iso(),
                    "fingerprint": fingerprint_tree(staging / "source"),
                    "fileCount": len(catalog["explanations"]),
                }
                write_json(staging / "workbench-package.json", record)
                os.replace(staging, target)
            finally:
                if staging.exists():
                    shutil.rmtree(staging, ignore_errors=True)
            self.workspace.record_asset_registration({
                "id": manifest["id"],
                "type": "input-explanations",
                "version": manifest.get("version", ""),
                "installedAt": now_iso(),
            })
            return self.record(manifest["id"])
        finally:
            if temp:
                temp.cleanup()

    def list(self) -> list[dict[str, Any]]:
        records = []
        for path in sorted((p for p in self.workspace.input_explanations.iterdir() if p.is_dir()), key=lambda item: item.name.lower()):
            record = read_json(path / "workbench-package.json", {})
            if record:
                records.append(record)
        return records

    def record(self, package_id: str) -> dict[str, Any]:
        path = self.workspace.within(self.workspace.input_explanations / package_id, self.workspace.input_explanations)
        record = read_json(path / "workbench-package.json", {})
        if not record or record.get("id") != package_id:
            raise WorkspaceError("Unknown input explanations package")
        return record

    def catalog_path(self, package_id: str) -> Path | None:
        if not package_id:
            return None
        path = self.workspace.within(self.workspace.input_explanations / package_id / "catalog.json", self.workspace.input_explanations)
        if not path.is_file():
            raise WorkspaceError("Unknown input explanations package")
        return path

    def remove(self, package_id: str) -> dict[str, Any]:
        record = self.record(package_id)
        shutil.rmtree(self.workspace.input_explanations / package_id)
        return {"removed": record}
