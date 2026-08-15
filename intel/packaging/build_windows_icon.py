from __future__ import annotations

import argparse
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ICON_DIR = ROOT / "desktop" / "src-tauri" / "icons"
SOURCES = ["32x32.png", "64x64.png", "128x128.png", "128x128@2x.png"]
OUTPUT = ICON_DIR / "icon.ico"


def png_size(data: bytes) -> tuple[int, int]:
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise ValueError("Icon source is not a valid PNG")
    return struct.unpack(">II", data[16:24])


def build_icon() -> bytes:
    images: list[tuple[int, int, bytes]] = []
    for name in SOURCES:
        data = (ICON_DIR / name).read_bytes()
        width, height = png_size(data)
        if width != height or width not in {32, 64, 128, 256}:
            raise ValueError(f"Unexpected icon frame {name}: {width}x{height}")
        images.append((width, height, data))
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries = bytearray()
    payload = bytearray()
    for width, height, data in images:
        entries.extend(struct.pack("<BBBBHHII", width if width < 256 else 0, height if height < 256 else 0, 0, 0, 1, 32, len(data), offset))
        payload.extend(data)
        offset += len(data)
    return header + bytes(entries) + bytes(payload)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the multi-resolution Windows Workbench icon")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = build_icon()
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_bytes() != expected:
            raise SystemExit("desktop/src-tauri/icons/icon.ico is stale or invalid; run packaging/build_windows_icon.py")
        return 0
    OUTPUT.write_bytes(expected)
    print(f"Wrote {OUTPUT} ({len(expected)} bytes, {len(SOURCES)} frames)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
