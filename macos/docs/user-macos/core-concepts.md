# Core Concepts and Glossary

## Assets and projects

**InputLibrary**
A named collection of input CSV files. Workbench copies it during import and uses it as the original source for scenario edits.

**Model template**
A validated, complete VisionEval model. It supplies configuration, module order, definitions, and base inputs. Every project uses one pinned template.

**Project**
A comparison workspace that pins a model template and InputLibrary and contains a baseline, editable scenarios, and run/result references.

**Baseline**
The reference scenario. A fresh baseline uses untouched project inputs. An existing completed baseline can be referenced, but Workbench warns when its provenance cannot be verified against the project.

**Scenario**
A named set of saved file changes and notes. A scenario starts from the project's untouched inputs; only saved file changes are applied when it runs.

## Model execution

**Run / job**
One execution of the baseline or a scenario. Each job has a state, log, runtime provenance, prepared model folder, and result verification.

**Batch**
A group of selected jobs submitted together in queued or parallel mode.

**Runtime profile**
The verified Docker adapter, platform, architecture, image reference/digest, version, and verification date. It is not a permanent container.

## Model data

**Input**
A user-editable CSV field read by an executed module.

**Module**
A VisionEval modeling step executed by the selected template's `run_model.R`.

**Intermediary**
A datastore value produced by one module and consumed by a later module. It may remain stored in the final datastore.

**Stored output**
A value available in completed results. An output may also be an intermediary.

**Dependency path**
A declared route from an input through modules and datastore values to a reachable output. It shows a possible effect, not proof that every input change will alter every output.

**Datastore**
VisionEval's structured results, including `DatastoreListing.Rda`. Successful verified datastores are registered in Compare.

## Geography

**Azone, Bzone, Czone, Marea**
VisionEval geography levels defined by the selected model. Their meaning and relationships come from that template's `defs/geo.csv`.

**County filter**
A convenience mapping from county labels to related Azone and Bzone values. It selects matching rows; it does not aggregate them into a county total.
