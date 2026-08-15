import struct
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WindowsIconTests(unittest.TestCase):
    def test_workbench_icon_has_valid_multiresolution_png_frames(self):
        data = (ROOT / "desktop" / "src-tauri" / "icons" / "icon.ico").read_bytes()
        reserved, kind, count = struct.unpack("<HHH", data[:6])
        self.assertEqual((reserved, kind, count), (0, 1, 4))
        sizes = []
        for index in range(count):
            entry = struct.unpack("<BBBBHHII", data[6 + index * 16:22 + index * 16])
            width, height, _, _, planes, depth, length, offset = entry
            sizes.append((width or 256, height or 256))
            self.assertEqual((planes, depth), (1, 32))
            self.assertEqual(data[offset:offset + 8], b"\x89PNG\r\n\x1a\n")
            self.assertLessEqual(offset + length, len(data))
        self.assertEqual(sizes, [(32, 32), (64, 64), (128, 128), (256, 256)])


if __name__ == "__main__":
    unittest.main()
