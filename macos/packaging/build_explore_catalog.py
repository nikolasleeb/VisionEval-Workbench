#!/usr/bin/env python3
"""Build the standalone Explore catalog from the V1 Editor's source material."""
from __future__ import annotations

import argparse
import csv
import html
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
ALIASES = {
    "azone_hh_ave_veh_per_driver": "azone_hh_av_veh_per_driver",
    "bzone_travel_demand_management": "bzone_travel_demand_mgt",
}
EXPLANATION_DATE_RE = re.compile(r"^(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}$", re.IGNORECASE)
EXPLANATION_TITLE_RE = re.compile(r"^(Optional\s+)?File\s+\d{1,3}[\s_.-].+|^\d{1,3}[_\s.-].+", re.IGNORECASE)


def document_key(path: Path) -> str:
    stem = re.sub(r"^\d+_\s*", "", path.stem).strip().lower()
    if stem.endswith(".csv"):
        stem = stem[:-4]
    return ALIASES.get(stem, stem)


def text(element: ET.Element) -> str:
    return "".join(node.text or "" for node in element.iter(f"{W_NS}t")).strip()


def strip_explanation_header(chunks: list[str]) -> list[str]:
    while chunks:
        value = re.sub(r"<[^>]+>", "", chunks[0]).strip()
        if EXPLANATION_TITLE_RE.match(value) or EXPLANATION_DATE_RE.match(value):
            chunks.pop(0)
            continue
        break
    return chunks


def render_docx(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    body = root.find(f"{W_NS}body")
    chunks: list[str] = []
    for child in body or []:
        if child.tag == f"{W_NS}p":
            value = text(child)
            if not value:
                continue
            style = child.find(f".//{W_NS}pStyle")
            style_name = style.attrib.get(f"{W_NS}val", "") if style is not None else ""
            tag = "h3" if style_name.lower().startswith("heading") else "p"
            chunks.append(f"<{tag}>{html.escape(value)}</{tag}>")
        elif child.tag == f"{W_NS}tbl":
            rows = []
            for row in child.findall(f"{W_NS}tr"):
                cells = [f"<td>{html.escape(text(cell))}</td>" for cell in row.findall(f"{W_NS}tc")]
                if cells:
                    rows.append(f"<tr>{''.join(cells)}</tr>")
            if rows:
                chunks.append(f"<table>{''.join(rows)}</table>")
    return "\n".join(strip_explanation_header(chunks))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="VisionEvalEditorTool repository")
    parser.add_argument("output", type=Path)
    parser.add_argument("--module-inputs", type=Path, help="visioneval-scenario-inputs.csv generated from executing module specifications")
    args = parser.parse_args()
    metadata = json.loads((args.source / "Metadata" / "metadata.json").read_text(encoding="utf-8"))
    explanations = {
        document_key(path): {"document": path.name, "html": render_docx(path)}
        for path in sorted((args.source / "Clean Explanations" / "DOCX").glob("*.docx"))
    }
    input_fields: dict[str, dict[str, dict]] = {}
    if args.module_inputs and args.module_inputs.is_file():
        with args.module_inputs.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                filename = str(row.get("file") or row.get("FILE") or "").strip().lower()
                field = str(row.get("name") or row.get("NAME") or "").strip()
                if not filename or not field:
                    continue
                package = str(row.get("package") or row.get("PACKAGE") or "").strip()
                module = str(row.get("module") or row.get("MODULE") or "").strip()
                spec = {
                    "field": field,
                    "authoritative": True,
                    "type": str(row.get("type") or row.get("TYPE") or "").strip(),
                    "units": str(row.get("units") or row.get("UNITS") or "").strip(),
                    "description": str(row.get("description") or row.get("DESCRIPTION") or "").strip(),
                    "module": "::".join(part for part in (package, module) if part),
                }
                key = field.split(".", 1)[0].lower()
                current = input_fields.setdefault(filename, {}).get(key)
                if current and any(current.get(name) != spec.get(name) for name in ("type", "units")):
                    current.setdefault("warnings", []).append(
                        f"Another executing specification reports type {spec['type'] or 'unspecified'} and unit {spec['units'] or 'unspecified'} in {spec['module'] or 'an unknown module'}."
                    )
                    continue
                input_fields[filename][key] = spec
    payload = {
        "version": 1,
        "variables": metadata.get("variables", {}),
        "explanations": explanations,
        "inputFields": input_fields,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


if __name__ == "__main__":
    main()
