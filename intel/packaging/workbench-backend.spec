# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path

root = Path(SPEC).resolve().parent.parent
staged_public = Path(os.environ.get("WORKBENCH_STAGED_PUBLIC", root / "build" / "staged-public"))
if not staged_public.is_dir():
    raise RuntimeError("Run packaging/build_backend.py so the staged public tree and capability flag are generated")
documentation_source = Path(os.environ.get("WORKBENCH_DOCUMENTATION_SOURCE", root / "docs" / "user-intel"))
if not documentation_source.is_dir():
    raise RuntimeError(f"Documentation source does not exist: {documentation_source}")
datas = [
    (str(staged_public), "public"),
    (str(root / "backend" / "rda_reader.R"), "."),
    (str(root / "backend" / "comparison_scan.R"), "."),
    (str(root / "backend" / "comparison_cache_extract.R"), "."),
    (str(root / "backend" / "explore_catalog.json"), "."),
    (str(root / "backend" / "unit_conflicts.json"), "."),
    (str(root / "backend" / "dependency_catalog.json"), "."),
    (str(root / "backend" / "asset_catalog.json"), "."),
    (str(root / "resources" / "examples" / "planrva-mm"), "bundled_assets/planrva-mm"),
    (str(root / "runtime" / "scripts" / "ve-cli-native.R"), "."),
    (str(documentation_source), "docs/user"),
]

a = Analysis(
    [str(root / "backend" / "main.py")],
    pathex=[str(root / "backend")],
    binaries=[],
    datas=datas,
    hiddenimports=["xlsxwriter"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="visioneval-workbench-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    # This binary is a background HTTP sidecar, not a second macOS GUI app.
    # The windowed bootloader calls TransformProcessType/RegisterApplication
    # and can abort when the Tauri app launches it as a child process.
    console=True,
)
