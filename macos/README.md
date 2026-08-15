# VisionEval Workbench 1.0.0 for Apple Silicon macOS

This folder contains the independently maintained Apple Silicon source for VisionEval Workbench 1.0.0. Its application behavior is preserved from the validated Mac implementation.

The Mac application uses Tauri, a bundled Python backend, and the macOS webview. Model runs and uncached R data access use Docker Desktop with the pinned ARM64 VisionEval Workbench runtime.

General users should download `VisionEval-Workbench-v1.0.0-macos-arm64.dmg` from the [latest release](https://github.com/nikolasleeb/VisionEval-Workbench/releases/latest) and follow the [Mac wiki guide](https://github.com/nikolasleeb/VisionEval-Workbench/wiki/macOS-Installation-and-Runtime).

Developer setup and build details are documented in [`docs/developer`](docs/developer) and on the [Building the macOS App](https://github.com/nikolasleeb/VisionEval-Workbench/wiki/Building-the-macOS-App) wiki page.
