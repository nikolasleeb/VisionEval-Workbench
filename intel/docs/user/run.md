# Run VisionEval

Run prepares and executes selected baselines and scenarios through the saved native runtime profile.

![Run tab before assets and a runtime have been configured](images/run.png)

## Before running

Run requires a verified `VE_RUNTIME`, compatible `VE_HOME` and `Rscript.exe`, a valid project, and saved scenario changes.

## Queue

Windows runs one job at a time. Selected baselines and scenarios enter a shared queue. Waiting jobs show their queue position and can be reordered; an active job cannot move.

## History and live output

Run History groups the active job first, waiting jobs in queue order, and completed history afterward. Live Output automatically follows the running job whenever the queue advances. You may select another tab to inspect its log; when the next job starts, the console follows that new active job and resumes tail-following.

Each job keeps its own output. Scroll upward to pause follow-tail. Complete output remains in the job's `run.log`.

## Stopping

**Stop Run** ends the selected active R process, releases the runtime slot, and removes partial prepared output. Waiting jobs can be removed without affecting the active process.

If cleanup cannot finish, **cleanup failed** remains with **Retry Cleanup**. The result is not registered until a successful run has produced and verified its datastore.

## Closing Workbench during a run

Choose **Stop Runs and Quit** to end Workbench-owned R processes and clean their partial files, or keep Workbench open. Workbench does not terminate unrelated R processes. Waiting jobs remain queued for the next launch.

## Successful results

After VisionEval exits successfully, Workbench verifies `results/Datastore/DatastoreListing.Rda`. Only then does the result become available in Compare.
