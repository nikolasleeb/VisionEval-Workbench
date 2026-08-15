# Testing and Release

## Required test layers

- **Workspace:** containment, manifests, imports, overlays, review diffs, archives, cleanup, and documentation synchronization.
- **Editor:** explicit save, Undo/Redo, unsaved navigation, batch changes, notes, geography mapping, and shortcuts.
- **Runtime:** Docker absent/stopped/ready, image verification, FIFO and parallel scheduling, two-slot enforcement, reordering, restart recovery, stop cleanup, logs, and registration.
- **Comparison:** safe keyed alignment, selected year/geography, county mapping, numeric/categorical statistics, scans/cache, dashboards, CSV/XLSX parity, workbook injection safety and row splitting, imported-result source preservation, and unsafe-table rejection.
- **Metadata/dependencies:** precedence, conflicts, identifiers, template graph extraction, unresolved custom modules, and cache invalidation.
- **Desktop:** onboarding, missing workspace recovery, settings/menu states, backend lifecycle, and native guide opening.
- **Documentation:** links, package contents, managed updates, stale-file removal, user-file preservation, and privacy review.

Use the PlanRVA multimodal model only as a controlled integration fixture. Unit tests should use small synthetic workspaces.

## Release gates

No public release is permitted until:

1. The official upstream release and unofficial Workbench `DoPredictions` compatibility patch are both verified, clearly labelled, and exercised by the representative PlanRVA smoke model.
2. The exact runtime artifact that passed verification is published and pinned by immutable digest.
3. Outstanding unit conflicts are resolved or intentionally shipped with approved warnings.
4. The AMD64 DMG is clearly labelled ad-hoc signed/not notarized and tested on a clean Intel Mac using the documented Gatekeeper workaround. Developer ID signing and notarization remain future release work.
5. First launch, Docker absent/stopped/ready, asset import, a full model run, Compare, documentation installation, and workspace recovery pass.
6. Asset packs have versioned manifests and SHA-256 checksums.
7. No private paths, credentials, unpublished image references, or development assets are present.
8. Release workflows run the required test layers before publication, and the GHCR workflow verifies the same digest it publishes.

Run `Publish Intel AMD64 runtime 1.0.0` first on the release branch. Its successful publication commits the real registry digest and makes `packaging/update_runtime_publication.py --check` pass. Only after that commit is merged to `main` may `Add Intel macOS assets to release 1.0.0` build and attach the DMG and exact source snapshot. Tag creation alone must never publish the application, runtime, or assets.
