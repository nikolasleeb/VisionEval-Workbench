# Assumptions and Interpretation Limits

## Scenario edits

Scenario edits are repeatable CSV transformations. Workbench preserves identifiers, years, geography fields, and module-required data types even when display or calculation rounding settings are active.

## Household, vehicle, and worker rows

Household, vehicle, and worker row IDs are useful for diagnosis, but they are not guaranteed to represent the same real-world entity across scenarios after VisionEval modules create, assign, and relocate records. For those tables, geographic averages and distribution summaries are usually more defensible than treating row-by-row differences as matched-person or matched-household changes.

## Compare

Direct row comparison is strongest for stable geography and summary tables. Changed-output scans and maps use observed datastore differences; they do not prove which input edit caused a change.

## Maps

Virginia map visualization depends on an installed package that provides Virginia Azone/Bzone identifiers and map context. In Virginia, Azones are county-equivalent localities, including independent cities. Future state packages must explicitly define their own county or locality mapping.

## Runtime

The Workbench runtime is an unofficial distribution based on official VisionEval VE-40-RC6 source plus a Workbench compatibility patch for composite household-ID alignment. It is verified before use but is not an official VisionEval release.
