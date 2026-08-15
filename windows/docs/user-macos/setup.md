# Setup

This page is the Mac-specific setup path for VisionEval Workbench 1.0.0 on Apple Silicon macOS. Windows uses a separate native-runtime guide; Intel Mac is not validated.

## What you need

- An Apple Silicon Mac running macOS 12 or newer.
- VisionEval Workbench 1.0.0.
- Docker Desktop for Apple silicon if you want to run models or read uncached RDA data.
- The separately distributed PlanRVA package, or another VisionEval InputLibrary and complete runnable model folder for your own project.

Explore, Create, workspace management, and already cached comparisons work without Docker. Run requires the verified runtime described below.

## 1. Install VisionEval Workbench

Download `VisionEval-Workbench-v1.0.0-macos-arm64.dmg` from the v1.0.0 GitHub release. Open it and drag **VisionEval Workbench.app** to **Applications**.

Version 2.0.0 test builds are unsigned and not notarized. If macOS says the downloaded application is damaged or cannot be opened, select **Cancel** and run this once in Terminal:

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

1. Download and install [Docker Desktop for Mac with Apple silicon](https://docs.docker.com/desktop/setup/install/mac-install/).
2. Open Workbench. If Docker is stopped, select **Start Docker Desktop** in onboarding, Run, or **Settings → Runtime**.
3. Wait for Docker to report that its engine is running.

Workbench does not run Docker permanently and does not shut down Docker Desktop when Workbench quits. It creates a disposable container only for an actual VisionEval job.

## 4. Install the VisionEval runtime

Workbench can manage the runtime image for you.

1. Install Docker Desktop for Apple Silicon.
2. Open Workbench.
3. Select **Install runtime** on first launch, or later from **Settings → Runtime**.
4. Wait while Workbench starts Docker Desktop if needed, finds the compatible GHCR image, downloads it, tags the local alias, and verifies it.
5. Confirm the Run tab reports the runtime is ready.

The first download can take several minutes. macOS may ask whether Workbench can send notifications the first time it tries to notify you that the runtime is ready. Denying notifications does not prevent the runtime from installing.

Verification automatically runs `doctor`, `verify-upstream-release`, and `verify-alignment-patch`. If the image is rebuilt under the same tag, its digest changes. Run **Verify runtime** again before starting a model.

## Advanced: runtime image details

Workbench 1.0.0 expects this local image name:

`local/visioneval:1.0.0-arm64`

The image starts from the official VisionEval `VE-40-RC6` source at commit `f7ef3389b5626daeba6c86eeda9d172a0f8cccc2`, built for ARM64 with R 4.5.1. It also contains the narrowly scoped, unofficial Workbench patch `2026-08-03-composite-household-id-alignment`. The patch restores predictions to datastore order by matching complete household IDs; it does not use RC6's ambiguous numeric-suffix ordering. The image is not an official VisionEval distribution.

### Recommended method: pull the published GHCR image

Pull the v1 runtime package from GHCR:

```bash
docker pull ghcr.io/nikolasleeb/visioneval-workbench-runtime:1.0.0-arm64
docker tag \
  ghcr.io/nikolasleeb/visioneval-workbench-runtime:1.0.0-arm64 \
  local/visioneval:1.0.0-arm64
```

The GitHub Release records the immutable `@sha256:…` digest. Use that digest instead of the mutable tag when reproducing or auditing a release.

### Fallback method: build the image locally

From the root of the Workbench source folder, run:

```bash
docker build \
  --platform linux/arm64 \
  --build-arg VISIONEVAL_REF=VE-40-RC6 \
  --build-arg VISIONEVAL_COMMIT=f7ef3389b5626daeba6c86eeda9d172a0f8cccc2 \
  --tag local/visioneval:1.0.0-arm64 \
  runtime
```

The first build can take a long time because Docker must download the R base image, compile/install VisionEval packages, and build several large layers. Later builds can reuse Docker's cache.

Verify the finished image:

```bash
docker run --rm --platform linux/arm64 \
  local/visioneval:1.0.0-arm64 doctor

docker run --rm --platform linux/arm64 \
  local/visioneval:1.0.0-arm64 verify-upstream-release

docker run --rm --platform linux/arm64 \
  local/visioneval:1.0.0-arm64 verify-alignment-patch
```

All three commands must succeed. The last command exercises shuffled composite county household IDs and rejects missing, duplicate, unexpected, and non-finite prediction results.

### If someone gives you an approved image archive

Load the archive, then confirm that it created the expected local tag:

```bash
docker load --input visioneval-workbench-runtime-1.0.0-arm64.tar
docker image inspect local/visioneval:1.0.0-arm64
```

Do not rename an unknown image to the expected tag merely to bypass verification. Workbench also checks its embedded release, source commit, architecture, required packages, and digest.

## 5. Install PlanRVA or another model package

The standard application starts without model assets. The optional `planrva-mm-1.0.0.zip` package contains the public **PlanRVA MM** InputLibrary, complete runnable model, and Virginia map context. It contains 52 input files: 51 CSVs plus `model_parameters.json`.

1. Open **Settings → Assets**.
2. Select **Choose ZIP…** and choose `planrva-mm-1.0.0.zip`, or select **Choose extracted folder…** if the package has already been unpacked.
3. Confirm that **PlanRVA MM** appears under both InputLibraries and model templates.
4. To use an unpackaged model, expand **Advanced imports → Unpackaged assets** and import an InputLibrary and a complete runnable VisionEval folder containing at least:
   - `visioneval.cnf`
   - `scripts/run_model.R`
   - `defs/`
   - `inputs/`
5. Optionally choose defaults for new projects.

Workbench copies imported assets into its workspace and never edits the external source folders.

Install `virginia-mpo-regions-1.0.zip` separately to enable Virginia MPO region building. MPO regions are the supported execution scope. Statewide geometry may appear as map context, but a runnable statewide Virginia region is not offered in this release. See [Virginia MPO package](virginia-package.md).

## 6. Confirm the installation

Before relying on the setup:

1. Open **Explore** and confirm the Input File Library and Dependencies view load for the imported template.
2. Create a small project and save a test scenario change.
3. Open **Run**, select only the intended scenario, and start it.
4. Confirm live R output appears and the result is registered only after verification succeeds.
5. Open **Compare** and load the completed datastore.

The patched runtime was smoke-tested through the complete PlanRVA 2024 model year, including the two `VETravelDemandMM` modules that fail with the unpatched RC6 ordering implementation. A model-specific smoke test remains part of release validation because image verification cannot prove every custom model completes.

## Updating VisionEval later

Do not overwrite the trusted runtime with a floating `latest` image. For a later official VisionEval release:

1. Review the upstream release and resolve its immutable source commit.
2. Update the runtime Dockerfile, Workbench runtime constants, compatibility manifest, workflow tags, documentation, and verification test together.
3. Build a new versioned image tag.
4. Run `doctor`, release verification, automated tests, a representative model, and comparison parity checks.
5. Record and approve the new image digest before making it the Workbench default.

The detailed maintainer procedure is in [Runtime image maintenance](../developer/runtime-image-maintenance.md).
