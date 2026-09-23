# How Workbench Works on Windows

Workbench keeps the application, workspace, connected native runtime, installed assets, and run outputs separate.

## Application

The Windows x64 app starts a local backend and opens the Workbench interface in WebView2. Installing a newer Workbench version does not replace your workspace or `VE_Runtime`.

## Workspace

The workspace stores projects, installed packages, generated regional assets, prepared runs, logs, registered results, caches, and user notes. A new user chooses this location on first launch.

## Assets

Regional packages are installed from **Settings > Assets**. They can provide model templates, InputLibraries, input explanations, regional definitions, map context, and package documentation. Workbench copies approved assets into the workspace and does not alter the source archive.

## Native runtime

Workbench connects to independently selected `VE_RUNTIME`, `VE_HOME`, and `Rscript.exe` paths. If no usable runtime exists, its no-admin managed installer can install the pinned R 4.5.3 and VisionEval RC7 pair for the current user. Validation rejects equal or nested runtime/home paths, including overlaps hidden by junctions or symbolic links. Windows jobs run one at a time through the verified native connection.

## Projects and scenarios

A project pins a model template and InputLibrary. A scenario stores notes and deliberate CSV edits. Each run prepares a fresh model copy from the pinned assets, applies the scenario overlay, and writes a reproducible run record.

## Results and comparison

Successful runs register their VisionEval datastore. Compare reads the RDA datastore as the authority and may build disposable caches for paging, statistics, changed-output scans, maps, charts, and exports.
