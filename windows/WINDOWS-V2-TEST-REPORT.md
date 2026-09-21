# VisionEval Workbench 2.0 — Windows Test Report

Candidate status: **UNSIGNED**  
Test date: September 20–21, 2026  
Checkpoint: `77d28f320ce6a315d7ea50ffb9ca50df5fe8eb84`  
Branch: `codex/windows-v2.0-port`

## Automated gates

| Gate | Result |
| --- | --- |
| Python suite | PASS — 369 tests, 22 dependency/integration skips |
| JavaScript syntax and frontend contract/accessibility coverage | PASS |
| Rust tests | PASS — 15 tests |
| `cargo fmt --check` | PASS |
| Documentation source validation | PASS — 60 Markdown files |
| Generated PDF consistency | PASS — User Guide 20 pages; What's New 1 page |
| Native R help/doctor/capability checks | PASS |
| `git diff --check` | PASS |

The Python suite covers workspace leases, restart serialization, port closure,
Windows child cleanup, runtime discovery precedence and stale candidates, Unicode
paths, FIFO batch ownership and recovery, Hypercube generation/regeneration,
scoped stop/retry behavior, matrix/cache/discovery/export workflows, package safety,
documentation contracts, and frontend accessibility contracts.

## Packaged-candidate inspection

- Built with a user-scoped Node/Python/LLVM toolchain; no administrator access was
  required.
- NSIS installs per-user and registers version 2.0.0.
- The installed application contains exactly the desktop executable, packaged
  backend executable, and uninstaller.
- Installer and extracted executables were scanned for private build/user paths,
  Docker executables/client payloads, credential paths, and credential files; no
  matches were found. Rust source paths were remapped before the final build.
- Installed startup reported a responsive `VisionEval Workbench` window, local
  backend health, application version 2.0.0, native adapter, R 4.5.3, and the
  expected independent VE runtime/home paths.
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

## Expected warnings

The missing `WORKBENCH-RELEASE` marker and Windows `C.UTF-8` locale warnings are
documented compatibility limitations. They did not prevent native doctor,
capability verification, or the successful Standard model run.
