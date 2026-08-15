# VisionEval unit conflicts for review

Generated July 18, 2026. Input units use this precedence: exact CSV header annotations, the selected model's `defs/units.csv`, the executing module specification, then the explanation guide. Output and intermediary units use the producing module specification. A selected effective label never removes the conflict warning or audit trail.

No manual JSON editing is required. The app applies this policy and keeps the remaining ambiguities here for later review.

| Status | File / output | Field | Competing unit | Effective label | Effective source | Remaining conflict |
|---|---|---|---|---|---|---|
| Unresolved output | Derived Bzone output | `D1B` | Consumers declare `PRSN/SQMI` and `PRSN/SQM` | People per acre (`PRSN/ACRE`) | Producing module | Consumer declarations still disagree. |
| Unresolved output | Derived Vehicle output | `OwnCostPerMile` | Downstream adjustment declares plain `USD` | 2017 USD | Producing module | The formal unit omits the per-vehicle-mile denominator stated by the definition. |
| Resolved by precedence, warning retained | `bzone_unprotected_area.csv` | `UrbanArea` | Module declares `ACRE` | Square miles (`SQMI`) | Selected model `defs/units.csv` | The field-specific module declaration still says acres. |
| Resolved by precedence, warning retained | `bzone_unprotected_area.csv` | `TownArea` | Module declares `ACRE` | Square miles (`SQMI`) | Selected model `defs/units.csv` | The field-specific module declaration still says acres. |
| Resolved by precedence, warning retained | `bzone_unprotected_area.csv` | `RuralArea` | Module declares `ACRE` | Square miles (`SQMI`) | Selected model `defs/units.csv` | The field-specific module declaration still says acres. |
| Partially resolved by precedence | `region_road_cost.csv` | Road and lane-mile cost fields | Generic model definition says `USD` | Header year and `.1e3` scale applied to USD | CSV header, then model definitions | Per-VMT and per-lane-mile denominators are described but not formally encoded in the unit. |

## Review notes

- **D1B:**
- **OwnCostPerMile:**
- **Urban/Town/Rural area:**
- **Road-cost currency fields:**

The machine-readable companion records the effective source and label. Future reviewer decisions can still be added to `reviewerNotes`; disagreements remain visible in the app even when precedence selects a display unit.
