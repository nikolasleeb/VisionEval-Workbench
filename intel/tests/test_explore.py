import csv
import json
import tempfile
import unittest
from pathlib import Path

from backend.workbench.explore import ExploreService
from backend.workbench.workspace import Workspace, WorkspaceError


class ExploreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Workspace(self.temp.name)
        library = self.workspace.input_library / "Example"
        library.mkdir()
        with (library / "azone_people.csv").open("w", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerows([["Geo", "Year", "Population"], ["A", "2045", "10"]])
        catalog = Path(self.temp.name) / "catalog.json"
        catalog.write_text(json.dumps({
            "variables": {"population": [{"table": "Azone", "display": "Population", "type": "double", "units": "persons", "description": "Number of residents"}]},
            "explanations": {"azone_people": {"document": "people.docx", "html": "<p>File 01_azone_people.csv</p>\n<p>May 21, 2026</p>\n<h3>Definition of the Input File</h3>\n<p>Long guide</p>"}},
            "inputFields": {"azone_people.csv": {"population": {"field": "Population", "type": "people", "units": "PRSN", "description": "Household population", "module": "VESimHouseholds::CreateHouseholds"}}},
        }))
        self.service = ExploreService(self.workspace, catalog)

    def tearDown(self):
        self.temp.cleanup()

    def test_lists_files_with_stable_internal_ids(self):
        result = self.service.files("Example")
        self.assertEqual(result["files"][0]["id"], "input:azone_people.csv")
        self.assertEqual(result["files"][0]["level"], "Azone")
        self.assertTrue(result["files"][0]["hasExplanation"])
        self.assertTrue(result["files"][0]["installed"])
        self.assertTrue(result["files"][0]["columnsAvailable"])

    def test_catalog_files_exist_without_an_installed_library(self):
        result = self.service.files("")
        entry = next(item for item in result["files"] if item["filename"] == "azone_people.csv")
        self.assertEqual(entry["source"], "catalog")
        self.assertFalse(entry["installed"])
        self.assertFalse(entry["columnsAvailable"])
        self.assertEqual(entry["columns"], [])
        detail = self.service.file("", "azone_people.csv")
        self.assertEqual(detail["fields"], [])
        self.assertIn("Long guide", detail["explanationHtml"])

    def test_returns_fields_explanation_and_mapping_anchor(self):
        result = self.service.file("Example", "azone_people.csv")
        population = next(field for field in result["fields"] if field["name"] == "Population")
        self.assertEqual(population["description"], "Household population")
        self.assertEqual(population["units"], "PRSN")
        self.assertEqual(population["source"], "VESimHouseholds::CreateHouseholds")
        self.assertEqual(result["explanationHtml"], "<h3>Definition of the Input File</h3>\n<p>Long guide</p>")
        self.assertEqual(result["mapping"]["inputId"], "input:azone_people.csv")

    def test_missing_field_metadata_uses_quiet_fallbacks(self):
        result = self.service.file("Example", "azone_people.csv")
        geo = next(field for field in result["fields"] if field["name"] == "Geo")
        self.assertEqual(geo["description"], "Description not available in the packaged guide.")
        self.assertFalse(geo["descriptionAvailable"])
        self.assertEqual(geo["source"], "Identifier")
        self.assertTrue(geo["sourceAvailable"])

    def test_rejects_path_traversal(self):
        with self.assertRaises(WorkspaceError):
            self.service.file("Example", "../secret.csv")

    def test_integer_input_metadata_blocks_decimal_storage(self):
        types = self.service.input_column_types("azone_people.csv", ["Geo", "Year", "Population"])
        self.assertEqual(types["Population"], "integer")
        self.service.validate_input_rows("azone_people.csv", ["Geo", "Year", "Population"], [["A", "2045", "11"]])
        with self.assertRaisesRegex(WorkspaceError, "whole numbers in Population"):
            self.service.validate_input_rows("azone_people.csv", ["Geo", "Year", "Population"], [["A", "2045", "11.5"]])

    def test_identifiers_are_unitless_and_unresolved_units_are_warned(self):
        conflicts = Path(self.temp.name) / "conflicts.json"
        conflicts.write_text(json.dumps({"conflicts": [{
            "scope": "input", "file": "azone_people.csv", "field": "Population",
            "reason": "Needs unit review", "status": "unresolved"
        }]}))
        service = ExploreService(self.workspace, Path(self.temp.name) / "catalog.json", conflicts)
        result = service.file("Example", "azone_people.csv")
        geo = next(field for field in result["fields"] if field["name"] == "Geo")
        population = next(field for field in result["fields"] if field["name"] == "Population")
        self.assertTrue(geo["identifier"])
        self.assertEqual(geo["units"], "")
        self.assertEqual(population["unitStatus"], "unresolved")
        self.assertIn("Needs unit review", population["unitWarning"])

    def test_reviewable_unit_conflict_formats_match_packaged_metadata(self):
        root = Path(__file__).parents[1]
        review = json.loads((root / "docs" / "unit-conflicts.json").read_text())
        packaged = json.loads((root / "backend" / "unit_conflicts.json").read_text())
        markdown = (root / "docs" / "unit-conflicts.md").read_text()
        self.assertEqual(review["conflicts"], packaged["conflicts"])
        self.assertTrue(review["conflicts"])
        for conflict in review["conflicts"]:
            self.assertIn(conflict["id"].split("-")[0].lower(), markdown.lower())
            self.assertIn("reviewerNotes", conflict)


if __name__ == "__main__":
    unittest.main()
