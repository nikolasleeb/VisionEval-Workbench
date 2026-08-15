# Building the Windows App

The Windows source is in `windows/`. The application combines:

- a Tauri/Rust desktop host;
- a static HTML, CSS, and JavaScript interface rendered by WebView2;
- a Python backend bundled as a sidecar;
- native VisionEval and R process execution.

Development requires Node.js 20, Python 3.11, Rust, the Tauri Windows prerequisites, and the Python packages listed in `windows/packaging/requirements-backend.txt`.

The release workflow installs dependencies, validates generated assets and documentation, runs Python and JavaScript tests, runs Rust formatting/tests, builds the Python sidecar, performs the frozen WebView2 renderer smoke gate, and creates the NSIS x64 installer.

The Windows source is intentionally maintained separately from the Mac source. Platform behavior should not be synchronized automatically.
