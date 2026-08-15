# Compare Results

Compare shows observed differences between completed or previously registered datastores. It has **Load Data**, **Compare**, **Map Visualization**, and **Percent-Change Chart** subtabs.

![Compare tab in an empty demonstration workspace](images/compare.png)

## Load Data

Choose one reference datastore and optionally up to two comparison datastores. Loading only the reference opens a single-datastore view with variable explanations, geography filters, sorting, paging, statistics, and reference exports. Deltas, change scans, percent-change summaries, and charts become available when a comparison datastore is also selected. Each result shows project, scenario, template, runtime, completion time, and verification status.

New results are registered when Workbench runs complete. Results imported by an older Workbench version remain selectable as read-only legacy records, but Compare no longer imports or manages external result folders.

Archived project results are hidden from normal selection.

## Compare values

Choose a table, variable, common year, row count, and optional geography filter. Workbench safely aligns rows by stable identifiers rather than assuming that row positions match.

Workbench builds a disposable SQLite cache from the authoritative RDA datastore. The requested page appears first while full-table statistics finish in the background. Repeating the same selection is normally much faster. Storage settings show the cache size and let you clear it; clearing the cache does not remove results.

Available analysis includes:

- Changed-row counts.
- Total percent change for numeric outputs.
- Rows-changed percentage for categorical outputs.
- Increased/decreased counts, net change, average-row percent, and distributions.
- Optional red/green directional deltas.
- Changed-rows-only filtering and pagination.
- Three-state column sorting: original, ascending, descending, then original.

Numeric values display at up to five decimal places. Geographic and entity identifiers are never rounded.

## Geography filters

Detailed comparisons, changed-output discovery, percent-change charts, and selected-location exports each have an independent location selector. A location change marks the affected result stale until its action is run again.

County filtering uses the result's model-template `defs/geo.csv` to map county labels to Azones and Bzones. Household, Vehicle, and Worker rows are included when their stored location belongs to a selected county in the reference or a comparison. County filtering is disabled for purely regional outputs that cannot be mapped safely.

## Discover changed outputs

- **Find changed outputs** scans every comparable output across the selected results; it is independent of the Table and Variable used by the detailed comparison.
- Each numeric result reports the total percent change in the variable's summed value relative to the reference. With two comparison datastores, each scenario receives its own total-percent-change value.
- **All locations** scans every location. **Selected locations** opens an independent cross-output location selector.

The activity strip shows phase, elapsed time, completion/failure, and Stop when cancellation is supported. A cold scan loads each datastore once and caches its safely keyed statistics. Repeating the same roles, data, year, and geography can use the cache.

Unsafe unknown multi-row tables and variables whose value count does not match the table's stable keys are skipped with a reason instead of reporting misleading row-position changes. One skipped variable does not stop discovery from scanning the remaining outputs.

## Chart and exports

**Map Visualization** shades package-defined geographies. The Virginia package offers **County / locality** (the package's Azone county-equivalent geometry) and **Bzone**. Technical metadata and exports retain the Azone identifier so the model geography remains explicit. Future state packages can expose County only when they provide an authoritative mapping.

Direct Azone and Bzone fields are preferred. Household and Worker outputs use their stored geography. Vehicle Bzones are derived independently in each result through `Vehicle.HhId -> Household.HhId -> Household.Bzone`; vehicles without a unique household match are counted as excluded rows. Every mapped numeric row contributes equally to the geographic mean, matching Workbench's ordinary Mean summaries rather than restricting calculations to entity IDs matched across scenarios.

The default display is Change %. Zero-to-zero is 0%; a nonzero comparison with a zero reference has no defined percent and uses the unavailable hatch. Change metrics use a symmetric diverging scale centered on zero and saturate at the 95th percentile of absolute displayed values so outliers do not flatten the rest of the map. **Map value labels** shows the active metric at useful zoom levels; it can be combined with zone IDs. Metric, MPO focus, layers, labels, zoom, and pan redraw the generated snapshot without recalculation. The map supports PDF, PNG, SVG, CSV, and Excel exports; visual exports preserve the current viewport and data exports preserve the current statewide or selected-MPO scope.

**Percent-Change Chart** displays a diverging horizontal bar chart for several numeric variables with a common year and its own optional location filter. Bars left of zero are decreases from the reference and bars right of zero are increases. After **Generate chart** finishes, Sort and Display controls immediately transform the cached result without rerunning the calculation.

**Export data** offers four products. **All Locations Changed Outputs** and **Selected Locations Changed Outputs** contain one row per changed output with a Change % column for each comparison. **Current View** contains every matching row for the active variable, comparison location scope, and sort order, not only the displayed page. **Full Variable Data** exports every row for one or more comparison-compatible outputs in original order and ignores active location filters. Its CSV option creates a ZIP with one CSV per output; its Excel option creates a workbook with separate variable sheets and an index. The macOS **Export** menu exposes the same products.

Excel workbooks add frozen and filtered headers, typed values, readable widths, neutral delta highlighting, statistics, and a provenance sheet. Provenance records datastore IDs and fingerprints, year, table, variable, units, geography filters, five-decimal comparison precision, generation time, and Workbench version without exposing workspace paths. Large datasets are split across numbered sheets rather than truncated. Workbook generation is reconnectable and cancellable from the Compare activity strip.
