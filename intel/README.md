# VisionEval Workbench 1.0.0 for Intel macOS

This folder contains the independently maintained Intel source for VisionEval Workbench 1.0.0. Its application behavior is preserved from the validated Mac implementation.

The Mac application uses Tauri, a bundled Python backend, and the macOS webview. Model runs and uncached R data access use Docker Desktop with the pinned AMD64 VisionEval Workbench runtime.

General users should download `VisionEval-Workbench-v1.0.0-macos-x64.dmg` from the [v1.0.0 release](https://github.com/nikolasleeb/VisionEval-Workbench/releases/tag/v1.0.0) and follow the [Intel Mac wiki guide](https://github.com/nikolasleeb/VisionEval-Workbench/wiki/Intel-macOS-Installation-and-Runtime).

The same release includes `VisionEval-Workbench-v1.0.0-intel-source.zip`, an exact snapshot of this source tree without generated build outputs.

Developer setup and build details are documented in [`docs/developer`](docs/developer) and on the [Building the Intel macOS App](https://github.com/nikolasleeb/VisionEval-Workbench/wiki/Building-the-Intel-macOS-App) wiki page.
