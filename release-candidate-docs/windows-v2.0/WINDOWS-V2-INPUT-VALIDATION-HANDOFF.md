# VisionEval Workbench 2.0 — Windows Input Editing and Validation Addendum

## Purpose

Implement the categorical editing and safe numeric/structured-input behavior that was added and tested on macOS after the original Windows 2.0 handoff was written. This is a required Windows 2.0 parity update.

Use this addendum together with `WINDOWS-V2-CODEX-HANDOFF.md`. All original Windows constraints still apply: use the already-installed native VisionEval runtime, do not introduce Docker, preserve Windows-native process handling and dialogs, keep the candidate unpublished, and do not describe an unsigned installer as signed.

## Source status and reference material

The original checkpoint branch does not contain this post-checkpoint macOS implementation. The SSD handoff includes a companion folder named:

`macos-input-validation-reference`

It contains the exact files from the tested macOS implementation. Treat them as behavioral and algorithmic references only. Do not overwrite the Windows tree with macOS files, and do not replace Windows-native runtime, path, process, dialog, WebView2, PyInstaller, or NSIS code.

Important reference files include:

- `backend/input_validation_rules.json`
- `backend/workbench/explore.py`
- `backend/workbench/workspace.py`
- `backend/workbench/server.py`
- `backend/workbench/hypercube.py`
- `public/app.js`
- `public/index.html`
- `public/styles.css`
- the focused `tests/` files
- `packaging/workbench-backend.spec`

The macOS reference passed 377 Python/frontend/accessibility tests with 7 expected skips, 15 Rust tests, JavaScript syntax checking, Rust formatting, strict nested code-signature verification, ARM64 verification, packaged-backend startup, and a packaged-resource check.

## Required behavior

### 1. Central validation catalog

Add the packaged `input_validation_rules.json` catalog to the Windows backend and include it in the Windows PyInstaller sidecar. The installed application must not depend on a repository checkout to find the catalog.

Expose catalog-derived metadata for every input column:

- `kind`: numeric, categorical, protected, or text;
- `directEditable` and `bulkEditable`;
- permitted operations/editing modes;
- minimum and maximum;
- integer requirement;
- categorical choices;
- linked-group identity, members, rule, target, tolerance, optional status, and remainder label;
- precision;
- concise guidance;
- protection reason.

The backend is authoritative. Frontend controls improve usability but must not be the only validation layer.

### 2. Classification and protection

Protect structural data, including:

- `Geo` and `Year`;
- IDs, codes, lookup keys, and structural row keys;
- `Level` in `other_ops_effectiveness.csv` because it identifies effectiveness rows;
- the explicit lookup/growth-basis columns listed in the catalog.

Do not classify a field merely because its name happens to end in the letters `id`; for example, `Paid` is not an identifier.

Treat a nonprotected field with 2–50 recognized existing values as categorical and bulk-editable. Build its allowed choices from authoritative source inputs, supplemented by baseline/current values. Treat unrecognized free text as read-only unless the catalog explicitly enables it.

### 3. Numeric rules

For newly changed values:

- require finite numeric values;
- require ordinary editable numeric values to be at least zero;
- require people, households, jobs, dwelling units, vehicles, and other true counts to be whole numbers;
- restrict true proportions and deployment fractions to `0–1`, inclusive;
- allow nonnegative ratios such as `RelEmp*`, `HvyTrkPCE`, drivers per person, and vehicles per driver to exceed `1`;
- restrict latitude to `-90` through `90` and longitude to `-180` through `180`;
- allow coordinates through direct editing only, never calculated operations, Batch Change, or Hypercube axes;
- preserve at least six decimal places, or greater existing source precision, for proportions and linked shares.

Reject invalid edits. Never silently clamp, cap, rebalance, or round an invalid value into validity. Preserve an unchanged legacy/source value even if it would violate a newly introduced rule; validation applies when that value is newly changed.

### 4. Categorical editing

Support categorical editing in both the single-file editor and Batch Change.

Single-file behavior:

- display categorical columns alongside numeric columns;
- permit one categorical column per operation;
- use `Set to` only;
- replace the numeric value field with a dropdown of recognized values;
- retain year, geography, and location filtering;
- prevent mixing numeric and categorical columns;
- render eligible categorical table cells as dropdowns for individual direct edits;
- preserve save, revert, undo, redo, and change highlighting.

Batch Change behavior:

- show categorical fields in file column lists;
- permit one categorical field across multiple files only when the field name and valid choices are compatible;
- clear numeric selection when entering categorical mode and vice versa;
- validate the entire batch before writing anything;
- preserve all existing numeric batch operations.

Save categorical operations as structured string-valued `set` operations. Validate submitted values against authoritative choices. Review text should explain the result, for example: `Set CarSvcLevel to Low.`

### 5. Linked-share group editor

Linked proportions must be edited as complete compositions rather than as independent columns. Selecting one member must open all members and use `Set to` only.

Require a total of `1` within `0.000001` for:

- household income-quartile shares;
- light-duty, heavy-truck, and bus road-class DVMT shares;
- transit fuel shares;
- transit powertrain shares;
- car-service powertrain shares;
- commercial-service powertrain shares;
- heavy-truck powertrain shares.

An optional group may remain entirely blank. Reject partially blank groups.

For Urban/Town dwelling-unit proportions, require each value to be in `0–1` and require `Urban + Town <= 1`. Display the remaining rural share, but do not automatically change either selected value.

Apply one explicit complete vector to every row matched by year/location filters. Do not redistribute other shares automatically.

Batch Change may apply only one compatible linked group from one file per operation. Preflight every affected row before saving.

Exclude linked-group members from individual Hypercube axes. Explain that share composition must be edited together. Independent bounded proportions remain valid Hypercube axes when every generated value is within its allowed range.

### 6. Direct editing and errors

Apply backend validation on every overlay save so a direct table edit cannot bypass the rules.

For an invalid direct edit:

- leave the entered value visible for correction;
- highlight the affected cell;
- show a concise, accessible error;
- disable saving until the edit is corrected or reverted;
- keep undo and redo functional.

Return structured backend errors containing enough information to identify:

- filename;
- field;
- row index and row/location identity;
- attempted value;
- rule/range and explanatory message.

The frontend must render structured errors but remain compatible with a plain error message from older code.

### 7. Timeless files

Do not block an operation merely because an input lacks a `Year` column. Display `All rows — no year field`, omit year filtering, and apply the selected location/row scope.

This is required for `other_ops_effectiveness.csv`: `Level` is protected, while its numeric effectiveness columns remain editable.

### 8. Atomic Batch Change

Add one batch-overlay endpoint equivalent to `POST /api/overlays/batch`.

The endpoint must:

1. load authoritative source/current rows for every requested file;
2. validate column metadata, numeric/categorical rules, and linked groups for every item;
3. stage every overlay;
4. commit all staged overlays only after every validation and write succeeds;
5. restore the previous state if validation or any write/rename fails.

No numeric, categorical, or linked-share batch may leave partially updated files.

### 9. Review and saved metadata

Record validation/value type and linked-group values in edit-operation metadata. Review must accurately describe numeric, categorical, and complete share-group changes. Existing projects and legacy numeric operations must continue to load and replay.

### 10. Hypercube validation

Use the same catalog and backend validator in Hypercube preview and generation.

- reject protected, categorical, text, coordinate, and linked-group columns as axes;
- accept independent numeric proportions only when every generated value is within `0–1`;
- apply integer, nonnegative, and other catalog bounds to every generated value;
- validate candidate rows again during generation so a crafted request cannot bypass preview checks;
- never restore the old name-based proportion cap.

## Interface guidance

Show concise field guidance near controls, such as:

- `Proportion · valid range 0–1`
- `Whole-number count · minimum 0`
- `Categorical · choose a recognized value`
- `Linked shares · total must equal 1`
- `Coordinate · direct editing only`

The linked-group editor must show a live total and validation state. Urban/Town groups must also show the calculated remaining rural share. Error and selection states must work in light/dark modes, narrow layouts, keyboard navigation, and screen readers.

## Windows-specific implementation notes

- Port the behavior into the current Windows application rather than copying the macOS tree wholesale.
- Preserve Windows-native paths and file replacement semantics. Atomic overlay commits must tolerate Windows file-locking behavior and produce a clear failure without partial saves.
- Ensure the validation catalog is bundled into the Windows PyInstaller executable and found through the frozen-resource path.
- Do not read validation policy from the VisionEval installation or modify that installation.
- Keep the existing native serialized queue and installed-runtime contract unchanged.
- Package the resulting x64 sidecar and app through the existing Tauri/NSIS pipeline.

## Required tests

At minimum, add and pass tests for:

1. `CarSvcLevel` changes between `High` and `Low` through row editing, year/location filtering, a single-file operation, and Batch Change.
2. Categorical compatibility and incompatibility across multiple files.
3. Protected `Level` in `other_ops_effectiveness.csv`, with its numeric columns editable and no Year filter required.
4. `0`, `1`, negative, above-one, blank, `NA`, fractional, and nonnumeric inputs through direct, single-file, Batch Change, and raw backend requests.
5. Negative/fractional count rejection and valid whole-number counts.
6. Valid ratios above `1`.
7. Every linked group: exact total, tolerance, precision, optional fully blank group, invalid partial blank group, and invalid total.
8. Urban/Town totals below, equal to, and above `1`, including remaining-rural display.
9. Coordinate boundaries and absence from bulk, Batch, and Hypercube controls.
10. Invalid direct-edit highlighting, save disabling, correction, revert, undo, and redo.
11. Batch atomic rollback on validation failure and simulated write/rename failure.
12. Hypercube acceptance of valid independent proportions and rejection of invalid, coordinate, or linked-share axes.
13. Compatibility with existing numeric overlays and projects.
14. Packaged Windows sidecar lookup of `input_validation_rules.json` without a source checkout.

Run the original Windows handoff's complete frontend-contract, accessibility, JavaScript, Python, Rust, native-runtime, packaging, and installed smoke-test gates as well.

## Acceptance checks for manual testing

Use an isolated workspace and verify:

- `bzone_carsvc_availability.csv`: change `CarSvcLevel` using dropdowns and filtered `Set to` operations;
- `other_ops_effectiveness.csv`: confirm `Level` is read-only, no Year selector blocks editing, and numeric effectiveness fields remain editable;
- one ordinary proportion: values `0` and `1` save, while a negative or value above `1` remains visible and cannot be saved;
- one ratio: a valid value above `1` saves;
- one count: a whole number saves and a fractional value does not;
- one linked share group: the live total controls save eligibility and no automatic redistribution occurs;
- one optional linked group: fully blank is valid and partially blank is rejected;
- Urban/Town shares: remaining rural share is displayed and totals above `1` are rejected;
- one coordinate: a boundary-valid direct edit saves, an out-of-range edit is rejected, and the field is absent from bulk/Batch/Hypercube selectors;
- a multi-file Batch Change rolls back fully when any member is invalid;
- Review accurately explains categorical and share-group changes;
- a small Hypercube previews and generates valid independent proportions but refuses linked shares.

## Build and delivery

### Official Workbench website link

Include the official website as a Version 2 parity requirement:

- Add **Help → VisionEval Workbench Website** to the native menu.
- Add a **Learn more online** card under **Settings → Documentation** with the text: “Visit the VisionEval Workbench website for tutorials, walkthroughs, downloads, and additional guidance.”
- Display `https://sites.google.com/view/ve-workbench/home` and provide an **Open Workbench Website** button.
- Route both entry points through one frontend action and open the exact URL with `explorer.exe`; never navigate the application WebView away from Workbench.
- Extend the desktop external-link allowlist for this exact URL only. Reject HTTP, whitespace, lookalike hosts, sibling Google Sites, and modified paths while retaining trusted GitHub release links.
- If Windows cannot open the system browser, show an accessible error that includes the address for manual copying. Do not perform background availability checks or telemetry.
- Test mouse and keyboard activation, accessible names, dark mode, narrow Settings layout, preservation of unsaved state, the exact allowlist, and packaged-installer behavior.

Do not add the link to the main header or replace the native About dialog. Do not update the bundled PDFs solely for this link.

After all tests pass, build a new local x64 Windows test candidate using the installed VisionEval runtime contract. Do not overwrite a previously approved installer until the new candidate passes installed smoke testing.

Return:

- Windows branch and commit SHA;
- automated test totals and manual-smoke results;
- installer path, size, and SHA-256;
- confirmation that the catalog is bundled;
- confirmation that Docker and VisionEval are not bundled;
- confirmation that the installer remains unsigned unless an Authenticode certificate was explicitly supplied;
- every remaining failure, limitation, or behavior difference.

Do not publish, tag, upload, or declare Windows 2.0 complete if any validation path can be bypassed, Batch Change can partially save, the native runtime is unverified, or a core v2 workflow fails.
