# VisionEval Workbench 1.0.0 for Apple Silicon macOS

This is the independently maintained Apple Silicon application. It uses Docker Desktop and the pinned ARM64 VisionEval Workbench runtime for model runs and uncached R data access.

Download `VisionEval-Workbench-v1.0.0-macos-arm64.dmg` from the GitHub release, drag the app to **Applications**, start Docker Desktop, and use Workbench's guided runtime installation and verification.

The application is ad-hoc signed for bundle integrity but is not Apple-notarized. The Mac wiki documents the one-time Gatekeeper workaround if macOS blocks the downloaded app.

Optional PlanRVA and Virginia MPO packages are installed from their ZIP files through **Settings → Assets**.

The refreshed 1.0.0 Apple Silicon build completes long first-launch runtime downloads in the background and uses the macOS trust store for official HTTPS map services.
