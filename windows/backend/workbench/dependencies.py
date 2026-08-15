from __future__ import annotations

import csv
import hashlib
import html
import json
import math
import re
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from .workspace import Workspace, WorkspaceError, read_json, write_json


SCHEMA_VERSION = 6
LAYOUT_VERSION = 4
IDENTIFIERS = {"geo", "azone", "bzone", "czone", "marea", "region", "hhid", "vehid", "wkrid", "year"}
BUILTIN_CATALOG_ID = "__builtin_module_catalog__"


def _field_base(value: str) -> str:
    return value.split(".", 1)[0]


def _unit_details(field: str, declaration: dict[str, Any], definitions: dict[str, str]) -> dict[str, Any]:
    if field.lower() in IDENTIFIERS:
        return {"unit": "", "source": "identifier", "warning": ""}
    kind = str(declaration.get("type", "")).strip().lower()
    module_unit = str(declaration.get("units", "")).strip()
    defined = definitions.get(kind, "")
    parts = field.split(".")[1:]
    year = next((item for item in parts if len(item) == 4 and item.isdigit()), "")
    magnitude = next((item for item in parts if item.lower().startswith("1e")), "")
    base = defined or module_unit
    source = "defs/units.csv" if defined else "module specification"
    if year:
        base = f"{year} {base or 'USD'}"
        source = "column header + " + source
    if magnitude:
        base = f"{base} × {magnitude}".strip()
        source = "column header + " + source if not source.startswith("column header") else source
    warning = ""
    if defined and module_unit and defined.lower() != module_unit.lower() and module_unit.upper() not in {"NA", "NONE"}:
        warning = f"Model definitions use {defined}; the executing module declares {module_unit}."
    return {"unit": "" if base.upper() in {"NA", "NONE", "ID"} else base, "source": source, "warning": warning}


class DependencyService:
    def __init__(self, workspace: Workspace, catalog_path: Path):
        self.workspace = workspace
        self.catalog = read_json(catalog_path, {"version": 1, "modules": {}})
        self.cache_root = workspace.exchange / "system" / "dependencies"
        self.cache_root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _execution(script: str) -> list[tuple[str, str]]:
        script = re.sub(r"(?m)^\s*#.*$", "", script)
        pattern = re.compile(r"runModule\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]", re.S)
        seen, output = set(), []
        for module, package in pattern.findall(script):
            key = (package, module)
            if key not in seen:
                seen.add(key)
                output.append(key)
        return output

    @staticmethod
    def _definitions(path: Path) -> dict[str, str]:
        output: dict[str, str] = {}
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                for row in csv.DictReader(handle):
                    if row.get("Type"):
                        output[str(row["Type"]).strip().lower()] = str(row.get("Units", "")).strip()
        except OSError:
            pass
        return output

    @staticmethod
    def _headers(path: Path) -> list[str]:
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                return next(csv.reader(handle), [])
        except (OSError, csv.Error):
            return []

    def _module_catalog(self, template_path: Path) -> dict[str, Any]:
        modules = {key: dict(value) for key, value in self.catalog.get("modules", {}).items()}
        candidates = (
            template_path / "defs" / "dependency_specifications.csv",
            template_path / "defs" / "module_specifications.csv",
            template_path / "module_specifications.csv",
        )
        for candidate in candidates:
            if not candidate.is_file():
                continue
            try:
                with candidate.open("r", encoding="utf-8-sig", newline="") as handle:
                    for row in csv.DictReader(handle):
                        package, name = str(row.get("package", "")).strip(), str(row.get("module", "")).strip()
                        section = str(row.get("section", "")).strip().capitalize()
                        if not package or not name or section not in {"Inp", "Get", "Set"}:
                            continue
                        module_id = f"{package}::{name}"
                        module = modules.setdefault(module_id, {"id": module_id, "package": package, "name": name, "Inp": [], "Get": [], "Set": []})
                        item = {key: str(row.get(key, "")) for key in ("table", "group", "name", "file", "units", "type", "description")}
                        if item not in module[section]:
                            module[section].append(item)
            except (OSError, csv.Error):
                continue
        return modules

    def _cache_path(self, template: dict[str, Any]) -> Path:
        token = hashlib.sha256(f"{template.get('fingerprint')}|VE-40-RC6|{SCHEMA_VERSION}".encode()).hexdigest()[:24]
        return self.cache_root / f"{template['id']}-{token}.json"

    def graph(
        self,
        template_id: str,
        focus_id: str = "",
        scope: str = "",
        origin_id: str = "",
        view: str = "",
        mode: str = "execution",
    ) -> dict[str, Any]:
        if mode not in {"execution", "catalog"}:
            raise WorkspaceError("Dependency mode must be catalog or execution")
        if mode == "catalog" or template_id == BUILTIN_CATALOG_ID:
            graph = self._catalog_graph()
        else:
            template_path, template = self.workspace.template(template_id)
            cache_path = self._cache_path(template)
            graph = read_json(cache_path, None)
            if not graph:
                graph = self._build(template_path, template)
                write_json(cache_path, graph)
        payload = graph if not focus_id else self._focused(graph, focus_id, scope, origin_id, view)
        payload = dict(payload)
        payload["layout"] = self._layout(payload)
        return payload

    def _catalog_graph(self) -> dict[str, Any]:
        """Build a package-neutral declaration graph without claiming model execution order."""
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, str]] = []
        node_ids: set[str] = set()
        nodes_by_id: dict[str, dict[str, Any]] = {}

        def add_node(node: dict[str, Any]) -> None:
            node_id = node["id"]
            if node_id not in node_ids:
                node_ids.add(node_id)
                nodes_by_id[node_id] = node
                nodes.append(node)
                return
            existing = nodes_by_id[node_id]
            if node.get("kind") == "variable":
                existing["kind"] = "variable"
            for flag in ("storedOutput", "intermediary"):
                existing[flag] = bool(existing.get(flag) or node.get(flag))
            for key in ("description", "units"):
                if not existing.get(key) and node.get(key):
                    existing[key] = node[key]

        modules = sorted(
            self.catalog.get("modules", {}).items(),
            key=lambda item: (str(item[1].get("package", "")).lower(), str(item[1].get("name", item[0])).lower()),
        )
        for display_order, (catalog_id, spec) in enumerate(modules, 1):
            package = str(spec.get("package") or str(catalog_id).split("::", 1)[0])
            module_name = str(spec.get("name") or str(catalog_id).split("::", 1)[-1])
            module_id = str(spec.get("id") or catalog_id)
            module_node = f"module:{module_id}"
            add_node({
                "id": module_node, "kind": "module", "label": module_name, "package": package,
                "moduleId": module_id, "order": display_order, "supported": True, "catalogOnly": True,
            })
            for item in spec.get("Inp", []):
                declared = str(item.get("name", ""))
                for value in str(item.get("file", "")).split("|"):
                    filename = Path(value).name
                    if not filename:
                        continue
                    file_id = f"file:{filename}"
                    input_id = f"input:{filename}:{declared}"
                    add_node({"id": file_id, "kind": "file", "label": filename, "file": filename, "active": True, "fields": []})
                    add_node({
                        "id": input_id, "kind": "input", "label": declared, "file": filename,
                        "field": declared, "table": item.get("table", ""), "description": item.get("description", ""),
                        "units": item.get("units", ""),
                    })
                    edges.extend((
                        {"from": file_id, "to": input_id, "kind": "contains"},
                        {"from": input_id, "to": module_node, "kind": "input"},
                    ))
            for section, direction in (("Get", "get"), ("Set", "set")):
                for item in spec.get(section, []):
                    table, name = str(item.get("table", "")), str(item.get("name", ""))
                    variable_id = f"catalog:{table}/{name}"
                    add_node({
                        "id": variable_id, "kind": "variable" if section == "Set" else "source",
                        "label": name, "table": table, "variableId": f"{table}/{name}",
                        "description": item.get("description", ""), "units": item.get("units", ""),
                        "storedOutput": section == "Set", "intermediary": section == "Get",
                    })
                    edges.append(
                        {"from": variable_id, "to": module_node, "kind": direction}
                        if section == "Get" else
                        {"from": module_node, "to": variable_id, "kind": direction}
                    )
        files = {node["id"] for node in nodes if node.get("kind") == "file"}
        return {
            "version": SCHEMA_VERSION,
            "visionEvalVersion": self.catalog.get("visionEvalVersion", ""),
            "template": {"id": BUILTIN_CATALOG_ID, "name": "VisionEval module catalog", "fingerprint": "builtin"},
            "graphMode": "catalog", "executionOrderAvailable": False,
            "notice": "Built-in module declarations are shown by package. Install or import a model template to see its actual execution order.",
            "nodes": nodes, "edges": edges, "unknownModules": [],
            "counts": {
                "files": len(files), "activeFiles": len(files), "modules": len(modules),
                "intermediaries": sum(1 for node in nodes if node.get("intermediary")),
                "outputs": sum(1 for node in nodes if node.get("storedOutput")), "edges": len(edges),
            },
        }

    @staticmethod
    def _overview_layout(graph: dict[str, Any]) -> dict[str, Any]:
        module_nodes = sorted(
            (node for node in graph.get("nodes", []) if node.get("kind") == "module"),
            key=lambda node: int(node.get("order") or 0),
        )
        columns, node_width, node_height, x_gap, y_gap = 4, 270, 54, 32, 24
        nodes: dict[str, dict[str, Any]] = {}
        for index, node in enumerate(module_nodes):
            column, row = index % columns, index // columns
            nodes[node["id"]] = {
                "x": 40 + column * (node_width + x_gap),
                "y": 76 + row * (node_height + y_gap),
                "width": node_width,
                "height": node_height,
                "lane": "module",
                "orderAnchor": int(node.get("order") or 0),
            }
        return {
            "version": graph.get("layout", {}).get("version", LAYOUT_VERSION),
            "nodes": nodes,
            "lanes": [{
                "id": "module",
                "label": (
                    "Module catalog — declarations are not model execution order"
                    if graph.get("graphMode") == "catalog"
                    else "Execution sequence — select a module to inspect its inputs and outputs"
                ),
                "x": 40,
                "width": node_width,
            }],
            "groups": [],
            "bounds": {"x": 0, "y": 0, "width": 40 + columns * (node_width + x_gap), "height": 120 + math.ceil(len(module_nodes) / columns) * (node_height + y_gap)},
        }

    @staticmethod
    def _layout(graph: dict[str, Any]) -> dict[str, Any]:
        """Return a stable layered layout shared by the UI and vector exports."""
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])
        by_id = {node["id"]: node for node in nodes}
        module_orders = {node["id"]: int(node.get("order") or 0) for node in nodes if node.get("kind") == "module"}
        forward: dict[str, list[str]] = defaultdict(list)
        reverse: dict[str, list[str]] = defaultdict(list)
        for edge in edges:
            forward[edge["from"]].append(edge["to"])
            reverse[edge["to"]].append(edge["from"])

        def nearest_order(node_id: str) -> int:
            node = by_id[node_id]
            if node.get("kind") == "module":
                return module_orders.get(node_id, 0)
            if node.get("producerOrder"):
                return int(node["producerOrder"])
            queue, visited = deque([(node_id, 0)]), {node_id}
            found: list[tuple[int, int]] = []
            while queue:
                current, distance = queue.popleft()
                if current in module_orders:
                    found.append((distance, module_orders[current]))
                    continue
                for adjacent in forward.get(current, []) + reverse.get(current, []):
                    if adjacent not in visited:
                        visited.add(adjacent); queue.append((adjacent, distance + 1))
            return min(found)[1] if found else 10**6

        focus_view = graph.get("focusView") or {}
        focused_roles = bool(focus_view)

        def lane(node: dict[str, Any]) -> str:
            if focused_roles:
                return {
                    "source-file": "input",
                    "file-input": "read",
                    "prior-value": "read",
                    "module": "module",
                    "written-value": "output",
                    "direct-effect-value": "output",
                    "producer-module": "producer",
                    "selected-value": "selected",
                    "consumer-module": "consumer",
                }.get(str(node.get("viewRole", "")), "read")
            if node.get("kind") in {"file", "input"}: return "input"
            if node.get("kind") == "module": return "module"
            if node.get("storedOutput"): return "output"
            return "intermediary"

        if focus_view.get("kind") == "value" and focus_view.get("view") == "production":
            lane_defs = [
                ("input", "Source files", 30), ("read", "Values read", 310),
                ("producer", "Producing module", 590), ("selected", "Selected value", 870),
            ]
        elif focus_view.get("kind") == "value" and focus_view.get("view") == "consumers":
            lane_defs = [("selected", "Selected value", 180), ("consumer", "Modules using value", 620)]
        elif focus_view.get("kind") in {"file", "input"}:
            lane_defs = [
                ("input", "Selected source", 40), ("read", "Selected columns", 390),
                ("module", "Modules using selection", 740), ("output", "Values directly written", 1090),
            ]
        elif focused_roles:
            lane_defs = [
                ("input", "Source files", 40), ("read", "Values read", 390),
                ("module", "Selected module", 740), ("output", "Values written", 1090),
            ]
        else:
            lane_defs = [
                ("input", "Inputs", 40), ("module", "Executed modules", 390),
                ("intermediary", "Intermediaries", 740), ("output", "Stored outputs", 1090),
            ]
        positions: dict[str, dict[str, Any]] = {}
        groups: list[dict[str, Any]] = []
        node_width, node_height, gap = 270, 54, 18
        max_rows = 1
        for lane_id, label, x in lane_defs:
            items = [node for node in nodes if lane(node) == lane_id]
            items.sort(key=lambda node: (nearest_order(node["id"]), int(node.get("order") or 0), str(node.get("label", "")).lower(), node["id"]))
            if focused_roles and lane_id == "read":
                cursor = 72
                for role, group_label in (("file-input", "File columns"), ("prior-value", "Values from earlier steps")):
                    role_items = [node for node in items if node.get("viewRole") == role]
                    if not role_items:
                        continue
                    groups.append({"lane": lane_id, "role": role, "label": group_label, "x": x, "y": cursor})
                    cursor += 24
                    for node in role_items:
                        positions[node["id"]] = {"x": x, "y": cursor, "width": node_width, "height": node_height, "lane": lane_id, "group": role, "orderAnchor": nearest_order(node["id"])}
                        cursor += node_height + gap
                    cursor += 12
                max_rows = max(max_rows, math.ceil(cursor / (node_height + gap)))
            else:
                max_rows = max(max_rows, len(items))
                for index, node in enumerate(items):
                    positions[node["id"]] = {"x": x, "y": 70 + index * (node_height + gap), "width": node_width, "height": node_height, "lane": lane_id, "orderAnchor": nearest_order(node["id"])}
        return {
            "version": LAYOUT_VERSION,
            "nodes": positions,
            "lanes": [{"id": lane_id, "label": label, "x": x, "width": node_width} for lane_id, label, x in lane_defs],
            "groups": groups,
            "bounds": {"x": 0, "y": 0, "width": max(1080, max(x for _, _, x in lane_defs) + node_width + 40), "height": max(460, 100 + max_rows * (node_height + gap))},
        }

    @staticmethod
    def _node_detail(node: dict[str, Any]) -> str:
        if node.get("kind") == "module":
            role = {
                "producer-module": "Producing module",
                "consumer-module": "Uses selected value",
                "module": "Selected module",
            }.get(str(node.get("viewRole", "")), "")
            return " · ".join(value for value in (f"{node.get('order', '')}. {node.get('package', '')}".strip(), role) if value)
        if node.get("kind") == "file":
            return "Used by this model" if node.get("active") else "Not used by this path"
        role = {
            "file-input": "File column",
            "written-value": "Written by selected module",
            "direct-effect-value": "Directly written by a module using selection",
            "selected-value": "Selected value",
        }.get(str(node.get("viewRole", "")), "")
        if node.get("viewRole") == "prior-value":
            upstream = node.get("upstreamSource") or {}
            if upstream.get("type") == "module":
                role = f"From {upstream.get('order', '')}. {upstream.get('label', '')}".strip()
            else:
                role = "Loaded earlier — source not declared"
        return " · ".join(str(value) for value in (node.get("table"), node.get("units"), role) if value)

    def svg(self, template_id: str, focus_id: str = "", scope: str = "", origin_id: str = "", view: str = "") -> bytes:
        graph = self.graph(template_id, focus_id, scope, origin_id, view)
        layout, by_id = self._overview_layout(graph) if not focus_id else graph["layout"], {node["id"]: node for node in graph["nodes"]}
        bounds = layout["bounds"]
        colors = {
            "input":"#5b8db8", "read":"#b47b43", "module":"#55966a",
            "intermediary":"#b47b43", "output":"#a86283", "producer":"#55966a",
            "selected":"#a86283", "consumer":"#55966a",
        }
        output = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{bounds["width"]}" height="{bounds["height"]}" viewBox="0 0 {bounds["width"]} {bounds["height"]}">',
                  '<style>text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;fill:#182330}.title{font-size:22px;font-weight:700}.label{font-size:12px;font-weight:700}.detail{font-size:10px;fill:#617286}.edge{fill:none;stroke:#9aa8b7;stroke-width:1;opacity:.55}.node{fill:#fff;stroke:#c8d3df}</style>',
                  f'<rect width="100%" height="100%" fill="#f3f6fa"/><text class="title" x="30" y="32">{html.escape(graph["template"]["name"])} dependency graph</text>']
        for lane in layout["lanes"]:
            output.append(f'<text class="label" x="{lane["x"]}" y="58">{html.escape(lane["label"])}</text>')
        for group in layout.get("groups", []):
            output.append(f'<text class="detail" x="{group["x"]}" y="{group["y"]}">{html.escape(group["label"])}</text>')
        for edge in graph["edges"]:
            a, b = layout["nodes"].get(edge["from"]), layout["nodes"].get(edge["to"])
            if not a or not b: continue
            x1, y1 = a["x"] + a["width"], a["y"] + a["height"] / 2
            x2, y2 = b["x"], b["y"] + b["height"] / 2
            mid = (x1 + x2) / 2
            output.append(f'<path class="edge" d="M{x1},{y1} C{mid},{y1} {mid},{y2} {x2},{y2}"/>')
        for node_id, position in layout["nodes"].items():
            node, color = by_id[node_id], colors[position["lane"]]
            output.append(f'<g><rect class="node" x="{position["x"]}" y="{position["y"]}" width="{position["width"]}" height="{position["height"]}" rx="7"/><rect x="{position["x"]}" y="{position["y"]}" width="5" height="{position["height"]}" rx="3" fill="{color}"/><text class="label" x="{position["x"]+13}" y="{position["y"]+22}">{html.escape(str(node.get("label", "")))}</text><text class="detail" x="{position["x"]+13}" y="{position["y"]+40}">{html.escape(self._node_detail(node))}</text></g>')
        if graph.get("unknownModules"):
            output.append(f'<text class="detail" x="30" y="{bounds["height"]-18}">Unresolved modules: {html.escape(", ".join(graph["unknownModules"]))}</text>')
        output.append('</svg>')
        return "".join(output).encode("utf-8")

    def html(self, template_id: str, focus_id: str = "", scope: str = "", origin_id: str = "", view: str = "") -> bytes:
        graph = self.graph(template_id, focus_id, scope, origin_id, view)
        svg = self.svg(template_id, focus_id, scope, origin_id, view).decode("utf-8")
        focus = graph.get("focusView") or {}
        focus_label = focus.get("label") or ("Execution overview" if not focus_id else "Focused dependency view")
        title = f'{graph["template"]["name"]} dependency graph'
        description = "Standalone dependency export from VisionEval Workbench."
        document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    body {{ margin: 0; padding: 24px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #182330; background: #f3f6fa; }}
    header {{ margin: 0 0 18px; }}
    h1 {{ margin: 0 0 4px; font-size: 22px; line-height: 1.25; }}
    p {{ margin: 0; color: #617286; }}
    .graph {{ overflow: auto; border: 1px solid #c8d3df; border-radius: 10px; background: white; }}
    .graph svg {{ display: block; }}
  </style>
</head>
<body>
  <header>
    <h1>{html.escape(title)}</h1>
    <p>{html.escape(str(focus_label))} · {description}</p>
  </header>
  <main class="graph">{svg}</main>
</body>
</html>
"""
        return document.encode("utf-8")

    def pdf(self, template_id: str, focus_id: str = "", scope: str = "", origin_id: str = "", view: str = "") -> bytes:
        """Generate a dependency poster as tiled vector PDF pages without extra packages."""
        graph = self.graph(template_id, focus_id, scope, origin_id, view); layout = self._overview_layout(graph) if not focus_id else graph["layout"]
        by_id = {node["id"]: node for node in graph["nodes"]}
        page_w, page_h, margin, scale = 792.0, 612.0, 30.0, 0.52
        tile_h = (page_h - 70) / scale
        pages = max(1, math.ceil(layout["bounds"]["height"] / tile_h))

        def esc(value: Any) -> str:
            return str(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        contents: list[bytes] = []
        for page in range(pages):
            y0, y1 = page * tile_h, (page + 1) * tile_h
            commands = ["q", f"{scale} 0 0 {scale} {margin} 28 cm", f"1 0 0 1 0 {-y0} cm", "0.75 G", "0.5 w"]
            for lane in layout.get("lanes", []):
                if y0 <= 58 <= y1:
                    commands.extend(["0 0 0 rg", "BT", "/F1 11 Tf", f"1 0 0 1 {lane['x']} 58 Tm", f"({esc(lane['label'])}) Tj", "ET"])
            for group in layout.get("groups", []):
                if y0 <= group["y"] <= y1:
                    commands.extend(["0.35 0.4 0.48 rg", "BT", "/F1 8 Tf", f"1 0 0 1 {group['x']} {group['y']} Tm", f"({esc(group['label'])}) Tj", "ET"])
            for edge in graph["edges"]:
                a, b = layout["nodes"].get(edge["from"]), layout["nodes"].get(edge["to"])
                if not a or not b: continue
                ay, by = a["y"] + a["height"]/2, b["y"] + b["height"]/2
                if max(ay, by) < y0 or min(ay, by) > y1: continue
                commands.append(f"{a['x']+a['width']} {ay} m {b['x']} {by} l S")
            for node_id, pos in layout["nodes"].items():
                if pos["y"] + pos["height"] < y0 or pos["y"] > y1: continue
                node = by_id[node_id]
                commands.extend(["1 1 1 rg", f"{pos['x']} {pos['y']} {pos['width']} {pos['height']} re B", "0 0 0 rg", "BT", "/F1 11 Tf", f"1 0 0 1 {pos['x']+10} {pos['y']+34} Tm", f"({esc(str(node.get('label',''))[:42])}) Tj", "/F1 8 Tf", f"1 0 0 1 {pos['x']+10} {pos['y']+17} Tm", f"({esc(self._node_detail(node)[:58])}) Tj", "ET"])
            commands.extend(["Q", "BT", "/F1 13 Tf", f"1 0 0 1 {margin} {page_h-25} Tm", f"({esc(graph['template']['name'])} dependency graph - page {page+1} of {pages}) Tj", "ET"])
            contents.append("\n".join(commands).encode("latin-1", "replace"))
        objects: list[bytes] = [b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
        content_ids = []
        for content in contents:
            objects.append(f"<< /Length {len(content)} >>\nstream\n".encode() + content + b"\nendstream"); content_ids.append(len(objects))
        page_ids, pages_id = [], 1 + len(contents) + len(contents) + 1
        for content_id in content_ids:
            objects.append(f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {page_w:g} {page_h:g}] /Resources << /Font << /F1 1 0 R >> >> /Contents {content_id} 0 R >>".encode()); page_ids.append(len(objects))
        objects.append(f"<< /Type /Pages /Kids [{' '.join(f'{item} 0 R' for item in page_ids)}] /Count {len(page_ids)} >>".encode()); actual_pages = len(objects)
        objects.append(f"<< /Type /Catalog /Pages {actual_pages} 0 R >>".encode()); catalog = len(objects)
        output, offsets = [b"%PDF-1.4\n"], [0]
        for index, body in enumerate(objects, 1): offsets.append(sum(map(len, output))); output.append(f"{index} 0 obj\n".encode()+body+b"\nendobj\n")
        xref=sum(map(len,output)); output.append(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode()); output.extend(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:]); output.append(f"trailer\n<< /Size {len(objects)+1} /Root {catalog} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
        return b"".join(output)

    def _build(self, template_path: Path, template: dict[str, Any]) -> dict[str, Any]:
        script_path = template_path / "scripts" / "run_model.R"
        execution = self._execution(script_path.read_text(encoding="utf-8", errors="replace"))
        definitions = self._definitions(template_path / "defs" / "units.csv")
        catalog_modules = self._module_catalog(template_path)
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        node_ids: set[str] = set()

        def add_node(node: dict[str, Any]) -> None:
            if node["id"] not in node_ids:
                node_ids.add(node["id"])
                nodes.append(node)

        files = sorted((path for path in (template_path / "inputs").iterdir() if path.is_file()), key=lambda path: path.name.lower())
        file_headers = {path.name: self._headers(path) for path in files if path.suffix.lower() == ".csv"}
        active_files: set[str] = set()
        input_nodes_by_key: dict[tuple[str, str], str] = {}
        occurrences: dict[tuple[str, str], list[tuple[int, str]]] = defaultdict(list)
        gets_by_variable: dict[str, list[int]] = defaultdict(list)
        unknown = []

        for order, (package, module_name) in enumerate(execution, 1):
            module_id = f"{package}::{module_name}"
            spec = catalog_modules.get(module_id)
            module_node = f"module:{module_id}"
            add_node({"id": module_node, "kind": "module", "label": module_name, "package": package, "moduleId": module_id, "order": order, "supported": bool(spec)})
            if not spec:
                unknown.append(module_id)
                continue
            for item in spec.get("Inp", []):
                filenames = [Path(value).name for value in str(item.get("file", "")).split("|") if value]
                for filename in filenames:
                    active_files.add(filename)
                    header = file_headers.get(filename, [])
                    declared = str(item.get("name", ""))
                    matching = next((field for field in header if _field_base(field).lower() == declared.lower()), declared)
                    input_id = f"input:{filename}:{matching}"
                    details = _unit_details(matching, item, definitions)
                    add_node({
                        "id": input_id, "kind": "input", "label": matching, "file": filename,
                        "field": matching, "table": item.get("table", ""), "description": item.get("description", ""),
                        "units": details["unit"], "unitSource": details["source"], "unitWarning": details["warning"],
                    })
                    input_nodes_by_key[(filename, matching)] = input_id
                    edges.append({"from": input_id, "to": module_node, "kind": "input"})
            for item in spec.get("Get", []):
                key = (str(item.get("table", "")), str(item.get("name", "")))
                prior = [entry for entry in occurrences.get(key, []) if entry[0] < order]
                if prior:
                    producer_order, variable_node = prior[-1]
                else:
                    variable_node = f"source:{key[0]}/{key[1]}"
                    add_node({"id": variable_node, "kind": "source", "label": key[1], "table": key[0], "variableId": f"{key[0]}/{key[1]}", "description": item.get("description", ""), "units": item.get("units", ""), "frameworkSource": True})
                edges.append({"from": variable_node, "to": module_node, "kind": "get"})
                gets_by_variable[variable_node].append(order)
            for item in spec.get("Set", []):
                table, name = str(item.get("table", "")), str(item.get("name", ""))
                stable = f"{table}/{name}"
                variable_node = f"variable:{stable}@{order}"
                add_node({
                    "id": variable_node, "kind": "variable", "label": name, "table": table,
                    "variableId": stable, "producer": module_id, "producerOrder": order,
                    "description": item.get("description", ""), "units": item.get("units", ""),
                    "intermediary": False, "storedOutput": False,
                })
                occurrences[(table, name)].append((order, variable_node))
                edges.append({"from": module_node, "to": variable_node, "kind": "set"})

        latest = {items[-1][1] for items in occurrences.values() if items}
        by_id = {node["id"]: node for node in nodes}
        consumed = {edge["from"] for edge in edges if edge["kind"] == "get" and edge["from"].startswith("variable:")}
        for node_id in latest:
            by_id[node_id]["storedOutput"] = True
        for node_id in consumed:
            by_id[node_id]["intermediary"] = True

        for path in files:
            file_id = f"file:{path.name}"
            add_node({"id": file_id, "kind": "file", "label": path.name, "file": path.name, "active": path.name in active_files, "fields": file_headers.get(path.name, [])})
            for (filename, field), input_id in input_nodes_by_key.items():
                if filename == path.name:
                    edges.append({"from": file_id, "to": input_id, "kind": "contains"})

        result = {
            "version": SCHEMA_VERSION, "visionEvalVersion": self.catalog.get("visionEvalVersion", "VE-40-RC6"),
            "template": {"id": template["id"], "name": template["name"], "fingerprint": template.get("fingerprint", "")},
            "graphMode": "execution", "executionOrderAvailable": True,
            "notice": "Declared possible effects show executable dependency paths; they do not guarantee a numeric output change.",
            "nodes": nodes, "edges": edges, "unknownModules": unknown,
        }
        result["counts"] = {
            "files": len(files), "activeFiles": len(active_files), "modules": len(execution),
            "intermediaries": sum(1 for node in nodes if node.get("intermediary")),
            "outputs": sum(1 for node in nodes if node.get("storedOutput")), "edges": len(edges),
        }
        return result

    @staticmethod
    def _focused(
        graph: dict[str, Any],
        focus_id: str,
        scope: str = "",
        origin_id: str = "",
        view: str = "",
    ) -> dict[str, Any]:
        if focus_id not in {node["id"] for node in graph.get("nodes", [])}:
            raise WorkspaceError("Unknown dependency node")
        forward: dict[str, list[str]] = defaultdict(list)
        reverse: dict[str, list[str]] = defaultdict(list)
        for edge in graph.get("edges", []):
            forward[edge["from"]].append(edge["to"])
            reverse[edge["to"]].append(edge["from"])
        by_id = {node["id"]: node for node in graph.get("nodes", [])}
        focus_kind = by_id[focus_id].get("kind")

        def logical_key(node_id: str) -> tuple[str, str]:
            node = by_id[node_id]
            name = str(node.get("field") or node.get("label") or "")
            return str(node.get("table") or "").lower(), _field_base(name).lower()

        def role_payload(
            selected: set[str],
            roles: dict[str, str],
            kind: str,
            resolved_view: str,
            metrics: list[tuple[str, int]],
            notice: str,
            resolved_scope: str = "",
            resolved_origin: str = "",
            navigation: dict[str, Any] | None = None,
        ) -> dict[str, Any]:
            payload = dict(graph)
            payload["focusId"] = focus_id
            focused_nodes = []
            for node in graph.get("nodes", []):
                if node["id"] not in selected:
                    continue
                item = dict(node, viewRole=roles[node["id"]])
                if roles[node["id"]] == "prior-value":
                    producer_id = f"module:{node.get('producer', '')}" if node.get("producer") else ""
                    producer = by_id.get(producer_id)
                    item["upstreamSource"] = (
                        {
                            "type": "module",
                            "moduleId": producer_id,
                            "order": int(producer.get("order") or node.get("producerOrder") or 0),
                            "label": str(producer.get("label") or ""),
                            "package": str(producer.get("package") or ""),
                        }
                        if producer else
                        {"type": "existing", "label": "Loaded earlier — source not declared"}
                    )
                focused_nodes.append(item)
            payload["nodes"] = focused_nodes
            payload["edges"] = [edge for edge in graph.get("edges", []) if edge["from"] in selected and edge["to"] in selected]
            role_counts = {
                "sourceFiles": sum(1 for role in roles.values() if role == "source-file"),
                "fileColumns": sum(1 for role in roles.values() if role == "file-input"),
                "priorValues": sum(1 for role in roles.values() if role == "prior-value"),
                "modules": sum(1 for role in roles.values() if role == "module"),
                "valuesWritten": sum(1 for role in roles.values() if role == "written-value"),
                "directEffectValues": sum(1 for role in roles.values() if role == "direct-effect-value"),
                "producingModules": sum(1 for role in roles.values() if role == "producer-module"),
                "selectedValues": sum(1 for role in roles.values() if role == "selected-value"),
                "consumerModules": sum(1 for role in roles.values() if role == "consumer-module"),
            }
            payload["counts"] = {
                "files": role_counts["sourceFiles"],
                "activeFiles": role_counts["sourceFiles"],
                "modules": role_counts["modules"] + role_counts["producingModules"] + role_counts["consumerModules"],
                "intermediaries": role_counts["priorValues"],
                "outputs": role_counts["valuesWritten"] + role_counts["directEffectValues"] + role_counts["selectedValues"],
                "edges": len(payload["edges"]),
            }
            payload["focusView"] = {
                "focusId": focus_id,
                "kind": kind,
                "view": resolved_view,
                "scope": resolved_scope,
                "originId": resolved_origin,
                "roleCounts": role_counts,
                "metrics": [{"label": label, "value": value} for label, value in metrics],
                "navigation": navigation or {},
            }
            payload["notice"] = notice
            return payload

        if focus_kind == "module":
            resolved_scope = scope or "context"
            if resolved_scope not in {"path", "context"}:
                raise WorkspaceError("Dependency scope must be path or context")
            if origin_id:
                if origin_id not in by_id or by_id[origin_id].get("kind") not in {"file", "input"}:
                    raise WorkspaceError("Dependency path origin must be an input file or field")
            if resolved_scope == "path":
                if not origin_id:
                    raise WorkspaceError("Selected path scope requires an origin")
                origin_kind = by_id[origin_id].get("kind")
                if origin_kind == "file":
                    fields = {
                        node_id for node_id in forward.get(origin_id, [])
                        if by_id.get(node_id, {}).get("kind") == "input" and focus_id in forward.get(node_id, [])
                    }
                    files = {origin_id}
                else:
                    fields = {origin_id} if focus_id in forward.get(origin_id, []) else set()
                    files = {
                        node_id for node_id in reverse.get(origin_id, [])
                        if by_id.get(node_id, {}).get("kind") == "file"
                    }
                if not fields:
                    raise WorkspaceError("The selected origin is not connected to this module")
                written = {
                    node_id for node_id in forward.get(focus_id, [])
                    if by_id.get(node_id, {}).get("kind") == "variable"
                }
                selected = {focus_id, *files, *fields, *written}
                roles = {**{item: "source-file" for item in files}, **{item: "file-input" for item in fields},
                         focus_id: "module", **{item: "written-value" for item in written}}
                return role_payload(
                    selected, roles, "module", "path",
                    [("Source files", len(files)), ("File columns", len(fields)),
                     ("Selected modules", 1), ("Values written", len(written))],
                    "Selected path shows only the originating file or column, the selected module, and values it writes directly.",
                    resolved_scope, origin_id,
                )

            predecessors = set(reverse.get(focus_id, []))
            file_inputs = {node_id for node_id in predecessors if by_id.get(node_id, {}).get("kind") == "input"}
            files = {
                parent for input_id in file_inputs for parent in reverse.get(input_id, [])
                if by_id.get(parent, {}).get("kind") == "file"
            }
            input_keys = {logical_key(node_id) for node_id in file_inputs}
            prior_values = {
                node_id for node_id in predecessors
                if by_id.get(node_id, {}).get("kind") in {"variable", "source"} and logical_key(node_id) not in input_keys
            }
            written = {
                node_id for node_id in forward.get(focus_id, [])
                if by_id.get(node_id, {}).get("kind") == "variable"
            }
            if origin_id:
                origin_kind = by_id[origin_id].get("kind")
                connected = origin_id in file_inputs if origin_kind == "input" else any(
                    input_id in forward.get(origin_id, []) for input_id in file_inputs
                )
                if not connected:
                    raise WorkspaceError("The selected origin is not connected to this module")
            selected = {focus_id, *files, *file_inputs, *prior_values, *written}
            roles = {**{item: "source-file" for item in files}, **{item: "file-input" for item in file_inputs},
                     **{item: "prior-value" for item in prior_values}, focus_id: "module",
                     **{item: "written-value" for item in written}}
            return role_payload(
                selected, roles, "module", "context",
                [("Source files", len(files)), ("File columns", len(file_inputs)),
                 ("Values from earlier steps", len(prior_values)), ("Values written", len(written))],
                "Full module context identifies every declared value read and every value written directly by the selected module.",
                resolved_scope, origin_id,
            )

        selected = {focus_id, *forward.get(focus_id, []), *reverse.get(focus_id, [])}
        if focus_kind in {"file", "input"}:
            first_modules = {
                node_id for node_id in selected if by_id.get(node_id, {}).get("kind") == "module"
            }
            if focus_kind == "file":
                fields = set(forward.get(focus_id, []))
                selected.update(fields)
                for field in fields:
                    first_modules.update(
                        node_id for node_id in forward.get(field, [])
                        if by_id.get(node_id, {}).get("kind") == "module"
                    )
            selected.update(first_modules)
            for module_id in first_modules:
                selected.update(forward.get(module_id, []))
            files = {node_id for node_id in selected if by_id[node_id].get("kind") == "file"}
            fields = {node_id for node_id in selected if by_id[node_id].get("kind") == "input"}
            modules = {node_id for node_id in selected if by_id[node_id].get("kind") == "module"}
            written = {
                node_id for module_id in modules for node_id in forward.get(module_id, [])
                if node_id in selected and by_id.get(node_id, {}).get("kind") == "variable"
            }
            selected = files | fields | modules | written
            roles = {**{item: "source-file" for item in files}, **{item: "file-input" for item in fields},
                     **{item: "module" for item in modules}, **{item: "direct-effect-value" for item in written}}
            return role_payload(
                selected, roles, str(focus_kind), "direct",
                [("Source files", len(files)), ("Selected columns", len(fields)),
                 ("Modules using selection", len(modules)), ("Values directly written", len(written))],
                "Direct possible effects show modules that read the selected source and values those modules write directly; they do not prove a numerical change.",
                "path", focus_id,
            )

        if focus_kind in {"variable", "source"}:
            producers = {
                node_id for node_id in reverse.get(focus_id, [])
                if by_id.get(node_id, {}).get("kind") == "module"
            }
            consumers = {
                node_id for node_id in forward.get(focus_id, [])
                if by_id.get(node_id, {}).get("kind") == "module"
            }
            resolved_view = view or ("production" if producers else "consumers")
            if resolved_view not in {"production", "consumers"}:
                raise WorkspaceError("Dependency value view must be production or consumers")
            navigation = {
                "canShowProduction": bool(producers),
                "canShowConsumers": True,
                "producerIds": sorted(producers),
                "consumerIds": sorted(consumers),
            }
            if resolved_view == "consumers":
                selected = {focus_id, *consumers}
                roles = {focus_id: "selected-value", **{item: "consumer-module" for item in consumers}}
                return role_payload(
                    selected, roles, "value", "consumers",
                    [("Selected values", 1), ("Modules using value", len(consumers))],
                    "Where used shows only later modules that directly read the selected value. Select a module to inspect everything it reads and writes.",
                    navigation=navigation,
                )

            if not producers:
                roles = {focus_id: "selected-value"}
                return role_payload(
                    {focus_id}, roles, "value", "production",
                    [("Source files", 0), ("File columns", 0), ("Values from earlier steps", 0),
                     ("Producing modules", 0), ("Selected values", 1)],
                    "No preceding declared producer exists for this value. It was loaded or initialized before the selected execution path.",
                    navigation=navigation,
                )

            producer_id = min(producers, key=lambda item: int(by_id[item].get("order") or 0))
            predecessors = set(reverse.get(producer_id, []))
            file_inputs = {node_id for node_id in predecessors if by_id.get(node_id, {}).get("kind") == "input"}
            files = {
                parent for input_id in file_inputs for parent in reverse.get(input_id, [])
                if by_id.get(parent, {}).get("kind") == "file"
            }
            input_keys = {logical_key(node_id) for node_id in file_inputs}
            prior_values = {
                node_id for node_id in predecessors
                if by_id.get(node_id, {}).get("kind") in {"variable", "source"} and logical_key(node_id) not in input_keys
            }
            selected = {focus_id, producer_id, *files, *file_inputs, *prior_values}
            roles = {
                **{item: "source-file" for item in files},
                **{item: "file-input" for item in file_inputs},
                **{item: "prior-value" for item in prior_values},
                producer_id: "producer-module",
                focus_id: "selected-value",
            }
            return role_payload(
                selected, roles, "value", "production",
                [("Source files", len(files)), ("File columns", len(file_inputs)),
                 ("Values from earlier steps", len(prior_values)), ("Producing modules", 1),
                 ("Selected values", 1)],
                "How produced shows one exact production step. Select an earlier value to continue tracing upstream.",
                navigation=navigation,
            )

        raise WorkspaceError("Unsupported dependency focus node")
