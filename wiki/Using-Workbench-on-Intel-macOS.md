# Using Workbench on Intel macOS

The Intel edition follows **Explore → Create → Run → Compare** and starts Docker only for work that requires the AMD64 VisionEval runtime.

## Explore

Inspect inputs, definitions, units, and dependencies without starting Docker or changing source packages.

## Create

Create projects and scenarios in the Workbench workspace. Installed assets are copied into the workspace; source packages and original model folders remain unchanged.

## Run

Start Docker Desktop and verify the managed AMD64 runtime. Workbench prepares a fresh model copy, applies the scenario overlay, and creates a temporary container for the job. Entering **Run** never starts a model automatically.

> [!TIP]
> macOS can run two jobs in parallel when the configured resources allow it. Additional jobs remain queued.

## Compare

Compare completed datastores with tables, statistics, charts, maps, and exports. Docker may be required to read uncached RDA data; existing comparison caches remain usable without it.

## Assets and guided exercise

Regional ZIP files are installed through **Settings → Assets**; see [Regional Packages](Regional-Packages). For a complete worked example, use the [scenario walkthrough](https://github.com/nikolasleeb/VisionEval-Workbench/blob/main/docs/tutorials/VisionEval-Workbench-Scenario-Walkthrough.pdf).

**Related:** [Intel Installation and Runtime](Intel-macOS-Installation-and-Runtime) · [Troubleshooting](Troubleshooting)
