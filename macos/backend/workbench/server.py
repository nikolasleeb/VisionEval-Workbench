from __future__ import annotations

import csv
import hashlib
import io
import json
import mimetypes
import os
import shutil
import time
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import __version__
from .bundled_assets import BundledAssetService
from .comparison import ComparisonOperationManager, ComparisonScanManager, ComparisonService
from .copy_operations import CopyOperationManager
from .dependencies import DependencyService
from .documentation import DocumentationService
from .diagnostics import DiagnosticsService
from .explore import ExploreService, InputValidationError
from .excel_exports import ComparisonExportManager
from .input_explanations import InputExplanationPackageService
from .model_packages import ModelPackageService
from .hypercube import HypercubeOperationManager, HypercubeService
from .hypercube_analysis import HypercubeAnalysisOperationManager, HypercubeAnalysisService, HypercubeCaseExportManager, HypercubeDiscoveryManager
from .region_packages import RegionPackageService, package_manifest_type
from .runtime import RuntimeManager
from .runtime import CURRENT_RELEASE_TAG
from .update_checks import UpdateCheckService
from .region_builder import RegionBuilderService
from .workspace import Workspace, WorkspaceError, fingerprint_tree, make_id, now_iso, read_json

# Windows' MIME registry does not consistently know modern JavaScript module
# extensions. Chromium refuses to execute an ES module served as text/plain.
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/json", ".json")
mimetypes.add_type("text/markdown", ".md")


class RuntimeInstallOperationManager:
    """Run the managed image installation without a long-lived HTTP request."""

    def __init__(self, runtime: RuntimeManager):
        self.runtime = runtime
        self.lock = threading.RLock()
        self.operations: dict[str, dict] = {}
        self.active_id = ""

    def start(self, profile: dict | None = None) -> dict:
        with self.lock:
            active = self.operations.get(self.active_id, {})
            if active.get("state") in {"waiting", "running"}:
                return dict(active)
            operation_id = make_id("runtime-install", "managed")
            operation = {
                "id": operation_id,
                "state": "waiting",
                "phase": "starting",
                "createdAt": now_iso(),
                "startedAt": "",
                "finishedAt": "",
                "message": "Preparing the pinned runtime installation.",
                "result": None,
            }
            self.operations[operation_id] = operation
            self.active_id = operation_id
        threading.Thread(target=self._run, args=(operation_id, profile), daemon=True).start()
        return self.status(operation_id)

    def _run(self, operation_id: str, profile: dict | None) -> None:
        with self.lock:
            operation = self.operations[operation_id]
            operation.update({
                "state": "running",
                "phase": "installing",
                "startedAt": now_iso(),
                "message": "Downloading and verifying the pinned runtime… This can take several minutes the first time.",
            })
        try:
            result = (
                self.runtime.install_or_update_runtime(profile)
                if profile is not None
                else self.runtime.install_or_update_runtime()
            )
            with self.lock:
                operation.update({
                    "state": "succeeded",
                    "phase": "complete",
                    "finishedAt": now_iso(),
                    "message": "Runtime downloaded and verified.",
                    "result": result,
                })
        except Exception as exc:
            with self.lock:
                operation.update({
                    "state": "failed",
                    "phase": "failed",
                    "finishedAt": now_iso(),
                    "message": str(exc),
                })

    def status(self, operation_id: str) -> dict:
        with self.lock:
            operation = self.operations.get(operation_id)
            if not operation:
                raise WorkspaceError("Unknown runtime installation operation")
            return dict(operation)


class WorkbenchApplication:
    def __init__(self, workspace_root: str | Path, public_root: str | Path, resource_root: str | Path):
        self.workspace = Workspace(workspace_root)
        self.public_root = Path(public_root).resolve()
        self.resource_root = Path(resource_root).resolve()
        self.bundled_assets = BundledAssetService(self.workspace, self.resource_root)
        self.bundled_asset_status = self.bundled_assets.seed_new_workspace()
        if os.environ.get("WORKBENCH_RENDERER_SMOKE") == "1":
            self.bundled_asset_status = self.bundled_assets.install_planrva(automatic=True)
        self.documentation = DocumentationService(self.workspace.root, self.resource_root)
        self.documentation_status = self.documentation.sync()
        self.asset_catalog = json.loads((self.resource_root / "asset_catalog.json").read_text(encoding="utf-8"))
        helper_target = self.workspace.exchange / "system" / "rda_reader.R"
        source_helper = self.resource_root / "rda_reader.R"
        if not helper_target.exists() or helper_target.read_bytes() != source_helper.read_bytes():
            shutil.copy2(source_helper, helper_target)
        scan_target = self.workspace.exchange / "system" / "comparison_scan.R"
        scan_source = self.resource_root / "comparison_scan.R"
        if not scan_target.exists() or scan_target.read_bytes() != scan_source.read_bytes():
            shutil.copy2(scan_source, scan_target)
        cache_extractor_target = self.workspace.exchange / "system" / "comparison_cache_extract.R"
        cache_extractor_source = self.resource_root / "comparison_cache_extract.R"
        if not cache_extractor_target.exists() or cache_extractor_target.read_bytes() != cache_extractor_source.read_bytes():
            shutil.copy2(cache_extractor_source, cache_extractor_target)
        hypercube_summary_target = self.workspace.exchange / "system" / "hypercube_summary.R"
        hypercube_summary_source = self.resource_root / "hypercube_summary.R"
        if not hypercube_summary_target.exists() or hypercube_summary_target.read_bytes() != hypercube_summary_source.read_bytes():
            shutil.copy2(hypercube_summary_source, hypercube_summary_target)
        conflicts_target = self.workspace.exchange / "system" / "unit_conflicts.json"
        conflicts_source = self.resource_root / "unit_conflicts.json"
        if not conflicts_target.exists() or conflicts_target.read_bytes() != conflicts_source.read_bytes():
            shutil.copy2(conflicts_source, conflicts_target)
        runtime_cli = self.resource_root / "ve-cli-native.R"
        if not runtime_cli.is_file():
            runtime_cli = self.resource_root.parent / "runtime" / "scripts" / "ve-cli-native.R"
        self.runtime = RuntimeManager(self.workspace, cli_path=runtime_cli)
        # Terminal history is operational metadata, not result ownership. Keep
        # it bounded without touching registered results or Datastores.
        self.runtime.clear_history(older_than_days=30)
        self.update_checks = UpdateCheckService(
            self.workspace,
            __version__,
            CURRENT_RELEASE_TAG,
            self.runtime.image_digest,
            self.runtime.adapter,
            self.runtime.runtime_profiles,
        )
        self.runtime_installations = RuntimeInstallOperationManager(self.runtime)
        self.diagnostics = DiagnosticsService(self.workspace, self.runtime, __version__)
        self.comparison = ComparisonService(self.workspace, self.runtime, helper_target, scan_target, conflicts_target, cache_extractor_target)
        self.comparison_operations = ComparisonOperationManager(self.comparison)
        self.comparison_scans = ComparisonScanManager(self.comparison)
        self.hypercube_analysis = HypercubeAnalysisService(self.workspace, self.comparison, hypercube_summary_target)
        self.hypercube_analysis_operations = HypercubeAnalysisOperationManager(self.hypercube_analysis)
        self.hypercube_discovery = HypercubeDiscoveryManager(self.hypercube_analysis, self.diagnostics.record_app_error)
        self.hypercube_case_exports = HypercubeCaseExportManager(self.hypercube_analysis)
        self.comparison_exports = ComparisonExportManager(self.comparison, __version__, self.hypercube_analysis)
        self.input_explanations = InputExplanationPackageService(self.workspace)
        self.model_packages = ModelPackageService(self.workspace)
        self.region_packages = RegionPackageService(self.workspace)
        self.package_previews: dict[str, dict] = {}
        self.explore = ExploreService(self.workspace, self.resource_root / "explore_catalog.json", self.resource_root / "unit_conflicts.json", self.resource_root / "dependency_catalog.json")
        self.hypercubes = HypercubeOperationManager(HypercubeService(self.workspace, self.explore))
        self.copy_operations = CopyOperationManager(self.workspace)
        self.dependencies = DependencyService(self.workspace, self.resource_root / "dependency_catalog.json")
        self.region_builder = RegionBuilderService(self.workspace, self.resource_root, self.region_packages)
        self._last_archive_cleanup = 0.0
        self._cleanup_archives()

    def preview_package(self, source: str) -> dict:
        source_path = Path(source).expanduser().resolve()
        package_type = package_manifest_type(source_path)
        service = {"input-explanations": self.input_explanations, "model-bundle": self.model_packages, "region-builder": self.region_packages}.get(package_type)
        if not service:
            raise WorkspaceError(f"Unsupported Workbench package type: {package_type or 'unknown'}")
        root, temporary = RegionPackageService._package_source(source_path)
        try:
            manifest = service._manifest(root)
            files = [item for item in root.rglob("*") if item.is_file()]
            size = sum(item.stat().st_size for item in files)
            source_fingerprint = hashlib.sha256(source_path.read_bytes()).hexdigest() if source_path.is_file() else fingerprint_tree(source_path)
            token = hashlib.sha256(f"{source_path}\0{source_fingerprint}\0{package_type}".encode()).hexdigest()
            warnings = [str(item) for item in manifest.get("warnings", []) if str(item)]
            is_statewide_region_source = package_type == "region-builder" and (
                str(manifest.get("coverage", "")).upper() in {"VA", "VIRGINIA", "STATEWIDE VIRGINIA"}
                or "virginia" in str(manifest.get("id", "")).lower()
            )
            if is_statewide_region_source and not warnings and not manifest.get("executionSupport"):
                warnings.append(
                    "This statewide source-data package does not include an execution-support notice. "
                    "Confirm its intended use before installing."
                )
            result = {
                "token": token, "name": manifest.get("name", manifest.get("id", "Package")), "version": manifest.get("version", ""),
                "type": package_type, "description": manifest.get("description", ""), "size": size, "fileCount": len(files),
                "compatibility": manifest.get("compatibilitySummary", "Validated for this Workbench package format"),
                "provenance": manifest.get("provenance", manifest.get("source", "Local package selected in Finder")),
                "intendedUse": manifest.get("intendedUse", "Install as a local Workbench asset"),
                "executionSupport": manifest.get("executionSupport", "Not declared by this package"),
                "capabilities": manifest.get("capabilities", []), "warnings": warnings, "checksumStatus": "Verified against the package manifest",
            }
            self.package_previews[token] = {"source": str(source_path), "fingerprint": source_fingerprint, "type": package_type}
            return result
        finally:
            if temporary:
                temporary.cleanup()

    def _cleanup_archives(self) -> None:
        now = time.monotonic()
        if now - self._last_archive_cleanup >= 86400 or not self._last_archive_cleanup:
            self.workspace.cleanup_archives()
            self._last_archive_cleanup = now

    @staticmethod
    def _manager_active(manager, kind: str) -> list[dict]:
        active = getattr(manager, "active", None)
        if callable(active):
            return [{"id": item.get("id", ""), "kind": item.get("kind") or kind, "state": item.get("state", ""), "message": item.get("message", "")} for item in active()]
        values = getattr(manager, "operations", {}).values()
        return [{"id": item.get("id", ""), "kind": kind, "state": item.get("state", ""), "message": item.get("message", "")} for item in values if item.get("state") in {"waiting", "running", "cancelling"}]

    def active_operations(self) -> dict:
        operations = []
        operations.extend({"id": job.get("id", ""), "kind": "model_run", "state": job.get("state", ""), "message": job.get("variationName", "")} for job in self.runtime.list_jobs(include_archived=True) if job.get("state") not in {"succeeded", "failed", "cancelled", "cleanup_failed"})
        for manager, kind in (
            (self.hypercubes, "hypercube_generation"),
            (self.hypercube_analysis_operations, "hypercube_analysis"),
            (self.hypercube_discovery, "hypercube_discovery"),
            (self.hypercube_case_exports, "hypercube_case_export"),
            (self.comparison_operations, "comparison"),
            (self.comparison_scans, "comparison_scan"),
            (self.comparison_exports, "export"),
            (self.copy_operations, "project_copy"),
            (self.runtime_installations, "runtime_installation"),
        ):
            operations.extend(self._manager_active(manager, kind))
        counts: dict[str, int] = {}
        for item in operations:
            counts[item["kind"]] = counts.get(item["kind"], 0) + 1
        return {"active": bool(operations), "operations": operations, "counts": counts}

    def stop_background_operations(self) -> dict:
        failures = []
        runtime_result = self.runtime.shutdown(True)
        failures.extend(runtime_result.get("failures") or [])
        for manager, kind in (
            (self.hypercubes, "hypercube_generation"),
            (self.hypercube_analysis_operations, "hypercube_analysis"),
            (self.hypercube_discovery, "hypercube_discovery"),
            (self.hypercube_case_exports, "hypercube_case_export"),
            (self.comparison_operations, "comparison"),
            (self.comparison_scans, "comparison_scan"),
            (self.comparison_exports, "export"),
            (self.copy_operations, "project_copy"),
        ):
            for item in self._manager_active(manager, kind):
                try:
                    manager.cancel(item["id"])
                except Exception as exc:
                    failures.append({"id": item["id"], "kind": kind, "message": str(exc)})
        installs = self._manager_active(self.runtime_installations, "runtime_installation")
        failures.extend({"id": item["id"], "kind": "runtime_installation", "message": "Runtime installation cannot be interrupted safely; wait for it to finish."} for item in installs)
        return {"ok": not failures, "failures": failures}

    def state(self) -> dict:
        self._cleanup_archives()
        runtime_status = self.runtime.docker_status()
        projects = self.workspace.list_projects()
        runtime_digest = str(runtime_status.get("imageDigest", ""))
        for project in projects:
            try:
                _, current = self.workspace.project(str(project.get("id", "")))
                project.update(current)
                project["resultStatuses"] = self.workspace.result_statuses(current, runtime_digest)
                for variation in project.get("variations", []):
                    statuses = project["resultStatuses"].get(variation.get("id", ""), [])
                    variation["resultStatus"] = "current" if any(item.get("status") == "current" for item in statuses) else (statuses[0].get("status") if statuses else "missing")
                baseline_statuses = project["resultStatuses"].get("baseline", [])
                project["baselineResultStatus"] = "current" if any(item.get("status") == "current" for item in baseline_statuses) else (baseline_statuses[0].get("status") if baseline_statuses else "missing")
                project["requiresBaseline"] = (
                    not any(item.get("status") == "current" for item in baseline_statuses)
                    if runtime_digest else not self.workspace.project_has_compatible_baseline(current)
                )
            except WorkspaceError:
                project["requiresBaseline"] = True
        return {
            "app": "VisionEval Workbench",
            "version": __version__,
            "workspace": str(self.workspace.root),
            "inputLibraries": self.workspace.list_input_libraries(),
            "inputExplanations": self.input_explanations.list(),
            "regionPackages": self.region_packages.list(),
            "developSources": self.region_builder.catalog()["packages"],
            "comparisonMapPackages": self.region_packages.comparison_map_providers(),
            "templates": self.workspace.list_templates(),
            "projects": projects,
            "jobs": self.runtime.list_jobs(),
            "queue": self.runtime.queue(),
            "catalog": self.workspace.display_catalog(False, False)["datastores"],
            "archivedProjects": self.workspace.list_archived_projects(),
            "runtime": runtime_status,
            "updates": self.update_checks.status(),
            "workspaceSettings": self.workspace.settings(),
            "assets": self.workspace.asset_inventory(),
            "assetCatalog": self.asset_catalog,
            "bundledAssets": {"planrva": self.bundled_assets.status()},
            "documentation": self.documentation_status,
        }

def json_body(handler: SimpleHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0") or 0)
    raw = handler.rfile.read(length).decode("utf-8") if length else "{}"
    payload = json.loads(raw or "{}")
    if not isinstance(payload, dict):
        raise WorkspaceError("JSON object required")
    return payload


def send_json(handler: SimpleHTTPRequestHandler, payload, status: int = 200) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def first(query: dict[str, list[str]], name: str, default: str = "") -> str:
    return query.get(name, [default])[0]


def csv_values(query: dict[str, list[str]], name: str) -> list[str]:
    return [part for value in query.get(name, []) for part in value.split("|") if part]


def send_bytes(handler: SimpleHTTPRequestHandler, payload: bytes, content_type: str, filename: str) -> None:
    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Disposition", f'attachment; filename="{filename}"')
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)


def send_file(handler: SimpleHTTPRequestHandler, path: Path, content_type: str, filename: str) -> None:
    size = path.stat().st_size
    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Disposition", f'attachment; filename="{filename}"')
    handler.send_header("Content-Length", str(size))
    handler.end_headers()
    with path.open("rb") as handle:
        shutil.copyfileobj(handle, handler.wfile, length=1024 * 1024)


def send_inline_file(handler: SimpleHTTPRequestHandler, path: Path, content_type: str) -> None:
    size = path.stat().st_size
    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Disposition", f'inline; filename="{path.name}"')
    handler.send_header("Content-Length", str(size))
    handler.end_headers()
    with path.open("rb") as handle:
        shutil.copyfileobj(handle, handler.wfile, length=1024 * 1024)


def handler_class(application: WorkbenchApplication):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(application.public_root), **kwargs)

        def log_message(self, fmt, *args):
            if os.environ.get("WORKBENCH_HTTP_LOG"):
                super().log_message(fmt, *args)

        def do_GET(self):
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            try:
                if parsed.path == "/api/health":
                    send_json(self, {"ok": True, "app": "VisionEval Workbench"})
                elif parsed.path == "/api/state":
                    send_json(self, application.state())
                elif parsed.path == "/api/runtime/status":
                    send_json(self, application.runtime.docker_status())
                elif parsed.path == "/api/runtime/install/status":
                    send_json(self, application.runtime_installations.status(first(query, "id")))
                elif parsed.path == "/api/settings":
                    send_json(self, application.workspace.settings())
                elif parsed.path == "/api/updates/status":
                    send_json(self, application.update_checks.status())
                elif parsed.path == "/api/documentation/user-guide":
                    send_json(self, application.documentation.user_guide())
                elif parsed.path == "/api/documentation/catalog":
                    send_json(self, application.documentation.catalog())
                elif parsed.path == "/api/documentation/document":
                    path = application.documentation.document_path(first(query, "id"))
                    send_inline_file(self, path, "application/pdf")
                elif parsed.path == "/api/documentation/page":
                    send_json(self, application.documentation.page(first(query, "path", "README.md")))
                elif parsed.path == "/api/documentation/asset":
                    path = application.documentation.asset_path(first(query, "path"))
                    send_inline_file(self, path, mimetypes.guess_type(path.name)[0] or "application/octet-stream")
                elif parsed.path == "/api/diagnostics/runs":
                    send_json(self, {"runs": application.diagnostics.runs(first(query, "state", "failed"))})
                elif parsed.path == "/api/diagnostics/errors":
                    send_json(self, {"errors": application.diagnostics.recent_errors()})
                elif parsed.path == "/api/diagnostics/run":
                    data, filename = application.diagnostics.run_zip(first(query, "jobId"), first(query, "includeResults").lower() == "true", first(query, "includeCache").lower() == "true")
                    send_bytes(self, data, "application/zip", filename)
                elif parsed.path == "/api/storage":
                    report = application.workspace.storage_report()
                    report["comparisonCache"] = application.comparison.cache.report() if application.comparison.cache else {"bytes":0,"entries":0,"limitBytes":0}
                    send_json(self, report)
                elif parsed.path == "/api/projects":
                    send_json(self, {"projects": application.workspace.list_projects()})
                elif parsed.path == "/api/projects/archived":
                    send_json(self, {"projects": application.workspace.list_archived_projects()})
                elif parsed.path == "/api/projects/copy-estimate":
                    selected = [item for item in first(query, "variationIds").split(",") if item]
                    send_json(self, application.workspace.copy_result_estimate(first(query, "projectId"), selected or None))
                elif parsed.path == "/api/projects/variations/delete-impact":
                    send_json(self, application.workspace.variation_deletion_impact(
                        first(query, "projectId"), first(query, "variationId")
                    ))
                elif parsed.path == "/api/projects/copy/status":
                    send_json(self, application.copy_operations.status(first(query, "id")))
                elif parsed.path == "/api/project":
                    _, project = application.workspace.project(first(query, "id"))
                    send_json(self, project)
                elif parsed.path == "/api/input-file":
                    library_id, filename = first(query, "libraryId"), Path(first(query, "filename")).name
                    path, overlay = application.workspace.input_file(library_id, filename, first(query, "projectId"), first(query, "variationId"))
                    with path.open("r", encoding="utf-8-sig", newline="") as handle:
                        rows = list(csv.reader(handle))
                    columns = rows[0] if rows else []
                    source_path, _ = application.workspace.input_file(library_id, filename)
                    with source_path.open("r", encoding="utf-8-sig", newline="") as handle:
                        source_rows = list(csv.reader(handle))
                    metadata = application.explore.input_column_metadata(filename, columns, source_rows[1:], rows[1:])
                    send_json(self, {"filename": filename, "columns": columns, "columnTypes": application.explore.input_column_types(filename, columns), "columnMetadata": metadata, "validationGroups": application.explore.validation_groups(filename), "rows": rows[1:], "overlay": overlay})
                elif parsed.path == "/api/explore/files":
                    package_id = first(query, "explanationPackageId")
                    package_path = application.input_explanations.catalog_path(package_id) if package_id else None
                    send_json(self, application.explore.files(first(query, "libraryId"), package_path))
                elif parsed.path == "/api/explore/file":
                    package_id = first(query, "explanationPackageId")
                    package_path = application.input_explanations.catalog_path(package_id) if package_id else None
                    send_json(self, application.explore.file(first(query, "libraryId"), first(query, "filename"), first(query, "templateId"), package_path))
                elif parsed.path == "/api/dependencies":
                    send_json(self, application.dependencies.graph(
                        first(query, "templateId"), first(query, "focusId"),
                        first(query, "scope"), first(query, "originId"), first(query, "view"),
                        first(query, "mode", "execution"),
                    ))
                elif parsed.path == "/api/dependencies/export.svg":
                    template_id, focus_id = first(query, "templateId"), first(query, "focusId")
                    send_bytes(self, application.dependencies.svg(
                        template_id, focus_id, first(query, "scope"), first(query, "originId"), first(query, "view"),
                    ), "image/svg+xml; charset=utf-8", "visioneval_dependencies.svg")
                elif parsed.path == "/api/dependencies/export.pdf":
                    template_id, focus_id = first(query, "templateId"), first(query, "focusId")
                    send_bytes(self, application.dependencies.pdf(
                        template_id, focus_id, first(query, "scope"), first(query, "originId"), first(query, "view"),
                    ), "application/pdf", "visioneval_dependencies.pdf")
                elif parsed.path == "/api/dependencies/export.html":
                    template_id, focus_id = first(query, "templateId"), first(query, "focusId")
                    send_bytes(self, application.dependencies.html(
                        template_id, focus_id, first(query, "scope"), first(query, "originId"), first(query, "view"),
                    ), "text/html; charset=utf-8", "visioneval_dependencies.html")
                elif parsed.path == "/api/region-builder/packages":
                    send_json(self, application.region_builder.catalog())
                elif parsed.path == "/api/region-builder/reference":
                    send_json(self, application.region_builder.reference(first(query, "packageId")))
                elif parsed.path == "/api/region-builder/sources":
                    send_json(self, application.region_builder.sources(first(query, "packageId")))
                elif parsed.path == "/api/region-builder/regions":
                    send_json(self, application.region_builder.regions(first(query, "packageId")))
                elif parsed.path == "/api/region-builder/geography-options":
                    send_json(self, application.region_builder.geography_options(
                        first(query, "packageId"), first(query, "sourceLibraryId"), first(query, "regionId")
                    ))
                elif parsed.path == "/api/region-builder/map/statewide":
                    send_json(self, application.region_builder.statewide_map_data(first(query, "packageId")))
                elif parsed.path == "/api/region-builder/map":
                    send_json(self, application.region_builder.map_data(first(query, "packageId"), first(query, "regionId")))
                elif parsed.path == "/api/geography-options":
                    send_json(self, application.workspace.geography_options(first(query, "projectId"), first(query, "filename")))
                elif parsed.path == "/api/project-review":
                    project_id = first(query, "projectId")
                    hypercube_id = first(query, "hypercubeId")
                    selected = None
                    if hypercube_id:
                        _, project = application.workspace.project(project_id)
                        hypercube = next((item for item in project.get("hypercubes", []) if item.get("id") == hypercube_id), None)
                        if not hypercube:
                            raise WorkspaceError("Unknown hypercube")
                        selected = set(hypercube.get("scenarioIds", []))
                    review = application.workspace.review_project(project_id, variation_ids=selected)
                    if hypercube_id:
                        review["hypercube"] = hypercube
                    review["validation"] = application.runtime.validate_project(project_id)
                    send_json(self, review)
                elif parsed.path == "/api/projects/hypercubes/status":
                    send_json(self, application.hypercubes.status(first(query, "id")))
                elif parsed.path == "/api/hypercube-analysis/inventory":
                    send_json(self, application.hypercube_analysis.inventory(first(query, "projectId")))
                elif parsed.path == "/api/hypercube-analysis/options":
                    send_json(self, application.hypercube_analysis.options(first(query, "projectId")))
                elif parsed.path == "/api/hypercube-analysis/storage":
                    send_json(self, application.hypercube_analysis.storage(first(query, "projectId")))
                elif parsed.path == "/api/hypercube-run/plan":
                    send_json(self, application.hypercube_analysis.run_plan(first(query, "projectId")))
                elif parsed.path == "/api/hypercube-analysis/discovery/status":
                    send_json(self, application.hypercube_discovery.status(first(query, "id")))
                elif parsed.path == "/api/hypercube-analysis/operations/status":
                    send_json(self, application.hypercube_analysis_operations.status(first(query, "id")))
                elif parsed.path == "/api/hypercube-exports/options":
                    send_json(self, application.hypercube_case_exports.options(first(query, "projectId")))
                elif parsed.path == "/api/hypercube-exports/status":
                    send_json(self, application.hypercube_case_exports.status(first(query, "id")))
                elif parsed.path == "/api/hypercube-exports/download":
                    path, filename = application.hypercube_case_exports.artifact(first(query, "id"))
                    send_file(self, path, "application/zip", filename)
                elif parsed.path == "/api/hypercube-analysis/export.csv":
                    request_payload = json.loads(first(query, "payload", "{}"))
                    analysis = application.hypercube_analysis.matrix(request_payload)
                    send_bytes(self, application.hypercube_analysis.csv_bytes(analysis), "text/csv; charset=utf-8", "visioneval_hypercube_analysis.csv")
                elif parsed.path == "/api/jobs":
                    send_json(self, {"jobs": application.runtime.list_jobs(first(query, "projectId"))})
                elif parsed.path == "/api/runs/history/impact":
                    send_json(self, application.runtime.history_clear_impact())
                elif parsed.path == "/api/operations/active":
                    send_json(self, application.active_operations())
                elif parsed.path == "/api/run-queue":
                    send_json(self, application.runtime.queue())
                elif parsed.path == "/api/job":
                    send_json(self, application.runtime.job(first(query, "id")))
                elif parsed.path == "/api/run-log":
                    send_json(self, application.runtime.log_chunk(first(query, "id"), int(first(query, "offset", "0"))))
                elif parsed.path == "/api/run-events":
                    self._stream_events(first(query, "id"), int(first(query, "offset", "0")))
                elif parsed.path == "/api/datastores":
                    include_hidden = first(query, "includeHidden").lower() == "true"
                    send_json(self, {"datastores": application.workspace.display_catalog(False, include_hidden)["datastores"]})
                elif parsed.path == "/api/comparison/variables":
                    ids = [item for item in first(query, "ids").split(",") if item]
                    send_json(self, {"variables": application.comparison.variables(ids)})
                elif parsed.path == "/api/comparison/options":
                    ids = [item for item in first(query, "ids").split(",") if item]
                    send_json(self, application.comparison.options(ids, first(query, "view", "compare")))
                elif parsed.path == "/api/comparison/geo-options":
                    send_json(self, application.comparison.geo_options(first(query, "reference"), first(query, "table"), first(query, "year", "2045")))
                elif parsed.path == "/api/comparison/cross-output-geo-options":
                    send_json(self, application.comparison.cross_output_geo_options(first(query, "reference"), first(query, "year", "2045")))
                elif parsed.path == "/api/comparison/map-options":
                    ids = [item for item in first(query, "ids").split(",") if item]
                    send_json(self, application.comparison.map_options(ids))
                elif parsed.path == "/api/comparison/compare":
                    comparisons = [item for item in first(query, "comparisons").split(",") if item]
                    payload = application.comparison.compare(
                        first(query, "reference"), comparisons, first(query, "table"), first(query, "variable"),
                        first(query, "year", "2045"), first(query, "changedOnly") == "true", int(first(query, "limit", "100")), int(first(query, "offset", "0")), first(query, "filterField"), csv_values(query, "filterValue"), first(query, "sortColumn", "id"), first(query, "sortDirection", "original"), first(query, "mode", "auto"),
                    )
                    send_json(self, payload)
                elif parsed.path == "/api/comparison/operations/status":
                    send_json(self, application.comparison_operations.status(first(query, "id")))
                elif parsed.path == "/api/comparison/exports/status":
                    send_json(self, application.comparison_exports.status(first(query, "id")))
                elif parsed.path == "/api/comparison/exports/download":
                    path, filename, mime_type = application.comparison_exports.download(first(query, "id"))
                    send_file(self, path, mime_type, filename)
                elif parsed.path == "/api/comparison/changes":
                    comparisons = [item for item in first(query, "comparisons").split(",") if item]
                    send_json(self, application.comparison.changes(first(query, "reference"), comparisons, first(query, "year", "2045"), first(query, "filterField"), csv_values(query, "filterValue")))
                elif parsed.path == "/api/comparison/scans/status":
                    send_json(self, application.comparison_scans.status(first(query, "id")))
                elif parsed.path == "/api/comparison/dashboard":
                    send_json(self, application.comparison.dashboard(first(query, "reference"), first(query, "comparison"), first(query, "year", "2045"), csv_values(query, "variableKey"), first(query, "filterField"), csv_values(query, "filterValue"), first(query, "sortBy", "name")))
                elif parsed.path == "/api/comparison/export-dashboard-pdf":
                    dashboard = application.comparison.dashboard_display(first(query, "dashboardToken"), first(query, "sortBy", "name"), first(query, "displayMode", "all"), float(first(query, "threshold", "0")), int(first(query, "count", "5")), first(query, "hideZero") == "true")
                    send_bytes(
                        self,
                        application.comparison.dashboard_pdf(
                            dashboard,
                            first(query, "increaseColor", "#2274a7"),
                            first(query, "decreaseColor", "#be3742"),
                        ),
                        "application/pdf",
                        "visioneval_percent_change_chart.pdf",
                    )
                elif parsed.path == "/api/comparison/export-dashboard-csv":
                    dashboard = application.comparison.dashboard_display(first(query, "dashboardToken"), first(query, "sortBy", "name"), first(query, "displayMode", "all"), float(first(query, "threshold", "0")), int(first(query, "count", "5")), first(query, "hideZero") == "true")
                    rows = [{**item, "scope": dashboard.get("scopeLabel", "All locations")} for item in (dashboard.get("rows") or [])]
                    send_bytes(self, application.comparison.csv_bytes(rows), "text/csv; charset=utf-8", "visioneval_percent_change_chart.csv")
                elif parsed.path == "/api/comparison/export-map-csv":
                    payload = application.comparison.comparison_map_snapshot(first(query, "mapToken"))
                    package_id, region_id = first(query, "packageId"), first(query, "regionId")
                    map_data = application.region_builder.statewide_map_data(package_id)
                    county_level = payload.get("geographyLevel") in {"azone", "county"}
                    collection = map_data.get("azones" if county_level else "bzones") or {}
                    id_key = "azoneId" if county_level else "bzoneId"
                    feature_names = {
                        str(feature.get("properties", {}).get(id_key)): str(feature.get("properties", {}).get("localityName") or feature.get("properties", {}).get("name") or "")
                        for feature in collection.get("features") or []
                        if feature.get("properties", {}).get(id_key)
                    }
                    scope_ids = set(feature_names)
                    scope_label = "All Virginia"
                    explicit_scope = {value for value in first(query, "scopeId").split("|") if value}
                    if explicit_scope:
                        scope_ids = explicit_scope
                        scope_label = "Project geography"
                    if region_id:
                        region = next((item for item in map_data.get("regions") or [] if item.get("id") == region_id), {})
                        scope_ids = {
                            str(value)
                            for value in (region.get("azoneFips") if county_level else region.get("selectedBzones") or [])
                        }
                        scope_label = region.get("name") or region_id
                    if payload.get("geographyLevel") == "marea":
                        bzone_scope = scope_ids
                        scope_ids = {
                            str(marea)
                            for marea, bzones in (payload.get("mareaBzones") or {}).items()
                            if set(map(str, bzones or [])).intersection(bzone_scope)
                        }
                        feature_names = {str(item.get("geographyId")): str(item.get("name", "")) for item in payload.get("geographyRows") or []}
                    rows = application.comparison.comparison_map_scope_rows(payload["mapToken"], scope_ids, feature_names)
                    export_rows = [{
                        "geography_id": item.get("geographyId"), "geography": item.get("name"),
                        "member_bzones": "|".join(map(str, (payload.get("mareaBzones") or {}).get(str(item.get("geographyId")), []))) if payload.get("geographyLevel") == "marea" else "",
                        "reference_value": item.get("referenceValue"), "comparison_value": item.get("comparisonValue"),
                        "reference_rows": item.get("referenceCount"), "comparison_rows": item.get("comparisonCount"),
                        "absolute_change": item.get("absoluteChange"), "change_percent": item.get("percentChange"),
                        "aggregation": payload.get("aggregation", "mean"), "units": payload.get("units", ""), "year": payload.get("year", ""), "scope": scope_label,
                    } for item in rows]
                    send_bytes(self, application.comparison.csv_bytes(export_rows), "text/csv; charset=utf-8", "visioneval_comparison_map.csv")
                elif parsed.path.startswith("/api/comparison/export-"):
                    comparisons = [item for item in first(query, "comparisons").split(",") if item]
                    export_type = parsed.path.rsplit("/", 1)[-1]
                    if export_type not in {"export-current", "export-filtered-changes", "export-change-summary", "export-dashboard-pdf"}:
                        raise WorkspaceError("Unknown comparison export")
                    if export_type == "export-change-summary":
                        scan_id = first(query, "scanId")
                        status = application.comparison_scans.status(scan_id) if scan_id else {}
                        result = status.get("result") if status.get("state") == "succeeded" else application.comparison.changes(first(query, "reference"), comparisons, first(query, "year", "2045"), first(query, "filterField"), csv_values(query, "filterValue"))
                        rows = []
                        for item in result["results"]:
                            row = {"output": f"{item.get('table', '')} / {item.get('variable', '')}"}
                            for index, pair in enumerate(item.get("pairStats") or [], 1):
                                row[f"{pair.get('label', f'Comparison {index}')} Change %"] = pair.get("totalPercentChange")
                            rows.append(row)
                        send_bytes(self, application.comparison.csv_bytes(rows), "text/csv; charset=utf-8", "change_summary.csv")
                    else:
                        token = first(query, "comparisonToken")
                        try:
                            result = application.comparison.comparison_snapshot_page(token, export_type == "export-filtered-changes", 0, 0, first(query, "sortColumn", "id"), first(query, "sortDirection", "original")) if token else None
                        except WorkspaceError:
                            result = None
                        result = result or application.comparison.compare(first(query, "reference"), comparisons, first(query, "table"), first(query, "variable"), first(query, "year", "2045"), export_type == "export-filtered-changes", 0, 0, first(query, "filterField"), csv_values(query, "filterValue"), first(query, "sortColumn", "id"), first(query, "sortDirection", "original"), mode=first(query, "mode", "auto"))
                        rows = []
                        if result.get("mode") == "aggregate":
                            labels = [(result.get("reference") or {}).get("label", "Reference"), *[(item.get("label") or f"Comparison {index + 1}") for index, item in enumerate(result.get("comparisons") or [])]]
                            summaries = result.get("aggregateSummaries") or []
                            changes = result.get("aggregateChanges") or []
                            for measure in ("recordCount", "numericCount", "missingCount", "sum", "mean", "min", "q1", "median", "q3", "max"):
                                out = {"measure": measure}
                                for label, summary in zip(labels, summaries): out[label] = summary.get(measure)
                                for index, change in enumerate(changes):
                                    detail = (change.get("measures") or {}).get(measure) or {}
                                    out[f"{labels[index + 1]} change"] = detail.get("change")
                                    out[f"{labels[index + 1]} change_percent"] = detail.get("percentChange")
                                rows.append(out)
                            categories = sorted({item.get("label", "") for summary in summaries for item in summary.get("categories") or []})
                            for category in categories:
                                counts, shares = {}, {}
                                for label, summary in zip(labels, summaries):
                                    detail = next((item for item in summary.get("categories") or [] if item.get("label") == category), {})
                                    counts[label], shares[label] = detail.get("count", 0), detail.get("share", 0)
                                rows.append({"measure": f"category count: {category}", **counts})
                                rows.append({"measure": f"category share %: {category}", **shares})
                        else:
                            for row in result["rows"]:
                                out = {"id":row["id"], "reference":row["reference"]}
                                for index, value in enumerate(row["comparisons"], 1): out[f"comparison_{index}"] = value; out[f"change_percent_{index}"] = row["percentChanges"][index-1]
                                rows.append(out)
                        send_bytes(self, application.comparison.csv_bytes(rows), "text/csv; charset=utf-8", f"{result['table']}_{result['variable']}_{export_type}.csv")
                else:
                    super().do_GET()
            except (WorkspaceError, ValueError, OSError, json.JSONDecodeError) as exc:
                application.diagnostics.record_app_error({"source": "backend", "message": str(exc), "path": parsed.path})
                send_json(self, {"error": str(exc)}, 400)
            except Exception as exc:
                application.diagnostics.record_app_error({"source": "backend", "message": str(exc), "path": parsed.path})
                send_json(self, {"error": str(exc)}, 500)

        def _stream_events(self, job_id: str, offset: int):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            try:
                while True:
                    chunk = application.runtime.log_chunk(job_id, offset)
                    offset = chunk["offset"]
                    data = json.dumps(chunk, ensure_ascii=False).replace("\n", "\\n")
                    self.wfile.write(f"id: {offset}\ndata: {data}\n\n".encode("utf-8"))
                    self.wfile.flush()
                    if chunk["terminal"]:
                        break
                    time.sleep(1)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_POST(self):
            parsed = urlparse(self.path)
            try:
                payload = json_body(self)
                if parsed.path == "/api/assets/bundled/planrva/install":
                    send_json(self, application.bundled_assets.install_planrva())
                elif parsed.path == "/api/packages/preview":
                    send_json(self, application.preview_package(str(payload.get("source", ""))))
                elif parsed.path == "/api/packages/install":
                    source = payload.get("source", "")
                    token = str(payload.get("token", ""))
                    preview = application.preview_package(str(source))
                    if not token or token != preview.get("token") or token not in application.package_previews:
                        raise WorkspaceError("The selected package changed after preview. Review it again before installing.")
                    package_type = package_manifest_type(source)
                    if package_type == "input-explanations":
                        result = application.input_explanations.install(source)
                    elif package_type == "model-bundle":
                        result = application.model_packages.install(source)
                    elif package_type == "region-builder":
                        result = application.region_packages.install(source)
                    else:
                        raise WorkspaceError(f"Unsupported Workbench package type: {package_type or 'unknown'}")
                    application.package_previews.pop(token, None)
                    send_json(self, result, 201)
                elif parsed.path == "/api/packages/input-explanations/remove":
                    send_json(self, application.workspace.archive_asset("input-explanations", payload.get("id", "")))
                elif parsed.path == "/api/packages/regions/remove":
                    send_json(self, application.workspace.archive_asset("regional-data", payload.get("id", "")))
                elif parsed.path == "/api/assets/archive":
                    send_json(self, application.workspace.archive_asset(
                        str(payload.get("kind", "")), str(payload.get("id", "")), bool(payload.get("includeRelated", False))
                    ))
                elif parsed.path == "/api/assets/restore":
                    send_json(self, application.workspace.restore_asset(str(payload.get("archiveId", ""))))
                elif parsed.path == "/api/assets/purge":
                    send_json(self, application.workspace.purge_asset(str(payload.get("archiveId", ""))))
                elif parsed.path == "/api/settings":
                    settings = application.workspace.update_settings(payload)
                    application.update_checks.settings_changed()
                    send_json(self, settings)
                elif parsed.path == "/api/updates/check":
                    requested = payload.get("sources")
                    if requested is not None and not isinstance(requested, list):
                        raise WorkspaceError("Update sources must be a list")
                    send_json(self, application.update_checks.check(force=True, sources=requested))
                elif parsed.path == "/api/diagnostics/app-error":
                    send_json(self, application.diagnostics.record_app_error(payload), 201)
                elif parsed.path == "/api/templates/import":
                    send_json(self, application.workspace.import_template(payload.get("source", ""), payload.get("name", "")), 201)
                elif parsed.path == "/api/templates/validate":
                    path = application.workspace.external_directory(payload.get("source", ""))
                    send_json(self, application.workspace.validate_template(path))
                elif parsed.path == "/api/region-builder/preview":
                    send_json(self, application.region_builder.preview(payload))
                elif parsed.path == "/api/region-builder/build":
                    send_json(self, application.region_builder.build(payload), 201)
                elif parsed.path == "/api/projects":
                    send_json(self, application.workspace.create_project(payload), 201)
                elif parsed.path == "/api/projects/copy":
                    send_json(self, application.workspace.copy_project(
                        payload.get("projectId", ""), payload.get("name", ""), bool(payload.get("includeResults"))
                    ), 201)
                elif parsed.path == "/api/projects/copy/start":
                    send_json(self, application.copy_operations.start_project(payload), 202)
                elif parsed.path == "/api/projects/copy/cancel":
                    send_json(self, application.copy_operations.cancel(payload.get("id", "")))
                elif parsed.path == "/api/projects/hypercubes/preview":
                    send_json(self, application.hypercubes.preview(payload))
                elif parsed.path == "/api/projects/hypercubes/draft":
                    send_json(self, application.hypercubes.service.save_draft(payload))
                elif parsed.path == "/api/projects/hypercubes/start":
                    send_json(self, application.hypercubes.start(payload), 202)
                elif parsed.path == "/api/projects/hypercubes/cancel":
                    send_json(self, application.hypercubes.cancel(payload.get("id", "")))
                elif parsed.path == "/api/hypercube-analysis/matrix":
                    send_json(self, application.hypercube_analysis.matrix(payload))
                elif parsed.path == "/api/hypercube-analysis/operations/start":
                    send_json(self, application.hypercube_analysis_operations.start(payload), 202)
                elif parsed.path == "/api/hypercube-analysis/operations/cancel":
                    send_json(self, application.hypercube_analysis_operations.cancel(payload.get("id", "")))
                elif parsed.path == "/api/hypercube-analysis/cleanup-exports":
                    send_json(self, application.hypercube_analysis.cleanup_exports(payload.get("projectId", "")))
                elif parsed.path == "/api/hypercube-run/start":
                    send_json(self, application.hypercube_analysis.start_run_plan(payload), 201)
                elif parsed.path == "/api/hypercube-run/stop":
                    send_json(self, application.runtime.stop_project(str(payload.get("projectId", ""))))
                elif parsed.path == "/api/hypercube-analysis/discovery/start":
                    send_json(self, application.hypercube_discovery.start(payload), 202)
                elif parsed.path == "/api/hypercube-analysis/discovery/cached":
                    send_json(self, application.hypercube_discovery.cached(payload))
                elif parsed.path == "/api/hypercube-analysis/discovery/cancel":
                    send_json(self, application.hypercube_discovery.cancel(payload.get("id", "")))
                elif parsed.path == "/api/hypercube-exports/start":
                    send_json(self, application.hypercube_case_exports.start(payload), 202)
                elif parsed.path == "/api/hypercube-exports/cancel":
                    send_json(self, application.hypercube_case_exports.cancel(payload.get("id", "")))
                elif parsed.path == "/api/projects/update":
                    send_json(self, application.workspace.update_project(payload.get("projectId", ""), payload.get("name", "")))
                elif parsed.path == "/api/projects/baseline/update":
                    send_json(self, application.workspace.update_baseline_name(payload.get("projectId", ""), payload.get("displayName", "")))
                elif parsed.path == "/api/projects/remove":
                    send_json(self, application.workspace.remove_project(payload.get("projectId", "")))
                elif parsed.path == "/api/projects/restore":
                    send_json(self, application.workspace.restore_project(payload.get("projectId", "")))
                elif parsed.path == "/api/projects/purge":
                    send_json(self, application.workspace.purge_project(payload.get("projectId", "")))
                elif parsed.path == "/api/projects/cleanup":
                    send_json(self, application.workspace.cleanup_archives())
                elif parsed.path == "/api/workspace/repair":
                    send_json(self, application.workspace.repair_workspace())
                elif parsed.path == "/api/projects/archive-all":
                    send_json(self, application.workspace.archive_all_projects())
                elif parsed.path == "/api/projects/wipe-all":
                    send_json(self, application.workspace.wipe_project_data(str(payload.get("confirmation", ""))))
                elif parsed.path == "/api/projects/import-v1":
                    send_json(self, self._import_v1(payload), 201)
                elif parsed.path == "/api/projects/variations":
                    send_json(self, application.workspace.add_variation(payload.get("projectId", ""), payload.get("name", ""), payload.get("duplicateFrom", "")), 201)
                elif parsed.path == "/api/projects/variations/copy":
                    destination = payload.get("destination") or {}
                    send_json(self, application.workspace.copy_variations(
                        payload.get("sourceProjectId", ""), payload.get("variationIds") or [],
                        target_project_id=destination.get("projectId", ""),
                        new_project_name=destination.get("name", ""),
                        include_results=bool(payload.get("includeResults")),
                    ), 201)
                elif parsed.path == "/api/projects/variations/copy/start":
                    send_json(self, application.copy_operations.start_variations(payload), 202)
                elif parsed.path == "/api/projects/variations/update":
                    send_json(self, application.workspace.update_variation(payload.get("projectId", ""), payload.get("variationId", ""), payload.get("name") if "name" in payload else None, payload.get("notes") if "notes" in payload else None, payload.get("scenarioNote") if "scenarioNote" in payload else None, payload.get("fileNote") if "fileNote" in payload else None))
                elif parsed.path == "/api/projects/variations/delete":
                    send_json(self, application.workspace.delete_variation(payload.get("projectId", ""), payload.get("variationId", "")))
                elif parsed.path == "/api/projects/results/unlink":
                    send_json(self, application.workspace.unlink_result(payload.get("projectId", ""), payload.get("datastoreId", "")))
                elif parsed.path == "/api/overlays":
                    source_path, _ = application.workspace.input_file(
                        application.workspace.project(payload.get("projectId", ""))[1]["inputLibrary"]["id"],
                        payload.get("filename", ""),
                    )
                    with source_path.open("r", encoding="utf-8-sig", newline="") as handle:
                        source_rows = list(csv.reader(handle))
                    current_path, _ = application.workspace.input_file(
                        application.workspace.project(payload.get("projectId", ""))[1]["inputLibrary"]["id"],
                        payload.get("filename", ""), payload.get("projectId", ""), payload.get("variationId", ""),
                    )
                    with current_path.open("r", encoding="utf-8-sig", newline="") as handle:
                        current_rows = list(csv.reader(handle))
                    metadata = application.explore.input_column_metadata(
                        payload.get("filename", ""), payload.get("columns") or [], source_rows[1:], current_rows[1:]
                    )
                    application.explore.validate_input_rows(
                        payload.get("filename", ""), payload.get("columns") or [], payload.get("rows") or [], current_rows[1:], metadata
                    )
                    application.explore.validate_categorical_operations(metadata, payload.get("editOperations"))
                    content = self._csv_content(payload)
                    send_json(self, application.workspace.save_overlay(
                        payload.get("projectId", ""), payload.get("variationId", ""),
                        payload.get("filename", ""), content,
                        payload.get("editOperations") if "editOperations" in payload else None,
                    ), 201)
                elif parsed.path == "/api/overlays/batch":
                    project_id = str(payload.get("projectId", ""))
                    variation_id = str(payload.get("variationId", ""))
                    _, project = application.workspace.project(project_id)
                    library_id = str(project["inputLibrary"]["id"])
                    prepared: list[dict] = []
                    for item in payload.get("items") or []:
                        filename = str(item.get("filename", ""))
                        columns = item.get("columns") or []
                        rows = item.get("rows") or []
                        source_path, _ = application.workspace.input_file(library_id, filename)
                        current_path, _ = application.workspace.input_file(library_id, filename, project_id, variation_id)
                        with source_path.open("r", encoding="utf-8-sig", newline="") as handle:
                            source_rows = list(csv.reader(handle))
                        with current_path.open("r", encoding="utf-8-sig", newline="") as handle:
                            current_rows = list(csv.reader(handle))
                        metadata = application.explore.input_column_metadata(filename, columns, source_rows[1:], current_rows[1:])
                        application.explore.validate_input_rows(filename, columns, rows, current_rows[1:], metadata)
                        application.explore.validate_categorical_operations(metadata, item.get("editOperations"))
                        prepared.append({
                            "filename": filename,
                            "content": self._csv_content(item),
                            "editOperations": item.get("editOperations") if "editOperations" in item else None,
                        })
                    send_json(self, application.workspace.save_overlays_atomic(project_id, variation_id, prepared), 201)
                elif parsed.path == "/api/overlays/delete":
                    send_json(self, application.workspace.delete_overlay(payload.get("projectId", ""), payload.get("variationId", ""), payload.get("filename", "")))
                elif parsed.path == "/api/runtime/pull":
                    send_json(self, application.runtime.pull_image())
                elif parsed.path == "/api/runtime/install":
                    profile = application.update_checks.runtime_candidate() if payload.get("source") == "update" else None
                    send_json(self, application.runtime.install_or_update_runtime(profile))
                elif parsed.path == "/api/runtime/install/start":
                    profile = application.update_checks.runtime_candidate() if payload.get("source") == "update" else None
                    send_json(self, application.runtime_installations.start(profile), 202)
                elif parsed.path == "/api/runtime/restore-previous":
                    send_json(self, application.runtime.restore_previous_runtime())
                elif parsed.path == "/api/runtime/discover":
                    send_json(self, application.runtime.discover_native(payload.get("veRuntime", "")))
                elif parsed.path == "/api/runtime/verify":
                    if application.runtime.adapter == "native":
                        application.runtime.configure_native(payload.get("veRuntime", ""), payload.get("veHome", ""), payload.get("rscript", ""))
                    send_json(self, application.runtime.verify_runtime())
                elif parsed.path == "/api/runtime/shutdown":
                    send_json(self, application.runtime.shutdown(bool(payload.get("cancelActive"))))
                elif parsed.path == "/api/operations/stop-all":
                    send_json(self, application.stop_background_operations())
                elif parsed.path == "/api/batches":
                    send_json(self, application.runtime.create_batch(
                        payload.get("projectId", ""), payload.get("variationIds") or [],
                        bool(payload.get("includeBaseline")), payload.get("mode", "queued"),
                        payload.get("forceRerunVariationIds") or [],
                    ), 201)
                elif parsed.path == "/api/runs/cancel":
                    send_json(self, application.runtime.cancel(payload.get("jobId", "")))
                elif parsed.path == "/api/runs/stop-all":
                    send_json(self, application.runtime.stop_all())
                elif parsed.path == "/api/backend/shutdown":
                    send_json(self, {"ok": True})
                    threading.Thread(target=self.server.shutdown, daemon=True, name="backend-shutdown").start()
                elif parsed.path == "/api/runs/queue/reorder":
                    send_json(self, application.runtime.reorder_queue(payload.get("jobIds") or [], payload.get("revision")))
                elif parsed.path == "/api/runs/queue/remove":
                    send_json(self, application.runtime.remove_waiting(payload.get("jobId", "")))
                elif parsed.path == "/api/runs/history/remove":
                    send_json(self, application.runtime.remove_history(payload.get("jobId", "")))
                elif parsed.path == "/api/runs/history/clear":
                    send_json(self, application.runtime.clear_history(require_idle=True))
                elif parsed.path == "/api/runs/cleanup/retry":
                    send_json(self, application.runtime.retry_cleanup(payload.get("jobId", "")))
                elif parsed.path == "/api/runs/retry":
                    send_json(self, application.runtime.retry(payload.get("jobId", "")), 201)
                elif parsed.path in {"/api/comparison/cache/clear", "/api/comparison/cache/rebuild"}:
                    send_json(self, application.comparison.clear_cache())
                elif parsed.path == "/api/comparison/operations/start":
                    send_json(self, application.comparison_operations.start(payload), 202)
                elif parsed.path == "/api/comparison/page":
                    send_json(self, application.comparison.comparison_snapshot_page(
                        payload.get("comparisonToken", ""), bool(payload.get("changedOnly")),
                        int(payload.get("limit", 100)), int(payload.get("offset", 0)),
                        payload.get("sortColumn", "id"), payload.get("sortDirection", "original"),
                    ))
                elif parsed.path == "/api/comparison/operations/cancel":
                    send_json(self, application.comparison_operations.cancel(payload.get("id", "")))
                elif parsed.path == "/api/comparison/exports/start":
                    send_json(self, application.comparison_exports.start(payload), 202)
                elif parsed.path == "/api/comparison/exports/cancel":
                    send_json(self, application.comparison_exports.cancel(payload.get("id", "")))
                elif parsed.path == "/api/comparison/scans/start":
                    send_json(self, application.comparison_scans.start(payload.get("reference", ""), payload.get("comparisons") or [], str(payload.get("year", "2045")), payload.get("filterField", ""), payload.get("filterValues") or []), 202)
                elif parsed.path == "/api/comparison/scans/cancel":
                    send_json(self, application.comparison_scans.cancel(payload.get("id", "")))
                else:
                    send_json(self, {"error": "Unknown endpoint"}, 404)
            except InputValidationError as exc:
                application.diagnostics.record_app_error({"source": "backend", "message": str(exc), "path": parsed.path})
                send_json(self, {"error": str(exc), "code": "input_validation", "validationErrors": exc.errors}, 400)
            except (WorkspaceError, ValueError, OSError, csv.Error, json.JSONDecodeError) as exc:
                application.diagnostics.record_app_error({"source": "backend", "message": str(exc), "path": parsed.path})
                send_json(self, {"error": str(exc)}, 400)
            except Exception as exc:
                application.diagnostics.record_app_error({"source": "backend", "message": str(exc), "path": parsed.path})
                send_json(self, {"error": str(exc)}, 500)

        @staticmethod
        def _csv_content(payload: dict) -> str:
            output = io.StringIO(newline="")
            writer = csv.writer(output, lineterminator="\n")
            writer.writerow(payload.get("columns") or [])
            writer.writerows(payload.get("rows") or [])
            return output.getvalue()

        @staticmethod
        def _import_v1(payload: dict):
            source = application.workspace.external_directory(payload.get("source", ""))
            manifest_path = source / "scenario_manifest.json"
            if not manifest_path.is_file():
                raise WorkspaceError("scenario_manifest.json was not found")
            legacy = json.loads(manifest_path.read_text(encoding="utf-8"))
            library_id = str(payload.get("inputLibraryId", ""))
            template_id = str(payload.get("templateId", ""))
            # V1 imports predate package registrations. Preserve the explicit
            # pair selected for that migration so normal server-side pairing
            # validation can remain authoritative for the resulting project.
            if library_id and template_id:
                application.workspace.input_library_pairing(library_id)
                application.workspace.template(template_id)
                application.workspace.record_asset_registration({
                    "id": f"legacy-import-pair:{library_id}:{template_id}",
                    "type": "legacy-import-pair",
                    "installedAt": now_iso(),
                    "assets": [
                        {"kind": "input-library", "id": library_id},
                        {"kind": "model-template", "id": template_id},
                    ],
                })
            project = application.workspace.create_project({
                "name": payload.get("name") or legacy.get("projectName") or source.name,
                "templateId": template_id,
                "inputLibraryId": library_id,
                "baseline": payload.get("baseline") or {"strategy": "fresh"},
                "variations": [{"name": sim.get("name") or "Scenario"} for sim in legacy.get("sims", [])],
            })
            directory, project = application.workspace.project(project["id"])
            shutil.copy2(manifest_path, directory / "legacy_scenario_manifest.json")
            project["legacyImport"] = {"source": str(source), "manifestVersion": legacy.get("version"), "manifest": "legacy_scenario_manifest.json"}
            for variant, sim in zip(project["variations"], legacy.get("sims", [])):
                inputs = source / sim.get("name", "") / "inputs"
                if inputs.is_dir():
                    for file in inputs.glob("*.csv"):
                        baseline_file = application.workspace.input_library / project["inputLibrary"]["id"] / file.name
                        if baseline_file.exists() and file.read_bytes() != baseline_file.read_bytes():
                            application.workspace.save_overlay(project["id"], variant["id"], file.name, file.read_text(encoding="utf-8"))
            _, project = application.workspace.project(project["id"])
            project["legacyImport"] = {"source": str(source), "manifestVersion": legacy.get("version"), "manifest": "legacy_scenario_manifest.json"}
            application.workspace.save_project(project)
            return project

    return Handler


def serve(workspace: str | Path, public_root: str | Path, resource_root: str | Path, port: int) -> None:
    application = WorkbenchApplication(workspace, public_root, resource_root)
    server = ThreadingHTTPServer(("127.0.0.1", port), handler_class(application))
    print(f"VisionEval Workbench: http://127.0.0.1:{port}", flush=True)
    print(f"Workspace: {application.workspace.root}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
