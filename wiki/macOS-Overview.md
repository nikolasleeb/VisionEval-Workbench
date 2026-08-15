# macOS Overview

This edition supports Apple Silicon Macs running macOS 12 or newer. Intel users should install the separate [Intel macOS edition](Intel-macOS-Overview).

Workbench stores projects, scenarios, packages, logs, and results in a separate workspace. Docker Desktop supplies the isolated ARM64 VisionEval runtime used for model runs and uncached R datastore access. Containers are temporary and are created only when required.

The desktop shell uses Tauri and the macOS webview. A bundled local Python service performs file, model, comparison, export, and runtime operations.

Next: [macOS Installation and Runtime](macOS-Installation-and-Runtime).
