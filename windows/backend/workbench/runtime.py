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
from pathlib import Path
from typing import Any, Callable

from .transit_inputs import FILE_GROUPS, validate_transit_inputs
from .workspace import RUN_VERSION, Workspace, WorkspaceError, make_id, now_iso, read_json, write_json


ARM64_LOCAL_IMAGE = "local/visioneval:1.0.0-arm64"
AMD64_LOCAL_IMAGE = "local/visioneval:2.0.0-amd64"


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
CURRENT_RELEASE_TAG = "VE-40-RC6"
CURRENT_RELEASE_COMMIT = "f7ef3389b5626daeba6c86eeda9d172a0f8cccc2"
COMPATIBILITY_PATCH = "2026-08-03-composite-household-id-alignment"
RELEASES_API = "https://api.github.com/repos/VisionEval/VisionEval-4/releases?per_page=20"
RELEASE_CHECK_TTL_SECONDS = 24 * 60 * 60
TERMINAL_STATES = {"succeeded", "failed", "cancelled", "cleanup_failed"}
ACTIVE_STATES = {"preparing", "running", "exporting", "stopping"}
MAX_GLOBAL_RUNS = 2


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


def discover_native_installation(runtime: str = "", home: str = "", rscript: str = "") -> dict[str, str]:
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
    return {
        "veRuntime": str(runtime_path or ""),
        "veHome": str(home_path or ""),
        "rscript": str(resolved_rscript or ""),
    }


class RuntimeManager:
    def __init__(self, workspace: Workspace, image: str = DEFAULT_IMAGE, runner: Callable[..., subprocess.CompletedProcess] | None = None, cli_path: str | Path | None = None):
        self.workspace = workspace
        self.image = image
        self.adapter = "native" if platform.system() == "Windows" else "docker"
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
        self.runner = runner or subprocess.run
        environment_allows_release_check = self.adapter == "docker" and os.environ.get("VISIONEVAL_RELEASE_CHECK_ENABLED", "false").lower() == "true"
        self.release_check_supported = runner is None and environment_allows_release_check
        self.release_check_enabled = self.release_check_supported and bool(self.workspace.settings().get("checkVisionEvalUpdates", True))
        self.release_status_path = self.workspace.exchange / "system" / "runtime-release-status.json"
        self.release_check_lock = threading.Lock()
        self.release_check_running = False
        self.lock = threading.RLock()
        self.condition = threading.Condition(self.lock)
        self.processes: dict[str, subprocess.Popen] = {}
        self.workers: dict[str, threading.Thread] = {}
        self.cancelled: set[str] = set()
        self.queue_state_path = self.workspace.runs / "queue.json"
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

    def _native_execution_lock_path(self) -> Path:
        """Return the per-runtime lock shared by every Workbench backend process."""
        runtime_identity = str((self.native_runtime or Path("VE_Runtime")).resolve()).casefold()
        runtime_hash = hashlib.sha256(runtime_identity.encode("utf-8")).hexdigest()[:24]
        lock_root = Path(
            os.environ.get(
                "VISIONEVAL_RUNTIME_LOCK_DIR",
                Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir())) / "VisionEval Workbench" / "locks",
            )
        )
        lock_root.mkdir(parents=True, exist_ok=True)
        return lock_root / f"native-runtime-{runtime_hash}.lock"

    def _try_native_execution_lock(self):
        """Acquire the Windows byte-range lock without blocking."""
        import msvcrt

        handle = self._native_execution_lock_path().open("a+b")
        try:
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            return handle
        except OSError:
            handle.close()
            return None

    @staticmethod
    def _release_native_execution_lock(handle) -> None:
        import msvcrt

        try:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
        finally:
            handle.close()

    def _wait_for_native_execution_lock(self, job_id: str):
        """Wait until this VE_Runtime is free, unless another process took the job."""
        while True:
            job = self._safe_job(job_id)
            if job.get("state") != "waiting":
                return None
            handle = self._try_native_execution_lock()
            if handle is not None:
                # A second backend can observe the same queued job. Recheck after
                # acquiring the machine-wide lock so only its original claimant runs it.
                if self._safe_job(job_id).get("state") == "waiting":
                    return handle
                self._release_native_execution_lock(handle)
                return None
            time.sleep(0.5)

    def _workspace_mount_args(self) -> list[str]:
        # Keep the runtime image's stable /workspace contract while allowing the
        # host workspace to use a cleaner managed layout.
        return [
            "-v", f"{self.workspace.root}:/workspace",
            "-v", f"{self.workspace.models}:/workspace/models",
            "-v", f"{self.workspace.runs}:/workspace/runs",
            "-v", f"{self.workspace.exchange}:/workspace/exchange",
        ]

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

    def discover_native(self, runtime: str = "") -> dict[str, str]:
        if self.adapter != "native":
            raise WorkspaceError("Native VisionEval discovery is available only on Windows")
        return discover_native_installation(runtime)

    def configure_native(self, runtime: str, home: str, rscript: str) -> None:
        if self.adapter != "native":
            raise WorkspaceError("Native VisionEval configuration is available only on Windows")
        resolved_runtime = find_native_runtime(runtime)
        if not resolved_runtime or resolved_runtime != Path(runtime).expanduser().resolve():
            raise WorkspaceError("Choose a VE_RUNTIME folder containing VisionEval startup configuration")
        resolved_home = find_native_home(home)
        if not resolved_home or resolved_home != Path(home).expanduser().resolve():
            raise WorkspaceError("Choose a VE_HOME folder containing ve-lib")
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
                "User-Agent": "VisionEval-Workbench/1.0.1",
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
                    job["state"] = "failed"
                    job["message"] = "Workbench stopped while this native VisionEval run was active. Retry it to run again."
                    job["finishedAt"] = now_iso()
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
                        cleaned = True
                    except (OSError, subprocess.TimeoutExpired):
                        pass
                job["state"] = "failed"
                job["message"] = "Workbench stopped while this run was active. Its stale container was cleaned up. Retry it to run again." if cleaned else "Workbench stopped while this run was active. Container ownership could not be verified, so no Docker resource was touched."
                job["finishedAt"] = now_iso()
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
            self._save_job(job, state="failed", message="The recovered VisionEval container is no longer available", finishedAt=now_iso(), verification="failed")
            return
        try:
            self._append_log(job, "\n--- Reconnected to the existing VisionEval container ---\n")
            waited = self.runner([executable, "wait", job["containerName"]], capture_output=True, text=True, timeout=None)
            logs = self.runner([executable, "logs", job["containerName"]], capture_output=True, text=True, timeout=30)
            if logs.stdout or logs.stderr:
                self._append_log(job, (logs.stdout or "") + (logs.stderr or ""))
            exit_code = int((waited.stdout or "1").strip().splitlines()[-1]) if waited.returncode == 0 else 1
            if exit_code:
                raise WorkspaceError(f"Recovered VisionEval container exited with code {exit_code}")
            self._finalize_success(job_id, executable)
        except Exception as exc:
            current = self._safe_job(job_id)
            self._append_log(current, f"\nWorkbench recovery error: {exc}\n")
            self._save_job(current, state="failed", message=str(exc), finishedAt=now_iso(), verification="failed")

    def _queue_state(self) -> dict[str, Any]:
        state = read_json(self.queue_state_path, {"version": 1, "revision": 0})
        return state if isinstance(state, dict) else {"version": 1, "revision": 0}

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
        if increment:
            state["revision"] = int(state.get("revision", 0)) + 1
        revision = int(state.get("revision", 0))
        for position, job in enumerate(jobs, 1):
            if job.get("queuePosition") != position or job.get("queueRevision") != revision:
                job["queuePosition"] = position
                job["queueRevision"] = revision
                write_json(self.workspace.runs / job["id"] / "job.json", job)
        write_json(self.queue_state_path, {"version": 1, "revision": revision, "updatedAt": now_iso()})
        return jobs

    def queue(self) -> dict[str, Any]:
        with self.lock:
            jobs = self._normalize_queue_locked()
            return {"revision": int(self._queue_state().get("revision", 0)), "jobs": jobs, "maxActive": self.max_active_runs}

    @property
    def max_active_runs(self) -> int:
        """Native VisionEval shares one R runtime and must execute serially."""
        return 1 if self.adapter == "native" else MAX_GLOBAL_RUNS

    def _batch(self, batch_id: str) -> dict[str, Any]:
        return read_json(self.workspace.runs / f"{batch_id}.json", {})

    def _eligible_locked(self, job: dict[str, Any]) -> bool:
        batch = self._batch(job.get("batchId", ""))
        if (job.get("batchMode") or batch.get("mode")) != "queued":
            return True
        batch_id = job.get("batchId")
        return not any(
            worker_id != job.get("id") and self._safe_job(worker_id).get("batchId") == batch_id
            for worker_id in self.workers
        )

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
            return labels.get("com.visioneval.workbench") == "true" and (
                labels.get("com.visioneval.job") == job.get("id") or
                (not labels.get("com.visioneval.job") and name == f"ve-{job.get('id')}")
            )
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

    def _dispatch_loop(self) -> None:
        while True:
            with self.condition:
                launched = False
                if not self.runtime_enabled:
                    self.condition.wait(timeout=1.0)
                    continue
                while len(self.workers) < self.max_active_runs:
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
                    if len(self.workers) + len(unreserved_containers) >= self.max_active_runs:
                        break
                    thread = threading.Thread(target=self._worker_entry, args=(job["id"],), daemon=True, name=f"job-{job['id']}")
                    self.workers[job["id"]] = thread
                    thread.start()
                    launched = True
                if not launched:
                    self.condition.wait(timeout=1.0)

    def _worker_entry(self, job_id: str) -> None:
        native_lock = None
        try:
            if self.adapter == "native":
                native_lock = self._wait_for_native_execution_lock(job_id)
                if native_lock is None:
                    return
            self._run_job(job_id)
        finally:
            if native_lock is not None:
                self._release_native_execution_lock(native_lock)
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
        return {
            "installed": bool(rscript), "running": present, "executable": rscript or "",
            "hostArchitecture": platform.machine(), "supported": platform.system() == "Windows",
            "image": str(home or ""), "imagePresent": present, "adapter": "native",
            "veRuntime": str(runtime or ""), "veHome": str(home or ""),
            "imageDigest": "", "digestMatches": True,
            "imageReleaseTag": "", "imageRevision": "",
            "imageCompatibilityPatch": "", "provenanceMatches": True,
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
        return {
            "releaseTag": release_tag,
            "revision": revision,
            "compatibilityPatch": compatibility_patch,
            "matches": release_tag == CURRENT_RELEASE_TAG and revision == CURRENT_RELEASE_COMMIT and compatibility_patch == COMPATIBILITY_PATCH,
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
                f"Runtime provenance mismatch. Expected {CURRENT_RELEASE_TAG} at {CURRENT_RELEASE_COMMIT}; "
                f"found {provenance['releaseTag'] or 'no release label'} at {provenance['revision'] or 'no revision label'}."
            )
        outputs = {}
        for command in ("doctor", "verify-upstream-release", "verify-alignment-patch"):
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
        return {"ok": True, "adapter": self.adapter, "platform": platform.system().lower(), "architecture": platform.machine(), "image": self.image, "digest": digest, "runtimeVersion": "VisionEval VE-40-RC6 / R 4.5.1", "releaseTag": provenance["releaseTag"], "revision": provenance["revision"], "compatibilityPatch": provenance["compatibilityPatch"], "verifiedAt": now_iso(), "checks": outputs}

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
        with self.condition:
            self.runtime_enabled = True
            self.condition.notify_all()
        return {
            "ok": True, "adapter": "native", "platform": platform.system().lower(), "architecture": platform.machine(),
            "image": str(self.native_home), "veHome": str(self.native_home), "veRuntime": str(self.native_runtime),
            "rscript": self.rscript or find_rscript_executable(), "digest": "",
            "runtimeVersion": f"VisionEval {runtime_info.get('visionEvalVersion', 'unknown')} / R {runtime_info.get('rVersion', 'unknown')}",
            **runtime_info,
            "releaseTag": "", "revision": "", "compatibilityPatch": "", "verifiedAt": now_iso(), "checks": outputs,
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

    def create_batch(self, project_id: str, variation_ids: list[str], include_baseline: bool, mode: str) -> dict[str, Any]:
        if mode not in {"queued", "parallel"}:
            raise WorkspaceError("Run mode must be queued or parallel")
        if self.adapter == "native":
            mode = "queued"
        validation = self.validate_project(project_id)
        if not validation["valid"]:
            raise WorkspaceError("Project is not runnable: " + "; ".join(validation["errors"]))
        _, project = self.workspace.project(project_id)
        available = {item["id"]: item for item in project["variations"]}
        selected = []
        if include_baseline:
            selected.append(("baseline", "Baseline", True))
        for variation_id in variation_ids:
            if variation_id not in available:
                raise WorkspaceError("Unknown project variation")
            selected.append((variation_id, available[variation_id]["name"], False))
        if not selected:
            raise WorkspaceError("Select at least one run")
        batch_id = make_id("batch", project["name"])
        image_digest = self.image_digest()
        jobs = []
        with self.condition:
            waiting = self._normalize_queue_locked()
            next_position = len(waiting) + 1
            queue_state = self._queue_state()
            revision = int(queue_state.get("revision", 0)) + 1
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
                    "image": self.image,
                    "imageDigest": image_digest,
                    "containerId": "",
                    "containerName": f"ve-{job_id}",
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
            write_json(self.queue_state_path, {"version": 1, "revision": revision, "updatedAt": now_iso()})
            self._normalize_queue_locked()
            self.condition.notify_all()
        return {**batch, "jobs": jobs, "validation": validation}

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
        self._save_job(job, state="exporting", message="Exporting results")
        environment = None
        if self.adapter == "native":
            export, environment = self._native_command("export", str(model_path))
        else:
            export = [executable, "run", "--rm", "--platform", self.container_platform, *self._container_resource_args(), *self._workspace_mount_args(), self.image, "export", job_id]
        with open(job["logPath"], "a", encoding="utf-8") as log:
            export_result = subprocess.run(export, stdout=log, stderr=subprocess.STDOUT, text=True, env=environment)
        if export_result.returncode:
            raise WorkspaceError(f"Result export exited with code {export_result.returncode}")
        if job_id in self.cancelled:
            self._cleanup_cancelled_job(job_id); return
        datastore = model_path / "results" / "Datastore"
        if not (datastore / "DatastoreListing.Rda").is_file():
            raise WorkspaceError("Run finished but DatastoreListing.Rda was not created")
        record = self.workspace.register_datastore({
            "label": f"{job['projectName']} — {job['variationName']}", "path": str(datastore),
            "role": "baseline" if job["baseline"] else "scenario", "projectId": job["projectId"],
            "projectName": job["projectName"], "variationId": job["variationId"], "variationName": job["variationName"],
            "templateId": job["templateId"], "templateFingerprint": job["templateFingerprint"],
            "runtimeImage": self.image, "completedAt": now_iso(), "verification": "verified", "runId": job_id,
        })
        job = self.job(job_id)
        self._save_job(job, state="succeeded", message="Run completed", exitCode=0, finishedAt=now_iso(), resultPath=str(datastore), verification="verified", datastoreId=record["id"])

    def _run_job(self, job_id: str) -> None:
        job = self.job(job_id)
        if job_id in self.cancelled:
            self._cleanup_cancelled_job(job_id)
            return
        try:
            self._save_job(job, state="preparing", message="Preparing runnable model", startedAt=now_iso())
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
                    raise WorkspaceError("The selected VisionEval installation is not compatible with this model. See the run log for missing packages or modules.")
                command, environment = self._native_command("run", str(model_path))
                executable = command[0]
            else:
                executable = find_docker_executable()
                if not executable:
                    raise WorkspaceError("Docker CLI was not found")
                command = [
                    executable, "run", "--rm", "--platform", self.container_platform, *self._container_resource_args(), "--name", job["containerName"],
                    "--label", "com.visioneval.workbench=true", "--label", f"com.visioneval.job={job_id}", *self._workspace_mount_args(), self.image, "run", job_id,
                ]
            self._save_job(job, state="running", message="VisionEval is running")
            mirror_stop = threading.Event()
            mirror = threading.Thread(target=self._mirror_model_log, args=(model_path, job, mirror_stop), daemon=True, name=f"log-{job_id}")
            mirror.start()
            try:
                with open(job["logPath"], "a", encoding="utf-8") as log:
                    process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, text=True, env=environment)
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
            if exit_code:
                raise WorkspaceError(f"VisionEval exited with code {exit_code}")
            self._finalize_success(job_id, executable)
        except Exception as exc:
            if job_id in self.cancelled:
                self._cleanup_cancelled_job(job_id)
                return
            job = self.job(job_id)
            self._append_log(job, f"\nWorkbench error: {exc}\n")
            self._save_job(job, state="failed", message=str(exc), exitCode=job.get("exitCode"), finishedAt=now_iso(), verification="failed")

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
            write_json(self.queue_state_path, {"version": 1, "revision": next_revision, "updatedAt": now_iso()})
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

    @staticmethod
    def _remove_cancelled_tree(path: Path) -> None:
        """Remove cancelled-run files after Windows releases transient handles."""
        delays = (0.1, 0.25, 0.5, 1.0, 2.0)
        for attempt in range(len(delays) + 1):
            try:
                shutil.rmtree(path)
                return
            except FileNotFoundError:
                return
            except OSError:
                if platform.system() != "Windows" or attempt == len(delays):
                    raise
                time.sleep(delays[attempt])

    def _terminate_process_tree(self, process: subprocess.Popen[Any]) -> None:
        """Stop a native Windows run and every R process it launched."""
        if process.poll() is not None:
            return
        if platform.system() == "Windows":
            result = self.runner(
                ["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True,
                text=True,
                timeout=20,
            )
            if result.returncode == 0:
                return
        process.terminate()

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
                    self._remove_cancelled_tree(model_path)
            self._remove_from_batch_and_project(job)
            run_dir = self.workspace.runs / job_id
            if run_dir.exists():
                self._remove_cancelled_tree(run_dir)
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
            self._terminate_process_tree(process)
        with self.condition:
            self.condition.notify_all()
        return self._safe_job(job_id)

    def stop_all(self) -> dict[str, Any]:
        jobs = self.list_jobs(include_archived=True)
        active = [job for job in jobs if job.get("state") in ACTIVE_STATES]
        waiting = [job for job in jobs if job.get("state") == "waiting"]
        stopped = 0
        removed = 0
        failures: list[dict[str, str]] = []
        for job in active:
            try:
                self.cancel(job["id"])
                stopped += 1
            except Exception as exc:
                failures.append({"jobId": str(job.get("id", "")), "action": "stop", "error": str(exc)})
        for job in waiting:
            try:
                self.remove_waiting(job["id"])
                removed += 1
            except Exception as exc:
                failures.append({"jobId": str(job.get("id", "")), "action": "remove", "error": str(exc)})
        return {"stopped": stopped, "removed": removed, "failures": failures}

    def shutdown(self, cancel_active: bool = False, timeout: float = 30.0) -> dict[str, Any]:
        """Gracefully stop only active Workbench jobs before the sidecar exits."""
        active = [job for job in self.list_jobs(include_archived=True) if job.get("state") in ACTIVE_STATES]
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
        batch = self.create_batch(prior["projectId"], [] if prior["baseline"] else [prior["variationId"]], prior["baseline"], "queued")
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
