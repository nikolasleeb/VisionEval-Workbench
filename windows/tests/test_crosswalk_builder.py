import importlib.util
import unittest
from pathlib import Path

try:
    from shapely.geometry import box, mapping
except ModuleNotFoundError:  # Optional maintenance dependency.
    box = mapping = None

SCRIPT = Path(__file__).resolve().parents[1] / "packaging" / "build_va_mpo_crosswalk.py"
if box is not None:
    SPEC = importlib.util.spec_from_file_location("build_va_mpo_crosswalk", SCRIPT)
    MODULE = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(MODULE)
    assign_positive_area_overlaps = MODULE.assign_positive_area_overlaps
    projected = MODULE.projected


@unittest.skipIf(box is None, "Shapely maintenance dependency is not installed")
class CrosswalkBuilderTests(unittest.TestCase):
    def test_one_percent_overlap_assigns_bzone_to_every_mpo_but_slivers_and_touch_do_not(self):
        mpo_rows = [
            ("LEFT", "left-mpo", "Left MPO", projected(box(0, 0, 1, 1))),
            ("RIGHT", "right-mpo", "Right MPO", projected(box(1, 0, 2, 1))),
        ]
        features = [
            {"properties": {"GEOID": "510010000001"}, "geometry": mapping(box(0.5, 0.2, 1.5, 0.8))},
            {"properties": {"GEOID": "510010000002"}, "geometry": mapping(box(1.999999, 0.2, 2.5, 0.8))},
            {"properties": {"GEOID": "510010000003"}, "geometry": mapping(box(2, 0.2, 2.5, 0.8))},
        ]
        output, unmatched = assign_positive_area_overlaps(mpo_rows, features, {"51001": "Example"})
        self.assertEqual(unmatched, set())
        self.assertIn("510010000001", output["left-mpo"]["bzones"])
        self.assertIn("510010000001", output["right-mpo"]["bzones"])
        self.assertNotIn("510010000002", output["right-mpo"]["bzones"])
        self.assertNotIn("510010000003", output["right-mpo"]["bzones"])

    def test_exactly_one_percent_is_inclusive_and_below_99_percent_is_boundary(self):
        mpo_rows = [("MPO", "example-mpo", "Example MPO", projected(box(0, 0, 0.01, 1)))]
        features = [
            {"properties": {"GEOID": "510010000004"}, "geometry": mapping(box(0, 0, 1, 1))},
        ]
        output, _ = assign_positive_area_overlaps(mpo_rows, features, {"51001": "Example"})
        self.assertEqual(output["example-mpo"]["bzones"], ["510010000004"])
        self.assertEqual(output["example-mpo"]["boundaryBzones"], [
            {"geoid": "510010000004", "overlapRatio": 0.01},
        ])


if __name__ == "__main__":
    unittest.main()
