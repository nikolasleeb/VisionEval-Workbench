# VisionEval Workbench 1.0.1 for Windows

This folder contains the independently maintained Windows 11 x64 source for VisionEval Workbench 1.0.1. Its application behavior is preserved from the validated Windows implementation.

The Windows application uses Tauri, a bundled Python backend, and Microsoft WebView2. Model runs connect to an existing native `VE_Runtime`, its `VE_HOME` package library, and a compatible `Rscript.exe`. Docker is not used.

General users should download `VisionEval-Workbench-v1.0.1-windows-x64-setup.exe` from the [latest release](https://github.com/nikolasleeb/VisionEval-Workbench/releases/latest) and follow the [Windows wiki guide](https://github.com/nikolasleeb/VisionEval-Workbench/wiki/Windows-Installation-and-Runtime).

Developer setup and build details are documented in [`docs/developer`](docs/developer) and on the [Building the Windows App](https://github.com/nikolasleeb/VisionEval-Workbench/wiki/Building-the-Windows-App) wiki page.
