# Windows Installation and Runtime

Use this page to install VisionEval Workbench 1.0.1 for Windows 11 x64 and connect it to an existing native VisionEval runtime.

> [!NOTE]
> For complete first-time-user guidance, use the current [Windows User Guide](https://github.com/nikolasleeb/VisionEval-Workbench/blob/main/windows/UserGuide.md). The older screenshot PDF and DOCX describe Windows 1.0.0 and are archived references.

## Requirements

- Windows 11 x64
- An existing compatible native VisionEval `VE_Runtime`
- Its separate `VE_HOME` package library
- A compatible `Rscript.exe`

## Install Workbench

1. Open the [latest release](https://github.com/nikolasleeb/VisionEval-Workbench/releases/latest).
2. Download `VisionEval-Workbench-v1.0.1-windows-x64-setup.exe`.
3. Run the installer and launch **VisionEval Workbench**.
4. Choose an empty, recognizable workspace folder that is separate from `VE_Runtime`.

## Connect the runtime

1. Open **Settings → Runtime**.
2. Select the existing `VE_Runtime` working folder.
3. Review the detected `VE_HOME` and `Rscript.exe` paths.
4. Use advanced overrides only when automatic detection is incorrect.
5. Select **Verify runtime** before starting a model run.

## Verify the setup

Continue only when Workbench reports that the runtime is verified and ready. Docker is not used by the Windows edition, and Workbench will not download or update the selected runtime.

**Next:** [Using Workbench on Windows](Using-Workbench-on-Windows) · [Troubleshooting](Troubleshooting)
