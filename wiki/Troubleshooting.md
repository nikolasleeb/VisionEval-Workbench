# Troubleshooting

## Start with Diagnostics

Open **Settings → Diagnostics** and review the application, workspace, package, and runtime status. Export a diagnostic ZIP before reporting a failure when possible.

## Windows runtime problems

Confirm that the selected folder is the `VE_Runtime` working folder, that the detected `VE_HOME` is correct, and that the selected `Rscript.exe` belongs to the compatible R installation. Re-run **Verify runtime** after correcting a path.

## Mac runtime problems

Confirm that Docker Desktop is installed and its engine is running. Return to **Settings → Runtime** and use the managed installation or verification action. Retagging an arbitrary VisionEval image will not satisfy Workbench's provenance and patch checks.

## Package problems

Install the original ZIP rather than a partially extracted folder. Confirm the package is one of the supported Workbench package types and that it was not modified after download.

## Report an issue

[Open a GitHub issue](https://github.com/nikolasleeb/VisionEval-Workbench/issues) with the operating system, Workbench version, visible error, runtime status, installed packages, failed operation, and diagnostic ZIP when available.
