# Runtime image maintenance

The supported v1 runtime is `local/visioneval:1.0.0-arm64`, built from `VisionEval/VisionEval-4` tag `VE-40-RC6` at commit `f7ef3389b5626daeba6c86eeda9d172a0f8cccc2` with R 4.5.1 and compatibility patch `2026-08-03-composite-household-id-alignment`.

## Updating VisionEval

1. Review the upstream release notes and confirm the release supports the container's R version.
2. Resolve the immutable commit for the new tag: `git ls-remote https://github.com/VisionEval/VisionEval-4.git refs/tags/TAG`.
3. Update the Dockerfile defaults, runtime image constant, verification metadata, compatibility manifest, workflow tags, and user-visible runtime version together.
4. Rebuild with explicit `VISIONEVAL_REF` and `VISIONEVAL_COMMIT` arguments. Never publish a build based only on a floating branch or tag.
5. Run `doctor`, the release-specific upstream verification, automated Workbench tests, a representative PlanRVA baseline, and comparison parity checks.
6. Record the resulting image digest. Publish only after the runtime-publication environment is approved.

Compatibility patches require a reviewed decision, a distinct image tag, an OCI identity label, behavioral verification, and a representative model smoke test. Upstream fixes remain preferred, and the exact repository, tag, commit, and patch identifier must stay visible in `/opt/visioneval/RELEASE` and OCI labels.

RC6 is built with `ve.build(..., check = FALSE)` plus an in-memory build-tool override that prevents VisionEval's builder from forcing a first-time `R CMD check`. RC6 contains module-documentation filenames that differ only by capitalization, which R 4.5's cross-platform package check rejects even though the package installs on Linux. The image must pass `doctor`, `verify-upstream-release`, `verify-alignment-patch`, provenance-label validation, and the PlanRVA smoke test before public release.

The official RC6 `VETravelDemandMM::DoPredictions` implementation extracts digits from composite household IDs. PlanRVA restarts numeric suffixes in each county, so those values are not a unique global order and RC6 reaches its interactive `browser()` fallback. The Workbench patch disables that reorder for the affected household models and applies the previously proven exact full-ID matcher at every prediction output. On 2026-08-03 the patched image completed both affected modules and the entire PlanRVA 2024 model year without the ordering error.

The CLI opens Workbench jobs by their absolute `/workspace/models/<job>` path and resets the process working directory to `/` after `startVisionEval()`. RC6 represents normalized absolute paths as `./workspace/...`; resolving those paths from `/` avoids the invalid `/workspace/workspace/...` path that otherwise prevents model scripts from loading. This is wrapper compatibility behavior and does not alter VisionEval source or model inputs.

## Local validation

Use the commands in the user guide's canonical [Setup](../user/setup.md) page. Inspect provenance with:

```bash
docker image inspect local/visioneval:1.0.0-arm64
docker run --rm local/visioneval:1.0.0-arm64 doctor
docker run --rm local/visioneval:1.0.0-arm64 verify-upstream-release
docker run --rm local/visioneval:1.0.0-arm64 verify-alignment-patch
```

The runtime image is an execution dependency, not a permanent service. Workbench creates disposable containers only for jobs.

## Release freshness checker

The backend queries the official public GitHub releases API no more than once every 24 hours and stores the result under `exchange/system/runtime-release-status.json`. It includes release candidates because VisionEval 4 releases use RC tags. Network failures retain a stale cached result when available and never disable a valid runtime.

Users can disable this advisory request in **Settings → Runtime → Check for newer VisionEval releases**. The workspace setting applies immediately; `VISIONEVAL_RELEASE_CHECK_ENABLED=false` remains an administrator-level override. Neither setting disables local image provenance and digest verification.

`CURRENT_RELEASE_TAG`, `CURRENT_RELEASE_COMMIT`, and `COMPATIBILITY_PATCH` in `backend/workbench/runtime.py` form the trusted runtime identity. The Dockerfile must write the same values to the OCI release, revision, and compatibility-patch labels. Update them together, add regression tests, and rebuild the image. The release checker may recommend a newer upstream tag, but it must never mutate the runtime profile or pull an image automatically.
