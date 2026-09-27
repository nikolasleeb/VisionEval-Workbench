# Mac 2.0 Hypercube

Read the illustrated [Hypercube walkthrough](https://github.com/nikolasleeb/VisionEval-Workbench/raw/refs/heads/main/docs/tutorials/macOS-v2.0/Mac-2.0-Hypercube-Walkthrough.pdf).

1. **Build:** create a dedicated Hypercube project with an untouched baseline. Add parameter axes, operation, start/end/interval, shared target year, and geography. Preview case counts, affected rows, and resource estimates before generating scenarios.
2. **Review:** check the saved matrix and provenance. Once a case is submitted or produces a result, the matrix locks; create a new project for a different experiment.
3. **Run:** use Run Missing for incomplete work and the common baseline if needed. Keep Workbench and Docker open. Set concurrency in **Settings → Resources** according to shared Docker memory.
4. **Analyze:** run **Find All Changes** first. Its own Year and Aggregation apply across eligible outputs and verified completed cases; response-matrix selections do not constrain it. Review output/scenario rankings, coverage, and warnings. Identical scans can reuse cached results.
5. Explore a variable in the Response Matrix. Select a cell for case details or two to compare cases. Select a case, then **Open Map** above the matrix. Check year, geography, aggregation, and measure in Compare → Map Visualization, then Generate Map. The map compares the selected case with the common baseline.
6. Export the displayed chart as PNG/SVG/PDF, or data as CSV/Excel. The **Export** tab prepares separate case ZIPs with resolved inputs and generated output CSVs, not complete workspace backups.

The fuel-cost/tax example uses five values per axis: 25 cases plus the common baseline. Target year 2045 selects affected rows; FuelCost.2024/FuelTax.2024 column labels do not set the analysis year. Choose an available completed output year.

Hypercube retains authoritative Datastores. Disposable analysis caches can be rebuilt. Reopening results after moving a workspace should not require rerunning successful cases.
