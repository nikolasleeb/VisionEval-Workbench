# Contributing

## Development setup

Read the [Developer Handbook](docs/developer/README.md) and [Local Development](docs/developer/local-development.md) before changing code. Platform behavior, workspace migrations, package schemas, runtime identity, and datastore comparison rules are compatibility contracts.

## Changes

- Keep source inputs and registered RDA datastores immutable.
- Add focused tests for behavior changes and migrations.
- Update canonical Intel user documentation in `docs/user-intel/`, then regenerate `UserGuide.md` with `python3 packaging/build_user_guide.py`.
- Record planned behavior in the roadmap rather than documenting it as implemented.
- Do not publish runtime images under existing trusted tags until all verification and model smoke tests pass.

## Required checks

```bash
python3 packaging/update_runtime_publication.py --check
python3 packaging/build_bundled_assets.py --check
python3 packaging/build_user_guide.py --check
python3 packaging/check_documentation.py
python3 -m unittest discover -s tests
node --check public/app.js
cargo test --manifest-path desktop/src-tauri/Cargo.toml
```

Use a draft pull request for test-candidate work. Include the affected workflows, migration impact, test evidence, and any unresolved limitations.
