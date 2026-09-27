# Mac 2.0 Workspaces and Resources

Read the illustrated [Workspaces and Resources guide](https://github.com/nikolasleeb/VisionEval-Workbench/raw/refs/heads/main/docs/tutorials/macOS-v2.0/Mac-2.0-Workspaces-and-Resources.pdf).

## Docker and parallel runs

In **Settings → Resources**, set batch mode and maximum concurrent VisionEval runs. Concurrency does not reserve memory: containers share Docker Desktop's allocation. Begin with one or two regional runs and leave headroom. The guide's approximate 2.5–3.5 GB per active regional run is planning guidance, not a guaranteed limit. Set total Docker memory in Docker Desktop. An advanced per-run cap is a ceiling, not a reservation.

## Open, move, and back up

- **Open another workspace** selects an existing complete workspace root without copying or removing either workspace. Select the root, not Projects, Results, or the drive itself.
- **Move workspace** copies and verifies the active workspace into a new empty folder, saves its location, then removes the old copy. Keep a separate backup if you want to retain it.
- Finish or cancel active/waiting jobs first. Keep the SSD connected and Workbench open through copying and verification.
- Check **Current workspace** afterward. Quit and reopen with the drive attached, then check projects, assets, and existing Compare or Hypercube analysis. This verifies retained results, not rerunning successful models.
- Back up the entire workspace root including hidden **.workbench** state after jobs and saves finish. Projects alone and case ZIPs are not complete backups.

If verification fails, preserve both copies. Visible destination files do not prove success. Retry into a new empty folder; do not overwrite another workspace or delete files merely to clear an error. For startup failures, report the exact error and source/destination paths. Quit before ejecting the SSD.
