# Intel macOS Installation and Runtime

Use this page to install the native x86_64 application and its managed AMD64 VisionEval runtime.

> [!NOTE]
> For screenshots and first-time-user guidance, use the complete [Intel macOS installation guide](https://github.com/nikolasleeb/VisionEval-Workbench/blob/main/docs/tutorials/VisionEval-Workbench-Installation-macOS-Intel.pdf).

## Requirements

- Intel Mac running macOS 12 or newer
- Docker Desktop for Mac with an Intel chip when running models or reading uncached R data
- Enough free disk space for the app, AMD64 runtime image, workspace, and results

## Install Workbench

1. Open the [latest release](https://github.com/nikolasleeb/VisionEval-Workbench/releases/latest).
2. Download `VisionEval-Workbench-v1.0.0-macos-x64.dmg`.
3. Open the DMG and drag **VisionEval Workbench** to **Applications**.

The app is ad-hoc signed but is not Apple-notarized. If macOS blocks the first launch, cancel the warning and run this once in Terminal:

```bash
xattr -dr com.apple.quarantine "/Applications/VisionEval Workbench.app"
open "/Applications/VisionEval Workbench.app"
```

This removes quarantine from this app copy only; it does not disable Gatekeeper globally.

## Install the runtime

1. Install and start Docker Desktop for Mac with an Intel chip.
2. In onboarding or **Settings → Runtime**, select **Install runtime**.
3. Wait while Workbench pulls the immutable AMD64 image, creates `local/visioneval:1.0.0-amd64`, and runs provenance and compatibility checks.
4. Continue only after Workbench reports **Installed**, **Verified**, and **Connected**.

Workbench records and rechecks the immutable image digest. Retagging another image does not bypass the `doctor`, upstream-release, compatibility-patch, architecture, or digest checks.

**Next:** [Using Workbench on Intel macOS](Using-Workbench-on-Intel-macOS) · [Troubleshooting](Troubleshooting)
