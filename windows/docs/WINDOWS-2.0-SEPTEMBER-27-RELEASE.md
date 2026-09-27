# Windows 2.0 installer update September 27 2026

Published asset: VisionEval-Workbench-v2.0.0-windows-x64-setup.exe

SHA-256: f4f2505fc9397ddf76057035a59cf63ce7519894b1c30ca8b3ccfb25a47f4cac

Size: 16,637,434 bytes. Unsigned Windows x64 per-user installer.

This source checkpoint corresponds to the tested installer. It includes regional source/crosswalk fixes and geography previews, compact Windows internal paths and native R path handling, required baseline selection, standard CSV comparisons with split-table identity joins, shared Find All Changes/chart scan summaries, bounded category serialization, metadata-only startup path migration, and percentage-precision-aware zero filtering. Display names and raw comparison totals are preserved. Hypercube comparisons remain Datastore-based.

Validation: 431 Python tests OK (18 skipped, 413 passed), 18 Rust tests passed, Rust formatting and JavaScript syntax checks passed, precision-aware frontend regression passed, packaged content inspection and isolated backend smoke passed. No user workspace, R, or runtime installation was modified by publishing this update.

The installer replaces only the Windows asset of the existing v2.0.0 release. Mac installer and regional data assets are preserved. The shared release tag is not moved; the matching Windows source is supplied through the Windows source branch and pull request.
