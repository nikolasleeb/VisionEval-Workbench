# Settings, Workspaces, and Storage

Open **VisionEval Workbench → Settings…** or press **⌘,**.

Use **Settings → Reset → Reset settings to defaults** to restore appearance, asset defaults, number formatting, export retention, notifications, resource limits, and Docker startup behavior. This preference reset preserves every workspace, installed package, project, result, runtime profile, and runtime image. When runs are active or waiting, resource changes are saved and applied after the next safe Workbench restart.

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

Install verified Workbench packages from the primary action at the top of Assets. Choose a default InputLibrary for new projects; Workbench automatically uses its verified paired model template. Inspect installed assets in count-bearing disclosures, and open **Unpackaged assets** only for provenance of development, migration, or legacy folders. Changing a default does not modify existing projects; they remain pinned to their original asset IDs and fingerprints.

Every installed asset has a removal status. Workbench blocks removal when an active or archived project still references the asset and names the affected projects. Unreferenced assets move to **Removed assets** for 30 days, where they can be restored or deleted permanently. Removing an unreferenced default clears that default after confirmation. Region Builder Model package and Input Library pairs are removed together. If the removed region was selected in Setup, Workbench clears that temporary selection so another installed Model package can be used immediately.

**Settings → Reset → Repair workspace structure** recreates missing workspace folders, cleans abandoned staging data, rebuilds references, and audits path lengths. It applies immediately and does not require saving Settings. It does not restore removed assets or rebuild regional packages.

## Numbers

The master decimal precision for continuous values defaults to two places. Optional overrides control single-file calculations, batch calculations, displayed output values, and displayed percentages. VisionEval inputs are type-sensitive: declared count fields remain whole numbers, while identifiers, years, geography codes, and similar labels are never rounded. Those safeguards cannot be overridden. Arithmetic results omit unnecessary trailing zeros, so increasing `2` by `10%` produces `2.2` at the default precision. Display precision never changes saved raw values or full-precision data exports.

## Appearance

Choose System, Light, or Dark. System follows macOS appearance.

## Runtime and resources

Runtime begins with a clear **Ready**, **Needs attention**, or **Not configured** summary. Image identity, verification evidence, and advanced details are collapsible; shortened references retain their complete accessible and copyable values. Existing install, verify, rollback, Docker-start, and setup-guide actions are unchanged. Docker Desktop's allocation is one shared pool for active containers. Automatic memory mode adds no Workbench cap; an advanced per-run limit becomes Docker's `--memory` limit for new containers only, does not reserve memory, does not affect already-running containers, and can terminate a run that reaches it. Increase the shared allocation in Docker Desktop settings, not Workbench.

When you select a package ZIP or extracted folder, Workbench validates it before installation and displays its name, version, type, contents, size, compatibility, provenance, intended use, execution support, warnings, and checksum status. Installation begins only after confirmation and the source is revalidated immediately before copying. The Virginia source-data package explicitly warns that it builds supported MPO or custom regional packages and is not intended to run Virginia as one statewide model.

Measured MPO/regional guidance is approximately 2.5–3.5 GB of Docker memory per active run. A statewide Virginia model is provisionally estimated at 24–32 GB per active run (will be updated once tested); run its first baseline by itself. Actual use varies by model stage, population, years, and outputs, so these estimates warn but do not restrict concurrency.

Docker Desktop's allocation is the total pool shared by every active run. The optional Workbench per-run limit is a ceiling for each newly created container; it does not reserve memory or increase that shared pool. A run can therefore exhaust its own cap, or several parallel runs can collectively exhaust Docker Desktop's allocation. Confirmed exhaustion is reported as a Docker out-of-memory failure; exit code 137 without Docker confirmation is reported as a likely memory-pressure failure.

The panel verifies the release tag, source commit, runtime API, architecture, household-ID behavior, and immutable image digest. Workbench 2.0.0 can install a manifest-approved RC7 digest after confirmation and restore the previous verified RC6 runtime. A failed candidate never replaces the active runtime.

When Docker Desktop is stopped, Workbench can launch the installed application, wait for its engine, and verify the pinned runtime when available. It does not quit Docker Desktop or stop unrelated containers.

Choose up to eight concurrent VisionEval jobs and whether new batches default to queued or parallel mode. The concurrency setting reserves no memory.

## Updates

Update checks are off by default. In **Settings → Updates**, enable weekly checks or use **Check Now** without enabling automatic checks. Select any combination of VisionEval, the Workbench runtime image, and VisionEval Workbench. Workbench contacts only the public GitHub release feeds and validated release manifests. It never installs an update automatically; **Install Runtime Update** always shows the proposed release and requires confirmation.

The three notices mean different things:

- **VisionEval** reports a newer official upstream release. It does not mean that release is already compatible with this Workbench.
- **Workbench runtime image** reports only an immutable GHCR digest explicitly approved by the Workbench compatibility manifest for this application version and Mac architecture. An arbitrary newer registry tag is never recommended.
- **VisionEval Workbench** reports a newer stable application release with an asset for this platform and architecture.

Results are cached for seven days. Offline use, GitHub rate limits, and malformed remote responses are shown as **Unable to check** and do not affect projects, runtime verification, or model execution. Release links open in the default browser. The Settings gear displays a small indicator when an advisory update is available.

## Storage

The **Retain full VisionEval CSV exports** setting applies to Standard-project jobs and is recorded when each job is queued. New Hypercube runs always keep the authoritative Datastore without generating the optional full CSV output tree. Large Standard runs can still use substantial disk space when both are retained. Actual size depends on the model, geography, years, and output tables.

The comparison cache contains requested output columns extracted from Datastores. It is disposable, shared across Compare and Hypercube Analysis, limited to 5 GB, and rebuilt on demand. Clearing it never deletes an authoritative result.

Storage settings report datastore, full-export, prepared-model, asset, project, and workspace totals separately. Changing the retain-exports preference does not retroactively delete existing data.

The comparison cache is disposable derived data. **Clear Cache** or **Rebuild Cache** does not remove registered results. Previously imported results remain readable legacy registrations; Workbench no longer offers result import or removal controls.

## Archived projects

Archived projects remain recoverable for 30 days. Workbench purges expired archives periodically, but retains a datastore still referenced as an active project's baseline until that dependency is removed.
