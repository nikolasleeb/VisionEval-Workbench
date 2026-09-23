# VisionEval Workbench 2.0.0 for Windows

This folder contains the Windows 11 x64 source for VisionEval Workbench 2.0.0. Shared behavior is ported from the frozen macOS 2.0 checkpoint while native runtime, process, WebView2, dialog, and NSIS behavior remains Windows-specific.

The Windows application uses Tauri, a bundled Python backend, and Microsoft WebView2. Model runs connect to an existing native `VE_Runtime`, its `VE_HOME` package library, and a compatible `Rscript.exe`. Docker is not used.

The local release candidate is built as `VisionEval-Workbench-v2.0.0-windows-x64-setup.exe`. It is unsigned and must not be published without an explicit release-owner decision.

Developer setup and build details are documented in [`docs/developer`](docs/developer) and on the [Building the Windows App](https://github.com/nikolasleeb/VisionEval-Workbench/wiki/Building-the-Windows-App) wiki page.
