# VisionEval Workbench

VisionEval Workbench is an unofficial desktop application that brings the main steps of a VisionEval project into one place. It helps planners and analysts inspect model inputs, create scenarios, run models, and compare completed results without manually editing prepared model folders.

## Get Version 2.0

| Computer | Download | Runtime |
|---|---|---|
| Apple Silicon Mac | [Download the macOS installer (DMG)](https://github.com/nikolasleeb/VisionEval-Workbench/releases/download/v2.0.0/VisionEval-Workbench-v2.0.0-macos-arm64.dmg) | Docker Desktop and the verified ARM64 Workbench runtime |
| Windows 11 x64 | [Download the Windows installer (EXE)](https://github.com/nikolasleeb/VisionEval-Workbench/releases/download/v2.0.0/VisionEval-Workbench-v2.0.0-windows-x64-setup.exe) | Native VisionEval VE-40-RC7, existing or installed through Workbench setup |

See the [Version 2.0 release page](https://github.com/nikolasleeb/VisionEval-Workbench/releases/tag/v2.0.0) for what's new and the optional regional packages. Version 2.0 does not include an Intel Mac installer. The Windows installer is unsigned, so Windows SmartScreen may show an unknown-publisher warning; the macOS app is Developer ID signed and notarized.

## Why it was created

VisionEval is powerful, but a complete workflow normally involves many folders, CSV files, scripts, runtime settings, and result files. Workbench was created to make that process easier to understand and repeat. It keeps the application, your workspace, regional packages, model runs, and results separate so the original source files are not changed.

## How it works

1. **Explore** input files, definitions, units, and relationships.
2. **Create** a project, preserve a baseline, and make scenario changes.
3. **Run** validated scenarios through the appropriate VisionEval runtime.
4. **Compare** completed datastores with tables, charts, maps, and exports.
5. **Hypercube** builds and analyzes bounded scenario matrices.

## Supported editions

The current release supports Windows 11 x64 and Apple Silicon Macs running macOS 12 or newer. Earlier Intel releases remain available in [past releases](https://github.com/nikolasleeb/VisionEval-Workbench/releases).

The editions are maintained separately because their runtime setup and operating-system integration differ. Their source code is available in the [`windows`](windows), [`macos`](macos), and [`intel`](intel) folders.

## Download and install

Use the direct installer links above, or browse the [latest release](https://github.com/nikolasleeb/VisionEval-Workbench/releases/latest).

- **Windows:** run the installer. Workbench can connect to an existing native runtime or offer the verified current-user R 4.5.3 and VisionEval VE-40-RC7 setup. The installer is unsigned, so Windows SmartScreen may show an unknown-publisher warning. Download it only from this official release and review the publisher warning before proceeding.
- **Apple Silicon Mac:** download `VisionEval-Workbench-v2.0.0-macos-arm64.dmg`, open it, and drag **VisionEval Workbench** to **Applications**. The app is Developer ID signed and Apple notarized. Install Docker Desktop for Apple silicon and follow the runtime setup in Workbench.

The v2.0 tag includes the complete Mac and Windows source. GitHub provides source ZIP and TAR archives automatically.

## Regional packages

The release includes three optional platform-neutral packages:

- [PlanRVA package](https://github.com/nikolasleeb/VisionEval-Workbench/releases/download/v2.0.0/planrva-2.0.zip) provides the model template and matching InputLibrary.
- [Virginia MPO regions package](https://github.com/nikolasleeb/VisionEval-Workbench/releases/download/v2.0.0/virginia-mpo-regions-2.0.zip) provides regional data and Region Builder support.
- [WPPDC package](https://github.com/nikolasleeb/VisionEval-Workbench/releases/download/v2.0.0/wppdc-2.0.zip) provides the WPPDC regional package.

Do not unzip these packages. In Workbench, open **Settings → Assets**, choose the downloaded ZIP, review its information, and install it into your workspace.

## Tutorials

The v2.0 applications include their current User Guide and What's New documents under **Settings → Documentation**. Earlier installation tutorials in this repository describe previous versions and are being refreshed for v2.0.

- [Browse all tutorials and walkthroughs](docs/tutorials/README.md)
- [Scenario walkthrough (PDF)](docs/tutorials/VisionEval-Workbench-Scenario-Walkthrough.pdf)
- [Windows User Guide](windows/UserGuide.md)
- [Apple Silicon macOS User Guide](macos/UserGuide.md)

Visit the [VisionEval Workbench website](https://sites.google.com/view/ve-workbench/home) for additional guidance and future Version 2 tutorials.

## Help and documentation

The [Workbench wiki](https://github.com/nikolasleeb/VisionEval-Workbench/wiki) contains additional workflow and developer information. Check the bundled Version 2 guides for the current application behavior.

If something fails, [open an issue](https://github.com/nikolasleeb/VisionEval-Workbench/issues) and include your operating system, Workbench version, runtime status, installed packages, and a diagnostic ZIP when available.

Official VisionEval documentation is available at [visioneval.org](https://visioneval.org/).

Developed by Nikolas Lee-Bishop.
