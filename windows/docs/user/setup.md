# Connect VE_Runtime on Windows

Workbench can connect to an existing native VisionEval installation or install the certified R 4.5.3 and VisionEval VE-40-RC7 pair for the current user. The managed installation does not require administrator privileges.

## What you need

- Windows 11 x64 and VisionEval Workbench 2.0.0.
- A `VE_RUNTIME` working folder, normally containing `.Renviron`, `.Rprofile`, or a `launch_R*.bat` script.
- A `VE_HOME` package library containing the required VisionEval packages.
- A compatible `Rscript.exe`.

These three paths are validated independently. `VE_HOME` and `VE_RUNTIME` must be separate, non-nested folders. Workbench resolves junctions and symbolic links before accepting them, so an alias cannot hide an overlap.

## 1. Install Workbench

Download the Windows x64 artifact, extract it, and run the NSIS setup executable. Launch **VisionEval Workbench** from the Start menu.

## 2. Choose a workspace

On first launch, accept the suggested File Explorer-visible workspace or choose an empty folder that is separate from `VE_RUNTIME` and `VE_HOME`. The workspace holds projects, installed assets, prepared runs, logs, results, caches, and personal notes. Workbench remembers it on later launches. A folder on an external SSD is supported and is recommended when internal disk space is limited.

If an existing workspace was moved or disconnected, use **Open existing workspace**. Workbench never silently substitutes a different folder.

## 3. Connect or install the runtime

If Workbench finds no usable runtime, first-run setup opens automatically. Choose **Detect again**, select all three existing paths, or choose **Install R 4.5.3 + VisionEval RC7**.

1. Open **Settings → Runtime**.
2. Select **Choose VE_Runtime…** and choose the folder used as `VE_RUNTIME`.
3. Review the detected `VE_HOME` and `Rscript.exe` paths.
4. Expand **Detected paths and advanced overrides** only if either detected path is incorrect.
5. Select **Verify runtime**.

Verification starts that R installation and reports detected R, VisionEval, package versions, registered modules, release tag, and `VECommit`. VisionEval packages continue to report version 4.0.0, so Workbench uses `VECommit` to identify RC7 correctly.

The managed installer reuses a compatible R 4.5 installation when available. Otherwise it installs R 4.5.3 under the current user's local application directory, installs the RC7 library under `%USERPROFILE%\VE_Home`, and creates the working folder at `%LOCALAPPDATA%\VisionEval\VE_Runtime`. Downloads use pinned official URLs and SHA-256 values. A failed checksum, TLS error, interrupted extraction, or failed verification stops the installation and cleans incomplete VisionEval files.

For offline setup, obtain the exact files listed in `WINDOWS-RUNTIME-COMPATIBILITY.md`, verify their SHA-256 values, install R for the current user, extract the VisionEval library into a separate `VE_HOME`, and then select `VE_HOME`, `VE_RUNTIME`, and `Rscript.exe` in Workbench. Never place `VE_RUNTIME` below `VE_HOME`.

The Runtime page reports exactly which path failed when the working folder, package library, or R executable cannot be used. Correct that path and verify again.

## 4. Install regional assets

Open **Settings → Assets** and install the approved regional package with **Choose ZIP…** or **Choose extracted folder…**. A regional package supplies the InputLibrary and model template used by Create. Virginia MPO geography building requires the separately distributed Virginia region package.

Workbench copies installed assets into the workspace and never edits their source archive or the connected runtime.

## 5. Confirm the connection

1. Confirm **Native VisionEval ready** appears in the application header.
2. Open **Explore** and verify the installed InputLibrary loads.
3. Create or open a small project and save a scenario change.
4. Open **Run**, start the intended job, and confirm live R output appears.
5. After it succeeds, open **Compare** and select the registered result.

Windows runs are queued and execute one at a time. Successful results are registered only after the expected datastore is verified.

## Moving or upgrading VE_Runtime

If the runtime, package library, or R installation moves, return to **Settings → Runtime**, select all changed paths, and verify again. Workbench does not automatically adopt a newer R or VisionEval release until that pair passes the full certification suite.
