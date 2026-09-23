# Getting Started

## First launch

Choose where Workbench should keep its workspace. Use the suggested location or an empty recognizable folder separate from `VE_RUNTIME` and `VE_HOME`. An external SSD is supported when internal space is limited. If a saved workspace is later moved or unavailable, Workbench asks you to locate it rather than creating a replacement.

## Runtime setup

When no verified runtime is available, onboarding opens automatically. Follow [Connect VE_Runtime on Windows](setup.md) to detect or select the three independent paths, or choose **Install R 4.5.3 + VisionEval RC7** for a current-user installation. Administrator privileges are not required.

Choose **Skip for now** if you only need to inspect inputs, edit projects, or view existing results. A verified connection is required before a run can start.

## Install assets

New workspaces contain no regional data. Open **Settings → Assets** and install an approved regional package. Region Builder creates compatible model templates and InputLibraries; manual runnable-model importing is not required.

## Create your first project

1. Open **Create → Develop** and preview or build the required region assets.
2. Open **Create → Setup** and choose a project name, model template, and InputLibrary.
3. Choose an untouched baseline or a compatible completed baseline.
4. Create the project, open Editor, and add a scenario.
5. Save changes, open Review, and continue to Run when validation passes.

Entering Run never starts a job automatically.

## Window behavior

Workbench follows the usable Windows viewport when maximized, restored, moved between displays, or scaled. Pages remain scrollable and reserve a bottom safety gutter so final controls stay above the taskbar.
