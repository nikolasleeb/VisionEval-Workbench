# Intel macOS Installation and Runtime

## Requirements

- Intel Mac running macOS 12 or newer.
- Docker Desktop for Mac with an Intel chip when running models or reading uncached R data.
- Enough free disk space for the application, AMD64 runtime image, workspace, and model results.

## Install

1. Open the [v1.0.0 release](https://github.com/nikolasleeb/VisionEval-Workbench/releases/tag/v1.0.0).
2. Download `VisionEval-Workbench-v1.0.0-macos-x64.dmg`.
3. Open the DMG and drag **VisionEval Workbench** to **Applications**.

The app is ad-hoc signed but is not Apple-notarized. If macOS blocks the first launch, cancel the warning and run:

```bash
xattr -dr com.apple.quarantine "/Applications/VisionEval Workbench.app"
open "/Applications/VisionEval Workbench.app"
```

This removes quarantine from this app copy only; it does not disable Gatekeeper globally.

## Runtime setup

1. Install and start Docker Desktop for Mac with an Intel chip.
2. In Workbench, choose **Install runtime** during onboarding or in **Settings → Runtime**.
3. Wait while Workbench pulls the immutable AMD64 image, creates `local/visioneval:1.0.0-amd64`, and runs the provenance and compatibility checks.
4. Confirm the runtime reports Installed, Verified, and Connected before running a model.

Workbench records and rechecks the immutable image digest. Retagging an arbitrary image does not bypass the `doctor`, upstream-release, compatibility-patch, architecture, or digest checks.
