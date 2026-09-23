# Build Your Own Package

Workbench packages are ZIP files with one top-level folder containing `workbench-package.json` and the files listed in that manifest.

## Package types

A package can provide:

- a model template;
- an InputLibrary;
- input explanations;
- regional data and map context;
- any combination supported by the manifest.

The app installs packages only from **Settings → Assets → Add package**. It validates `workbench-package.json`, checks the listed file hashes, and then copies the package into the workspace.

## Minimum manifest expectations

Use stable IDs, a clear display name, a package version, source/provenance fields, and a complete file inventory with sizes and SHA-256 hashes. Regional packages should also include a `SOURCES.md` file that explains source data, processing rules, and known limitations.

## Model and InputLibrary pairing

If a package generates or ships a model template and InputLibrary that must be used together, mark them with a shared pair identifier. Workbench can then auto-select the paired asset and prevent accidental region/template mismatches.

## Regional packages

A regional package should define:

- region records shown in Create → Develop;
- the InputLibrary used to build regional assets;
- any model-template scaffold needed for runnable output;
- geographic identifiers and crosswalks;
- map capabilities and supported geography levels;
- source documentation and build assumptions.

Do not redistribute third-party raw geometry unless the source license permits it. The Virginia package stores reproducible identifiers and crosswalks, then downloads official geometry on demand and caches it locally.

## Recommended build workflow

1. Create the package folder.
2. Add model, input, regional, and documentation files.
3. Generate `workbench-package.json` with every packaged file listed.
4. Zip the top-level package folder.
5. Install the ZIP into a clean Workbench workspace.
6. Create a small project, run it, compare outputs, export diagnostics if anything fails, and update `SOURCES.md`.
