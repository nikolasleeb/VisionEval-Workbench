# Windows Installation and Runtime

Use this page for VisionEval Workbench 2.0 on Windows 11 x64. Start with the [Windows 2.0 installation and upgrade quick-start](https://github.com/nikolasleeb/VisionEval-Workbench/blob/main/docs/tutorials/windows-v2.0/Windows-2.0-Installation-and-Upgrade-Quick-Start.pdf) if you are coming from an older Workbench, R, or VisionEval setup. The [complete Windows 2.0 User Guide](https://github.com/nikolasleeb/VisionEval-Workbench/blob/main/windows/docs/user/VisionEval-Workbench-2.0-Windows-User-Guide.pdf) covers the full workflow.

## Install Workbench

1. Download the [Windows 2.0 installer](https://github.com/nikolasleeb/VisionEval-Workbench/releases/download/v2.0.0/VisionEval-Workbench-v2.0.0-windows-x64-setup.exe) and run the EXE.
2. Launch **VisionEval Workbench**. Choose a new workspace or **Open existing workspace** to keep using your projects and results.
3. Finish or stop active runs before changing a connected runtime.

The EXE installs Workbench, not R or VisionEval. The optional **Install R 4.5.3 + VisionEval RC7** action in first-run setup or **Settings → Runtime** downloads, installs, and verifies the certified pair for your Windows account. Docker is not used by the Windows edition.

## Connect or install the runtime

- If you already have a complete R 4.5 and VE-40-RC7 installation, select its `VE_RUNTIME`, `VE_HOME`, and `Rscript.exe` paths independently in **Settings → Runtime**, then choose **Verify runtime**.
- If VisionEval is older, Workbench cannot enable model runs until the selected runtime verifies as VE-40-RC7. The managed setup can reuse a compatible R 4.5 installation while installing RC7.
- If you only have an older R series, managed setup installs R 4.5.3 for the current user and leaves the older R installation in place.

Installing RC7 into an existing `VE_HOME` can replace that location's R 4.5 VisionEval library. If you need the earlier runtime to remain usable, record its paths and select separate `VE_RUNTIME` and `VE_HOME` folders for 2.0. These two folders must be separate and non-nested. The workspace is a third location and should not be deleted as part of runtime setup.

Continue only when Workbench reports **Native VisionEval ready**. Then install the needed regional/model package under **Settings → Assets** and test a small run. See the [detailed runtime setup and offline instructions](https://github.com/nikolasleeb/VisionEval-Workbench/blob/main/windows/docs/user/setup.md) if detection, download, or verification fails.

The previous [Windows 1.0.1 installation guide](https://github.com/nikolasleeb/VisionEval-Workbench/blob/main/docs/tutorials/VisionEval-Workbench-Installation-Windows-x64.pdf) remains available for earlier releases; do not use it as the primary 2.0 setup guide.

**Next:** [Using Workbench on Windows](Using-Workbench-on-Windows) · [Troubleshooting](Troubleshooting)
