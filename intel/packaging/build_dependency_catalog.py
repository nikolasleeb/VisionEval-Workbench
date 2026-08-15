from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


def add_rows(modules: dict[str, dict], source: Path, only_missing_modules: bool = False) -> None:
    if not source.is_file():
        return
    existing_modules = set(modules)
    with source.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            module_id = f"{row['package']}::{row['module']}"
            if only_missing_modules and module_id in existing_modules:
                continue
            module = modules.setdefault(module_id, {"id": module_id, "package": row["package"], "name": row["module"], "Inp": [], "Get": [], "Set": []})
            section = str(row.get("section", "")).capitalize()
            if section in {"Inp", "Get", "Set"}:
                declaration = {key: row.get(key, "") for key in ("table", "group", "name", "file", "units", "type", "description")}
                if declaration not in module[section]:
                    module[section].append(declaration)


def main() -> None:
    if len(sys.argv) not in {3, 4}:
        raise SystemExit("Usage: build_dependency_catalog.py <specifications.csv> <output.json> [supplemental-specifications.csv]")
    source, output = Path(sys.argv[1]), Path(sys.argv[2])
    modules: dict[str, dict] = {}
    add_rows(modules, source)
    supplemental = Path(sys.argv[3]) if len(sys.argv) == 4 else Path(__file__).with_name("multimodal_module_specifications.csv")
    add_rows(modules, supplemental, only_missing_modules=True)
    payload = {"version": 1, "visionEvalVersion": "VE-40-RC6", "modules": modules}
    output.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {len(modules)} modules to {output}")


if __name__ == "__main__":
    main()
