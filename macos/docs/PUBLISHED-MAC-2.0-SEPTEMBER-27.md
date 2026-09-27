# Published Mac 2.0 installer source — September 27, 2026

This checkpoint publishes the local source used for the tested Mac performance candidate 2, subsequently uploaded as `VisionEval-Workbench-v2.0.0-macos-arm64.dmg` on the existing v2.0.0 release.

The app shell was retained from the previous published signed Mac app. The Python sidecar and bundled web interface were rebuilt from this source. The app and DMG were Developer ID signed; Apple accepted notarization submission `9a1b8f17-b4fe-4d05-b35a-cef8b0dac983`. The DMG ticket was stapled and the GitHub-downloaded installer passed Gatekeeper assessment.

Included fixes cover external-drive workspace copy/verification and startup, housekeeping-file exclusion, Hypercube year discovery, startup metadata-only migration, shared comparison scan/chart summaries, categorical summary bounds, synthetic-ID handling, precision-aware zero filtering, and safe handling of empty scanner totals.

Local validation: 388 Python tests, 385 passed and 3 skipped; JavaScript syntax check; isolated real-Docker scanner fixtures; packaged backend startup and updated-UI smoke checks. The user tested and approved this installer. No Windows or Intel code or installer is changed by this source checkpoint.

Outstanding performance work includes the standard-run exported-CSV fast path and measured production-workspace performance benchmarks. Publishing this source does not rebuild or replace the approved installer, move the v2.0.0 tag, or claim byte-for-byte reproducibility across toolchains.
