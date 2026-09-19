# Getting Started

## First launch

On the first launch, Workbench asks where to keep its workspace. The recommended location is:

`~/VisionEval Workbench Workspace`

That location is easy to find from your Home folder. You can instead choose an empty folder or select a recognizable existing Workbench workspace. Workbench remembers the selected workspace and reopens it on later launches.

If the saved folder is moved, disconnected, or deleted, Workbench shows recovery choices. It does not silently create a different workspace.

## Runtime setup

The runtime step is optional during onboarding. Follow [Setup](setup.md) for the supported Docker Desktop installation, local image build, verification, and Workbench connection procedure.

Workbench does not connect permanently to a container. It creates temporary containers only while running models.

Choose **Skip for Now** if you want to explore inputs, create scenarios, or inspect existing results without running a model.

## Install assets

New workspaces intentionally contain no model or input data. Install a verified model or regional package from **Settings → Assets → Install package…**. A package supplies a matched InputLibrary and runnable model template; Workbench selects the template automatically when you choose its InputLibrary.

- An **InputLibrary** is a folder of scenario input CSV files.
- A **model template** is a complete runnable VisionEval model folder.

Package authors should include a runnable model containing:

- `visioneval.cnf`
- `scripts/run_model.R`
- `defs/`
- `inputs/`

Workbench copies verified package assets into the workspace. It never edits the original package.

## Create your first project

1. Open **Create → Setup**.
2. Choose a project name and InputLibrary. Workbench uses that library's verified paired model template.
3. Choose an untouched baseline or a compatible completed baseline.
4. Create the project. Workbench opens the Editor.
5. Select **New Scenario**, then **New File** to edit one input CSV or **Batch Change** to apply the same operation across several files.
6. Save changes, open Review, and continue to Run when validation passes.

The Run confirmation never starts automatically when you enter the Run tab.
