from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


DOCUMENTATION_SCHEMA_VERSION = 2
WORKSPACE_MANIFEST = ".workbench-documentation.json"
MANAGED_GUIDE_DIRECTORY = "Workbench User Guide"
SOURCE_MANIFEST = "documentation.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _write_json(path: Path, payload: Any) -> None:
    data = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    _write_bytes(path, data)


class DocumentationService:
    """Install the packaged user guide without touching workspace-owned notes.

    The previous manifest is the authority for which paths Workbench owns. Unknown
    files are deliberately ignored, including files placed inside the guide folder.
    """

    def __init__(self, workspace_root: str | Path, resource_root: str | Path):
        self.workspace_root = Path(workspace_root).resolve()
        self.resource_root = Path(resource_root).resolve()
        self.documentation_root = self.workspace_root / "Documentation"
        self.guide_root = self.documentation_root / MANAGED_GUIDE_DIRECTORY
        self.manifest_path = self.documentation_root / WORKSPACE_MANIFEST

    def source_root(self) -> Path:
        candidates = (
            self.resource_root / "docs" / "user",
            self.resource_root.parent / "docs" / "user-macos",
            self.resource_root.parent / "docs" / "user",
        )
        for candidate in candidates:
            if (candidate / SOURCE_MANIFEST).is_file():
                return candidate.resolve()
        raise FileNotFoundError("The bundled Workbench user guide is missing")

    @staticmethod
    def _safe_relative(value: str) -> Path:
        posix = PurePosixPath(value)
        if posix.is_absolute() or ".." in posix.parts or not posix.parts:
            raise ValueError(f"Unsafe documentation path: {value}")
        return Path(*posix.parts)

    def _source_files(self, source: Path) -> list[Path]:
        metadata = self._source_metadata(source)
        if int(metadata.get("schemaVersion", 1)) >= 2:
            return [source / document["filename"] for document in self._documents(metadata, source)]
        files = []
        for path in sorted(source.rglob("*")):
            if path.is_file() and path.name != SOURCE_MANIFEST and not path.is_symlink():
                files.append(path)
        if not files or not (source / "README.md").is_file():
            raise ValueError("The bundled user guide has no README.md")
        return files

    def _source_metadata(self, source: Path | None = None) -> dict[str, Any]:
        resolved_source = source or self.source_root()
        metadata = _read_json(resolved_source / SOURCE_MANIFEST, {})
        if not isinstance(metadata, dict):
            raise ValueError("The bundled documentation catalog is invalid")
        return metadata

    def _documents(self, metadata: dict[str, Any], source: Path | None = None) -> list[dict[str, Any]]:
        documents = metadata.get("documents", [])
        if not isinstance(documents, list) or not documents:
            raise ValueError("The bundled documentation catalog has no documents")
        resolved_source = source or self.source_root()
        normalized: list[dict[str, Any]] = []
        identifiers: set[str] = set()
        for item in documents:
            if not isinstance(item, dict):
                raise ValueError("The bundled documentation catalog contains an invalid document")
            document_id = str(item.get("id", "")).strip()
            if not document_id or not document_id.replace("-", "").isalnum() or document_id in identifiers:
                raise ValueError("The bundled documentation catalog contains an invalid document ID")
            relative = self._safe_relative(str(item.get("filename", "")))
            if relative.suffix.lower() != ".pdf" or len(relative.parts) != 1:
                raise ValueError(f"Documentation file must be an allowlisted PDF: {relative}")
            source_path = resolved_source / relative
            if not source_path.is_file() or source_path.is_symlink():
                raise FileNotFoundError(f"Bundled documentation file not found: {relative}")
            title = str(item.get("title", "")).strip()
            description = str(item.get("description", "")).strip()
            version = str(item.get("version", "")).strip()
            page_count = int(item.get("pageCount", 0))
            if not title or not description or not version or page_count < 1:
                raise ValueError(f"Documentation metadata is incomplete for {document_id}")
            identifiers.add(document_id)
            normalized.append({
                "id": document_id,
                "title": title,
                "description": description,
                "filename": relative.as_posix(),
                "format": "pdf",
                "pageCount": page_count,
                "version": version,
            })
        return normalized

    def catalog(self) -> dict[str, Any]:
        source = self.source_root()
        metadata = self._source_metadata(source)
        return {
            "documentationVersion": str(metadata.get("documentationVersion", "")),
            "title": str(metadata.get("title", "VisionEval Workbench Documentation")),
            "documents": self._documents(metadata, source),
        }

    def document_path(self, document_id: str) -> Path:
        catalog = self.catalog()
        document = next((item for item in catalog["documents"] if item["id"] == document_id), None)
        if document is None:
            raise ValueError("Unknown documentation document")
        relative = self._safe_relative(document["filename"])
        installed = self.guide_root / relative
        path = installed if installed.is_file() else self.source_root() / relative
        resolved = path.resolve()
        allowed_roots = (self.guide_root.resolve(), self.source_root().resolve())
        if not resolved.is_file() or resolved.suffix.lower() != ".pdf":
            raise FileNotFoundError("The requested documentation PDF is missing")
        if not any(resolved.is_relative_to(root) for root in allowed_roots):
            raise ValueError("Documentation file is outside the managed guide")
        return resolved

    def sync(self) -> dict[str, Any]:
        self.documentation_root.mkdir(parents=True, exist_ok=True)
        (self.documentation_root / "User Notes").mkdir(parents=True, exist_ok=True)
        try:
            source = self.source_root()
            source_metadata = self._source_metadata(source)
            documentation_version = str(source_metadata.get("documentationVersion", "")).strip()
            if not documentation_version:
                raise ValueError("The bundled user guide has no documentationVersion")

            previous = _read_json(self.manifest_path, {})
            previous_files = previous.get("managedFiles", []) if isinstance(previous, dict) else []
            previous_paths = {
                str(item.get("path", ""))
                for item in previous_files
                if isinstance(item, dict) and item.get("path")
            }
            managed_files = []
            current_paths = set()
            for source_path in self._source_files(source):
                relative = source_path.relative_to(source)
                managed_relative = Path(MANAGED_GUIDE_DIRECTORY) / relative
                target = self.documentation_root / managed_relative
                payload = source_path.read_bytes()
                if not target.is_file() or target.read_bytes() != payload:
                    _write_bytes(target, payload)
                normalized = managed_relative.as_posix()
                current_paths.add(normalized)
                managed_files.append({"path": normalized, "sha256": _sha256(target)})

            documents = self._documents(source_metadata, source) if int(source_metadata.get("schemaVersion", 1)) >= 2 else []
            document_links = "\n".join(
                f"- [{item['title']}]({MANAGED_GUIDE_DIRECTORY.replace(' ', '%20')}/{item['filename']})"
                for item in documents
            )
            index_payload = (
                "# VisionEval Workbench Documentation\n\n"
                f"{document_links or '- [Workbench User Guide](Workbench%20User%20Guide/README.md)'}\n\n"
                "Files in `Workbench User Guide/` are maintained by VisionEval Workbench and may be "
                "updated when the application is upgraded. Put personal documentation in `User Notes/`; "
                "Workbench never modifies that folder.\n"
            ).encode("utf-8")
            index_path = self.documentation_root / "README.md"
            if not index_path.is_file() or index_path.read_bytes() != index_payload:
                _write_bytes(index_path, index_payload)
            current_paths.add("README.md")
            managed_files.append({"path": "README.md", "sha256": _sha256(index_path)})

            for old_value in sorted(previous_paths - current_paths, reverse=True):
                old_relative = self._safe_relative(old_value)
                target = self.documentation_root / old_relative
                try:
                    target.relative_to(self.documentation_root)
                except ValueError:
                    continue
                if target.is_file() or target.is_symlink():
                    target.unlink()
                parent = target.parent
                while parent != self.documentation_root and parent != self.guide_root.parent:
                    try:
                        parent.rmdir()
                    except OSError:
                        break
                    parent = parent.parent

            manifest = {
                "schemaVersion": DOCUMENTATION_SCHEMA_VERSION,
                "documentationVersion": documentation_version,
                "installedAt": _now_iso(),
                "entrypoint": "README.md",
                "managedFiles": sorted(managed_files, key=lambda item: item["path"]),
            }
            _write_json(self.manifest_path, manifest)
            return {
                "state": "ready",
                "documentationVersion": documentation_version,
                "entrypoint": "Documentation/README.md",
                "managedFileCount": len(managed_files),
                "documents": documents,
                "message": "The Workbench User Guide is installed in this workspace.",
            }
        except Exception as exc:
            return {
                "state": "warning",
                "documentationVersion": "",
                "entrypoint": "",
                "managedFileCount": 0,
                "message": f"User documentation could not be installed: {exc}",
            }

    def user_guide(self) -> dict[str, Any]:
        return self.page("README.md")

    def page_path(self, value: str = "README.md") -> Path:
        relative = self._safe_relative(value or "README.md")
        path = self.guide_root / relative
        if not path.is_file():
            source = self.source_root() / relative
            if not source.is_file():
                raise FileNotFoundError(f"Documentation page not found: {value}")
            path = source
        if path.suffix.lower() not in {".md", ".markdown"}:
            raise ValueError("Documentation page must be Markdown")
        return path

    def asset_path(self, value: str) -> Path:
        relative = self._safe_relative(value)
        path = self.guide_root / relative
        if not path.is_file():
            source = self.source_root() / relative
            if not source.is_file():
                raise FileNotFoundError(f"Documentation asset not found: {value}")
            path = source
        return path

    def page(self, value: str = "README.md") -> dict[str, Any]:
        path = self.page_path(value)
        try:
            relative = path.relative_to(self.guide_root).as_posix()
        except ValueError:
            relative = path.relative_to(self.source_root()).as_posix()
        return {"title": "Workbench User Guide", "path": relative, "body": path.read_text(encoding="utf-8")}
