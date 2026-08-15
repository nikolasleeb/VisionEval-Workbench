#!/usr/bin/env python3
"""Build and verify the bundled PlanRVA example manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "resources" / "examples" / "planrva-mm"
MANIFEST = EXAMPLE / "manifest.json"
FORBIDDEN = re.compile(
    rb"(?:/Users/|\\Users\\|nikolasleebishop|api[_-]?key|private[_-]?key|password\s*[:=]|secret\s*[:=]|token\s*[:=])",
    re.IGNORECASE,
)
EXPECTED_INPUT_CSVS = 51


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def inventory() -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    paths = (item for item in EXAMPLE.rglob("*") if item.is_file() and item != MANIFEST)
    for path in sorted(paths, key=lambda item: item.relative_to(EXAMPLE).as_posix()):
        data = path.read_bytes()
        if FORBIDDEN.search(data):
            raise SystemExit(f"Forbidden private or credential-like text in {path.relative_to(ROOT)}")
        output.append({
            "path": path.relative_to(EXAMPLE).as_posix(),
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        })
    return output


def build_payload() -> dict[str, object]:
    input_csvs = sorted((EXAMPLE / "input-library").glob("*.csv"))
    if len(input_csvs) != EXPECTED_INPUT_CSVS:
        raise SystemExit(f"Expected {EXPECTED_INPUT_CSVS} input CSVs, found {len(input_csvs)}")
    required = [
        EXAMPLE / "model-template" / "visioneval.cnf",
        EXAMPLE / "model-template" / "scripts" / "run_model.R",
        EXAMPLE / "model-template" / "defs" / "geo.csv",
        EXAMPLE / "model-template" / "defs" / "units.csv",
        EXAMPLE / "model-template" / "defs" / "deflators.csv",
        EXAMPLE / "model-template" / "queries" / "Full-Query.VEqry",
        EXAMPLE / "model-template" / "inputs" / "model_parameters.json",
    ]
    missing = [path.relative_to(EXAMPLE).as_posix() for path in required if not path.is_file()]
    if missing:
        raise SystemExit("Bundled PlanRVA model is incomplete: " + ", ".join(missing))
    files = inventory()
    tree_digest = hashlib.sha256()
    for record in files:
        tree_digest.update(str(record["path"]).encode("utf-8"))
        tree_digest.update(str(record["sha256"]).encode("ascii"))
    return {
        "schemaVersion": 1,
        "id": "planrva-mm-v1",
        "version": "1.0.0",
        "name": "PlanRVA MM Example",
        "assetType": "bundled-example",
        "inputLibrary": {"id": "PlanRVA MM", "csvCount": EXPECTED_INPUT_CSVS, "inputFileCount": 52},
        "modelTemplate": {
            "id": "template-planrva-mm-8f140cd4cb",
            "name": "PlanRVA MM",
            "fingerprint": "20d581d194edb965960506ca61dcb320f7314ff1c80b79fe07ca2a25ffd274b8",
        },
        "comparisonMap": {
            "id": "planrva-virginia-map-context",
            "path": "map-context",
        },
        "compatibility": {
            "workbenchVersion": "1.0.0",
            "visionEvalVersion": "VE-40-RC6",
            "runtimeImage": "ghcr.io/nikolasleeb/visioneval-workbench-runtime:1.0.0-arm64",
            "runtimeDigest": "sha256:b19208b5788e3c9fbb38b7d81dcdb9f052c349453695b69966cad95e827629b0",
            "patch": "2026-08-03-composite-household-id-alignment",
            "architecture": "arm64",
        },
        "provenance": {
            "owner": "PlanRVA",
            "source": "Public PlanRVA VisionEval multimodal planning model and input data",
            "notice": "Public planning example provided without warranty; not owned or published by VisionEval.",
        },
        "treeSha256": tree_digest.hexdigest(),
        "files": files,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Verify the tracked manifest without rewriting it")
    args = parser.parse_args()
    payload = build_payload()
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not MANIFEST.is_file() or MANIFEST.read_text(encoding="utf-8") != rendered:
            if MANIFEST.is_file():
                tracked = json.loads(MANIFEST.read_text(encoding="utf-8"))
                tracked_files = {record["path"]: record for record in tracked.get("files", [])}
                current_files = {record["path"]: record for record in payload["files"]}
                changed = sorted(
                    path
                    for path in tracked_files.keys() | current_files.keys()
                    if tracked_files.get(path) != current_files.get(path)
                )
                print(
                    "Bundled PlanRVA manifest mismatch: "
                    f"tracked tree {tracked.get('treeSha256')}, current tree {payload['treeSha256']}; "
                    f"changed files: {', '.join(changed[:10]) or 'metadata only'}"
                )
            raise SystemExit("Bundled PlanRVA manifest is missing or stale; run packaging/build_bundled_assets.py")
        print(f"Bundled PlanRVA example verified: {len(payload['files'])} files, {payload['treeSha256']}")
        return
    MANIFEST.write_text(rendered, encoding="utf-8", newline="\n")
    print(f"Wrote {MANIFEST.relative_to(ROOT)} with {len(payload['files'])} files")


if __name__ == "__main__":
    main()
