# Windows 11 x64 Overview

VisionEval Workbench 2.0 for Windows runs models through a verified native VisionEval VE-40-RC7 runtime. Docker is not required.

| Component | Windows behavior |
|---|---|
| Supported system | Windows 11 x64 |
| VisionEval runtime | Existing certified `VE_RUNTIME`, `VE_HOME`, and R 4.5 `Rscript.exe`, or optional current-user setup for R 4.5.3 and VE-40-RC7 |
| Model execution | One job at a time through the verified native runtime |
| Desktop shell | Tauri with Microsoft WebView2 |

The Workbench EXE does not contain R or VisionEval. Its optional managed setup downloads and verifies the certified runtime after you choose to install it. Older R installations remain in place; installing RC7 into an existing `VE_HOME` can replace that location's R 4.5 VisionEval library. See the [Windows 2.0 installation and upgrade quick-start](https://github.com/nikolasleeb/VisionEval-Workbench/blob/main/docs/tutorials/windows-v2.0/Windows-2.0-Installation-and-Upgrade-Quick-Start.pdf) before changing an older setup.

## What remains separate

Workbench stores projects, scenarios, packages, logs, and results in its workspace, separate from the application and runtime. Keep an existing workspace when upgrading; do not create a new empty one if you need the old projects and results.

## Start here

1. Follow the [Windows 2.0 installation and upgrade quick-start](https://github.com/nikolasleeb/VisionEval-Workbench/blob/main/docs/tutorials/windows-v2.0/Windows-2.0-Installation-and-Upgrade-Quick-Start.pdf).
2. [Connect or install the runtime](Windows-Installation-and-Runtime).
3. Learn the platform workflow in [Using Workbench on Windows](Using-Workbench-on-Windows).
4. Use the [complete Windows 2.0 User Guide](https://github.com/nikolasleeb/VisionEval-Workbench/blob/main/windows/docs/user/VisionEval-Workbench-2.0-Windows-User-Guide.pdf) for assets, scenarios, runs, comparison, and Hypercube.

**Developer path:** [Building the Windows App](Building-the-Windows-App)
