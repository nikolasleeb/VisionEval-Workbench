# Virginia MPO Package

The Virginia MPO package is optional. It appears in Create → Develop only after `virginia-mpo-regions-1.0.zip` is installed with **Settings → Assets → Choose ZIP…**. An already extracted package can instead be selected with **Choose extracted folder…**.

## What it enables

- Virginia MPO selection in Region Builder.
- A statewide Virginia map viewer for context. This viewer is available only after the package is installed.
- MPO-specific region asset generation.
- Virginia Azone/Bzone map visualization for compatible completed results.

The package does not enable running all of Virginia as one model region in Workbench 1.0.0. MPO regions are the supported execution scope.

## Included data

The package includes:

- a Virginia InputLibrary;
- 15 official VDOT MPO definitions as package region options;
- a reproducible MPO-to-Bzone membership crosswalk;
- all 133 Virginia county-equivalent Azone/locality identifiers;
- all 5,963 packaged Virginia Bzone identifiers;
- the Workbench-compatible model-template scaffold used to build MPO regions;
- `SOURCES.md`, package metadata, and transit compatibility notes.

## Source data

The package was assembled and checked on August 5, 2026 from:

- VisionEval Azone/Bzone map: https://www.arcgis.com/apps/mapviewer/index.html?webmap=bf7d33b13f074ae3b8f5f6e278c6dd62
- VDOT MPO Study Areas: https://www.virginiaroads.org/datasets/VDOT::vdot-mpo-study-areas/explore
- VDOT MPO Listing dated September 1, 2023.
- U.S. Census Bureau 2020 Virginia county-equivalent FIPS table.

The package does not redistribute VDOT raw boundary polygons. Official geometry is downloaded when the map is first opened and then cached locally. Region preview and region building use the package crosswalk and do not require the map or an internet connection.

## Crosswalk rule

A Bzone is selected when its representative point falls inside the MPO polygon or at least 50% of its projected area overlaps. Crossing Bzones with less than 99% overlap are reported as boundary cases for review.

## Transit compatibility assumptions

VisionEval requires complete Van, Bus, and Rail fuel or powertrain groups. The Virginia source library contains some missing groups. Workbench preserves complete source rows and fills missing compatible rows using the versioned `virginia-transit-service-v1` rule:

- Van with no service uses gasoline and conventional powertrain defaults.
- Bus with no service uses diesel and conventional powertrain defaults.
- Rail electric share is derived from monorail/automated-guideway, streetcar/trolleybus, and light/heavy-rail revenue miles.
- Rail conventional share is derived from commuter/hybrid/cable/aerial revenue miles and uses diesel for hydrocarbon fuel.

These are Workbench compatibility assumptions, not official VDOT values.
