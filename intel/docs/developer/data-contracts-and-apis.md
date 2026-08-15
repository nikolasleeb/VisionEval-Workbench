# Data Contracts and APIs

## Workspace contract

Workspace format 2 exposes four user-facing areas and stores application state beneath `.workbench`:

| Area | Contract |
| --- | --- |
| `Assets/InputLibraries/` | Copied input-library folders; imported sources are never edited. |
| `Assets/ModelTemplates/` | Complete validated models with immutable import provenance. |
| `Assets/InputExplanations/` | Installed explanation packages. |
| `Assets/RegionalData/` | Installed regional geography packages. |
| `Projects/<id>/project.json` | Project, baseline, internal variations/scenarios, edits, notes, run references, and registrations. |
| `Results/Models/<run-id>/` | Prepared runnable copies and retained model results. |
| `Documentation/` | Managed user guide plus unmanaged `User Notes/`. |
| `.workbench/settings.json` | Workspace defaults and preferences. |
| `.workbench/datastore_catalog.json` | Registered datastore metadata. |
| `.workbench/runs/<job-id>/` | Job manifest and complete `run.log`; batches have their own manifests. |
| `.workbench/exchange/` | R helpers, caches, inbox/outbox, and integrations. |
| `.workbench/archive/` | Recoverable projects and assets. |

`.workbench/exchange/comparison-cache/v2/` contains disposable SQLite databases and manifests. The neighboring comparison operation directories contain reconnectable operation records. None is authoritative user data.

Older workspaces may contain `role: imported` datastore registrations beneath `models/import-<datastore-id>/`. These records remain readable for compatibility, but current releases do not create, hide, restore, or remove them through the application API.

Project, scenario, job, batch, template, library, and datastore IDs are stable API identifiers. Frontend callers must not send arbitrary workspace paths.

## Documentation contract

`docs/user-intel/documentation.json` declares the canonical documentation version. On sidecar startup, `DocumentationService` installs the guide into `Documentation/Workbench User Guide/`, writes `Documentation/README.md`, and records every managed path and SHA-256 in `Documentation/.workbench-documentation.json`.

Only paths listed by the previous manifest may be overwritten or removed. Unknown files and everything beneath `Documentation/User Notes/` are workspace-owned and preserved. Missing packaged documentation returns a warning in `/api/state` and must not prevent startup.

## HTTP API conventions

- APIs are loopback-only and return JSON unless exporting a file or streaming SSE.
- Read endpoints use IDs and query parameters; mutations accept a JSON object.
- Known validation and filesystem errors return an `error` string with a 400 response.
- Unexpected failures return 500 without exposing arbitrary filesystem browsing.
- Run logs use a reconnectable SSE stream and byte offset so a client can resume.
- Comparisons and scans are asynchronous operations with start, status/reconnect, cancellation, page/result retrieval, and explicit phase reporting. Existing synchronous comparison URLs remain compatibility wrappers.

Comparison operation endpoints are `POST /api/comparison/operations/start`, `GET /api/comparison/operations/status?id=…`, and `POST /api/comparison/operations/cancel`. Cache controls are `POST /api/comparison/cache/clear` and `/rebuild`; `GET /api/storage` reports bytes, entries, and the 5 GB limit.

Datastore selection is read-only. `GET /api/state` and `GET /api/datastores` expose completed Workbench results plus visible legacy registrations; there are no datastore import or management mutation endpoints.

Comparison export endpoints are `POST /api/comparison/exports/start`, `GET /api/comparison/exports/status?id=…`, `POST /api/comparison/exports/cancel`, and `GET /api/comparison/exports/download?id=…`. The `full-variables` kind accepts `format` (`xlsx` or `csv-zip`), `year`, and `variableKeys`; it always uses original row order and no geography filter. Status records the artifact filename and MIME type, and downloads expose safe filenames without workspace paths.

`GET /api/state` is the aggregate bootstrap response. It includes assets, projects, jobs, queue, datastore catalog, runtime, workspace settings, archives, and documentation status. Avoid adding large table data or log bodies to it.

Asset lifecycle mutations use `POST /api/assets/archive`, `/api/assets/restore`, and `/api/assets/purge`. The state response includes dependency records for active and archived projects, default status, generated asset relationships, removal eligibility, and the recoverable asset archive.

## Native commands

Tauri commands own desktop-only capabilities: workspace selection/movement, runtime profiles, appearance, menu state, backend start/restart, and opening the user guide. Native commands validate the saved workspace before resolving a path. The user-guide command opens only `Documentation/README.md` in the current workspace.

The menu emits semantic actions to the web interface for context-sensitive commands such as New Scenario and Stop Selected Run. Commands that are invalid for the current selection remain disabled.

## Versioning and compatibility

Desktop configuration, workspace marker, workspace settings, project manifests, and job manifests have independent versions. Add optional fields with defaults when possible. Keep the internal `variations` collection until a deliberate manifest migration is designed; user-facing language calls these records scenarios.

Never silently reinterpret historical provenance. A migration must be restart-safe, test legacy and current records, and preserve source versions.
