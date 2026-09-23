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

Before a Standard batch starts, choose:

- **Queued:** runs one selected job at a time.
- **Parallel:** allows selected jobs to share the runtime slots configured under **Settings → Resources**.

Standard and Hypercube work share one workspace FIFO queue. Only the oldest unfinished batch owns runtime slots; jobs within that batch may use its configured concurrency, but Standard and Hypercube batches never execute simultaneously. Later batches remain grouped behind it and start automatically when the active batch finishes or is stopped. Queued/parallel mode is recorded for each batch rather than imposed on the whole unfinished queue.

Waiting jobs show **Queued #1**, **Queued #2**, and so on. Reordering keeps every batch together. Active jobs cannot move. Remove from Queue deletes only the selected Standard job that has not started.

## History and live output

Run History groups active jobs first, waiting jobs in queue order, and finished history afterward. Standard jobs remain individual cards. Every Hypercube project appears as one compact card showing active slots, current case range, progress counts, and approximate remaining time; its individual cases and logs remain under **5 Hypercube → Run**. Hypercube cases are excluded from Standard Live Output tabs and automatic log following.

Run History has its own bounded scrollbar and a compact toolbar for **Clear history…**, **Hide history**, and **Refresh**. **Clear history…** previews and removes terminal job records and logs across the workspace while preserving projects, registered results, Datastores, and comparison data. It is unavailable while any job is preparing, running, exporting, stopping, or queued, and the backend rechecks this atomically before deletion. Terminal history older than 30 days is removed automatically using the same safe rules.

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

## Quitting while work is active

Workbench manages only its own labelled VisionEval job containers. It starts Docker Desktop only when you select **Start Docker Desktop**, never quits Docker Desktop, and never stops unrelated containers. If model runs, Hypercube work, comparisons, exports, copies, builds, or runtime installation are active, the quit dialog lists them. Choose **Keep Working** or **Stop Work and Quit**. Workbench requests cancellation and quits only after safe cleanup; an operation that cannot stop safely keeps the app open and explains why.

After an unexpected restart, Workbench reconnects to a still-running container only when its Workbench and job ownership labels match the saved manifest. Unverifiable containers are never stopped or removed automatically.

After a managed container exits, Workbench reads its terminal Docker state and then removes it only after verifying the Workbench and job ownership labels. This lets History distinguish confirmed out-of-memory failures without touching unrelated containers.

## Successful results

After VisionEval exits successfully, Workbench verifies `results/Datastore/DatastoreListing.Rda`. Only then is the result registered in Compare. Registration does not automatically switch tabs or select the result.

Each queued job records its result-retention mode. New Hypercube case and baseline runs use **Datastore only**: Workbench keeps the authoritative VisionEval Datastore and skips the large optional `results/output` CSV tree. Standard-project runs use the **Retain full VisionEval CSV exports** preference that was active when the job was queued. Changing the preference does not change an active or waiting job.
