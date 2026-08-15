# VisionEval Workbench Developer Handbook

This handbook describes the implemented VisionEval Workbench application and the contracts that must remain stable as it evolves. The repository [README](../../README.md) is the short project introduction; this directory is the engineering source of truth.

## Handbook

- [Architecture](architecture.md) — processes, trust boundaries, and data flow.
- [Local development](local-development.md) — prerequisites, running, testing, and packaging.
- [Data contracts and APIs](data-contracts-and-apis.md) — workspace records, identifiers, HTTP APIs, events, native commands, and documentation management.
- [Runtime and global queue](runtime-and-queue.md) — Docker verification, two-slot scheduling, logs, cancellation, and recovery.
- [Runtime image maintenance](runtime-image-maintenance.md) — pinned upstream source, rebuilding, verification, and safe upgrades.
- [Comparison, metadata, and dependencies](comparison-metadata-dependencies.md) — alignment, scans, geography, units, dependency extraction, and exports.
- [Comparison performance notes](comparison-performance.md) — retained datastore-versus-CSV measurements and the resulting cache design.
- [Virginia MPO regional package](virginia-mpo-region-builder.md) — package boundary, official boundary overlay, versioned Bzone crosswalk, source record, refresh procedure, and accuracy limits.
- [Security, compatibility, and migrations](security-compatibility.md) — filesystem boundaries, provenance, versioning, and supported platforms.
- [Testing and release](testing-and-release.md) — required checks and publication gates.
- [Roadmap](roadmap.md) — prioritized future improvements, known limitations, and research questions.

## Focused references

- [Runtime setup](../user/setup.md)
- [Workspaces and storage](../user/settings-workspaces-storage.md)
- [Keyboard shortcuts](../user/keyboard-shortcuts.md)
- [Unit conflict review](../unit-conflicts.md) and [machine-readable decisions](../unit-conflicts.json)
- [Compatibility manifest](../compatibility-manifest.json)
- [Asset manifest schema](../asset-manifest.schema.json)

## Documentation policy


Developer documentation stays in the repository. User documentation is canonical in [`docs/user`](../user/README.md), is bundled with the sidecar, and is installed into each workspace. Do not document planned behavior as if it is implemented. Use the roadmap for proposals and the release checklist for gated functionality.
