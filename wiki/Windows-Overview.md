# Windows Overview

The Windows edition supports Windows 11 x64. It is designed for organizations that already maintain a native VisionEval runtime.

Workbench stores projects, scenarios, packages, logs, and results in a separate workspace. It connects to—but does not install, replace, or modify—your selected `VE_Runtime`, `VE_HOME`, or R installation.

The desktop shell uses Tauri and Microsoft WebView2. A bundled local Python service performs file, model, comparison, export, and runtime operations. Windows model jobs run one at a time through the verified native runtime.

Next: [Windows Installation and Runtime](Windows-Installation-and-Runtime).
