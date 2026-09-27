# Using Workbench on Apple Silicon macOS 2.0

Follow the illustrated [Project and Scenario walkthrough](https://github.com/nikolasleeb/VisionEval-Workbench/raw/refs/heads/main/docs/tutorials/macOS-v2.0/Mac-2.0-Project-and-Scenario-Walkthrough.pdf) alongside the [Mac videos](https://sites.google.com/view/ve-workbench/documentation/mac-resources).

1. **Explore:** read input explanations, units, and dependencies.
2. **Create → Develop:** build an official MPO or custom region from a source covering its geography. For Virginia regions, choose the package's statewide Virginia InputLibrary, not unrelated PlanRVA inputs.
3. **Create → Setup:** name the project and preserve an untouched baseline.
4. **Create → Editor:** use **New file** for a focused single-file edit. The Batch Change arrow opens coordinated edits across multiple files with shared operation and scope. Choose target year and geography deliberately.
5. **Create → Review:** start with the scenario summary and saved file, row, and cell counts. Expand Automatic summary and file details to inspect before/after values. Your note records intent; the generated summary records saved changes.
6. **Run:** select baseline and scenarios, check runtime and resources, and wait for successful completion. Inspect job logs for failures.
7. **Compare:** select completed reference and comparison results. Run **Find All Changes** first to discover affected outputs, then explore one variable in detail. Use Map Visualization for spatial inspection. Check units, coverage, and warnings.

Synthetic-population IDs can be run-local; do not assume identical IDs identify the same entity across independent runs. Positive change means an increase, not automatically an improvement.

[Hypercube](macOS-Hypercube) adds **Build → Review → Run → Analyze → Export** for bounded matrices. [Workspaces and Resources](macOS-Workspaces-and-Resources) explains concurrency, Docker memory, storage, and SSD move/reopen behavior.
