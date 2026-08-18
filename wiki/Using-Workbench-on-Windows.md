# Using Workbench on Windows

The Windows edition follows the same **Explore → Create → Run → Compare** workflow as macOS while executing models through a verified native VisionEval runtime.

## Explore

Inspect input files, descriptions, units, declared dependencies, and available regional data without changing source folders.

## Create

Create a project from an installed model template and InputLibrary. Workbench preserves an untouched baseline, stores scenarios as deliberate overlays, and lets you review saved differences before running.

## Run

Workbench prepares a fresh model copy, applies the selected scenario overlay, and executes it through the verified native runtime. Entering **Run** never starts a job automatically.

> [!NOTE]
> Windows model jobs run one at a time. Allow the active run to finish before the next queued scenario begins.

## Compare

Register completed VisionEval datastores and compare tables, statistics, charts, 2D maps, optional 3D geography, and exports. Generated caches can be rebuilt and are not the authoritative result.

## Assets and guided exercise

Regional ZIP files are installed through **Settings → Assets**; see [Regional Packages](Regional-Packages). For a complete worked example, use the [scenario walkthrough](https://github.com/nikolasleeb/VisionEval-Workbench/blob/main/docs/tutorials/VisionEval-Workbench-Scenario-Walkthrough.pdf).

**Related:** [Windows Installation and Runtime](Windows-Installation-and-Runtime) · [Troubleshooting](Troubleshooting)
