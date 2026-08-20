# VisionEval Workbench

VisionEval Workbench is an unofficial desktop application that brings the main steps of a VisionEval project into one place. It helps planners and analysts inspect model inputs, create scenarios, run models, and compare completed results without manually editing prepared model folders.

## Why it was created

VisionEval is powerful, but a complete workflow normally involves many folders, CSV files, scripts, runtime settings, and result files. Workbench was created to make that process easier to understand and repeat. It keeps the application, your workspace, regional packages, model runs, and results separate so the original source files are not changed.

## How it works

1. **Explore** input files, definitions, units, and relationships.
2. **Create** a project, preserve a baseline, and make scenario changes.
3. **Run** validated scenarios through the appropriate VisionEval runtime.
4. **Compare** completed datastores with tables, charts, maps, and exports.

## Supported editions

| Edition | Supported system | Installer | VisionEval runtime |
|---|---|---|---|
| Windows | Windows 11 x64 | `VisionEval-Workbench-v1.0.1-windows-x64-setup.exe` | Existing native `VE_Runtime`, `VE_HOME`, and compatible R installation |
| Apple Silicon Mac | macOS 12 or newer | `VisionEval-Workbench-v1.0.0-macos-arm64.dmg` | Docker Desktop with the managed ARM64 Workbench runtime |
| Intel Mac | macOS 12 or newer | `VisionEval-Workbench-v1.0.0-macos-x64.dmg` | Docker Desktop with the managed AMD64 Workbench runtime |

The editions are maintained separately because their runtime setup and operating-system integration differ. Their source code is available in the [`windows`](windows), [`macos`](macos), and [`intel`](intel) folders.

## Download and install

Go to the [latest release](https://github.com/nikolasleeb/VisionEval-Workbench/releases/latest).

- **Windows:** download `VisionEval-Workbench-v1.0.1-windows-x64-setup.exe`, run the installer, and connect Workbench to an existing native VisionEval runtime.
- **Apple Silicon Mac:** download `VisionEval-Workbench-v1.0.0-macos-arm64.dmg`, open it, and drag **VisionEval Workbench** to **Applications**. Install Docker Desktop for Apple silicon before setting up the runtime.
- **Intel Mac:** download `VisionEval-Workbench-v1.0.0-macos-x64.dmg`, open it, and drag **VisionEval Workbench** to **Applications**. Install Docker Desktop for Mac with an Intel chip before setting up the runtime.

The release also provides `VisionEval-Workbench-v1.0.0-intel-source.zip`, an exact buildable snapshot of the Intel source tree.

The Mac applications are ad-hoc signed but are not Apple-notarized. If macOS blocks the first launch, follow the one-time Gatekeeper instructions in the matching [Apple Silicon](https://github.com/nikolasleeb/VisionEval-Workbench/wiki/macOS-Installation-and-Runtime) or [Intel](https://github.com/nikolasleeb/VisionEval-Workbench/wiki/Intel-macOS-Installation-and-Runtime) installation guide.

## Regional packages

The release also includes two optional platform-neutral packages:

- `planrva-mm.zip` provides PlanRVA MM 2.0, including the original working model template and InputLibrary plus the Virginia comparison-map provider.
- `virginia-mpo-regions.zip` provides Virginia MPO regional data and Region Builder support.

Do not unzip these packages. In Workbench, open **Settings → Assets**, choose the downloaded ZIP, review its information, and install it into your workspace.

PlanRVA 2.0 does not require the Virginia MPO package. On the first comparison-map use, Workbench downloads Virginia MPO, Azone, and Bzone geometry from the official ArcGIS services and saves it in the shared Virginia cache. Later map uses can reuse that cache offline; installing the Virginia MPO package remains optional and uses the same cache.

## Tutorials

The repository includes a screenshot-driven scenario walkthrough and separate installation guidance for Windows 11 x64, Apple Silicon macOS, and Intel macOS. The Windows installation PDF and editable Word guide remain accurate for installing version 1.0.1. The text-based User Guide provides additional operating and troubleshooting detail.

- [Browse all tutorials and walkthroughs](docs/tutorials/README.md)
- [Scenario walkthrough (PDF)](docs/tutorials/VisionEval-Workbench-Scenario-Walkthrough.pdf)
- [Windows 11 x64 installation guide](docs/tutorials/VisionEval-Workbench-Installation-Windows-x64.pdf)
- [Windows User Guide](windows/UserGuide.md)
- [Apple Silicon macOS installation guide (PDF)](docs/tutorials/VisionEval-Workbench-Installation-macOS-Apple-Silicon.pdf)
- [Intel macOS installation guide (PDF)](docs/tutorials/VisionEval-Workbench-Installation-macOS-Intel.pdf)

The two macOS editions require different installers and runtime images. Choose the Apple Silicon guide for M-series Macs and the Intel guide for Intel-based Macs.

## Help and documentation

The [Workbench wiki](https://github.com/nikolasleeb/VisionEval-Workbench/wiki) contains separate Windows, Apple Silicon macOS, and Intel macOS instructions, workflow explanations, troubleshooting, tutorials, and developer-oriented build notes.

If something fails, [open an issue](https://github.com/nikolasleeb/VisionEval-Workbench/issues) and include your operating system, Workbench version, runtime status, installed packages, and a diagnostic ZIP when available.

Official VisionEval documentation is available at [visioneval.org](https://visioneval.org/).

Developed by Nikolas Lee-Bishop.
