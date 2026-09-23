# Setup

This page is the setup path for VisionEval Workbench 2.0.0 on Apple Silicon macOS.

## What you need

- An Apple Silicon Mac running macOS 12 or newer.
- VisionEval Workbench 2.0.0.
- Docker Desktop for Apple silicon if you want to run models or read uncached RDA data.
- The separately distributed PlanRVA package, or another VisionEval InputLibrary and complete runnable model folder for your own project.

Explore, Create, workspace management, and already cached comparisons work without Docker. Run requires the verified runtime described below.

## 1. Install VisionEval Workbench

Open `VisionEval-Workbench-v2.0.0-macos-arm64.dmg`, drag **VisionEval Workbench.app** to **Applications**, and open it normally. The release is Developer ID signed with the hardened runtime, notarized by Apple, and stapled so Gatekeeper can validate it without a workaround.

## 2. Choose a workspace

On first launch, choose where Workbench should store imported assets, projects, jobs, results, caches, and your notes. The suggested location is:

`~/VisionEval Workbench Workspace`

Use an empty folder or a recognizable existing Workbench workspace. Workbench remembers the location. If it later moves or becomes unavailable, Workbench asks you to locate it rather than silently creating a replacement.

## 3. Install and start Docker Desktop

1. Download and install [Docker Desktop for Mac with Apple silicon](https://docs.docker.com/desktop/setup/install/mac-install/).
2. Open Workbench. If Docker is stopped, select **Start Docker Desktop** in onboarding, Run, or **Settings → Runtime**.
3. Wait for Docker to report that its engine is running.

Workbench does not run Docker permanently and does not shut down Docker Desktop when Workbench quits. It creates a disposable container only for an actual VisionEval job.

## 4. Install the VisionEval runtime

Workbench installs the pinned runtime image and verifies it for you. The exact commands remain visible under **Runtime Setup → Advanced manual setup** for auditing and troubleshooting.

1. Install Docker Desktop for Apple Silicon.
2. Open Workbench.
3. Select **Install runtime** in first-launch setup or **Settings → Runtime**.
4. Wait while Workbench starts Docker Desktop if needed, pulls the architecture-specific immutable digest, and runs the complete verification.
5. Confirm the screen reports that the runtime is installed, verified, and connected and that Run is available.

The first download can take several minutes. macOS may ask whether Workbench can send notifications the first time it tries to notify you that the runtime is ready. Denying notifications does not prevent the runtime from installing.

Verification automatically runs `doctor`, `verify-upstream-release`, and `verify-household-id-alignment`. **Verify runtime** remains available to repeat those checks later without downloading the image again.

## Advanced: runtime image details

Workbench 2.0.0 reads the approved runtime profile from the signed release compatibility data and runs the image by immutable platform digest. The preferred image contains official VisionEval `VE-40-RC7` source at commit `7852dc58fad460ff279f5eebf4dd55fe191470ad`, built for ARM64 with R 4.5.1. RC7 includes the official complete-household-ID correction and the Workbench image applies no unofficial VisionEval source patch.

### Recommended method: pull the published GHCR image

The readable tag is convenient for inspection:

```bash
docker pull ghcr.io/nikolasleeb/visioneval-workbench-runtime:VE-40-RC7
```

`VE-40-RC7` and `latest` are multi-platform tags, so Docker selects the host architecture. The runtime index records the immutable ARM64 `@sha256:…` digest; use that digest for auditing. Activate and verify an update through **Settings → Updates → Install Runtime Update** rather than renaming it to an older local alias.

### Fallback method: build the image locally

From the root of the Workbench source folder, run:

```bash
docker build \
  --platform linux/arm64 \
  --build-arg VISIONEVAL_REF=VE-40-RC7 \
  --build-arg VISIONEVAL_COMMIT=7852dc58fad460ff279f5eebf4dd55fe191470ad \
  --tag visioneval-workbench-runtime:VE-40-RC7-arm64 \
  macos/runtime
```

The first build can take a long time because Docker must download the R base image, compile/install VisionEval packages, and build several large layers. Later builds can reuse Docker's cache.

Verify the finished image:

```bash
docker run --rm --platform linux/arm64 \
  visioneval-workbench-runtime:VE-40-RC7-arm64 doctor

docker run --rm --platform linux/arm64 \
  visioneval-workbench-runtime:VE-40-RC7-arm64 verify-upstream-release

docker run --rm --platform linux/arm64 \
  visioneval-workbench-runtime:VE-40-RC7-arm64 verify-household-id-alignment
```

All three commands must succeed. The last command exercises shuffled composite county household IDs and rejects missing, duplicate, unexpected, and non-finite prediction results.

### If someone gives you an approved image archive

Load the archive, then confirm that it created the expected local tag:

```bash
docker load --input visioneval-workbench-runtime-VE-40-RC7-arm64.tar
docker image inspect visioneval-workbench-runtime:VE-40-RC7-arm64
```

Do not rename an unknown image to the expected tag merely to bypass verification. Workbench also checks its embedded release, source commit, architecture, required packages, and digest.

## 5. Install PlanRVA or another model package

The standard application starts without model assets. The optional `planrva-2.2.zip` package contains the public **PlanRVA** InputLibrary, complete runnable model, and Virginia map context. It contains 52 input files: 51 CSVs plus `model_parameters.json`.

1. Open **Settings → Assets**.
2. Select **Install package…** and choose `planrva-2.2.zip`.
3. Confirm that **PlanRVA** appears under both InputLibraries and model templates.
4. Optionally choose the default InputLibrary for new projects. Its paired template is selected automatically.

Workbench installs verified package assets into its workspace and never edits the external package.

The PlanRVA package itself enables Develop for viewing its eight contained localities and 749 Bzones or building a smaller PlanRVA subregion. Install `virginia-mpo-regions.zip` separately to build other Virginia MPOs or custom regions outside PlanRVA. Statewide geometry may appear as map context, but a runnable statewide Virginia region is not offered in this release. See [Virginia MPO package](virginia-package.md).

## 6. Confirm the installation

Before relying on the setup:

1. Open **Explore** and confirm the Input File Library and Dependencies view load for the imported template.
2. Create a small project and save a test scenario change.
3. Open **Run**, select only the intended scenario, and start it.
4. Confirm live R output appears and the result is registered only after verification succeeds.
5. Open **Compare** and load the completed datastore.

The RC7 runtime is smoke-tested through the complete PlanRVA model and the numeric and nonnumeric multi-Azone household-ID regressions. A model-specific smoke test remains part of release validation because image verification cannot prove every custom model completes.

## Updating VisionEval later

Do not overwrite the trusted runtime with a floating `latest` image. Workbench 2.0.0 discovers approved updates through its validated runtime index, asks before downloading, verifies the immutable platform digest, and retains the previous verified image for rollback. For a later official VisionEval release:

1. Review the upstream release and resolve its immutable source commit.
2. Update the runtime Dockerfile, Workbench runtime constants, compatibility manifest, workflow tags, documentation, and verification test together.
3. Build a new versioned image tag.
4. Run `doctor`, release verification, automated tests, a representative model, and comparison parity checks.
5. Record and approve the new image digest before making it the Workbench default.

The detailed maintainer procedure is in [Runtime image maintenance](../developer/runtime-image-maintenance.md).
