#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "macos" / "docs" / "update-manifest.json"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_manifest(runtime_index: dict | None = None) -> dict:
    mac = read_json(ROOT / "macos" / "docs" / "compatibility-manifest.json")
    version = read_json(ROOT / "macos" / "desktop" / "src-tauri" / "tauri.conf.json")["version"]
    if str(mac.get("applicationVersion")) != str(version):
        raise SystemExit("macOS compatibility manifest and Tauri version do not match")

    def image(record: dict, architecture: str) -> dict:
        runtime = record["runtimeImage"]
        digest = str(runtime["digest"])
        if not digest.startswith("sha256:") or len(digest) != 71:
            raise SystemExit(f"Invalid {architecture} runtime digest")
        return {
            "platform": "macos",
            "architecture": architecture,
            "reference": runtime.get("digestReference") or f"{runtime['reference'].split(':', 1)[0]}@{digest}",
            "digest": digest,
            "minimumWorkbenchVersion": str(version),
            "visionEvalVersion": str(record["visionEvalVersion"]),
        }

    runtime_images = [image(mac, "arm64")]
    vision_eval_version = str(mac["visionEvalVersion"])
    if runtime_index is not None:
        if runtime_index.get("schemaVersion") != 1 or runtime_index.get("runtimeApi") != 1:
            raise SystemExit("Runtime index is not compatible with Workbench 2.0")
        minimum_workbench = str(runtime_index.get("minimumWorkbenchVersion") or "")
        if minimum_workbench != str(version):
            raise SystemExit("Runtime index minimum Workbench version does not match this build")
        indexed = runtime_index.get("images")
        if not isinstance(indexed, list) or {item.get("architecture") for item in indexed} != {"arm64", "x86_64"}:
            raise SystemExit("Runtime index must contain ARM64 and x86_64 images")
        runtime_images = []
        for item in indexed:
            digest = str(item.get("digest") or "")
            reference = str(item.get("reference") or "")
            if not digest.startswith("sha256:") or len(digest) != 71 or reference != f"ghcr.io/nikolasleeb/visioneval-workbench-runtime@{digest}":
                raise SystemExit("Runtime index contains an invalid immutable reference")
            runtime_images.append({
                "platform": "macos",
                "architecture": str(item["architecture"]),
                "reference": reference,
                "digest": digest,
                "minimumWorkbenchVersion": minimum_workbench,
                "visionEvalVersion": str(runtime_index["preferredVisionEvalVersion"]),
                "runtimeApi": 1,
                "downloadSizeBytes": int(item.get("downloadSizeBytes") or 0),
                "storageSizeBytes": int(item.get("storageSizeBytes") or 0),
            })
        vision_eval_version = str(runtime_index["preferredVisionEvalVersion"])
    return {
        "schemaVersion": 1,
        "workbench": {
            "version": str(version),
            "releaseUrl": f"https://github.com/nikolasleeb/VisionEval-Workbench/releases/tag/v{version}",
        },
        "visionEval": {
            "version": vision_eval_version,
            "releaseUrl": "https://github.com/VisionEval/VisionEval-4/releases",
        },
        "runtimeImages": runtime_images,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--runtime-index", type=Path)
    args = parser.parse_args()
    payload = json.dumps(build_manifest(read_json(args.runtime_index) if args.runtime_index else None), indent=2, sort_keys=True) + "\n"
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != payload:
            raise SystemExit(f"Update manifest is stale: {args.output}")
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8")


if __name__ == "__main__":
    main()
