# Security Policy

## Supported version

Security fixes are evaluated for the current 2.0.0 release candidate. The Windows installer is not Authenticode-signed and should not be treated as a managed enterprise deployment.

## Reporting

Report suspected vulnerabilities privately to the repository owner rather than opening a public issue. Include reproduction steps, affected files or versions, and the potential impact. Do not include workspace data, credentials, Docker tokens, or proprietary model inputs.

## Trust boundaries

- Workbench operates only inside the selected workspace and copies imported assets before editing them.
- Native VisionEval jobs use validated paths and one serialized runtime slot.
- Package manifests and checksums must be validated before installation.
- Official map geometry is fetched from recorded sources and cached locally; package metadata and crosswalks remain versioned.
- Never publish signing keys, GitHub tokens, Docker credentials, private workspaces, model results, or local configuration.

See [Security, compatibility, and migrations](docs/developer/security-compatibility.md) for implementation details.
