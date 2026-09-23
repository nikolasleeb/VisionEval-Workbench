# Windows 2.0 update-message correction for Windows Codex

The current Windows v2.0.0 installer is still a release candidate. Do not publish it yet. Start from the final Windows source commit `ceb3eb82b2a193aa851c24d35c6416f210fb3eab` on `codex/windows-v2.0-port` (or its descendant in the combined release branch).

## Required change

In `windows/backend/workbench/update_checks.py`, `_check_workbench` currently reports a newer Windows release as “available for this Mac.” Change the update-available message to correctly identify Windows. Preserve the existing current/up-to-date message, platform-specific asset selection, release URL, and offline behavior.

Add a focused test in `windows/tests/test_update_checks.py` that creates a Windows/x64 update candidate, checks the Windows wording and selected Windows installer URL, and confirms it never says “Mac.” Keep the existing Mac-specific tests in the macOS tree unchanged.

## Verify and deliver

1. Run the focused update-check test, complete Windows Python tests, frontend/JavaScript checks, and Rust formatting/tests. Record the results.
2. Build and smoke-test a replacement `VisionEval-Workbench-v2.0.0-windows-x64-setup.exe` using the existing native/managed VisionEval runtime approach. Do not add Docker or claim the installer is signed. Confirm the update notice in the installed application.
3. Update the Windows release-candidate SHA-256 manifest and test report. Verify the new installer checksum and size.
4. Commit and push the Windows fix on `codex/windows-v2.0-port`. Do not merge or publish a GitHub release from the Windows computer.
5. Put the replacement installer, updated checksum manifest, report, and a short final-source note in `/Volumes/Nikolas SSD/VDOT/VE Workbench/Sept Update/Windows/release-candidate-v2.0.0-windows/` (or the equivalent drive letter and folder on Windows). Clearly identify which old installer is superseded without deleting unrelated files.
6. Return the new commit SHA, installer SHA-256, exact SSD path, and test results to Mac Codex. The release draft must remain unpublished until Mac Codex uploads the replacement and updates release notes/checksums.

The currently uploaded Windows installer has SHA-256 `6af29f895c8b6eab9446d686af868ba37bbeeb129be3d9f3154af1c29ef158ef`; it will be replaced after this correction. Its lack of Authenticode signing and possible SmartScreen warning must remain disclosed.
