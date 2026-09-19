# Runtime and Global Queue

## Runtime profile

A runtime profile records adapter, platform, architecture, image reference, immutable digest, VisionEval/R version, verification result, and verification time. It is not a connection to a permanent container.

Apple Silicon uses Docker and executes a validated ARM64 immutable digest. Workbench 1.1.0 negotiates runtime API v1, supports the pinned RC6 legacy profile, and prefers official VisionEval `VE-40-RC7`. Verification checks Docker availability, architecture, image digest, OCI provenance, runtime API, `doctor`, upstream release, and complete household-ID alignment. The public package is `ghcr.io/nikolasleeb/visioneval-workbench-runtime`; `latest` exists only as a convenience alias and is never trusted for execution.

Advisory update discovery is separate from runtime verification. Each release attaches a validated `update-manifest.json` that maps a Workbench version and host architecture to one approved immutable runtime digest. A registry tag alone is never evidence of compatibility. The application also checks the official VisionEval and Workbench GitHub release feeds when the user explicitly enables automatic checks or selects **Check Now**. Remote failures must remain non-fatal.

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

Automatic memory mode adds no Workbench container cap. Docker Desktop's allocation is shared by all active containers. An optional advanced per-run cap becomes Docker's `--memory` limit for new jobs only; it reserves no memory, can terminate a run that reaches the limit, and does not affect existing containers. Workbench never changes Docker Desktop settings.

Resource guidance uses the measured MPO/regional planning range of 2.5–3.5 GB per active run. Statewide Virginia runs use a provisional 24–32 GB per-run estimate, explicitly marked “will be updated once tested,” and recommend a single first baseline. Both estimates are advisory.

Managed job containers are not started with Docker's automatic removal flag. After the process exits, Workbench verifies the ownership labels, reads `.State.OOMKilled`, `.State.ExitCode`, and `.State.Error`, records structured failure metadata, and removes the stopped container. Cancellation and restart recovery use the same ownership-checked cleanup path. Short-lived runtime verification and export containers may continue using automatic removal.

Performance work must report measured peak memory and distinguish Python, R, Docker VM, and per-container use. “Uses all memory” is not a meaningful acceptance criterion without those boundaries.
