# Regional Packages

Release 1.0.0 includes two optional ZIP packages. They work with both desktop editions.

## PlanRVA MM

`planrva-mm.zip` contains the PlanRVA multimodal model template, matching InputLibrary, and comparison map context. It is intended as a ready-to-use regional model bundle.

## Virginia MPO Regional Data

`virginia-mpo-regions.zip` contains statewide input data, official VDOT MPO boundaries joined to VisionEval Bzones, and the resources used by Region Builder to create MPO or custom regional assets.

## Install a package

1. Download the ZIP from the [latest release](https://github.com/nikolasleeb/VisionEval-Workbench/releases/latest).
2. Do not unzip it.
3. Open **Settings → Assets** in Workbench.
4. Select the ZIP, review the package information, and install it.

Workbench copies validated package contents into the current workspace. It does not change the downloaded ZIP.

## Build a regional package

Data maintainers can follow [Building a Regional Package](Building-a-Regional-Package) to prepare, validate, test, and publish a platform-neutral `region-builder` package. The guide uses the Virginia MPO package as its worked example and explains the Workbench 1.0.0 compatibility limits.
