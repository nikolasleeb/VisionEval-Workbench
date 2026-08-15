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
VERSION = "1.0.0"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dist/packages/planrva-mm.zip")
    args = parser.parse_args()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    source_manifest = json.loads((SOURCE / "manifest.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as temporary:
        package_root = Path(temporary) / f"planrva-mm-{VERSION}"
        data = package_root / "data"
        shutil.copytree(SOURCE / "input-library", data / "input-library")
        shutil.copytree(SOURCE / "model-template", data / "model-template")
        shutil.copytree(SOURCE / "map-context", data / "map-context")
        shutil.copy2(SOURCE / "NOTICE.md", package_root / "NOTICE.md")
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
            "name": "PlanRVA MM",
            "version": source_manifest["version"],
            "description": "PlanRVA multimodal VisionEval model template and matching InputLibrary.",
            "inputLibrary": {
                "id": source_manifest["inputLibrary"]["id"],
                "name": "PlanRVA MM",
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
            "compatibility": source_manifest.get("compatibility", {}),
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
