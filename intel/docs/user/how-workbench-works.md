# How Workbench Works on Windows

Workbench keeps the application, workspace, connected native runtime, installed assets, and run outputs separate.

## Application

The Windows x64 app starts a local backend and opens the Workbench interface in WebView2. Installing a newer Workbench version does not replace your workspace or `VE_Runtime`.

## Workspace

The workspace stores projects, installed packages, generated regional assets, prepared runs, logs, registered results, caches, and user notes. A new user chooses this location on first launch.

## Assets

Regional packages are installed from **Settings > Assets**. They can provide model templates, InputLibraries, input explanations, regional definitions, map context, and package documentation. Workbench copies approved assets into the workspace and does not alter the source archive.

## Native runtime

Workbench connects to an existing `VE_RUNTIME` working folder, its `VE_HOME` VisionEval package library, and a compatible `Rscript.exe`. Verification starts that R installation and reports what it finds; it does not download, update, patch, or replace the runtime. Windows jobs run one at a time through this verified native connection.

## Projects and scenarios

A project pins a model template and InputLibrary. A scenario stores notes and deliberate CSV edits. Each run prepares a fresh model copy from the pinned assets, applies the scenario overlay, and writes a reproducible run record.

## Results and comparison

Successful runs register their VisionEval datastore. Compare reads the RDA datastore as the authority and may build disposable caches for paging, statistics, changed-output scans, maps, charts, and exports.
