import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.workbench.comparison_cache import ComparisonCache
from backend.workbench.workspace import Workspace, WorkspaceError


class ComparisonCacheTests(unittest.TestCase):
    def test_cache_imports_keys_once_and_reuses_fingerprinted_variable(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory) / "workspace")
            datastore = workspace.models / "fixture" / "results" / "Datastore"
            table = datastore / "2045" / "Azone"; table.mkdir(parents=True)
            (datastore / "DatastoreListing.Rda").touch(); (table / "Azone.Rda").write_bytes(b"keys"); (table / "Value.Rda").write_bytes(b"values")
            extractor = Path(directory) / "extractor.R"; extractor.touch()
            cache = ComparisonCache(workspace, "unused", extractor)
            calls = []

            def command(root, year, table_name, key, output, variables):
                calls.append((key, list(variables)))
                output.mkdir(parents=True, exist_ok=True)
                with (output / "keys.tsv").open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.writer(handle, delimiter="\t", quoting=csv.QUOTE_ALL); writer.writerow(["row_index", "entity_key"]); writer.writerows([[0, "a"], [1, "b"]])
                for index, _ in enumerate(variables, 1):
                    with (output / f"column_{index}.tsv").open("w", newline="", encoding="utf-8") as handle:
                        writer = csv.writer(handle, delimiter="\t", quoting=csv.QUOTE_ALL); writer.writerow(["row_index", "is_null", "numeric_value", "text_value", "compare_value"]); writer.writerows([[0, 0, 1.25, "", 1.25], [1, 0, 2.5, "", 2.5]])
                    (output / f"column_{index}.kind").write_text("numeric")
                return [sys.executable, "-c", "pass"]

            with patch.object(cache, "_extract_command", side_effect=command):
                first = cache.column(datastore, "2045", "Azone", "Value")
                second = cache.column(datastore, "2045", "Azone", "Value")

            self.assertEqual(first["order"], ["a", "b"])
            self.assertEqual(first["list"], [1.25, 2.5])
            self.assertEqual(second["metrics"]["cacheHit"], True)
            self.assertEqual(calls, [("Azone", ["Value"])])
            self.assertEqual(cache.report()["entries"], 1)

    def test_cache_skips_non_aligned_variable_and_keeps_valid_columns(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory) / "workspace")
            datastore = workspace.models / "fixture" / "results" / "Datastore"
            table = datastore / "2045" / "Marea"; table.mkdir(parents=True)
            (datastore / "DatastoreListing.Rda").touch()
            (table / "Marea.Rda").write_bytes(b"keys")
            (table / "Value.Rda").write_bytes(b"values")
            (table / "OthSpd.Rda").write_bytes(b"scalar")
            extractor = Path(directory) / "extractor.R"; extractor.touch()
            cache = ComparisonCache(workspace, "unused", extractor)

            def command(root, year, table_name, key, output, variables):
                output.mkdir(parents=True, exist_ok=True)
                with (output / "keys.tsv").open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.writer(handle, delimiter="\t", quoting=csv.QUOTE_ALL)
                    writer.writerow(["row_index", "entity_key"]); writer.writerows([[0, "urban"], [1, "non-urban"]])
                skipped = []
                for index, variable in enumerate(variables, 1):
                    if variable == "OthSpd":
                        skipped.append([variable, "Marea/OthSpd cannot be aligned safely: 1 values for 2 Marea keys"])
                        continue
                    with (output / f"column_{index}.tsv").open("w", newline="", encoding="utf-8") as handle:
                        writer = csv.writer(handle, delimiter="\t", quoting=csv.QUOTE_ALL)
                        writer.writerow(["row_index", "is_null", "numeric_value", "text_value", "compare_value"])
                        writer.writerows([[0, 0, 1, "", 1], [1, 0, 2, "", 2]])
                    (output / f"column_{index}.kind").write_text("numeric")
                with (output / "skipped.tsv").open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.writer(handle, delimiter="\t", quoting=csv.QUOTE_ALL)
                    writer.writerow(["variable", "reason"]); writer.writerows(skipped)
                return [sys.executable, "-c", "pass"]

            with patch.object(cache, "_extract_command", side_effect=command):
                prepared = cache.ensure(datastore, "2045", "Marea", ["Value", "OthSpd"])
                valid = cache.column(datastore, "2045", "Marea", "Value")
                with self.assertRaisesRegex(WorkspaceError, "cannot be aligned safely"):
                    cache.column(datastore, "2045", "Marea", "OthSpd")

            self.assertIn("OthSpd", prepared["skipped"])
            self.assertEqual(valid["list"], [1.0, 2.0])

    def test_clear_removes_disposable_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = ComparisonCache(Workspace(Path(directory) / "workspace"), "unused", Path(directory) / "extractor.R")
            (cache.root / "fixture.sqlite").touch(); (cache.root / "fixture.manifest.json").touch()
            result = cache.clear()
            self.assertTrue(result["cleared"])
            self.assertEqual(result["entries"], 0)

    def test_remove_datastore_only_removes_matching_manifest_files(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = ComparisonCache(Workspace(Path(directory) / "workspace"), "unused", Path(directory) / "extractor.R")
            for name, datastore_id in (("matching", "imported-one"), ("other", "imported-two")):
                database = cache.root / f"{name}.sqlite"; database.write_bytes(b"sqlite")
                (cache.root / f"{name}.sqlite-wal").write_bytes(b"wal")
                (cache.root / f"{name}.manifest.json").write_text(json.dumps({"database":database.name,"metadata":{"datastore_id":datastore_id}}), encoding="utf-8")
            result = cache.remove_datastore("imported-one")
            self.assertEqual(result["cacheFilesRemoved"], 3)
            self.assertFalse((cache.root / "matching.sqlite").exists())
            self.assertTrue((cache.root / "other.sqlite").exists())


if __name__ == "__main__":
    unittest.main()
