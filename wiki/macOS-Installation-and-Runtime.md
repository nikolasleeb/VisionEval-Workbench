# Apple Silicon macOS 2.0 Installation and Runtime

Read the illustrated [Installation and Setup PDF](https://github.com/nikolasleeb/VisionEval-Workbench/raw/refs/heads/main/docs/tutorials/macOS-v2.0/Mac-2.0-Installation-and-Setup.pdf) for screenshots and videos.

1. Confirm Apple Silicon and macOS 12 or newer. Install [Docker Desktop for Apple silicon](https://docs.docker.com/desktop/setup/install/mac-install/) and start its engine.
2. Download the [Workbench 2.0 ARM64 DMG](https://github.com/nikolasleeb/VisionEval-Workbench/releases/download/v2.0.0/VisionEval-Workbench-v2.0.0-macos-arm64.dmg).
3. Open the DMG and drag VisionEval Workbench to Applications. Launch the Applications copy, then eject the installer.
4. Choose a workspace for projects, assets, runs, and results, separate from the application.
5. Follow Workbench's runtime setup to install and verify the approved ARM64 runtime. Confirm **Settings → Runtime → Ready** before running models; keep Docker running.
6. Download optional package ZIPs from the [2.0 release](https://github.com/nikolasleeb/VisionEval-Workbench/releases/tag/v2.0.0). In **Settings → Assets**, select the intact ZIP, review its preview, and install. Do not unzip it first.

The current installer is Developer ID signed and notarized. Earlier ad-hoc signing and quarantine-removal workarounds do not apply.

See [Regional Packages](Regional-Packages) for data sources and [Workspaces and Resources](macOS-Workspaces-and-Resources) before increasing concurrency or moving to an SSD.
