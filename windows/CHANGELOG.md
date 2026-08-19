# Changelog

## 1.0.1

- Prevented multiple Windows desktop instances from starting separate backends.
- Added a cross-process lock so one native `VE_Runtime` can never execute two Workbench jobs concurrently.
- Reworked spacing for Numbers, Notifications, and Resources settings.
- Restored the About page in Settings.

## 1.0.0

- First public release of the independently maintained Windows 11 x64 application.
- Connects to an existing native `VE_Runtime`, `VE_HOME`, and compatible R installation.
- Includes the complete Explore, Create, Run, and Compare workflow.
- Includes Windows-specific onboarding, diagnostics, documentation, and installer support.

Known limitations are maintained in [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md).
