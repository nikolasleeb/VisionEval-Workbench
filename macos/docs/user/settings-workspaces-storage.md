# Settings, Workspaces, and Storage

Settings uses a fixed desktop sidebar for Workspace, Assets, Appearance, Numbers, Notifications, Runtime, Resources, Diagnostics, Documentation, and Storage. Only the selected page scrolls. The dialog leaves a visible gap above the Windows taskbar and white space beneath **Save Settings**.

Open Settings with the gear button or **Ctrl+,**.

## Diagnostics

**Settings → Diagnostics** lists failed runs and recent application errors. Exported diagnostic ZIPs include logs, manifests, native runtime/profile information, and app errors. Optional result-datastore and comparison-cache inclusions are off by default because they can be large.

## Documentation

**Settings → Documentation** displays this managed Windows User Guide without leaving Workbench. Guide home and Reload appear above the page. Internal links and bundled images remain in the viewer; external links are explicit. Upgrades refresh managed files but never replace `Documentation/User Notes/`.

## Workspace

The workspace contains `Projects`, `Assets`, `Results`, `Documentation`, and internal `.workbench` state. Use **Open another workspace** or **Move workspace** to change it safely. Back up the complete workspace when you need a portable copy.

**Forget** removes only a saved shortcut. **Move to Recycle Bin** is offered only for an inactive verified workspace and never for the current workspace.

## Assets

Install approved Workbench packages from Assets. Model and regional packages provide a matched Model package and Input Library. Choose the Model package; Workbench selects its verified internal pairing automatically. Workbench blocks removal while a project references an asset. Removed unreferenced assets remain recoverable for 30 days. Removing a Region Builder pair clears any temporary Setup selection so another installed Model package can be used immediately.

**Settings → Reset → Repair workspace structure** recreates missing workspace folders, cleans abandoned staging data, rebuilds references, and audits path lengths. It applies immediately and does not require saving Settings. It does not restore removed assets or rebuild regional packages.

## Appearance and numbers

Appearance controls theme and accessible decrease, neutral, and increase palettes. The optional master palette applies one set everywhere while retaining individual choices. Number settings control calculation and display precision without changing authoritative raw values. VisionEval inputs are type-sensitive: declared counts remain whole numbers, continuous values can use the configured precision, and identifiers such as years and geography codes are never rounded.

## Runtime and resources

Runtime shows the selected `VE_RUNTIME`, detected `VE_HOME`, `Rscript.exe`, R and VisionEval versions, verification result, and repair actions. Re-run verification after any path or installation change.

Windows executes one VisionEval job at a time. Resource guidance reports native-process and workspace usage.

## Storage

Storage reports datastore, full-export, prepared-model, asset, project, cache, and total workspace sizes. The comparison cache is disposable: clearing or rebuilding it never removes registered results.
