# VisionEval Workbench 2.0.0

Version 2.0.0 brings a complete Hypercube workflow, improved scenario editing and validation, faster cached analysis, and platform-specific runtime setup to Apple Silicon macOS and Windows x64.

## Version 2.0 downloads

- **Apple Silicon macOS:** `VisionEval-Workbench-v2.0.0-macos-arm64.dmg` — Developer ID signed, notarized, and stapled. Requires Docker Desktop and the verified ARM64 VisionEval runtime.
- **Windows 11 x64:** `VisionEval-Workbench-v2.0.0-windows-x64-setup.exe` — native VisionEval execution. Connect an existing compatible R and VE-40-RC7 installation or use the optional current-user runtime setup. The installer is **unsigned**; Windows SmartScreen may display an unknown-publisher warning.
- **Asset packages:** `planrva-2.0.zip`, `virginia-mpo-regions-2.0.zip`, and `wppdc-2.0.zip` are installed separately through **Settings → Assets**.

The [v2.0.0 release page](https://github.com/nikolasleeb/VisionEval-Workbench/releases/tag/v2.0.0) lists SHA-256 checksums for every download. GitHub also supplies source archives for the release tag. The runtime index is published separately with the `runtime-VE-40-RC7` metadata release.

## New in Version 2

- **Hypercube:** build a bounded parameter matrix, preview and run its cases, monitor one compact batch with an estimated remaining time, and stop or retry that Hypercube without disturbing unrelated work.
- **Analysis:** compare completed results in cached Response Matrices; use **Find All Changes** to rank outputs and scenarios across a Hypercube, inspect a variable's case ranking, and export up to three completed cases or the baseline as separate CSV ZIP packages.
- **Scenario editing:** edit eligible categorical values, validate numeric ranges and whole-number counts, and edit linked share groups together. Batch Change validates all selected files before saving.
- **Queues and recovery:** Standard and Hypercube work share a persistent queue. The Windows native runtime uses one execution slot; macOS can run verified Docker jobs in parallel when resources allow.
- **Documentation:** current User Guide and What's New documents are available in **Settings → Documentation**, alongside a link to the VisionEval Workbench website.

Standard runs keep their authoritative Datastores and can optionally retain full output CSV exports. Hypercube runs retain Datastores without persistent full output CSV trees. Compare and Hypercube Analysis use disposable caches built from the Datastores.

## Earlier release notes: Version 1.1.0

Version 1.1.0 adds the runtime compatibility contract and the official VisionEval VE-40-RC7 runtime for Apple Silicon and Intel Macs. Existing verified RC6 images remain supported as the rollback profile.

## Downloads

- **Windows 11 x64:** `VisionEval-Workbench-v1.0.1-windows-x64-setup.exe`
- **Apple Silicon macOS:** `VisionEval-Workbench-v1.1.0-macos-arm64.dmg`
- **Intel macOS:** `VisionEval-Workbench-v1.1.0-macos-x64.dmg`
- **Intel source snapshot:** `VisionEval-Workbench-v1.1.0-intel-source.zip`
- **PlanRVA model package:** `planrva-2.2.zip`
- **Virginia MPO regional package:** `virginia-mpo-regions.zip`

Exact platform source snapshots are also attached. GitHub additionally supplies automatic source archives for the full repository.

## Windows 1.0.1 patch

Windows 1.0.1 makes native `VE_Runtime` execution strictly serial across jobs, Workbench windows, and backend processes. It keeps onboarding and settings dialogs above the taskbar, restores both About views, and checks GitHub weekly for newer stable Workbench releases using the Windows certificate trust store.

Application errors are retained for 30 days or 500 entries and can be cleared without deleting failed runs or results. Cancelling a run now stops the complete native R process tree and retries cleanup while Windows releases temporary file locks. Settings spacing is also corrected for Numbers, Notifications, and Resources.

Use the [Windows installation guide](docs/tutorials/VisionEval-Workbench-Installation-Windows-x64.pdf) for illustrated setup instructions. Its [editable Word version](docs/tutorials/VisionEval-Workbench-Installation-Windows-x64.docx) is also available. The [Windows User Guide](windows/UserGuide.md) provides additional operating and troubleshooting detail.

## Tutorials and guides

The release includes installation guides for Windows 11 x64, Apple Silicon macOS, and Intel macOS; the text-based Windows User Guide; and a screenshot-driven Charlottesville–Albemarle scenario walkthrough. Editable tutorial files are maintained in [`docs/tutorials`](docs/tutorials/README.md).

## Platform differences

The Windows application connects to an existing native `VE_Runtime`, its `VE_HOME` package library, and a compatible `Rscript.exe`. It does not use Docker.

The Mac applications use Docker Desktop with architecture-specific, digest-pinned Workbench runtimes published through GitHub Packages: ARM64 for Apple Silicon and AMD64 for Intel. Both guide users through runtime installation and verification.

All three applications provide the Explore, Create, Run, and Compare workflow while retaining their platform-specific runtime and operating-system behavior.

The refreshed Mac builds keep first-launch runtime downloads in background operations so long image pulls can finish and persist their verified profiles. The Apple Silicon build preserves the current ARM64 profile rather than treating it as a legacy alias. Both Mac builds use the macOS trust store for official HTTPS map services.

## Important notes

- **Settings → Updates** provides optional weekly or manual advisory checks for stable Workbench releases, official VisionEval releases, and architecture-compatible runtime images approved by the release manifest. It never installs updates automatically.
- The Mac application is ad-hoc signed for bundle integrity but is not Apple-notarized.
- Each Mac DMG is architecture-specific; use the ARM64 build on Apple Silicon and the x64 build on Intel.
- The preferred runtime is built from the official VisionEval `VE-40-RC7` source at commit `7852dc58fad460ff279f5eebf4dd55fe191470ad`, with no unofficial source patch.
- Settings can install a manifest-approved, architecture-specific immutable runtime digest and restore the previous verified runtime.
- `VE-40-RC7` and `latest` are readable multi-platform registry tags; Workbench executes the validated digest, never the floating tag.
- Regional planning data are provided as-is and are installed separately through **Settings → Assets**.
