from __future__ import annotations

import json
import os
import re
import threading
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable

from .workspace import Workspace, now_iso

RELEASES_API = "https://api.github.com/repos/nikolasleeb/VisionEval-Workbench/releases?per_page=30"
VISIONEVAL_API = "https://api.github.com/repos/VisionEval/VisionEval-4/releases?per_page=20"
RUNTIME_INDEX_NAME = "runtime-index.json"
SOURCES = ("visioneval", "runtimeImage", "workbench")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def trusted_https(value: Any, hosts: set[str]) -> bool:
    parsed = urllib.parse.urlparse(str(value or ""))
    return parsed.scheme == "https" and parsed.hostname in hosts


def version_is_newer(candidate: str, current: str) -> bool:
    def parts(value: str) -> tuple[int, ...]:
        match = re.match(r"^[vV]?(\d+(?:\.\d+)*)", str(value or ""))
        return tuple(map(int, match.group(1).split("."))) if match else ()
    left, right = parts(candidate), parts(current)
    width = max(len(left), len(right)); return bool(left and right and left + (0,) * (width-len(left)) > right + (0,) * (width-len(right)))


class UpdateCheckService:
    """Opt-in discovery of Workbench, VisionEval, and approved Intel runtimes."""

    def __init__(self, workspace: Workspace, app_version: str, vision_eval_version: str, runtime_digest: Callable[[], str], runtime_adapter: str, runtime_profiles: Callable[[], dict[str, Any]] | None = None, http_get: Callable[[str], Any] | None = None):
        self.workspace, self.app_version, self.vision_eval_version = workspace, str(app_version), str(vision_eval_version)
        self.runtime_digest, self.runtime_adapter, self.runtime_profiles = runtime_digest, runtime_adapter, runtime_profiles or (lambda: {})
        self.http_get = http_get or self._get; self.checking = False; self.lock = threading.RLock()
        self.disabled = os.environ.get("WORKBENCH_UPDATE_CHECK_ENABLED", "true").lower() == "false"
        if self._automatic_due(): self._schedule()

    @staticmethod
    def _get(url: str) -> Any:
        request = urllib.request.Request(url, headers={"Accept":"application/vnd.github+json","User-Agent":"VisionEval-Workbench/1.1.0","X-GitHub-Api-Version":"2022-11-28"})
        with urllib.request.urlopen(request, timeout=8) as response: return json.loads(response.read().decode("utf-8"))

    def _settings(self) -> dict[str, Any]:
        value = self.workspace.settings().get("updateChecks")
        return value if isinstance(value, dict) else {"automatic":False,"sources":{key:True for key in SOURCES},"statuses":{},"lastCheckedAt":""}

    def _automatic_due(self) -> bool:
        settings=self._settings()
        if self.disabled or not settings.get("automatic"): return False
        try: checked=datetime.fromisoformat(str(settings.get("lastCheckedAt") or "").replace("Z","+00:00"))
        except ValueError: return True
        return (datetime.now(timezone.utc)-checked.astimezone(timezone.utc)).total_seconds() >= 7*24*60*60

    def _schedule(self) -> None:
        with self.lock:
            if self.checking: return
            self.checking=True
        threading.Thread(target=self._background,daemon=True,name="workbench-update-check").start()

    def _background(self) -> None:
        try: self.check(force=True)
        finally:
            with self.lock: self.checking=False

    @staticmethod
    def _record(source: str, status: str, message: str, installed: str = "", available: str = "", url: str = "", profile: dict | None = None) -> dict:
        return {"source":source,"status":status,"message":message,"installedVersion":installed,"availableVersion":available,"url":url,"releaseNotesUrl":url,"runtimeProfile":profile,"checkedAt":now_iso(),"advisoryOnly":source!="runtimeImage"}

    def status(self) -> dict[str, Any]:
        if self._automatic_due() and not self.checking: self._schedule()
        settings=self._settings(); selected=settings.get("sources") or {}; statuses=dict(settings.get("statuses") or {})
        for source in SOURCES:
            if not selected.get(source,True): statuses[source]=self._record(source,"not_selected","This update source is not selected.")
            elif source not in statuses: statuses[source]=self._record(source,"not_checked","This source has not been checked yet.")
        return {"automatic":bool(settings.get("automatic")),"sources":{key:bool(selected.get(key,True)) for key in SOURCES},"lastCheckedAt":settings.get("lastCheckedAt") or "","statuses":statuses,"checking":self.checking,"administrativelyDisabled":self.disabled,"advisoryOnly":False}

    def check(self, *, force: bool = False, sources: list[str] | None = None) -> dict[str, Any]:
        if self.disabled: return self.status()
        settings=self._settings(); selected=settings.get("sources") or {}; requested=[item for item in (sources or SOURCES) if item in SOURCES]; results=dict(settings.get("statuses") or {})
        try: releases=self.http_get(RELEASES_API)
        except Exception as exc: releases=[]; release_error=exc
        else: release_error=None
        for source in requested:
            if not selected.get(source,True): continue
            try:
                if source=="visioneval": results[source]=self._vision_eval()
                elif release_error: raise release_error
                elif source=="workbench": results[source]=self._workbench(releases)
                else: results[source]=self._runtime(releases)
            except Exception as exc: results[source]=self._record(source,"unavailable",f"Unable to check for updates: {exc}")
        checked=now_iso(); self.workspace.update_check_cache(checked_at=checked,statuses=results); return self.status()

    def _vision_eval(self) -> dict:
        releases=self.http_get(VISIONEVAL_API); latest=next((item for item in releases if not item.get("draft") and not item.get("prerelease")),None)
        if not latest: raise ValueError("No official VisionEval release was returned")
        active=(self.runtime_profiles() or {}).get("active") or {}
        installed=str(active.get("visionEvalVersion") or self.vision_eval_version)
        version=str(latest.get("tag_name") or ""); update=version!=installed
        return self._record("visioneval","update_available" if update else "current",f"VisionEval {version} is available upstream. Workbench compatibility is not implied." if update else "The Workbench VisionEval release is current.",installed,version,str(latest.get("html_url") or ""))

    def _workbench(self, releases: list[dict]) -> dict:
        release=next((item for item in releases if not item.get("draft") and not item.get("prerelease") and any("macos-x64.dmg" in str(asset.get("name") or "") for asset in item.get("assets") or [])),None)
        if not release: raise ValueError("No Intel Workbench release was found")
        version=str(release.get("tag_name") or "").lstrip("vV"); update=version_is_newer(version,self.app_version)
        return self._record("workbench","update_available" if update else "current",f"VisionEval Workbench {version} is available for Intel Mac." if update else "VisionEval Workbench is up to date.",self.app_version,version,str(release.get("html_url") or ""))

    def _runtime(self, releases: list[dict]) -> dict:
        for release in releases:
            if release.get("draft") or not str(release.get("tag_name") or "").startswith("runtime-"): continue
            asset=next((item for item in release.get("assets") or [] if item.get("name")==RUNTIME_INDEX_NAME),None)
            if not asset: continue
            index_url=str(asset.get("browser_download_url") or "")
            if not trusted_https(index_url,{"github.com","objects.githubusercontent.com"}): raise ValueError("The runtime index URL is not trusted")
            index=self.http_get(index_url); image=next((item for item in index.get("images") or [] if item.get("platform")=="macos" and item.get("architecture")=="x86_64"),None)
            if index.get("schemaVersion")!=1 or index.get("runtimeApi")!=1 or not image or not DIGEST_RE.fullmatch(str(image.get("digest") or "")): raise ValueError("The runtime index is invalid")
            digest=str(image["digest"]); reference=str(image.get("reference") or "")
            if reference!=f"ghcr.io/nikolasleeb/visioneval-workbench-runtime@{digest}": raise ValueError("The runtime index contains an untrusted image")
            capabilities=list(map(str,index.get("capabilities") or [])); required={"doctor","verify-upstream-release","verify-household-id-alignment","run","export"}
            if not required.issubset(set(capabilities)): raise ValueError("The runtime is missing required capabilities")
            version=str(index.get("preferredVisionEvalVersion") or ""); minimum=str(index.get("minimumWorkbenchVersion") or "1.1.0")
            commit=str(index.get("visionEvalCommit") or "")
            url=str(index.get("releaseUrl") or release.get("html_url") or "")
            if not re.fullmatch(r"VE-\d+-RC\d+",version) or not re.fullmatch(r"[0-9a-f]{40}",commit): raise ValueError("The runtime index has invalid VisionEval provenance")
            if not trusted_https(url,{"github.com"}): raise ValueError("The runtime index has an untrusted release URL")
            profile={"runtimeApi":1,"visionEvalVersion":version,"visionEvalCommit":commit,"digest":digest,"reference":reference,"platform":"macos","architecture":"x86_64","capabilities":capabilities,"minimumWorkbenchVersion":minimum,"publishedAt":str(index.get("publishedAt") or ""),"downloadSizeBytes":int(image.get("downloadSizeBytes") or 0),"storageSizeBytes":int(image.get("storageSizeBytes") or 0)}
            active=(self.runtime_profiles() or {}).get("active") or {}; update=str(active.get("digest") or self.runtime_digest() or "")!=digest
            if version_is_newer(minimum,self.app_version):
                return self._record("runtimeImage","update_available",f"This runtime requires Workbench {minimum} or later. Update Workbench first.",str(active.get("visionEvalVersion") or "Not installed"),version,url,profile)
            return self._record("runtimeImage","update_available" if update else "current",f"VisionEval {version} is available as a compatible Workbench runtime." if update else f"The VisionEval {version} Workbench runtime is active.",str(active.get("visionEvalVersion") or "Not installed"),version,url,profile)
        raise ValueError("No compatible runtime index was published")

    def runtime_candidate(self) -> dict[str, Any]:
        profile=((self.status().get("statuses") or {}).get("runtimeImage") or {}).get("runtimeProfile")
        if not isinstance(profile,dict): raise ValueError("No compatible runtime update is currently available")
        return dict(profile)

    def settings_changed(self) -> None:
        if self._automatic_due(): self._schedule()
