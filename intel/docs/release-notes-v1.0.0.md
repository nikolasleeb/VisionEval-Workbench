# VisionEval Workbench 1.0.0 for Intel macOS

This is the independently maintained Intel application. It uses Docker Desktop and the pinned AMD64 VisionEval Workbench runtime for model runs and uncached R data access.

Download `VisionEval-Workbench-v1.0.0-macos-x64.dmg` from the GitHub release, drag the app to **Applications**, start Docker Desktop, and use Workbench's guided runtime installation and verification.

Runtime installation runs as a background operation shared by first-launch setup and **Settings → Runtime**. The interface polls its progress, so a long initial Docker pull does not fail merely because an HTTP response stayed open too long.

The application is ad-hoc signed for bundle integrity but is not Apple-notarized. The Mac wiki documents the one-time Gatekeeper workaround if macOS blocks the downloaded app.

Optional PlanRVA and Virginia MPO packages are installed from their ZIP files through **Settings → Assets**.
