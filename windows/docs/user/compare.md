# Compare Results

Compare shows observed differences between completed or previously registered Datastores. Its **Compare**, **Map Visualization**, and **Percent-Change Chart** views each have independent result selectors and retain their own state. Hypercube response analysis lives in **5 Hypercube → Analyze**; a selected Hypercube case can open directly in Map when the output supports geography.

![Compare tab in an empty demonstration workspace](images/compare.png)

## Choose results

Choose a reference and optional comparison in the same control panel as Table, Variable, Year, Rows, and geography. Map and Percent-Change Chart have their own selectors. An uninitialized view inherits the last valid pair, but later changes stay local to that view. Reference-only Compare provides variable explanations, geography filters, sorting, paging, statistics, and reference exports. Ordinary selectors show standard and imported results, not individual Hypercube cases.

New results are registered when Workbench runs complete. Results imported by an older Workbench version remain selectable as read-only legacy records, but Compare no longer imports or manages external result folders.

Archived project results are hidden from normal selection. Hypercube cases stay in Hypercube Analyze rather than appearing as ordinary Compare selections.

## Compare values

Choose a table, variable, common year, row count, and optional geography filter. Workbench safely aligns rows by stable identifiers rather than assuming that row positions match.

Workbench builds a disposable fingerprinted inventory and SQLite value cache from the authoritative RDA datastore. The inventory records tables, variables, years, types, and geography keys after one tree walk. Repeating a selection is normally immediate. The activity bar reports metadata, geometry, calculation, and drawing phases; completed activity uses a stationary checkmark.

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

## Find All Changes

- **Find All Changes** scans every comparable output across the selected results; it is independent of the Table and Variable used by the detailed comparison.
- Each numeric result reports the total percent change in the variable's summed value relative to the reference.
- **All locations** scans every location. **Selected locations** opens an independent cross-output location selector.

The activity strip shows phase, elapsed time, completion/failure, and Stop when cancellation is supported. A cold scan loads each datastore once and caches its safely keyed statistics. Repeating the same roles, data, year, and geography can use the cache.

Unsafe unknown multi-row tables and variables whose value count does not match the table's stable keys are skipped with a reason instead of reporting misleading row-position changes. One skipped variable does not stop discovery from scanning the remaining outputs.

## Chart and exports

**Map Visualization** shades package-defined geographies. The Virginia package offers **County / locality** (the package's Azone county-equivalent geometry) and **Bzone**. Technical metadata and exports retain the Azone identifier so the model geography remains explicit. Future state packages can expose County only when they provide an authoritative mapping.

Direct Azone and Bzone fields are preferred. Household and Worker outputs use their stored geography. Vehicle Bzones are derived independently in each result through `Vehicle.HhId -> Household.HhId -> Household.Bzone`; vehicles without a unique household match are counted as excluded rows. Every mapped numeric row contributes equally to the geographic mean, matching Workbench's ordinary Mean summaries rather than restricting calculations to entity IDs matched across scenarios.

The default display is Change %. Zero-to-zero is 0%; a nonzero comparison with a zero reference has no defined percent and uses the unavailable hatch. Change metrics use a symmetric diverging scale centered on zero and sized to the largest visible absolute change. Reference and comparison metrics use the visible minimum and maximum. A square-root perceptual ramp gives every nonzero value a visible tint while preserving sign and value order; exact zero stays neutral. Map fills, sampled legends, inspectors, 2D/3D views, and exports use the palettes saved in Settings. **Map value labels** shows the active metric at useful zoom levels; it can be combined with zone IDs. Metric, MPO focus, layers, labels, zoom, and pan redraw the generated snapshot without recalculation. The map supports PDF, PNG, SVG, CSV, and Excel exports; visual exports preserve the current viewport and data exports preserve the current statewide or selected-MPO scope.

For PlanRVA Marea outputs, Workbench visually dissolves the contributing Bzones into exactly two clean, selectable logical regions: **Richmond UZA** and **Non-UZA**. Internal Bzone edges are hidden; a zero-valued region remains visible with a neutral fill, outline, label, and displayed zero. Inspector details and data exports retain the technical Marea ID and contributing Bzone provenance. The Virginia state outline remains visible beneath the value layer in 2D and 3D even when optional context layers are hidden.

**Percent-Change Chart** displays a diverging horizontal bar chart for several numeric variables with a common year and its own optional location filter. Bars left of zero are decreases from the reference and bars right of zero are increases. After **Generate chart** finishes, Sort and Display controls immediately transform the cached result without rerunning the calculation.

## Hypercube drilldowns

From **5 Hypercube → Analyze**, select a matrix cell to inspect that case immediately or select two cells for an in-place difference. **Open Map** preserves the selected case and output and routes spatial results into Map. The removed general Compare and curve handoffs are not shown. See [Hypercube workflow](hypercube.md) for cached response matrices, Find All Changes, scenario rankings, and exports.

**Export data** offers four products. **All Locations Changed Outputs** and **Selected Locations Changed Outputs** contain one row per changed output with a Change % column for each comparison. **Current View** contains every matching row for the active variable, comparison location scope, and sort order, not only the displayed page. **Full Variable Data** exports every row for one or more comparison-compatible outputs in original order and ignores active location filters. Its CSV option creates a ZIP with one CSV per output; its Excel option creates a workbook with separate variable sheets and an index. The Windows **Export** menu exposes the same products.

Excel workbooks add frozen and filtered headers, typed values, readable widths, neutral delta highlighting, statistics, and a provenance sheet. Provenance records datastore IDs and fingerprints, year, table, variable, units, geography filters, five-decimal comparison precision, generation time, and Workbench version without exposing workspace paths. Large datasets are split across numbered sheets rather than truncated. Workbook generation is reconnectable and cancellable from the Compare activity strip.
