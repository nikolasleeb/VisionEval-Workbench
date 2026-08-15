#!/usr/bin/env python3
"""Build the Python sidecar with a Tauri-compatible platform suffix."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BIN_NAME = "visioneval-workbench-backend"
STAGED_PUBLIC = ROOT / "build" / "staged-public"
NATIVE_CLI = ROOT / "runtime" / "scripts" / "ve-cli-native.R"


def verify_native_cli() -> None:
    payload = NATIVE_CLI.read_bytes()
    if payload.startswith(b"\xef\xbb\xbf"):
        raise SystemExit(f"Native runtime entry script must not contain a UTF-8 BOM: {NATIVE_CLI}")
    try:
        payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SystemExit(f"Native runtime entry script is not valid UTF-8: {NATIVE_CLI}") from exc


def stage_public(comparison_map_3d: bool) -> Path:
    if STAGED_PUBLIC.exists():
        shutil.rmtree(STAGED_PUBLIC)
    shutil.copytree(ROOT / "public", STAGED_PUBLIC)
    capability = {"comparisonMap3d": comparison_map_3d}
    (STAGED_PUBLIC / "build-capabilities.js").write_text(
        "window.__WORKBENCH_BUILD_CAPABILITIES__ = Object.freeze("
        + json.dumps(capability, separators=(",", ":"))
        + ");\n",
        encoding="utf-8",
        newline="\n",
    )
    return STAGED_PUBLIC


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
        default=os.environ.get("WORKBENCH_DOCUMENTATION_SOURCE", "docs/user"),
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
    verify_native_cli()
    staged_public = stage_public(args.comparison_map_3d == "enabled")
    subprocess.run(
        [sys.executable, "-c", "import xlsxwriter, PyInstaller"], check=True
    )
    environment = os.environ.copy()
    environment["WORKBENCH_STAGED_PUBLIC"] = str(staged_public)
    environment["WORKBENCH_DOCUMENTATION_SOURCE"] = str(documentation_source)
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
    target_triple = args.target_triple or rust_host()
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
