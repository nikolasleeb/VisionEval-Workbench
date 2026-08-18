# VisionEval Workbench 1.0.0

This is the first public release of the clean VisionEval Workbench repository. It provides separate desktop applications for Windows 11 x64, Apple Silicon macOS, and Intel macOS.

## Downloads

- **Windows 11 x64:** `VisionEval-Workbench-v1.0.0-windows-x64-setup.exe`
- **Apple Silicon macOS:** `VisionEval-Workbench-v1.0.0-macos-arm64.dmg`
- **Intel macOS:** `VisionEval-Workbench-v1.0.0-macos-x64.dmg`
- **Intel source snapshot:** `VisionEval-Workbench-v1.0.0-intel-source.zip`
- **PlanRVA model package:** `planrva-mm.zip`
- **Virginia MPO regional package:** `virginia-mpo-regions.zip`

Exact platform source snapshots are also attached. GitHub additionally supplies automatic source archives for the full repository.

## Tutorials and guides

The release includes four PDF guides: installation and setup for Windows 11 x64, Apple Silicon macOS, and Intel macOS, plus a screenshot-driven Charlottesville–Albemarle scenario walkthrough. Editable Word copies are maintained in [`docs/tutorials`](docs/tutorials/README.md).

## Platform differences

The Windows application connects to an existing native `VE_Runtime`, its `VE_HOME` package library, and a compatible `Rscript.exe`. It does not use Docker.

The Mac applications use Docker Desktop with architecture-specific, digest-pinned Workbench runtimes published through GitHub Packages: ARM64 for Apple Silicon and AMD64 for Intel. Both guide users through runtime installation and verification.

All three applications provide the Explore, Create, Run, and Compare workflow while retaining their platform-specific runtime and operating-system behavior.

The refreshed Mac builds keep first-launch runtime downloads in background operations so long image pulls can finish and persist their verified profiles. The Apple Silicon build preserves the current ARM64 profile rather than treating it as a legacy alias. Both Mac builds use the macOS trust store for official HTTPS map services.

## Important notes

- The Mac application is ad-hoc signed for bundle integrity but is not Apple-notarized.
- Each Mac DMG is architecture-specific; use the ARM64 build on Apple Silicon and the x64 build on Intel.
- The runtime is an unofficial distribution built from VisionEval VE-40-RC6 and includes the documented Workbench compatibility patch.
- Regional planning data are provided as-is and are installed separately through **Settings → Assets**.
