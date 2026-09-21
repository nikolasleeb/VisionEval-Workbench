# What Is New in VisionEval Workbench 2.0 for Windows

VisionEval Workbench 2.0 brings the complete bounded Hypercube workflow to Windows while continuing to use the VisionEval and R installation already present on the computer.

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
- The Windows edition is native-only: it does not require or activate Docker and does not install or change VisionEval.

## Unsigned release candidate

This local candidate is not Authenticode-signed. Windows may show a SmartScreen or unknown-publisher warning. Publisher identity has not been verified; do not disable SmartScreen globally.
