# Architecture and Developer Overview

VisionEval Workbench is a local desktop system that keeps the user interface, workspace management, and platform-specific model execution behind clear boundaries.

## System boundaries

| Layer | Responsibility |
|---|---|
| **Tauri host** | Desktop window, application configuration, backend lifecycle, filesystem permissions, and operating-system integration |
| **Static web interface** | Explore, Create, Run, Compare, Settings, and documentation views |
| **Local Python backend** | Workspaces, packages, model preparation, jobs, datastore scanning, caching, maps, and exports |
| **Platform runtime** | Native R and `VE_Runtime` on Windows; pinned ARM64 Docker image on Apple Silicon; pinned AMD64 Docker image on Intel macOS |

## Data and reproducibility

- Projects pin a model template and InputLibrary.
- Scenarios store deliberate overlays instead of altering the baseline.
- Each run is prepared in a new folder with a reproducible record.
- Completed VisionEval RDA datastores remain authoritative.
- SQLite and other comparison caches are disposable accelerators and can be rebuilt.

## Platform source trees

| Source tree | Target |
|---|---|
| `windows/` | Windows 11 x64 with a native VisionEval runtime |
| `macos/` | Apple Silicon macOS with the ARM64 managed runtime |
| `intel/` | Intel macOS with the AMD64 managed runtime |

These implementations remain intentionally separate. Root GitHub Actions workflows test and package them independently.

**Build guides:** [Windows](Building-the-Windows-App) · [Apple Silicon](Building-the-macOS-App) · [Intel](Building-the-Intel-macOS-App) · [Regional package](Building-a-Regional-Package)
