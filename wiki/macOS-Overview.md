# Apple Silicon macOS Overview

The Apple Silicon edition supports M-series Macs running macOS 12 or newer and uses a managed ARM64 VisionEval runtime through Docker Desktop.

| Component | Apple Silicon behavior |
|---|---|
| Supported system | Apple Silicon Mac, macOS 12 or newer |
| VisionEval runtime | Digest-pinned ARM64 Docker image |
| Model execution | Temporary containers created only when required |
| Desktop shell | Native ARM64 Tauri app with the macOS webview |

> [!IMPORTANT]
> Intel Mac users must install the separate [Intel macOS edition](Intel-macOS-Overview). The installers and runtime images are not interchangeable.

## What works without Docker

You can explore inputs, create projects, manage the workspace, and use previously generated comparison caches without starting Docker. Docker is required for model runs and may be required to read uncached R data.

## Start here

1. Follow the [Apple Silicon installation guide](https://github.com/nikolasleeb/VisionEval-Workbench/blob/main/docs/tutorials/VisionEval-Workbench-Installation-macOS-Apple-Silicon.pdf).
2. [Install Workbench and its runtime](macOS-Installation-and-Runtime).
3. Learn the platform workflow in [Using Workbench on macOS](Using-Workbench-on-macOS).
4. Complete the [scenario walkthrough](https://github.com/nikolasleeb/VisionEval-Workbench/blob/main/docs/tutorials/VisionEval-Workbench-Scenario-Walkthrough.pdf).

**Developer path:** [Building the Apple Silicon macOS App](Building-the-macOS-App)
