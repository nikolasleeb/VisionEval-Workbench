# VisionEval Workbench 1.0.0

This is the first public release of the clean VisionEval Workbench repository. It provides separate, validated desktop applications for Windows 11 x64 and Apple Silicon macOS.

## Downloads

- **Windows 11 x64:** `VisionEval-Workbench-v1.0.0-windows-x64-setup.exe`
- **Apple Silicon macOS:** `VisionEval-Workbench-v1.0.0-macos-arm64.dmg`
- **PlanRVA model package:** `planrva-mm.zip`
- **Virginia MPO regional package:** `virginia-mpo-regions.zip`

Exact platform source snapshots are also attached. GitHub additionally supplies automatic source archives for the full repository.

## Platform differences

The Windows application connects to an existing native `VE_Runtime`, its `VE_HOME` package library, and a compatible `Rscript.exe`. It does not use Docker.

The Mac application supports Apple Silicon and uses Docker Desktop with the pinned ARM64 Workbench runtime published through GitHub Packages. It can guide users through runtime installation and verification.

Both applications provide the Explore, Create, Run, and Compare workflow, while retaining the platform-specific behavior for which each was built and validated.

## Important notes

- The Mac application is ad-hoc signed for bundle integrity but is not Apple-notarized.
- Intel Macs and Windows systems other than Windows 11 x64 have not been validated.
- The runtime is an unofficial distribution built from VisionEval VE-40-RC6 and includes the documented Workbench compatibility patch.
- Regional planning data are provided as-is and are installed separately through **Settings → Assets**.
