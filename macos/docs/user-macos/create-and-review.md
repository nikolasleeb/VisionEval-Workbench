# Create and Review Scenarios

Create opens on **Setup** and also provides **Develop**, **Editor**, and **Review** subtabs. While Workbench remains open, each of the four main sections remembers its last nested view and scroll position, so returning to Create takes you back to the Editor, Review, or other Create view you were using. This session navigation memory resets to the normal defaults after the application quits. Explicit workflow actions still take you directly to the relevant subtab.

Opening **Develop** starts preparing map geometry from an eligible installed model or regional package in the background. The status beside **View map** indicates whether geometry is being prepared, ready, cached locally, or needs a retry. A first load uses the package's official geometry services; later loads can use the local cache.

![Create Setup in an empty demonstration workspace](images/create.png)

## Develop a packaged region

Develop creates a matched InputLibrary and runnable model template. It can use an installed regional data package, or an eligible model package such as PlanRVA to build a smaller subregion contained within that model. When neither kind is installed, Develop shows an **Install package** action.

1. Install a model or regional package ZIP supplied for the area you need.
2. Choose the Develop source and region or installed-model scope.
3. Review the package's source links, source-check date, and source notes.
4. Review or edit the region name and state abbreviation. Workbench derives the internal VisionEval region code from the name.
5. Select **Preview region**.
6. Review the selected Azone and Bzone counts, boundary cases, copied/defaulted files, and warnings.
7. Select **Build region assets** only after the preview is acceptable.
8. Continue to Setup and create a project from the generated InputLibrary. Its paired template is selected automatically.

With only the PlanRVA model package installed, Develop exposes the eight localities and 749 Bzones actually contained in PlanRVA. You can build a smaller selection from those Bzones, but unrelated Virginia geography is not displayed or selectable. Install the separate Virginia regional package to build other Virginia MPOs or planner-defined regions outside PlanRVA.

The package's official region is the default, not a locked boundary. Select **Customize** under Geography to add or remove whole Azones or individual Bzones before previewing. A CSV may contain an `Azone` column, a `Bzone` column, or both. Azone values may be locality names or five-digit FIPS codes; Bzone values are full GEOIDs. The import replaces the dialog's current draft and is validated against the selected MPO's participating localities.

Virginia statewide geometry remains available as supporting map context where the installed package provides it. Workbench does not offer a full-state Virginia runnable build in this release because the statewide input set has known execution limits in VisionEval.

Custom geography is written to the generated manifest with the final Azone/Bzone lists and the Bzones added or removed relative to the official package selection. **Restore official** resets the draft at any time before previewing.

Each package is independent. Installing a package for another state adds that package's terminology, regions, inputs, crosswalk, and provenance without changing or requiring the Virginia package.

### Virginia MPO package

The separately built **Virginia MPO Regional Data** package contains the statewide Virginia InputLibrary, all 15 MPO definitions, and a versioned spatial crosswalk between official VDOT MPO Study Areas and Virginia VisionEval Bzones. The collapsed **Data sources** section records the official source links and the date those sources were checked without interrupting the region workflow.

A Bzone is included when its representative point is inside the MPO or at least half of its area overlaps. Bzones below 99% overlap are reported as boundary cases in the preview and build manifest. If the crosswalk does not match the package InputLibrary, Workbench reports the mismatch instead of mixing source versions.

The generated boundary is accurate to complete Bzones, not an exact clipping of the MPO polygon. Workbench does not split a Bzone that crosses the official boundary. Azone and Marea input rows also remain whole-locality values, and region/non-spatial files are copied unchanged. Treat those inputs and any generated defaults as modeling assumptions requiring review before policy use.

Use **View map** to inspect all Virginia MPO outlines, Azones, and Bzones. The map's MPO menu is exploratory: choosing an MPO highlights its official study area, selected Bzones, and included or excluded boundary cases without changing the Region Builder selection. Select any visible MPO, Azone, or Bzone to inspect its identifiers, locality, MPO memberships, current-MPO status, and recorded boundary overlap. **Zone ID labels** adds collision-reduced Azone IDs at MPO scale and Bzone IDs at close scale. Drag to pan, use the wheel or `+`/`-` controls to zoom, select **Fit MPO** to restore the review extent, or select **Virginia** to return to the statewide extent. Azones represent whole Virginia localities and can extend well beyond an MPO study area.

The first statewide map view retrieves simplified geometry from the official ArcGIS services and caches it in the local workspace. Later views use that versioned cache. Previewing and building a region use the packaged crosswalk and remain available offline even when map geometry has not been downloaded.

## Setup

Setup imports assets, creates projects, and manages saved and archived projects. The baseline is part of the project and remains read-only in the Editor.

An existing completed baseline is available only after a verified compatible baseline has run successfully with the same Model package and Input Library. Failed, missing, unverified, or incompatible results cannot be selected as a project baseline.

Setup creates Standard scenario projects for ordinary scenarios, Batch Change, and single-file editing. Hypercube projects are created only from **5 Hypercube → Build** and contain one parameter matrix plus its generated cases.

A Hypercube matrix can be replaced only before any generated case has been submitted to Run and before the project has results. After that point, create a new Hypercube project for a revised matrix. Copying the full project preserves its Hypercube type. Copying an individual generated case into a Standard project turns the case into an ordinary standalone scenario.

Saved Work cards expand independently, so several projects can remain open while you compare their scenarios and completed results. Result labels follow the current project and scenario names; the names recorded when a run or copy occurred remain preserved as provenance. **Copy Project** and **Copy Scenarios** create independent copies of every verified completed result that applies to the copied content, including older result versions. Result files are copied into the destination project; run logs and run history are not. Deleting the source therefore cannot break the copy. Workbench estimates the required storage, checks available disk space, and shows cancellable progress before publishing the copy atomically. A project with an unfinished run remains visible but unavailable as a copy destination until every run in that project finishes or is stopped.

After a copy, **Review Runs** opens Run with only copied scenarios that are missing results or whose inputs have changed. Workbench never starts a run as a side effect of copying.

Removing a project archives it for 30 days. Archived projects, jobs, and results disappear from normal Create, Run, and Compare lists. Restore reactivates it; Delete Now permanently removes eligible data. A project with active or waiting jobs cannot be archived.

For a Standard project, the trash button beside a scenario opens a compact summary of the saved files, terminal runs, logs, completed results, and storage that will be removed. Confirming permanently removes that scenario and its project-owned artifacts. Results still referenced by another active or archived project are retained and marked as having a removed source scenario. A scenario with an unfinished run cannot be removed. Generated Hypercube cases cannot be removed individually because doing so would invalidate the matrix.

## Editor workflow

The sidebar represents the project:

1. **New Scenario** creates an editable scenario container and opens Batch Change with clean controls. Scenario names are unique without regard to capitalization, so `Scenario A` and `scenario a` cannot coexist in one project. Its suggested name is the lowest unused `Scenario N` name; duplication and cross-project copies resolve conflicts with the next available copy suffix using the same case-insensitive rule.
2. **New File** opens one input CSV inside that scenario and clears file-dependent controls until a file is selected.
3. Repeat New File for other individual inputs.
4. Use **Batch Change** when the same operation should affect several input files.

**Copy Scenario** makes a same-project copy of its saved file changes, scenario note, and file notes. The copied notes are independent of the source. Batch-only copies reopen in Batch Change, single-file copies reopen the copied file, and mixed copies preserve the current editing mode when possible.

### Single-file mode

Choose locations, target year, editable columns, an operation, and a value.

- **Apply and Save Change** calculates and saves the selected operation in one atomic action.
- If the operation targets cells already adjusted from the untouched baseline, choose **From baseline** to replace the targeted cells using untouched values, **Apply additional operation** to compound from current scenario values, or **Cancel**.
- Direct table-cell edits remain separate; **Save Direct Edits** persists them explicitly.
- **Revert Direct Edits** returns the table to the last saved version.
- Undo and Redo affect unsaved direct table edits.
- Removing a saved file from the sidebar restores the scenario to the original InputLibrary file.

Direct table edits remain temporary until saved. Workbench prompts before you leave a file, scenario, project, or subtab with unsaved work. **⌘S** saves direct edits when a dirty file is open.

The table keeps saved scenario differences visible after reopening a file, including files created through Batch Change. Light yellow cells are saved changes from the original InputLibrary baseline. Darker yellow cells with an inset outline are additional unsaved preview changes. Saving converts the darker preview state to the saved-change state; Review remains the complete before/after audit.

Selections are remembered separately for each scenario and file, including after restarting Workbench. If no working selection has been saved locally, the Editor reconstructs one from recorded saved operations. When prior edits used different operations, amounts, or location scopes, the controls show **Mixed** and require a specific choice before another change can be applied. **Clear selections** clears only these controls; it does not remove saved scenario changes.

### Batch mode

Select one or more files and fields, then use the same geography, year, operation, and value controls. **Apply and Save Batch Changes** persists the changes immediately. Files that cannot represent the selected geography are listed and skipped before you confirm. In **Choose the starting values**, leave **Start this batch from the untouched baseline** off to apply the operation on top of current scenario changes. Turn it on to replace earlier changes only within the selected files, columns, year, and locations using untouched baseline values. Apply controls are disabled while work is in progress so a rapid repeated click cannot submit the same operation twice.

The Notes panel stays at the top of the active workspace and shows only the note relevant to the current mode: the scenario note in Batch Change, or the selected file's note in single-file editing. Both note types save automatically after a short pause or when you leave the field, without saving pending CSV changes.

Compact provenance emblems identify **Batch change**, **Single-file change**, or **Batch and single-file changes** in Editor, Review, and Setup → Saved Work. Hover or move keyboard focus to an emblem for its full label. Existing changes without source metadata are never guessed and show no emblem.

Hypercube projects now live in the primary **5 Hypercube** workflow rather than Create. Use its Build, Review, Run, and Analyze subtabs; see [Hypercube workflow](hypercube.md).

## Geography selection

Location options come from the project's model-template definitions. County selection begins empty; select specific counties or explicitly select all. For PlanRVA, county choices map to county-named Azones and related Bzones.

**All locations** is an explicit unfiltered mode. County mode requires at least one county.

## Review

Review compares each saved scenario file with its original InputLibrary source. It shows changed files, rows and cells, geography, years, before/after values, notes, and validation warnings.

Use **Active project** in the Review toolbar to inspect another project without returning to Setup or Editor. The Editor and Review project selectors share the same active project.

Each scenario also has a deterministic **Automatic summary** generated locally from its saved edit operations and complete before/after differences. It does not use an LLM. Review shows the compact headline directly on the collapsed scenario card; expand the scenario and then **Automatic summary** to see the hierarchical per-file details. When several calculated operations affect one file, Review lists them separately in application order because later operations use the current scenario values. If validated operations explain only part of the saved result, Review follows them with **Other saved changes** derived from the actual differences. Automatic summaries appear only in Review and remain separate from editable scenario and file notes. Each saved file also has a collapsed **Changed-row audit**. Expanding it shows only affected CSV rows and variables; every highlighted cell includes its baseline and saved scenario values.

Continue to Run is disabled when required files, schemas, geography, or model configuration are invalid. It opens Run with the reviewed project/scenarios preselected but does not start Docker.

Batch Change selections are remembered independently for each scenario. Returning to a scenario restores its local working selection or reconstructs the combined selection from its recorded batch operations.
