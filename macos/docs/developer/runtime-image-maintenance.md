# Runtime image maintenance

The preferred runtime API v1 image is built from official `VisionEval/VisionEval-4` tag `VE-40-RC7` at commit `7852dc58fad460ff279f5eebf4dd55fe191470ad` with R 4.5.1. It carries no unofficial VisionEval source patch. Workbench 2.0.0 also accepts the pinned RC6 profile as a legacy rollback image.

## Updating VisionEval

1. Review the upstream release notes and confirm the release supports the container's R version.
2. Resolve the immutable commit for the new tag: `git ls-remote https://github.com/VisionEval/VisionEval-4.git refs/tags/TAG`.
3. Update the Dockerfile defaults, runtime image constant, verification metadata, compatibility manifest, workflow tags, and user-visible runtime version together.
4. Rebuild with explicit `VISIONEVAL_REF` and `VISIONEVAL_COMMIT` arguments. Never publish a build based only on a floating branch or tag.
5. Run `doctor`, the release-specific upstream verification, automated Workbench tests, a representative PlanRVA baseline, and comparison parity checks.
6. Record the resulting image digest. Publish only after the runtime-publication environment is approved.

Compatibility patches require a reviewed decision, a distinct image tag, an OCI identity label, behavioral verification, and a representative model smoke test. Upstream fixes remain preferred. RC7 incorporates the complete-household-ID correction upstream, so the runtime verifies that official behavior with numeric and nonnumeric multi-Azone regression cases instead of applying a Workbench patch.

The CLI retains the Workbench filesystem-path wrapper: jobs open by absolute `/workspace/models/<job>` path and the process working directory resets to `/` after `startVisionEval()`. This wrapper compatibility behavior does not alter VisionEval source or model inputs.

## Local validation

Use the commands in the user guide's canonical [Setup](../user/setup.md) page. Inspect provenance with:

```bash
docker image inspect visioneval-workbench-runtime:VE-40-RC7-arm64
docker run --rm visioneval-workbench-runtime:VE-40-RC7-arm64 doctor
docker run --rm visioneval-workbench-runtime:VE-40-RC7-arm64 verify-upstream-release
docker run --rm visioneval-workbench-runtime:VE-40-RC7-arm64 verify-household-id-alignment
```

The runtime image is an execution dependency, not a permanent service. Workbench creates disposable containers only for jobs.

## Release freshness checker

The backend reads the GitHub-hosted runtime index through the opt-in update checker. The index declares runtime API, capabilities, platform digests, publication time, and the minimum Workbench version. Network failures retain a valid installed runtime and never disable offline execution.

Runtime installation is always user-approved in **Settings → Updates**. The installer pulls the selected platform digest, verifies architecture, provenance, runtime API, doctor, upstream release, and household alignment, then atomically activates it. A failed candidate leaves the active image unchanged. One previous verified Workbench runtime is retained for rollback.

The runtime index and OCI labels form the compatibility contract. `VE-40-RC7` is the readable multi-platform tag and `latest` is a movable convenience alias; neither is the execution identity. Workbench stores and runs the validated architecture-specific digest.
