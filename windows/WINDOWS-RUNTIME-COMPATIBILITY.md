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
| VisionEval release | VE-40-RC7 (`7852dc58fad460ff279f5eebf4dd55fe191470ad`) |
| VisionEval package version | 4.0.0 |
| visioneval package | 3.1.1 |
| VEStart | 4.0.0 |
| VEModel | 3.1.1 |
| VETravelDemandMM | 3.1.1 |

The candidate independently discovers and validates `VE_RUNTIME`, `VE_HOME`, and
`Rscript.exe`. Invalid configured or environment candidates are skipped with a
diagnostic warning while discovery continues. Validated paths are canonicalized,
and paths containing spaces and non-ASCII characters are supported. `VE_HOME` and
`VE_RUNTIME` cannot be equal or nested; canonical path checks also reject overlaps
hidden by junctions or symbolic links.

## Certified current-user installation

When no usable native runtime is found, Workbench offers **Install R 4.5.3 +
VisionEval RC7**. It reuses a compatible R 4.5 installation or installs R 4.5.3
for the current user, then installs the official RC7 Windows library. It does not
request elevation or modify system-wide settings.

| Artifact | Official URL | SHA-256 |
| --- | --- | --- |
| R 4.5.3 x64 | `https://cran.r-project.org/bin/windows/base/old/4.5.3/R-4.5.3-win.exe` | `768ae31bb0b6056def5b1a9789a7dc49306bd037d69b0a99cdd90183aa0c1a31` |
| VisionEval RC7 R4.5 library | `https://github.com/VisionEval/VisionEval-4/releases/download/VE-40-RC7/VE-Installer_WinLibrary-R4.5_2026-09-07.zip` | `01a3f58ee5eb0ab40113cc8835ca99ab1d060b89ff9b442b41c35ce93708155d` |

Default locations are `%USERPROFILE%\VE_Home` for `VE_HOME` and
`%LOCALAPPDATA%\VisionEval\VE_Runtime` for `VE_RUNTIME`. The workspace is selected
separately and may reside on an external SSD. Workbench fails closed on download,
TLS, checksum, extraction, or post-install verification errors and restores the
previous VisionEval library when applicable.

## Execution contract

- Windows uses the native adapter unconditionally. Docker settings and environment
  overrides cannot select a Docker adapter.
- Standard and Hypercube work share one FIFO execution slot. Hypercube execution is
  always dispatched as a serialized native batch.
- Runtime restart and shutdown are serialized. Active R descendants are stopped with
  Windows process-tree termination and a direct-termination fallback.
- The Workbench application installer does not bundle R, VisionEval, a Docker client
  or image, Datastores, workspaces, or credentials. Runtime installation is a
  separate, explicit current-user action in first-run setup or Settings.

## Known limitations

- The candidate is unsigned. Windows SmartScreen may show an unknown-publisher
  warning; users should verify the published SHA-256 before running it.
- Official VisionEval packages retain semantic version 4.0.0. Workbench therefore
  certifies RC7 from the `VECommit` field rather than the package version alone.
- R 4.5.3 emits `C.UTF-8` locale warnings on this Windows host. Native doctor,
  capability verification, and model execution continue successfully.
- Native execution is intentionally serialized in 2.0. Docker and native parallel
  execution are out of scope.
- Hypercubes are safe on laptops, but larger matrices can consume substantial time,
  memory, and SSD space. Less than 16 GB RAM is advisory limited-resource hardware;
  it does not disable Hypercube creation or execution.

