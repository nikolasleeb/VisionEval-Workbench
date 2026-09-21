from __future__ import annotations

import threading
from typing import Any

from .workspace import CopyCancelled, Workspace, WorkspaceError, make_id, now_iso


class CopyOperationManager:
    """Run potentially large project/result copies without blocking the UI server."""

    def __init__(self, workspace: Workspace):
        self.workspace = workspace
        self.lock = threading.RLock()
        self.operations: dict[str, dict[str, Any]] = {}
        self.cancel_events: dict[str, threading.Event] = {}

    def start_project(self, payload: dict[str, Any]) -> dict[str, Any]:
        reservation_id = self.workspace.reserve_project_copy(str(payload.get("projectId", "")))
        try:
            return self._start("project", payload, reservation_id)
        except Exception:
            self.workspace.release_copy_reservation(reservation_id)
            raise

    def start_variations(self, payload: dict[str, Any]) -> dict[str, Any]:
        destination = payload.get("destination") or {}
        reservation_id = self.workspace.reserve_variation_copy(
            str(payload.get("sourceProjectId", "")), payload.get("variationIds") or [],
            str(destination.get("projectId", "")),
        )
        try:
            return self._start("variations", payload, reservation_id)
        except Exception:
            self.workspace.release_copy_reservation(reservation_id)
            raise

    def _start(self, kind: str, payload: dict[str, Any], reservation_id: str = "") -> dict[str, Any]:
        operation_id = make_id("copy-operation", kind)
        operation = {
            "id": operation_id, "kind": kind, "state": "waiting", "phase": "preparing",
            "completedBytes": 0, "totalBytes": 0, "createdAt": now_iso(), "message": "Preparing copy",
        }
        event = threading.Event()
        with self.lock:
            self.operations[operation_id] = operation
            self.cancel_events[operation_id] = event
        threading.Thread(
            target=self._run, args=(operation_id, kind, dict(payload), event, reservation_id), daemon=True,
        ).start()
        return dict(operation)

    def _run(
        self, operation_id: str, kind: str, payload: dict[str, Any], event: threading.Event,
        reservation_id: str = "",
    ) -> None:
        def progress(completed: int, total: int) -> None:
            with self.lock:
                operation = self.operations[operation_id]
                operation.update({
                    "state": "running", "phase": "copying_results", "completedBytes": completed,
                    "totalBytes": total, "message": "Copying completed results",
                })

        try:
            if kind == "variations":
                # The run state may have changed after the synchronous request
                # preflight but before this background worker was scheduled.
                self.workspace.assert_variations_copyable(
                    str(payload.get("sourceProjectId", "")), payload.get("variationIds") or [], reservation_id,
                )
                destination = payload.get("destination") or {}
                self.workspace.assert_copy_destination_idle(str(destination.get("projectId", "")), reservation_id)
            else:
                self.workspace.assert_project_copyable(str(payload.get("projectId", "")), reservation_id)
            with self.lock:
                self.operations[operation_id].update({"state": "running", "phase": "copying_design", "message": "Copying project design"})
            if kind == "project":
                result = self.workspace.copy_project(
                    str(payload.get("projectId", "")), str(payload.get("name", "")), True,
                    cancelled=event.is_set, progress=progress, reservation_id=reservation_id,
                )
            else:
                destination = payload.get("destination") or {}
                result = self.workspace.copy_variations(
                    str(payload.get("sourceProjectId", "")), payload.get("variationIds") or [],
                    target_project_id=str(destination.get("projectId", "")),
                    new_project_name=str(destination.get("name", "")),
                    cancelled=event.is_set, progress=progress, reservation_id=reservation_id,
                )
            with self.lock:
                self.operations[operation_id].update({
                    "state": "succeeded", "phase": "complete", "message": "Copy complete",
                    "result": result, "finishedAt": now_iso(),
                })
        except CopyCancelled:
            with self.lock:
                self.operations[operation_id].update({
                    "state": "cancelled", "phase": "cancelled", "message": "Copy cancelled",
                    "finishedAt": now_iso(),
                })
        except (WorkspaceError, OSError, ValueError) as exc:
            with self.lock:
                self.operations[operation_id].update({
                    "state": "failed", "phase": "failed", "message": str(exc), "finishedAt": now_iso(),
                })
        finally:
            self.workspace.release_copy_reservation(reservation_id)
            with self.lock:
                self.cancel_events.pop(operation_id, None)

    def status(self, operation_id: str) -> dict[str, Any]:
        with self.lock:
            operation = self.operations.get(operation_id)
            if not operation:
                raise WorkspaceError("Unknown copy operation")
            return dict(operation)

    def cancel(self, operation_id: str) -> dict[str, Any]:
        with self.lock:
            operation = self.operations.get(operation_id)
            event = self.cancel_events.get(operation_id)
            if not operation:
                raise WorkspaceError("Unknown copy operation")
            if event and operation.get("state") in {"waiting", "running"}:
                event.set()
                operation.update({"state": "cancelling", "message": "Cancelling copy"})
            return dict(operation)
