#!/usr/bin/env python3
"""Build the separately installable PlanRVA model and InputLibrary package."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "resources/examples/planrva-mm"
VERSION = "2.0"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / f"dist/packages/planrva-{VERSION}.zip")
    args = parser.parse_args()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    source_manifest = json.loads((SOURCE / "manifest.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as temporary:
        package_root = Path(temporary) / f"planrva-{VERSION}"
        data = package_root / "data"
        shutil.copytree(SOURCE / "input-library", data / "input-library")
        shutil.copytree(SOURCE / "model-template", data / "model-template")
        shutil.copytree(SOURCE / "map-context", data / "map-context")
        shutil.copy2(SOURCE / "NOTICE.md", package_root / "NOTICE.md")
        template_path = data / "model-template" / "workbench_template.json"
        template = json.loads(template_path.read_text(encoding="utf-8"))
        template["importedAt"] = f"package-release-{VERSION}"
        template_path.write_text(json.dumps(template, indent=2) + "\n", encoding="utf-8")
        files = []
        for path in sorted(item for item in package_root.rglob("*") if item.is_file()):
            files.append({
                "path": path.relative_to(package_root).as_posix(),
                "size": path.stat().st_size,
                "sha256": sha256(path),
            })
        manifest = {
            "schemaVersion": 1,
            "type": "model-bundle",
            "id": source_manifest["id"],
            "name": "PlanRVA",
            "version": VERSION,
            "contentSourceVersion": source_manifest["version"],
            "description": "A ready-to-run VisionEval model and matching inputs for the PlanRVA region.",
            "compatibilitySummary": "VisionEval Workbench 2.0 on Apple Silicon Mac with a verified supported runtime.",
            "intendedUse": "Create and run PlanRVA baseline, scenario, and Hypercube projects.",
            "executionSupport": "Ready to run after Workbench verifies the supported VisionEval runtime.",
            "capabilities": [
                "Create PlanRVA projects and scenarios",
                "Run standard and Hypercube analyses",
                "Compare results with Virginia map context",
            ],
            "warnings": [],
            "inputLibrary": {
                "id": source_manifest["inputLibrary"]["id"],
                "name": "PlanRVA",
                "path": "data/input-library",
            },
            "modelTemplate": {
                "id": source_manifest["modelTemplate"]["id"],
                "name": source_manifest["modelTemplate"]["name"],
                "path": "data/model-template",
            },
            "comparisonMap": {
                "id": "planrva-virginia-map-context",
                "path": "data/map-context",
            },
            "compatibility": {
                **source_manifest.get("compatibility", {}),
                "minimumWorkbenchVersion": "2.0.0",
                "testedWorkbenchVersion": "2.0.0",
            },
            "provenance": source_manifest.get("provenance", {}),
            "files": files,
        }
        (package_root / "workbench-package.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(item for item in package_root.rglob("*") if item.is_file()):
                archive.write(path, path.relative_to(package_root.parent).as_posix())
    print(output)


if __name__ == "__main__":
    main()
