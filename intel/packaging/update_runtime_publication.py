#!/usr/bin/env python3
"""Pin or verify the published Intel AMD64 runtime identity."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PENDING_DIGEST = "sha256:" + ("0" * 64)
DIGEST_PATTERN = re.compile(r"sha256:[0-9a-f]{64}")
RUNTIME_MODULE = ROOT / "backend/workbench/runtime.py"
TEXT_TARGETS = [
    ROOT / "packaging/build_bundled_assets.py",
    ROOT / "public/index.html",
]
JSON_TARGETS = [
    ROOT / "docs/compatibility-manifest-intel.json",
    ROOT / "docs/compatibility-manifest.json",
]


def validate_digest(value: str) -> str:
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
        raise SystemExit("Digest must be sha256 followed by 64 lowercase hexadecimal characters")
    if value == PENDING_DIGEST:
        raise SystemExit("The AMD64 runtime digest is still pending")
    return value


def pinned_digest() -> str:
    text = RUNTIME_MODULE.read_text(encoding="utf-8")
    match = re.search(r'^PINNED_AMD64_RUNTIME_DIGEST = "(sha256:[0-9a-f]{64})"$', text, re.MULTILINE)
    if not match:
        raise SystemExit("Could not read PINNED_AMD64_RUNTIME_DIGEST")
    return match.group(1)


def update(digest: str, revision: str) -> None:
    runtime_text = RUNTIME_MODULE.read_text(encoding="utf-8")
    runtime_text, count = re.subn(
        r'^PINNED_AMD64_RUNTIME_DIGEST = "sha256:[0-9a-f]{64}"$',
        f'PINNED_AMD64_RUNTIME_DIGEST = "{digest}"',
        runtime_text,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise SystemExit("Could not update the pinned runtime digest constant")
    RUNTIME_MODULE.write_text(runtime_text, encoding="utf-8")

    for path in TEXT_TARGETS:
        text = path.read_text(encoding="utf-8")
        updated, count = DIGEST_PATTERN.subn(digest, text)
        if not count:
            raise SystemExit(f"No runtime digest found in {path.relative_to(ROOT)}")
        path.write_text(updated, encoding="utf-8")

    for path in JSON_TARGETS:
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["releaseStatus"] = "public"
        for supported in payload.get("supported", []):
            if supported.get("platform") == "macOS" and supported.get("architecture") == "x86_64":
                supported["status"] = "released"
        runtime = payload["runtimeImage"]
        runtime["digest"] = digest
        if "digestReference" in runtime:
            runtime["digestReference"] = f"ghcr.io/nikolasleeb/visioneval-workbench-runtime@{digest}"
            runtime["immutableTag"] = f"1.0.0-amd64-{revision[:12]}"
            runtime["buildRevision"] = revision
        runtime["published"] = True
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def check() -> None:
    digest = validate_digest(pinned_digest())
    for path in TEXT_TARGETS:
        values = set(DIGEST_PATTERN.findall(path.read_text(encoding="utf-8")))
        if values != {digest}:
            raise SystemExit(f"Runtime digest mismatch in {path.relative_to(ROOT)}: {sorted(values)}")
    for path in JSON_TARGETS:
        payload = json.loads(path.read_text(encoding="utf-8"))
        runtime = payload["runtimeImage"]
        if payload.get("releaseStatus") != "public" or runtime.get("digest") != digest or not runtime.get("published"):
            raise SystemExit(f"Runtime publication metadata is incomplete in {path.relative_to(ROOT)}")
        intel_entries = [
            item for item in payload.get("supported", [])
            if item.get("platform") == "macOS" and item.get("architecture") == "x86_64"
        ]
        if intel_entries and any(item.get("status") != "released" for item in intel_entries):
            raise SystemExit(f"Intel application support is not marked released in {path.relative_to(ROOT)}")
    print(f"Intel AMD64 runtime publication is pinned consistently: {digest}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--digest")
    parser.add_argument("--revision")
    args = parser.parse_args()
    if args.check:
        check()
        return
    if not args.digest or not args.revision or not re.fullmatch(r"[0-9a-f]{40}", args.revision):
        raise SystemExit("Updating requires --digest and a 40-character --revision")
    update(validate_digest(args.digest), args.revision)
    print(f"Pinned Intel AMD64 runtime {args.digest} at revision {args.revision}")


if __name__ == "__main__":
    main()
