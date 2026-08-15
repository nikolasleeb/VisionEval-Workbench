# Prioritized Roadmap

Statuses: **Release blocker**, **Near term**, **Planned**, and **Research**. Acceptance criteria are required before implementation begins.

## Future plans at a glance

1. **Dependency evidence and observed-change links:** make the model graph explain which module consumes or produces a field, then connect declared paths to outputs that actually changed in selected runs.
2. **Notification routing and batch summaries:** aggregate run batches and make notification clicks return to the relevant run, comparison, scan, dashboard, or completed export.
3. **Runtime resource diagnostics:** report Docker allocation, Workbench limits, peak job/scan memory, storage growth, and slow phases with actionable guidance.
4. **Comparison visualization and geography:** add question-driven charts and a shared, licensed, keyboard-accessible geography map without inventing unsupported boundaries.
5. **Release maturity:** after the unsigned AMD64 v1, add signing/notarization, validate additional platforms, and keep the pinned runtime and PlanRVA regression review current.

Formatted Excel exports and native Save dialogs are implemented. Older imported-result registrations remain readable for compatibility, while new external result imports are intentionally unsupported.

## Release blockers

### Approved immutable runtime

- **Motivation:** users need reproducible runtime setup.
- **Current limitation:** the v1 candidate uses official VE-40-RC6 plus an explicitly unofficial Workbench compatibility patch; publication and clean-machine verification remain gated.
- **Dependencies:** AMD64 build verification, clean-machine model checks, public registry policy, and repository approval.
- **Acceptance:** publish the approved image by immutable digest, update compatibility data, verify clean first launch, and provide rollback instructions.

### Metadata decisions

- **Motivation:** trustworthy units are essential for editing and comparison.
- **Current limitation:** D1B, OwnCostPerMile, rate denominators, currency years, and road-cost fields retain conflicts or ambiguity.
- **Dependencies:** producing/consuming module review and domain-owner approval.
- **Acceptance:** update both conflict formats with reviewer decisions; preserve competing sources; add regression tests for every approved label.

### Signed release and broader platform support

- **Motivation:** a public app must install predictably without hidden development dependencies.
- **Current limitation:** v1 is ad-hoc signed and not notarized. Apple Silicon and Windows use separate validated packages.
- **Dependencies:** Apple credentials, platform-specific runtime validation, approved image, and compatibility manifests.
- **Acceptance:** signed/notarized/stapled AMD64 DMG plus equivalent tested packages for any newly supported platform; verified checksums and clean-machine smoke tests.

## Near-term reliability and performance

### Comparison data-path benchmark

**Status: In progress.** Compare now includes a selected-variable profiler that measures authoritative RDA cold/warm reads, stable-key decoding and alignment, retained CSV discovery/parsing, bytes, row counts, and five-decimal key/value parity. It never changes the active data path. Representative table-wide peak-memory and storage results are still required before choosing a source per operation.

- **Motivation:** comparison and scan latency is the largest analysis cost.
- **Current limitation:** the in-app sample profiler covers one selected reference variable at a time; a repeatable suite across small, household, vehicle, worker, zone, and regional outputs is not complete.
- **Dependencies:** representative small and PlanRVA fixtures, correctness/key parity harness, cold/warm cache instrumentation.
- **Acceptance:** publish correctness, wall-time, peak-memory, and storage results by table; choose paths per operation using evidence; never prefer faulty or manually patched CSVs.

### Scan, dashboard, and export profiling

- **Motivation:** Changed-output discovery must finish predictably and show progress.
- **Current limitation:** performance targets and phase-level telemetry need broader validation.
- **Dependencies:** operation tracing, cache metrics, cancellation tests, Docker memory diagnostics.
- **Acceptance:** PlanRVA cold global scan under three minutes and cached scan under five seconds on the reference Mac; actionable memory errors; verified cancellation and reconnection.

### Resource diagnostics

- **Motivation:** users need to understand whether Docker memory constrains work.
- **Current limitation:** Automatic mode is accurate but does not report peak usage.
- **Dependencies:** Docker capability inspection and process/container metrics.
- **Acceptance:** report Docker allocation, Workbench cap, peak per-job/scan memory, and clear recommendations without modifying Docker Desktop settings.

### Completion notifications

**Status: In progress.** Opt-in macOS notifications now cover individual VisionEval run success/failure and tracked Compare operations, including comparison, scan, datastore import, dashboard, and Excel export completion. Batch-level aggregation and notification-click routing remain open.

- **Motivation:** comparisons and exports can run long enough for users to switch tasks.
- **Current limitation:** progress is visible only inside Workbench.
- **Dependencies:** macOS notification permission and background-operation lifecycle.
- **Acceptance:** opt-in success/failure notifications for scans, comparisons, dashboards, exports, and run batches; clicking returns to the relevant operation.

### Formatted spreadsheet exports

**Status: Completed July 21, 2026; refined August 5, 2026.** Compare produces persistent, cancellable XLSX jobs for the current view, changed rows in the current view, and changed-output scans. Workbooks contain typed data, percentage changes, statistics, provenance, filters, frozen headers, safe text handling, and row-limit splitting. CSV exports use the same comparison snapshot and scope.

- **Motivation:** analysts frequently hand results to Excel users.
- **Current limitation:** packaged-app and representative PlanRVA workbook performance still need release-candidate validation.
- **Dependencies:** workbook library and export metadata contract.
- **Acceptance:** XLSX with provenance/metadata sheet, typed values, units, filters, frozen headers, sensible widths, and neutral directional delta formatting; CSV output remains unchanged.

## Planned visualization and understanding

### Dependency tagging, grouping, and observed-change links

- **Motivation:** the existing graph is comprehensive but difficult to scan across many modules.
- **Current limitation:** focused paths lack domain tags, model-family grouping, and direct links to observed Comparison results.
- **Dependencies:** stable tags for files, fields, modules, intermediaries, and outputs; comparison-variable mapping.
- **Acceptance:** filter/search by tag and family; collapse groups; open an input's possible outputs; distinguish predicted paths from outputs that actually changed in selected runs.

### Model explorer documentation links

- **Motivation:** users need to understand why a module consumes or produces a value.
- **Current limitation:** graph nodes do not consistently link to version-specific VisionEval source and documentation.
- **Dependencies:** exact runtime/module version metadata and durable official URLs.
- **Acceptance:** each supported module links to its version-matched source/specification; custom modules link to imported specifications or display unresolved status.

### Shared geography map

- **Motivation:** selecting geography is clearer spatially than through long checklists.
- **Current limitation:** Editor and Compare have mappings but no shared map.
- **Candidate source:** the public UVA Library ArcGIS `AzonesBzonesVa` map has been recorded in [`reference-data/virginia-visioneval-zones.arcgis.json`](reference-data/virginia-visioneval-zones.arcgis.json). It exposes 133 Azone and 5,963 Bzone polygons through GeoJSON-capable query layers.
- **Dependencies:** licensing/attribution approval for the candidate source, a checksummed simplified snapshot, stable IDs, template `defs/geo.csv`, performant rendering.
- **Acceptance:** one component used by Editor and Compare; linked MPO, county, Azone, Bzone, and supported lower levels; keyboard-accessible selection; never infer boundaries absent from the template.

### Comparison visualizations

- **Motivation:** tables and the dashboard do not cover distributions, geographic patterns, or scenario tradeoffs.
- **Current limitation:** visualization types and decision questions are not yet cataloged.
- **Dependencies:** shared chart contracts, units, filtering, and export support.
- **Acceptance:** add only charts tied to documented questions, with reference/comparison roles, accessible legends, filters, provenance, and downloadable output.

## Research

### Virginia dataset to MPO workflow

- **Question:** can users reliably build an MPO-ready model and geography from the statewide Virginia dataset?
- **Candidate source:** [`reference-data/virginia-visioneval-zones.arcgis.json`](reference-data/virginia-visioneval-zones.arcgis.json) records statewide Azone/Bzone geometry and reproducible GeoJSON queries. It does not contain MPO membership or authoritative MPO boundaries.
- **Unknowns:** required inputs, authoritative MPO boundary or locality-membership source, crosswalk validation, model configuration, and whether this belongs in Create or a dedicated Geography/MPO tab.
- **Acceptance before planning:** prototype one documented MPO, enumerate required transformations, validate against a known model, and define provenance and error checks.

### County districts and subcounty geographies

- **Question:** which district boundaries are authoritative and how do they map to VisionEval zones?
- **Unknowns:** many templates do not define county districts in `defs/geo.csv`.
- **Acceptance before implementation:** identify a licensed authoritative source, stable identifiers, and validated Azone/Bzone crosswalks. Do not invent or spatially approximate unsupported districts.
