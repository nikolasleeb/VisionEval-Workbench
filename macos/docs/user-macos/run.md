# Run VisionEval

The Run tab prepares and executes selected baselines and scenarios with the saved runtime profile.

![Run tab before assets and a runtime have been configured](images/run.png)

## Before running

Run requires:

- Docker Desktop installed and running.
- A compatible image present at the saved immutable digest.
- Successful runtime doctor, manifest-approved immutable-digest verification, and complete household-ID alignment verification.
- A valid project and saved scenario changes.

## Queued and parallel modes

Before a batch starts, choose:

- **Queued:** runs one selected job at a time.
- **Parallel:** allows up to two selected jobs to use the global runtime slots.

All projects share the same queue. Workbench permits at most two VisionEval runtimes across the entire application, not two per project. New work waits behind already queued work.

Waiting jobs show **Queued #1**, **Queued #2**, and so on. Use the up/down arrow controls to change their order. Active jobs cannot move. Remove from Queue deletes only the selected job that has not started.

## History and live output

Run History groups active jobs first, waiting jobs in queue order, and finished history afterward. Jobs belonging to an active batch have a green outline; a running job has stronger emphasis.

In parallel mode, each job has its own console tab. Output is not mixed. The console follows new output while you are near its bottom; scroll upward to pause follow-tail. Complete output remains in the job's `run.log`.

Removing the waiting job whose tab is selected keeps the batch console open and automatically returns Live Output to an active job from that batch when one exists. It never removes, stops, or changes the running job.

The duration badge shows elapsed time for active work and total duration for completed work.

Failed jobs use plain-language messages in History while Live Output and diagnostics retain the exact technical error. Right-click a failed history card and choose **Retry Run…**, or select it and use **Retry** beside Live Output. Retrying creates a new job and preserves the failed history and log.

For memory-related failures, Workbench shows the current concurrency, Docker Desktop allocation, and optional per-run limit before retrying. **Open Resource Settings** does not queue a run or change any setting. **Retry Anyway** uses the current settings and may fail again if memory pressure has not been addressed.

## Exit code 137 and Docker memory

When Docker reports `OOMKilled`, Workbench identifies the failure as confirmed memory exhaustion. Reduce concurrent runs, increase Docker Desktop's total memory allocation, or review the advanced per-run limit before retrying.

Exit code 137 without an available `OOMKilled` result means the process was forcibly stopped. Memory pressure is the most common cause, but the exact code remains in Live Output because another external kill can produce the same result. Check **Settings → Resources**, then export diagnostics if the failure repeats.

## Stopping

Stop Selected Run is enabled only for the selected active job. When stopped, Workbench:

1. Stops and removes the Docker container.
2. Ends the local runtime process.
3. Deletes the prepared model and partial results.
4. Deletes the job manifest and log.
5. Removes the batch reference and any datastore registration.

The job disappears after cleanup. If cleanup cannot finish, a small **cleanup failed** entry remains with **Retry Cleanup**. The runtime slot stays reserved until cleanup completes.

## Quitting while a run is active

Workbench manages only its own labelled VisionEval job containers. It starts Docker Desktop only when you select **Start Docker Desktop**, never quits Docker Desktop, and never stops unrelated containers. If you close Workbench while a run is active, choose either **Stop Runs and Quit** or keep Workbench open. Quitting completes only after the selected Workbench jobs and partial files are safely cleaned up. Waiting jobs own no containers and remain queued for the next launch.

After an unexpected restart, Workbench reconnects to a still-running container only when its Workbench and job ownership labels match the saved manifest. Unverifiable containers are never stopped or removed automatically.

After a managed container exits, Workbench reads its terminal Docker state and then removes it only after verifying the Workbench and job ownership labels. This lets History distinguish confirmed out-of-memory failures without touching unrelated containers.

## Successful results

After VisionEval exits successfully, Workbench verifies `results/Datastore/DatastoreListing.Rda`. Only then is the result registered in Compare. Registration does not automatically switch tabs or select the result.
