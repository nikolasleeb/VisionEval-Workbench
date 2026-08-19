# Settings, Workspaces, and Storage

Settings uses a fixed desktop sidebar for Workspace, Assets, Appearance, Numbers, Notifications, Runtime, Resources, Diagnostics, Documentation, Storage, and About. Only the selected page scrolls. The dialog leaves a visible gap above the Windows taskbar and white space beneath **Save Settings**.

Open Settings with the gear button or **Ctrl+,**.

## Save and refresh

**Save Settings** keeps Settings open and reports the actual result in the footer. Ordinary preferences show **Settings saved and applied.** A verified `VE_Runtime` connection that the running backend has not adopted yet offers **Refresh Workbench**.

Refresh restarts only Workbench's local backend, waits for it to become healthy, and reconnects the same native window. It is unavailable while a run is queued, preparing, running, exporting, or stopping. Close remains the only normal control that closes Settings.

## Diagnostics

**Settings → Diagnostics** lists failed runs and recent application errors. App errors are retained in the current workspace for 30 days, up to 500 entries. **Clear app errors** removes only that error history after confirmation; it does not remove failed runs, results, or previously exported diagnostic ZIPs.

Exported diagnostic ZIPs include logs, manifests, native runtime/profile information, and the most recent retained app errors. Optional result-datastore and comparison-cache inclusions are off by default because they can be large.

## Documentation

**Settings → Documentation** displays this managed Windows User Guide without leaving Workbench. Guide home and Reload appear above the page. Internal links and bundled images remain in the viewer; external links are explicit. Upgrades refresh managed files but never replace `Documentation/User Notes/`.

## Workspace

The workspace contains `Projects`, `Assets`, `Results`, `Documentation`, and internal `.workbench` state. Use **Open another workspace…** or **Move workspace…** to change it safely. Back up the complete workspace when you need a portable copy.

**Forget** removes only a saved shortcut. **Move to Recycle Bin** is offered only for an inactive verified workspace and never for the current workspace.

## Assets

Install approved Workbench packages from Assets. Regional packages provide matched model-template and InputLibrary assets. Workbench blocks removal while a project references an asset. Removed unreferenced assets remain recoverable for 30 days.

## Appearance and numbers

Appearance controls theme and accessible decrease, neutral, and increase palettes. The optional master palette applies one set everywhere while retaining individual choices. Number settings control calculation and display precision without changing authoritative raw values.

## Runtime and resources

Runtime shows the selected `VE_RUNTIME`, detected `VE_HOME`, `Rscript.exe`, R and VisionEval versions, verification result, and repair actions. Re-run verification after any path or installation change.

Windows executes one VisionEval job at a time. Resource guidance reports native-process and workspace usage.

Workbench also prevents a second desktop window from starting and reserves the selected `VE_Runtime` with a cross-process lock while a job is active. These protections keep native runs serial even if an older backend process is still shutting down.

## About

**Settings → About** shows the installed Workbench version, Windows edition, project information, and source/release link. Workbench checks GitHub at most once every seven days for a newer published stable release. Use **Check for updates** for an immediate check. Update notices link to the release but never download or install it automatically.

## Storage

Storage reports datastore, full-export, prepared-model, asset, project, cache, and total workspace sizes. The comparison cache is disposable: clearing or rebuilding it never removes registered results.
