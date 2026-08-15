# Building the macOS App

The Apple Silicon source is in `macos/`. The application combines:

- a Tauri/Rust desktop host;
- a static HTML, CSS, and JavaScript interface rendered by the macOS webview;
- a Python backend bundled as a sidecar;
- Docker-based VisionEval execution.

Development requires Node.js 20, Python 3.11, Rust with the `aarch64-apple-darwin` target, Xcode command-line tools, and Docker Desktop for runtime testing.

The release workflow validates generated assets and documentation, runs Python and JavaScript tests, runs Rust formatting/tests, builds the sidecar and ARM64 application, ad-hoc signs the bundle, verifies the signature, and packages the app in a DMG.

The Mac source is intentionally maintained separately from the Windows source. Its guided Docker setup and runtime behavior should remain Mac-specific.

The Intel build has its own source and release process in `intel/`; see [Building the Intel macOS App](Building-the-Intel-macOS-App).
