# Building the Intel macOS App

The Intel source is in `intel/`. The application combines a Tauri/Rust desktop host, static web interface, bundled Python sidecar, and Docker-based VisionEval execution.

Development requires an Intel Mac, Node.js 20, Python 3.11, Rust with the `x86_64-apple-darwin` target, Xcode command-line tools, and Docker Desktop for runtime testing.

The AMD64 runtime must be published and its immutable digest committed before a release build. The Intel release workflow validates generated assets and documentation, runs Python, JavaScript, and Rust tests, builds native x86_64 app and sidecar binaries, rejects ARM64 binaries, ad-hoc signs the bundle, mounts and verifies the DMG, and creates the exact Intel source ZIP.

The release assets are `VisionEval-Workbench-v1.0.0-macos-x64.dmg` and `VisionEval-Workbench-v1.0.0-intel-source.zip`.
