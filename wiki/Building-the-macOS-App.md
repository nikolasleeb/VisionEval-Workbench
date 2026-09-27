# Building the Apple Silicon macOS App

This page is for contributors building the native ARM64 edition from the separate `macos/` source tree.

## Components

- Tauri/Rust desktop host
- Static HTML, CSS, and JavaScript interface rendered by the macOS webview
- Python backend bundled as a sidecar
- Docker-based VisionEval execution

## Requirements

- Apple Silicon Mac
- Node.js 20 and Python 3.11
- Rust with the `aarch64-apple-darwin` target
- Xcode command-line tools
- Docker Desktop for runtime testing

## Release verification

For the current Mac 2.0 release, the public app and DMG are Developer ID signed and Apple notarized. Use the current macos packaging scripts and release verification instructions in the repository when preparing a release; older ad-hoc packaging does not describe the public 2.0 installer. This guide publication changes documentation only and does not rebuild the application.

> [!IMPORTANT]
> Apple Silicon, Intel, and Windows source trees are maintained separately because their runtime and operating-system integration differ.

**Related:** [Architecture and Developer Overview](Architecture-and-Developer-Overview) · [Building the Intel macOS App](Building-the-Intel-macOS-App)
