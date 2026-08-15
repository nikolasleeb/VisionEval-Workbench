# Virginia MPO Region Builder

## Package boundary

Virginia geography and model inputs are distributed as the separate `virginia-mpo-regions` regional package. They are not embedded in the Workbench sidecar. The core Develop UI enumerates installed `region-builder` packages and shows a no-package installation state when the workspace has none.

Build the current package with:

```bash
python packaging/build_va_region_package.py
```

The output is versioned under `dist/packages/virginia-mpo-regions-<version>.zip`. Its `workbench-package.json` inventories every payload file with its size and SHA-256 checksum. Its `SOURCES.md` records all authority links, licensing constraints, methodology, transit compatibility assumptions, and the August 5, 2026 source-check date. The package contains the derived Bzone crosswalk, not copies of the source polygon geometry.

Regional packages use generic metadata for coverage, terminology, region definitions, crosswalk paths, source documents, and package-specific default inputs. This prevents Virginia assumptions from being applied to a future package for another state.

## Source hierarchy

The builder separates authoritative boundary geometry from model values:

1. VDOT `VDOT MPO Study Areas`, item `d1bf64ec02114346aea498b51f1d9594`, supplies the 15 official MPO polygons and stable `MPO_ID` values.
2. `AzonesBzonesVa_WFL1`, item `bfdfaabcb59845fbb6bd51ef392ddbc5`, supplies the statewide Bzone polygons and 12-digit `GEOID` values.
3. The selected Virginia InputLibrary supplies CSV model values. Its Bzone IDs must match the versioned crosswalk exactly.
4. `virginia_mpo_regions.json` maps locality FIPS prefixes to VisionEval Azone names and remains the fallback when the spatial crosswalk is not packaged.
5. The Census Bureau's 2020 Virginia county-equivalent code table supplies the complete 133-row FIPS/name lookup used by statewide feature inspection.

The application never performs a live geometry overlay. At package-build time it reads `docs/developer/reference-data/virginia_mpo_bzone_crosswalk.json`; the installed package carries the versioned result and its provenance.

## Rebuilding the crosswalk

Install Shapely in a maintenance environment, then run:

```bash
python packaging/build_va_mpo_crosswalk.py
```

The command downloads all features in paged GeoJSON requests, requires exactly 15 VDOT MPO features and at least 5,000 Bzones, repairs polygon geometry, computes overlap, and writes the crosswalk. Review every reported boundary overlap before committing a refreshed artifact.

A Bzone is included when at least 1% of its repaired, projected area overlaps an MPO polygon. Ratios from 1% through less than 99% are reported as boundary overlaps; ratios of 99% or greater are substantially inside. Undefined or missing locality FIPS mappings stop the build.

## Runtime behavior

`RegionBuilderService` reads only installed package resources. It prefers the spatial crosswalk and rejects any selected Bzone absent from the package or selected compatible InputLibrary because using mixed vintages could silently corrupt the region. When a package intentionally has no spatial membership for a region, it uses that package's curated locality/FIPS fallback and displays an explicit approximation warning.

The generated `region_builder_manifest.json` records the selection method, source metadata, assignment rule, and boundary cases. Spatially selected Bzones determine which localities are retained as Azones. Existing locality names remain Mareas because the Virginia source inputs contain locality-keyed Marea rows; changing to one MPO Marea requires a separately validated aggregation method.

## Statewide map cache

`GET /api/region-builder/map/statewide?packageId=...` pages through the official ArcGIS object IDs and returns simplified geometry for every MPO, Azone, and Bzone. Features include normalized MPO, Azone, Bzone, and locality identifiers; the response also carries each package region's selected, included-boundary, and excluded-boundary Bzone identifiers. Its local cache fingerprint includes the schema, package version, crosswalk generation date, source modification metadata, and layer URLs. Raw VDOT geometry is not distributed in the package.

The legacy region-specific map endpoint remains available for compatibility. The frontend renders statewide source geometry once, changes SVG group `display` for layer controls, and replaces only focused overlays when the independent map MPO selection changes. Reverse membership indexes support a read-only feature inspector. Optional ID labels are viewport-filtered and collision-reduced rather than rendering all 5,963 Bzone labels.

## Accuracy limits

- Official geometry does not make a complete-Bzone representation identical to the source polygon.
- Area overlap is not population overlap.
- Azone and Marea values may represent an entire locality even when only part lies in the MPO.
- Region and non-spatial inputs are copied, and missing required inputs may use documented defaults.
- VDOT notes that administrative updates can lag boundary decisions, so source modification dates must remain visible.
