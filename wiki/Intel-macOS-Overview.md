# Intel macOS Overview

The Intel edition supports Intel Macs running macOS 12 or newer and uses a managed AMD64 VisionEval runtime through Docker Desktop.

| Component | Intel behavior |
|---|---|
| Supported system | Intel Mac, macOS 12 or newer |
| VisionEval runtime | Digest-pinned AMD64 Docker image |
| Model execution | Temporary containers created only when required |
| Desktop shell | Native x86_64 Tauri app with the macOS webview |

> [!IMPORTANT]
> Apple Silicon users must install the separate [Apple Silicon edition](macOS-Overview). The installers and runtime images are not interchangeable.

## What works without Docker

You can explore inputs, create projects, manage the workspace, and use previously generated comparison caches without starting Docker. Docker is required for model runs and may be required to read uncached R data.

## Start here

1. Follow the [Intel macOS installation guide](https://github.com/nikolasleeb/VisionEval-Workbench/blob/main/docs/tutorials/VisionEval-Workbench-Installation-macOS-Intel.pdf).
2. [Install Workbench and its runtime](Intel-macOS-Installation-and-Runtime).
3. Learn the platform workflow in [Using Workbench on Intel macOS](Using-Workbench-on-Intel-macOS).
4. Complete the [scenario walkthrough](https://github.com/nikolasleeb/VisionEval-Workbench/blob/main/docs/tutorials/VisionEval-Workbench-Scenario-Walkthrough.pdf).

**Developer path:** [Building the Intel macOS App](Building-the-Intel-macOS-App)
