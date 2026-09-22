from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from .transit_inputs import FILE_GROUPS, validate_transit_inputs
from .workspace import RUN_VERSION, Workspace, WorkspaceError, make_id, now_iso, read_json, write_json


ARM64_LOCAL_IMAGE = "local/visioneval:2.0.0-arm64"
AMD64_LOCAL_IMAGE = "local/visioneval:2.0.0-amd64"
RUNTIME_REPOSITORY = "ghcr.io/nikolasleeb/visioneval-workbench-runtime"
PINNED_ARM64_RUNTIME_DIGEST = "sha256:f6dba706e39bc403ad08c8fb27c2a8d69d74875de096475df3ac8311e1c13791"
PINNED_ARM64_RUNTIME_REFERENCE = f"{RUNTIME_REPOSITORY}@{PINNED_ARM64_RUNTIME_DIGEST}"
LEGACY_ARM64_RUNTIME_DIGEST = "sha256:d730e304e890efd6c20ff2d0e89b2301899832105917b43eaca68cbbcced7caa"
LEGACY_ARM64_RUNTIME_REFERENCE = f"{RUNTIME_REPOSITORY}@{LEGACY_ARM64_RUNTIME_DIGEST}"


def docker_platform() -> str:
    """Return the verified Linux container platform for this desktop host."""
    machine = platform.machine().lower()
    if machine in {"arm64", "aarch64"}:
        return "linux/arm64"
    return "linux/amd64"


def local_runtime_image() -> str:
    return ARM64_LOCAL_IMAGE if docker_platform() == "linux/arm64" else AMD64_LOCAL_IMAGE


def docker_host_supported() -> bool:
    system, machine = platform.system(), platform.machine().lower()
    return (system == "Windows" and machine in {"amd64", "x86_64"}) or (
        system == "Darwin" and machine in {"arm64", "aarch64"}
    )


LOCAL_IMAGE = local_runtime_image()
DEFAULT_ADAPTER = "native" if platform.system() == "Windows" else "docker"
DEFAULT_IMAGE = os.environ.get("VISIONEVAL_IMAGE", LOCAL_IMAGE)
CURRENT_RELEASE_TAG = "VE-40-RC7"
CURRENT_RELEASE_COMMIT = "7852dc58fad460ff279f5eebf4dd55fe191470ad"
COMPATIBILITY_PATCH = "2026-08-03-composite-household-id-alignment"
SUPPORTED_RUNTIME_API = 1
RC7_RELEASE_TAG = "VE-40-RC7"
RC7_RELEASE_COMMIT = "7852dc58fad460ff279f5eebf4dd55fe191470ad"
PINNED_RUNTIME_PROFILE = {
    "runtimeApi": 1,
    "visionEvalVersion": RC7_RELEASE_TAG,
    "visionEvalCommit": RC7_RELEASE_COMMIT,
    "digest": PINNED_ARM64_RUNTIME_DIGEST,
    "reference": PINNED_ARM64_RUNTIME_REFERENCE,
    "platform": "macos",
    "architecture": "arm64",
    "capabilities": ["doctor", "verify-upstream-release", "verify-household-id-alignment", "run", "export"],
    "verificationCommands": ["doctor", "verify-upstream-release", "verify-household-id-alignment"],
    "compatibilityPatch": "none",
    "minimumWorkbenchVersion": "2.0.0",
    "downloadSizeBytes": 3042051717,
    "storageSizeBytes": 4386387432,
}
LEGACY_RUNTIME_PROFILE = {
    "runtimeApi": 0,
    "visionEvalVersion": "VE-40-RC6",
    "visionEvalCommit": "f7ef3389b5626daeba6c86eeda9d172a0f8cccc2",
    "digest": LEGACY_ARM64_RUNTIME_DIGEST,
    "reference": LEGACY_ARM64_RUNTIME_REFERENCE,
    "platform": "macos",
    "architecture": "arm64",
    "capabilities": ["doctor", "verify-upstream-release", "verify-alignment-patch", "run", "export"],
    "verificationCommands": ["doctor", "verify-upstream-release", "verify-alignment-patch"],
    "compatibilityPatch": COMPATIBILITY_PATCH,
}
RELEASES_API = "https://api.github.com/repos/VisionEval/VisionEval-4/releases?per_page=20"
RELEASE_CHECK_TTL_SECONDS = 24 * 60 * 60
TERMINAL_STATES = {"succeeded", "failed", "cancelled", "cleanup_failed"}
ACTIVE_STATES = {"preparing", "running", "exporting", "stopping"}
MAX_GLOBAL_RUNS = 1
CERTIFIED_R_VERSION = "4.5.3"
CERTIFIED_R_SERIES = "4.5"
CERTIFIED_R_INSTALLER_NAME = f"R-{CERTIFIED_R_VERSION}-win.exe"
CERTIFIED_R_INSTALLER_URL = f"https://cran.r-project.org/bin/windows/base/old/{CERTIFIED_R_VERSION}/{CERTIFIED_R_INSTALLER_NAME}"
CERTIFIED_R_INSTALLER_SHA256 = "768ae31bb0b6056def5b1a9789a7dc49306bd037d69b0a99cdd90183aa0c1a31"
CERTIFIED_VE_ARCHIVE_NAME = "VE-Installer_WinLibrary-R4.5_2026-09-07.zip"
CERTIFIED_VE_ARCHIVE_URL = f"https://github.com/VisionEval/VisionEval-4/releases/download/{RC7_RELEASE_TAG}/{CERTIFIED_VE_ARCHIVE_NAME}"
CERTIFIED_VE_ARCHIVE_SHA256 = "01a3f58ee5eb0ab40113cc8835ca99ab1d060b89ff9b442b41c35ce93708155d"


class RuntimeInstallCancelled(WorkspaceError):
    """Raised when the user cancels a managed runtime installation."""


def _canonical_path(value: str | Path) -> Path:
    return Path(value).expanduser().resolve(strict=False)


def validate_native_path_separation(runtime: str | Path, home: str | Path) -> tuple[Path, Path]:
    """Return canonical native paths after proving neither contains the other."""
    runtime_path, home_path = _canonical_path(runtime), _canonical_path(home)
    if os.path.normcase(str(runtime_path)) == os.path.normcase(str(home_path)):
        raise WorkspaceError("VE_RUNTIME and VE_HOME must be different folders.")
    try:
        common = Path(os.path.commonpath([str(runtime_path), str(home_path)]))
    except ValueError:
        common = None
    if common is not None and os.path.normcase(str(common)) in {
        os.path.normcase(str(runtime_path)), os.path.normcase(str(home_path))
    }:
        raise WorkspaceError("VE_RUNTIME and VE_HOME must be separate folders; neither can be inside the other.")
    return runtime_path, home_path


def read_description(path: Path) -> dict[str, str]:
    """Read the fields needed from an R package DESCRIPTION file."""
    values: dict[str, str] = {}
    current = ""
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if raw[:1].isspace() and current:
            values[current] = f"{values[current]} {raw.strip()}".strip()
            continue
        if ":" not in raw:
            current = ""
            continue
        current, value = raw.split(":", 1)
        current = current.strip()
        values[current] = value.strip()
    return values


def native_runtime_provenance(home: str | Path | None) -> dict[str, str]:
    """Identify an installed native release from package commit metadata."""
    if not home:
        return {"releaseTag": "", "revision": "", "packageVersion": ""}
    candidates = sorted(Path(home).glob("ve-lib/*/VEStart/DESCRIPTION"), reverse=True)
    fields = read_description(candidates[0]) if candidates else {}
    revision = str(fields.get("VECommit") or fields.get("RemoteSha") or "").strip().lower()
    release = RC7_RELEASE_TAG if revision == RC7_RELEASE_COMMIT else ""
    return {
        "releaseTag": release,
        "revision": revision,
        "packageVersion": str(fields.get("Version") or ""),
    }


class RunFailure(WorkspaceError):
    """A run failure with safe user-facing recovery metadata."""

    def __init__(
        self,
        message: str,
        *,
        kind: str = "unknown",
        exit_code: int | None = None,
        oom_killed: bool | None = None,
        technical_detail: str = "",
        recommended_action: str = "Review the run log and export diagnostics if the problem continues.",
        retryable: bool = True,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.exit_code = exit_code
        self.oom_killed = oom_killed
        self.technical_detail = technical_detail or message
        self.recommended_action = recommended_action
        self.retryable = retryable


def docker_command_env() -> dict[str, str]:
    """Expose Docker Desktop and its credential helper to Finder-launched builds."""
    environment = os.environ.copy()
    existing = [item for item in environment.get("PATH", "").split(os.pathsep) if item]
    preferred = [
        "/Applications/Docker.app/Contents/Resources/bin",
        str(Path.home() / ".docker" / "bin"),
        "/opt/homebrew/bin",
        "/usr/local/bin",
        "/usr/bin",
        "/bin",
        "/usr/sbin",
        "/sbin",
    ]
    merged: list[str] = []
    for item in [*preferred, *existing]:
        if Path(item).is_dir() and item not in merged:
            merged.append(item)
    environment["PATH"] = os.pathsep.join(merged)
    return environment


def find_docker_executable() -> str | None:
    """Find Docker even when a Finder-launched macOS app has a minimal PATH."""
    discovered = shutil.which("docker")
    if discovered:
        return discovered
    candidates = [
        os.environ.get("DOCKER_CLI", ""),
        str(Path.home() / ".docker" / "bin" / "docker"),
        "/usr/local/bin/docker",
        "/opt/homebrew/bin/docker",
        "/Applications/Docker.app/Contents/Resources/bin/docker",
    ]
    return next((path for path in candidates if path and Path(path).is_file() and os.access(path, os.X_OK)), None)


def find_rscript_executable(configured: str = "", version_hint: str = "", runtime: str | Path = "") -> str | None:
    """Find Rscript in PATH or a standard user/system Windows installation."""
    candidates = [configured]
    ambient = [os.environ.get("RSCRIPT", ""), shutil.which("Rscript") or ""]
    if platform.system() == "Windows":
        runtime_path = Path(runtime).expanduser() if runtime else None
        if runtime_path and runtime_path.is_dir():
            for launcher in sorted(runtime_path.glob("launch_R*.bat"), reverse=True):
                text = launcher.read_text(encoding="utf-8-sig", errors="replace")
                match = re.search(r'(?im)^\s*set\s+(?:"R_HOME_BASE\s*=\s*([^"\r\n]+)"|R_HOME_BASE\s*=\s*(.+?))\s*$', text)
                if match:
                    root = Path(os.path.expandvars((match.group(1) or match.group(2)).strip().strip('"')))
                    candidates.extend([str(root / "bin" / "Rscript.exe"), str(root / "bin" / "x64" / "Rscript.exe")])
        roots = [
            Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "Programs" / "R",
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "R",
        ]
        for root in roots:
            if root.is_dir() and version_hint:
                candidates.extend([str(root / f"R-{version_hint}" / "bin" / "Rscript.exe"), str(root / f"R-{version_hint}" / "bin" / "x64" / "Rscript.exe")])
        candidates.extend(ambient)
        for root in roots:
            if root.is_dir():
                candidates.extend(str(path) for path in sorted(root.glob("R-*/bin/Rscript.exe"), reverse=True))
                candidates.extend(str(path) for path in sorted(root.glob("R-*/bin/x64/Rscript.exe"), reverse=True))
    else:
        candidates.extend(ambient)
    return next((path for path in candidates if path and Path(path).is_file()), None)


def read_renviron(directory: str | Path) -> dict[str, str]:
    """Read the simple KEY=VALUE entries used by installed VE runtime folders."""
    values: dict[str, str] = {}
    path = Path(directory).expanduser() / ".Renviron"
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key in {"VE_HOME", "VE_RUNTIME"} and value:
            values[key] = os.path.expandvars(value)
    return values


def find_native_runtime(configured: str = "") -> Path | None:
    candidates = [configured, os.environ.get("VISIONEVAL_RUNTIME", ""), os.environ.get("VE_RUNTIME", "")]
    if platform.system() == "Windows":
        candidates.extend([str(Path.home() / "VE"), r"C:\VE"])
    for value in candidates:
        if not value:
            continue
        path = Path(value).expanduser()
        markers = (
            (path / ".Renviron").is_file(),
            (path / ".Rprofile").is_file(),
            (path / "r.version").is_file(),
            (path / "VisionEval.Rproj").is_file(),
            (path / "WORKBENCH-RELEASE").is_file(),
            any(path.glob("launch_R*.bat")) if path.is_dir() else False,
        )
        if path.is_dir() and any(markers):
            return path.resolve()
    return None


def find_native_home(configured: str = "") -> Path | None:
    candidates = [
        configured,
        os.environ.get("VISIONEVAL_HOME", ""),
        os.environ.get("VE_HOME", ""),
        r"C:\VisionEval",
        str(Path.home() / "VE_Home"),
        str(Path.home() / "VisionEval"),
        str(Path.home() / "Documents" / "VisionEval"),
    ]
    for value in candidates:
        if not value or value.startswith("local/"):
            continue
        path = Path(value).expanduser()
        if (path / "ve-lib").is_dir():
            return path.resolve()
    return None


def discover_native_installation(runtime: str = "", home: str = "", rscript: str = "") -> dict[str, Any]:
    warnings: list[str] = []
    if runtime:
        candidate = Path(runtime).expanduser()
        markers = (
            (candidate / ".Renviron").is_file(),
            (candidate / ".Rprofile").is_file(),
            (candidate / "r.version").is_file(),
            (candidate / "VisionEval.Rproj").is_file(),
            (candidate / "WORKBENCH-RELEASE").is_file(),
            any(candidate.glob("launch_R*.bat")) if candidate.is_dir() else False,
        )
        if not candidate.is_dir() or not any(markers):
            warnings.append(f"Ignored invalid VE_RUNTIME candidate: {runtime}")
    if home and not (Path(home).expanduser() / "ve-lib").is_dir():
        warnings.append(f"Ignored invalid VE_HOME candidate: {home}")
    if rscript and not Path(rscript).expanduser().is_file():
        warnings.append(f"Ignored invalid Rscript.exe candidate: {rscript}")
    runtime_path = find_native_runtime(runtime)
    environment = read_renviron(runtime_path) if runtime_path else {}
    home_path = find_native_home(home or environment.get("VE_HOME", ""))
    version_hint = ""
    for directory in (runtime_path, home_path):
        version_file = directory / "r.version" if directory else None
        if version_file and version_file.is_file():
            match = re.search(r"(\d+\.\d+(?:\.\d+)?)", version_file.read_text(encoding="utf-8-sig", errors="replace"))
            if match:
                version_hint = match.group(1)
                break
    resolved_rscript = find_rscript_executable(rscript, version_hint, runtime_path or "")
    if runtime_path and home_path:
        try:
            validate_native_path_separation(runtime_path, home_path)
        except WorkspaceError as exc:
            warnings.append(str(exc))
            home_path = None
    return {
        "veRuntime": str(runtime_path or ""),
        "veHome": str(home_path or ""),
        "rscript": str(resolved_rscript or ""),
        "warnings": warnings,
    }


class RuntimeManager:
    def __init__(self, workspace: Workspace, image: str = DEFAULT_IMAGE, runner: Callable[..., subprocess.CompletedProcess] | None = None, cli_path: str | Path | None = None):
        self.workspace = workspace
        self.image = image
        # The Windows edition deliberately supports one execution adapter. Do
        # not let configuration or an inherited environment variable activate
        # Docker in an installed Windows build.
        self.adapter = "native"
        self.container_platform = docker_platform()
        discovered_native = discover_native_installation(
            os.environ.get("VISIONEVAL_RUNTIME", ""),
            os.environ.get("VISIONEVAL_HOME", "") or os.environ.get("VE_HOME", ""),
            os.environ.get("RSCRIPT", ""),
        ) if self.adapter == "native" else {"veRuntime": "", "veHome": "", "rscript": ""}
        self.native_runtime = Path(discovered_native["veRuntime"]) if discovered_native["veRuntime"] else None
        self.native_home = Path(discovered_native["veHome"]) if discovered_native["veHome"] else None
        self.rscript = discovered_native["rscript"] if self.adapter == "native" else find_rscript_executable(os.environ.get("RSCRIPT", ""))
        self.cli_path = Path(cli_path or os.environ.get("VISIONEVAL_CLI", Path(__file__).resolve().parents[2] / "runtime" / "scripts" / "ve-cli-native.R"))
        if not self.cli_path.is_file():
            packaged_cli = Path(__file__).resolve().parent.parent / "ve-cli-native.R"
            if packaged_cli.is_file():
                self.cli_path = packaged_cli
        self.expected_digest = os.environ.get("VISIONEVAL_EXPECTED_DIGEST", "")
        self.runtime_enabled = os.environ.get("VISIONEVAL_RUNTIME_ENABLED", "true").lower() == "true"
        try:
            self.memory_limit_gb = float(os.environ["VISIONEVAL_MEMORY_GB"]) if os.environ.get("VISIONEVAL_MEMORY_GB") else None
        except ValueError:
            self.memory_limit_gb = None
        try:
            self.configured_max_runs = 1
        except ValueError:
            self.configured_max_runs = 1
        self.runner = runner or subprocess.run
        # The legacy runtime-only checker remains readable for old diagnostic
        # records, but scheduling now belongs to UpdateCheckService so runtime
        # verification never triggers a second network request.
        self.release_check_supported = False
        self.release_check_enabled = False
        self.release_status_path = self.workspace.exchange / "system" / "runtime-release-status.json"
        self.release_check_lock = threading.Lock()
        self.release_check_running = False
        self.lock = threading.RLock()
        self.condition = threading.Condition(self.lock)
        self.processes: dict[str, subprocess.Popen] = {}
        self.workers: dict[str, threading.Thread] = {}
        self.cancelled: set[str] = set()
        self.stop_all_in_progress = False
        self.stopping_projects: set[str] = set()
        self.queue_state_path = self.workspace.runs / "queue.json"
        self.runtime_profile_path = self.workspace.exchange / "system" / "runtime-profile.json"
        self.workspace_id = str(read_json(self.workspace.marker_path, {}).get("id") or "")
        self.active_runtime_profile = dict(PINNED_RUNTIME_PROFILE)
        self.previous_runtime_profile: dict[str, Any] | None = None
        self._load_runtime_profiles()
        self._prefer_installed_image()
        recovered = self._recover_jobs()
        with self.lock:
            self._normalize_queue_locked()
            for job_id in recovered:
                thread = threading.Thread(target=self._recovered_worker_entry, args=(job_id,), daemon=True, name=f"recovered-{job_id}")
                self.workers[job_id] = thread; thread.start()
        self.dispatcher = threading.Thread(target=self._dispatch_loop, daemon=True, name="visioneval-global-queue")
        self.dispatcher.start()
        if self.release_check_enabled:
            self._schedule_release_check()

    def _workspace_mount_args(self) -> list[str]:
        # Keep the runtime image's stable /workspace contract while allowing the
        # host workspace to use a cleaner managed layout.
        return [
            "-v", f"{self.workspace.root}:/workspace",
            "-v", f"{self.workspace.models}:/workspace/models",
            "-v", f"{self.workspace.runs}:/workspace/runs",
            "-v", f"{self.workspace.exchange}:/workspace/exchange",
        ]

    def _load_runtime_profiles(self) -> None:
        state = read_json(self.runtime_profile_path, {})
        has_saved_active = isinstance(state, dict) and isinstance(state.get("active"), dict)
        active = state.get("active") if isinstance(state, dict) else None
        previous = state.get("previous") if isinstance(state, dict) else None
        if isinstance(active, dict):
            try:
                self.active_runtime_profile = self._validate_runtime_profile(active, allow_legacy=True)
            except WorkspaceError:
                self.active_runtime_profile = dict(PINNED_RUNTIME_PROFILE)
        if isinstance(previous, dict):
            try:
                self.previous_runtime_profile = self._validate_runtime_profile(previous, allow_legacy=True)
            except WorkspaceError:
                self.previous_runtime_profile = None
        if has_saved_active and not os.environ.get("VISIONEVAL_IMAGE"):
            self.image = str(self.active_runtime_profile["reference"])
            self.expected_digest = str(self.active_runtime_profile["digest"])
        elif not os.environ.get("VISIONEVAL_EXPECTED_DIGEST"):
            # A fresh Version 2 workspace starts from the approved RC7 digest.
            # Existing workspaces retain any valid saved legacy profile above.
            self.expected_digest = str(self.active_runtime_profile["digest"])

    def _save_runtime_profiles(self) -> None:
        write_json(self.runtime_profile_path, {
            "schemaVersion": 1,
            "active": self.active_runtime_profile,
            "previous": self.previous_runtime_profile,
            "updatedAt": now_iso(),
        })

    def _validate_runtime_profile(self, profile: dict[str, Any], *, allow_legacy: bool = False) -> dict[str, Any]:
        value = dict(profile)
        runtime_api = int(value.get("runtimeApi") or 0)
        digest = str(value.get("digest") or "")
        reference = str(value.get("reference") or "")
        architecture = str(value.get("architecture") or "")
        version = str(value.get("visionEvalVersion") or "")
        commit = str(value.get("visionEvalCommit") or "")
        capabilities = list(map(str, value.get("capabilities") or []))
        if runtime_api == 0 and allow_legacy and digest == LEGACY_ARM64_RUNTIME_DIGEST:
            return {**LEGACY_RUNTIME_PROFILE, **value}
        if runtime_api != SUPPORTED_RUNTIME_API:
            raise WorkspaceError(f"Runtime API {runtime_api} is not supported by this Workbench release.")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest) or reference != f"{RUNTIME_REPOSITORY}@{digest}":
            raise WorkspaceError("The runtime profile does not contain a trusted immutable image digest.")
        if architecture != "arm64" or value.get("platform") != "macos":
            raise WorkspaceError("The runtime profile does not match this Mac architecture.")
        if not re.fullmatch(r"VE-\d+-RC\d+", version) or not re.fullmatch(r"[0-9a-f]{40}", commit):
            raise WorkspaceError("The runtime profile has invalid VisionEval provenance.")
        required = {"doctor", "verify-upstream-release", "verify-household-id-alignment", "run", "export"}
        if not required.issubset(set(capabilities)):
            raise WorkspaceError("The runtime profile is missing required Workbench capabilities.")
        value["verificationCommands"] = ["doctor", "verify-upstream-release", "verify-household-id-alignment"]
        value["compatibilityPatch"] = "none"
        return value

    def runtime_profiles(self) -> dict[str, Any]:
        return {"active": dict(self.active_runtime_profile), "previous": dict(self.previous_runtime_profile) if self.previous_runtime_profile else None}

    def _native_environment(self) -> dict[str, str]:
        if not self.native_runtime or not self.native_home:
            raise WorkspaceError("VisionEval native runtime was not found. Choose VE_RUNTIME and VE_HOME in Runtime settings.")
        environment = os.environ.copy()
        environment.update({
            "VISIONEVAL_RUNTIME_ADAPTER": "native",
            "VE_HOME": str(self.native_home),
            "VE_RUNTIME": str(self.native_runtime),
            "VE_RELEASE_METADATA": str(self.native_home / "WORKBENCH-RELEASE"),
        })
        return environment

    def _native_command(self, command: str, *args: str) -> tuple[list[str], dict[str, str]]:
        rscript = self.rscript or find_rscript_executable()
        if not rscript:
            raise WorkspaceError("Rscript was not found. Choose the Rscript.exe used by this VisionEval installation.")
        if not self.cli_path.is_file():
            raise WorkspaceError("The Workbench VisionEval command script is missing")
        return [rscript, "--vanilla", str(self.cli_path), command, *args], self._native_environment()

    @staticmethod
    def _native_creation_flags() -> int:
        return subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0

    @staticmethod
    def _terminate_native_tree(process: subprocess.Popen, timeout: float = 10) -> None:
        """Stop an R process and every child it created on Windows."""
        if process.poll() is not None:
            return
        if os.name == "nt":
            subprocess.run(
                ["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        else:
            process.terminate()
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=timeout)

    def discover_native(self, runtime: str = "", home: str = "", rscript: str = "") -> dict[str, Any]:
        if self.adapter != "native":
            raise WorkspaceError("Native VisionEval discovery is available only on Windows")
        return discover_native_installation(runtime, home, rscript)

    def configure_native(self, runtime: str, home: str, rscript: str) -> None:
        if self.adapter != "native":
            raise WorkspaceError("Native VisionEval configuration is available only on Windows")
        resolved_runtime = find_native_runtime(runtime)
        if not resolved_runtime or resolved_runtime != Path(runtime).expanduser().resolve():
            raise WorkspaceError("Choose a VE_RUNTIME folder containing VisionEval startup configuration")
        resolved_home = find_native_home(home)
        if not resolved_home or resolved_home != Path(home).expanduser().resolve():
            raise WorkspaceError("Choose a VE_HOME folder containing ve-lib")
        resolved_runtime, resolved_home = validate_native_path_separation(resolved_runtime, resolved_home)
        resolved_rscript = find_rscript_executable(rscript)
        if not resolved_rscript or Path(resolved_rscript).resolve() != Path(rscript).expanduser().resolve():
            raise WorkspaceError("Choose a valid Rscript.exe")
        self.native_runtime = resolved_runtime
        self.native_home = resolved_home
        self.image = str(resolved_home)
        self.rscript = str(Path(resolved_rscript).resolve())

    def runtime_path(self, path: str | Path) -> str:
        resolved = Path(path).resolve()
        if self.adapter == "native":
            return str(resolved)
        try:
            return "/workspace/" + resolved.relative_to(self.workspace.root).as_posix()
        except ValueError as exc:
            raise WorkspaceError(f"Runtime helper path is outside the Workbench workspace: {resolved}") from exc

    def r_command(self, script: str | Path, *args: str) -> tuple[list[str], dict[str, str] | None]:
        if self.adapter == "native":
            rscript = self.rscript or find_rscript_executable()
            if not rscript:
                raise WorkspaceError("Rscript was not found. Choose Rscript.exe in Runtime settings.")
            return [rscript, "--vanilla", str(Path(script).resolve()), *map(str, args)], self._native_environment()
        docker = find_docker_executable()
        if not docker:
            raise WorkspaceError("Docker Desktop is required on macOS to read VisionEval datastores")
        mapped = []
        for value in map(str, args):
            candidate = Path(value)
            mapped.append(self.runtime_path(candidate) if candidate.is_absolute() else value)
        return [docker, "run", "--rm", "--platform", self.container_platform, "--entrypoint", "Rscript", *self._workspace_mount_args(), self.image, self.runtime_path(script), *mapped], None

    def _cached_release_status(self) -> dict[str, Any]:
        cached = read_json(self.release_status_path, {})
        if not isinstance(cached, dict):
            cached = {}
        cached.setdefault("currentTag", CURRENT_RELEASE_TAG)
        cached.setdefault("currentCommit", CURRENT_RELEASE_COMMIT)
        return cached

    def _schedule_release_check(self, force: bool = False) -> None:
        if not self.release_check_enabled:
            return
        cached = self._cached_release_status()
        checked_at = float(cached.get("checkedAtEpoch") or 0)
        if not force and checked_at and time.time() - checked_at < RELEASE_CHECK_TTL_SECONDS:
            return
        with self.release_check_lock:
            if self.release_check_running:
                return
            self.release_check_running = True
        threading.Thread(target=self._refresh_release_status, daemon=True, name="visioneval-release-check").start()

    def _fetch_public_releases(self) -> list[dict[str, Any]]:
        request = urllib.request.Request(
            RELEASES_API,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "VisionEval-Workbench/2.0.0",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        with urllib.request.urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, list):
            raise ValueError("VisionEval release service returned an unexpected response")
        return [item for item in payload if isinstance(item, dict) and not item.get("draft")]

    def _refresh_release_status(self) -> None:
        previous = self._cached_release_status()
        try:
            releases = self._fetch_public_releases()
            if not releases:
                raise ValueError("No published VisionEval releases were returned")
            latest = releases[0]
            latest_tag = str(latest.get("tag_name") or "").strip()
            current_index = next((index for index, item in enumerate(releases) if item.get("tag_name") == CURRENT_RELEASE_TAG), None)
            releases_behind = 0 if latest_tag == CURRENT_RELEASE_TAG else (current_index if current_index is not None else len(releases))
            status = {
                "status": "current" if latest_tag == CURRENT_RELEASE_TAG else "update_available",
                "currentTag": CURRENT_RELEASE_TAG,
                "currentCommit": CURRENT_RELEASE_COMMIT,
                "latestTag": latest_tag,
                "latestName": latest.get("name") or latest_tag,
                "latestPublishedAt": latest.get("published_at") or "",
                "latestUrl": latest.get("html_url") or "https://github.com/VisionEval/VisionEval-4/releases",
                "releasesBehind": releases_behind,
                "checkedAt": now_iso(),
                "checkedAtEpoch": time.time(),
                "stale": False,
                "advisoryOnly": True,
                "message": "The pinned VisionEval release is current." if latest_tag == CURRENT_RELEASE_TAG else f"VisionEval {latest_tag} is available. Updating is optional.",
            }
            if self.release_check_enabled:
                self.release_status_path.parent.mkdir(parents=True, exist_ok=True)
                write_json(self.release_status_path, status)
        except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError) as exc:
            failure = {
                **previous,
                "status": previous.get("status", "unavailable"),
                "currentTag": CURRENT_RELEASE_TAG,
                "currentCommit": CURRENT_RELEASE_COMMIT,
                "checkError": str(exc),
                "lastAttemptAt": now_iso(),
                "stale": True,
                "advisoryOnly": True,
                "message": "Could not check for newer VisionEval releases. The pinned runtime can still be used.",
            }
            if self.release_check_enabled:
                self.release_status_path.parent.mkdir(parents=True, exist_ok=True)
                write_json(self.release_status_path, failure)
        finally:
            with self.release_check_lock:
                self.release_check_running = False

    def release_status(self) -> dict[str, Any]:
        cached = self._cached_release_status()
        if not self.release_check_enabled:
            return {
                **cached,
                "status": "disabled",
                "checking": False,
                "advisoryOnly": True,
                "message": "Automatic VisionEval update checks are disabled.",
            }
        if self.release_check_enabled:
            self._schedule_release_check()
        if not cached.get("status"):
            cached.update({
                "status": "checking" if self.release_check_enabled else "disabled",
                "message": "Checking the official VisionEval release feed…" if self.release_check_enabled else "Automatic release checks are disabled.",
                "advisoryOnly": True,
            })
        cached["checking"] = self.release_check_running
        return cached

    def set_release_check_enabled(self, enabled: bool) -> None:
        self.release_check_enabled = self.release_check_supported and bool(enabled)
        if self.release_check_enabled:
            self._schedule_release_check(force=True)

    def _prefer_installed_image(self) -> None:
        if self.adapter == "native":
            discovered = find_native_home(self.image)
            if discovered:
                self.native_home = discovered
                self.image = str(discovered)
            return
        if os.environ.get("VISIONEVAL_IMAGE") or self.image != DEFAULT_IMAGE:
            return
        executable = find_docker_executable()
        if not executable:
            return
        try:
            preferred = self.runner([executable, "image", "inspect", self.image], capture_output=True, text=True, timeout=15)
            if preferred.returncode == 0:
                return
            local = self.runner([executable, "image", "inspect", LOCAL_IMAGE], capture_output=True, text=True, timeout=15)
            if local.returncode == 0:
                self.image = LOCAL_IMAGE
        except (OSError, subprocess.TimeoutExpired):
            pass

    def _recover_jobs(self) -> list[str]:
        recovered: list[str] = []
        for path in self.workspace.runs.glob("*/job.json"):
            job = read_json(path, {})
            if job.get("state") in ACTIVE_STATES:
                if self.adapter == "native":
                    failure = RunFailure(
                        "Workbench closed while this VisionEval run was active. Retry it to start the run again.",
                        kind="recovery",
                        technical_detail="Workbench stopped while this native VisionEval run was active",
                        recommended_action="Retry this run. If the problem repeats, export diagnostics.",
                    )
                    job.update(state="failed", finishedAt=now_iso(), verification="failed", **self._failure_fields(failure))
                    write_json(path, job)
                    continue
                executable = find_docker_executable()
                owned = bool(executable and job.get("containerName") and self._container_owned(job))
                if owned and job.get("state") in {"running", "exporting"}:
                    recovered.append(job["id"])
                    job["message"] = "Reconnecting to VisionEval after Workbench restart"
                    write_json(path, job)
                    continue
                cleaned = False
                if owned:
                    try:
                        self.runner([executable, "stop", "--time", "10", job["containerName"]], capture_output=True, text=True, timeout=20)
                        cleaned = self._remove_owned_container(job, executable)
                    except (OSError, subprocess.TimeoutExpired):
                        pass
                failure = RunFailure(
                    "Workbench closed while this run was active. Retry it to start the run again." if cleaned else "Workbench could not safely reconnect to the prior run. Its container was left untouched because ownership could not be verified.",
                    kind="recovery",
                    technical_detail="Stale Workbench container cleaned up after restart" if cleaned else "Container ownership could not be verified after restart",
                    recommended_action="Retry this run." if cleaned else "Check Docker Desktop for the prior container, then export diagnostics before retrying.",
                )
                job.update(state="failed", finishedAt=now_iso(), verification="failed", **self._failure_fields(failure))
                write_json(path, job)
        return recovered

    def _recovered_worker_entry(self, job_id: str) -> None:
        try:
            self._monitor_recovered_job(job_id)
        finally:
            with self.condition:
                self.workers.pop(job_id, None); self.condition.notify_all()

    def _monitor_recovered_job(self, job_id: str) -> None:
        job, executable = self.job(job_id), find_docker_executable()
        if not executable or not self._container_owned(job):
            failure = RunFailure(
                "Workbench could not reconnect to the prior VisionEval container. Retry the run to start it again.",
                kind="recovery",
                technical_detail="The recovered VisionEval container is no longer available",
                recommended_action="Confirm Docker Desktop is running, then retry this run.",
            )
            self._save_job(job, state="failed", finishedAt=now_iso(), verification="failed", **self._failure_fields(failure))
            return
        container_state: dict[str, Any] = {}
        try:
            self._append_log(job, "\n--- Reconnected to the existing VisionEval container ---\n")
            waited = self.runner([executable, "wait", job["containerName"]], capture_output=True, text=True, timeout=None)
            logs = self.runner([executable, "logs", job["containerName"]], capture_output=True, text=True, timeout=30)
            if logs.stdout or logs.stderr:
                self._append_log(job, (logs.stdout or "") + (logs.stderr or ""))
            exit_code = int((waited.stdout or "1").strip().splitlines()[-1]) if waited.returncode == 0 else 1
            container_state = self._container_state(job, executable)
            self._remove_owned_container(job, executable)
            if exit_code:
                raise self._execution_failure(exit_code, container_state, recovered=True)
            self._finalize_success(job_id, executable)
        except Exception as exc:
            current = self._safe_job(job_id)
            if current.get("containerName") and self._container_exists(current["containerName"]):
                if not container_state:
                    container_state = self._container_state(current, executable)
                self._remove_owned_container(current, executable)
            fields = self._failure_fields(exc)
            self._append_log(current, f"\nWorkbench recovery error: {fields.get('technicalDetail') or exc}\n")
            self._save_job(current, state="failed", finishedAt=now_iso(), verification="failed", **fields)

    def _queue_state(self) -> dict[str, Any]:
        state = read_json(self.queue_state_path, {"version": 2, "revision": 0, "modeLock": None})
        return state if isinstance(state, dict) else {"version": 2, "revision": 0, "modeLock": None}

    def _job_mode(self, job: dict[str, Any]) -> str:
        mode = job.get("batchMode") or self._batch(job.get("batchId", "")).get("mode")
        return mode if mode in {"queued", "parallel"} else "queued"

    def _unfinished_jobs_locked(self) -> list[dict[str, Any]]:
        jobs = []
        for path in self.workspace.runs.glob("*/job.json"):
            job = read_json(path, {})
            if job.get("state") in ACTIVE_STATES | {"waiting"}:
                jobs.append(job)
        return sorted(jobs, key=lambda item: (item.get("createdAt", ""), item.get("id", "")))

    def _mode_lock_locked(self, state: dict[str, Any] | None = None, unfinished: list[dict[str, Any]] | None = None) -> str | None:
        unfinished = self._unfinished_jobs_locked() if unfinished is None else unfinished
        if not unfinished:
            return None
        active_batch = self._active_batch_id_locked(unfinished)
        owner = next(
            (
                job for job in unfinished
                if str(job.get("batchId") or job.get("id") or "") == active_batch
            ),
            unfinished[0],
        )
        return "queued" if self.adapter == "native" else self._job_mode(owner)

    def _write_queue_state_locked(self, revision: int, mode_lock: str | None) -> None:
        try:
            write_json(self.queue_state_path, {
                "version": 2,
                "revision": revision,
                "modeLock": mode_lock,
                "updatedAt": now_iso(),
            })
        except OSError:
            # A daemon dispatcher can briefly outlive a temporary workspace in
            # tests or an app shutdown. Suppress only that teardown race; a
            # missing path in a live workspace remains a real error.
            if not self.workspace.root.exists() or not self.queue_state_path.parent.exists():
                return
            raise

    def _normalize_queue_locked(self, increment: bool = False) -> list[dict[str, Any]]:
        jobs = []
        for path in self.workspace.runs.glob("*/job.json"):
            job = read_json(path, {})
            if job.get("state") == "waiting":
                jobs.append(job)
        jobs.sort(key=lambda item: (
            item.get("queuePosition") if isinstance(item.get("queuePosition"), int) else 10**12,
            item.get("createdAt", ""), item.get("id", ""),
        ))
        state = self._queue_state()
        unfinished = self._unfinished_jobs_locked()
        mode_lock = self._mode_lock_locked(state, unfinished)
        if increment:
            state["revision"] = int(state.get("revision", 0)) + 1
        revision = int(state.get("revision", 0))
        for position, job in enumerate(jobs, 1):
            if job.get("queuePosition") != position or job.get("queueRevision") != revision:
                job["queuePosition"] = position
                job["queueRevision"] = revision
                write_json(self.workspace.runs / job["id"] / "job.json", job)
        self._write_queue_state_locked(revision, mode_lock)
        return jobs

    def queue(self) -> dict[str, Any]:
        with self.lock:
            jobs = self._normalize_queue_locked()
            state = self._queue_state()
            mode_lock = self._mode_lock_locked(state)
            return {
                "revision": int(state.get("revision", 0)),
                "jobs": jobs,
                "maxActive": self._effective_max_active_locked(mode_lock),
                "modeLock": mode_lock,
                "activeBatchId": self._active_batch_id_locked(),
            }

    @property
    def max_active_runs(self) -> int:
        """Native VisionEval shares one R runtime and must execute serially."""
        return 1 if self.adapter == "native" else self.configured_max_runs

    def _effective_max_active_locked(self, mode_lock: str | None = None) -> int:
        mode_lock = self._mode_lock_locked() if mode_lock is None else mode_lock
        return 1 if self.adapter == "native" or mode_lock == "queued" else self.max_active_runs

    def _batch(self, batch_id: str) -> dict[str, Any]:
        return read_json(self.workspace.runs / f"{batch_id}.json", {})

    def _eligible_locked(self, job: dict[str, Any]) -> bool:
        active_batch = self._active_batch_id_locked()
        job_batch = str(job.get("batchId") or job.get("id") or "")
        if active_batch and job_batch != active_batch:
            return False
        mode_lock = self._mode_lock_locked()
        return mode_lock != "queued" or not any(worker_id != job.get("id") for worker_id in self.workers)

    def _active_batch_id_locked(self, unfinished: list[dict[str, Any]] | None = None) -> str | None:
        """Return the only submitted batch currently entitled to runtime slots."""
        unfinished = self._unfinished_jobs_locked() if unfinished is None else unfinished
        active = sorted(
            (job for job in unfinished if job.get("state") in ACTIVE_STATES),
            key=lambda item: (item.get("startedAt") or item.get("createdAt", ""), item.get("id", "")),
        )
        if active:
            return str(active[0].get("batchId") or active[0].get("id") or "")
        waiting = sorted(
            (job for job in unfinished if job.get("state") == "waiting"),
            key=lambda item: (item.get("queuePosition", 10**12), item.get("createdAt", ""), item.get("id", "")),
        )
        return str(waiting[0].get("batchId") or waiting[0].get("id") or "") if waiting else None

    def _next_waiting_job_locked(self, waiting: list[dict[str, Any]]) -> dict[str, Any] | None:
        """Return an eligible job that has not already reserved a runtime slot.

        Jobs remain in the ``waiting`` state briefly after their worker thread is
        created. Excluding reserved IDs prevents the dispatcher from selecting the
        same job repeatedly while it still owns the queue lock, which would starve
        the worker before it can transition the job to ``preparing``.
        """
        return next(
            (
                item
                for item in waiting
                if item.get("id") not in self.workers and self._eligible_locked(item)
            ),
            None,
        )

    def _safe_job(self, job_id: str) -> dict[str, Any]:
        return read_json(self.workspace.runs / job_id / "job.json", {})

    def _running_container_names(self) -> set[str]:
        if self.adapter == "native":
            return set()
        executable = find_docker_executable()
        if not executable:
            return set()
        try:
            result = self.runner(
                [executable, "ps", "--filter", "label=com.visioneval.workbench=true", "--format", "{{.Names}}"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode:
                return set()
            return {line.strip() for line in result.stdout.splitlines() if line.strip() and line.strip() != "{}"}
        except (OSError, subprocess.TimeoutExpired):
            return set()

    def _container_owned(self, job: dict[str, Any]) -> bool:
        """Accept only a container carrying the Workbench label and matching job identity."""
        executable, name = find_docker_executable(), job.get("containerName", "")
        if not executable or not name:
            return False
        try:
            result = self.runner([executable, "inspect", "--format", "{{json .Config.Labels}}", name], capture_output=True, text=True, timeout=10)
            if result.returncode:
                return False
            labels = json.loads(result.stdout or "{}") or {}
            identity_matches = labels.get("com.visioneval.workbench") == "true" and (
                labels.get("com.visioneval.job") == job.get("id") or
                (not labels.get("com.visioneval.job") and name == f"ve-{job.get('id')}")
            )
            expected_workspace = str(job.get("workspaceId") or self.workspace_id or "")
            expected_attempt = str(job.get("executionAttempt") or "")
            workspace_matches = not expected_workspace or not labels.get("com.visioneval.workspace") or labels.get("com.visioneval.workspace") == expected_workspace
            attempt_matches = not expected_attempt or labels.get("com.visioneval.attempt") == expected_attempt
            return identity_matches and workspace_matches and attempt_matches
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
            return False

    def _container_exists(self, name: str) -> bool:
        executable = find_docker_executable()
        if not executable or not name:
            return False
        try:
            result = self.runner([executable, "inspect", name], capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False

    def _container_state(self, job: dict[str, Any], executable: str | None = None) -> dict[str, Any]:
        """Read terminal state only from the labelled container owned by this job."""
        executable = executable or find_docker_executable()
        if not executable or not self._container_owned(job):
            return {}
        try:
            result = self.runner(
                [executable, "inspect", "--format", "{{json .State}}", job.get("containerName", "")],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode:
                return {}
            state = json.loads(result.stdout or "{}") or {}
            return state if isinstance(state, dict) else {}
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
            return {}

    def _remove_owned_container(self, job: dict[str, Any], executable: str | None = None) -> bool:
        """Remove a stopped job container without ever touching an unverified container."""
        executable = executable or find_docker_executable()
        if not executable or not job.get("containerName") or not self._container_owned(job):
            return False
        try:
            result = self.runner(
                [executable, "rm", "-f", job["containerName"]],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False

    @staticmethod
    def _execution_failure(exit_code: int, container_state: dict[str, Any] | None = None, *, recovered: bool = False) -> RunFailure:
        state = container_state or {}
        oom_known = "OOMKilled" in state
        oom_killed = bool(state.get("OOMKilled")) if oom_known else None
        state_error = str(state.get("Error") or "").strip()
        prefix = "Recovered VisionEval container" if recovered else "VisionEval"
        technical = f"{prefix} exited with code {exit_code}"
        if state_error:
            technical += f"; Docker reported: {state_error}"
        if oom_killed:
            return RunFailure(
                "Docker stopped this run because it ran out of available memory. Reduce parallel runs or increase Docker’s memory allocation, then retry.",
                kind="memory",
                exit_code=exit_code,
                oom_killed=True,
                technical_detail=technical,
                recommended_action="Open Settings → Resources, reduce concurrent runs or raise the applicable Docker memory limit, then retry.",
            )
        if exit_code == 137:
            return RunFailure(
                "This run was forcibly stopped, but Docker did not report an out-of-memory event. Check whether Workbench, Docker, or the computer stopped the container before retrying.",
                kind="interrupted",
                exit_code=exit_code,
                oom_killed=oom_killed,
                technical_detail=technical,
                recommended_action="Review the run log and Docker status, then retry. Reduce concurrency only if memory pressure is independently confirmed.",
            )
        if exit_code in {125, 126, 127}:
            return RunFailure(
                "Docker could not start the VisionEval run. Check that Docker Desktop and the verified runtime are available, then retry.",
                kind="docker_start",
                exit_code=exit_code,
                oom_killed=oom_killed,
                technical_detail=technical,
                recommended_action="Verify the runtime in Settings and review the run log before retrying.",
            )
        return RunFailure(
            "VisionEval stopped before completing this run. Review the run log for the model stage that failed, then retry after correcting the problem.",
            kind="model_execution",
            exit_code=exit_code,
            oom_killed=oom_killed,
            technical_detail=technical,
            recommended_action="Review Live Output or export diagnostics, correct the reported model error, and retry.",
        )

    @staticmethod
    def _failure_fields(exc: Exception) -> dict[str, Any]:
        if isinstance(exc, RunFailure):
            return {
                "message": str(exc),
                "failureKind": exc.kind,
                "exitCode": exc.exit_code,
                "oomKilled": exc.oom_killed,
                "technicalDetail": exc.technical_detail,
                "recommendedAction": exc.recommended_action,
                "retryable": exc.retryable,
            }
        text = str(exc)
        match = re.search(r"(?:exit(?:ed)?(?: with)? code|code)\s+(-?\d+)", text, re.IGNORECASE)
        exit_code = int(match.group(1)) if match else None
        if exit_code is not None:
            failure = RuntimeManager._execution_failure(exit_code)
            fields = RuntimeManager._failure_fields(failure)
            fields["technicalDetail"] = text
            return fields
        if isinstance(exc, WorkspaceError):
            lowered = text.lower()
            kind = "runtime_incompatible" if any(token in lowered for token in ("runtime", "compatible", "package", "module")) else "model_preparation"
            return {
                "message": text,
                "failureKind": kind,
                "exitCode": None,
                "oomKilled": None,
                "technicalDetail": text,
                "recommendedAction": "Review the run log, correct the reported configuration or model-data problem, and retry.",
                "retryable": True,
            }
        return {
            "message": "Workbench could not complete this run. Review Live Output and export diagnostics if the problem continues.",
            "failureKind": "unknown",
            "exitCode": None,
            "oomKilled": None,
            "technicalDetail": text,
            "recommendedAction": "Review the run log and export diagnostics before retrying.",
            "retryable": True,
        }

    def _dispatch_loop(self) -> None:
        while True:
            if not self.workspace.root.exists():
                return
            with self.condition:
                launched = False
                if not self.runtime_enabled:
                    self.condition.wait(timeout=1.0)
                    continue
                if self.stop_all_in_progress:
                    self.condition.wait(timeout=.1)
                    continue
                while len(self.workers) < self._effective_max_active_locked():
                    waiting = self._normalize_queue_locked()
                    job = self._next_waiting_job_locked(waiting)
                    if not job:
                        break
                    # A worker reserves a slot before preparation. Containers not owned by a
                    # reserved worker are stale/external Workbench containers and also consume
                    # capacity, preventing a restart race from exceeding the hard ceiling.
                    running_names = self._running_container_names()
                    reserved_names = {
                        self._safe_job(worker_id).get("containerName", "")
                        for worker_id in self.workers
                    }
                    unreserved_containers = running_names - reserved_names - {""}
                    if len(self.workers) + len(unreserved_containers) >= self._effective_max_active_locked():
                        break
                    thread = threading.Thread(target=self._worker_entry, args=(job["id"],), daemon=True, name=f"job-{job['id']}")
                    self.workers[job["id"]] = thread
                    thread.start()
                    launched = True
                if not launched:
                    self.condition.wait(timeout=1.0)

    def _worker_entry(self, job_id: str) -> None:
        try:
            self._run_job(job_id)
        finally:
            with self.condition:
                self.workers.pop(job_id, None)
                self._normalize_queue_locked(increment=True)
                self.condition.notify_all()

    def docker_status(self) -> dict[str, Any]:
        if self.adapter == "native":
            return self._native_status()
        self._prefer_installed_image()
        executable = find_docker_executable()
        result = {
            "installed": bool(executable),
            "running": False,
            "executable": executable or "",
            "hostArchitecture": platform.machine(),
            "supported": docker_host_supported(),
            "containerPlatform": self.container_platform,
            "image": self.image,
            "imagePresent": False,
            "adapter": self.adapter,
            "imageDigest": "",
            "digestMatches": False,
            "imageReleaseTag": "",
            "imageRevision": "",
            "imageCompatibilityPatch": "",
            "provenanceMatches": False,
            "releaseCheck": self.release_status(),
            "dockerMemoryBytes": 0,
            "memoryLimitGb": self.memory_limit_gb,
            "remoteStatus": "local" if self.image.startswith("local/") else "configured-remote",
            "profileEnabled": self.runtime_enabled,
            "runtimeProfiles": self.runtime_profiles(),
            "error": "",
        }
        if not executable:
            result["error"] = "Docker CLI was not found. Install Docker Desktop to run VisionEval."
            return result
        try:
            info = self.runner([executable, "info", "--format", "{{json .}}"], capture_output=True, text=True, timeout=15)
            result["running"] = info.returncode == 0
            if info.returncode == 0:
                try:
                    result["dockerMemoryBytes"] = int(json.loads(info.stdout or "{}").get("MemTotal") or 0)
                except (ValueError, json.JSONDecodeError):
                    pass
            if info.returncode:
                result["error"] = (info.stderr or info.stdout).strip()
            inspect = self.runner([executable, "image", "inspect", self.image], capture_output=True, text=True, timeout=15)
            result["imagePresent"] = inspect.returncode == 0
            if result["imagePresent"]:
                result["imageDigest"] = self.image_digest()
                result["digestMatches"] = not self.expected_digest or result["imageDigest"] == self.expected_digest
                provenance = self.image_provenance()
                result["imageReleaseTag"] = provenance["releaseTag"]
                result["imageRevision"] = provenance["revision"]
                result["imageCompatibilityPatch"] = provenance["compatibilityPatch"]
                result["provenanceMatches"] = provenance["matches"]
                if self.expected_digest and not result["digestMatches"]:
                    result["error"] = "The saved runtime image digest has changed. Verify the runtime again before running models."
                elif not result["provenanceMatches"]:
                    result["error"] = "The runtime image does not match the verified Workbench VisionEval runtime. Rebuild or replace it before running models."
        except (OSError, subprocess.TimeoutExpired) as exc:
            result["error"] = str(exc)
        return result

    def _native_status(self) -> dict[str, Any]:
        self._prefer_installed_image()
        rscript = self.rscript or find_rscript_executable()
        runtime = self.native_runtime
        home = self.native_home
        present = bool(rscript and runtime and home and self.cli_path.is_file())
        error = ""
        if not rscript:
            error = "Rscript was not found. Choose the Rscript.exe used by this VisionEval installation."
        elif not runtime:
            error = "VE_RUNTIME was not found. Choose the folder used to start VisionEval."
        elif not home:
            error = "VE_HOME was not found. Choose the folder containing ve-lib."
        elif not self.cli_path.is_file():
            error = "The Workbench VisionEval command script is missing."
        provenance = native_runtime_provenance(home)
        return {
            "installed": bool(rscript), "running": present, "executable": rscript or "",
            "hostArchitecture": platform.machine(), "supported": platform.system() == "Windows",
            "image": str(home or ""), "imagePresent": present, "adapter": "native",
            "veRuntime": str(runtime or ""), "veHome": str(home or ""),
            "imageDigest": "", "digestMatches": True,
            "imageReleaseTag": provenance["releaseTag"], "imageRevision": provenance["revision"],
            "imageCompatibilityPatch": "", "provenanceMatches": provenance["releaseTag"] == RC7_RELEASE_TAG,
            "releaseCheck": self.release_status(), "dockerMemoryBytes": 0, "memoryLimitGb": self.memory_limit_gb,
            "remoteStatus": "local", "profileEnabled": self.runtime_enabled, "error": error,
        }

    def pull_image(self) -> dict[str, Any]:
        if self.adapter == "native":
            raise WorkspaceError("Native VisionEval is installed with the official Windows installer, not pulled as a Docker image.")
        executable = find_docker_executable()
        if not executable:
            raise WorkspaceError("Docker CLI was not found")
        if self.image.startswith("local/"):
            raise WorkspaceError("This local runtime alias cannot be pulled. Follow Runtime setup to pull and tag the matching image, then verify it.")
        result = self.runner([executable, "pull", self.image], capture_output=True, text=True)
        if result.returncode:
            raise WorkspaceError((result.stderr or result.stdout).strip() or "Docker image pull failed")
        return {"ok": True, "image": self.image, "digest": self.image_digest(), "output": result.stdout.strip()}

    @staticmethod
    def _install_progress(callback: Callable[..., None] | None, phase: str, message: str, **details: Any) -> None:
        if callback:
            callback(phase, message, **details)

    @staticmethod
    def _check_install_cancelled(cancel_event: threading.Event | None) -> None:
        if cancel_event and cancel_event.is_set():
            raise RuntimeInstallCancelled("Runtime installation was cancelled.")

    def _download_verified(
        self,
        url: str,
        destination: Path,
        expected_sha256: str,
        *,
        phase: str,
        progress: Callable[..., None] | None,
        cancel_event: threading.Event | None,
    ) -> None:
        if not url.lower().startswith("https://"):
            raise WorkspaceError("Managed runtime downloads require a pinned HTTPS URL.")
        request = urllib.request.Request(url, headers={"User-Agent": "VisionEval-Workbench/2.0.0"})
        digest = hashlib.sha256()
        received = 0
        try:
            with urllib.request.urlopen(request, timeout=45) as response, destination.open("wb") as handle:
                total = int(response.headers.get("Content-Length") or 0)
                while True:
                    self._check_install_cancelled(cancel_event)
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
                    digest.update(chunk)
                    received += len(chunk)
                    self._install_progress(
                        progress,
                        phase,
                        f"Downloading {destination.name}",
                        bytesReceived=received,
                        bytesTotal=total,
                        percent=round(received * 100 / total, 1) if total else None,
                    )
        except (OSError, urllib.error.URLError) as exc:
            raise WorkspaceError(f"Could not download {destination.name}: {exc}") from exc
        if digest.hexdigest().lower() != expected_sha256.lower():
            raise WorkspaceError(f"The checksum for {destination.name} does not match the certified manifest.")

    @staticmethod
    def _compatible_rscript() -> str | None:
        roots = [
            Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "Programs" / "R",
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "R",
        ]
        candidates = [os.environ.get("RSCRIPT", ""), shutil.which("Rscript") or ""]
        for root in roots:
            candidates.extend(str(path) for path in sorted(root.glob("R-4.5*/bin/Rscript.exe"), reverse=True))
            candidates.extend(str(path) for path in sorted(root.glob("R-4.5*/bin/x64/Rscript.exe"), reverse=True))
        for value in candidates:
            if value and Path(value).is_file() and re.search(r"R-4\.5(?:\.|[/\\])", str(Path(value))):
                return str(Path(value).resolve())
        return None

    @staticmethod
    def _safe_extract_runtime(archive: Path, destination: Path, cancel_event: threading.Event | None) -> Path:
        destination.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as bundle:
            root = destination.resolve()
            for member in bundle.infolist():
                RuntimeManager._check_install_cancelled(cancel_event)
                if (member.external_attr >> 16) & 0o170000 == 0o120000:
                    raise WorkspaceError("The VisionEval archive contains an unsupported symbolic link.")
                target = (destination / member.filename).resolve()
                try:
                    target.relative_to(root)
                except ValueError as exc:
                    raise WorkspaceError("The VisionEval archive contains an unsafe path.") from exc
                bundle.extract(member, destination)
        descriptions = sorted(destination.rglob("VEStart/DESCRIPTION"))
        if not descriptions:
            raise WorkspaceError("The VisionEval archive does not contain the VEStart package.")
        return descriptions[0].parent.parent

    @staticmethod
    def _write_native_runtime_files(runtime: Path, home: Path, rscript: Path) -> None:
        runtime.mkdir(parents=True, exist_ok=True)
        (runtime / "models").mkdir(exist_ok=True)
        runtime_text, home_text = runtime.as_posix(), home.as_posix()
        environment = f'VE_HOME="{home_text}"\nVE_RUNTIME="{runtime_text}"\n'
        (runtime / ".Renviron").write_text(environment, encoding="utf-8")
        home.mkdir(parents=True, exist_ok=True)
        (home / ".Renviron").write_text(environment, encoding="utf-8")
        (runtime / "r.version").write_text(f"R version {CERTIFIED_R_VERSION}\n", encoding="utf-8")
        profile = (
            've.home <- Sys.getenv("VE_HOME")\n'
            've.runtime <- Sys.getenv("VE_RUNTIME")\n'
            f'.libPaths(c(file.path(ve.home, "ve-lib", "{CERTIFIED_R_SERIES}"), .libPaths()))\n'
            'suppressPackageStartupMessages(library(VEStart))\n'
            'startVisionEval(ve.home=ve.home, ve.runtime=ve.runtime, overwrite=FALSE)\n'
        )
        (runtime / ".Rprofile").write_text(profile, encoding="utf-8")
        (runtime / "VisionEval.Rproj").write_text("Version: 1.0\nRestoreWorkspace: No\nSaveWorkspace: No\n", encoding="utf-8")
        r_home = rscript.parent.parent if rscript.parent.name.lower() == "bin" else rscript.parent.parent.parent
        launcher = (
            "@echo off\r\n"
            f"set R_HOME_BASE={r_home.as_posix()}\r\n"
            "if \"%R_HOME%\" == \"\" set R_HOME=%R_HOME_BASE%\r\n"
            "start \"\" \"%R_HOME%\\bin\\x64\\RGui.exe\" --no-save\r\n"
        )
        (runtime / f"launch_R{CERTIFIED_R_VERSION}.bat").write_text(launcher, encoding="utf-8")
        release = (
            "repository=https://github.com/VisionEval/VisionEval-4\n"
            f"tag={RC7_RELEASE_TAG}\ncommit={RC7_RELEASE_COMMIT}\n"
            f"r_version={CERTIFIED_R_VERSION}\ndistribution=official-visioneval-windows-library\n"
            "compatibility_patch=none\n"
        )
        (home / "WORKBENCH-RELEASE").write_text(release, encoding="utf-8")

    def _install_native_runtime(
        self,
        options: dict[str, Any] | None,
        progress: Callable[..., None] | None,
        cancel_event: threading.Event | None,
    ) -> dict[str, Any]:
        if platform.system() != "Windows":
            raise WorkspaceError("The managed native installer is available only on Windows.")
        with self.lock:
            if self._unfinished_jobs_locked():
                raise WorkspaceError("Finish or stop all active and waiting runs before changing the runtime.")
        options = options or {}
        local_app_data = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
        runtime, home = validate_native_path_separation(
            options.get("veRuntime") or local_app_data / "VisionEval" / "VE_Runtime",
            options.get("veHome") or Path.home() / "VE_Home",
        )
        work_root = local_app_data / "VisionEval" / "Workbench" / "install"
        work_root.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix="runtime-", dir=work_root))
        previous_library: Path | None = None
        installed_library = False
        target_library = home / "ve-lib" / CERTIFIED_R_SERIES
        managed_files = [
            runtime / ".Renviron", runtime / ".Rprofile", runtime / "r.version",
            runtime / "VisionEval.Rproj", runtime / f"launch_R{CERTIFIED_R_VERSION}.bat",
            home / ".Renviron", home / "WORKBENCH-RELEASE",
        ]
        file_backups = {path: path.read_bytes() if path.is_file() else None for path in managed_files}
        try:
            self._check_install_cancelled(cancel_event)
            rscript_text = self._compatible_rscript()
            reused_r = bool(rscript_text)
            if not rscript_text:
                installer = temporary / CERTIFIED_R_INSTALLER_NAME
                self._download_verified(
                    CERTIFIED_R_INSTALLER_URL,
                    installer,
                    CERTIFIED_R_INSTALLER_SHA256,
                    phase="downloading-r",
                    progress=progress,
                    cancel_event=cancel_event,
                )
                r_root = local_app_data / "Programs" / "R" / f"R-{CERTIFIED_R_VERSION}"
                self._install_progress(progress, "installing-r", f"Installing R {CERTIFIED_R_VERSION} for the current user.")
                process = subprocess.Popen([
                    str(installer), "/CURRENTUSER", "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", f"/DIR={r_root}"
                ])
                while process.poll() is None:
                    if cancel_event and cancel_event.wait(0.25):
                        self._terminate_native_tree(process, timeout=5)
                        raise RuntimeInstallCancelled("Runtime installation was cancelled.")
                if process.returncode:
                    raise WorkspaceError(f"R {CERTIFIED_R_VERSION} installation failed with exit code {process.returncode}.")
                rscript_text = find_rscript_executable(str(r_root / "bin" / "Rscript.exe"))
                if not rscript_text:
                    raise WorkspaceError(f"R {CERTIFIED_R_VERSION} installed, but Rscript.exe was not found.")
            else:
                self._install_progress(progress, "reusing-r", "Using the existing compatible R 4.5 installation.")

            archive = temporary / CERTIFIED_VE_ARCHIVE_NAME
            self._download_verified(
                CERTIFIED_VE_ARCHIVE_URL,
                archive,
                CERTIFIED_VE_ARCHIVE_SHA256,
                phase="downloading-visioneval",
                progress=progress,
                cancel_event=cancel_event,
            )
            self._install_progress(progress, "extracting-visioneval", f"Installing VisionEval {RC7_RELEASE_TAG}.")
            package_root = self._safe_extract_runtime(archive, temporary / "extracted", cancel_event)
            staged_library = home / "ve-lib" / f".{CERTIFIED_R_SERIES}.installing-{make_id('ve', 'rc7')}"
            staged_library.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(package_root, staged_library)
            self._check_install_cancelled(cancel_event)
            if target_library.exists():
                previous_library = target_library.with_name(f".{CERTIFIED_R_SERIES}.previous-{make_id('ve', 'backup')}")
                target_library.replace(previous_library)
            staged_library.replace(target_library)
            installed_library = True
            self._write_native_runtime_files(runtime, home, Path(rscript_text))
            self.native_runtime, self.native_home, self.rscript = runtime, home, str(Path(rscript_text).resolve())
            self.image = str(home)
            self._install_progress(progress, "verifying", "Verifying the installed VisionEval runtime.")
            result = self.verify_runtime()
            if result.get("revision") != RC7_RELEASE_COMMIT:
                raise WorkspaceError("The installed VisionEval packages do not match the certified RC7 commit.")
            if previous_library and previous_library.exists():
                shutil.rmtree(previous_library)
            return {
                **result,
                "managed": True,
                "source": CERTIFIED_VE_ARCHIVE_URL,
                "rReused": reused_r,
            }
        except Exception:
            if previous_library and previous_library.exists():
                if target_library.exists():
                    shutil.rmtree(target_library, ignore_errors=True)
                previous_library.replace(target_library)
            elif installed_library and target_library.exists():
                shutil.rmtree(target_library, ignore_errors=True)
            for path, content in file_backups.items():
                if content is None:
                    path.unlink(missing_ok=True)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(content)
            raise
        finally:
            shutil.rmtree(temporary, ignore_errors=True)
            try:
                work_root.rmdir()
            except OSError:
                pass

    def install_or_update_runtime(
        self,
        profile: dict[str, Any] | None = None,
        *,
        options: dict[str, Any] | None = None,
        progress: Callable[..., None] | None = None,
        cancel_event: threading.Event | None = None,
    ) -> dict[str, Any]:
        """Atomically install and activate a manifest-approved runtime."""
        if self.adapter == "native":
            return self._install_native_runtime(options, progress, cancel_event)
        if platform.system() != "Darwin" or self.container_platform != "linux/arm64":
            raise WorkspaceError("The managed runtime installer supports Apple Silicon macOS only.")
        executable = find_docker_executable()
        if not executable:
            raise WorkspaceError("Docker CLI was not found. Install Docker Desktop, then choose Install runtime again.")
        environment = docker_command_env()
        info = self.runner(
            [executable, "info", "--format", "{{json .}}"],
            capture_output=True,
            text=True,
            timeout=15,
            env=environment,
        )
        if info.returncode:
            raise WorkspaceError("Docker Desktop is not running. Start Docker Desktop, then choose Install runtime again.")
        with self.lock:
            if self._unfinished_jobs_locked():
                raise WorkspaceError("Finish or stop all active and waiting runs before changing the runtime.")
        target = self._validate_runtime_profile(profile, allow_legacy=True) if profile else dict(PINNED_RUNTIME_PROFILE)
        target_reference = str(target["reference"])
        pull = self.runner(
            [executable, "pull", "--platform", "linux/arm64", target_reference],
            capture_output=True,
            text=True,
            env=environment,
        )
        if pull.returncode:
            raise WorkspaceError((pull.stderr or pull.stdout).strip() or "Runtime image download failed")
        old_active = dict(self.active_runtime_profile)
        old_previous = dict(self.previous_runtime_profile) if self.previous_runtime_profile else None
        old_image, old_digest = self.image, self.expected_digest
        self.image = target_reference
        self.expected_digest = str(target["digest"])
        self.active_runtime_profile = target
        try:
            verification = self.verify_runtime()
        except Exception:
            with self.condition:
                self.image = old_image
                self.expected_digest = old_digest
                self.active_runtime_profile = old_active
                self.previous_runtime_profile = old_previous
            raise
        if verification.get("digest") != target["digest"]:
            self.image = old_image
            self.expected_digest = old_digest
            self.active_runtime_profile = old_active
            self.previous_runtime_profile = old_previous
            raise WorkspaceError("The downloaded runtime digest does not match the approved runtime profile.")
        if old_active.get("digest") != target.get("digest"):
            self.previous_runtime_profile = old_active
        self._save_runtime_profiles()
        if old_previous and old_previous.get("digest") not in {target.get("digest"), self.previous_runtime_profile.get("digest") if self.previous_runtime_profile else ""}:
            self._remove_owned_runtime_image(old_previous)
        return {
            **verification,
            "source": target_reference,
            "sourceTag": target_reference,
            "activeProfile": target,
            "previousProfile": self.previous_runtime_profile,
            "pullOutput": ((pull.stdout or "") + (pull.stderr or "")).strip(),
        }

    def _remove_owned_runtime_image(self, profile: dict[str, Any]) -> None:
        reference = str(profile.get("reference") or "")
        if not reference.startswith(f"{RUNTIME_REPOSITORY}@sha256:"):
            return
        executable = find_docker_executable()
        if not executable:
            return
        labels = self.runner([executable, "image", "inspect", "--format", "{{json .Config.Labels}}", reference], capture_output=True, text=True)
        if labels.returncode:
            return
        try:
            values = json.loads(labels.stdout or "{}") or {}
        except json.JSONDecodeError:
            return
        if values.get("org.opencontainers.image.source") != "https://github.com/nikolasleeb/VisionEval-Workbench":
            return
        self.runner([executable, "image", "rm", reference], capture_output=True, text=True)

    def restore_previous_runtime(self) -> dict[str, Any]:
        if self.adapter == "native" or not self.previous_runtime_profile:
            raise WorkspaceError("No previous verified Docker runtime is available.")
        with self.lock:
            if self._unfinished_jobs_locked():
                raise WorkspaceError("Finish or stop all active and waiting runs before restoring the previous runtime.")
        target = dict(self.previous_runtime_profile)
        current = dict(self.active_runtime_profile)
        self.image = str(target["reference"])
        self.expected_digest = str(target["digest"])
        self.active_runtime_profile = target
        verification = self.verify_runtime()
        self.previous_runtime_profile = current
        self._save_runtime_profiles()
        return {**verification, "activeProfile": target, "previousProfile": current, "restored": True}

    def image_digest(self) -> str:
        if self.adapter == "native":
            return ""
        executable = find_docker_executable()
        if not executable:
            return ""
        result = self.runner([executable, "image", "inspect", "--format", "{{if .RepoDigests}}{{join .RepoDigests \"|\"}}{{else}}{{.Id}}{{end}}", self.image], capture_output=True, text=True)
        if result.returncode:
            return ""
        digests = [item for item in result.stdout.strip().split("|") if "@sha256:" in item]
        if digests:
            return digests[0].split("@", 1)[1]
        identifier = result.stdout.strip()
        return identifier if identifier.startswith("sha256:") else ""

    def image_provenance(self) -> dict[str, Any]:
        if self.adapter == "native":
            return {"releaseTag": "", "revision": "", "compatibilityPatch": "", "matches": True}
        executable = find_docker_executable()
        if not executable:
            return {"releaseTag": "", "revision": "", "compatibilityPatch": "", "matches": False}
        result = self.runner(
            [executable, "image", "inspect", "--format", "{{json .Config.Labels}}", self.image],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode:
            return {"releaseTag": "", "revision": "", "compatibilityPatch": "", "matches": False}
        try:
            labels = json.loads(result.stdout or "{}") or {}
        except json.JSONDecodeError:
            labels = {}
        # The generic OCI version/revision describe the Workbench image build.
        # VisionEval source provenance is carried in its own labels so an image
        # can truthfully identify both the Workbench build and upstream commit.
        release_tag = str(labels.get("com.visioneval.upstream.release") or "")
        revision = str(labels.get("com.visioneval.upstream.revision") or "")
        compatibility_patch = str(labels.get("com.visioneval.workbench.compatibility-patch") or "")
        try:
            runtime_api = int(labels.get("com.visioneval.workbench.runtime-api") or 0)
        except (TypeError, ValueError):
            runtime_api = -1
        expected = self.active_runtime_profile
        return {
            "releaseTag": release_tag,
            "revision": revision,
            "compatibilityPatch": compatibility_patch,
            "runtimeApi": runtime_api,
            "matches": (
                release_tag == expected.get("visionEvalVersion")
                and revision == expected.get("visionEvalCommit")
                and compatibility_patch == expected.get("compatibilityPatch", "none")
                and (runtime_api == expected.get("runtimeApi") or expected.get("runtimeApi") == 0)
            ),
        }

    def _container_resource_args(self) -> list[str]:
        return ["--memory", f"{self.memory_limit_gb:g}g"] if self.memory_limit_gb else []

    def verify_runtime(self) -> dict[str, Any]:
        if self.adapter == "native":
            return self._verify_native_runtime()
        executable = find_docker_executable()
        if not executable:
            raise WorkspaceError("Docker CLI was not found")
        provenance = self.image_provenance()
        if not provenance["matches"]:
            raise WorkspaceError(
                f"Runtime provenance mismatch. Expected {self.active_runtime_profile.get('visionEvalVersion')} at {self.active_runtime_profile.get('visionEvalCommit')}; "
                f"found {provenance['releaseTag'] or 'no release label'} at {provenance['revision'] or 'no revision label'}."
            )
        outputs = {}
        for command in self.active_runtime_profile.get("verificationCommands") or ("doctor", "verify-upstream-release"):
            result = self.runner(
                [executable, "run", "--rm", "--platform", self.container_platform, *self._container_resource_args(), *self._workspace_mount_args(), self.image, command],
                capture_output=True,
                text=True,
            )
            outputs[command] = {"ok": result.returncode == 0, "output": (result.stdout + result.stderr).strip()}
            if result.returncode:
                raise WorkspaceError(f"Runtime {command} failed: {outputs[command]['output']}")
        digest = self.image_digest()
        with self.condition:
            # A successful verification establishes the digest trusted for the
            # remainder of this backend session. The desktop persists the same
            # value for future launches.
            self.expected_digest = digest
            self.runtime_enabled = True
            self.condition.notify_all()
        return {"ok": True, "adapter": self.adapter, "platform": platform.system().lower(), "architecture": platform.machine(), "image": self.image, "digest": digest, "runtimeVersion": f"VisionEval {provenance['releaseTag']} / R 4.5.1", "releaseTag": provenance["releaseTag"], "revision": provenance["revision"], "runtimeApi": provenance.get("runtimeApi", 0), "compatibilityPatch": provenance["compatibilityPatch"], "verifiedAt": now_iso(), "checks": outputs}

    def _verify_native_runtime(self) -> dict[str, Any]:
        outputs = {}
        runtime_info: dict[str, Any] = {}
        for command in ("doctor", "verify-capabilities"):
            invocation, environment = self._native_command(command)
            result = self.runner(invocation, capture_output=True, text=True, env=environment)
            output = ((result.stdout or "") + (result.stderr or "")).strip()
            outputs[command] = {"ok": result.returncode == 0, "output": output}
            if result.returncode:
                raise WorkspaceError(f"Runtime {command} failed: {output}")
            if command == "verify-capabilities":
                info_line = next((line for line in output.splitlines() if line.startswith("WORKBENCH_RUNTIME_INFO|")), "")
                if info_line:
                    fields = dict(part.split("=", 1) for part in info_line.split("|")[1:] if "=" in part)
                    packages = dict(part.split("=", 1) for part in fields.get("Packages", "").split(";") if "=" in part)
                    runtime_info = {
                        "visionEvalVersion": fields.get("VisionEval", "unknown"),
                        "rVersion": fields.get("R", "unknown"),
                        "packageVersions": packages,
                    }
        provenance = native_runtime_provenance(self.native_home)
        if provenance["revision"] != RC7_RELEASE_COMMIT:
            found = provenance["revision"] or "no VECommit metadata"
            raise WorkspaceError(
                f"VisionEval provenance mismatch. Expected {RC7_RELEASE_TAG} at {RC7_RELEASE_COMMIT}; found {found}."
            )
        with self.condition:
            self.runtime_enabled = True
            self.condition.notify_all()
        return {
            "ok": True, "adapter": "native", "platform": platform.system().lower(), "architecture": platform.machine(),
            "image": str(self.native_home), "veHome": str(self.native_home), "veRuntime": str(self.native_runtime),
            "rscript": self.rscript or find_rscript_executable(), "digest": "",
            "runtimeVersion": f"VisionEval {RC7_RELEASE_TAG} / R {runtime_info.get('rVersion', 'unknown')}",
            **runtime_info,
            "releaseTag": RC7_RELEASE_TAG, "revision": provenance["revision"],
            "packageVersion": provenance["packageVersion"], "compatibilityPatch": "none",
            "verifiedAt": now_iso(), "checks": outputs,
        }

    @staticmethod
    def _csv_header(path: Path) -> list[str]:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return next(csv.reader(handle), [])

    def validate_project(self, project_id: str) -> dict[str, Any]:
        _, project = self.workspace.project(project_id)
        template_path, _ = self.workspace.template(project["template"]["id"])
        library = self.workspace.input_library / project["inputLibrary"]["id"]
        errors, warnings = [], []
        region_manifest = read_json(template_path / "region_builder_manifest.json", {})
        if region_manifest.get("selection", {}).get("method") == "package-statewide" or region_manifest.get("region", {}).get("regionType") == "statewide":
            errors.append("Virginia statewide execution is not supported. Create an MPO-sized regional project instead.")
        input_consistency_errors: list[dict[str, Any]] = []
        template_files = {p.name: p for p in (template_path / "inputs").iterdir() if p.is_file()}
        library_files = {p.name: p for p in library.iterdir() if p.is_file()}
        for name, template_file in template_files.items():
            candidate = library_files.get(name)
            if candidate is None:
                warnings.append(f"Using template default because the input library does not contain {name}")
                continue
            if name.lower().endswith(".csv"):
                try:
                    expected, actual = self._csv_header(template_file), self._csv_header(candidate)
                    if expected != actual:
                        errors.append(f"CSV columns do not match the template for {name}")
                except (OSError, csv.Error) as exc:
                    errors.append(f"Could not read {name}: {exc}")
        config = (template_path / "visioneval.cnf").read_text(encoding="utf-8", errors="replace")
        years_match = re.search(r"(?m)^\s*Years\s*:\s*\[([^]]+)\]", config)
        configured_years = {item.strip().strip("'\"") for item in years_match.group(1).split(",")} if years_match else set()
        geo_values: dict[str, set[str]] = {}
        geo_path = template_path / "defs" / "geo.csv"
        if geo_path.is_file():
            with geo_path.open("r", encoding="utf-8-sig", newline="") as handle:
                for row in csv.DictReader(handle):
                    for level in ("Azone", "Bzone", "Marea"):
                        value = str(row.get(level, "")).strip()
                        if value and value.upper() != "NA":
                            geo_values.setdefault(level.lower(), set()).add(value)
        for name, candidate in library_files.items():
            if not name.lower().endswith(".csv"):
                continue
            try:
                with candidate.open("r", encoding="utf-8-sig", newline="") as handle:
                    reader = csv.DictReader(handle)
                    rows = list(reader)
                    field_map = {field.lower(): field for field in (reader.fieldnames or [])}
                year_field = field_map.get("year")
                if year_field and configured_years:
                    unexpected = sorted({str(row.get(year_field, "")).strip() for row in rows} - configured_years - {""})
                    if unexpected:
                        errors.append(f"{name} contains years not configured by the model: {', '.join(unexpected[:5])}")
                level = next((item for item in ("azone", "bzone", "marea") if name.lower().startswith(item + "_")), "")
                geo_field = field_map.get("geo")
                if level and geo_field and geo_values.get(level):
                    unexpected_geo = {str(row.get(geo_field, "")).strip() for row in rows} - geo_values[level] - {""}
                    if unexpected_geo:
                        errors.append(f"{name} contains {len(unexpected_geo)} geography values absent from defs/geo.csv")
            except (OSError, csv.Error) as exc:
                errors.append(f"Could not validate {name}: {exc}")
        for variant in project["variations"]:
            for overlay in variant.get("overlays", []):
                try:
                    original = library / overlay["fileName"]
                    edited = Path(overlay["path"])
                    if self._csv_header(original) != self._csv_header(edited):
                        errors.append(f"Edited columns changed in {variant['name']} / {overlay['fileName']}")
                except (OSError, csv.Error) as exc:
                    errors.append(f"Invalid overlay for {variant['name']}: {exc}")
        template_inputs = template_path / "inputs"
        effective_transit_paths = {
            filename: (library / filename if (library / filename).is_file() else template_inputs / filename)
            for filename in FILE_GROUPS
            if (library / filename).is_file() or (template_inputs / filename).is_file()
        }
        baseline_transit_errors = validate_transit_inputs(library, effective_transit_paths, scenario="Baseline")
        input_consistency_errors.extend(baseline_transit_errors)
        for variant in project["variations"]:
            overlay_paths = {
                str(overlay.get("fileName", "")): Path(str(overlay.get("path", "")))
                for overlay in variant.get("overlays", [])
                if str(overlay.get("fileName", "")) in FILE_GROUPS
            }
            if overlay_paths:
                input_consistency_errors.extend(validate_transit_inputs(
                    library,
                    {**effective_transit_paths, **overlay_paths},
                    str(variant.get("name", "Scenario")),
                ))
        errors.extend(item["message"] for item in input_consistency_errors)
        return {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
            "inputConsistencyErrors": input_consistency_errors,
        }

    def list_jobs(self, project_id: str = "", include_archived: bool = False) -> list[dict[str, Any]]:
        jobs = [read_json(path, {}) for path in self.workspace.runs.glob("*/job.json")]
        active = self.workspace.active_project_ids()
        output = [
            job for job in jobs
            if job and (include_archived or job.get("projectId") in active) and (not project_id or job.get("projectId") == project_id)
        ]
        active_jobs = sorted((item for item in output if item.get("state") in ACTIVE_STATES), key=lambda item: item.get("startedAt") or item.get("createdAt", ""))
        waiting_jobs = sorted((item for item in output if item.get("state") == "waiting"), key=lambda item: (item.get("queuePosition", 10**12), item.get("createdAt", "")))
        history = sorted((item for item in output if item.get("state") not in ACTIVE_STATES | {"waiting"}), key=lambda item: item.get("finishedAt") or item.get("createdAt", ""), reverse=True)
        return active_jobs + waiting_jobs + history

    def job(self, job_id: str) -> dict[str, Any]:
        path = self.workspace.within(self.workspace.runs / job_id / "job.json", self.workspace.runs)
        job = read_json(path, {})
        if job.get("id") != job_id:
            raise WorkspaceError("Unknown run")
        return job

    def _save_job(self, job: dict[str, Any], **updates: Any) -> dict[str, Any]:
        with self.lock:
            job.update(updates)
            write_json(self.workspace.runs / job["id"] / "job.json", job)
        return job

    def create_batch(
        self, project_id: str, variation_ids: list[str], include_baseline: bool, mode: str,
        force_rerun_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        with self.workspace.activity_lock:
            self.workspace.assert_run_start_allowed(project_id, variation_ids)
            return self._create_batch_locked(
                project_id, variation_ids, include_baseline, mode, force_rerun_ids,
            )

    def _create_batch_locked(
        self, project_id: str, variation_ids: list[str], include_baseline: bool, mode: str,
        force_rerun_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        with self.condition:
            if self.stop_all_in_progress:
                raise WorkspaceError("Wait for Stop All to finish before starting new runs")
        if mode not in {"queued", "parallel"}:
            raise WorkspaceError("Run mode must be queued or parallel")
        if self.adapter == "native":
            mode = "queued"
        validation = self.validate_project(project_id)
        if not validation["valid"]:
            raise WorkspaceError("Project is not runnable: " + "; ".join(validation["errors"]))
        _, project = self.workspace.project(project_id)
        image_digest = self.image_digest()
        if not include_baseline and not self.workspace.current_result(project, "baseline", image_digest):
            raise WorkspaceError("Run the baseline first for this exact model package and Input Library")
        available = {item["id"]: item for item in project["variations"]}
        selected = []
        reused_results = []
        force = {str(item) for item in (force_rerun_ids or [])}
        if include_baseline:
            reusable = None if "baseline" in force else self.workspace.current_result(project, "baseline", image_digest)
            if reusable:
                reused_results.append({"variationId": "baseline", "datastoreId": reusable["id"]})
            else:
                selected.append(("baseline", "Baseline", True))
        for variation_id in variation_ids:
            if variation_id not in available:
                raise WorkspaceError("Unknown project variation")
            reusable = None if variation_id in force else self.workspace.current_result(project, variation_id, image_digest)
            if reusable:
                reused_results.append({"variationId": variation_id, "datastoreId": reusable["id"]})
            else:
                selected.append((variation_id, available[variation_id]["name"], False))
        if not selected and not reused_results:
            raise WorkspaceError("Select at least one run")
        batch_id = make_id("batch", project["name"])
        if not selected:
            return {
                "id": batch_id, "mode": mode, "projectId": project_id, "jobIds": [],
                "createdAt": now_iso(), "jobs": [], "reusedResults": reused_results,
                "validation": validation,
            }
        jobs = []
        with self.condition:
            if self.stop_all_in_progress:
                raise WorkspaceError("Wait for Stop All to finish before starting new runs")
            if project_id in self.stopping_projects:
                raise WorkspaceError("Wait for this project's runs to finish stopping before starting new work")
            waiting = self._normalize_queue_locked()
            queue_state = self._queue_state()
            next_position = len(waiting) + 1
            revision = int(queue_state.get("revision", 0)) + 1
            result_retention_mode = (
                "datastore_only"
                if project.get("projectType") == "hypercube"
                else "datastore_and_csv" if self.workspace.settings().get("retainFullExports", True) else "datastore_only"
            )
            for index, (variation_id, variation_name, baseline) in enumerate(selected):
                job_id = make_id("run", variation_name)
                directory = self.workspace.runs / job_id
                directory.mkdir()
                job = {
                    "version": RUN_VERSION,
                    "id": job_id,
                    "batchId": batch_id,
                    "batchMode": mode,
                    "projectId": project_id,
                    "projectName": project["name"],
                    "variationId": variation_id,
                    "variationName": variation_name,
                    "baseline": baseline,
                    "templateId": project["template"]["id"],
                    "templateFingerprint": project["template"]["fingerprint"],
                    "inputLibraryId": project["inputLibrary"]["id"],
                    "inputLibraryFingerprint": project["inputLibrary"].get("fingerprint", ""),
                    "image": self.image,
                    "imageDigest": image_digest,
                    "inputStateFingerprint": self.workspace.scenario_input_fingerprint(project, variation_id),
                    "resultRetentionMode": result_retention_mode,
                    "containerId": "",
                    "containerName": f"ve-{job_id}",
                    "executionAttempt": "",
                    "state": "waiting",
                    "message": "Waiting to run",
                    "createdAt": now_iso(),
                    "startedAt": "",
                    "finishedAt": "",
                    "exitCode": None,
                    "logPath": str(directory / "run.log"),
                    "modelPath": str(self.workspace.models / job_id),
                    "resultPath": "",
                    "verification": "pending",
                    "queuePosition": next_position + index,
                    "queueRevision": revision,
                }
                write_json(directory / "job.json", job)
                (directory / "run.log").touch()
                jobs.append(job)
            # The dispatcher also holds this condition while reading waiting jobs.
            # Publish the batch mode before releasing it so queued jobs can never
            # be observed without their serial-execution policy.
            batch = {"id": batch_id, "mode": mode, "projectId": project_id, "jobIds": [job["id"] for job in jobs], "createdAt": now_iso()}
            write_json(self.workspace.runs / f"{batch_id}.json", batch)
        project["runIds"].extend(job["id"] for job in jobs)
        self.workspace.save_project(project)
        with self.condition:
            self._write_queue_state_locked(revision, self._mode_lock_locked())
            self._normalize_queue_locked()
            self.condition.notify_all()
        return {**batch, "jobs": jobs, "reusedResults": reused_results, "validation": validation}

    def _append_log(self, job: dict[str, Any], text: str) -> None:
        with open(job["logPath"], "a", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()

    def _mirror_model_log(self, model_path: Path, job: dict[str, Any], stop: threading.Event) -> None:
        active_path: Path | None = None
        offset = 0
        while not stop.is_set():
            candidates = sorted((model_path / "results").glob("Log_*.txt"), key=lambda path: path.stat().st_mtime)
            if candidates:
                latest = candidates[-1]
                if latest != active_path:
                    active_path, offset = latest, 0
                    self._append_log(job, f"\n--- VisionEval model log: {latest.name} ---\n")
                with latest.open("r", encoding="utf-8", errors="replace") as handle:
                    handle.seek(offset)
                    text = handle.read()
                    offset = handle.tell()
                if text:
                    self._append_log(job, text)
            stop.wait(0.75)
        if active_path and active_path.exists():
            with active_path.open("r", encoding="utf-8", errors="replace") as handle:
                handle.seek(offset)
                text = handle.read()
            if text:
                self._append_log(job, text)

    def _finalize_success(self, job_id: str, executable: str) -> None:
        job = self.job(job_id); model_path = Path(job["modelPath"])
        datastore = model_path / "results" / "Datastore"
        if not (datastore / "DatastoreListing.Rda").is_file():
            raise RunFailure(
                "VisionEval finished without creating a complete result datastore. Review the final model stages in the run log before retrying.",
                kind="incomplete_results",
                technical_detail="Run finished but DatastoreListing.Rda was not created",
                recommended_action="Review the end of the run log and export diagnostics before retrying.",
            )
        retention_mode = str(job.get("resultRetentionMode") or "datastore_and_csv")
        if retention_mode == "datastore_and_csv":
            self._save_job(job, state="exporting", message="Exporting full CSV results")
            environment = None
            if self.adapter == "native":
                export, environment = self._native_command("export", str(model_path))
            else:
                export = [executable, "run", "--rm", "--platform", self.container_platform, *self._container_resource_args(), *self._workspace_mount_args(), self.image, "export", job_id]
            with open(job["logPath"], "a", encoding="utf-8") as log:
                export_process = subprocess.Popen(
                    export,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    text=True,
                    env=environment,
                    creationflags=self._native_creation_flags() if self.adapter == "native" else 0,
                )
                with self.lock:
                    self.processes[job_id] = export_process
                while export_process.poll() is None:
                    if job_id in self.cancelled:
                        self._terminate_native_tree(export_process)
                        break
                    time.sleep(.25)
                export_code = export_process.wait()
                with self.lock:
                    self.processes.pop(job_id, None)
            if job_id in self.cancelled:
                self._cleanup_cancelled_job(job_id)
                return
            if export_code:
                raise RunFailure(
                    "VisionEval finished, but Workbench could not export its results. Review the run log, then retry.",
                    kind="export",
                    exit_code=export_code,
                    technical_detail=f"Result export exited with code {export_code}",
                    recommended_action="Review the export section of the run log and export diagnostics before retrying.",
                )
        else:
            self._append_log(job, "Workbench retained the authoritative Datastore and skipped the optional full CSV export.\n")
        if job_id in self.cancelled:
            self._cleanup_cancelled_job(job_id); return
        record = self.workspace.register_datastore({
            "label": f"{job['projectName']} — {job['variationName']}", "path": str(datastore),
            "role": "baseline" if job["baseline"] else "scenario", "projectId": job["projectId"],
            "projectName": job["projectName"], "variationId": job["variationId"], "variationName": job["variationName"],
            "templateId": job["templateId"], "templateFingerprint": job["templateFingerprint"],
            "inputLibraryId": job.get("inputLibraryId", ""), "inputLibraryFingerprint": job.get("inputLibraryFingerprint", ""),
            "runtimeImage": self.image, "completedAt": now_iso(), "verification": "verified", "runId": job_id,
            "runtimeImageDigest": job.get("imageDigest", ""),
            "inputStateFingerprint": job.get("inputStateFingerprint", ""),
            "executionFingerprint": self.workspace.execution_fingerprint(
                str(job.get("inputStateFingerprint", "")), str(job.get("imageDigest", ""))
            ),
            "resultVersion": 1,
        })
        job = self.job(job_id)
        self._save_job(job, state="succeeded", message="Run completed", exitCode=0, finishedAt=now_iso(), resultPath=str(datastore), verification="verified", datastoreId=record["id"], resultRetentionMode=retention_mode)

    def export_model_results(
        self,
        model_path: str | Path,
        log_path: str | Path,
        cancelled: Callable[[], bool] | None = None,
    ) -> None:
        """Generate disposable CSV outputs for a prepared model copy."""
        model = self.workspace.within(Path(model_path), self.workspace.models)
        log = Path(log_path)
        environment = None
        if self.adapter == "native":
            command, environment = self._native_command("export", str(model))
        else:
            executable = find_docker_executable()
            if not executable:
                raise WorkspaceError("Docker is not available for CSV export")
            command = [
                executable, "run", "--rm", "--platform", self.container_platform,
                *self._container_resource_args(), *self._workspace_mount_args(), self.image,
                "export", model.name,
            ]
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8") as handle:
            process = subprocess.Popen(
                command,
                stdout=handle,
                stderr=subprocess.STDOUT,
                text=True,
                env=environment,
                creationflags=self._native_creation_flags(),
            )
            while process.poll() is None:
                if cancelled and cancelled():
                    self._terminate_native_tree(process)
                    raise WorkspaceError("Hypercube case export cancelled")
                time.sleep(.25)
        if process.returncode:
            raise WorkspaceError(f"VisionEval CSV export exited with code {process.returncode}")

    def _run_job(self, job_id: str) -> None:
        with self.lock:
            job = self.job(job_id)
            if job.get("state") != "waiting":
                return
            if job_id in self.cancelled:
                self._cleanup_cancelled_job(job_id)
                return
            attempt_id = make_id("attempt")
            job.update(
                state="preparing",
                message="Preparing runnable model",
                startedAt=now_iso(),
                executionAttempt=attempt_id,
                workspaceId=self.workspace_id,
            )
            write_json(self.workspace.runs / job_id / "job.json", job)
        exit_code: int | None = None
        container_state: dict[str, Any] = {}
        executable = ""
        try:
            model_path, provenance = self.workspace.prepare_model(job["projectId"], job["variationId"], job_id, job["baseline"])
            if job_id in self.cancelled:
                self._cleanup_cancelled_job(job_id)
                return
            job = self.job(job_id)
            self._append_log(job, f"Prepared {provenance['variationName']} from template {provenance['templateId']}\n")
            environment = None
            if self.adapter == "native":
                preflight, preflight_environment = self._native_command("verify-model", str(model_path))
                with open(job["logPath"], "a", encoding="utf-8") as log:
                    preflight_result = subprocess.run(preflight, stdout=log, stderr=subprocess.STDOUT, text=True, env=preflight_environment)
                if preflight_result.returncode:
                    raise RunFailure(
                        "The selected VisionEval runtime is not compatible with this model. Review the run log for missing packages or modules.",
                        kind="runtime_incompatible",
                        exit_code=preflight_result.returncode,
                        technical_detail=f"Model preflight exited with code {preflight_result.returncode}",
                        recommended_action="Verify the runtime in Settings and correct the missing package or module before retrying.",
                    )
                command, environment = self._native_command("run", str(model_path))
                executable = command[0]
            else:
                executable = find_docker_executable()
                if not executable:
                    raise RunFailure(
                        "Docker could not be found. Start or install Docker Desktop, verify the runtime, and retry.",
                        kind="docker_unavailable",
                        technical_detail="Docker CLI was not found",
                        recommended_action="Open Runtime Setup, start Docker Desktop, and verify the runtime before retrying.",
                    )
                command = [
                    executable, "run", "--platform", self.container_platform, *self._container_resource_args(), "--name", job["containerName"],
                    "--label", "com.visioneval.workbench=true",
                    "--label", f"com.visioneval.workspace={self.workspace_id}",
                    "--label", f"com.visioneval.job={job_id}",
                    "--label", f"com.visioneval.attempt={attempt_id}",
                    *self._workspace_mount_args(), self.image, "run", job_id,
                ]
            self._save_job(job, state="running", message="VisionEval is running")
            mirror_stop = threading.Event()
            mirror = threading.Thread(target=self._mirror_model_log, args=(model_path, job, mirror_stop), daemon=True, name=f"log-{job_id}")
            mirror.start()
            try:
                with open(job["logPath"], "a", encoding="utf-8") as log:
                    process = subprocess.Popen(
                        command,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        text=True,
                        env=environment,
                        creationflags=self._native_creation_flags() if self.adapter == "native" else 0,
                    )
                    with self.lock:
                        self.processes[job_id] = process
                    if self.adapter == "native":
                        job = self.job(job_id)
                        self._save_job(job, containerId=f"pid:{process.pid}", containerName="")
                    else:
                        for _ in range(20):
                            inspected = subprocess.run([executable, "inspect", "--format", "{{.Id}}", job["containerName"]], capture_output=True, text=True)
                            if inspected.returncode == 0 and inspected.stdout.strip():
                                job = self.job(job_id)
                                self._save_job(job, containerId=inspected.stdout.strip())
                                break
                            if process.poll() is not None:
                                break
                            time.sleep(0.1)
                    exit_code = process.wait()
            finally:
                mirror_stop.set()
                mirror.join(timeout=3)
            with self.lock:
                self.processes.pop(job_id, None)
            job = self.job(job_id)
            if job_id in self.cancelled:
                self._cleanup_cancelled_job(job_id)
                return
            if self.adapter == "docker":
                container_state = self._container_state(job, executable)
                self._remove_owned_container(job, executable)
            if exit_code:
                raise self._execution_failure(exit_code, container_state)
            self._finalize_success(job_id, executable)
        except Exception as exc:
            if job_id in self.cancelled:
                self._cleanup_cancelled_job(job_id)
                return
            job = self.job(job_id)
            if self.adapter == "docker" and job.get("containerName") and self._container_exists(job["containerName"]):
                if not container_state:
                    container_state = self._container_state(job, executable or None)
                self._remove_owned_container(job, executable or None)
            fields = self._failure_fields(exc)
            if exit_code is not None and fields.get("exitCode") is None:
                fields["exitCode"] = exit_code
            technical = fields.get("technicalDetail") or str(exc)
            self._append_log(job, f"\nWorkbench error: {technical}\n")
            self._save_job(job, state="failed", finishedAt=now_iso(), verification="failed", **fields)

    def reorder_queue(self, job_ids: list[str], revision: int | None = None) -> dict[str, Any]:
        with self.condition:
            current = self._normalize_queue_locked()
            state = self._queue_state()
            current_revision = int(state.get("revision", 0))
            if revision is not None and int(revision) != current_revision:
                raise WorkspaceError("The queue changed. Refresh it and try again.")
            current_ids = [item["id"] for item in current]
            if len(job_ids) != len(set(job_ids)) or set(job_ids) != set(current_ids):
                raise WorkspaceError("Queue order must contain every waiting job exactly once")
            next_revision = current_revision + 1
            by_id = {item["id"]: item for item in current}
            for position, job_id in enumerate(job_ids, 1):
                job = by_id[job_id]
                job.update(queuePosition=position, queueRevision=next_revision)
                write_json(self.workspace.runs / job_id / "job.json", job)
            self._write_queue_state_locked(next_revision, self._mode_lock_locked(state))
            self.condition.notify_all()
            return self.queue()

    def _remove_from_batch_and_project(self, job: dict[str, Any]) -> None:
        batch_path = self.workspace.runs / f"{job.get('batchId', '')}.json"
        batch = read_json(batch_path, {})
        if batch:
            batch["jobIds"] = [item for item in batch.get("jobIds", []) if item != job.get("id")]
            if batch["jobIds"]:
                write_json(batch_path, batch)
            else:
                batch_path.unlink(missing_ok=True)
        try:
            _, project = self.workspace.project(job.get("projectId", ""))
            project["runIds"] = [item for item in project.get("runIds", []) if item != job.get("id")]
            self.workspace.save_project(project)
        except WorkspaceError:
            pass

    def _cleanup_cancelled_job(self, job_id: str) -> dict[str, Any]:
        job_path = self.workspace.runs / job_id / "job.json"
        job = read_json(job_path, {})
        if not job:
            return {"removed": True, "jobId": job_id}
        try:
            executable = find_docker_executable() if self.adapter == "docker" else None
            if executable and job.get("containerName"):
                if self._container_exists(job["containerName"]) and not self._container_owned(job):
                    raise WorkspaceError("Container ownership could not be verified; no Docker resources or run files were removed")
                if self._container_owned(job):
                    self.runner([executable, "rm", "-f", job["containerName"]], capture_output=True, text=True, timeout=30)
            self.workspace.unregister_run_datastores(job_id)
            model_path = Path(job.get("modelPath", ""))
            if job.get("modelPath"):
                self.workspace.within(model_path, self.workspace.models, must_exist=False)
                if model_path.exists():
                    shutil.rmtree(model_path)
            self._remove_from_batch_and_project(job)
            run_dir = self.workspace.runs / job_id
            if run_dir.exists():
                shutil.rmtree(run_dir)
            self.cancelled.discard(job_id)
            return {"removed": True, "jobId": job_id}
        except Exception as exc:
            failure = {**job, "state": "cleanup_failed", "message": f"Could not delete cancelled run: {exc}", "finishedAt": now_iso(), "verification": "cancelled"}
            write_json(job_path, failure)
            return failure

    def remove_waiting(self, job_id: str) -> dict[str, Any]:
        with self.condition:
            job = self.job(job_id)
            if job.get("state") != "waiting":
                raise WorkspaceError("Only a waiting job can be removed from the queue")
            self.cancelled.add(job_id)
            result = self._cleanup_cancelled_job(job_id)
            self._normalize_queue_locked(increment=True)
            self.condition.notify_all()
            return result

    def remove_history(self, job_id: str) -> dict[str, Any]:
        """Remove a terminal job's UI history and log without deleting results."""
        with self.condition:
            job = self.job(job_id)
            if job.get("state") not in TERMINAL_STATES:
                raise WorkspaceError("Only completed, failed, or cancelled jobs can be removed from Run History")
            if job_id in self.workers or job_id in self.processes:
                raise WorkspaceError("This job is still being finalized and cannot be removed yet")
            self._remove_from_batch_and_project(job)
            run_dir = self.workspace.within(self.workspace.runs / job_id, self.workspace.runs)
            (run_dir / "run.log").unlink(missing_ok=True)
            (run_dir / "job.json").unlink(missing_ok=True)
            try:
                run_dir.rmdir()
            except OSError:
                pass
            return {
                "removed": True,
                "jobId": job_id,
                "resultsPreserved": bool(job.get("resultPath") or job.get("datastoreId")),
                "datastoreId": job.get("datastoreId", ""),
            }

    def history_clear_impact(self, older_than_days: int | None = None) -> dict[str, Any]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=max(0, int(older_than_days))) if older_than_days is not None else None
        jobs: list[dict[str, Any]] = []
        log_count = removable_bytes = 0
        for job in self.list_jobs(include_archived=True):
            if job.get("state") not in TERMINAL_STATES or job.get("id") in self.workers or job.get("id") in self.processes:
                continue
            if cutoff:
                timestamp = str(job.get("finishedAt") or job.get("createdAt") or "").replace("Z", "+00:00")
                try:
                    if datetime.fromisoformat(timestamp) >= cutoff:
                        continue
                except ValueError:
                    continue
            run_dir = self.workspace.within(self.workspace.runs / str(job["id"]), self.workspace.runs)
            for item in (run_dir / "job.json", run_dir / "run.log"):
                try:
                    if item.is_file():
                        removable_bytes += item.stat().st_size
                        log_count += int(item.name == "run.log")
                except OSError:
                    pass
            jobs.append(job)
        unfinished = [job for job in self.list_jobs(include_archived=True) if job.get("state") not in TERMINAL_STATES]
        return {
            "terminalJobs": len(jobs), "logs": log_count, "removableBytes": removable_bytes,
            "jobIds": [str(job["id"]) for job in jobs], "blocked": bool(unfinished),
            "unfinishedJobs": len(unfinished),
        }

    def clear_history(self, older_than_days: int | None = None, *, require_idle: bool = False) -> dict[str, Any]:
        with self.condition:
            impact = self.history_clear_impact(older_than_days)
            if require_idle and impact["blocked"]:
                raise WorkspaceError("Clear history will be available after all running and queued jobs finish")
            removed = []
            for job_id in impact["jobIds"]:
                try:
                    removed.append(self.remove_history(job_id))
                except WorkspaceError:
                    # Age-based maintenance remains safe if job state changes.
                    if require_idle:
                        raise
                    continue
        return {**impact, "removedJobs": len(removed), "resultsPreserved": True}

    def retry_cleanup(self, job_id: str) -> dict[str, Any]:
        job = self.job(job_id)
        if job.get("state") != "cleanup_failed":
            raise WorkspaceError("This job does not need cleanup")
        self.cancelled.add(job_id)
        return self._cleanup_cancelled_job(job_id)

    def cancel(self, job_id: str) -> dict[str, Any]:
        job = self.job(job_id)
        if job["state"] == "waiting":
            return self.remove_waiting(job_id)
        if job["state"] in TERMINAL_STATES:
            return job
        if self.adapter == "docker" and job.get("containerName") and self._container_exists(job["containerName"]) and not self._container_owned(job):
            raise WorkspaceError("The matching container is not verified as Workbench-owned and was not stopped")
        self.cancelled.add(job_id)
        self._save_job(job, state="stopping", message="Stopping VisionEval and deleting partial files", verification="cancelled")
        executable = find_docker_executable() if self.adapter == "docker" else None
        if executable and job.get("containerName") and self._container_owned(job):
            self.runner([executable, "stop", "--time", "10", job["containerName"]], capture_output=True, text=True)
        process = self.processes.get(job_id)
        if process and process.poll() is None:
            self._terminate_native_tree(process)
        with self.condition:
            self.condition.notify_all()
        return self._safe_job(job_id)

    def stop_all(self) -> dict[str, Any]:
        failures: list[dict[str, str]] = []
        active: list[dict[str, Any]] = []
        removed = 0
        with self.condition:
            if self.stop_all_in_progress:
                raise WorkspaceError("Stop All is already in progress")
            self.stop_all_in_progress = True
            jobs = self.list_jobs(include_archived=True)
            waiting = [job for job in jobs if job.get("state") == "waiting"]
            active = [job for job in jobs if job.get("state") in ACTIVE_STATES]
            for job in waiting:
                job_id = str(job.get("id", ""))
                try:
                    self.cancelled.add(job_id)
                    if job_id in self.workers:
                        # The worker owns a slot but has not begun preparation. Remove it
                        # from the runnable queue and let its cancellation checkpoint clean up.
                        self._save_job(job, state="stopping", message="Removing queued run", verification="cancelled")
                    else:
                        self._cleanup_cancelled_job(job_id)
                    removed += 1
                except Exception as exc:
                    failures.append({"jobId": job_id, "action": "remove", "error": str(exc)})
            self._normalize_queue_locked(increment=True)
            self.condition.notify_all()

        stopped = 0
        result_lock = threading.Lock()

        def stop(job: dict[str, Any]) -> None:
            nonlocal stopped
            try:
                self.cancel(str(job["id"]))
                with result_lock:
                    stopped += 1
            except Exception as exc:
                with result_lock:
                    failures.append({"jobId": str(job.get("id", "")), "action": "stop", "error": str(exc)})

        threads = [threading.Thread(target=stop, args=(job,), daemon=True) for job in active]
        try:
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
        finally:
            with self.condition:
                self.stop_all_in_progress = False
                self.condition.notify_all()
        return {"stopped": stopped, "removed": removed, "failures": failures}

    def stop_project(self, project_id: str) -> dict[str, Any]:
        """Stop only active and waiting work owned by one Hypercube project."""
        with self.workspace.activity_lock:
            return self._stop_project_locked(project_id)

    def _stop_project_locked(self, project_id: str) -> dict[str, Any]:
        _, project = self.workspace.project(project_id)
        if project.get("projectType") != "hypercube":
            raise WorkspaceError("Scoped Hypercube stopping requires a Hypercube project")
        failures: list[dict[str, str]] = []
        removed = 0
        with self.condition:
            if self.stop_all_in_progress or project_id in self.stopping_projects:
                raise WorkspaceError("Stopping runs is already in progress")
            self.stopping_projects.add(project_id)
            jobs = [
                job for job in self.list_jobs(include_archived=True)
                if job.get("projectId") == project_id
            ]
            waiting = [job for job in jobs if job.get("state") == "waiting"]
            active = [job for job in jobs if job.get("state") in ACTIVE_STATES]
            for job in waiting:
                job_id = str(job.get("id", ""))
                try:
                    self.cancelled.add(job_id)
                    if job_id in self.workers:
                        self._save_job(job, state="stopping", message="Removing queued Hypercube run", verification="cancelled")
                    else:
                        self._cleanup_cancelled_job(job_id)
                    removed += 1
                except Exception as exc:
                    failures.append({"jobId": job_id, "action": "remove", "error": str(exc)})
            self._normalize_queue_locked(increment=True)
            self.condition.notify_all()

        stopped = 0
        result_lock = threading.Lock()

        def stop(job: dict[str, Any]) -> None:
            nonlocal stopped
            try:
                self.cancel(str(job["id"]))
                with result_lock:
                    stopped += 1
            except Exception as exc:
                with result_lock:
                    failures.append({"jobId": str(job.get("id", "")), "action": "stop", "error": str(exc)})

        threads = [threading.Thread(target=stop, args=(job,), daemon=True) for job in active]
        try:
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
        finally:
            with self.condition:
                self.stopping_projects.discard(project_id)
                self.condition.notify_all()
        return {"projectId": project_id, "stopped": stopped, "removed": removed, "failures": failures}

    def shutdown(self, cancel_active: bool = False, timeout: float = 30.0) -> dict[str, Any]:
        """Gracefully stop only active Workbench jobs before the sidecar exits."""
        active = [job for job in self.list_jobs(include_archived=True) if job.get("state") in ACTIVE_STATES | {"waiting"}]
        if active and not cancel_active:
            return {"ok": False, "requiresConfirmation": True, "jobs": [{"id": job["id"], "name": job.get("variationName", job["id"]), "state": job["state"]} for job in active]}
        failures = []
        for job in active:
            try:
                self.cancel(job["id"])
            except Exception as exc:
                failures.append({"id": job["id"], "message": str(exc)})
        deadline = time.monotonic() + timeout
        while active and time.monotonic() < deadline:
            remaining = []
            for prior in active:
                current = self._safe_job(prior["id"])
                if current and current.get("state") in ACTIVE_STATES:
                    remaining.append(current)
            active = remaining
            if active:
                time.sleep(.2)
        failures.extend({"id": job["id"], "message": "Timed out while stopping this run"} for job in active)
        return {"ok": not failures, "requiresConfirmation": False, "failures": failures, "stopped": len(active) == 0}

    def retry(self, job_id: str) -> dict[str, Any]:
        prior = self.job(job_id)
        if prior.get("state") != "failed" or prior.get("retryable") is False:
            raise WorkspaceError("Only a retryable failed run can be retried")
        with self.lock:
            self._normalize_queue_locked()
            mode = self._mode_lock_locked() or self._job_mode(prior)
        force = ["baseline"] if prior["baseline"] else [prior["variationId"]]
        batch = self.create_batch(
            prior["projectId"], [] if prior["baseline"] else [prior["variationId"]], prior["baseline"], mode,
            force_rerun_ids=force,
        )
        return batch["jobs"][0]

    def log_chunk(self, job_id: str, offset: int = 0) -> dict[str, Any]:
        job = self.job(job_id)
        path = Path(job["logPath"])
        size = path.stat().st_size if path.exists() else 0
        offset = max(0, min(int(offset), size))
        with path.open("rb") as handle:
            handle.seek(offset)
            data = handle.read(128 * 1024)
        text = data.decode("utf-8", errors="replace").replace("\r\n", "\n")
        return {"job": job, "offset": offset + len(data), "text": text, "terminal": job["state"] in TERMINAL_STATES}
