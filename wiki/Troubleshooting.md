# Troubleshooting

Start with the evidence Workbench already collects, then isolate the failing layer before changing runtime or package settings.

## 1. Create a diagnostic bundle

Open **Settings → Diagnostics** and review application, workspace, package, and runtime status. Export a diagnostic ZIP before reporting a failure when possible.

> [!TIP]
> Include datastores or caches only when they are relevant and safe to share; those options can make the bundle substantially larger.

## 2. Identify the problem area

| Problem area | First checks |
|---|---|
| **Windows runtime** | Confirm the selected folder is the `VE_Runtime` working folder, the detected `VE_HOME` is correct, and `Rscript.exe` belongs to the compatible R installation. Then rerun **Verify runtime**. |
| **Mac runtime** | Confirm Docker Desktop is installed and its engine is running. Use the managed install or verification action in **Settings → Runtime**. |
| **Regional package** | Install the original ZIP, confirm it is a supported package type, and verify it was not modified after download. |
| **Run or comparison** | Record the project, scenario, failed operation, visible error, and whether the datastore was completed and registered. |

> [!IMPORTANT]
> Retagging another VisionEval image does not satisfy Workbench's provenance, architecture, compatibility-patch, and digest checks.

## 3. Report the issue

[Open a GitHub Issue](https://github.com/nikolasleeb/VisionEval-Workbench/issues) and include:

- Operating system and processor architecture
- Workbench version
- Runtime status and installed packages
- Project, scenario, and failed operation
- Exact visible error
- Diagnostic ZIP when available and appropriate to share

**Related:** [Windows runtime setup](Windows-Installation-and-Runtime) · [Apple Silicon runtime setup](macOS-Installation-and-Runtime) · [Intel runtime setup](Intel-macOS-Installation-and-Runtime)
