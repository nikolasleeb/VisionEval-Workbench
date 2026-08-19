# VisionEval Workbench 1.0.1 for Windows

This Windows patch release makes native VisionEval execution strictly serial. Workbench now permits one desktop instance at a time and uses a cross-process lock for the selected `VE_Runtime`, protecting against duplicate or still-shutting-down backend processes.

Settings spacing is corrected on Numbers, Notifications, and Resources. Onboarding, Settings, About, and other dialogs remain above the Windows taskbar, including on scaled or shorter displays. About is available again in Settings and as a working application-menu window, reports the installed version, and can manually check GitHub for updates.

Workbench checks once weekly for newer published stable releases and shows a dismissible in-app link when one is available. This advisory check never downloads or installs an update. App diagnostic errors are retained per workspace for 30 days or 500 entries, and can be cleared from Settings without affecting runs, results, or exported bundles.

GitHub checks use the Windows certificate trust store so they also work on networks with locally installed certificate authorities. Cancelling a native run now stops its complete R process tree and retries cleanup while Windows releases temporary file locks, preventing partial results from being stranded as a cleanup failure.

Download `VisionEval-Workbench-v1.0.1-windows-x64-setup.exe` from the GitHub release. Existing workspaces and runtime profiles are retained when upgrading.
