#!/usr/bin/env python3
"""Assert that every deterministic renderer asset is present and declared."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    "vendor/maplibre/maplibre-gl.js",
    "vendor/maplibre/maplibre-gl.css",
    "vendor/maplibre/LICENSE.txt",
    "vendor/maplibre/README.md",
    "build-capabilities.js",
    "renderer-assets.json",
    "map3d-smoke.html",
    "map3d-smoke.js",
    "extrusion-borders.js",
}


def check(public: Path) -> None:
    manifest = json.loads((public / "renderer-assets.json").read_text(encoding="utf-8"))
    declared = {item["path"] for item in manifest["assets"]}
    missing = REQUIRED - declared
    if missing:
        raise SystemExit(f"Renderer manifest is missing declarations: {sorted(missing)}")
    absent = [relative for relative in REQUIRED if not (public / relative).is_file()]
    if absent:
        raise SystemExit(f"Renderer assets are absent: {sorted(absent)}")
    bundle = (public / "vendor/maplibre/maplibre-gl.js").read_text(encoding="utf-8")
    if "maplibre-gl-shared.mjs" in bundle or "import.meta" in bundle:
        raise SystemExit("Renderer bundle still depends on a module-relative artifact")
    if (public / "vendor/maplibre/maplibre-gl.mjs").exists() or (public / "map3d.js").exists():
        raise SystemExit("Obsolete MapLibre module artifacts are still present")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("public", nargs="?", type=Path, default=ROOT / "public")
    args = parser.parse_args()
    check(args.public.resolve())


if __name__ == "__main__":
    main()
