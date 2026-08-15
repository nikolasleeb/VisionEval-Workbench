# Units, Rounding, and Provenance

## Input metadata

Workbench chooses an input display unit in this order:

1. A year or scale written in the exact CSV column header.
2. The selected model template's `defs/units.csv`.
3. The executing VisionEval module specification.
4. The human-written explanation guide.

The selected label does not erase disagreements. Explore displays a warning when sources conflict or remain ambiguous.

## Outputs and intermediaries

The producing module specification is the effective source because output columns do not have an input-file header. Disagreements with consuming modules remain visible.

Known items requiring review include D1B, OwnCostPerMile, some rate denominators, and road-cost currency fields. Workbench does not guess missing denominators.

## Rounding

Workbench rounds displayed numeric measurements to five decimal places. It does not change the underlying datastore or exported value.

Geo, Azone, Bzone, Czone, Marea, household, vehicle, and worker identifiers are treated as unitless strings. They are not rounded even when they contain only digits.

## Provenance

Projects record template and InputLibrary identities and fingerprints. Runs additionally record the project/scenario, app/runtime versions, image digest, timestamps, exit status, and result verification. Compare shows this provenance beside selectable results.

An external baseline without matching provenance is labeled compatibility unverified. That warning does not necessarily mean the data is wrong; it means Workbench cannot prove that its assets/runtime match the project.
