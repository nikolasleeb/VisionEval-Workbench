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

New workspaces intentionally contain no model or input data.

- An **InputLibrary** is a folder of scenario input CSV files.
- A **model template** is a complete runnable VisionEval model folder.

Open **Settings → Assets** or **Create → Setup** to import them. A runnable model must contain:

- `visioneval.cnf`
- `scripts/run_model.R`
- `defs/`
- `inputs/`

Workbench copies imported assets into the workspace. It never edits the original folders.

## Create your first project

1. Open **Create → Setup**.
2. Choose a project name, model template, and InputLibrary.
3. Choose an untouched baseline or a compatible completed baseline.
4. Create the project. Workbench opens the Editor.
5. Select **New Scenario**, then **New File** to edit one input CSV or **Batch Change** to apply the same operation across several files.
6. Save changes, open Review, and continue to Run when validation passes.

The Run confirmation never starts automatically when you enter the Run tab.
