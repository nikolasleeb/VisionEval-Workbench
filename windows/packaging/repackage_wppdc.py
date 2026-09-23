#!/usr/bin/env python3
"""Rebuild the WPPDC model bundle with current user-facing names."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path

VERSION = "2.0"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, default=Path(f"wppdc-{VERSION}.zip"))
    args = parser.parse_args()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as temporary:
        extracted = Path(temporary) / "extracted"
        with zipfile.ZipFile(args.source.resolve()) as archive:
            archive.extractall(extracted)
        roots = [item for item in extracted.iterdir() if item.is_dir()]
        if len(roots) != 1:
            raise ValueError("WPPDC package must contain exactly one top-level directory")
        source_root = roots[0]
        package_root = Path(temporary) / f"wppdc-{VERSION}"
        source_root.rename(package_root)

        manifest_path = package_root / "workbench-package.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("id") != "wppdc-mm-v1":
            raise ValueError("Unexpected WPPDC package identity")
        source_version = str(manifest.get("version", ""))
        manifest["version"] = VERSION
        manifest["contentSourceVersion"] = source_version
        manifest["name"] = "WPPDC"
        manifest["description"] = "A ready-to-run VisionEval model and matching inputs for the WPPDC region."
        manifest["compatibilitySummary"] = "VisionEval Workbench 2.0 on Apple Silicon Mac with the verified VE-40-RC7 runtime."
        manifest["intendedUse"] = "Create and run WPPDC baseline, scenario, and Hypercube projects."
        manifest["executionSupport"] = "Ready to run after Workbench verifies the supported VisionEval runtime."
        manifest["capabilities"] = [
            "Create WPPDC projects and scenarios",
            "Run standard and Hypercube analyses",
            "Compare results with Virginia map context",
        ]
        manifest["warnings"] = []
        prior_compatibility = manifest.get("compatibility") or {}
        manifest["compatibility"] = {
            "minimumWorkbenchVersion": "2.0.0",
            "testedWorkbenchVersion": "2.0.0",
            "supportedVisionEvalVersions": ["VE-40-RC7"],
            "runtimeApi": 1,
            "architecture": "arm64",
            "runtimeDigest": prior_compatibility.get("runtimeDigest", ""),
        }
        manifest["inputLibrary"]["name"] = "WPPDC"
        manifest["modelTemplate"]["name"] = "WPPDC"

        template_path = package_root / manifest["modelTemplate"]["path"] / "workbench_template.json"
        template = json.loads(template_path.read_text(encoding="utf-8"))
        template["name"] = "WPPDC"
        template["importedAt"] = f"package-release-{VERSION}"
        template_path.write_text(json.dumps(template, indent=2) + "\n", encoding="utf-8")
        map_context_path = package_root / manifest["comparisonMap"]["path"] / "workbench-map-context.json"
        map_context = json.loads(map_context_path.read_text(encoding="utf-8"))
        map_context["version"] = "2026.09.19.1"
        geographies = map_context.get("comparisonMap", {}).setdefault("geographies", [])
        if not any(item.get("id") == "marea" for item in geographies):
            geographies.append({
                "id": "marea",
                "label": "Marea",
                "geometry": "bzone",
                "identifier": "Marea",
                "technicalLevel": "Marea",
            })
        map_context_path.write_text(json.dumps(map_context, indent=2) + "\n", encoding="utf-8")
        notice_path = package_root / "NOTICE.md"
        notice_path.write_text(
            notice_path.read_text(encoding="utf-8").replace("# WPPDC MM package notice", "# WPPDC package notice"),
            encoding="utf-8",
        )

        manifest["files"] = [
            {
                "path": path.relative_to(package_root).as_posix(),
                "size": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in sorted(package_root.rglob("*"))
            if path.is_file() and path != manifest_path
        ]
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(item for item in package_root.rglob("*") if item.is_file()):
                archive.write(path, path.relative_to(package_root.parent).as_posix())
    print(output)


if __name__ == "__main__":
    main()
