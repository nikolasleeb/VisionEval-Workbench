# Architecture and Developer Overview

VisionEval Workbench is a local desktop system with four main boundaries:

1. The Tauri host manages the desktop window, application configuration, backend lifecycle, filesystem permissions, and operating-system integration.
2. The static web interface provides Explore, Create, Run, Compare, Settings, and documentation views.
3. The local Python backend manages workspaces, packages, model preparation, jobs, datastore scanning, caching, maps, and exports.
4. The platform runtime executes VisionEval: native R and `VE_Runtime` on Windows, a pinned ARM64 Docker image on Apple Silicon, or a pinned AMD64 Docker image on Intel macOS.

Projects pin a model template and InputLibrary. Scenarios store deliberate overlays rather than altering the baseline. Every run is prepared in a new folder with a reproducible record. Completed VisionEval RDA datastores remain authoritative; SQLite and other comparison caches are disposable accelerators.

The separate `windows/`, `macos/`, and `intel/` source trees reflect intentionally different platform implementations. Root GitHub Actions workflows test and package them independently.
