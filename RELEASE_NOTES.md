# VisionEval Workbench 1.1.0

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
