# Known Limitations

## Platform support

- The public Windows application is validated for Windows 11 x64.
- The installer is not Authenticode-signed, so Windows may display a publisher warning.
- Workbench requires an existing compatible native `VE_Runtime`, `VE_HOME`, and R installation; it does not install or update them.
- Docker and the ARM64 Workbench runtime image are not used by the Windows application.

## Virginia statewide execution

The Virginia package supports statewide region generation, map inspection, and MPO extraction. Full statewide VisionEval execution may fail in `VELandUse::PredictHousing` when statewide integer housing demand is allocated across zero-probability groups. Use an MPO-sized region for executable Virginia scenario testing.

## Runtime and data

- Generated projects remain pinned to the assets recorded when they were created.
- Installing a newer package does not silently rewrite an existing project.
- Official ArcGIS map geometry may be downloaded on first use and cached locally; restricted raw geometry is not redistributed in the regional package.
