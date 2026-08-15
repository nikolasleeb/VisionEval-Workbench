import tempfile
import unittest
from pathlib import Path

from backend.workbench.transit_inputs import normalize_virginia_transit_inputs, validate_transit_inputs


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


class TransitInputTests(unittest.TestCase):
    def test_normalization_preserves_complete_rows_and_derives_missing_rail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write(root / "marea_transit_service.csv", "Geo,Year,DRRevMi,VPRevMi,MBRevMi,RBRevMi,MGRevMi,SRRevMi,HRRevMi,CRRevMi\nA,2045,1,0,1,0,20,0,30,50\nB,2045,0,0,0,0,0,0,0,0\n")
            write(root / "marea_transit_fuel.csv", "Geo,Year,VanPropDiesel,VanPropGasoline,VanPropCng,BusPropDiesel,BusPropGasoline,BusPropCng,RailPropDiesel,RailPropGasoline\nA,2045,0,1,0,1,0,0,NA,NA\nB,2045,NA,NA,NA,NA,NA,NA,NA,NA\n")
            write(root / "marea_transit_powertrain_prop.csv", "Geo,Year,VanPropIcev,VanPropHev,VanPropBev,BusPropIcev,BusPropHev,BusPropBev,RailPropIcev,RailPropHev,RailPropEv\nA,2045,1,0,0,1,0,0,NA,NA,NA\nB,2045,1,0,0,1,0,0,NA,NA,NA\n")

            result = normalize_virginia_transit_inputs(root)

            self.assertTrue(result["applied"])
            fuel = (root / "marea_transit_fuel.csv").read_text(encoding="utf-8")
            powertrain = (root / "marea_transit_powertrain_prop.csv").read_text(encoding="utf-8")
            self.assertIn("A,2045,0,1,0,1,0,0,1,0", fuel)
            self.assertIn("B,2045,0,1,0,1,0,0,1,0", fuel)
            self.assertIn("A,2045,1,0,0,1,0,0,0.5,0,0.5", powertrain)
            self.assertIn("B,2045,1,0,0,1,0,0,1,0,0", powertrain)
            self.assertEqual(validate_transit_inputs(root), [])

    def test_nonzero_van_service_without_technology_data_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write(root / "marea_transit_service.csv", "Geo,Year,DRRevMi,VPRevMi,MBRevMi,RBRevMi,MGRevMi,SRRevMi,HRRevMi,CRRevMi\nA,2045,1,0,0,0,0,0,0,0\n")
            write(root / "marea_transit_fuel.csv", "Geo,Year,VanPropDiesel,VanPropGasoline,VanPropCng\nA,2045,NA,NA,NA\n")
            with self.assertRaisesRegex(ValueError, "nonzero Van service"):
                normalize_virginia_transit_inputs(root)

    def test_validator_reports_mixed_global_and_bad_sum(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write(root / "marea_transit_fuel.csv", "Geo,Year,RailPropDiesel,RailPropGasoline\nA,2045,0.8,0.1\nB,2045,NA,NA\n")
            errors = validate_transit_inputs(root, scenario="Scenario 1")
            self.assertEqual({error["code"] for error in errors}, {"transit-mode-mixed-global", "transit-proportion-sum"})
            self.assertTrue(all(error["scenario"] == "Scenario 1" for error in errors))

    def test_all_na_mode_is_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write(root / "marea_transit_fuel.csv", "Geo,Year,RailPropDiesel,RailPropGasoline\nA,2045,NA,NA\nB,2045,NA,NA\n")
            self.assertEqual(validate_transit_inputs(root), [])


if __name__ == "__main__":
    unittest.main()
