param([string]$ToolsDirectory = (Join-Path (Split-Path $PSScriptRoot -Parent) ".tools"))

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path $PSScriptRoot -Parent
$rVersion = "4.5.1"
$releaseTag = "VE-40-RC6"
$releaseCommit = "f7ef3389b5626daeba6c86eeda9d172a0f8cccc2"
$patchId = "2026-08-03-composite-household-id-alignment"
$runtimeArchiveName = "VE-Installer_WinLibrary-R4.5_2026-07-24.zip"
$runtimeArchiveSha256 = "E07EEFA534F859DEA64941EB16929C5C0CC6876541C18D6C86673C3429A4730B"
$rInstaller = Join-Path $ToolsDirectory "R-$rVersion-win.exe"
$rRoot = Join-Path $ToolsDirectory "R-$rVersion"
$rscript = Join-Path $rRoot "bin\Rscript.exe"
$rExecutable = Join-Path $rRoot "bin\R.exe"
$veRuntimeHome = Join-Path $ToolsDirectory "VisionEval"
$veLibrary = Join-Path $veRuntimeHome "ve-lib\4.5"
$sourceRoot = Join-Path $ToolsDirectory "VisionEval-4"
$runtimeArchive = Join-Path $ToolsDirectory $runtimeArchiveName

New-Item -ItemType Directory -Force -Path $ToolsDirectory | Out-Null
if (-not (Test-Path -LiteralPath $rscript)) {
    if (-not (Test-Path -LiteralPath $rInstaller)) {
        Invoke-WebRequest "https://cran.r-project.org/bin/windows/base/old/$rVersion/R-$rVersion-win.exe" -OutFile $rInstaller
    }
    $arguments = "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /DIR=`"$rRoot`""
    $installed = Start-Process $rInstaller -ArgumentList $arguments -Wait -PassThru -WindowStyle Hidden
    if ($installed.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $rscript)) { throw "R $rVersion installation failed." }
}
if (-not (Test-Path -LiteralPath (Join-Path $veLibrary "VEStart"))) {
    if (-not (Test-Path -LiteralPath $runtimeArchive)) {
        Invoke-WebRequest "https://github.com/VisionEval/VisionEval-4/releases/download/$releaseTag/$runtimeArchiveName" -OutFile $runtimeArchive
    }
    if ((Get-FileHash $runtimeArchive -Algorithm SHA256).Hash -ne $runtimeArchiveSha256) { throw "The VisionEval runtime archive checksum does not match." }
    New-Item -ItemType Directory -Force -Path $veLibrary | Out-Null
    tar -xf $runtimeArchive -C $veLibrary
}
if (-not (Test-Path -LiteralPath (Join-Path $sourceRoot ".git"))) {
    git clone --depth 1 --branch $releaseTag https://github.com/VisionEval/VisionEval-4.git $sourceRoot
}
if ((git -C $sourceRoot rev-parse HEAD).Trim() -ne $releaseCommit) { throw "VisionEval source is not the pinned RC6 commit." }

$installedPatch = & $rscript --vanilla -e ".libPaths(c('$($veLibrary.Replace('\','/'))',.libPaths())); value<-packageDescription('VETravelDemandMM')[['VEAlignmentPatch']]; cat(if(is.null(value)) '' else value)" 2>$null
if ($installedPatch -ne $patchId) {
    & $rscript --vanilla (Join-Path $projectRoot "runtime\scripts\apply-planrva-alignment-patch.R") $sourceRoot
    if ($LASTEXITCODE -ne 0) { throw "The PlanRVA compatibility patch could not be applied." }
    New-Item -ItemType Directory -Force -Path (Join-Path $sourceRoot "sources\optional\VETravelDemandMM\data") | Out-Null
    & $rExecutable CMD INSTALL --no-multiarch "--library=$veLibrary" (Join-Path $sourceRoot "sources\optional\VETravelDemandMM")
    if ($LASTEXITCODE -ne 0) { throw "The patched VETravelDemandMM package could not be installed." }
}

@"
repository=https://github.com/VisionEval/VisionEval-4
tag=$releaseTag
commit=$releaseCommit
r_version=$rVersion
distribution=unofficial-workbench-native-runtime
compatibility_patch=$patchId
compatibility_patch_status=unofficial
compatibility_patch_target=VETravelDemandMM::DoPredictions
"@ | Set-Content -Encoding utf8 (Join-Path $veRuntimeHome "WORKBENCH-RELEASE")
Set-Content -Encoding utf8 (Join-Path $veRuntimeHome "VisionEval.R") 'library(VEStart); startVisionEval(ve.home=getwd(), ve.runtime=Sys.getenv("VE_RUNTIME", getwd()), overwrite=FALSE)'
$renvironPath = $veRuntimeHome.Replace('\', '/')
@"
VE_RUNTIME="$renvironPath"
VE_HOME="$renvironPath"
"@ | Set-Content -Encoding utf8 (Join-Path $veRuntimeHome ".Renviron")

[Environment]::SetEnvironmentVariable("VISIONEVAL_RUNTIME_ADAPTER", "native", "User")
[Environment]::SetEnvironmentVariable("VISIONEVAL_RUNTIME", $veRuntimeHome, "User")
[Environment]::SetEnvironmentVariable("VE_RUNTIME", $veRuntimeHome, "User")
[Environment]::SetEnvironmentVariable("VISIONEVAL_HOME", $veRuntimeHome, "User")
[Environment]::SetEnvironmentVariable("VE_HOME", $veRuntimeHome, "User")
[Environment]::SetEnvironmentVariable("RSCRIPT", $rscript, "User")
Write-Host "Native VisionEval $releaseTag is ready at $veRuntimeHome. Restart Workbench to use it."
