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
| Python suite | PASS — 389 tests, 18 dependency/integration skips |
| JavaScript syntax and frontend contract/accessibility coverage | PASS |
| Rust tests | PASS — 17 tests |
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
  client rectangle, the current monitor work area, their client-relative visible
  intersection, scale factor, and maximized state in physical pixels. The
  frontend maps that intersection through the native-inner/layout-viewport ratio
  and centers large dialogs within a fixed 24 CSS-pixel inset.
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

## Dialog recentering and website-link follow-up

- Native layout metrics now include the physical work-area/client intersection as
  a client-relative rectangle. The frontend converts that rectangle through the
  measured native-inner/layout-viewport ratio, centers each large dialog with a
  single fixed-position translate rule, and corrects any measured edge drift.
- Settings size persistence now uses a versioned record. The malformed size from
  the preceding candidate is discarded once; later valid sizes are clamped,
  recentered, and retained across openings and layout changes.
- The installed-app smoke exposed and corrected two integration defects that
  static geometry tests did not catch: overlapping resize notifications could
  prevent the first layout from committing, and `inset: auto !important`
  overrode the controller's inline center coordinates. Layout synchronization is
  now single-flight/coalesced, and the controller owns all four inset edges.
- Help and Settings Documentation now share one action for the official website,
  `https://sites.google.com/view/ve-workbench/home`. The desktop command accepts
  that string only by exact equality, while retaining the separate trusted GitHub
  update-link policy.
- Final source gates: 389 Python tests passed with 18 expected
  dependency/integration skips; 77 frontend contract tests passed with 2 expected
  skips; 17 Rust tests passed; JavaScript syntax, Rust formatting, and
  `git diff --check` passed.
- The final per-user installed smoke showed Settings centered with equal visible
  clearance above/below and left/right, fixed header/footer, internal scrolling,
  and a reachable bottom-right resize grip. Hypercube showed the same 24–25 px
  usable-edge clearance with a fixed header/footer and internally scrolling
  warning content.
- The Help website item opened the Windows default Chrome browser. The Settings
  Documentation card displayed the exact URL and remained open without saving or
  discarding state. Exact-URL rejection variants are covered by Rust tests.
- The final installer was rebuilt with Rust source-path remapping and contains no
  private user or SSD build path. Silent current-user installation preserved the
  desktop configuration and SSD workspace unchanged.
- After all automated and installed-app gates passed, the corrected unsigned
  installer was promoted from the temporary SSD build folder into the Windows
  release-candidate folder. It remains unpublished and untagged.

## PlanRVA package-preview follow-up

- Diagnosed an installed-app wait where the PlanRVA package validated in the
  backend in under one second, but its review dialog could remain behind the
  already-modal Settings window while the Assets button continued to say
  `Validating…`.
- Package validation now has a bounded two-minute wait with an actionable error.
  Once validation succeeds, Settings is temporarily suspended, the package
  review opens as the only foreground modal, and Settings is restored without
  rerendering or losing its draft controls when review ends.
- The Assets button leaves its validation state before review begins and changes
  to `Installing…` only after the user approves installation.
- Focused frontend contracts and the real PlanRVA package-preview test pass. The
  complete Python suite passes 389 tests with 18 expected skips.
- The rebuilt candidate installed per-user with exit code 0 while preserving the
  desktop configuration and SSD workspace. Its installed backend previewed the
  119-file PlanRVA 2.0 package in 552 ms and verified the package manifest.
- The user confirmed that the PlanRVA package review dialog now appears. The
  tested unsigned installer was promoted to the Windows release-candidate folder;
  it remains unpublished and untagged.

## Hypercube tracking, resources, logs, and documentation follow-up

- The seven-case PlanRVA Hypercube completed without intervention. Baseline and
  all six cases remain `succeeded` and `verified`; no case was rerun for this fix.
- Native RC7 runtime identity now uses a stable fingerprint of the validated R
  executable, `VE_HOME`, `VE_RUNTIME`, and package DESCRIPTION metadata. The
  installed backend reconciled all seven older blank-digest results as `current`
  only after matching their successful jobs, Datastores, input fingerprints,
  runtime home, and package provenance. The Hypercube tracker displayed seven
  successful and zero missing, with **Run Missing** disabled.
- The installed Hypercube Run card displayed seven of seven complete, a stable
  elapsed duration, one native slot, and no estimated time remaining. Each case
  and the outside Run history agreed on success. Selecting a case showed its log
  inside a bounded, internally scrolling pane; selecting it again cleared the
  pane. No log extended into the next card.
- The installed 81-case planning example used nine comparable completed runs
  from this computer: 81 serialized waves, approximately 22.3 hours, and about
  23.2 GB of retained Datastores. It reported 8.2 GB installed RAM, current
  available/in-use RAM, and 404.2 GB free in the SSD workspace; low RAM remained
  advisory. These are planning estimates, not guarantees for other models.
- Windows Documentation now offers only **Read in Workbench**. Both bundled PDFs
  were present; What's New rendered in the installed reader without the former
  unsigned-candidate warning. The stale system-viewer sentence was removed and
  checked after the final per-user reinstall. Settings and the Hypercube warning
  retained visible taskbar clearance.
- Final automated gates: 392 Python tests with 22 expected skips; 80 frontend
  contract tests with two expected skips; 17 Rust tests; JavaScript syntax,
  `cargo fmt --check`, documentation verification, and `git diff --check` passed.
  The live transition cadence was not re-smoked by launching another model;
  single-flight polling and local timer ticks are covered by frontend contracts.
- The final SSD-built installer is unsigned, 15,675,593 bytes, and has SHA-256
  `6af29f895c8b6eab9446d686af868ba37bbeeb129be3d9f3154af1c29ef158ef`.
  Its installed desktop and backend executable hashes match the built files.
  Archive inspection confirmed the revised frontend, validation catalog, and
  both Windows PDFs; binary scans found no private paths, Datastore, credentials,
  or Docker payload. Tauri again returned Windows file-mapping error 1224 after
  NSIS wrote the installer; the installer passed hash, current-user install,
  launch, backend recovery, and UI checks.

## Expected warnings

Windows R still emits `C.UTF-8` locale warnings. The official RC7 Windows library
does not include the legacy `WORKBENCH-RELEASE` marker; RC7 provenance is instead
verified from `VECommit` in package `DESCRIPTION` metadata. Neither warning blocks
native execution.

This candidate is **UNSIGNED**. Windows SmartScreen may show an unknown-publisher
warning. No tag was created and nothing was published.

## September 23 update-message correction

- Corrected the update-available notice from “available for this Mac” to
  “available for Windows” in the Windows backend only. The current notice,
  release URL, offline behavior, and Windows asset selection are unchanged.
- A focused Windows/x64 test verifies the exact message, selection of the
  Windows setup executable over a macOS asset, and the release-notes URL.
- Focused update checks: 8 passed. Complete Python suite: 393 passed, 18
  expected skips. JavaScript syntax and 80 frontend contracts passed (2
  expected skips). `cargo fmt --check` and `git diff --check` passed. The
  previously built Rust test executable passed 17 tests; a fresh `cargo test`
  link was unavailable after the build-only Windows SDK/LLVM tools were
  removed during the approved SSD cleanup. Rust source was not changed.
- Rebuilt the PyInstaller backend and repackaged the unchanged desktop binary
  as a 15,674,956-byte, unsigned Windows x64 NSIS installer with SHA-256
  `a905f4230f2cfb28261418a54530a7524790b406a653198fcfc328120bd6fc57`.
  The newly packaged backend started from its build output and passed the
  `/api/health` check.
- A same-version silent install returned exit code 0 but did not replace the
  existing installed backend binary. The installed app launched and completed
  a live update check, reporting the current 2.0.0 message against the
  published 1.0.0 release; because no newer public release exists, the
  update-available wording could not be observed in that installed UI.
  Therefore the replacement installer is packaged and source-tested, but its
  same-version reinstall behavior and updated installed UI remain unverified.
- The prior uploaded draft installer, SHA-256
  `6af29f895c8b6eab9446d686af868ba37bbeeb129be3d9f3154af1c29ef158ef`,
  is superseded only after the replacement is installed and accepted. Neither
  installer is signed; no release was tagged or published in this follow-up.
