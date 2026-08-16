from __future__ import annotations

import csv
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
from .dependencies import DependencyService
from .documentation import DocumentationService
from .diagnostics import DiagnosticsService
from .explore import ExploreService
from .excel_exports import ComparisonExportManager
from .input_explanations import InputExplanationPackageService
from .model_packages import ModelPackageService
from .region_packages import RegionPackageService, package_manifest_type
from .runtime import RuntimeManager
from .region_builder import RegionBuilderService
from .workspace import Workspace, WorkspaceError, read_json

# Windows' MIME registry does not consistently know modern JavaScript module
# extensions. Chromium refuses to execute an ES module served as text/plain.
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/json", ".json")
mimetypes.add_type("text/markdown", ".md")


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
        conflicts_target = self.workspace.exchange / "system" / "unit_conflicts.json"
        conflicts_source = self.resource_root / "unit_conflicts.json"
        if not conflicts_target.exists() or conflicts_target.read_bytes() != conflicts_source.read_bytes():
            shutil.copy2(conflicts_source, conflicts_target)
        runtime_cli = self.resource_root / "ve-cli-native.R"
        if not runtime_cli.is_file():
            runtime_cli = self.resource_root.parent / "runtime" / "scripts" / "ve-cli-native.R"
        self.runtime = RuntimeManager(self.workspace, cli_path=runtime_cli)
        self.diagnostics = DiagnosticsService(self.workspace, self.runtime, __version__)
        self.comparison = ComparisonService(self.workspace, self.runtime, helper_target, scan_target, conflicts_target, cache_extractor_target)
        self.comparison_operations = ComparisonOperationManager(self.comparison)
        self.comparison_scans = ComparisonScanManager(self.comparison)
        self.comparison_exports = ComparisonExportManager(self.comparison)
        self.input_explanations = InputExplanationPackageService(self.workspace)
        self.model_packages = ModelPackageService(self.workspace)
        self.region_packages = RegionPackageService(self.workspace)
        self.explore = ExploreService(self.workspace, self.resource_root / "explore_catalog.json", self.resource_root / "unit_conflicts.json", self.resource_root / "dependency_catalog.json")
        self.dependencies = DependencyService(self.workspace, self.resource_root / "dependency_catalog.json")
        self.region_builder = RegionBuilderService(self.workspace, self.resource_root, self.region_packages)
        self._last_archive_cleanup = 0.0
        self._cleanup_archives()

    def _cleanup_archives(self) -> None:
        now = time.monotonic()
        if now - self._last_archive_cleanup >= 86400 or not self._last_archive_cleanup:
            self.workspace.cleanup_archives()
            self._last_archive_cleanup = now

    def state(self) -> dict:
        self._cleanup_archives()
        runtime_status = self.runtime.docker_status()
        return {
            "app": "VisionEval Workbench",
            "version": __version__,
            "workspace": str(self.workspace.root),
            "inputLibraries": self.workspace.list_input_libraries(),
            "inputExplanations": self.input_explanations.list(),
            "regionPackages": self.region_packages.list(),
            "comparisonMapPackages": self.region_packages.comparison_map_providers(),
            "templates": self.workspace.list_templates(),
            "projects": self.workspace.list_projects(),
            "jobs": self.runtime.list_jobs(),
            "queue": self.runtime.queue(),
            "catalog": self.workspace.catalog(False, False)["datastores"],
            "archivedProjects": self.workspace.list_archived_projects(),
            "runtime": runtime_status,
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
    try:
        handler.wfile.write(body)
    except (BrokenPipeError, ConnectionResetError):
        # The WebView can discard an in-flight response when a dialog closes,
        # the workspace reloads, or the backend reconnects. The operation may
        # already have completed successfully, so this is not an application
        # or runtime failure and must not be added to Diagnostics.
        return


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
                elif parsed.path == "/api/settings":
                    send_json(self, application.workspace.settings())
                elif parsed.path == "/api/documentation/user-guide":
                    send_json(self, application.documentation.user_guide())
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
                elif parsed.path == "/api/project":
                    _, project = application.workspace.project(first(query, "id"))
                    send_json(self, project)
                elif parsed.path == "/api/input-file":
                    library_id, filename = first(query, "libraryId"), Path(first(query, "filename")).name
                    path, overlay = application.workspace.input_file(library_id, filename, first(query, "projectId"), first(query, "variationId"))
                    with path.open("r", encoding="utf-8-sig", newline="") as handle:
                        rows = list(csv.reader(handle))
                    columns = rows[0] if rows else []
                    send_json(self, {"filename": filename, "columns": columns, "columnTypes": application.explore.input_column_types(filename, columns), "rows": rows[1:], "overlay": overlay})
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
                    review = application.workspace.review_project(first(query, "projectId"))
                    review["validation"] = application.runtime.validate_project(first(query, "projectId"))
                    send_json(self, review)
                elif parsed.path == "/api/jobs":
                    send_json(self, {"jobs": application.runtime.list_jobs(first(query, "projectId"))})
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
                    send_json(self, {"datastores": application.workspace.catalog(False, include_hidden)["datastores"]})
                elif parsed.path == "/api/comparison/variables":
                    ids = [item for item in first(query, "ids").split(",") if item]
                    send_json(self, {"variables": application.comparison.variables(ids)})
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
                    rows = application.comparison.comparison_map_scope_rows(payload["mapToken"], scope_ids, feature_names)
                    export_rows = [{
                        "geography_id": item.get("geographyId"), "geography": item.get("name"),
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
                if parsed.path == "/api/setup/input-library":
                    send_json(self, application.workspace.copy_input_library(payload.get("source", "")), 201)
                elif parsed.path == "/api/assets/bundled/planrva/install":
                    send_json(self, application.bundled_assets.install_planrva())
                elif parsed.path == "/api/packages/install":
                    source = payload.get("source", "")
                    package_type = package_manifest_type(source)
                    if package_type == "input-explanations":
                        result = application.input_explanations.install(source)
                    elif package_type == "model-bundle":
                        result = application.model_packages.install(source)
                    elif package_type == "region-builder":
                        result = application.region_packages.install(source)
                    else:
                        raise WorkspaceError(f"Unsupported Workbench package type: {package_type or 'unknown'}")
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
                    application.runtime.set_release_check_enabled(settings["checkVisionEvalUpdates"])
                    send_json(self, settings)
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
                elif parsed.path == "/api/projects/import-v1":
                    send_json(self, self._import_v1(payload), 201)
                elif parsed.path == "/api/projects/variations":
                    send_json(self, application.workspace.add_variation(payload.get("projectId", ""), payload.get("name", ""), payload.get("duplicateFrom", "")), 201)
                elif parsed.path == "/api/projects/variations/update":
                    send_json(self, application.workspace.update_variation(payload.get("projectId", ""), payload.get("variationId", ""), payload.get("name") if "name" in payload else None, payload.get("notes") if "notes" in payload else None, payload.get("scenarioNote") if "scenarioNote" in payload else None))
                elif parsed.path == "/api/projects/variations/delete":
                    send_json(self, application.workspace.delete_variation(payload.get("projectId", ""), payload.get("variationId", "")))
                elif parsed.path == "/api/overlays":
                    application.explore.validate_input_rows(
                        payload.get("filename", ""), payload.get("columns") or [], payload.get("rows") or []
                    )
                    content = self._csv_content(payload)
                    send_json(self, application.workspace.save_overlay(payload.get("projectId", ""), payload.get("variationId", ""), payload.get("filename", ""), content), 201)
                elif parsed.path == "/api/overlays/delete":
                    send_json(self, application.workspace.delete_overlay(payload.get("projectId", ""), payload.get("variationId", ""), payload.get("filename", "")))
                elif parsed.path == "/api/runtime/pull":
                    send_json(self, application.runtime.pull_image())
                elif parsed.path == "/api/runtime/install":
                    send_json(self, application.runtime.install_or_update_runtime())
                elif parsed.path == "/api/runtime/discover":
                    send_json(self, application.runtime.discover_native(payload.get("veRuntime", "")))
                elif parsed.path == "/api/runtime/verify":
                    if application.runtime.adapter == "native":
                        application.runtime.configure_native(payload.get("veRuntime", ""), payload.get("veHome", ""), payload.get("rscript", ""))
                    send_json(self, application.runtime.verify_runtime())
                elif parsed.path == "/api/runtime/shutdown":
                    send_json(self, application.runtime.shutdown(bool(payload.get("cancelActive"))))
                elif parsed.path == "/api/batches":
                    send_json(self, application.runtime.create_batch(payload.get("projectId", ""), payload.get("variationIds") or [], bool(payload.get("includeBaseline")), payload.get("mode", "queued")), 201)
                elif parsed.path == "/api/runs/cancel":
                    send_json(self, application.runtime.cancel(payload.get("jobId", "")))
                elif parsed.path == "/api/runs/stop-all":
                    send_json(self, application.runtime.stop_all())
                elif parsed.path == "/api/runs/queue/reorder":
                    send_json(self, application.runtime.reorder_queue(payload.get("jobIds") or [], payload.get("revision")))
                elif parsed.path == "/api/runs/queue/remove":
                    send_json(self, application.runtime.remove_waiting(payload.get("jobId", "")))
                elif parsed.path == "/api/runs/history/remove":
                    send_json(self, application.runtime.remove_history(payload.get("jobId", "")))
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
            project = application.workspace.create_project({
                "name": payload.get("name") or legacy.get("projectName") or source.name,
                "templateId": payload.get("templateId", ""),
                "inputLibraryId": payload.get("inputLibraryId", ""),
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
