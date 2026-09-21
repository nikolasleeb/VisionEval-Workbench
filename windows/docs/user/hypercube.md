# Hypercube Workflow

Open primary tab **5 Hypercube** or press **Ctrl+5**. Workbench presents the resource disclosure once per application launch because a small-looking parameter grid can create many complete model runs. Hypercubes are intended for a dedicated computer; avoid a large matrix on a computer needed for other work.

## Build

Create or select a Hypercube project, then configure one or two numeric parameter axes. An interval must be at least 2, each axis may contain at most 20 generated values, and a new or replacement definition may contain at most 400 cases. Existing older matrices remain runnable and analyzable even if they exceed those limits, but an out-of-policy replacement is rejected.

Setup changes save automatically without creating cases. **Saving…**, **Saved**, and **Not saved—Retry** report the draft state. Preview uses the latest saved revision and shows every generated value, exact case count, shared row scope, estimated serialized runtime, and retained disk. Only **Generate Scenarios** creates or replaces cases.

The project name is the matrix name. Shared year selects dated input rows; it does not change model years. **All matching rows** applies each combination to every compatible row without adding a location dimension. A specific geography requires at least one location.

## Review

Review shows the immutable generated definition, axes and values, case count, year, geography, scope, model provenance, and a current resource estimate.

## Run

Choose the project rather than dozens of individual scenarios. **Run Missing** queues only a missing baseline and missing cases. **Retry Failed** queues only failed work. Successful work is not routinely rerun. The batch card reports totals, progress, elapsed time, estimated remaining time, waves, and concurrency. Completed elapsed time is frozen at the latest terminal job instead of continuing to advance. **Stop This Hypercube** removes its waiting jobs and stops its owned active containers without disturbing unrelated batches. Normal Run history shows one compact Hypercube card; detailed case logs remain here. A completion notification is sent for the project rather than for every case.

New Hypercube runs retain the authoritative Datastore and skip the optional full CSV export tree.

## Analyze

Choose an actual VisionEval output table and variable, year, optional geography, aggregation, and metric. Aggregation is an explicit analytical choice: Sum measures totals, Mean measures the arithmetic average, Median measures the middle row or location, and Minimum or Maximum shows an extreme. Two axes render as a labelled response matrix with one cell per case; Scenario ranking provides the sortable alternative view. Fingerprinted matrices are cached. Selecting one or two cells updates details immediately from the existing matrix without recalculating it. Available metrics include result value, absolute and percent change from baseline, typical row change, and breadth. Zero-reference percent changes are unavailable rather than infinite. Household, Vehicle, and Worker identifiers are run-local, so Find All Changes uses aggregate distributions rather than unsafe individual matching.

Analysis state remains in memory while you visit other Workbench tabs. Active matrix and discovery operations keep the previous result visible, lock request-changing controls, show phase, case/table progress, elapsed time, heartbeat, bytes read, summaries written, and cache growth, and provide **Cancel**. The primary Hypercube tab pulses while work continues elsewhere. Completion or failure notifies you off-screen. Restarting Workbench resets the visible analysis session but retains safe fingerprinted summary checkpoints.

**Find All Changes** is the Hypercube-wide equivalent of the Compare operation. It has its own Year and Aggregation controls, independent of the single-output Response Matrix. Median is the default; Sum, Mean, Minimum, and Maximum are also available. It runs only when you press the button, reads each baseline table once, processes every verified completed case, and checkpoints after each case/table. Large or uncached scans can take several minutes. It is cancellable, sends one completion or failure notification, and repeating an identical project/year/aggregation request restores the fingerprinted result cache. Results can be searched and ranked by overall shift, typical row shift, breadth, or extreme change. Select an output to open its scenario-ranking side panel without another scan, or use the Scenarios view to rank cases across all eligible outputs. Keyboard-focusable help explains both tables, and rankings measure sensitivity rather than desirability. No opaque combined score is used. Response matrices are also fingerprinted and reused until their request or underlying Datastores change. All cached material shares the disposable comparison-cache limit.

Select one cell for its details or two cells for an in-place difference. **Open Map** sends the selected case and output to the spatial view. Export the displayed analysis—not the complete result tree—as PNG, SVG, PDF, CSV, or Excel.

The storage card reports completed cases, authoritative Datastores, and disposable analysis-cache files. Hypercube runs do not create persistent full CSV trees.

## Export

Use **5 Hypercube → Export** to choose the common baseline or up to three verified completed cases per batch. Workbench queues each item separately in the app-wide FIFO export queue, generates output CSVs temporarily from its Datastore, and opens one save dialog per ZIP. The activity panel reports the current case and package position, preparation, CSV generation, compression, save-dialog state, cleanup, elapsed time, heartbeat, artifact size, and queued count. Each ZIP contains the complete resolved input CSV set, generated output CSVs, and a manifest with project, case, axis, runtime, and fingerprint information. It never includes the Datastore. Temporary generated CSVs are removed after success, cancellation, or failure, and later packages continue if one item is cancelled or fails.
