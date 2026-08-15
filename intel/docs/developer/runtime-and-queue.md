# Runtime and Global Queue

## Runtime profile

A runtime profile records adapter, platform, architecture, image reference, immutable digest, VisionEval/R version, verification result, and verification time. It is not a connection to a permanent container.

Intel uses Docker and recognizes the model-neutral local alias `local/visioneval:1.0.0-amd64`. The image is built from official VisionEval `VE-40-RC6` at its pinned commit and contains the unofficial Workbench composite household-ID ordering patch for `VETravelDemandMM::DoPredictions`. Verification checks Docker availability, architecture, image presence/digest, `doctor`, upstream release provenance, and the compatibility patch marker. The public package name is `ghcr.io/nikolasleeb/visioneval-workbench-runtime`; no floating `latest` tag is used.

## Dispatcher invariants

- All projects share one FIFO queue.
- No more than two Workbench VisionEval slots may be reserved at once.
- A slot is reserved before preparation and held through execution, export, stopping, and cancellation cleanup.
- Queued batches may run only one member at a time; parallel batches may use both global slots.
- Before container creation, the dispatcher checks active Workbench-labeled containers to guard against submission races.
- Waiting jobs have persisted `queuePosition` and `queueRevision`; reorder requests with stale revisions are rejected.

The UI groups active jobs first, then waiting jobs in canonical queue order, then terminal history newest first. Parallel logs remain independent and are selected with job tabs; output is never interleaved.

## Job lifecycle

`waiting → preparing → running → exporting → succeeded`

Failure may occur during any active phase. Stop introduces `stopping`; the slot is released only after the container, local process, prepared model, partial results, job manifest, log, batch reference, and datastore registration are removed. A failed cleanup retains a minimal `cleanup_failed` record with Retry Cleanup.

Complete logs remain in `run.log`. UI buffers are bounded and follow the tail only while the user is near the bottom.

## Restart recovery

Waiting jobs are reconstructed from manifests and assigned missing positions by creation order. Existing active containers are reattached only when ownership and state can be verified; otherwise stale-container recovery prevents unsafe duplicate execution. Queue mutation and recovery must occur under the same dispatcher lock.

Containers carry both `com.visioneval.workbench=true` and a job-specific ownership label. Stop, cleanup, recovery, and graceful shutdown verify both the manifest identity and labels before issuing Docker removal commands. A name match alone is insufficient.

The desktop close hook first calls the sidecar shutdown contract. With active jobs it leaves the window open until the user confirms cancellation and the sidecar reports cleanup success. A cleanup error cancels application exit and remains actionable in Run. Workbench starts Docker Desktop only after an explicit user action and never quits it; waiting manifests persist and unrelated containers are outside Workbench's authority.

## Resource behavior

Automatic memory mode adds no Workbench container cap. Docker Desktop's global allocation controls available memory. An optional advanced per-container cap is passed to new jobs only. Workbench never changes Docker Desktop settings.

Performance work must report measured peak memory and distinguish Python, R, Docker VM, and per-container use. “Uses all memory” is not a meaningful acceptance criterion without those boundaries.
