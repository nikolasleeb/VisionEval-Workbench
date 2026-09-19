import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.workbench.update_checks import (
    UPDATE_MANIFEST_NAME,
    UpdateCheckService,
    version_is_newer,
)
from backend.workbench.workspace import Workspace, read_json


class UpdateCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Workspace(Path(self.temp.name) / "workspace")
        self.release_url = "https://github.com/nikolasleeb/VisionEval-Workbench/releases/tag/v1.1.0"
        self.manifest_url = "https://github.com/nikolasleeb/VisionEval-Workbench/releases/download/v1.1.0/update-manifest.json"
        self.download_url = "https://github.com/nikolasleeb/VisionEval-Workbench/releases/download/v1.1.0/VisionEval-Workbench-v1.1.0-macos-arm64.dmg"

    def tearDown(self):
        self.temp.cleanup()

    def responses(self):
        releases = [{
            "tag_name": "v1.1.0", "draft": False, "prerelease": False,
            "html_url": self.release_url,
            "assets": [
                {"name": "VisionEval-Workbench-v1.1.0-macos-arm64.dmg", "browser_download_url": self.download_url},
                {"name": UPDATE_MANIFEST_NAME, "browser_download_url": self.manifest_url},
            ],
        }]
        manifest = {
            "schemaVersion": 1,
            "workbench": {"version": "1.1.0", "releaseUrl": self.release_url},
            "visionEval": {"version": "VE-40-RC7"},
            "runtimeImages": [{
                "platform": "macos", "architecture": "arm64",
                "reference": "ghcr.io/nikolasleeb/visioneval-workbench-runtime@sha256:" + "2" * 64,
                "digest": "sha256:" + "2" * 64,
                "minimumWorkbenchVersion": "1.0.0",
            }],
        }
        vision = [{"tag_name": "VE-40-RC7", "draft": False, "prerelease": False, "html_url": "https://github.com/VisionEval/VisionEval-4/releases/tag/VE-40-RC7"}]
        return releases, manifest, vision

    def service(self, http_get):
        with patch("backend.workbench.update_checks._platform_name", return_value="macos"), patch("backend.workbench.update_checks._architecture", return_value="arm64"):
            return UpdateCheckService(self.workspace, "1.0.0", "VE-40-RC6", lambda: "sha256:" + "1" * 64, "docker", http_get=http_get)

    def test_semantic_versions_handle_stable_and_prerelease(self):
        self.assertTrue(version_is_newer("1.1.0", "1.0.9"))
        self.assertTrue(version_is_newer("1.0.0", "1.0.0-rc1"))
        self.assertFalse(version_is_newer("1.0.0-rc1", "1.0.0"))

    def test_manual_check_reports_app_and_upstream_advisories_with_installable_runtime(self):
        releases, manifest, vision = self.responses()
        def fetch(url):
            if "VisionEval-4" in url:
                return vision
            if url == self.manifest_url:
                return manifest
            return releases
        result = self.service(fetch).check(force=True)
        self.assertEqual(result["statuses"]["workbench"]["status"], "update_available")
        self.assertEqual(result["statuses"]["runtimeImage"]["status"], "update_available")
        self.assertEqual(result["statuses"]["visioneval"]["status"], "update_available")
        self.assertFalse(result["statuses"]["runtimeImage"]["advisoryOnly"])
        stored = read_json(self.workspace.settings_path, {})
        self.assertIn("updateChecks", stored)
        self.assertNotIn("checkVisionEvalUpdates", stored)

    def test_unselected_source_is_not_requested(self):
        self.workspace.update_settings({"updateChecks": {"automatic": False, "sources": {"visioneval": False, "runtimeImage": False, "workbench": True}}})
        releases, _, _ = self.responses()
        result = self.service(lambda _url: releases).check(force=True, sources=["workbench"])
        self.assertEqual(result["statuses"]["visioneval"]["status"], "not_selected")
        self.assertEqual(result["statuses"]["runtimeImage"]["status"], "not_selected")

    def test_remote_failure_is_nonfatal_and_cached(self):
        def fail(_url):
            raise OSError("offline")
        result = self.service(fail).check(force=True)
        self.assertEqual(result["statuses"]["workbench"]["status"], "unavailable")
        self.assertEqual(result["statuses"]["runtimeImage"]["status"], "unavailable")
        self.assertEqual(result["statuses"]["visioneval"]["status"], "unavailable")

    def test_legacy_setting_is_read_but_not_rewritten(self):
        path = self.workspace.settings_path
        path.write_text(json.dumps({"version": 1, "checkVisionEvalUpdates": True}), encoding="utf-8")
        self.assertTrue(self.workspace.settings()["updateChecks"]["automatic"])
        self.workspace.update_settings({"updateChecks": {"automatic": False}})
        stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertNotIn("checkVisionEvalUpdates", stored)


if __name__ == "__main__":
    unittest.main()
