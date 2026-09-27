import csv
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.workbench.comparison import ComparisonService
from backend.workbench.runtime import find_rscript_executable, find_native_home, native_process_path, RuntimeManager
from backend.workbench.workspace import Workspace, WorkspaceError, make_id, write_json


class WindowsCsvComparisonTests(unittest.TestCase):
    def test_high_cardinality_categories_are_bounded_but_tail_changes_are_detected(self):
        rscript, home = find_rscript_executable(), find_native_home()
        if not rscript or not home:
            self.skipTest("Native R/VisionEval unavailable")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            records = []
            for label in ("base", "case"):
                path = root / f"{label}.csv"
                rows = [f"{i},group{i:05}" for i in range(1000)]
                if label == "case":
                    rows[-1] = "999,group99999"
                path.write_text("HhId,Category\n" + "\n".join(rows))
                records.append({"path": label, "label": label, "county": {}, "csvTables": {"2045/Household": [str(path)]}})
            write_json(root / "request.json", {"records": records, "year": "2045", "filterField": "", "filterValues": [],
                                              "variables": [{"table": "Household", "name": "Category"}]})
            helper = Path(__file__).resolve().parents[1] / "backend/comparison_scan.R"
            process = subprocess.run([str(rscript), str(helper), str(root / "request.json"), str(root / "output.json"), str(root / "progress.json")],
                                     capture_output=True, text=True, env={**os.environ, "VE_HOME": str(home), "VISIONEVAL_RUNTIME_ADAPTER": "native"})
            self.assertEqual(process.returncode, 0, process.stderr)
            output = json.loads((root / "output.json").read_text())
            summary = output["summaries"][0]["reference"]
            self.assertEqual(len(summary["categories"]), 50)
            self.assertEqual(summary["distinctCategories"], 1000)
            self.assertTrue(summary["categoriesTruncated"])
            self.assertNotIn("distribution", summary)
            self.assertEqual(output["changedVariables"], 1)
            self.assertLess((root / "output.json").stat().st_size, 60000)
            self.assertEqual(json.loads((root / "progress.json").read_text())["phase"], "finalizing")
    def test_native_process_path_normalizes_drive_and_unc_without_shortening_labels(self):
        self.assertEqual(native_process_path(r"\\?\C:\R folder\Rscript.exe"), r"C:\R folder\Rscript.exe")
        self.assertEqual(native_process_path(r"\\?\UNC\server\share\Rscript.exe"), r"\\server\share\Rscript.exe")
        self.assertEqual(native_process_path(r"C:\R folder\Rscript.exe"), r"C:\R folder\Rscript.exe")

    @unittest.skipUnless(os.name == "nt", "Windows Rscript launcher regression")
    def test_configured_prefixed_rscript_launches_successfully(self):
        executable = find_rscript_executable()
        if not executable:
            self.skipTest("Rscript unavailable")
        discovered = find_rscript_executable("\\\\?\\" + executable)
        self.assertFalse(discovered.startswith("\\\\?\\"))
        result = subprocess.run([discovered, "--version"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Rscript", result.stdout + result.stderr)

    def test_windows_generated_ids_are_compact_and_unique(self):
        with patch("backend.workbench.workspace.os.name", "nt"):
            first, second = make_id("project", "A very long display name" * 20), make_id("project", "A very long display name" * 20)
        self.assertEqual(len(first), len("project-") + 10)
        self.assertNotEqual(first, second)

    @unittest.skipUnless(os.name == "nt", "Windows path contract")
    def test_windows_long_json_path_is_rejected_before_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / ("a" * 160) / ("b" * 80) / "job.json"
            with self.assertRaisesRegex(WorkspaceError, "240-character"):
                write_json(target, {})
            self.assertFalse(target.parent.exists())

    def test_standard_csv_inventory_and_hypercube_separation(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(directory)
            service = ComparisonService(workspace, None, Path(directory)/"reader.R")
            root = workspace.models/"run-short"/"results"/"Datastore"
            output = root.parent/"output"/"r_CSV_"
            output.mkdir(parents=True)
            (output/"Azone_run-short_2045.csv").write_text("Azone,Value\n001,12\n", encoding="utf-8")
            (output/"Metadata.csv").write_text("Group,Table,Name,Scenario,DBTable,Units\n2045,Azone,Value,run-short,Azone_run-short_2045.csv,PRSN\n", encoding="utf-8")
            record = {"projectId":"p", "path":str(root)}
            with patch.object(workspace, "project", return_value=(workspace.projects, {"projectType":"standard"})):
                inventory = service._csv_inventory(record)
                self.assertEqual(inventory["metadata"]["Azone/Value"]["units"], "PRSN")
                self.assertEqual(len(inventory["csvTables"]["2045/Azone"]), 1)
                (output/"Metadata.csv").unlink()
                with self.assertRaisesRegex(WorkspaceError, "completed CSV"):
                    service._csv_inventory(record)
            with patch.object(workspace, "project", return_value=(workspace.projects, {"projectType":"hypercube"})):
                self.assertIsNone(service._csv_inventory(record))

    def test_native_batch_csv_scanner_keeps_synthetic_identity_aggregate(self):
        rscript = find_rscript_executable()
        home = find_native_home()
        if not rscript or not home:
            self.skipTest("Native R/VisionEval unavailable")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            records = []
            for name, rows in (("base", "1,10,A\n2,20,B\n"), ("case", "7,12,B\n8,22,A\n")):
                path = root/f"{name}.csv"
                path.write_text("HhId,Income,Category\n"+rows, encoding="utf-8")
                records.append({"path":name, "label":name, "csvTables":{"2045/Household":[str(path)]}, "county":{}})
            request = {"records":records,"year":"2045","filterField":"","filterValues":[],"variables":[
                {"table":"Household","name":name,"units":"","description":""} for name in ("Income","Category")]}
            request_path = root/"request.json"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            helper = Path(__file__).resolve().parents[1]/"backend"/"comparison_scan.R"
            environment = {**os.environ,"VE_HOME":str(home),"VISIONEVAL_RUNTIME_ADAPTER":"native"}
            result = subprocess.run([str(rscript),str(helper),str(request_path),str(root/"output.json"),str(root/"progress.json")], capture_output=True, text=True, env=environment)
            self.assertEqual(result.returncode, 0, result.stderr)
            output = json.loads((root/"output.json").read_text())
            # Category distribution is unchanged despite different IDs/row order.
            self.assertEqual([item["variable"] for item in output["results"]], ["Income"])
            self.assertEqual(output["results"][0]["pairStats"][0]["netChange"], 4)
            self.assertEqual(output["summaryVersion"], 1)
            self.assertEqual(len(output["summaries"]), 2)
            self.assertEqual(output["summaries"][0]["reference"]["sum"], 30)
            self.assertEqual(output["summaries"][1]["changedRows"], 0)

    def test_csv_reader_joins_column_partitions_without_duplicate_ids(self):
        rscript, home = find_rscript_executable(), find_native_home()
        if not rscript or not home:
            self.skipTest("Native R/VisionEval unavailable")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first, second = root / "first.csv", root / "second.csv"
            first.write_text("Scenario,Year,Marea,Value\nbase,2045,001,12\nbase,2045,002,24\n", encoding="utf-8")
            second.write_text("Scenario,Year,Marea,Other\nbase,2045,002,8\nbase,2045,001,9\n", encoding="utf-8")
            helper = Path(__file__).resolve().parents[1] / "backend" / "rda_reader.R"
            for variable in ("Marea", "Value", "Other"):
                result = subprocess.run([str(rscript), str(helper), "--csv", variable, str(first), str(second)], capture_output=True, text=True, env={**os.environ, "VE_HOME": str(home)})
                self.assertEqual(result.returncode, 0, result.stderr)
                values = json.loads(result.stdout)["values"]
                self.assertEqual(len(values), 2)
                if variable == "Marea":
                    self.assertEqual(set(values), {"001", "002"})

    def test_batch_summaries_preserve_split_tables_missing_values_and_zero_change(self):
        rscript, home = find_rscript_executable(), find_native_home()
        if not rscript or not home:
            self.skipTest("Native R/VisionEval unavailable")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            records = []
            for label, values in (("base", "001,-10,7,0\n002,,3,0\n"), ("case", "001,-8,7,4\n002,,3,0\n")):
                first, second = root / f"{label}-1.csv", root / f"{label}-2.csv"
                first.write_text("Azone,Negative,Same,Zero\n" + values)
                second.write_text("Azone,Category\n002,B\n001,A\n")
                records.append({"path": label, "label": label, "county": {}, "csvTables": {"2045/Azone": [str(first), str(second)]}})
            request = {"records": records, "year": "2045", "filterField": "", "filterValues": [],
                       "variables": [{"table": "Azone", "name": name} for name in ("Negative", "Same", "Zero", "Category")]}
            write_json(root / "request.json", request)
            helper = Path(__file__).resolve().parents[1] / "backend/comparison_scan.R"
            process = subprocess.run([str(rscript), str(helper), str(root / "request.json"), str(root / "output.json"), str(root / "progress.json")],
                                     capture_output=True, text=True, env={**os.environ, "VE_HOME": str(home), "VISIONEVAL_RUNTIME_ADAPTER": "native"})
            self.assertEqual(process.returncode, 0, process.stderr)
            result = json.loads((root / "output.json").read_text())
            summaries = {item["variable"]: item for item in result["summaries"]}
            self.assertEqual(summaries["Negative"]["reference"]["sum"], -10)
            self.assertEqual(summaries["Negative"]["reference"]["missingCount"], 1)
            self.assertEqual(summaries["Same"]["changedRows"], 0)
            self.assertEqual(summaries["Zero"]["reference"]["sum"], 0)
            self.assertEqual(summaries["Category"]["changedRows"], 0)
            self.assertEqual({item["totalRows"] for item in summaries.values()}, {2})


if __name__ == "__main__":
    unittest.main()
