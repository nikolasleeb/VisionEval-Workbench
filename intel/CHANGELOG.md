# Changelog

## 1.0.0

- First public release of the independently maintained Intel application.
- Uses Docker Desktop with the pinned AMD64 VisionEval Workbench runtime.
- Includes the complete Explore, Create, Run, and Compare workflow.
- Includes guided runtime installation, Mac-specific documentation, and DMG packaging.
- Keeps the first-launch runtime download in a background operation so the WebView cannot report a false `Load failed` while Docker is still pulling and verifying the image.

Known limitations are maintained in [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md).
