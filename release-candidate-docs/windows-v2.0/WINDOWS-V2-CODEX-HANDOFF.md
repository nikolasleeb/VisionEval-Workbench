# VisionEval Workbench 2.0 — Windows Port Handoff

## Mission

Build and verify the Windows x64 edition of VisionEval Workbench 2.0 from the frozen macOS 2.0 release source. Windows must execute VisionEval through the native runtime already installed on the Windows computer. Do not add Docker as a dependency, install or patch VisionEval automatically, publish a release, or claim the unsigned installer is signed.

## Immutable source checkpoint

- Repository: `https://github.com/nikolasleeb/VisionEval-Workbench.git`
- Checkpoint branch: `codex/v2.0-release-checkpoint`
- macOS 2.0 source baseline: `ed284507b8d405982f765f6c862256fc95658453`
- Handoff document commit: run `git log -1 --format=%H -- release-candidate-docs/windows-v2.0/WINDOWS-V2-CODEX-HANDOFF.md` after checkout. The SSD copy records the resolved SHA explicitly.
- Product version: `2.0.0`
- Windows architecture: `x86_64`
- Expected installer name: `VisionEval-Workbench-v2.0.0-windows-x64-setup.exe`

Start with:

```powershell
git clone https://github.com/nikolasleeb/VisionEval-Workbench.git
cd VisionEval-Workbench
git fetch origin
git switch -c codex/windows-v2.0-port origin/codex/v2.0-release-checkpoint
git rev-parse HEAD
git status --short
```

The first SHA must be the handoff commit on `codex/v2.0-release-checkpoint`, and the checkout must initially be clean. Keep all Windows work on `codex/windows-v2.0-port`.

## Non-negotiable boundaries

1. Treat `macos/` at the checkpoint as the behavior reference, not as a directory to copy over `windows/`.
2. Preserve Windows-native paths, process creation and termination, native file dialogs, WebView2 behavior, PyInstaller sidecar packaging, Tauri/NSIS packaging, and installed-runtime discovery.
3. The existing `windows/` tree is an older 1.0 implementation. Audit and selectively port 2.0 behavior into it.
4. On Windows, `RuntimeManager.adapter` must always be `native`. A configuration value or environment variable must never activate Docker.
5. Do not install, upgrade, patch, or replace R or VisionEval. Use the installation already present on the Windows machine and report incompatibility clearly if validation fails.
6. Keep VisionEval execution serialized through one active native runtime slot and the common FIFO batch queue. Do not enable native parallel execution unless a separate, reproducible safety test proves that the installed runtime supports it without shared-state collisions.
7. Do not change the frozen macOS source, macOS release artifacts, or macOS documentation while doing the port.
8. Do not tag, create a GitHub release, upload an installer, or otherwise publish from this task.

## Phase 1: inventory the Windows machine

Before changing code, collect a native-runtime compatibility record without modifying the installation:

- Windows edition and build;
- CPU architecture;
- installed WebView2 runtime version;
- Node.js, npm, Rust, Cargo, Python, and PowerShell versions;
- resolved `VE_RUNTIME`, `VE_HOME`, and `Rscript.exe` paths;
- R version;
- VisionEval release/version markers, Git revision when available, and hashes of the runtime marker files;
- whether `VE_RUNTIME/.Renviron`, `VE_RUNTIME/.Rprofile`, `VE_RUNTIME/r.version`, `VE_RUNTIME/WORKBENCH-RELEASE`, `VE_HOME/ve-lib`, and the Workbench native CLI contract are present;
- available disk space and the test workspace location.

Discovery precedence must remain explicit and testable:

1. saved Workbench runtime settings;
2. `VISIONEVAL_RUNTIME`, `VISIONEVAL_HOME`, and `RSCRIPT`;
3. `VE_RUNTIME` and `VE_HOME`;
4. standard user/system R and VisionEval locations;
5. an interactive Runtime Settings selection.

Paths must be canonicalized and validated before being saved. Never assume that `VE_RUNTIME` and `VE_HOME` are the same directory. Do not log personal paths in distributable documentation; redact the user-profile prefix in the compatibility report.

Stop and request direction if the installed runtime cannot successfully perform the existing native verification command or if it lacks APIs required by the v2 features. Do not silently substitute Docker or download a different runtime.

## Phase 2: bring the Windows application to 2.0 parity

Port behavior in coherent slices and add tests with each slice. At minimum, Windows 2.0 must include the following macOS checkpoint behavior.

### Desktop and backend lifecycle

- Version every application, compatibility, update, and documentation manifest as `2.0.0`.
- Enforce one Workbench backend per workspace using the workspace lease.
- Serialize start/restart operations, stop the complete backend process tree, wait for the port to close, and recover interrupted native jobs accurately.
- Preserve Windows parent-process watching without Unix-only signals or process-group assumptions.
- Keep job ownership tokens and atomic waiting-job claims even though Windows is serialized.
- Use Windows-native cancellation and cleanup for the active R process and its children.

### Unified work and export queues

- Keep Standard and Hypercube work in one workspace FIFO batch queue.
- Only the oldest unfinished batch may own the native runtime slot.
- Later batches remain queued and begin automatically when the active batch finishes or is stopped.
- Preserve batch-specific mode metadata for workspace compatibility, but expose Windows execution as queued/serialized rather than Docker parallelism.
- Keep the app-wide FIFO export queue, progress, heartbeats, cancellation, cleanup, and save-dialog sequencing.

### Hypercube creation and execution

- Dedicated Hypercube projects, bounded two-axis matrices, safe regeneration rules, immutable completed cases, and case-insensitive scenario-name handling.
- One compact Hypercube card in normal Run history; do not show every Hypercube case as an ordinary run or Live Output tab.
- Project-scoped completion notifications only, not one notification per case.
- Stable completed elapsed time, queue-aware ETA, current-case reporting, and retry-batch accounting.
- `Stop This Hypercube` must remove that project's waiting jobs, stop its active native process, clean partial files, and leave unrelated batches intact.
- Detailed per-case logs remain on Hypercube → Run.
- Replace Docker memory/concurrency guidance with native-runtime queued-execution guidance. A Windows Hypercube has one active runtime slot unless native parallelism is separately approved.

### Hypercube analysis

- Cached Response Matrix results with explicit aggregation; do not restore the removed `Auto` behavior.
- Matrix-cell selection must be immediate and must not recalculate the matrix.
- `Find All Changes` has independent Year and Aggregation controls, defaults to Median, scans all verified completed cases and eligible outputs, reconnects to identical work, reuses matching caches, supports cancellation, and sends a completion notification.
- Outputs and Scenarios views, accessible help text/tooltips, per-output scenario side panel, ranking choices, zero-baseline handling, and scenario drilldowns.
- Stable cache fingerprints based on verified results and the operation's own controls.
- No Response Curves and no obsolete general Compare handoffs. Preserve the spatial Map handoff where supported.

### Hypercube export

- Export the baseline or up to three verified completed cases per batch.
- Produce one ZIP per selection containing resolved input CSVs, output CSVs generated temporarily from the Datastore, and a manifest; never include the Datastore.
- Show preparation, CSV extraction, compression, save-dialog, cleanup, elapsed time, heartbeat, artifact size, package position, and queued count.
- Clean staging after success, cancellation, and failure. One failed or cancelled export must not block later queued exports.

### Standard projects and documentation

- Preserve Standard-project CSV retention and existing native execution behavior.
- Port the current Explore, Create, Review, Run, Compare, settings, workspace, asset-package, diagnostics, accessibility, and notification changes that are shared with macOS.
- Bundle Windows-specific 2.0 documentation. Remove macOS signing/notarization instructions, Docker runtime setup, and Mac-only paths from Windows user-facing material.
- Keep diagnostics useful for native-runtime failures and long-operation failures, without leaking user paths or data.

## Phase 3: Windows packaging

Update the Windows Tauri project from the obsolete 1.0/macOS-oriented configuration:

- application and package version `2.0.0`;
- Tauri bundle target `nsis` for x64 Windows, not `dmg`;
- current icons and branding;
- bundled x64 Python backend sidecar;
- bundled native Workbench R command scripts required to drive the installed runtime;
- no bundled R installation, VisionEval installation, Docker client, Docker image, Datastores, workspace, or private test data;
- native Windows user-guide and What’s New PDFs included in the application;
- deterministic installer name `VisionEval-Workbench-v2.0.0-windows-x64-setup.exe`.

Use the repository's existing Windows PyInstaller and Tauri pipeline as the starting point. Replace Bash-only build steps with PowerShell or cross-platform commands where the Windows build invokes them. Keep generated artifacts outside Git.

## Verification gates

All gates must pass on Windows before presenting the candidate.

### Automated

- `git diff --check` and a staged secret/private-path scan;
- JavaScript syntax and frontend contract tests;
- accessibility contracts, including keyboard and screen-reader names;
- complete Python unit suite under a supported Python 3.11+ interpreter;
- `cargo fmt --check` and complete Rust tests;
- native-runtime discovery/configuration tests using paths containing spaces and non-ASCII characters;
- native process start, cancellation, child cleanup, restart, lease, interrupted-job recovery, and FIFO tests;
- Hypercube timer, queue, stop, analysis-cache, Find All Changes, ranking, export, notification, and failure-diagnostic tests;
- packaging checks proving the installer contains no Docker dependency, VisionEval installation, Datastore, test workspace, credential, or private path.

### Installed smoke test

Install the candidate on the Windows computer and use an isolated workspace. Verify:

1. first launch and WebView2 rendering;
2. installed-runtime discovery and explicit verification;
3. backend restart and application restart recovery;
4. one small Standard baseline/scenario run through the native runtime;
5. FIFO behavior when Standard and Hypercube batches are both queued;
6. a small 2 × 2 Hypercube run, stable elapsed time, scoped stop, retry, and one completion notification;
7. Response Matrix calculation and cache reuse;
8. Find All Changes without first calculating a single variable, followed by identical-cache reuse and notification;
9. Outputs/Scenarios ranking help and keyboard operation;
10. one Hypercube case export with progress/heartbeat and staging cleanup;
11. app restart followed by successful reuse of completed results and caches;
12. bundled Windows documentation opening from the app;
13. uninstall behavior without deleting an external workspace or installed VisionEval runtime.

## Required deliverables

Place the following in a new Windows release-candidate folder outside Git:

- `VisionEval-Workbench-v2.0.0-windows-x64-setup.exe`;
- `SHA256SUMS.txt` covering every distributed file;
- `WINDOWS-RUNTIME-COMPATIBILITY.md` with redacted paths, detected versions/fingerprints, verification outcome, and any limitations;
- `WINDOWS-V2-TEST-REPORT.md` listing commands, test counts, expected skips, installed smoke results, and unresolved warnings;
- final Windows User Guide and What's New source/output documents.

Report the final branch SHA and installer SHA-256. Keep the installer local and unpublished.

## Unsigned-build publication gate

No Authenticode certificate is currently available. The Windows Codex may build and fully test an unsigned installer, but it must:

- label the candidate `UNSIGNED` in the test report and release manifest;
- document the expected SmartScreen/reputation warning;
- never claim that publisher identity was verified;
- never weaken Windows security settings or instruct users to disable SmartScreen globally;
- stop before tagging, uploading, publishing, or creating a GitHub release.

Authenticode signing requires a trusted code-signing certificate and access to its private key; it does not require a generic Windows developer account. Publication of an unsigned installer is a separate explicit release-owner decision.

## Completion report

Return a concise report containing:

- Windows port branch and final commit;
- installed runtime identity and verification result;
- automated test totals and smoke-test results;
- installer path, size, and SHA-256;
- confirmation that Docker is absent from the runtime path and package;
- confirmation that the installer is unsigned;
- every remaining blocker or behavioral difference from macOS 2.0.

Do not declare the Windows release complete if any required gate is skipped, the installed runtime is unverified, or a core v2 Hypercube workflow fails.
