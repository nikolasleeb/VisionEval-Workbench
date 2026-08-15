# macOS Installation and Runtime

## Requirements

- Apple Silicon Mac
- macOS 12 or newer
- Docker Desktop for Apple Silicon when running models or reading uncached R data

## Install Workbench

1. Open the [latest release](https://github.com/nikolasleeb/VisionEval-Workbench/releases/latest).
2. Download `VisionEval-Workbench-v1.0.0-macos-arm64.dmg`.
3. Open the DMG and drag **VisionEval Workbench** to **Applications**.
4. Choose an empty, recognizable workspace folder on first launch.

The app is ad-hoc signed but is not Apple-notarized. If macOS reports that it cannot be opened, cancel the warning and run this once in Terminal:

```bash
xattr -dr com.apple.quarantine "/Applications/VisionEval Workbench.app"
open "/Applications/VisionEval Workbench.app"
```

## Install the runtime

1. Install and start Docker Desktop for Apple Silicon.
2. In onboarding or **Settings → Runtime**, select **Install runtime**.
3. Keep Workbench open while it pulls the pinned image and performs verification.
4. Continue only after Workbench reports that the runtime is installed, verified, and connected.

Workbench uses an immutable container digest internally. Normal users do not need to enter Docker commands or manage tags.
