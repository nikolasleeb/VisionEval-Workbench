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
VERSION = "2.0.0"
SHARED_MAP_ID = "virginia-mpo-regions"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024): digest.update(block)
    return digest.hexdigest()


def shared_virginia_map_context(path: Path, target: Path, template_id: str) -> None:
    with zipfile.ZipFile(path) as archive:
        manifests = [name for name in archive.namelist() if Path(name).name == "workbench-package.json"]
        if len(manifests) != 1: raise SystemExit(f"Virginia package must contain one workbench-package.json: {path}")
        manifest_name = manifests[0]; prefix = manifest_name.rsplit("/", 1)[0]; manifest = json.loads(archive.read(manifest_name))
        if manifest.get("type") != "region-builder" or manifest.get("id") != SHARED_MAP_ID: raise SystemExit(f"Not a compatible Virginia MPO package: {path}")
        builder = manifest.get("builder", {})
        def package_bytes(relative: str) -> bytes:
            name = f"{prefix}/{relative}" if prefix else relative
            try: return archive.read(name)
            except KeyError as exc: raise SystemExit(f"Virginia package resource is missing: {relative}") from exc
        files = {"regions.json": str(builder.get("regionsPath", "")), "mpo_bzone_crosswalk.json": str(builder.get("crosswalkPath", "")), "virginia_county_equivalents_2020.txt": str(builder.get("localitiesPath", "")), "SOURCES.md": str(manifest.get("sourcesDocument", ""))}
        if any(not value for value in files.values()) or not isinstance(manifest.get("comparisonMap"), dict): raise SystemExit(f"Virginia package map metadata is incomplete: {path}")
        target.mkdir(parents=True, exist_ok=True)
        for filename, relative in files.items(): (target / filename).write_bytes(package_bytes(relative))
        context = {"schemaVersion": 1, "type": "map-context", "id": SHARED_MAP_ID, "name": "Virginia MPO Map Context for PlanRVA", "version": str(manifest["version"]), "coverage": "Virginia", "componentOf": "planrva-mm-v1", "compatibleTemplateIds": [template_id], "description": "Virginia map context shared with the Virginia MPO package for PlanRVA comparison maps.", "builder": {"kind": "statewide-map-context", "regionsPath": "regions.json", "crosswalkPath": "mpo_bzone_crosswalk.json", "localitiesPath": "virginia_county_equivalents_2020.txt"}, "comparisonMap": manifest["comparisonMap"], "sourcesDocument": "SOURCES.md"}
        (target / "workbench-map-context.json").write_text(json.dumps(context, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, default=ROOT / "dist/packages/planrva-mm.zip"); parser.add_argument("--shared-map-package", type=Path, required=True, help="Virginia MPO package whose map provider and cache should be shared"); args = parser.parse_args()
    output = args.output.resolve(); output.parent.mkdir(parents=True, exist_ok=True); source_manifest = json.loads((SOURCE / "manifest.json").read_text(encoding="utf-8"))
    compatibility = {key: value for key, value in source_manifest.get("compatibility", {}).items() if key not in {"architecture", "runtimeDigest", "runtimeImage"}}
    with tempfile.TemporaryDirectory() as temporary:
        package_root = Path(temporary) / f"planrva-mm-{VERSION}"; data = package_root / "data"
        shutil.copytree(SOURCE / "input-library", data / "input-library"); shutil.copytree(SOURCE / "model-template", data / "model-template"); shared_virginia_map_context(args.shared_map_package.expanduser().resolve(), data / "map-context", str(source_manifest["modelTemplate"]["id"])); shutil.copy2(SOURCE / "NOTICE.md", package_root / "NOTICE.md")
        files = [{"path": path.relative_to(package_root).as_posix(), "size": path.stat().st_size, "sha256": sha256(path)} for path in sorted(item for item in package_root.rglob("*") if item.is_file())]
        manifest = {"schemaVersion": 1, "type": "model-bundle", "id": source_manifest["id"], "name": "PlanRVA MM", "version": VERSION, "description": "PlanRVA multimodal model and matching InputLibrary with the shared Virginia online map provider.", "inputLibrary": {"id": source_manifest["inputLibrary"]["id"], "name": "PlanRVA MM", "path": "data/input-library"}, "modelTemplate": {"id": source_manifest["modelTemplate"]["id"], "name": source_manifest["modelTemplate"]["name"], "path": "data/model-template"}, "comparisonMap": {"id": SHARED_MAP_ID, "path": "data/map-context"}, "compatibility": compatibility, "provenance": source_manifest.get("provenance", {}), "files": files}
        (package_root / "workbench-package.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(item for item in package_root.rglob("*") if item.is_file()): archive.write(path, path.relative_to(package_root.parent).as_posix())
    print(output)


if __name__ == "__main__": main()
