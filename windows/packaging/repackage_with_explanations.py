#!/usr/bin/env python3
"""Add the checked Virginia input-explanation catalog to a Workbench package."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "backend" / "explore_catalog.json"
EXPLANATION_ID = "virginia-visioneval-input-explanations"
EXPLANATION_VERSION = "2026.09.16.1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def safe_extract(archive: zipfile.ZipFile, target: Path) -> None:
    for info in archive.infolist():
        pure = PurePosixPath(info.filename)
        if pure.is_absolute() or ".." in pure.parts or "\\" in info.filename:
            raise SystemExit(f"Unsafe archive path: {info.filename}")
        if ((info.external_attr >> 16) & 0o170000) == 0o120000:
            raise SystemExit(f"Archive contains a symbolic link: {info.filename}")
    archive.extractall(target)


def package_root(extracted: Path) -> Path:
    manifests = [
        path for path in extracted.rglob("workbench-package.json")
        if "__MACOSX" not in path.parts
    ]
    if len(manifests) != 1:
        raise SystemExit(f"Expected one package manifest; found {len(manifests)}")
    return manifests[0].parent


def explanation_key(filename: str) -> str:
    return Path(filename).stem.lower()


def package_catalog(input_root: Path, package_name: str) -> tuple[dict, list[str]]:
    source = json.loads(CATALOG.read_text(encoding="utf-8"))
    explanations = dict(source.get("explanations", {}))
    # The Virginia guide describes azone_lttrk_prop.csv in the historical
    # azone_hh_lttrk_prop sheet, so retain that source text under both names.
    explanations.setdefault("azone_lttrk_prop", explanations.get("azone_hh_lttrk_prop", {}))
    explanations.setdefault("model_parameters", explanations.get("model_parameters.json", {}))
    explanations.setdefault("marea_transit_biofuel_mix", {
        "document": "packaged-definition",
        "html": (
            "<h3>Definition of the Input File</h3>"
            "<p>This file specifies, by Marea and model year, the renewable blend shares used by "
            "non-electric transit fuels: ethanol in gasoline, biodiesel in diesel, and renewable "
            "natural gas in compressed natural gas. Values are proportions from 0 to 1.</p>"
            "<h3>Use in scenarios</h3>"
            "<p>Change these values to test transit-fuel blending assumptions. Keep each value within "
            "0 and 1 and review the companion transit fuel and powertrain files so the shares remain "
            "internally consistent.</p>"
        ),
    })

    package_files = sorted(path.name for path in input_root.iterdir() if path.is_file())
    reference_root = ROOT / "resources" / "examples" / "planrva-mm" / "input-library"
    filenames = sorted(path.name for path in reference_root.iterdir() if path.is_file())
    selected: dict[str, dict] = {}
    missing: list[str] = []
    for filename in filenames:
        key = explanation_key(filename)
        item = explanations.get(key)
        if not item:
            missing.append(filename)
        else:
            selected[key] = item
    if missing:
        raise SystemExit("No input explanation is available for: " + ", ".join(missing))
    uncovered = sorted(set(package_files) - set(filenames))
    if uncovered:
        raise SystemExit("Package inputs are not covered by the shared Virginia guide: " + ", ".join(uncovered))

    input_fields = {
        key: value for key, value in source.get("inputFields", {}).items()
        if Path(key).name.lower() in {name.lower() for name in filenames}
    }
    catalog = {
        "version": 1,
        "package": {
            "id": EXPLANATION_ID,
            "name": "Virginia VisionEval Input Explanations",
            "version": EXPLANATION_VERSION,
            "description": "Input-file definitions for the Virginia VisionEval multimodal input set.",
            "appliesTo": {"state": "VA"},
        },
        "variables": source.get("variables", {}),
        "inputFields": input_fields,
        "explanations": selected,
        "coveredFiles": filenames,
    }
    return catalog, filenames


def repackage(source_zip: Path, output: Path, version: str) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        temp = Path(temporary)
        with zipfile.ZipFile(source_zip) as archive:
            safe_extract(archive, temp / "source")
        source_root = package_root(temp / "source")
        manifest = json.loads((source_root / "workbench-package.json").read_text(encoding="utf-8"))
        manifest["version"] = version

        wrapper = temp / f"{manifest['id']}-{version}"
        shutil.copytree(source_root, wrapper, ignore=shutil.ignore_patterns("workbench-package.json", ".DS_Store", "__MACOSX"))
        input_root = wrapper / str(manifest["inputLibrary"]["path"])
        catalog, covered_files = package_catalog(input_root, str(manifest["name"]))
        catalog_path = wrapper / "data" / "input-explanations" / "catalog.json"
        catalog_path.parent.mkdir(parents=True, exist_ok=True)
        catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        manifest["inputExplanations"] = {
            "id": EXPLANATION_ID,
            "name": "Virginia VisionEval Input Explanations",
            "version": EXPLANATION_VERSION,
            "path": "data/input-explanations/catalog.json",
            "fileCount": len(covered_files),
            "appliesTo": {"state": "VA"},
        }

        inventory = []
        for path in sorted(item for item in wrapper.rglob("*") if item.is_file()):
            relative = path.relative_to(wrapper).as_posix()
            inventory.append({"path": relative, "size": path.stat().st_size, "sha256": sha256(path)})
        manifest["files"] = inventory
        (wrapper / "workbench-package.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(item for item in wrapper.rglob("*") if item.is_file()):
                archive.write(path, f"{wrapper.name}/{path.relative_to(wrapper).as_posix()}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    repackage(args.source.resolve(), args.output.resolve(), args.version)
    print(args.output.resolve())


if __name__ == "__main__":
    main()
