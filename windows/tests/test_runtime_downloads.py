import hashlib
import io
import ssl
import subprocess
import tempfile
import threading
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from backend.workbench.runtime import RuntimeInstallCancelled, RuntimeManager
from backend.workbench.workspace import WorkspaceError


class Response(io.BytesIO):
    def __init__(self, data=b"verified payload", length=None):
        super().__init__(data)
        self.headers = {"Content-Length": str(len(data) if length is None else length)}


class RuntimeDownloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "runtime.zip"
        self.manager = RuntimeManager.__new__(RuntimeManager)
        self.digest = hashlib.sha256(b"verified payload").hexdigest()

    def download(self, **kwargs):
        self.manager._download_verified(
            "https://example.invalid/runtime.zip", self.path, self.digest,
            phase="downloading-visioneval", progress=kwargs.get("progress"),
            cancel_event=kwargs.get("cancel_event"),
        )

    def test_timeout_retries_and_reports_attempt(self):
        progress = []
        with patch("backend.workbench.runtime.urllib.request.urlopen", side_effect=[
            TimeoutError("read timed out"), Response(),
        ]) as opener, patch("backend.workbench.runtime.time.sleep"):
            self.download(progress=lambda phase, message, **details: progress.append((message, details)))
        self.assertEqual(opener.call_count, 2)
        self.assertEqual(opener.call_args.kwargs["timeout"], 120)
        self.assertEqual(self.path.read_bytes(), b"verified payload")
        self.assertTrue(any("retrying" in message and details["attempt"] == 2 for message, details in progress))

    def test_partial_timeout_restarts_without_appending(self):
        class Interrupted(Response):
            def read1(self, count):
                if self.tell():
                    raise TimeoutError("interrupted")
                return super().read1(3)
        with patch("backend.workbench.runtime.urllib.request.urlopen", side_effect=[Interrupted(), Response()]), patch("backend.workbench.runtime.time.sleep"):
            self.download()
        self.assertEqual(self.path.read_bytes(), b"verified payload")

    def test_retry_exhaustion_cleans_partial_file(self):
        with patch("backend.workbench.runtime.urllib.request.urlopen", side_effect=TimeoutError("timed out")) as opener, patch("backend.workbench.runtime.time.sleep"):
            with self.assertRaisesRegex(WorkspaceError, "after 3 attempt.*Setup guide"):
                self.download()
        self.assertEqual(opener.call_count, 3)
        self.assertFalse(self.path.exists())

    def test_truncated_body_retries(self):
        with patch("backend.workbench.runtime.urllib.request.urlopen", side_effect=[Response(b"short", 99), Response()]) as opener, patch("backend.workbench.runtime.time.sleep"):
            self.download()
        self.assertEqual(opener.call_count, 2)

    def test_checksum_failure_never_retries(self):
        with patch("backend.workbench.runtime.urllib.request.urlopen", return_value=Response(b"bad")) as opener:
            with self.assertRaisesRegex(WorkspaceError, "checksum"):
                self.download()
        self.assertEqual(opener.call_count, 1)
        self.assertFalse(self.path.exists())

    def test_tls_failure_never_retries(self):
        with patch("backend.workbench.runtime.urllib.request.urlopen", side_effect=urllib.error.URLError(ssl.SSLCertVerificationError("untrusted"))) as opener:
            with self.assertRaises(WorkspaceError):
                self.download()
        self.assertEqual(opener.call_count, 1)

    def test_http_not_found_never_retries(self):
        with patch("backend.workbench.runtime.urllib.request.urlopen", side_effect=urllib.error.HTTPError("https://example.invalid", 404, "Not found", {}, None)) as opener:
            with self.assertRaises(WorkspaceError):
                self.download()
        self.assertEqual(opener.call_count, 1)

    def test_http_service_unavailable_retries(self):
        error = urllib.error.HTTPError("https://example.invalid", 503, "Unavailable", {}, None)
        with patch("backend.workbench.runtime.urllib.request.urlopen", side_effect=[error, Response()]) as opener, patch("backend.workbench.runtime.time.sleep"):
            self.download()
        self.assertEqual(opener.call_count, 2)

    def test_cancellation_between_attempts(self):
        cancelled = threading.Event()
        def progress(phase, message, **details):
            if "retrying" in message:
                cancelled.set()
        with patch("backend.workbench.runtime.urllib.request.urlopen", side_effect=TimeoutError("timeout")) as opener:
            with self.assertRaises(RuntimeInstallCancelled):
                self.download(progress=progress, cancel_event=cancelled)
        self.assertEqual(opener.call_count, 1)
        self.assertFalse(self.path.exists())

    def test_cancelled_before_download_does_not_connect(self):
        cancelled = threading.Event()
        cancelled.set()
        with patch("backend.workbench.runtime.urllib.request.urlopen") as opener:
            with self.assertRaises(RuntimeInstallCancelled):
                self.download(cancel_event=cancelled)
        opener.assert_not_called()

    def test_disk_failure_does_not_retry_network(self):
        with patch("backend.workbench.runtime.urllib.request.urlopen", return_value=Response()) as opener, patch.object(Path, "open", side_effect=PermissionError("disk unavailable")):
            with self.assertRaises(PermissionError):
                self.download()
        self.assertEqual(opener.call_count, 1)

    def test_runtime_marker_uses_selected_r_version_and_no_forced_overwrite(self):
        root = Path(self.temp.name)
        runtime, home = root / "runtime", root / "home"
        RuntimeManager._write_native_runtime_files(runtime, home, root / "R/bin/Rscript.exe", "4.5.2")
        self.assertEqual((runtime / "r.version").read_text(), "that.R:4.5.2\n")
        self.assertIn("overwrite=FALSE", (runtime / ".Rprofile").read_text())

    def test_marker_parses_with_native_r_like_rc7_check_setup(self):
        rscript = RuntimeManager._compatible_rscript()
        if not rscript:
            self.skipTest("Compatible native R is not installed")
        version = subprocess.run([rscript, "--vanilla", "-e", 'cat(paste(R.version[c("major","minor")],collapse="."))'], capture_output=True, text=True, check=True).stdout.strip()
        root = Path(self.temp.name)
        RuntimeManager._write_native_runtime_files(root / "runtime", root / "home", Path(rscript), version)
        expression = (
            'args <- commandArgs(TRUE); '
            'vars <- data.frame(scan(file=args[1],sep=":",what=list(var=character(),var=character()),quiet=TRUE)); '
            'stopifnot(vars[1,1] == "that.R", vars[1,2] == paste(R.version[c("major","minor")],collapse=".")); cat("marker accepted")'
        )
        result = subprocess.run([rscript, "--vanilla", "-e", expression, str(root / "runtime/r.version")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("marker accepted", result.stdout)
