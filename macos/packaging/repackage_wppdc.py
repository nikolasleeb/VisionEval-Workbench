#!/usr/bin/env python3
"""Rebuild the WPPDC model bundle with current user-facing names."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path

VERSION = "1.2"


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
        manifest["version"] = VERSION
        manifest["name"] = "WPPDC"
        manifest["inputLibrary"]["name"] = "WPPDC"
        manifest["modelTemplate"]["name"] = "WPPDC"

        template_path = package_root / manifest["modelTemplate"]["path"] / "workbench_template.json"
        template = json.loads(template_path.read_text(encoding="utf-8"))
        template["name"] = "WPPDC"
        template["importedAt"] = f"package-release-{VERSION}"
        template_path.write_text(json.dumps(template, indent=2) + "\n", encoding="utf-8")
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
