# Changelog

## 1.0.0

- First public release of the independently maintained Apple Silicon application.
- Uses Docker Desktop with the pinned ARM64 VisionEval Workbench runtime.
- Includes the complete Explore, Create, Run, and Compare workflow.
- Includes guided runtime installation, Mac-specific documentation, and DMG packaging.
- Keeps the first-launch runtime download alive as a background operation and restores packaged HTTPS certificate discovery.
- Preserves verification for the current `local/visioneval:1.0.0-arm64` runtime profile instead of migrating it as a legacy alias.

Known limitations are maintained in [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md).
