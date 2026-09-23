# VisionEval Workbench

VisionEval Workbench is an unofficial desktop application that brings the main steps of a VisionEval project into one place. It helps planners and analysts inspect model inputs, create scenarios, run models, and compare completed results without manually editing prepared model folders.

## Why it was created

VisionEval is powerful, but a complete workflow normally involves many folders, CSV files, scripts, runtime settings, and result files. Workbench was created to make that process easier to understand and repeat. It keeps the application, your workspace, regional packages, model runs, and results separate so the original source files are not changed.

## How it works

1. **Explore** input files, definitions, units, and relationships.
2. **Create** a project, preserve a baseline, and make scenario changes.
3. **Run** validated scenarios through the appropriate VisionEval runtime.
4. **Compare** completed datastores with tables, charts, maps, and exports.
5. **Hypercube** builds and analyzes bounded scenario matrices.

## Supported editions

| Edition | Supported system | Installer | VisionEval runtime |
|---|---|---|---|
| Windows | Windows 11 x64 | `VisionEval-Workbench-v2.0.0-windows-x64-setup.exe` | Existing native VisionEval VE-40-RC7 and compatible R, or the optional current-user runtime setup |
| Apple Silicon Mac | macOS 12 or newer | `VisionEval-Workbench-v2.0.0-macos-arm64.dmg` | Docker Desktop with the verified ARM64 Workbench runtime |

Version 2.0 does not include an Intel Mac installer. Earlier Intel releases remain available in [past releases](https://github.com/nikolasleeb/VisionEval-Workbench/releases).

The editions are maintained separately because their runtime setup and operating-system integration differ. Their source code is available in the [`windows`](windows), [`macos`](macos), and [`intel`](intel) folders.

## Download and install

Go to the [latest release](https://github.com/nikolasleeb/VisionEval-Workbench/releases/latest).

- **Windows:** download `VisionEval-Workbench-v2.0.0-windows-x64-setup.exe` and run the installer. Workbench can connect to an existing native runtime or offer the verified current-user R 4.5.3 and VisionEval VE-40-RC7 setup. The installer is unsigned, so Windows SmartScreen may show an unknown-publisher warning. Verify its SHA-256 in the release notes before deciding whether to run it.
- **Apple Silicon Mac:** download `VisionEval-Workbench-v2.0.0-macos-arm64.dmg`, open it, and drag **VisionEval Workbench** to **Applications**. The app is Developer ID signed and Apple notarized. Install Docker Desktop for Apple silicon and follow the runtime setup in Workbench.

The v2.0 tag includes the complete Mac and Windows source. GitHub provides source ZIP and TAR archives automatically.

## Regional packages

The release includes three optional platform-neutral packages:

- `planrva-2.0.zip` provides the PlanRVA model template and matching InputLibrary.
- `virginia-mpo-regions-2.0.zip` provides Virginia MPO regional data and Region Builder support.
- `wppdc-2.0.zip` provides the WPPDC regional package.

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
