import json
import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "packaging" / "build_va_region_package.py"
SPEC = importlib.util.spec_from_file_location("build_va_region_package", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
validate_input_library_coverage = MODULE.validate_input_library_coverage


class VirginiaRegionPackageTests(unittest.TestCase):
    def test_statewide_coverage_rejects_partial_input_library(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            library = root / "library"
            library.mkdir()
            (library / "bzone_lat_lon.csv").write_text(
                "Geo,Year,Latitude,Longitude\n510010001001,2024,1,2\n",
                encoding="utf-8",
            )
            crosswalk = root / "crosswalk.json"
            crosswalk.write_text(json.dumps({"regions": {
                "one": {"bzones": ["510010001001", "510030001001"]},
            }}), encoding="utf-8")
            with self.assertRaisesRegex(SystemExit, "not statewide: 1 of 2"):
                validate_input_library_coverage(library, crosswalk)

    def test_statewide_coverage_accepts_all_crosswalk_bzones(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            library = root / "library"
            library.mkdir()
            (library / "bzone_lat_lon.csv").write_text(
                "Geo,Year,Latitude,Longitude\n510010001001,2024,1,2\n510030001001,2024,3,4\n",
                encoding="utf-8",
            )
            crosswalk = root / "crosswalk.json"
            crosswalk.write_text(json.dumps({"regions": {
                "one": {"bzones": ["510010001001"]},
                "two": {"bzones": ["510030001001"]},
            }}), encoding="utf-8")
            self.assertEqual(
                validate_input_library_coverage(library, crosswalk),
                {"availableBzones": 2, "crosswalkBzones": 2},
            )


if __name__ == "__main__":
    unittest.main()
