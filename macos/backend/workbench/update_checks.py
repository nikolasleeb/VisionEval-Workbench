from __future__ import annotations

import json
import os
import platform
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Callable

from .workspace import Workspace, now_iso


WORKBENCH_RELEASES_API = "https://api.github.com/repos/nikolasleeb/VisionEval-Workbench/releases?per_page=20"
VISIONEVAL_RELEASES_API = "https://api.github.com/repos/VisionEval/VisionEval-4/releases?per_page=20"
UPDATE_MANIFEST_NAME = "update-manifest.json"
RUNTIME_RELEASES_API = "https://api.github.com/repos/nikolasleeb/VisionEval-Workbench/releases?per_page=30"
RUNTIME_INDEX_NAME = "runtime-index.json"
UPDATE_CHECK_TTL_SECONDS = 7 * 24 * 60 * 60
UPDATE_SOURCES = ("visioneval", "runtimeImage", "workbench")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _version_parts(value: str) -> tuple[tuple[int, ...], tuple[str, ...]]:
    text = str(value or "").strip().lstrip("vV")
    match = re.match(r"^(\d+(?:\.\d+)*)(?:[-+](.*))?$", text)
    if not match:
        return (), (text.lower(),) if text else ()
    numeric = tuple(int(part) for part in match.group(1).split("."))
    suffix = tuple(part for part in re.split(r"[.\-]", match.group(2) or "") if part)
    return numeric, tuple(part.lower() for part in suffix)


def version_is_newer(candidate: str, current: str) -> bool:
    candidate_numbers, candidate_suffix = _version_parts(candidate)
    current_numbers, current_suffix = _version_parts(current)
    if not candidate_numbers or not current_numbers:
        return False
    width = max(len(candidate_numbers), len(current_numbers))
    left = candidate_numbers + (0,) * (width - len(candidate_numbers))
    right = current_numbers + (0,) * (width - len(current_numbers))
    if left != right:
        return left > right
    # A stable release is newer than a prerelease at the same numeric version.
    if bool(candidate_suffix) != bool(current_suffix):
        return not candidate_suffix
    return candidate_suffix > current_suffix


def _is_https_url(value: Any, *, hosts: set[str] | None = None) -> bool:
    try:
        parsed = urllib.parse.urlparse(str(value or ""))
    except ValueError:
        return False
    return parsed.scheme == "https" and bool(parsed.netloc) and (hosts is None or parsed.hostname in hosts)


def _architecture() -> str:
    machine = platform.machine().lower()
    return "arm64" if machine in {"arm64", "aarch64"} else "x86_64"


def _platform_name() -> str:
    return {"Darwin": "macos", "Windows": "windows"}.get(platform.system(), platform.system().lower())


def _asset_matches(asset: dict[str, Any], platform_name: str, architecture: str) -> bool:
    name = str(asset.get("name") or "").lower()
    url = str(asset.get("browser_download_url") or "")
    if not name or not _is_https_url(url, hosts={"github.com", "objects.githubusercontent.com"}):
        return False
    platform_tokens = ("macos", "darwin", ".dmg") if platform_name == "macos" else ("windows", ".exe", ".msi")
    architecture_tokens = ("arm64", "aarch64") if architecture == "arm64" else ("x86_64", "amd64", "x64")
    return any(token in name for token in platform_tokens) and any(token in name for token in architecture_tokens)


class UpdateCheckService:
    """Advisory-only update discovery with a workspace-scoped seven-day cache."""

    def __init__(
        self,
        workspace: Workspace,
        app_version: str,
        vision_eval_version: str,
        runtime_digest: Callable[[], str],
        runtime_adapter: str,
        runtime_profiles: Callable[[], dict[str, Any]] | None = None,
        http_get: Callable[[str], Any] | None = None,
    ) -> None:
        self.workspace = workspace
        self.app_version = str(app_version)
        self.vision_eval_version = str(vision_eval_version)
        self.runtime_digest = runtime_digest
        self.runtime_adapter = runtime_adapter
        self.runtime_profiles = runtime_profiles or (lambda: {})
        self.platform = _platform_name()
        self.architecture = _architecture()
        self.http_get = http_get or self._http_get
        self.lock = threading.RLock()
        self.checking = False
        self.administratively_disabled = os.environ.get("WORKBENCH_UPDATE_CHECK_ENABLED", "true").lower() == "false"
        if self._automatic_due():
            self._schedule()

    def _http_get(self, url: str) -> Any:
        request = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"VisionEval-Workbench/{self.app_version}",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        with urllib.request.urlopen(request, timeout=8) as response:
            return json.loads(response.read().decode("utf-8"))

    def _settings(self) -> dict[str, Any]:
        return self.workspace.settings()["updateChecks"]

    def _automatic_due(self) -> bool:
        settings = self._settings()
        if self.administratively_disabled or not settings.get("automatic"):
            return False
        value = str(settings.get("lastCheckedAt") or "")
        if not value:
            return True
        try:
            checked = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return (datetime.now(timezone.utc) - checked.astimezone(timezone.utc)).total_seconds() >= UPDATE_CHECK_TTL_SECONDS
        except ValueError:
            return True

    def _schedule(self) -> None:
        with self.lock:
            if self.checking:
                return
            self.checking = True
        threading.Thread(target=self._background_check, daemon=True, name="workbench-update-check").start()

    def settings_changed(self) -> None:
        """Apply an update preference change without coupling it to runtime setup."""
        if self._automatic_due():
            self._schedule()

    def _background_check(self) -> None:
        try:
            self.check(force=True)
        finally:
            with self.lock:
                self.checking = False

    def status(self) -> dict[str, Any]:
        if self._automatic_due() and not self.checking:
            self._schedule()
        settings = self._settings()
        sources = settings.get("sources") or {}
        statuses = dict(settings.get("statuses") or {})
        for source in UPDATE_SOURCES:
            if not sources.get(source, True):
                statuses[source] = self._not_selected(source)
            elif source not in statuses:
                statuses[source] = self._not_checked(source)
        return {
            "automatic": bool(settings.get("automatic")),
            "sources": {source: bool(sources.get(source, True)) for source in UPDATE_SOURCES},
            "lastCheckedAt": settings.get("lastCheckedAt") or "",
            "statuses": statuses,
            "checking": self.checking,
            "administrativelyDisabled": self.administratively_disabled,
            "advisoryOnly": False,
        }

    def check(self, *, force: bool = False, sources: list[str] | None = None) -> dict[str, Any]:
        settings = self._settings()
        selected = settings.get("sources") or {}
        requested = [source for source in (sources or UPDATE_SOURCES) if source in UPDATE_SOURCES]
        enabled = [source for source in requested if selected.get(source, True)]
        if self.administratively_disabled:
            return self.status()
        if not force and not self._automatic_due():
            return self.status()

        releases: list[dict[str, Any]] | None = None
        releases_error: Exception | None = None
        try:
            releases = self._workbench_releases()
        except Exception as exc:  # Remote failures are converted to per-source status.
            releases_error = exc

        results = dict(settings.get("statuses") or {})
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {}
            for source in enabled:
                if source == "visioneval":
                    futures[executor.submit(self._check_visioneval)] = source
                elif releases_error:
                    results[source] = self._failure(source, releases_error)
                elif source == "workbench":
                    futures[executor.submit(self._check_workbench, releases or [])] = source
                else:
                    futures[executor.submit(self._check_runtime)] = source
            for future in as_completed(futures):
                source = futures[future]
                try:
                    results[source] = future.result()
                except Exception as exc:
                    results[source] = self._failure(source, exc)
        for source in UPDATE_SOURCES:
            if not selected.get(source, True):
                results[source] = self._not_selected(source)
        checked_at = now_iso()
        self.workspace.update_check_cache(checked_at=checked_at, statuses=results)
        return self.status()

    def _workbench_releases(self) -> list[dict[str, Any]]:
        payload = self.http_get(WORKBENCH_RELEASES_API)
        if not isinstance(payload, list):
            raise ValueError("Workbench release service returned an unexpected response")
        allow_prerelease = bool(_version_parts(self.app_version)[1])
        return [item for item in payload if isinstance(item, dict) and not item.get("draft") and (allow_prerelease or not item.get("prerelease"))]

    def _check_workbench(self, releases: list[dict[str, Any]]) -> dict[str, Any]:
        candidates = []
        for release in releases:
            asset = next((item for item in release.get("assets") or [] if isinstance(item, dict) and _asset_matches(item, self.platform, self.architecture)), None)
            if asset:
                candidates.append((release, asset))
        if not candidates:
            raise ValueError(f"No {self.platform} {self.architecture} Workbench release asset was found")
        release, asset = candidates[0]
        available = str(release.get("tag_name") or "").lstrip("vV")
        update = version_is_newer(available, self.app_version)
        return self._record(
            "workbench", "update_available" if update else "current",
            installed=self.app_version, available=available or self.app_version,
            url=str(asset.get("browser_download_url") or release.get("html_url") or ""),
            release_notes_url=str(release.get("html_url") or ""),
            message=(f"VisionEval Workbench {available} is available for this Mac." if update else "VisionEval Workbench is up to date."),
        )

    def _check_visioneval(self) -> dict[str, Any]:
        profile_state = self.runtime_profiles() or {}
        active_profile = profile_state.get("active") if isinstance(profile_state, dict) else None
        installed_version = (
            str(active_profile.get("visionEvalVersion") or "")
            if isinstance(active_profile, dict)
            else ""
        ) or self.vision_eval_version
        if os.environ.get("VISIONEVAL_RELEASE_CHECK_ENABLED", "true").lower() == "false":
            return self._record("visioneval", "unavailable", installed=installed_version, message="VisionEval release checks were disabled by an administrator.")
        payload = self.http_get(VISIONEVAL_RELEASES_API)
        if not isinstance(payload, list):
            raise ValueError("VisionEval release service returned an unexpected response")
        releases = [item for item in payload if isinstance(item, dict) and not item.get("draft") and not item.get("prerelease")]
        if not releases:
            raise ValueError("No stable VisionEval release was returned")
        latest = releases[0]
        available = str(latest.get("tag_name") or "")
        update = available != installed_version
        return self._record(
            "visioneval", "update_available" if update else "current",
            installed=installed_version, available=available,
            url=str(latest.get("html_url") or "https://github.com/VisionEval/VisionEval-4/releases"),
            release_notes_url=str(latest.get("html_url") or ""),
            message=(f"VisionEval {available} is available upstream. Workbench compatibility is not yet implied." if update else "The Workbench VisionEval release is current."),
        )

    def _manifest_for_release(self, releases: list[dict[str, Any]]) -> dict[str, Any]:
        for release in releases:
            asset = next((item for item in release.get("assets") or [] if isinstance(item, dict) and item.get("name") == UPDATE_MANIFEST_NAME), None)
            if not asset:
                continue
            url = str(asset.get("browser_download_url") or "")
            if not _is_https_url(url, hosts={"github.com", "objects.githubusercontent.com"}):
                raise ValueError("Update manifest URL is not trusted")
            payload = self.http_get(url)
            self._validate_manifest(payload)
            return payload
        raise ValueError("No compatible runtime update manifest was published")

    @staticmethod
    def _validate_manifest(payload: Any) -> None:
        if not isinstance(payload, dict) or payload.get("schemaVersion") != 1:
            raise ValueError("Update manifest has an unsupported schema")
        workbench = payload.get("workbench")
        images = payload.get("runtimeImages")
        if not isinstance(workbench, dict) or not _version_parts(str(workbench.get("version") or ""))[0]:
            raise ValueError("Update manifest has no valid Workbench version")
        if not _is_https_url(workbench.get("releaseUrl"), hosts={"github.com"}):
            raise ValueError("Update manifest has an invalid release URL")
        if not isinstance(images, list):
            raise ValueError("Update manifest has no runtime image list")
        for image in images:
            if not isinstance(image, dict) or not DIGEST_RE.fullmatch(str(image.get("digest") or "")):
                raise ValueError("Update manifest has an invalid runtime digest")
            if not str(image.get("reference") or "").startswith("ghcr.io/nikolasleeb/visioneval-workbench-runtime@sha256:"):
                raise ValueError("Update manifest has an untrusted runtime reference")

    def _runtime_index(self) -> dict[str, Any]:
        releases = self.http_get(RUNTIME_RELEASES_API)
        if not isinstance(releases, list):
            raise ValueError("Runtime release service returned an unexpected response")
        for release in releases:
            if not isinstance(release, dict) or release.get("draft") or not str(release.get("tag_name") or "").startswith("runtime-"):
                continue
            asset = next((item for item in release.get("assets") or [] if isinstance(item, dict) and item.get("name") == RUNTIME_INDEX_NAME), None)
            if not asset:
                continue
            url = str(asset.get("browser_download_url") or "")
            if not _is_https_url(url, hosts={"github.com", "objects.githubusercontent.com"}):
                raise ValueError("Runtime index URL is not trusted")
            payload = self.http_get(url)
            self._validate_runtime_index(payload)
            return payload
        # Workbench 1.0 releases did not publish a runtime index. Retain the
        # release-manifest fallback until the first RC7 runtime is public.
        return self._manifest_for_release(self._workbench_releases())

    @staticmethod
    def _validate_runtime_index(payload: Any) -> None:
        if not isinstance(payload, dict) or payload.get("schemaVersion") != 1:
            raise ValueError("Runtime index has an unsupported schema")
        if payload.get("runtimeApi") != 1 or not re.fullmatch(r"VE-\d+-RC\d+", str(payload.get("preferredVisionEvalVersion") or "")):
            raise ValueError("Runtime index has an unsupported runtime API or VisionEval version")
        if not re.fullmatch(r"[0-9a-f]{40}", str(payload.get("visionEvalCommit") or "")):
            raise ValueError("Runtime index has an invalid upstream commit")
        if not _version_parts(str(payload.get("minimumWorkbenchVersion") or ""))[0]:
            raise ValueError("Runtime index has an invalid minimum Workbench version")
        if not _is_https_url(payload.get("releaseUrl"), hosts={"github.com"}):
            raise ValueError("Runtime index has an invalid release URL")
        capabilities = payload.get("capabilities")
        required = {"doctor", "verify-upstream-release", "verify-household-id-alignment", "run", "export"}
        if not isinstance(capabilities, list) or not required.issubset(set(map(str, capabilities))):
            raise ValueError("Runtime index is missing required capabilities")
        images = payload.get("images")
        if not isinstance(images, list) or not images:
            raise ValueError("Runtime index has no runtime images")
        for image in images:
            if not isinstance(image, dict) or not DIGEST_RE.fullmatch(str(image.get("digest") or "")):
                raise ValueError("Runtime index has an invalid runtime digest")
            if str(image.get("reference") or "") != f"ghcr.io/nikolasleeb/visioneval-workbench-runtime@{image.get('digest')}":
                raise ValueError("Runtime index has an untrusted runtime reference")
            for field in ("downloadSizeBytes", "storageSizeBytes"):
                if field in image and (not isinstance(image[field], int) or image[field] <= 0):
                    raise ValueError(f"Runtime index has an invalid {field}")

    def _check_runtime(self) -> dict[str, Any]:
        if self.runtime_adapter != "docker":
            return self._record("runtimeImage", "current", installed="Native VisionEval", available="Not applicable", message="This platform uses a native VisionEval runtime rather than a Workbench container image.")
        manifest = self._runtime_index()
        images = manifest.get("images") or manifest.get("runtimeImages") or []
        matches = [item for item in images if item.get("platform") == self.platform and item.get("architecture") == self.architecture]
        if not matches:
            raise ValueError(f"The update manifest has no {self.platform} {self.architecture} runtime")
        image = matches[0]
        minimum = str(image.get("minimumWorkbenchVersion") or manifest.get("minimumWorkbenchVersion") or "0.0.0")
        installed_digest = str(self.runtime_digest() or "")
        available_digest = str(image["digest"])
        release_url = str(manifest.get("releaseUrl") or (manifest.get("workbench") or {}).get("releaseUrl") or "")
        vision_eval_version = str(manifest.get("preferredVisionEvalVersion") or image.get("visionEvalVersion") or "")
        runtime_profile = {
            "runtimeApi": int(manifest.get("runtimeApi") or 0),
            "visionEvalVersion": vision_eval_version,
            "visionEvalCommit": str(manifest.get("visionEvalCommit") or ""),
            "digest": available_digest,
            "reference": str(image.get("reference") or ""),
            "platform": str(image.get("platform") or ""),
            "architecture": str(image.get("architecture") or ""),
            "capabilities": list(manifest.get("capabilities") or []),
            "minimumWorkbenchVersion": minimum,
            "publishedAt": str(manifest.get("publishedAt") or ""),
            "downloadSizeBytes": int(image.get("downloadSizeBytes") or 0),
            "storageSizeBytes": int(image.get("storageSizeBytes") or 0),
        }
        profile_state = self.runtime_profiles() or {}
        active_profile = profile_state.get("active") if isinstance(profile_state, dict) else {}
        installed_version = str((active_profile or {}).get("visionEvalVersion") or installed_digest or "Not installed")
        if version_is_newer(minimum, self.app_version):
            return self._record(
                "runtimeImage", "update_available", installed=installed_version, available=vision_eval_version or available_digest,
                url=release_url, release_notes_url=release_url,
                message=f"A newer runtime image requires Workbench {minimum} or later. Update Workbench first.",
                requires_workbench=minimum, runtime_profile=runtime_profile,
            )
        update = bool(installed_digest and installed_digest != available_digest)
        if not installed_digest:
            update = True
        return self._record(
            "runtimeImage", "update_available" if update else "current",
            installed=installed_version, available=vision_eval_version or available_digest,
            url=release_url, release_notes_url=release_url,
            message=(f"VisionEval {vision_eval_version} is available as a compatible Workbench runtime." if update else f"The VisionEval {vision_eval_version} Workbench runtime is active."),
            runtime_profile=runtime_profile,
        )

    def _record(self, source: str, status: str, *, installed: str = "", available: str = "", url: str = "", release_notes_url: str = "", message: str = "", requires_workbench: str = "", runtime_profile: dict[str, Any] | None = None) -> dict[str, Any]:
        for candidate in (url, release_notes_url):
            if candidate and not _is_https_url(candidate, hosts={"github.com", "objects.githubusercontent.com"}):
                raise ValueError("Update response contained an untrusted link")
        return {
            "source": source, "status": status, "installedVersion": installed,
            "availableVersion": available, "url": url, "releaseNotesUrl": release_notes_url,
            "message": message, "checkedAt": now_iso(), "requiresWorkbenchVersion": requires_workbench,
            "advisoryOnly": source != "runtimeImage", "runtimeProfile": runtime_profile,
        }

    def runtime_candidate(self) -> dict[str, Any]:
        status = (self.status().get("statuses") or {}).get("runtimeImage") or {}
        profile = status.get("runtimeProfile")
        if not isinstance(profile, dict):
            raise ValueError("No compatible runtime update is currently available")
        self._validate_runtime_index({
            "schemaVersion": 1,
            "runtimeApi": profile.get("runtimeApi"),
            "preferredVisionEvalVersion": profile.get("visionEvalVersion"),
            "visionEvalCommit": profile.get("visionEvalCommit"),
            "minimumWorkbenchVersion": profile.get("minimumWorkbenchVersion"),
            "releaseUrl": status.get("releaseNotesUrl") or status.get("url"),
            "capabilities": profile.get("capabilities"),
            "images": [profile],
        })
        return dict(profile)

    def _failure(self, source: str, error: Exception) -> dict[str, Any]:
        detail = str(error) or error.__class__.__name__
        if isinstance(error, urllib.error.HTTPError) and error.code == 403:
            detail = "GitHub rate limit reached. Try again later."
        return self._record(source, "unavailable", message=f"Unable to check for updates: {detail}")

    @staticmethod
    def _not_selected(source: str) -> dict[str, Any]:
        return {"source": source, "status": "not_selected", "message": "This update source is not selected.", "advisoryOnly": True}

    @staticmethod
    def _not_checked(source: str) -> dict[str, Any]:
        return {"source": source, "status": "not_checked", "message": "This source has not been checked yet.", "advisoryOnly": True}
