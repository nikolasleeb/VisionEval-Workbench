# Create and Review Scenarios

Create opens on **Setup** and also provides **Develop**, **Editor**, and **Review** subtabs. Explicit workflow actions still take you directly to the relevant subtab.

Opening **Develop** starts preparing installed regional-package map geometry in the background. The status beside **View map** indicates whether geometry is being prepared, ready, cached locally, or needs a retry. A first load uses the package's official geometry services; later loads can use the local cache.

![Create Setup in an empty demonstration workspace](images/create.png)

## Develop a packaged region

Develop creates an InputLibrary and runnable model template from an installed regional data package. The core Workbench app does not include a state package. When none is installed, Develop shows an **Install regional package** action instead of state-specific controls.

1. Install a regional package ZIP supplied for the state or region you need.
2. Choose the package, its source InputLibrary, and a region definition.
3. Review the package's source links, source-check date, and source notes.
4. Review or edit the generated region name, code, and state.
5. Select **Preview region**.
6. Review the selected Azone and Bzone counts, boundary cases, copied/defaulted files, and warnings.
7. Select **Build region assets** only after the preview is acceptable.
8. Continue to Setup and create a project from the generated model template and InputLibrary.

Choose **Use an official MPO boundary** for the package-defined geography, or **Build your own region** to start with an empty selection. Custom geography is selected directly from whole Azones or individual Bzones; checking an Azone selects all of its Bzones, and individual Bzones can then be removed. Map clicks, searchable lists, selection counts, and CSV import remain synchronized. The map provides pan, wheel and button zoom, **Fit selection**, **Virginia**, optional MPO/Azone/Bzone context layers, and independent Azone-name, Azone-ID, and Bzone-ID labels. A CSV may contain an `Azone` column, a `Bzone` column, or both; Azone values may be locality names or five-digit FIPS codes and Bzone values are full GEOIDs.

Custom region assets contain only the selected Bzones. Full Virginia geography is available as map context, but statewide generation is not offered as an executable region.

Custom geography is written to the generated manifest with the final Azone/Bzone lists and the Bzones added or removed relative to the official package selection. **Restore official** resets the draft at any time before previewing.

Each package is independent. Installing a package for another state adds that package's terminology, regions, inputs, crosswalk, and provenance without changing or requiring the Virginia package.

### Virginia MPO package

The separately built **Virginia MPO Regional Data** package contains the statewide Virginia InputLibrary, all 15 MPO definitions, and a versioned spatial crosswalk between official VDOT MPO Study Areas and Virginia VisionEval Bzones. The collapsed **Data sources** section records the official source links and the date those sources were checked without interrupting the region workflow.

A Bzone is included when at least 1% of its repaired, projected area overlaps the MPO. Bzones from 1% through less than 99% overlap are reported as boundary cases in the preview and build manifest; Bzones at 99% or more are substantially inside. If the crosswalk does not match the package InputLibrary, Workbench reports the mismatch instead of mixing source versions.

The generated boundary is accurate to complete Bzones, not an exact clipping of the MPO polygon. Workbench does not split a Bzone that crosses the official boundary. Azone and Marea input rows also remain whole-locality values, and region/non-spatial files are copied unchanged. Treat those inputs and any generated defaults as modeling assumptions requiring review before policy use.

Use **View map** to inspect all Virginia MPO outlines, Azones, and Bzones. Statewide Virginia is map context only; projects must select an MPO. The map's MPO menu is exploratory: choosing an MPO highlights its official study area, selected Bzones, and meaningful boundary overlaps without changing the Region Builder selection. Select any visible MPO, Azone, or Bzone to inspect its identifiers, locality, MPO memberships, current-MPO status, and recorded boundary overlap. **Map labels** is enabled by default and shows collision-reduced MPO names and IDs, locality/Azone names and IDs, and—when space permits—Bzone IDs with their parent locality. Drag to pan, use the wheel or `+`/`-` controls to zoom, select **Fit MPO** to restore the review extent, or select **Virginia** to return to the statewide extent. Azones represent whole Virginia localities and can extend well beyond an MPO study area.

The first statewide map view retrieves simplified geometry from the official ArcGIS services and caches it in the local workspace. Later views use that versioned cache. Previewing and building a region use the packaged crosswalk and remain available offline even when map geometry has not been downloaded.

## Setup

Setup imports assets, creates projects, and manages saved and archived projects. The baseline is part of the project and remains read-only in the Editor.

Removing a project archives it for 30 days. Archived projects, jobs, and results disappear from normal Create, Run, and Compare lists. Restore reactivates it; Delete Now permanently removes eligible data. A project with active or waiting jobs cannot be archived.

## Editor workflow

The sidebar represents the project:

1. **New Scenario** creates an editable scenario container.
2. **New File** opens one input CSV inside that scenario.
3. Repeat New File for other individual inputs.
4. Use **Batch Change** when the same operation should affect several input files.

Duplicating a scenario copies its saved file changes and scenario note.

### Single-file mode

Choose locations, target year, editable columns, an operation, and a value.

- **Apply Preview** changes only the temporary working copy shown in the table.
- **Save File Changes** persists that preview and the file note to the scenario so Review and Run can use it.
- **Revert Preview** returns to the last saved version.
- Undo and Redo affect the current preview.
- Removing a saved file from the sidebar restores the scenario to the original InputLibrary file.

Direct table edits also remain temporary until saved. Workbench prompts before you leave a file, scenario, project, or subtab with unsaved work. **Ctrl+S** saves the current file changes when a dirty file is open.

The table keeps saved scenario differences visible after reopening a file, including files created through Batch Change. Light yellow cells are saved changes from the original InputLibrary baseline. Darker yellow cells with an inset outline are additional unsaved preview changes. Saving converts the darker preview state to the saved-change state; Review remains the complete before/after audit.

### Batch mode

Select one or more files and fields, then use the same geography, year, operation, and value controls. **Apply and Save Batch Changes** persists the changes immediately. Files that cannot represent the selected geography are listed and skipped before you confirm.

Use the scenario note for assumptions that apply to the whole scenario. File notes remain available for file-specific context.

## Geography selection

Location options come from the project's model-template definitions. County selection begins empty; select specific counties or explicitly select all. For PlanRVA, county choices map to county-named Azones and related Bzones.

**All locations** is an explicit unfiltered mode. County mode requires at least one county.

## Review

Review compares each saved scenario file with its original InputLibrary source. It shows changed files, rows and cells, geography, years, before/after values, notes, and validation warnings.

Continue to Run is disabled when required files, schemas, geography, or model configuration are invalid. It opens Run with the reviewed project/scenarios preselected but does not start a job.

Batch Change selections are temporary to the scenario currently open in Scenario Tools. Switching to a different scenario—or creating or duplicating one—starts with no batch files or columns selected. Saved file edits remain on their original scenario; only the unsaved batch selection is reset.
