# Local Development

## Prerequisites

- Intel Mac running macOS 12 or newer.
- Python 3.11.
- Node.js 20 or newer.
- Rust toolchain compatible with Tauri 2.
- Docker Desktop when exercising Run or Docker-backed RDA reading.
- PyInstaller plus the pinned dependencies in `packaging/requirements-backend.txt` for packaged sidecar builds.

The Intel edition supports the Linux AMD64 Docker adapter on Intel macOS. Windows native and Apple Silicon ARM64 behavior remain in their separately maintained source trees.

## Run from source

Use a disposable workspace so development does not alter real projects:

```bash
cd VisionEval-Workbench/intel
WORKBENCH_DOCUMENTATION_SOURCE=docs/user-intel VISIONEVAL_WORKSPACE_ROOT="$PWD/.development-workspace" python3 backend/main.py
```

Open `http://127.0.0.1:3000`. Source mode resolves user documentation from `docs/user-intel/`; packaged mode resolves it from the PyInstaller resource bundle.

For the desktop wrapper:

```bash
cd desktop
npm install
npm run tauri:dev
```

The Tauri build command first packages the Python sidecar. Build output and caches must not be committed.

## Tests

Run the Python suite from the repository root:

```bash
python3 -m unittest discover -s tests -v
```

Run Rust tests from `desktop/src-tauri`:

```bash
cargo test
```

Documentation checks validate internal links, managed-copy behavior, source-manifest coverage, and private-path exclusions. Runtime and integration tests require Docker; unit tests should remain usable without it.

## Packaging

Install the locked backend dependency before packaging:

```bash
python3 -m pip install -r packaging/requirements-backend.txt
```

`packaging/build-backend.sh` creates the platform-specific sidecar under `desktop/src-tauri/binaries/`. `packaging/workbench-backend.spec` bundles the web UI, R helpers, metadata catalogs, and the canonical user guide. The Tauri configuration produces an AMD64 DMG.

Signing, notarization, public runtime publication, and downloadable assets are intentionally gated. A local successful build is not a releasable artifact until every item in [Testing and release](testing-and-release.md) is complete.

## Troubleshooting development startup

- If the desktop window never leaves startup, run the sidecar directly and inspect its stderr.
- A sidecar must exit when its Tauri parent disappears; `WORKBENCH_PARENT_PID` implements this guard.
- If the port is occupied, the desktop chooses another free loopback port automatically.
- If Docker is unavailable, verify that Explore, Create, and existing Compare data still work. Run should explain why it is disabled.
- Never point a development build at the user's primary workspace while changing migrations or cleanup logic.
