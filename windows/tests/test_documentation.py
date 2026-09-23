import hashlib
import json
import re
import tempfile
import unittest
from pathlib import Path
from urllib.parse import unquote

from backend.workbench.documentation import DocumentationService
from backend.workbench.server import WorkbenchApplication


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def source_guide(root: Path, version: str = "test-1") -> Path:
    guide = root / "docs" / "user"
    write(guide / "documentation.json", json.dumps({
        "schemaVersion": 1,
        "documentationVersion": version,
        "entrypoint": "README.md",
    }))
    write(guide / "README.md", "# User guide\n\n[Run](run.md)\n")
    write(guide / "run.md", "# Run\n")
    return guide


def source_pdf_catalog(root: Path, version: str = "test-2") -> Path:
    guide = root / "docs" / "user"
    documents = [
        {
            "id": "user-guide",
            "title": "User Guide",
            "description": "Complete reference guide.",
            "filename": "guide.pdf",
            "format": "pdf",
            "pageCount": 15,
            "version": "2.0",
        },
        {
            "id": "whats-new",
            "title": "What's New",
            "description": "One-page overview.",
            "filename": "whats-new.pdf",
            "format": "pdf",
            "pageCount": 1,
            "version": "2.0",
        },
    ]
    write(guide / "documentation.json", json.dumps({
        "schemaVersion": 2,
        "documentationVersion": version,
        "entrypoint": "guide.pdf",
        "documents": documents,
    }))
    for document in documents:
        (guide / document["filename"]).parent.mkdir(parents=True, exist_ok=True)
        (guide / document["filename"]).write_bytes(b"%PDF-1.7\n")
    return guide


class DocumentationSyncTests(unittest.TestCase):
    def test_fresh_workspace_installs_guide_manifest_and_notes_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_guide(root / "resources")
            workspace = root / "workspace"
            status = DocumentationService(workspace, root / "resources").sync()

            self.assertEqual(status["state"], "ready")
            self.assertEqual(status["documentationVersion"], "test-1")
            documentation = workspace / "Documentation"
            self.assertTrue((documentation / "README.md").is_file())
            self.assertTrue((documentation / "Workbench User Guide" / "run.md").is_file())
            self.assertTrue((documentation / "User Notes").is_dir())
            manifest = json.loads((documentation / ".workbench-documentation.json").read_text())
            self.assertEqual(manifest["schemaVersion"], 2)
            self.assertEqual(manifest["documentationVersion"], "test-1")
            for item in manifest["managedFiles"]:
                target = documentation / item["path"]
                self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), item["sha256"])

    def test_upgrade_replaces_managed_files_removes_stale_and_preserves_user_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            guide = source_guide(root / "resources")
            workspace = root / "workspace"
            service = DocumentationService(workspace, root / "resources")
            self.assertEqual(service.sync()["state"], "ready")

            documentation = workspace / "Documentation"
            write(documentation / "User Notes" / "my-notes.md", "keep me")
            write(documentation / "Workbench User Guide" / "personal.md", "also keep me")
            (guide / "run.md").unlink()
            write(guide / "README.md", "# Updated guide\n")
            metadata = json.loads((guide / "documentation.json").read_text())
            metadata["documentationVersion"] = "test-2"
            write(guide / "documentation.json", json.dumps(metadata))

            status = service.sync()
            self.assertEqual(status["documentationVersion"], "test-2")
            self.assertEqual(
                (documentation / "Workbench User Guide" / "README.md").read_text(),
                "# Updated guide\n",
            )
            self.assertFalse((documentation / "Workbench User Guide" / "run.md").exists())
            self.assertEqual((documentation / "User Notes" / "my-notes.md").read_text(), "keep me")
            self.assertEqual((documentation / "Workbench User Guide" / "personal.md").read_text(), "also keep me")

    def test_pdf_catalog_installs_only_allowlisted_pdfs_and_replaces_old_managed_pages(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            legacy = source_guide(root / "resources")
            workspace = root / "workspace"
            service = DocumentationService(workspace, root / "resources")
            self.assertEqual(service.sync()["state"], "ready")
            documentation = workspace / "Documentation"
            write(documentation / "User Notes" / "notes.md", "keep")
            write(documentation / "Workbench User Guide" / "unrecognized.txt", "keep")

            for path in legacy.iterdir():
                if path.is_file():
                    path.unlink()
            source_pdf_catalog(root / "resources")
            status = service.sync()

            self.assertEqual(status["state"], "ready")
            self.assertEqual([item["id"] for item in status["documents"]], ["user-guide", "whats-new"])
            self.assertFalse((documentation / "Workbench User Guide" / "README.md").exists())
            self.assertFalse((documentation / "Workbench User Guide" / "run.md").exists())
            self.assertTrue((documentation / "Workbench User Guide" / "guide.pdf").is_file())
            self.assertTrue((documentation / "Workbench User Guide" / "whats-new.pdf").is_file())
            self.assertEqual((documentation / "User Notes" / "notes.md").read_text(), "keep")
            self.assertEqual((documentation / "Workbench User Guide" / "unrecognized.txt").read_text(), "keep")
            self.assertIn("guide.pdf", (documentation / "README.md").read_text())

    def test_pdf_catalog_and_document_paths_are_allowlisted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_pdf_catalog(root / "resources")
            service = DocumentationService(root / "workspace", root / "resources")
            self.assertEqual(service.sync()["state"], "ready")
            self.assertEqual(len(service.catalog()["documents"]), 2)
            self.assertEqual(service.document_path("user-guide").name, "guide.pdf")
            with self.assertRaises(ValueError):
                service.document_path("../User Notes/private.pdf")
            with self.assertRaises(ValueError):
                service.document_path("missing")

    def test_missing_bundled_guide_is_a_nonblocking_warning(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            status = DocumentationService(root / "workspace", root / "resources").sync()
            self.assertEqual(status["state"], "warning")
            self.assertIn("missing", status["message"].lower())
            self.assertTrue((root / "workspace" / "Documentation" / "User Notes").is_dir())

    def test_pages_and_assets_are_confined_to_the_managed_guide(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            guide = source_guide(root / "resources")
            write(guide / "images" / "diagram.svg", "<svg xmlns='http://www.w3.org/2000/svg'/>")
            service = DocumentationService(root / "workspace", root / "resources")
            self.assertEqual(service.sync()["state"], "ready")
            self.assertEqual(service.page("run.md")["body"], "# Run\n")
            self.assertEqual(service.asset_path("images/diagram.svg").suffix, ".svg")
            with self.assertRaises(ValueError):
                service.page("../User Notes/private.md")
            with self.assertRaises(ValueError):
                service.asset_path("../private.txt")

    def test_application_state_reports_documentation_status(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            resource_root = Path(__file__).resolve().parents[1] / "backend"
            public_root = Path(__file__).resolve().parents[1] / "public"
            app = WorkbenchApplication(root / "workspace", public_root, resource_root)
            self.assertEqual(app.state()["documentation"]["state"], "ready")


class DocumentationSourceTests(unittest.TestCase):
    def test_bundled_windows_guide_uses_only_native_runtime_guidance(self):
        repository = Path(__file__).resolve().parents[1]
        pages = sorted((repository / "docs" / "user").glob("*.md"))
        combined = "\n".join(path.read_text(encoding="utf-8") for path in pages)
        self.assertIn("VE_Runtime", combined)
        for obsolete in ("macOS", "Finder", "⌘"):
            self.assertNotIn(obsolete.casefold(), combined.casefold(), obsolete)
        self.assertNotIn("install Docker", combined)
        self.assertNotIn("start Docker", combined)

    def test_future_improvements_identifies_requested_roadmap_work(self):
        repository = Path(__file__).resolve().parents[1]
        roadmap = (repository / "docs" / "user" / "future-improvements.md").read_text(encoding="utf-8")
        self.assertIn("turning supported VisionEval modules on or off", roadmap)
        self.assertIn("official VisionEval GitHub documentation", roadmap)
        self.assertIn("Increased error handling", roadmap)
        self.assertIn("roadmap items", roadmap)

    def test_internal_markdown_links_resolve(self):
        repository = Path(__file__).resolve().parents[1]
        documents = [repository / "README.md", *sorted((repository / "docs").rglob("*.md"))]
        pattern = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
        failures = []
        for document in documents:
            for target in pattern.findall(document.read_text(encoding="utf-8")):
                target = target.strip().split("#", 1)[0]
                if not target or "://" in target or target.startswith("mailto:"):
                    continue
                resolved = (document.parent / unquote(target)).resolve()
                if not resolved.exists():
                    failures.append(f"{document.relative_to(repository)} -> {target}")
        self.assertEqual(failures, [])

    def test_user_guide_manifest_and_package_spec_are_complete(self):
        repository = Path(__file__).resolve().parents[1]
        guide = repository / "docs" / "user"
        metadata = json.loads((guide / "documentation.json").read_text())
        self.assertEqual(metadata["schemaVersion"], 2)
        self.assertTrue(metadata["documentationVersion"])
        self.assertTrue((guide / metadata["entrypoint"]).is_file())
        spec = (repository / "packaging" / "workbench-backend.spec").read_text()
        self.assertIn('root / "docs" / "user"', spec)
        self.assertIn('root / "backend" / "hypercube_summary.R"', spec)
        builder = (repository / "packaging" / "build_backend.py").read_text()
        self.assertIn('WORKBENCH_DOCUMENTATION_SOURCE", "docs/user"', builder)

    def test_platform_guides_and_release_identity_are_separate(self):
        repository = Path(__file__).resolve().parents[1]
        windows = json.loads((repository / "docs" / "user" / "documentation.json").read_text())
        tauri = json.loads((repository / "desktop" / "src-tauri" / "tauri.conf.json").read_text())
        package = json.loads((repository / "desktop" / "package.json").read_text())
        windows_manifest = json.loads(
            (repository / "docs" / "compatibility-manifest-windows.json").read_text()
        )
        self.assertEqual(tauri["version"], "2.0.0")
        self.assertEqual(package["version"], "2.0.0")
        self.assertEqual(windows["documentationVersion"], "2.0.0-windows-rev3")
        self.assertEqual(windows["schemaVersion"], 2)
        self.assertEqual([item["id"] for item in windows["documents"]], ["user-guide", "whats-new"])
        self.assertEqual(windows_manifest["runtimeAdapter"], "native-ve-runtime")
        self.assertFalse(windows_manifest["runtime"]["dockerRequired"])
        self.assertEqual(windows_manifest["releaseStatus"], "release-candidate-unsigned")

    @unittest.skip("macOS guide is outside the Windows release package")
    def test_macos_guide_is_current_and_free_of_encoding_corruption(self):
        repository = Path(__file__).resolve().parents[1]
        pages = sorted((repository / "docs" / "user-macos").glob("*.md"))
        combined = "\n".join(path.read_text(encoding="utf-8") for path in pages)
        self.assertIn("VisionEval-Workbench-v2.0.0-macos-arm64.dmg", combined)
        self.assertNotIn("VisionEval-Workbench-v1.1.0-macos-arm64.dmg", combined)
        self.assertNotIn("repository's release candidate", combined)
        for corrupted in ("â", "Ã"):
            self.assertNotIn(corrupted, combined)

    def test_public_documentation_contains_no_local_private_paths(self):
        repository = Path(__file__).resolve().parents[1]
        forbidden = ("/Users/", "nikolasleebishop", "Library/Application Support/com.visioneval")
        failures = []
        for path in [repository / "README.md", *sorted((repository / "docs").rglob("*"))]:
            if not path.is_file() or path.suffix.lower() not in {".md", ".json", ".svg"}:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for value in forbidden:
                if value in text:
                    failures.append(f"{path.relative_to(repository)} contains {value}")
        self.assertEqual(failures, [])

    def test_guide_images_are_real_and_contain_no_private_path_strings(self):
        repository = Path(__file__).resolve().parents[1]
        images = sorted((repository / "docs" / "user" / "images").iterdir())
        self.assertGreaterEqual(len(images), 5)
        forbidden = (b"/Users/", b"nikolasleebishop", b"Application Support")
        for path in images:
            payload = path.read_bytes()
            self.assertGreater(len(payload), 100, path.name)
            if path.suffix == ".png":
                self.assertTrue(payload.startswith(b"\x89PNG\r\n\x1a\n"), path.name)
            for value in forbidden:
                self.assertNotIn(value, payload, path.name)


if __name__ == "__main__":
    unittest.main()
