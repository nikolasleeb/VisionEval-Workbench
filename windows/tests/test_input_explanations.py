import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from backend.workbench.embedded_explanations import install_embedded_explanations
from backend.workbench.input_explanations import InputExplanationPackageService
from backend.workbench.workspace import Workspace


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class VirginiaExplanationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.workspace = Workspace(self.root / "workspace")
        self.service = InputExplanationPackageService(self.workspace)

    def tearDown(self):
        self.temp.cleanup()

    def embedded(self, html: str = "<p>Guide</p>") -> tuple[Path, dict]:
        root = self.root / "mpo"
        catalog = {"version": 1, "variables": {}, "inputFields": {}, "coveredFiles": ["households.csv"], "explanations": {"households": {"html": html}}}
        write_json(root / "catalog.json", catalog)
        manifest = {
            "id": "planrva-package", "name": "PlanRVA package", "type": "model-package",
            "inputExplanations": {"id": "va-guidance", "name": "PlanRVA explanations", "version": "1", "path": "catalog.json", "fileCount": 1, "appliesTo": {"state": "VA"}},
        }
        return root, manifest

    def standalone(self, name: str = "Virginia statewide explanations", html: str = "<p>Guide</p>") -> Path:
        root = self.root / name.replace(" ", "-")
        payload = {"explanations": {"households": {"html": html}}}
        raw = json.dumps(payload).encode()
        (root / "guidance.json").parent.mkdir(parents=True, exist_ok=True)
        (root / "guidance.json").write_bytes(raw)
        write_json(root / "workbench-package.json", {
            "id": "va-guidance", "name": name, "type": "input-explanations", "version": "1",
            "appliesTo": {"state": "VA"},
            "files": [{"path": "guidance.json", "size": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}],
        })
        return root

    def test_statewide_provider_consolidates_and_uninstall_restores_mpo(self):
        root, manifest = self.embedded()
        install_embedded_explanations(self.workspace, root, manifest, root)
        self.service.install(self.standalone())
        visible = self.service.list()
        self.assertEqual(len(visible), 1)
        self.assertEqual(visible[0]["name"], "Virginia statewide explanations")
        self.assertEqual(visible[0]["preferredProvider"]["packageId"], "va-guidance")
        self.assertEqual(visible[0]["providerCount"], 2)

        self.service.remove(visible[0]["id"])
        fallback = self.service.list()
        self.assertEqual(len(fallback), 1)
        self.assertEqual(fallback[0]["preferredProvider"]["packageId"], "planrva-package")

    def test_different_catalogs_in_same_family_remain_visible_with_warning(self):
        root, manifest = self.embedded()
        install_embedded_explanations(self.workspace, root, manifest, root)
        self.service.install(self.standalone("Virginia alternate", "<p>Different</p>"))
        visible = self.service.list()
        self.assertEqual(len(visible), 2)
        self.assertTrue(all(item["familyConflict"] for item in visible))


if __name__ == "__main__":
    unittest.main()
