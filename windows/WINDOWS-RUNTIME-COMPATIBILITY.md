# VisionEval Workbench 2.0 — Windows Runtime Compatibility

Release status: **UNSIGNED release candidate**  
Target: Windows x64, native VisionEval only  
Application version: 2.0.0

## Verified environment

| Component | Verified value |
| --- | --- |
| Windows | 10.0.26100.8894, AMD64 |
| WebView2 | 153.0.4234.48 |
| R | 4.5.3 x64 (UCRT) |
| VisionEval | 4.0.0 |
| visioneval package | 3.1.1 |
| VEStart | 4.0.0 |
| VEModel | 3.1.1 |
| VETravelDemandMM | 3.1.1 |

The candidate independently discovers and validates `VE_RUNTIME`, `VE_HOME`, and
`Rscript.exe`. Invalid configured or environment candidates are skipped with a
diagnostic warning while discovery continues. Validated paths are canonicalized,
and paths containing spaces are supported.

## Execution contract

- Windows uses the native adapter unconditionally. Docker settings and environment
  overrides cannot select a Docker adapter.
- Standard and Hypercube work share one FIFO execution slot. A request for parallel
  Hypercube execution is persisted and dispatched as a serialized native batch.
- Runtime restart and shutdown are serialized. Active R descendants are stopped with
  Windows process-tree termination and a direct-termination fallback.
- The installer does not install or modify R, VisionEval, a Docker client or image,
  user Datastores, workspaces, or credentials.

## Known limitations

- The candidate is unsigned. Windows SmartScreen may show an unknown-publisher
  warning; users should verify the published SHA-256 before running it.
- The verified VisionEval installation does not contain `WORKBENCH-RELEASE`.
  Package/version capability checks pass, but release-marker provenance is reported
  as unavailable.
- R 4.5.3 emits `C.UTF-8` locale warnings on this Windows host. Native doctor,
  capability verification, and model execution continue successfully.
- Native execution is intentionally serialized in 2.0. Docker and native parallel
  execution are out of scope.

