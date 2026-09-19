# Runtime image maintenance

The preferred runtime API v1 image is built from official `VisionEval/VisionEval-4` tag `VE-40-RC7` at commit `7852dc58fad460ff279f5eebf4dd55fe191470ad` with R 4.5.1. It carries no unofficial VisionEval source patch. Workbench 1.1.0 also accepts the pinned RC6 profile as a legacy rollback image.

## Updating VisionEval

1. Review the upstream release notes and confirm the release supports the container's R version.
2. Resolve the immutable commit for the new tag: `git ls-remote https://github.com/VisionEval/VisionEval-4.git refs/tags/TAG`.
3. Update the Dockerfile defaults, runtime image constant, verification metadata, compatibility manifest, workflow tags, and user-visible runtime version together.
4. Rebuild with explicit `VISIONEVAL_REF` and `VISIONEVAL_COMMIT` arguments. Never publish a build based only on a floating branch or tag.
5. Run `doctor`, the release-specific upstream verification, automated Workbench tests, a representative PlanRVA baseline, and comparison parity checks.
6. Record the resulting image digest. Publish only after the runtime-publication environment is approved.

Compatibility patches require a reviewed decision, a distinct image tag, an OCI identity label, behavioral verification, and a representative model smoke test. Upstream fixes remain preferred, and the exact repository, tag, commit, and patch identifier must stay visible in `/opt/visioneval/RELEASE` and OCI labels.

RC7 must pass `doctor`, `verify-upstream-release`, `verify-household-id-alignment`, provenance-label validation, and the PlanRVA smoke test before public release.

RC7 incorporates the complete-household-ID correction upstream. The Workbench runtime verifies that official behavior with numeric and nonnumeric multi-Azone regression cases and applies no compatibility patch.

The CLI opens Workbench jobs by their absolute `/workspace/models/<job>` path and resets the process working directory to `/` after `startVisionEval()`. Resolving VisionEval's normalized paths from `/` avoids the invalid `/workspace/workspace/...` path. This wrapper compatibility behavior does not alter VisionEval source or model inputs.

## Local validation

Use the commands in the Intel user guide's canonical [Setup](../user-intel/setup.md) page. Inspect provenance with:

```bash
docker image inspect visioneval-workbench-runtime:VE-40-RC7-amd64
docker run --rm visioneval-workbench-runtime:VE-40-RC7-amd64 doctor
docker run --rm visioneval-workbench-runtime:VE-40-RC7-amd64 verify-upstream-release
docker run --rm visioneval-workbench-runtime:VE-40-RC7-amd64 verify-household-id-alignment
```

The runtime image is an execution dependency, not a permanent service. Workbench creates disposable containers only for jobs.

## Release freshness checker

The backend queries the official public GitHub releases API no more than once every 24 hours and stores the result under `exchange/system/runtime-release-status.json`. It includes release candidates because VisionEval 4 releases use RC tags. Network failures retain a stale cached result when available and never disable a valid runtime.

Users can disable this advisory request in **Settings → Runtime → Check for newer VisionEval releases**. The workspace setting applies immediately; `VISIONEVAL_RELEASE_CHECK_ENABLED=false` remains an administrator-level override. Neither setting disables local image provenance and digest verification.

`CURRENT_RELEASE_TAG`, `CURRENT_RELEASE_COMMIT`, and `COMPATIBILITY_PATCH` in `backend/workbench/runtime.py` form the trusted runtime identity. The Dockerfile must write the same values to the OCI release, revision, and compatibility-patch labels. Update them together, add regression tests, and rebuild the image. The release checker may recommend a newer upstream tag, but it must never mutate the runtime profile or pull an image automatically.
