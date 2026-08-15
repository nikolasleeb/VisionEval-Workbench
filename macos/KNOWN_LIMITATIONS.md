# Known Limitations

## Platform support

- The public Mac application is validated for Apple Silicon and macOS 12 or newer.
- Intel Macs are not supported.
- The application is ad-hoc signed but is not Apple-notarized, so a one-time Gatekeeper workaround may be required.
- The verified Docker runtime is `linux/arm64` and is not a Windows/x64 runtime.

## Virginia statewide execution

The Virginia package supports statewide region generation, map inspection, and MPO extraction. Full statewide VisionEval execution may fail in `VELandUse::PredictHousing` when statewide integer housing demand is allocated across zero-probability groups. Use an MPO-sized region for executable Virginia scenario testing.

## Runtime and data

- The runtime is an unofficial Workbench distribution built from VisionEval `VE-40-RC6` plus the documented composite household-ID alignment patch.
- The app pins an immutable runtime digest and does not use a floating `latest` tag.
- Generated projects remain pinned to the assets recorded when they were created.
- Installing a newer package does not silently rewrite an existing project.
