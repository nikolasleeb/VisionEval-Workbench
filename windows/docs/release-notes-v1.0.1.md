# VisionEval Workbench 1.0.1 for Windows

This Windows patch release makes native VisionEval execution strictly serial. Workbench now permits one desktop instance at a time and uses a cross-process lock for the selected `VE_Runtime`, protecting against duplicate or still-shutting-down backend processes.

Settings spacing is corrected on Numbers, Notifications, and Resources. Onboarding, Settings, About, and other dialogs remain above the Windows taskbar, including on scaled or shorter displays. About is available again in Settings and as a working application-menu window, and reports the installed version.

Download `VisionEval-Workbench-v1.0.1-windows-x64-setup.exe` from the GitHub release. Existing workspaces and runtime profiles are retained when upgrading.
