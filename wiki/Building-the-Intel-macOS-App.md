# Building the Intel macOS App

This page is for contributors building the native x86_64 edition from the separate `intel/` source tree.

## Components

- Tauri/Rust desktop host
- Static HTML, CSS, and JavaScript interface rendered by the macOS webview
- Python backend bundled as a sidecar
- Docker-based AMD64 VisionEval execution

## Requirements

- Intel Mac
- Node.js 20 and Python 3.11
- Rust with the `x86_64-apple-darwin` target
- Xcode command-line tools
- Docker Desktop for runtime testing

## Runtime publication

The AMD64 runtime must be published and its immutable digest committed before a release build.

## Release verification

The workflow validates generated assets and documentation; runs Python, JavaScript, and Rust tests; builds native x86_64 app and sidecar binaries; rejects ARM64 binaries; ad-hoc signs the bundle; mounts and verifies the DMG; and creates the exact Intel source ZIP.

Release assets are `VisionEval-Workbench-v1.0.0-macos-x64.dmg` and `VisionEval-Workbench-v1.0.0-intel-source.zip`.

**Related:** [Architecture and Developer Overview](Architecture-and-Developer-Overview) · [Intel macOS Overview](Intel-macOS-Overview)
