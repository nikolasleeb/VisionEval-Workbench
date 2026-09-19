# Troubleshooting

If you cannot resolve a problem, open a GitHub Issue at https://github.com/nikolasleeb/VisionEval-Workbench/issues. For run failures, include the diagnostics ZIP from **Settings → Diagnostics** or the failed run card. For app errors, include the visible message, your Workbench version, macOS version, Docker status, and the packages installed in the workspace.

## The app cannot find my workspace

Choose Retry if a removable or network volume is temporarily unavailable. Choose Locate Workspace if the folder moved. Create New starts an empty workspace; it does not recover the old one.

## Docker is not installed or stopped

Install Docker Desktop, select **Start Docker Desktop** in Workbench, and wait for the engine to report Running. Open **Settings → Runtime** and verify again. Explore, Create, and existing comparison data can still be used without Docker.

## Runtime verification fails

Open **Settings → Runtime** and confirm the active digest exists. If necessary, install the approved update or restore the previous verified runtime, then select **Verify runtime**. Review the `doctor`, `verify-upstream-release`, or `verify-household-id-alignment` error before rebuilding the runtime.

## A PlanRVA run stops in `DoPredictions`

This error indicates that the active image failed its complete-ID behavior contract or has a stale runtime profile. Install or restore a manifest-approved runtime and select **Verify runtime**. The accepted image must pass `verify-household-id-alignment`; retagging an unknown image cannot satisfy digest and provenance verification.

## A project does not appear in Run or Compare

The project may be archived. Restore it from **Create → Setup → Archived Projects**. Only verified successful runs appear in Compare. Failed, stopped, or partial results are excluded.

## A scenario change is missing from a run

Apply Preview is temporary. Return to the file and select **Save File Changes** (or press **⌘S**) before Review and Run. Batch changes save immediately after confirmation.

## County filtering is unavailable

The selected output may have only regional/Marea geography, or its registered template may not contain a usable county-to-zone mapping. Choose a compatible table or use its native geography level.

## Changed-output discovery is slow

A cold scan may need to load large datastores. Keep the activity strip open to see its phase and elapsed time. Repeating the same data, roles, year, and geography can use the cache. A memory failure should report Docker resource guidance; do not repeatedly restart the same scan without checking available memory.

## Stop leaves “cleanup failed”

Workbench retains only enough information to finish cleanup. Start Docker if necessary and select **Retry Cleanup**. The result is not registered while cleanup is incomplete.

## Documentation warning

Restart the application to retry installation of the bundled guide. Files in `Documentation/User Notes/` are unaffected. If the warning remains after reinstalling the app, preserve the workspace and report the exact warning message.

## Virginia statewide run fails in `PredictHousing`

The Virginia regional package can build and map all 133 county-equivalent Azones and 5,963 Bzones. A complete statewide VisionEval execution is not release-supported, however. The current statewide inputs can reach `VELandUse::PredictHousing` with a housing allocation group that has too few positive probabilities for the requested integer sample.

This is separate from the repaired transit-input completeness issue. Reinstalling Docker or retrying the same statewide project will not correct it. Use an MPO region for executable scenario work. Keep the statewide build for geography inspection and future data validation until a scientifically defensible statewide housing-allocation rule is implemented and validated.
