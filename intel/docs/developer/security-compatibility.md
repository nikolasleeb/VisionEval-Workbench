# Security, Compatibility, and Migrations

## Filesystem safety

- Resolve project and asset paths from internal IDs below the current workspace.
- Validate external paths only for explicit imports and copy their contents before use.
- Do not expose unrestricted read, write, delete, reveal, or open commands to the web interface.
- Use atomic replacement for manifests and settings.
- Before destructive cleanup, resolve exact job/project targets and retain a recoverable record when cleanup cannot complete.
- Documentation cleanup is limited to paths recorded in the previous managed-file manifest.

## Docker safety

Use command argument arrays, an immutable verified image digest, Workbench labels, a single workspace mount, and unique container names. Do not interpolate user input into shell commands. Stopping a job must verify ownership before removing a container.

## Privacy and provenance

Documentation, screenshots, tests, logs, and release artifacts must not contain personal paths, real project names, local usernames, or unpublished image credentials. Every prepared run and registered result retains project, scenario, template, input-library, application, and runtime provenance.

## Supported compatibility

The supported runtime for this source tree is Intel macOS with Docker AMD64. Runtime profiles from a different host architecture must be replaced and reverified against the Intel image. Model compatibility requires a complete runnable folder with `visioneval.cnf`, `scripts/run_model.R`, `defs/`, and `inputs/`.

## Migration rules

- Prefer additive optional fields with defaults.
- Preserve original V1 manifests and source versions on import.
- Never rewrite imported source folders.
- Archive project removal for 30 days; hide related jobs and datastores from normal views.
- Retain results referenced by active project baselines.
- Make migrations idempotent and restart-safe, with rollback or recovery metadata for filesystem moves.
- Do not advance a version marker until validation succeeds.
