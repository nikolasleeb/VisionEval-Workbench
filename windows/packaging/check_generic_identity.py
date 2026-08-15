#!/usr/bin/env python3
"""Reject optional-package branding in model-neutral Workbench surfaces."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERIC_TARGETS = (
    ROOT / "public",
    ROOT / "desktop" / "src-tauri" / "src",
    ROOT / "backend" / "workbench" / "runtime.py",
    ROOT / "backend" / "workbench" / "region_builder.py",
    ROOT / "backend" / "workbench" / "dependencies.py",
    ROOT / "backend" / "workbench" / "explore.py",
    ROOT / "packaging" / "build_va_region_package.py",
    ROOT / "resources" / "region-builder",
)


def violations() -> list[str]:
    found: list[str] = []
    for target in GENERIC_TARGETS:
        files = target.rglob("*") if target.is_dir() else (target,)
        for path in files:
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if "planrva" in text.lower():
                found.append(path.relative_to(ROOT).as_posix())
    return sorted(found)


def main() -> None:
    found = violations()
    if found:
        raise SystemExit("Optional package branding found in generic Workbench surfaces: " + ", ".join(found))
    print("Generic Workbench identity check passed")


if __name__ == "__main__":
    main()
