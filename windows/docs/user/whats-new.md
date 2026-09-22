# What Is New in VisionEval Workbench 2.0 for Windows

VisionEval Workbench 2.0 brings the complete bounded Hypercube workflow to Windows and can either connect to an existing native installation or install the certified R 4.5.3 and VisionEval VE-40-RC7 pair for the current user.

## First-run runtime setup

- Detect an existing `VE_RUNTIME`, `VE_HOME`, and `Rscript.exe`, or select each path independently.
- Install the pinned R 4.5.3 and official RC7 Windows library without administrator privileges when no usable runtime is available.
- Keep `VE_HOME`, `VE_RUNTIME`, the application, and the workspace separate. Equal, nested, junction-aliased, and symbolic-link-aliased runtime/home paths are rejected.
- Verify official download SHA-256 values and RC7 `VECommit` package metadata before enabling runs.
- Cancel, retry, or use the documented offline/manual setup path without leaving a partial VisionEval library active.

## Hypercube experiments

- Create a dedicated two-axis project and preview every generated case before committing it.
- Run cases through one native VisionEval slot in the common workspace FIFO queue.
- Stop one Hypercube without removing unrelated Standard or Hypercube batches.
- Review one compact Run-history card while retaining detailed case logs on Hypercube → Run.

## Analysis and export

- Build cached Response Matrices with explicit aggregation and instant cell selection.
- Find changes across every verified completed case with independent Year and Aggregation controls.
- Rank outputs or scenarios, inspect zero-baseline results, and open scenario details without recalculating.
- Export the baseline or up to three completed cases as separate ZIP packages containing resolved inputs, temporary output CSVs, and a manifest—never the Datastore.

## Reliability and Windows behavior

- Standard and Hypercube batches share a persistent FIFO queue and recover accurately after restart.
- Workspace leases prevent two backends from controlling the same workspace.
- Active R process trees are stopped with Windows-native cleanup before partial files are removed.
- The Windows edition is native-only: it does not require or activate Docker. The optional managed installer changes only the selected current-user R, `VE_HOME`, and `VE_RUNTIME` locations after explicit approval.
- Hypercubes are safe on laptops. Systems below 16 GB of RAM receive advisory guidance, while low workspace capacity produces a confirmation warning rather than an automatic block.

## Unsigned release candidate

This local candidate is not Authenticode-signed. Windows may show a SmartScreen or unknown-publisher warning. Publisher identity has not been verified; do not disable SmartScreen globally.
