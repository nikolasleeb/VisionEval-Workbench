from __future__ import annotations

import io
import json
import os
import platform
import tempfile
import threading
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .runtime import ACTIVE_STATES, TERMINAL_STATES, RuntimeManager
from .workspace import Workspace, now_iso, read_json

APP_ERROR_RETENTION_DAYS = 30
APP_ERROR_MAX_ENTRIES = 500


class DiagnosticsService:
    def __init__(self, workspace: Workspace, runtime: RuntimeManager, app_version: str):
        self.workspace = workspace
        self.runtime = runtime
        self.app_version = app_version
        self.error_log_path = self.workspace.internal / "diagnostics" / "app-errors.jsonl"
        self._error_log_lock = threading.Lock()

    @staticmethod
    def _error_timestamp(value: Any) -> datetime | None:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
        except (TypeError, ValueError):
            return None

    def _read_error_entries(self) -> list[dict[str, Any]]:
        if not self.error_log_path.is_file():
            return []
        entries = []
        for line in self.error_log_path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                entries.append(item)
        return entries

    @classmethod
    def _retained_error_entries(cls, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=APP_ERROR_RETENTION_DAYS)
        retained = [entry for entry in entries if (cls._error_timestamp(entry.get("timestamp")) or cutoff) >= cutoff]
        return retained[-APP_ERROR_MAX_ENTRIES:]

    def _write_error_entries(self, entries: list[dict[str, Any]]) -> None:
        self.error_log_path.parent.mkdir(parents=True, exist_ok=True)
        if not entries:
            self.error_log_path.unlink(missing_ok=True)
            return
        fd, temporary = tempfile.mkstemp(prefix=f".{self.error_log_path.name}.", dir=self.error_log_path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                for entry in entries:
                    handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
            os.replace(temporary, self.error_log_path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def record_app_error(self, payload: dict[str, Any]) -> dict[str, Any]:
        entry = {"timestamp": now_iso(), "source": str(payload.get("source") or "app")[:80], "message": str(payload.get("message") or payload.get("error") or "Unknown error")[:4000], "path": str(payload.get("path") or "")[:500], "context": payload.get("context") if isinstance(payload.get("context"), dict) else {}}
        with self._error_log_lock:
            entries = self._retained_error_entries([*self._read_error_entries(), entry])
            self._write_error_entries(entries)
        return entry

    def recent_errors(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._error_log_lock:
            existing = self._read_error_entries()
            entries = self._retained_error_entries(existing)
            if entries != existing:
                self._write_error_entries(entries)
            return entries[-max(1, min(limit, APP_ERROR_MAX_ENTRIES)):]

    def clear_errors(self) -> dict[str, Any]:
        with self._error_log_lock:
            cleared = len(self._read_error_entries())
            self._write_error_entries([])
        return {"cleared": cleared, "retentionDays": APP_ERROR_RETENTION_DAYS, "maxEntries": APP_ERROR_MAX_ENTRIES}

    def runs(self, state: str = "failed") -> list[dict[str, Any]]:
        jobs = self.runtime.list_jobs(include_archived=True)
        if state == "all": return jobs
        if state == "active": return [job for job in jobs if job.get("state") in ACTIVE_STATES]
        if state == "terminal": return [job for job in jobs if job.get("state") in TERMINAL_STATES]
        return [job for job in jobs if job.get("state") in {"failed", "cleanup_failed"}]

    @staticmethod
    def _safe_name(value: str) -> str:
        cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in value.strip().lower())
        return "-".join(part for part in cleaned.split("-") if part)[:80] or "run"

    @staticmethod
    def _add_file(archive: zipfile.ZipFile, path: Path, name: str) -> None:
        if path.is_file():
            archive.write(path, name)

    def _add_tree(self, archive: zipfile.ZipFile, root: Path, prefix: str, *, include_results: bool = False) -> None:
        if not root.is_dir():
            return
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(root)
            if not include_results and relative.parts and relative.parts[0].lower() in {"results", ".comparison_csv_cache"}:
                continue
            self._add_file(archive, path, f"{prefix}/{relative.as_posix()}")

    def run_zip(self, job_id: str, include_results: bool = False, include_cache: bool = False) -> tuple[bytes, str]:
        job = self.runtime.job(job_id)
        run_dir = self.workspace.runs / job_id
        project_id = str(job.get("projectId") or "")
        project_dir = self.workspace.projects / project_id
        project = read_json(project_dir / "project.json", {})
        model_path = Path(str(job.get("modelPath") or ""))
        filename = f"visioneval-diagnostics-{self._safe_name(job.get('projectName', 'project'))}-{self._safe_name(job.get('variationName', 'run'))}.zip"
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            manifest = {"generatedAt": now_iso(), "appVersion": self.app_version, "os": {"system": platform.system(), "release": platform.release(), "machine": platform.machine()}, "workspace": {"schemaVersion": self.workspace.settings().get("workspaceSchemaVersion", "")}, "job": job, "project": {"id": project_id, "name": project.get("name", job.get("projectName", ""))}, "runtime": {"adapter": getattr(self.runtime, "adapter", ""), "profile": self.runtime.docker_status()}, "options": {"includeResults": include_results, "includeComparisonCache": include_cache}}
            archive.writestr("diagnostics/manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            archive.writestr("diagnostics/recent-app-errors.json", json.dumps(self.recent_errors(), ensure_ascii=False, indent=2))
            self._add_file(archive, run_dir / "job.json", "run/job.json")
            self._add_file(archive, run_dir / "run.log", "run/run.log")
            self._add_file(archive, project_dir / "project.json", "project/project.json")
            if project:
                template_id = str((project.get("template") or {}).get("id") or "")
                library_id = str((project.get("inputLibrary") or {}).get("id") or "")
                template_dir = self.workspace.templates / template_id
                library_dir = self.workspace.input_library / library_id
                self._add_file(archive, template_dir / "workbench_template.json", "assets/template/workbench_template.json")
                self._add_file(archive, template_dir / "region_builder_manifest.json", "assets/template/region_builder_manifest.json")
                self._add_file(archive, library_dir / "region_builder_manifest.json", "assets/input-library/region_builder_manifest.json")
                region_manifest = read_json(library_dir / "region_builder_manifest.json", {}) or read_json(template_dir / "region_builder_manifest.json", {})
                package_id = str((region_manifest.get("regionPackage") or {}).get("id") or region_manifest.get("regionPackageId") or "")
                if package_id:
                    package_dir = self.workspace.region_packages / package_id
                    self._add_file(archive, package_dir / "workbench-package.json", "assets/regional-package/workbench-package.json")
                    self._add_file(archive, package_dir / "SOURCES.md", "assets/regional-package/SOURCES.md")
            if model_path.exists():
                for name in ("workbench_provenance.json", "visioneval.cnf", "region_builder_manifest.json"):
                    self._add_file(archive, model_path / name, f"model/{name}")
                self._add_tree(archive, model_path / "inputs", "model/inputs")
                self._add_tree(archive, model_path / "defs", "model/defs")
                for log_path in sorted((model_path / "results").glob("Log_*.txt")):
                    self._add_file(archive, log_path, f"model/results/{log_path.name}")
                if include_results:
                    self._add_tree(archive, model_path / "results", "model/results", include_results=True)
            if include_cache:
                self._add_tree(archive, self.workspace.exchange / "comparison-cache", "comparison-cache", include_results=True)
        return buffer.getvalue(), filename
