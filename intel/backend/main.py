#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path

from workbench.server import serve


def configure_macos_certificates() -> None:
    """Point frozen macOS builds at the operating system CA bundle.

    PyInstaller's embedded Python does not inherit the certificate path used by
    the system Python installation.  Without this, HTTPS requests made by the
    packaged backend (including the official ArcGIS region-map downloads) fail
    certificate verification even though the same URLs work in the browser.
    Respect an explicitly configured path and leave non-macOS/development
    environments unchanged.
    """
    if sys.platform != "darwin" or not getattr(sys, "frozen", False):
        return
    certificate_bundle = Path("/etc/ssl/cert.pem")
    if certificate_bundle.is_file():
        os.environ.setdefault("SSL_CERT_FILE", str(certificate_bundle))


def watch_parent(parent_pid: int) -> None:
    """Exit the sidecar after a Force Quit, which bypasses Tauri close events."""
    if sys.platform == "win32":
        # Unlike POSIX, os.kill(pid, 0) is not a harmless existence check on
        # Windows: Python implements it with TerminateProcess. Wait on a
        # SYNCHRONIZE-only process handle instead so the watcher cannot kill
        # the desktop process it is meant to observe.
        import ctypes
        from ctypes import wintypes

        synchronize = 0x00100000
        infinite = 0xFFFFFFFF
        wait_object_0 = 0
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
        kernel32.WaitForSingleObject.restype = wintypes.DWORD
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel32.CloseHandle.restype = wintypes.BOOL

        handle = kernel32.OpenProcess(synchronize, False, parent_pid)
        if not handle:
            # If Windows will not grant a monitoring handle, leave lifecycle
            # management to the Tauri parent rather than stopping the backend.
            return
        try:
            parent_exited = kernel32.WaitForSingleObject(handle, infinite) == wait_object_0
        finally:
            kernel32.CloseHandle(handle)
        if parent_exited:
            os._exit(0)
        return

    while True:
        time.sleep(1)
        try:
            os.kill(parent_pid, 0)
        except ProcessLookupError:
            os._exit(0)
        except PermissionError:
            return


def main() -> None:
    configure_macos_certificates()
    frozen = getattr(sys, "frozen", False)
    app_root = Path(sys.executable).resolve().parent if frozen else Path(__file__).resolve().parent.parent
    resource_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)).resolve()
    public_root = resource_root / "public" if (resource_root / "public").is_dir() else app_root / "public"
    workspace = Path(os.environ.get("VISIONEVAL_WORKSPACE_ROOT", app_root / "Workspace")).expanduser()
    parent_pid = int(os.environ.get("WORKBENCH_PARENT_PID", "0") or 0)
    if parent_pid > 1:
        threading.Thread(target=watch_parent, args=(parent_pid,), name="workbench-parent-watch", daemon=True).start()
    serve(workspace, public_root, resource_root, int(os.environ.get("PORT", "3000")))


if __name__ == "__main__":
    main()
