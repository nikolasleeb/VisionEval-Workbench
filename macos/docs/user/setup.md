# Connect VE_Runtime on Windows

Workbench uses an existing native VisionEval installation. It does not install or replace VisionEval, R, or your package library.

## What you need

- Windows 11 x64 and VisionEval Workbench 2.1.
- A `VE_RUNTIME` working folder, normally containing `.Renviron`, `.Rprofile`, or a `launch_R*.bat` script.
- A `VE_HOME` package library containing the required VisionEval packages.
- A compatible `Rscript.exe`.

These three paths may be in different folders.

## 1. Install Workbench

Download the Windows x64 artifact, extract it, and run the NSIS setup executable. Launch **VisionEval Workbench** from the Start menu.

## 2. Choose a workspace

On first launch, accept the suggested File Explorer-visible workspace or choose an empty folder that is separate from `VE_RUNTIME`. The workspace holds projects, installed assets, prepared runs, logs, results, caches, and personal notes. Workbench remembers it on later launches.

If an existing workspace was moved or disconnected, use **Open existing workspace**. Workbench never silently substitutes a different folder.

## 3. Connect VE_Runtime

1. Open **Settings → Runtime**.
2. Select **Choose VE_Runtime…** and choose the folder used as `VE_RUNTIME`.
3. Review the detected `VE_HOME` and `Rscript.exe` paths.
4. Expand **Detected paths and advanced overrides** only if either detected path is incorrect.
5. Select **Verify runtime**.

Verification starts that R installation and reports detected R, VisionEval, and package versions plus registered modules. It does not compare source hashes, download packages, alter the runtime, or copy results into it.

The Runtime page reports exactly which path failed when the working folder, package library, or R executable cannot be used. Correct that path and verify again.

## 4. Install regional assets

Open **Settings → Assets** and install the approved regional package. A regional package supplies the InputLibrary and model template used by Create. Virginia MPO geography building requires the separately distributed Virginia region package.

Workbench copies installed assets into the workspace and never edits their source archive or the connected runtime.

## 5. Confirm the connection

1. Confirm **Native VisionEval ready** appears in the application header.
2. Open **Explore** and verify the installed InputLibrary loads.
3. Create or open a small project and save a scenario change.
4. Open **Run**, start the intended job, and confirm live R output appears.
5. After it succeeds, open **Compare** and select the registered result.

Windows runs are queued and execute one at a time. Successful results are registered only after the expected datastore is verified.

## Moving or upgrading VE_Runtime

If the runtime, package library, or R installation moves, return to **Settings → Runtime**, select the new working folder, and verify it again. Upgrade the VisionEval installation through its normal managed process; Workbench will not update it automatically.
