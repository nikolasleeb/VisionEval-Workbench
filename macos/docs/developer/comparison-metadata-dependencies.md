# Comparison, Metadata, and Dependencies

## Comparison engine

The datastore catalog is the primary result source. Each registration records project, scenario, template fingerprint, runtime version/digest, result path, completion time, and verification state. Older imported registrations remain readable, but new results are registered only from completed Workbench runs.

Rows are aligned with stable table-specific keys. Known household, vehicle, worker, Azone, Bzone, and Marea structures are supported. Unknown multi-row tables are rejected when a safe key cannot be established; row position must never masquerade as identity.

Selected year and geography apply consistently to row comparisons, statistics, percent change, scans, dashboard data, and exports. County filtering maps county labels to Azone and Bzone membership through the registered template's `defs/geo.csv`; it selects rows and does not aggregate them.

## Change scans and cache

Comparisons, changed-output discovery, location-scoped scans, and dashboards share the SQLite comparison cache. The batch R extractor loads each table's stable key once and all missing requested variables together. Persistent operations expose cache validation, extraction/import, page-query, statistics, success, failure, and cancellation state. Cache and summary keys include datastore registrations and source-file fingerprints, year, table, variable, geography, precision, and roles; registrations or changed RDA contents invalidate derived data.

Performance comparisons between RDA and CSV must verify identical values and keys before timing. Faulty or manually patched CSV output is not an acceptable optimization source.

## Units and explanations

Input metadata precedence is:

1. Exact unit year or scale encoded in a CSV header.
2. Selected template `defs/units.csv`.
3. Executing module specification.
4. Human-written explanation guide.

Output and intermediary metadata use the producing module specification, while consumer disagreements remain warnings. Identifiers such as Geo, Azone, Bzone, household, vehicle, and worker IDs are unitless strings and are never rounded. Numeric display values are rounded to five decimal places without modifying stored values.

All disagreements remain in [unit-conflicts.md](../unit-conflicts.md) and its JSON companion. Do not silently “fix” disputed metadata.

## Dependency extraction

Each model template has a fingerprinted graph derived from `scripts/run_model.R` execution order plus VisionEval VE-40-RC6 Get/Set/input specifications. The closest valid preceding producer is connected to a later consumer by table and variable. Custom specifications are used when present; unsupported custom modules appear as unresolved nodes.

A datastore variable can be both an intermediary and stored output. Catalog-only variables absent from the selected execution path are excluded by default. The graph communicates declared possible effects—not guaranteed sensitivity or causality.

Dependency responses include deterministic layered layout metadata keyed by stable node IDs. Focused responses include backend-defined metrics and lanes plus `focusView.kind`, `focusView.view`, role-specific counts, navigation metadata, and per-node `viewRole`. Earlier-step values include `upstreamSource`: a known preceding producer is identified by module ID, execution order, label, and package; an unmatched framework source is explicitly marked `type: existing`. Module requests accept `scope=context|path`; path scope requires a connected input-file or input-field `originId`. Value requests accept `view=production|consumers`; existing value URLs default to production when a producer exists and consumers otherwise.

The focused presentation classifies nodes by their role in the current question rather than their global datastore lifetime. Value production is deliberately bounded to one producer step; deeper ancestry is navigated value by value because a late PlanRVA output may have hundreds of ancestors. Value-consumer views contain direct readers only. Equivalent Inp/Get declarations are collapsed only in focused payloads; the authoritative full graph retains both technical nodes. The browser applies only a viewport transform for pan and zoom. Identical parameters and coordinates feed SVG and tiled vector-PDF exports. Layout/cache versions are independent compatibility boundaries and must be bumped when positioning semantics change.

## Exports

CSV exports preserve raw tabular interchange. Full-variable CSV exports use a ZIP with one CSV per output. XLSX exports preserve the same values and identifiers while adding filters, frozen headers, typed cells, neutral delta formatting, statistics, and path-free provenance. Workbook jobs are persistent, reconnectable, cancellable, and split at Excel's row limit without truncation. Percent-change chart PDF is presentation-oriented. Dependency SVG and PDF exports contain only graph metadata already returned by the dependency API and never expose workspace paths.
