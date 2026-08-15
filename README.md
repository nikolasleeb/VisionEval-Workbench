# VisionEval Workbench

VisionEval Workbench is an unofficial desktop application that brings the main steps of a VisionEval project into one place. It helps planners and analysts inspect model inputs, create scenarios, run models, and compare completed results without manually editing prepared model folders.

## Why it was created

VisionEval is powerful, but a complete workflow normally involves many folders, CSV files, scripts, runtime settings, and result files. Workbench was created to make that process easier to understand and repeat. It keeps the application, your workspace, regional packages, model runs, and results separate so the original source files are not changed.

## How it works

1. **Explore** input files, definitions, units, and relationships.
2. **Create** a project, preserve a baseline, and make scenario changes.
3. **Run** validated scenarios through the appropriate VisionEval runtime.
4. **Compare** completed datastores with tables, charts, maps, and exports.

## Windows and Mac versions

| | Windows | Mac |
|---|---|---|
| Supported system | Windows 11 x64 | Apple Silicon Mac with macOS 12 or newer |
| Installer | `VisionEval-Workbench-v1.0.0-windows-x64-setup.exe` | `VisionEval-Workbench-v1.0.0-macos-arm64.dmg` |
| VisionEval runtime | Connects to an existing native `VE_Runtime`, `VE_HOME`, and compatible R installation | Uses Docker Desktop and the managed ARM64 Workbench runtime image |
| Docker required | No | Yes, when running models or reading uncached R data |

The two applications are maintained separately because their runtime setup and operating-system integration are different. Their source code is available in the [`windows`](windows) and [`macos`](macos) folders.

## Download and install

Go to the [latest release](https://github.com/nikolasleeb/VisionEval-Workbench/releases/latest).

- **Windows:** download `VisionEval-Workbench-v1.0.0-windows-x64-setup.exe`, run the installer, and connect Workbench to an existing native VisionEval runtime.
- **Mac:** download `VisionEval-Workbench-v1.0.0-macos-arm64.dmg`, open it, and drag **VisionEval Workbench** to **Applications**. Install and start Docker Desktop before setting up the runtime in Workbench.

The Mac application is ad-hoc signed but is not Apple-notarized. If macOS blocks the first launch, follow the one-time Gatekeeper instructions in the [Mac installation guide](https://github.com/nikolasleeb/VisionEval-Workbench/wiki/macOS-Installation-and-Runtime).

## Regional packages

The release also includes two optional platform-neutral packages:

- `planrva-mm-1.0.0.zip` provides the PlanRVA multimodal model template and matching InputLibrary.
- `virginia-mpo-regions-2026.08.12.3.zip` provides Virginia MPO regional data and Region Builder support.

Do not unzip these packages. In Workbench, open **Settings → Assets**, choose the downloaded ZIP, review its information, and install it into your workspace.

## Help and documentation

The [Workbench wiki](https://github.com/nikolasleeb/VisionEval-Workbench/wiki) contains separate Windows and Mac instructions, workflow explanations, troubleshooting, and developer-oriented build notes.

If something fails, [open an issue](https://github.com/nikolasleeb/VisionEval-Workbench/issues) and include your operating system, Workbench version, runtime status, installed packages, and a diagnostic ZIP when available.

Official VisionEval documentation is available at [visioneval.org](https://visioneval.org/).

Developed by Nikolas Lee-Bishop.
