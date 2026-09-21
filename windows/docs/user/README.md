# VisionEval Workbench User Guide for Windows

VisionEval Workbench 2.0.0 is a native Windows x64 desktop application for inspecting VisionEval inputs, designing repeatable scenarios and bounded Hypercubes, running them through an existing `VE_Runtime`, and analyzing completed datastores. Project data remains in the workspace you select.

The normal workflow has five parts:

1. **Explore** input files and model dependencies.
2. **Create** a baseline and edited scenarios.
3. **Run** VisionEval through the verified native runtime.
4. **Compare** completed datastores and maps.
5. **Hypercube** creates and analyzes bounded two-parameter experiments.

![Workbench workflow](images/workflow-overview.svg)

## How it works

- Workbench connects to your existing `VE_RUNTIME` working folder, `VE_HOME` package library, and compatible `Rscript.exe`.
- Installed regional packages provide compatible model templates, InputLibraries, and map context.
- Saved scenarios record deliberate CSV changes and notes. Each run prepares a fresh model copy, applies the selected scenario, and preserves provenance.
- Windows jobs run one at a time through the native runtime. Workbench owns the prepared models, logs, and results in its workspace and does not modify the runtime installation.
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
