#!/usr/bin/env python3
"""Build the Python sidecar with a Tauri-compatible platform suffix."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BIN_NAME = "visioneval-workbench-backend"
STAGED_PUBLIC = ROOT / "build" / "staged-public"
STAGED_DOCUMENTATION = ROOT / "build" / "staged-documentation"


def stage_public(comparison_map_3d: bool, target_triple: str) -> Path:
    if STAGED_PUBLIC.exists():
        shutil.rmtree(STAGED_PUBLIC)
    shutil.copytree(ROOT / "public", STAGED_PUBLIC)
    platform_name = "macos" if "apple-darwin" in target_triple else "windows" if "windows" in target_triple else ""
    if platform_name:
        markup_path = STAGED_PUBLIC / "index.html"
        markup = markup_path.read_text(encoding="utf-8")
        for candidate in ("macos", "windows"):
            pattern = rf"<!-- runtime-platform:{candidate}:start -->.*?<!-- runtime-platform:{candidate}:end -->"
            if candidate == platform_name:
                markup = re.sub(rf"<!-- runtime-platform:{candidate}:(?:start|end) -->", "", markup)
            else:
                markup = re.sub(pattern, "", markup, flags=re.DOTALL)
        markup_path.write_text(markup, encoding="utf-8")
    capability = {"comparisonMap3d": comparison_map_3d}
    (STAGED_PUBLIC / "build-capabilities.js").write_text(
        "window.__WORKBENCH_BUILD_CAPABILITIES__ = Object.freeze("
        + json.dumps(capability, separators=(",", ":"))
        + ");\n",
        encoding="utf-8",
    )
    return STAGED_PUBLIC


def stage_documentation(source: Path) -> Path:
    if STAGED_DOCUMENTATION.exists():
        shutil.rmtree(STAGED_DOCUMENTATION)
    manifest_path = source / "documentation.json"
    metadata = json.loads(manifest_path.read_text(encoding="utf-8"))
    if int(metadata.get("schemaVersion", 1)) < 2:
        shutil.copytree(source, STAGED_DOCUMENTATION)
        return STAGED_DOCUMENTATION
    documents = metadata.get("documents")
    if not isinstance(documents, list) or not documents:
        raise SystemExit("The documentation catalog has no documents")
    STAGED_DOCUMENTATION.mkdir(parents=True)
    shutil.copy2(manifest_path, STAGED_DOCUMENTATION / manifest_path.name)
    for item in documents:
        filename = str(item.get("filename", "")) if isinstance(item, dict) else ""
        relative = Path(filename)
        if not filename or relative.is_absolute() or len(relative.parts) != 1 or relative.suffix.lower() != ".pdf":
            raise SystemExit(f"Unsafe documentation catalog filename: {filename}")
        pdf = source / relative
        if not pdf.is_file():
            raise SystemExit(f"Documentation PDF does not exist: {pdf}")
        shutil.copy2(pdf, STAGED_DOCUMENTATION / relative)
    return STAGED_DOCUMENTATION


def rust_host() -> str:
    output = subprocess.check_output(["rustc", "-Vv"], text=True)
    for line in output.splitlines():
        if line.startswith("host:"):
            return line.split(":", 1)[1].strip()
    raise RuntimeError("rustc did not report a host target")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--comparison-map-3d",
        choices=("enabled", "disabled"),
        default=os.environ.get("WORKBENCH_COMPARISON_MAP_3D", "enabled"),
    )
    parser.add_argument(
        "--documentation-source",
        default=os.environ.get("WORKBENCH_DOCUMENTATION_SOURCE", "docs/user-macos"),
        help="Guide tree to bundle as docs/user (relative paths resolve from the repository root)",
    )
    parser.add_argument(
        "--target-triple",
        default=None,
        help="Tauri sidecar target suffix; defaults to the current rustc host",
    )
    args = parser.parse_args()
    documentation_source = Path(args.documentation_source)
    if not documentation_source.is_absolute():
        documentation_source = ROOT / documentation_source
    documentation_source = documentation_source.resolve()
    if not documentation_source.is_dir():
        raise SystemExit(f"Documentation source does not exist: {documentation_source}")
    target_triple = args.target_triple or rust_host()
    staged_public = stage_public(args.comparison_map_3d == "enabled", target_triple)
    staged_documentation = stage_documentation(documentation_source)
    subprocess.run(
        [sys.executable, "-c", "import xlsxwriter, PyInstaller"], check=True
    )
    environment = os.environ.copy()
    environment["WORKBENCH_STAGED_PUBLIC"] = str(staged_public)
    environment["WORKBENCH_DOCUMENTATION_SOURCE"] = str(staged_documentation)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--clean",
            "--noconfirm",
            str(ROOT / "packaging" / "workbench-backend.spec"),
        ],
        cwd=ROOT,
        env=environment,
        check=True,
    )
    extension = ".exe" if sys.platform == "win32" else ""
    source = ROOT / "dist" / f"{BIN_NAME}{extension}"
    destination = (
        ROOT
        / "desktop"
        / "src-tauri"
        / "binaries"
        / f"{BIN_NAME}-{target_triple}{extension}"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    print(
        f"Prepared Workbench backend for {target_triple}: {destination} "
        f"(documentation: {documentation_source})"
    )


if __name__ == "__main__":
    main()
