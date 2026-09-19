# Setup

This page is the setup path for VisionEval Workbench 1.1.0 on Intel macOS.

## What you need

- An Intel Mac running macOS 12 or newer.
- VisionEval Workbench 1.1.0.
- Docker Desktop for Intel if you want to run models or read uncached RDA data.
- The separately distributed PlanRVA package, or another VisionEval InputLibrary and complete runnable model folder for your own project.

Explore, Create, workspace management, and already cached comparisons work without Docker. Run requires the verified runtime described below.

## 1. Install VisionEval Workbench

Download `VisionEval-Workbench-v1.1.0-macos-x64.dmg` from the v1.1.0 GitHub release. Open it and drag **VisionEval Workbench.app** to **Applications**.

The v1.1.0 application is ad-hoc signed for bundle integrity but is not Apple-notarized. If macOS says the downloaded application is damaged or cannot be opened, select **Cancel** and run this once in Terminal:

```bash
xattr -dr com.apple.quarantine "/Applications/VisionEval Workbench.app"
open "/Applications/VisionEval Workbench.app"
```

This removes the download quarantine attribute from this local application copy. It does not disable Gatekeeper globally.

## 2. Choose a workspace

On first launch, choose where Workbench should store imported assets, projects, jobs, results, caches, and your notes. The suggested location is:

`~/VisionEval Workbench Workspace`

Use an empty folder or a recognizable existing Workbench workspace. Workbench remembers the location. If it later moves or becomes unavailable, Workbench asks you to locate it rather than silently creating a replacement.

## 3. Install and start Docker Desktop

1. Download and install Docker Desktop for Mac with an Intel chip from the [official Docker installation guide](https://docs.docker.com/desktop/setup/install/mac-install/).
2. Open Workbench. If Docker is stopped, select **Start Docker Desktop** in onboarding, Run, or **Settings → Runtime**.
3. Wait for Docker to report that its engine is running.

Workbench does not run Docker permanently and does not shut down Docker Desktop when Workbench quits. It creates a disposable container only for an actual VisionEval job.

## 4. Install the VisionEval runtime

Workbench installs the pinned runtime image and verifies it for you. The exact commands remain visible under **Runtime Setup → Advanced manual setup** for auditing and troubleshooting.

1. Install Docker Desktop for Mac with an Intel chip.
2. Open Workbench.
3. Select **Install runtime** in first-launch setup or **Settings → Runtime**.
4. Wait while Workbench starts Docker Desktop if needed, pulls the architecture-specific immutable digest, and runs the complete verification.
5. Confirm the screen reports that the runtime is installed, verified, and connected and that Run is available.

The first download can take several minutes. macOS may ask whether Workbench can send notifications the first time it tries to notify you that the runtime is ready. Denying notifications does not prevent the runtime from installing.

Verification automatically runs `doctor`, `verify-upstream-release`, and `verify-household-id-alignment`. **Verify runtime** remains available to repeat those checks later without downloading the image again.

## Advanced: runtime image details

Workbench 1.1.0 reads the approved runtime profile from the release compatibility data and runs the image by immutable platform digest. The preferred image contains official VisionEval `VE-40-RC7` source at commit `7852dc58fad460ff279f5eebf4dd55fe191470ad`, built for AMD64 with R 4.5.1. RC7 includes the official complete-household-ID correction and the Workbench image applies no unofficial VisionEval source patch.

### Recommended method: pull the published GHCR image

Pull the v1 runtime package from GHCR:

```bash
docker pull ghcr.io/nikolasleeb/visioneval-workbench-runtime:VE-40-RC7
```

`VE-40-RC7` and `latest` are multi-platform tags, so Docker selects the host architecture. The runtime index records the immutable AMD64 `@sha256:…` digest; use that digest for auditing. Activate and verify an update through **Settings → Updates → Install Runtime Update** rather than renaming it to an older local alias.

### Fallback method: build the image locally

From the root of the Workbench source folder, run:

```bash
docker build \
  --platform linux/amd64 \
  --build-arg VISIONEVAL_REF=VE-40-RC7 \
  --build-arg VISIONEVAL_COMMIT=7852dc58fad460ff279f5eebf4dd55fe191470ad \
  --tag visioneval-workbench-runtime:VE-40-RC7-amd64 \
  intel/runtime
```

The first build can take a long time because Docker must download the R base image, compile/install VisionEval packages, and build several large layers. Later builds can reuse Docker's cache.

Verify the finished image:

```bash
docker run --rm --platform linux/amd64 \
  visioneval-workbench-runtime:VE-40-RC7-amd64 doctor

docker run --rm --platform linux/amd64 \
  visioneval-workbench-runtime:VE-40-RC7-amd64 verify-upstream-release

docker run --rm --platform linux/amd64 \
  visioneval-workbench-runtime:VE-40-RC7-amd64 verify-household-id-alignment
```

All three commands must succeed. The last command exercises shuffled composite county household IDs and rejects missing, duplicate, unexpected, and non-finite prediction results.

### If someone gives you an approved image archive

Load the archive, then compare the loaded image's platform digest with the signed release runtime index. Do not rename an unknown image to an expected tag merely to bypass verification. Workbench activates only a manifest-approved immutable digest and also checks its embedded release, source commit, architecture, runtime API, and verification commands.

## 5. Install PlanRVA or another model package

The standard application starts without model assets. The optional `planrva-mm.zip` package contains the public **PlanRVA MM** InputLibrary, complete runnable model, and Virginia map context. It contains 52 input files: 51 CSVs plus `model_parameters.json`.

1. Open **Settings → Assets**.
2. Select **Add package** and choose `planrva-mm.zip`.
3. Confirm that **PlanRVA MM** appears under both InputLibraries and model templates.
4. To use an unpackaged model, expand **Advanced imports → Unpackaged assets** and import an InputLibrary and a complete runnable VisionEval folder containing at least:
   - `visioneval.cnf`
   - `scripts/run_model.R`
   - `defs/`
   - `inputs/`
5. Optionally choose defaults for new projects.

Workbench copies imported assets into its workspace and never edits the external source folders.

Install `virginia-mpo-regions.zip` separately to enable Virginia MPO region building. MPO regions are the supported execution scope. Statewide geometry may appear as map context, but a runnable statewide Virginia region is not offered in this release. See [Virginia MPO package](virginia-package.md).

## 6. Confirm the installation

Before relying on the setup:

1. Open **Explore** and confirm the Input File Library and Dependencies view load for the imported template.
2. Create a small project and save a test scenario change.
3. Open **Run**, select only the intended scenario, and start it.
4. Confirm live R output appears and the result is registered only after verification succeeds.
5. Open **Compare** and load the completed datastore.

The RC7 runtime is smoke-tested through the complete PlanRVA model and the numeric and nonnumeric multi-Azone household-ID regressions. A model-specific smoke test remains part of release validation because image verification cannot prove every custom model completes.

## Updating VisionEval later

Do not overwrite the trusted runtime with a floating `latest` image. For a later official VisionEval release:

1. Review the upstream release and resolve its immutable source commit.
2. Update the runtime Dockerfile, Workbench runtime constants, compatibility manifest, workflow tags, documentation, and verification test together.
3. Build a new versioned image tag.
4. Run `doctor`, release verification, automated tests, a representative model, and comparison parity checks.
5. Record and approve the new image digest before making it the Workbench default.

The detailed maintainer procedure is in [Runtime image maintenance](../developer/runtime-image-maintenance.md).
