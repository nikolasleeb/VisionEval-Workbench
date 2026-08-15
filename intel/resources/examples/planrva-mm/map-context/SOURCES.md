# PlanRVA Virginia Map Context

This component was assembled and checked on **August 5, 2026**.

It supplies statewide Virginia context for PlanRVA comparison maps. The package contains source descriptors, locality identifiers, and the versioned MPO-to-Bzone crosswalk. It does **not** redistribute raw polygon geometry. Workbench downloads geometry from the official services on first use and caches it locally for later offline use.

- VisionEval Azone/Bzone web map: https://www.arcgis.com/apps/mapviewer/index.html?webmap=bf7d33b13f074ae3b8f5f6e278c6dd62
- VisionEval Azone/Bzone feature service: https://services2.arcgis.com/8k2PygHqghVevhzy/arcgis/rest/services/AzonesBzonesVa_WFL1/FeatureServer
- VDOT MPO Study Areas: https://www.virginiaroads.org/datasets/VDOT::vdot-mpo-study-areas/explore
- Virginia county-equivalent identifiers: https://www2.census.gov/geo/docs/reference/codes2020/cou/st51_va_cou2020.txt

The full Virginia geometry is display context only. Comparison aggregation and CSV/Excel exports use only Azone/Bzone identifiers represented by the compared PlanRVA model results.
