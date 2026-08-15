# Troubleshooting

## A control is hidden behind the Windows taskbar

Maximize or restore Workbench once, then reopen the page or dialog. Workbench recalculates the visual viewport after resize, display scaling, and application zoom changes. If clipping remains, record the display scale, Workbench zoom, and window size.

## The app cannot find my workspace

Choose Retry if the location is temporarily unavailable. Choose **Open existing workspace** if it moved. Creating a workspace starts empty and does not recover the old one.

## Runtime verification fails

Open **Settings → Runtime** and check all three detected paths:

- `VE_RUNTIME` must be the working folder used to launch VisionEval.
- `VE_HOME` must be the compatible VisionEval package library.
- `Rscript.exe` must belong to the matching R installation.

Use advanced overrides only when automatic detection is wrong, then select **Verify runtime** again. The diagnostic details include the failing command and detected package versions.

After a successful path change, select **Refresh Workbench** in the Settings footer so the local backend reconnects with the verified `VE_Runtime`. Refresh is intentionally blocked until all queued and active runs reach a terminal state.

## Refresh Workbench fails

Settings keeps the error visible and does not close. Confirm there are no waiting, preparing, running, exporting, or stopping jobs, then retry. If reconnection still fails, close and reopen Workbench and export a diagnostic bundle from **Settings → Diagnostics**.

## Run does not become available

Confirm the header says **Native VisionEval ready**, all project changes are saved, Review passes, and the selected model template and InputLibrary belong to the same regional package.

## A project does not appear in Run or Compare

Restore it if archived. Only verified successful runs appear in Compare; failed, stopped, and partial results are excluded.

## A scenario change is missing

Apply Preview is temporary. Return to the file and select **Save File Changes** or press **Ctrl+S** before Review and Run.

## Map Visualization opens with empty selectors

This is intentional in a fresh session. Choose two distinct registered results. Compatible tables, variables, years, and geographies load after the pair is valid; geometry loads only after **Generate map**.

## The Virginia button does not move the 3D map

The Virginia action uses packaged statewide Azone bounds independently of whether context layers are visible. Install the current build and regenerate the map if an older build does nothing. **Virginia** preserves pitch and bearing; **Reset view** restores the default project camera.

## 3D geography is unavailable

3D requires WebGL and the bundled offline MapLibre renderer. Restart Workbench after updating the graphics driver. The complete 2D map remains available.

## Export is outside the comparison card

Install the current build. Its responsive header wraps controls within the card and opens the Export menu inward.

## Stop leaves “cleanup failed”

Select **Retry Cleanup** after confirming the Workbench-owned R process has ended. No result is registered while cleanup is incomplete.

## Documentation warning

Restart Workbench to retry the managed guide installation. Files in `Documentation/User Notes/` remain untouched. Preserve the workspace and report the exact warning if it continues.
