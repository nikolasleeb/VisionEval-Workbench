from __future__ import annotations

import hashlib
import csv
import io
import json
import re
import threading
import time
import zipfile
from pathlib import Path
from typing import Any, Callable

from .workspace import WorkspaceError, make_id, now_iso, read_json, write_json


EXCEL_MAX_DATA_ROWS = 1_048_575
TERMINAL_STATES = {"succeeded", "failed", "cancelled"}


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")
    return (cleaned or "visioneval_comparison")[:120]


def _registration_fingerprint(record: dict[str, Any]) -> str:
    public = {key: value for key, value in record.items() if key not in {"path", "source"}}
    return record.get("registrationFingerprint") or hashlib.sha256(json.dumps(public, sort_keys=True, default=str).encode()).hexdigest()


class WorkbookWriter:
    def __init__(self, path: Path, app_version: str = "1.0.0"):
        try:
            import xlsxwriter
        except ImportError as exc:
            raise WorkspaceError("Excel export support is unavailable in this build") from exc
        self.xlsxwriter = xlsxwriter
        self.path = path
        self.app_version = app_version

    @staticmethod
    def _write_value(sheet, row: int, column: int, value: Any, formats: dict[str, Any], delta: bool = False) -> None:
        if value is None:
            sheet.write_blank(row, column, None, formats["blank"])
        elif isinstance(value, bool):
            sheet.write_boolean(row, column, value)
        elif isinstance(value, (int, float)):
            style = formats["delta_positive"] if delta and value > 0 else formats["delta_negative"] if delta and value < 0 else formats["number"]
            sheet.write_number(row, column, value, style)
        else:
            sheet.write_string(row, column, str(value), formats["text"])

    @staticmethod
    def _sheet_name(base: str, index: int) -> str:
        suffix = f" {index}" if index > 1 else ""
        return (base[: 31 - len(suffix)] + suffix)[:31]

    def _formats(self, workbook) -> dict[str, Any]:
        return {
            "title": workbook.add_format({"bold": True, "font_size": 15, "font_color": "#1F4E78"}),
            "header": workbook.add_format({"bold": True, "font_color": "#FFFFFF", "bg_color": "#1F4E78", "border": 1, "text_wrap": True}),
            "text": workbook.add_format({"num_format": "@"}),
            "number": workbook.add_format({"num_format": "0.#####"}),
            "delta_positive": workbook.add_format({"num_format": "0.#####", "font_color": "#1F4E78", "bg_color": "#DCEAF7"}),
            "delta_negative": workbook.add_format({"num_format": "0.#####", "font_color": "#9C4A16", "bg_color": "#FCE4D6"}),
            "blank": workbook.add_format({"num_format": "General"}),
            "label": workbook.add_format({"bold": True, "bg_color": "#D9EAF7"}),
            "percent": workbook.add_format({"num_format": "0.00%"}),
        }

    def _write_table_sheets(self, workbook, base_name: str, headers: list[str], rows: list[list[Any]], delta_columns: set[int], formats: dict[str, Any], cancelled: Callable[[], bool]) -> list[str]:
        chunks = [rows[index:index + EXCEL_MAX_DATA_ROWS] for index in range(0, len(rows), EXCEL_MAX_DATA_ROWS)] or [[]]
        names = []
        for sheet_index, chunk in enumerate(chunks, 1):
            if cancelled():
                raise WorkspaceError("Excel export cancelled")
            name = self._sheet_name(base_name, sheet_index)
            names.append(name)
            sheet = workbook.add_worksheet(name)
            sheet.freeze_panes(1, 1)
            sheet.autofilter(0, 0, max(0, len(chunk)), max(0, len(headers) - 1))
            for column, header in enumerate(headers):
                sheet.write_string(0, column, str(header), formats["header"])
                sheet.set_column(column, column, min(42, max(12, len(str(header)) + 2)))
            for row_index, values in enumerate(chunk, 1):
                if row_index % 10_000 == 0 and cancelled():
                    raise WorkspaceError("Excel export cancelled")
                for column, value in enumerate(values):
                    self._write_value(sheet, row_index, column, value, formats, column in delta_columns)
        return names

    def _write_statistics(self, workbook, payload: dict[str, Any], formats: dict[str, Any]) -> None:
        sheet = workbook.add_worksheet("Statistics")
        sheet.set_column(0, 0, 28); sheet.set_column(1, 4, 18)
        sheet.write_string(0, 0, "VisionEval comparison statistics", formats["title"])
        headers = ["Comparison", "Rows compared", "Rows changed", "Net change", "Total percent change"]
        for column, header in enumerate(headers): sheet.write_string(2, column, header, formats["header"])
        for row_index, item in enumerate(payload.get("stats") or [], 3):
            values = [item.get("label"), item.get("rowsCompared"), item.get("rowsChanged"), item.get("netChange"), (item.get("totalPercentChange") / 100) if item.get("totalPercentChange") is not None else None]
            for column, value in enumerate(values):
                if column == 4 and value is not None: sheet.write_number(row_index, column, value, formats["percent"])
                else: self._write_value(sheet, row_index, column, value, formats)
        summary_row = 4 + len(payload.get("stats") or [])
        summaries = [((payload.get("reference") or {}).get("label", "Reference"), payload.get("referenceSummary") or {})]
        summaries.extend((record.get("label", f"Comparison {index + 1}"), summary) for index, (record, summary) in enumerate(zip(payload.get("comparisons") or [], payload.get("comparisonSummaries") or [])))
        sheet.write_string(summary_row, 0, "Dataset summaries", formats["title"])
        summary_headers = ["Dataset", "Kind", "Count", "Sum", "Mean", "Minimum", "Maximum", "Top categories"]
        for column, header in enumerate(summary_headers): sheet.write_string(summary_row + 1, column, header, formats["header"])
        sheet.set_column(7, 7, 42)
        for index, (label, summary) in enumerate(summaries, summary_row + 2):
            categories = ", ".join(f"{item.get('label')}: {item.get('count')}" for item in summary.get("topCategories") or [])
            values = [label, summary.get("kind"), summary.get("count"), summary.get("sum"), summary.get("mean"), summary.get("min"), summary.get("max"), categories]
            for column, value in enumerate(values): self._write_value(sheet, index, column, value, formats)

    def _write_provenance(self, workbook, payload: dict[str, Any], export_kind: str, formats: dict[str, Any]) -> None:
        sheet = workbook.add_worksheet("Provenance")
        sheet.set_column(0, 0, 30); sheet.set_column(1, 1, 80)
        sheet.write_string(0, 0, "VisionEval Workbench export provenance", formats["title"])
        records = [payload.get("reference") or {}, *(payload.get("comparisons") or [])]
        entries: list[tuple[str, Any]] = [
            ("Export type", export_kind), ("Generated at", now_iso()), ("Workbench version", self.app_version),
            ("Year", payload.get("year", "")), ("Table", payload.get("table", "")), ("Variable", payload.get("variable", "")),
            ("Units", (payload.get("metadata") or {}).get("units", "")), ("Comparison precision", "Five decimal places"),
            ("Geography filter", payload.get("filterField", "") or "All locations"),
            ("Filter values", ", ".join(str(value) for value in payload.get("filterValues") or []) or "All locations"),
        ]
        for index, record in enumerate(records):
            role = "Reference" if index == 0 else f"Comparison {index}"
            entries.extend([
                (f"{role} label", record.get("label", "")),
                (f"{role} datastore ID", record.get("id", "")),
                (f"{role} fingerprint", _registration_fingerprint(record)),
                (f"{role} verification", record.get("verification", "")),
            ])
        for row, (label, value) in enumerate(entries, 2):
            sheet.write_string(row, 0, label, formats["label"])
            self._write_value(sheet, row, 1, value, formats)

    @staticmethod
    def _comparison_table(payload: dict[str, Any]) -> tuple[list[str], list[list[Any]], set[int]]:
        reference = payload.get("reference") or {}
        comparisons = payload.get("comparisons") or []
        if payload.get("mode") == "aggregate":
            labels = [reference.get("label") or "Reference", *[item.get("label") or f"Comparison {index + 1}" for index, item in enumerate(comparisons)]]
            summaries = payload.get("aggregateSummaries") or []
            changes = payload.get("aggregateChanges") or []
            headers = ["Measure", labels[0]]
            delta_columns: set[int] = set()
            for label in labels[1:]:
                headers.extend([label, f"Change {label}", f"Change % {label}"])
                delta_columns.update({len(headers) - 2, len(headers) - 1})
            rows: list[list[Any]] = []
            for measure in ("recordCount", "numericCount", "missingCount", "sum", "mean", "min", "q1", "median", "q3", "max"):
                row = [measure, summaries[0].get(measure) if summaries else None]
                for index, summary in enumerate(summaries[1:]):
                    detail = ((changes[index].get("measures") or {}).get(measure) or {}) if index < len(changes) else {}
                    row.extend([summary.get(measure), detail.get("change"), detail.get("percentChange")])
                rows.append(row)
            categories = sorted({str(item.get("label", "")) for summary in summaries for item in summary.get("categories") or []})
            for category in categories:
                counts, shares = [], []
                for summary in summaries:
                    detail = next((item for item in summary.get("categories") or [] if str(item.get("label", "")) == category), {})
                    counts.append(detail.get("count", 0)); shares.append(detail.get("share", 0))
                count_row, share_row = [f"Category count: {category}", counts[0]], [f"Category share %: {category}", shares[0]]
                for index in range(1, len(counts)):
                    count_row.extend([counts[index], counts[index] - counts[0], None])
                    share_row.extend([shares[index], shares[index] - shares[0], None])
                rows.extend([count_row, share_row])
            return headers, rows, delta_columns
        headers = [payload.get("key") or "ID", reference.get("label") or "Reference"]
        delta_columns = set()
        for comparison in comparisons:
            headers.extend([comparison.get("label") or "Comparison", f"Change % {comparison.get('label') or 'Comparison'}"])
            delta_columns.add(len(headers) - 1)
        rows = []
        for item in payload.get("rows") or []:
            row = [str(item.get("id", "")), item.get("reference")]
            for value, percent in zip(item.get("comparisons") or [], item.get("percentChanges") or []): row.extend([value, percent])
            rows.append(row)
        return headers, rows, delta_columns

    def comparison(self, payload: dict[str, Any], export_kind: str, cancelled: Callable[[], bool]) -> str:
        workbook = self.xlsxwriter.Workbook(str(self.path), {"constant_memory": True, "strings_to_formulas": False, "strings_to_urls": False})
        try:
            formats = self._formats(workbook)
            headers, rows, delta_columns = self._comparison_table(payload)
            self._write_table_sheets(workbook, "Comparison", headers, rows, delta_columns, formats, cancelled)
            self._write_statistics(workbook, payload, formats)
            self._write_provenance(workbook, payload, export_kind, formats)
        finally:
            workbook.close()
        return _safe_filename(f"{payload.get('table','comparison')}_{payload.get('variable','values')}_{export_kind}.xlsx")

    def change_summary(self, payload: dict[str, Any], records: list[dict[str, Any]], cancelled: Callable[[], bool]) -> str:
        workbook = self.xlsxwriter.Workbook(str(self.path), {"constant_memory": True, "strings_to_formulas": False, "strings_to_urls": False})
        try:
            formats = self._formats(workbook)
            comparisons = records[1:]
            headers = ["Output"]
            headers.extend(f"{record.get('label') or f'Comparison {index}'} Change %" for index, record in enumerate(comparisons, 1))
            rows = []
            for item in payload.get("results") or []:
                pair_stats = item.get("pairStats") or []
                values = [f"{item.get('table', '')} / {item.get('variable', '')}"]
                values.extend((pair_stats[index].get("totalPercentChange") if index < len(pair_stats) else None) for index in range(len(comparisons)))
                rows.append(values)
            percent_change_columns = set(range(1, 1 + len(comparisons)))
            self._write_table_sheets(workbook, "Change Summary", headers, rows, percent_change_columns, formats, cancelled)
            provenance = {**payload, "reference": records[0] if records else {}, "comparisons": records[1:], "table": "All safe tables", "variable": "Changed variables", "metadata": {"units": "Mixed"}}
            self._write_provenance(workbook, provenance, "change-summary", formats)
        finally:
            workbook.close()
        return _safe_filename(f"change_summary_{payload.get('year','')}.xlsx")

    @staticmethod
    def _variable_sheet_base(table: str, variable: str, used: set[str], sheet_count: int) -> str:
        base = re.sub(r"[\[\]:*?/\\]+", "_", f"{table}-{variable}").strip() or "Variable"
        candidate = base[:31]
        index = 2
        candidate_names = lambda value: {
            WorkbookWriter._sheet_name(value, sheet_index).casefold()
            for sheet_index in range(1, sheet_count + 1)
        }
        while candidate_names(candidate) & used:
            suffix = f"-{index}"
            candidate = f"{base[:31-len(suffix)]}{suffix}"
            index += 1
        used.update(candidate_names(candidate))
        return candidate

    def full_variables(self, payloads, request: dict[str, Any], cancelled: Callable[[], bool], progress: Callable[[int, int, str], None]) -> str:
        workbook = self.xlsxwriter.Workbook(str(self.path), {"constant_memory": True, "strings_to_formulas": False, "strings_to_urls": False})
        try:
            formats = self._formats(workbook)
            index_sheet = workbook.add_worksheet("Index")
            index_sheet.set_column(0, 0, 36); index_sheet.set_column(1, 3, 18); index_sheet.set_column(4, 4, 60)
            index_sheet.write_string(0, 0, "VisionEval full variable comparison export", formats["title"])
            for column, header in enumerate(["Output", "Units", "Rows", "Worksheet count", "Worksheets"]):
                index_sheet.write_string(2, column, header, formats["header"])
            used = {"index", "provenance"}
            total = len(request.get("variableKeys") or [])
            provenance_payload = None
            for item_index, payload in enumerate(payloads, 1):
                if cancelled():
                    raise WorkspaceError("Full variable export cancelled")
                output_label = f"{payload.get('table', '')} / {payload.get('variable', '')}"
                progress(item_index - 1, total, output_label)
                headers, rows, delta_columns = self._comparison_table(payload)
                sheet_count = max(1, (len(rows) + EXCEL_MAX_DATA_ROWS - 1) // EXCEL_MAX_DATA_ROWS)
                base = self._variable_sheet_base(payload.get("table", ""), payload.get("variable", ""), used, sheet_count)
                sheet_names = self._write_table_sheets(workbook, base, headers, rows, delta_columns, formats, cancelled)
                values = [output_label, (payload.get("metadata") or {}).get("units", ""), len(rows), len(sheet_names), ", ".join(sheet_names)]
                for column, value in enumerate(values):
                    self._write_value(index_sheet, item_index + 2, column, value, formats)
                provenance_payload = provenance_payload or payload
                progress(item_index, total, output_label)
            if provenance_payload:
                provenance = {**provenance_payload, "table": "Selected comparison-compatible outputs", "variable": ", ".join(request.get("variableKeys") or []), "filterField": "", "filterValues": []}
                self._write_provenance(workbook, provenance, "full-variable-data", formats)
        finally:
            workbook.close()
        return _safe_filename(f"full_variable_data_{request.get('year','')}.xlsx")

    def dashboard(self, payload: dict[str, Any], cancelled: Callable[[], bool]) -> str:
        workbook = self.xlsxwriter.Workbook(str(self.path), {"strings_to_formulas": False, "strings_to_urls": False})
        try:
            formats = self._formats(workbook)
            displayed = payload.get("rows") or []
            source = payload.get("sourceRows") or []
            view = workbook.add_worksheet("Chart")
            view.set_column(0, 0, 38); view.set_column(1, 3, 18)
            view.write_string(0, 0, "VisionEval percent-change chart", formats["title"])
            view.write_string(1, 0, f"{(payload.get('reference') or {}).get('label','Reference')} to {(payload.get('comparison') or {}).get('label','Comparison')} - {payload.get('year','')}")
            view.write_string(2, 0, f"Scope: {payload.get('scopeLabel', 'All locations')}", formats["text"])
            headers = ["Output", "Percent change", "Changed rows", "Total rows"]
            for column, header in enumerate(headers): view.write_string(3, column, header, formats["header"])
            for row_index, item in enumerate(displayed, 4):
                view.write_string(row_index, 0, str(item.get("label", "")), formats["text"])
                view.write_number(row_index, 1, float(item.get("percentChange") or 0) / 100, formats["percent"])
                self._write_value(view, row_index, 2, item.get("changedRows"), formats)
                self._write_value(view, row_index, 3, item.get("totalRows"), formats)
            if displayed:
                chart = workbook.add_chart({"type": "bar"})
                palette = payload.get("palette") or {}
                increase = str(palette.get("increase") or "#2274a7")
                decrease = str(palette.get("decrease") or "#be3742")
                neutral = str(palette.get("neutral") or "#9aa6af")
                points = []
                for item in displayed:
                    value = float(item.get("percentChange") or 0)
                    color = increase if value > 0 else decrease if value < 0 else neutral
                    points.append({"fill": {"color": color}, "border": {"none": True}})
                chart.add_series({"name": "Percent change", "categories": ["Chart", 4, 0, 3 + len(displayed), 0], "values": ["Chart", 4, 1, 3 + len(displayed), 1], "points": points, "border": {"none": True}})
                chart.set_title({"name": "Percent change by output"}); chart.set_legend({"none": True})
                chart.set_x_axis({"name": "Percent change", "num_format": "0.0%", "major_gridlines": {"visible": True}})
                chart.set_y_axis({"reverse": True}); chart.set_size({"width": 900, "height": max(360, min(1200, 28 * len(displayed)))})
                view.insert_chart(3, 5, chart)
            table_headers = ["Table", "Variable", "Output", "Percent change", "Reference sum", "Comparison sum", "Changed rows", "Total rows", "Units", "Description"]
            def values(item):
                return [item.get("table"), item.get("variable"), item.get("label"), item.get("percentChange"), item.get("referenceSum"), item.get("comparisonSum"), item.get("changedRows"), item.get("totalRows"), item.get("units"), item.get("description")]
            self._write_table_sheets(workbook, "Displayed Data", table_headers, [values(item) for item in displayed], {3}, formats, cancelled)
            self._write_table_sheets(workbook, "Source Data", table_headers, [values(item) for item in source], {3}, formats, cancelled)
            provenance = {**payload, "comparisons": [payload.get("comparison") or {}], "table": "All comparable outputs", "variable": "Percent change", "metadata": {"units": "Percent"}}
            self._write_provenance(workbook, provenance, "dashboard", formats)
        finally:
            workbook.close()
        return _safe_filename(f"percent_change_chart_{payload.get('year','')}.xlsx")

    def comparison_map(self, payload: dict[str, Any], rows: list[dict[str, Any]], cancelled: Callable[[], bool]) -> str:
        workbook = self.xlsxwriter.Workbook(str(self.path), {"constant_memory": True, "strings_to_formulas": False, "strings_to_urls": False})
        try:
            formats = self._formats(workbook)
            aggregation = str(payload.get("aggregation", "mean")).replace("_", " ").title()
            headers = ["Geography ID", "Geography", f"Reference {aggregation}", f"Comparison {aggregation}", "Reference rows", "Comparison rows", "Absolute change", "Change %", "Units"]
            values = [[
                item.get("geographyId"), item.get("name"), item.get("referenceValue"), item.get("comparisonValue"),
                item.get("referenceCount"), item.get("comparisonCount"), item.get("absoluteChange"), item.get("percentChange"), payload.get("units", ""),
            ] for item in rows]
            self._write_table_sheets(workbook, "Map Data", headers, values, {6, 7}, formats, cancelled)
            provenance = {
                **payload, "comparisons": [payload.get("comparison") or {}],
                "metadata": {"units": payload.get("units", "")},
                "filterField": "Project map scope", "filterValues": [payload.get("scopeLabel", "Project geography")],
            }
            self._write_provenance(workbook, provenance, "comparison-map", formats)
        finally:
            workbook.close()
        return _safe_filename(f"comparison_map_{payload.get('table','')}_{payload.get('variable','')}_{payload.get('year','')}.xlsx")


class ComparisonExportManager:
    def __init__(self, service, app_version: str = "1.0.0"):
        self.service = service
        self.app_version = app_version
        self.root = service.workspace.exchange / "comparison-exports"
        self.root.mkdir(parents=True, exist_ok=True)
        for operation_path in self.root.glob("*/operation.json"):
            operation = read_json(operation_path, {})
            if operation.get("state") in {"waiting", "running"}:
                operation.update({"state": "waiting", "message": "Resuming comparison export after restart"})
                write_json(operation_path, operation)
                threading.Thread(target=self._run, args=(operation_path.parent.name,), daemon=True).start()

    def start(self, payload: dict[str, Any]) -> dict[str, Any]:
        kind = payload.get("kind", "")
        if kind not in {"current", "filtered", "change-scan", "dashboard", "full-variables", "comparison-map"}:
            raise WorkspaceError("Unknown comparison export type")
        if kind == "full-variables":
            export_format = payload.get("format", "")
            variable_keys = list(dict.fromkeys(payload.get("variableKeys") or []))
            if export_format not in {"xlsx", "csv-zip"}:
                raise WorkspaceError("Choose Excel or CSV ZIP for the full variable export")
            if not variable_keys:
                raise WorkspaceError("Select at least one variable to export")
            records = [payload.get("reference", ""), *(payload.get("comparisons") or [])]
            available = {f"{item['table']}/{item['name']}" for item in self.service.variables(records) if str(payload.get("year", "")) in item.get("years", [])}
            invalid = [key for key in variable_keys if key not in available]
            if invalid:
                raise WorkspaceError(f"These variables are unavailable for the selected year: {', '.join(invalid[:5])}")
            payload = {**payload, "variableKeys": variable_keys}
        operation_id = make_id("comparison-export", kind)
        directory = self.root / operation_id; directory.mkdir()
        operation = {"id": operation_id, "state": "waiting", "phase": "query", "message": "Waiting to prepare export", "createdAt": now_iso(), "startedAt": "", "finishedAt": "", "downloadReady": False, "filename": "", "mimeType": "", "artifact": ""}
        write_json(directory / "request.json", payload); write_json(directory / "operation.json", operation)
        threading.Thread(target=self._run, args=(operation_id,), daemon=True).start()
        return self.status(operation_id)

    def _cancelled(self, path: Path) -> bool:
        return read_json(path, {}).get("state") == "cancelled"

    def _full_variable_payload(self, request: dict[str, Any], key: str) -> dict[str, Any]:
        table, variable = key.split("/", 1)
        return self.service.compare(
            request.get("reference", ""), request.get("comparisons") or [], table, variable,
            str(request.get("year", "2045")), False, 0, 0, "", [], "id", "original",
        )

    def _full_variable_payloads(self, request: dict[str, Any]):
        for key in request.get("variableKeys") or []:
            yield self._full_variable_payload(request, key)

    def _write_full_variable_zip(self, output: Path, request: dict[str, Any], operation_path: Path, operation: dict[str, Any]) -> str:
        keys = request.get("variableKeys") or []
        used: set[str] = set()
        manifest = {"year": request.get("year"), "reference": request.get("reference"), "comparisons": request.get("comparisons") or [], "variables": keys, "generatedAt": now_iso()}
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
            for index, key in enumerate(keys, 1):
                if self._cancelled(operation_path):
                    raise WorkspaceError("Full variable export cancelled")
                operation.update({"phase": "query", "message": f"Exporting {index} of {len(keys)}: {key}", "progress": {"completed": index - 1, "total": len(keys), "output": key}})
                write_json(operation_path, operation)
                payload = self._full_variable_payload(request, key)
                headers, rows, _ = WorkbookWriter._comparison_table(payload)
                base = _safe_filename(key.replace("/", "_")) or f"variable_{index}"
                filename = f"{base}.csv"
                suffix = 2
                while filename.casefold() in used:
                    filename = f"{base}_{suffix}.csv"; suffix += 1
                used.add(filename.casefold())
                with archive.open(filename, "w") as raw:
                    with io.TextIOWrapper(raw, encoding="utf-8", newline="", write_through=True) as stream:
                        writer = csv.writer(stream, lineterminator="\n")
                        writer.writerow(headers)
                        for row_index, row in enumerate(rows):
                            if row_index and row_index % 10_000 == 0 and self._cancelled(operation_path):
                                raise WorkspaceError("Full variable export cancelled")
                            writer.writerow(row)
                operation["progress"] = {"completed": index, "total": len(keys), "output": key}
                write_json(operation_path, operation)
            archive.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=True))
        return _safe_filename(f"full_variable_data_{request.get('year','')}.zip")

    def _run(self, operation_id: str) -> None:
        directory = self.service.workspace.within(self.root / operation_id, self.root)
        operation_path = directory / "operation.json"; request = read_json(directory / "request.json", {})
        operation = read_json(operation_path, {}); operation.update({"state": "running", "phase": "query", "message": "Querying comparison data", "startedAt": operation.get("startedAt") or now_iso()}); write_json(operation_path, operation)
        full_zip = request.get("kind") == "full-variables" and request.get("format") == "csv-zip"
        artifact = "export.zip" if full_zip else "export.xlsx"
        output = directory / artifact
        try:
            kind = request.get("kind")
            cancelled = lambda: self._cancelled(operation_path)
            if kind == "full-variables" and full_zip:
                filename = self._write_full_variable_zip(output, request, operation_path, operation)
                mime_type = "application/zip"
            elif kind == "full-variables":
                writer = WorkbookWriter(output, self.app_version)
                total = len(request.get("variableKeys") or [])
                def progress(completed: int, count: int, label: str) -> None:
                    operation.update({"phase": "workbook", "message": f"Formatting {completed} of {count}: {label}", "progress": {"completed": completed, "total": count, "output": label}})
                    write_json(operation_path, operation)
                filename = writer.full_variables(self._full_variable_payloads(request), request, cancelled, progress)
                mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            elif kind == "dashboard":
                writer = WorkbookWriter(output, self.app_version)
                payload = self.service.dashboard_display(request.get("dashboardToken", ""), request.get("sortBy", "name"), request.get("displayMode", "all"), float(request.get("threshold", 0)), int(request.get("count", 5)), bool(request.get("hideZero", False)))
                payload["palette"] = request.get("palette") or {}
                operation.update({"phase": "workbook", "message": "Formatting chart workbook"}); write_json(operation_path, operation)
                filename = writer.dashboard(payload, cancelled)
                mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            elif kind == "comparison-map":
                writer = WorkbookWriter(output, self.app_version)
                payload = self.service.comparison_map_snapshot(request.get("mapToken", ""))
                scope_ids = {str(value) for value in request.get("scopeIds") or []}
                rows = self.service.comparison_map_scope_rows(payload["mapToken"], scope_ids) if scope_ids else list(payload.get("geographyRows") or [])
                scoped = {**payload, "scopeLabel": request.get("scopeLabel", "All Virginia")}
                operation.update({"phase": "workbook", "message": "Formatting comparison map workbook"}); write_json(operation_path, operation)
                filename = writer.comparison_map(scoped, rows, cancelled)
                mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            elif kind == "change-scan":
                writer = WorkbookWriter(output, self.app_version)
                records = [self.service._record(request.get("reference", "")), *[self.service._record(item) for item in request.get("comparisons") or []]]
                payload = None
                scan_id = request.get("scanId", "")
                if scan_id:
                    scan_dir = self.service.workspace.within(self.service.workspace.exchange / "comparison-scans" / scan_id, self.service.workspace.exchange / "comparison-scans")
                    if read_json(scan_dir / "operation.json", {}).get("state") == "succeeded": payload = read_json(scan_dir / "result.json", None)
                payload = payload or self.service.changes(request.get("reference", ""), request.get("comparisons") or [], str(request.get("year", "2045")), request.get("filterField", ""), request.get("filterValues") or [], cancelled=cancelled)
                operation.update({"phase": "workbook", "message": "Formatting changed-output scan workbook"}); write_json(operation_path, operation)
                filename = writer.change_summary(payload, records, cancelled)
                mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            else:
                writer = WorkbookWriter(output, self.app_version)
                changed_only = kind == "filtered"
                token = request.get("comparisonToken", "")
                try:
                    payload = self.service.comparison_snapshot_page(token, changed_only, 0, 0, request.get("sortColumn", "id"), request.get("sortDirection", "original")) if token else None
                except WorkspaceError:
                    payload = None
                payload = payload or self.service.compare(request.get("reference", ""), request.get("comparisons") or [], request.get("table", ""), request.get("variable", ""), str(request.get("year", "2045")), changed_only, 0, 0, request.get("filterField", ""), request.get("filterValues") or [], request.get("sortColumn", "id"), request.get("sortDirection", "original"), mode=request.get("mode", "auto"))
                operation.update({"phase": "workbook", "message": "Formatting Excel workbook"}); write_json(operation_path, operation)
                filename = writer.comparison(payload, kind, cancelled)
                mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            if cancelled(): return
            operation.update({"state": "succeeded", "phase": "ready", "message": "Export ready", "finishedAt": now_iso(), "downloadReady": True, "filename": filename, "mimeType": mime_type, "artifact": artifact})
        except Exception as exc:
            output.unlink(missing_ok=True)
            if not self._cancelled(operation_path): operation.update({"state": "failed", "message": str(exc), "finishedAt": now_iso()})
        finally:
            if not self._cancelled(operation_path): write_json(operation_path, operation)

    def status(self, operation_id: str) -> dict[str, Any]:
        directory = self.service.workspace.within(self.root / operation_id, self.root)
        operation_path = directory / "operation.json"
        operation: dict[str, Any] = {}
        # A Windows status poll can overlap the atomic replacement used by the
        # export worker. Treat that short hand-off as busy, not as a vanished
        # operation, so callers never lose a valid export during rapid polling.
        for attempt in range(20):
            operation = read_json(operation_path, {})
            if operation:
                break
            if not directory.is_dir():
                break
            time.sleep(0.01 * (attempt + 1))
        if not operation: raise WorkspaceError("Unknown comparison export")
        return operation

    def cancel(self, operation_id: str) -> dict[str, Any]:
        directory = self.service.workspace.within(self.root / operation_id, self.root); path = directory / "operation.json"
        operation = read_json(path, {})
        if operation.get("state") in {"waiting", "running"}:
            operation.update({"state": "cancelled", "message": "Comparison export cancelled", "finishedAt": now_iso(), "downloadReady": False}); write_json(path, operation)
        return self.status(operation_id)

    def download(self, operation_id: str) -> tuple[Path, str, str]:
        operation = self.status(operation_id)
        if operation.get("state") != "succeeded" or not operation.get("downloadReady"):
            raise WorkspaceError("Comparison export is not ready")
        directory = self.service.workspace.within(self.root / operation_id, self.root)
        artifact = operation.get("artifact") or "export.xlsx"
        path = self.service.workspace.within(directory / artifact, directory)
        return path, _safe_filename(operation.get("filename") or "visioneval_comparison.xlsx"), operation.get("mimeType") or "application/octet-stream"
