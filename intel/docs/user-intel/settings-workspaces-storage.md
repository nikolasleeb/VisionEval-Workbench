# Settings, Workspaces, and Storage

Open **VisionEval Workbench → Settings…** or press **⌘,**.

## Notifications

Notifications are off until you enable them. macOS still controls whether alerts are allowed; the first attempted notification can trigger the system permission prompt. In **Settings → Notifications**, enable or disable alerts for completed or failed VisionEval runs, first runtime setup, and long-running Compare work, including comparisons, change scans, datastore imports, and map/chart exports. Use **Send Test Notification** to verify notification delivery later.

Workbench suppresses alerts for old history when it launches or refreshes. It alerts only when work changes from an active state to completed or failed while the app is running.

## Workspace

Settings shows the current path and keeps optional other workspaces in a collapsed disclosure. Multiple workspaces are useful when separate organizations, production work, or testing must not share projects and assets; most users need only one. Category actions reveal Projects, Assets, Results, or Documentation without exposing technical state. The complete root remains available under **Storage → Advanced workspace access**. Switching and moving are blocked while a job is active or waiting.

**Forget** removes only the shortcut from Workbench. **Move to Trash** is available only for an inactive workspace whose identity can be verified; it moves the complete folder to the operating-system Trash. Workbench never offers either action for the current workspace.

A move is verified before Workbench saves the new path. Recovery metadata retains the previous location until the move is confirmed.

Back up the entire workspace when you need a complete portable copy. Do not copy only project manifests if you also need run results and imported assets.

The managed layout keeps user-facing data in `Projects`, `Assets`, `Results`, and `Documentation`. Settings, catalogs, run queues, caches, recovery archives, and preserved legacy files live in the hidden `.workbench` folder. Use Workbench rather than Finder to remove managed data.

## Assets

Install verified Workbench packages from the primary action at the top of Assets. Choose compact defaults for new projects, inspect installed assets in count-bearing disclosures, and open **Unpackaged assets** only for development, migration, or legacy folders that are not distributed as verified packages. Changing a default does not modify existing projects; they remain pinned to their original asset IDs and fingerprints.

Every installed asset has a removal status. Workbench blocks removal when an active or archived project still references the asset and names the affected projects. Unreferenced assets move to **Removed assets** for 30 days, where they can be restored or deleted permanently. Removing an unreferenced default clears that default after confirmation. Region Builder template and InputLibrary pairs are removed together.

## Numbers

The master decimal precision defaults to two places. Optional overrides control single-file calculations, batch calculations, displayed output values, and displayed percentages. Arithmetic results omit unnecessary trailing zeros, so increasing `2` by `10%` produces `2.2` at the default precision. Display precision never changes saved raw values or full-precision data exports.

## Appearance

Choose System, Light, or Dark. System follows macOS appearance.

## Runtime and resources

Runtime shows Docker status, saved image reference/digest, verification, and repair actions. Long image references and digests wrap within the panel; **Copy Digest** copies the complete immutable value. Automatic memory mode applies no additional Workbench cap; Docker Desktop's own allocation controls available memory. An advanced per-container limit affects new jobs only.

The panel verifies the release tag, source commit, unofficial compatibility-patch identity, and immutable image digest. Workbench 1.0.0 can install the compatible GHCR runtime image for you and then verifies that exact image before Run is enabled.

When Docker Desktop is stopped, Workbench can launch the installed application, wait for its engine, and verify the pinned runtime when available. It does not quit Docker Desktop or stop unrelated containers.

The maximum number of concurrent VisionEval jobs is fixed at two. Choose whether new batches default to queued or parallel mode.

## Storage

Full VisionEval CSV exports are retained after successful runs by default. Large model runs can use substantial disk space because Workbench may retain both the authoritative datastore and optional full CSV output. Actual size depends on the model, geography, years, and output tables.

Storage settings report datastore, full-export, prepared-model, asset, project, and workspace totals separately. Changing the retain-exports preference does not retroactively delete existing data.

The comparison cache is disposable derived data. **Clear Cache** or **Rebuild Cache** does not remove registered results. Previously imported results remain readable legacy registrations; Workbench no longer offers result import or removal controls.

## Archived projects

Archived projects remain recoverable for 30 days. Workbench purges expired archives periodically, but retains a datastore still referenced as an active project's baseline until that dependency is removed.
