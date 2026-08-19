# Changelog

## 1.0.1

- Prevented multiple Windows desktop instances from starting separate backends.
- Added a cross-process lock so one native `VE_Runtime` can never execute two Workbench jobs concurrently.
- Reworked spacing for Numbers, Notifications, and Resources settings.
- Kept onboarding, Settings, About, and other dialogs inside the Windows taskbar-safe area.
- Restored About in Settings and added a working About window to the application menu.
- Restored weekly GitHub checks for newer stable Workbench releases, with an actionable in-app notice and manual checks in About.
- Used Windows' trusted certificates for GitHub update checks, including locally installed network certificates.
- Retained app diagnostic errors for 30 days or 500 entries and added a clear control in Settings.
- Stopped the complete native R process tree on cancellation and retried cleanup when Windows temporarily holds result files open.

## 1.0.0

- First public release of the independently maintained Windows 11 x64 application.
- Connects to an existing native `VE_Runtime`, `VE_HOME`, and compatible R installation.
- Includes the complete Explore, Create, Run, and Compare workflow.
- Includes Windows-specific onboarding, diagnostics, documentation, and installer support.

Known limitations are maintained in [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md).
