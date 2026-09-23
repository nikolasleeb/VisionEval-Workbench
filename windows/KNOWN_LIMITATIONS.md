# Known Limitations

## Platform support

- The public Windows application is validated for Windows 11 x64.
- The installer is not Authenticode-signed, so Windows may display a publisher warning.
- Workbench requires an existing compatible native `VE_Runtime`, `VE_HOME`, and R installation; it does not install or update them.
- Docker and the ARM64 Workbench runtime image are not used by the Windows application.
- This unsigned candidate may trigger Microsoft Defender SmartScreen; verify the SHA-256 checksum before running it.

## Virginia statewide execution

The Virginia package supports statewide region generation, map inspection, and MPO extraction. Full statewide VisionEval execution may fail in `VELandUse::PredictHousing` when statewide integer housing demand is allocated across zero-probability groups. Use an MPO-sized region for executable Virginia scenario testing.

## Runtime and data

- VisionEval 4.0.0 and R 4.5.3 x64 pass the native capability checks. The current installation does not contain a `WORKBENCH-RELEASE` marker, so provenance is reported as unavailable rather than inferred.
- R may print nonfatal `C.UTF-8` locale warnings on Windows before the native CLI output.
- Generated projects remain pinned to the assets recorded when they were created.
- Installing a newer package does not silently rewrite an existing project.
- Official ArcGIS map geometry may be downloaded on first use and cached locally; restricted raw geometry is not redistributed in the regional package.
