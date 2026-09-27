# Regional Packages

VisionEval Workbench 1.0.0 provides two optional, platform-neutral ZIP packages. Install them directly in Workbench without extracting them first.

| Package | Type | Purpose |
|---|---|---|
| `planrva-2.2.zip` | Model bundle | Ready-to-use PlanRVA multimodal model template, matching InputLibrary, and comparison-map context |
| `virginia-mpo-regions.zip` | Region builder | Statewide inputs, official VDOT MPO boundaries joined to VisionEval Bzones, and resources for creating MPO or custom regional assets |

## Install a package

### Current Mac 2.0 packages

The [2.0 release](https://github.com/nikolasleeb/VisionEval-Workbench/releases/tag/v2.0.0) provides **planrva-2.0.zip**, **virginia-mpo-regions-2.0.zip**, and **wppdc-2.0.zip**. The table above describes the earlier package naming.

For Mac 2.0, PlanRVA supplies its paired model and InputLibrary for the PlanRVA region. In **Create → Develop**, Virginia MPO Regional Data supplies its own statewide **Virginia InputLibrary (49 files)** for other MPOs/custom regions. These inputs are inside the regional package even when Settings → Assets does not list them as a separate Input Library. Do not substitute PlanRVA inputs to bypass a missing-zone or locality error.

Preview the region and confirm coverage before building its assets. The [Mac project/scenario walkthrough](https://github.com/nikolasleeb/VisionEval-Workbench/raw/refs/heads/main/docs/tutorials/macOS-v2.0/Mac-2.0-Project-and-Scenario-Walkthrough.pdf) illustrates the current workflow.

1. Download the ZIP from the [latest release](https://github.com/nikolasleeb/VisionEval-Workbench/releases/latest).
2. Keep the ZIP intact; do not unzip it.
3. Open **Settings → Assets**.
4. Select the ZIP and review its package identity, type, and contents.
5. Install it into the current workspace.

> [!NOTE]
> Workbench validates and copies package contents into the current workspace. It does not modify the downloaded ZIP.

## Which package should I use?

- Use **PlanRVA** when you want the prepared PlanRVA model and InputLibrary.
- Use **Virginia MPO Regional Data** when Region Builder should create assets for an official Virginia MPO or a supported custom region.

## Build another regional package

Data maintainers can follow [Building a Regional Package](Building-a-Regional-Package) to prepare, validate, test, and publish a `region-builder` package. The guide uses Virginia as its worked example and documents the Workbench 1.0.0 compatibility limits.

**Related:** [Tutorials and Walkthroughs](Tutorials-and-Walkthroughs) · [Troubleshooting](Troubleshooting)
