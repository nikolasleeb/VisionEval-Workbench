# VisionEval Workbench User Guide for Windows

VisionEval Workbench 2.0.0 is a native Windows x64 desktop application for inspecting VisionEval inputs, designing repeatable scenarios and bounded Hypercubes, running them through a verified `VE_RUNTIME`, and analyzing completed datastores. It can connect to an existing installation or install the certified R 4.5.3 and VisionEval RC7 pair for the current user. Project data remains in the workspace you select.

The normal workflow has five parts:

1. **Explore** input files and model dependencies.
2. **Create** a baseline and edited scenarios.
3. **Run** VisionEval through the verified native runtime.
4. **Compare** completed datastores and maps.
5. **Hypercube** creates and analyzes bounded two-parameter experiments.

![Workbench workflow](images/workflow-overview.svg)

## How it works

- Workbench discovers or independently selects `VE_RUNTIME`, `VE_HOME`, and a compatible `Rscript.exe`; its optional managed installation requires no administrator privileges.
- Installed regional packages provide compatible model templates, InputLibraries, and map context.
- Saved scenarios record deliberate CSV changes and notes. Each run prepares a fresh model copy, applies the selected scenario, and preserves provenance.
- Windows jobs run one at a time through the native runtime. Workbench owns the prepared models, logs, and results in its workspace. A managed runtime installation occurs only after explicit approval and never places `VE_RUNTIME` inside `VE_HOME`.
- Successful datastores are registered for Compare. A disposable cache accelerates filtering, statistics, maps, and exports while the RDA datastore remains authoritative.

## Start here

- [Connect VE_Runtime](setup.md)
- [Getting started](getting-started.md)
- [Core concepts and glossary](core-concepts.md)
- [Explore inputs and dependencies](explore.md)
- [Create and review scenarios](create-and-review.md)
- [Run VisionEval](run.md)
- [Compare results](compare.md)
- [Create, run, analyze, and export Hypercubes](hypercube.md)
- [Settings, workspaces, and storage](settings-workspaces-storage.md)
- [Units, rounding, and provenance](data-units-provenance.md)
- [Troubleshooting](troubleshooting.md)
- [Keyboard shortcuts](keyboard-shortcuts.md)
- [Future improvements](future-improvements.md)

## Before connecting the runtime

You can open Workbench, manage the workspace, explore installed inputs, create scenarios, and inspect already registered results. A verified native runtime connection is required to start a new VisionEval run.

## Your notes are safe

Workbench refreshes this managed guide during upgrades. Put personal documentation in `Documentation/User Notes/`; upgrades never replace those files.
