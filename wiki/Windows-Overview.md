# Windows 11 x64 Overview

The Windows 1.0.1 edition is designed for organizations that already maintain a compatible native VisionEval installation.

| Component | Windows behavior |
|---|---|
| Supported system | Windows 11 x64 |
| VisionEval runtime | Existing native `VE_Runtime`, `VE_HOME`, and compatible `Rscript.exe` |
| Model execution | One job at a time through the verified native runtime |
| Desktop shell | Tauri with Microsoft WebView2 |

> [!IMPORTANT]
> Workbench connects to the runtime you select. It does not install, replace, update, or modify that native VisionEval environment.

## What remains separate

Workbench stores projects, scenarios, packages, logs, and results in its own workspace. The bundled local Python service manages files, comparisons, exports, and runtime operations without altering the source model folders.

## Start here

1. Read the [current Windows User Guide](https://github.com/nikolasleeb/VisionEval-Workbench/blob/main/windows/UserGuide.md).
2. [Install Workbench and connect the runtime](Windows-Installation-and-Runtime).
3. Learn the platform workflow in [Using Workbench on Windows](Using-Workbench-on-Windows).
4. Complete the [scenario walkthrough](https://github.com/nikolasleeb/VisionEval-Workbench/blob/main/docs/tutorials/VisionEval-Workbench-Scenario-Walkthrough.pdf).

**Developer path:** [Building the Windows App](Building-the-Windows-App)
