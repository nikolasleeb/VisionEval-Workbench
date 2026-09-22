# VisionEval Workbench 2.0 — Windows Test Report

Candidate status: **UNSIGNED**  
Test date: September 20–22, 2026
Checkpoint: `77d28f320ce6a315d7ea50ffb9ca50df5fe8eb84`  
Branch: `codex/windows-v2.0-port`

Certified runtime: VisionEval `VE-40-RC7`
(`7852dc58fad460ff279f5eebf4dd55fe191470ad`) with R 4.5.3 x64.

## Automated gates

| Gate | Result |
| --- | --- |
| Python suite | PASS — 368 tests, 18 dependency/integration skips |
| JavaScript syntax and frontend contract/accessibility coverage | PASS |
| Rust tests | PASS — 15 tests |
| `cargo fmt --check` | PASS |
| Documentation source validation | PASS — 62 Markdown files |
| Generated document consistency | PASS — User Guide PDF 20 pages and DOCX 27 pages; What's New PDF/DOCX 1 page each |
| Native R help/doctor/capability/provenance checks | PASS |
| `git diff --check` | PASS |

The Python suite covers workspace leases, restart serialization, port closure,
Windows child cleanup, runtime discovery precedence and stale candidates, Unicode
and spaced paths, junction/overlap rejection, FIFO batch ownership and recovery,
managed-install checksum failure/cancellation/rollback/compatible-R reuse,
Hypercube generation/regeneration, scoped stop/retry behavior, matrix/cache/
discovery/export workflows, package safety, documentation contracts, and frontend
accessibility contracts.

## RC7 runtime and first-run setup

- Runtime discovery independently resolved R 4.5.3, `VE_HOME`, and `VE_RUNTIME`.
- Package `DESCRIPTION` metadata reported `VECommit`
  `7852dc58fad460ff279f5eebf4dd55fe191470ad`; Workbench therefore reported
  `VE-40-RC7` even though package versions remain 4.0.0.
- Native `doctor`, `verify-capabilities`, and `verify-upstream-release` completed
  successfully against the installed runtime.
- Automated managed-install tests verified pinned HTTPS URLs and SHA-256 values,
  current-user locations, R 4.5 reuse, safe ZIP extraction, cancellation,
  temporary-file cleanup, and rollback after failed verification.
- First-run contracts show **Install R 4.5.3 + VisionEval RC7** only when no usable
  runtime is found. Explicit selections are canonicalized and cannot place
  `VE_RUNTIME` inside `VE_HOME` or vice versa.

## Packaged-candidate inspection

- Built with a user-scoped Node/Python/LLVM/Windows SDK toolchain on the external
  SSD; no administrator access was required.
- NSIS installs per-user and registers version 2.0.0.
- The release application compiled successfully and NSIS produced the x64
  installer. Windows intermittently returned OS error 1224 after NSIS wrote the
  installer because the new executable was temporarily memory-mapped; the
  resulting installer passed PE metadata, hash, install, launch, and uninstall
  checks.
- The installed application contains exactly the desktop executable, packaged
  backend executable, and uninstaller.
- Installer and extracted executables were scanned for private build/user paths,
  Docker executables/client payloads, credential paths, and credential files; no
  matches were found. Rust source paths were remapped before the final build.
- The final per-user install completed with exit code 0. Startup reported a
  responsive `VisionEval Workbench` window, local backend health, application
  version 2.0.0, native adapter, R 4.5.3, RC7 provenance, and the expected
  independent VE runtime/home paths.
- The live packaged backend reported the SSD workspace
  `D:\VDOT\VE Workbench\Workspaces`, approximately 478 GB free, and 8 GB RAM as
  an advisory condition only. Runtime execution remained enabled.
- Graceful window close terminated the complete backend process tree and closed
  its loopback port.
- Both packaged documentation PDFs were available through the installed backend.
- Silent uninstall returned success, removed the application directory, and
  preserved the pre-existing R, VisionEval runtime/home, and Workbench workspace
  directories with unchanged directory timestamps.

## Native acceptance smoke

- Used an isolated workspace on the D: SSD and the installed PyInstaller backend.
- Installed and verified the bundled PlanRVA package, built a 50-zone test region,
  and completed a native Standard baseline run with a verified Datastore.
- Generated a bounded 2×2 two-axis Hypercube with four immutable cases.
- Confirmed a requested parallel batch was coerced to FIFO (`mode: queued`) with
  one active native job and all remaining jobs waiting.
- Scoped stop terminated one active Hypercube R tree, removed four waiting jobs,
  left unrelated work untouched, and emptied the queue; retry then dispatched a
  fresh serialized batch.
- The retry completed the baseline and all four cases successfully, with five
  verified Datastores and no overlapping native R execution.
- Response Matrix returned four available cells and reused its stable operation
  identity. Find All Changes completed 28 scan units, found 77 changed outputs,
  produced four scenario rankings, and reused its fingerprinted cache without a
  second scan.
- A verified case export completed all four phases and produced a 108,565,273-byte
  ZIP containing `manifest.json`, 51 input CSVs, and 21 output CSVs. It contained no
  Datastore and left no temporary staging directory.
- Restarting the rebuilt packaged backend against the same workspace recovered all
  completed Standard/Hypercube state with no active orphan operation.

Two acceptance findings were corrected and retested: native analysis helpers now
add the selected `VE_HOME` library before loading `jsonlite`, and Hypercube export
staging uses a short fixed hash to remain below legacy Windows path limits.

The final RC7/setup/layout changes do not alter the model execution engine. After
those changes, the complete 368-test regression suite and installed
startup/runtime/storage/shutdown smoke were rerun against the final candidate.

## Native work-area and input-validation follow-up

- Added the native Tauri `window_layout_metrics` command. It reports the WebView
  client rectangle, the current monitor work area, scale factor, and maximized
  state in physical pixels. The frontend intersects that rectangle with the DOM
  client area and `VisualViewport`, maps it through the measured physical/CSS
  ratios, and centers large dialogs within a fixed 24 CSS-pixel inset.
- Window move, resize, maximize/restore, scale-factor, visual-viewport, document
  resize, and Workbench zoom changes all trigger reclamping. Settings has a
  persistent pointer/keyboard resize handle; Hypercube remains non-resizable.
- Added the authoritative packaged input-validation catalog, structured
  `input_validation` HTTP 400 responses, categorical and linked-share editing,
  timeless-file handling, atomic multi-file Batch Change rollback, and matching
  Hypercube axis/candidate enforcement.
- Final automated gates: 368 Python tests passed with 18 dependency/integration
  skips; 74 frontend contract tests passed with 2 skips; 15 Rust tests passed;
  JavaScript syntax, Rust formatting, and `git diff --check` passed.
- A per-user install of the temporary candidate started successfully and reported
  application 2.0.0, the SSD workspace, the native adapter, R 4.5.3, VisionEval
  RC7, and the existing separate runtime/home paths. The packaged backend contains
  `input_validation_rules.json`.
- The privacy-clean installer and installed executables contain no user-profile,
  private project, SSD build, Docker executable, Datastore, or workspace paths.
  The installer is unsigned, as expected.

Manual on-screen confirmation of the exact Settings/Hypercube taskbar clearance
is still required because native window automation is unavailable in this Codex
session. Until that confirmation, the installer remains in the temporary SSD
candidate folder and has not replaced the published release-candidate artifacts.

## Popup safe-area follow-up

- Large Settings, Hypercube, onboarding, export, shortcuts, runtime-guide,
  geography, and map dialogs now share a fixed 24 CSS-pixel viewport inset and
  explicit viewport centering. The former Hypercube-specific 112px/72px sizing
  formulas and short-display inset reduction were removed.
- Settings remains resizable, with fixed header/footer rows and internally
  scrollable content. Hypercube remains non-resizable, with fixed header/action
  rows and only its warning content scrolling.
- Responsive geometry checks at 1920x1080, 1536x864, 1280x720, and 960x540 CSS
  viewports (100%, 125%, 150%, and 200% display-scale equivalents) confirmed at
  least 24px clearance on all edges. At 960x540 the Hypercube dialog measured
  exactly 24px on every side, retained its visible action footer, and scrolled
  internally. The Settings contract measured 912x492 with fixed 24px insets and
  `resize: both`, leaving its bottom-right resize grip inside the usable area.
- JavaScript syntax checks, 74 frontend contract tests (2 expected skips), the
  complete 379-test Python suite (18 expected skips), 15 Rust tests,
  `cargo fmt --check`, and `git diff --check` passed.
- The rebuilt unsigned installer completed a current-user installation and
  launched successfully. The installed backend retained the SSD workspace at
  `D:\VDOT\VE Workbench\Workspaces`, the native adapter, R 4.5.3, VisionEval
  RC7, and independent `VE_RUNTIME`/`VE_HOME` paths.

## Expected warnings

Windows R still emits `C.UTF-8` locale warnings. The official RC7 Windows library
does not include the legacy `WORKBENCH-RELEASE` marker; RC7 provenance is instead
verified from `VECommit` in package `DESCRIPTION` metadata. Neither warning blocks
native execution.

This candidate is **UNSIGNED**. Windows SmartScreen may show an unknown-publisher
warning. No tag was created and nothing was published.
