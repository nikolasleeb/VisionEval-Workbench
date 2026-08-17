from __future__ import annotations

from pathlib import Path
import os
import sys
import unittest
from unittest.mock import patch

BACKEND_ROOT = Path(__file__).parents[1] / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from main import configure_macos_certificates


class BackendMainTests(unittest.TestCase):
    def test_frozen_macos_backend_uses_system_certificate_bundle(self) -> None:
        with (
            patch.object(sys, "platform", "darwin"),
            patch.object(sys, "frozen", True, create=True),
            patch.object(Path, "is_file", return_value=True),
            patch.dict(os.environ, {}, clear=True),
        ):
            configure_macos_certificates()
            self.assertEqual(os.environ["SSL_CERT_FILE"], "/etc/ssl/cert.pem")

    def test_macos_certificate_configuration_preserves_explicit_override(self) -> None:
        with (
            patch.object(sys, "platform", "darwin"),
            patch.object(sys, "frozen", True, create=True),
            patch.object(Path, "is_file", return_value=True),
            patch.dict(os.environ, {"SSL_CERT_FILE": "/custom/ca.pem"}, clear=True),
        ):
            configure_macos_certificates()
            self.assertEqual(os.environ["SSL_CERT_FILE"], "/custom/ca.pem")

    def test_development_backend_does_not_override_certificate_path(self) -> None:
        with (
            patch.object(sys, "platform", "darwin"),
            patch.object(sys, "frozen", False, create=True),
            patch.dict(os.environ, {}, clear=True),
        ):
            configure_macos_certificates()
            self.assertNotIn("SSL_CERT_FILE", os.environ)

    def test_windows_parent_watcher_does_not_use_os_kill(self) -> None:
        source = (Path(__file__).parents[1] / "backend" / "main.py").read_text(
            encoding="utf-8"
        )
        windows_branch = source.split('if sys.platform == "win32":', 1)[1].split(
            "while True:", 1
        )[0]

        self.assertIn("WaitForSingleObject", windows_branch)
        self.assertNotIn("os.kill(parent_pid, 0)\n", windows_branch)


if __name__ == "__main__":
    unittest.main()
