# Building the Windows App

This page is for contributors building the Windows 11 x64 edition from the separate `windows/` source tree.

## Components

- Tauri/Rust desktop host
- Static HTML, CSS, and JavaScript interface rendered by WebView2
- Python backend bundled as a sidecar
- Native VisionEval and R process execution

## Requirements

- Node.js 20
- Python 3.11 and `windows/packaging/requirements-backend.txt`
- Rust and the Tauri Windows prerequisites
- A compatible native VisionEval runtime for integration testing

## Release verification

The release workflow installs dependencies, validates generated assets and documentation, runs Python and JavaScript tests, runs Rust formatting and tests, builds the Python sidecar, performs the frozen WebView2 renderer smoke gate, and creates the NSIS x64 installer.

> [!IMPORTANT]
> Windows source is intentionally maintained separately from the Mac source. Platform behavior must not be synchronized automatically.

**Related:** [Architecture and Developer Overview](Architecture-and-Developer-Overview) · [Windows Overview](Windows-Overview)
