# How Workbench Works

Workbench keeps the application, workspace, packages, Docker runtime, and run outputs separate.

## Application

The macOS app starts a local backend and opens the Workbench interface. The app can be replaced by a newer DMG without replacing your workspace.

## Workspace

The workspace stores projects, imported packages, generated regional assets, run records, logs, registered results, caches, and user notes. A new user chooses this location on first launch.

## Packages

Packages are installed from **Settings → Assets** as ZIP files or selected extracted folders. The standard app does not include the PlanRVA or Virginia MPO packages. A package may provide model templates, InputLibraries, input explanations, regional definitions, map context, and package documentation.

## Runtime

Docker Desktop is required only for **Run**. Workbench downloads the compatible GHCR runtime image, tags the expected local alias, verifies the image identity, and records the immutable digest. A VisionEval container is created only for a model job and is stopped when the job ends or Workbench quits.

## Projects and scenarios

A project pins a model template and InputLibrary. A scenario stores notes and deliberate CSV edits. Each run prepares a fresh model copy from the pinned assets, applies the scenario overlay, and writes a reproducible run record.

## Results and comparison

Successful runs register their VisionEval datastore. Compare reads the RDA datastore as the authority and may build disposable caches for paging, statistics, changed-output scans, maps, charts, and exports.
