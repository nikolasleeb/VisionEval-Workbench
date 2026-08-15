from __future__ import annotations

import json
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path

from backend.workbench.region_packages import RegionPackageService, package_manifest_type, package_root
from backend.workbench.workspace import WorkspaceError


class PackageSourceTests(unittest.TestCase):
    def test_folder_accepts_root_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "workbench-package.json").write_text(json.dumps({"type": "region-builder"}), encoding="utf-8")
            self.assertEqual(package_root(root), root.resolve())
            self.assertEqual(package_manifest_type(root), "region-builder")

    def test_folder_accepts_one_wrapper_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wrapper = root / "downloaded-package"
            wrapper.mkdir()
            (wrapper / "workbench-package.json").write_text(json.dumps({"type": "model-bundle"}), encoding="utf-8")
            self.assertEqual(package_root(root), wrapper.resolve())

    def test_folder_rejects_ambiguous_and_deep_manifests(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("one", "two"):
                child = root / name
                child.mkdir()
                (child / "workbench-package.json").write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(WorkspaceError, "multiple"):
                package_root(root)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            deep = root / "one" / "two"
            deep.mkdir(parents=True)
            (deep / "workbench-package.json").write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(WorkspaceError, "root or in one wrapper"):
                package_root(root)

    def test_zip_rejects_deep_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "package.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("one/two/workbench-package.json", json.dumps({"type": "region-builder"}))
            with self.assertRaisesRegex(WorkspaceError, "zip root or in one wrapper"):
                package_manifest_type(archive_path)

    def test_zip_rejects_unsafe_paths_and_symbolic_links(self):
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "traversal.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("../workbench-package.json", "{}")
            with self.assertRaisesRegex(WorkspaceError, "unsafe file path"):
                package_manifest_type(archive_path)
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "link.zip"
            link = zipfile.ZipInfo("wrapper/link")
            link.create_system = 3
            link.external_attr = (stat.S_IFLNK | 0o777) << 16
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("wrapper/workbench-package.json", "{}")
                archive.writestr(link, "target")
            with self.assertRaisesRegex(WorkspaceError, "symbolic link"):
                package_manifest_type(archive_path)

    def test_package_source_accepts_extracted_wrapper(self):
        with tempfile.TemporaryDirectory() as directory:
            wrapper = Path(directory) / "wrapper"
            wrapper.mkdir()
            (wrapper / "workbench-package.json").write_text("{}", encoding="utf-8")
            selected, temporary = RegionPackageService._package_source(directory)
            self.assertEqual(selected, wrapper.resolve())
            self.assertIsNone(temporary)


if __name__ == "__main__":
    unittest.main()
