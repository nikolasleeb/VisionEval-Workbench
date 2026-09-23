param(
    [string]$VeHome = (Join-Path $env:USERPROFILE "VE_Home"),
    [string]$VeRuntime = (Join-Path $env:LOCALAPPDATA "VisionEval\VE_Runtime"),
    [string]$DownloadDirectory = (Join-Path $env:LOCALAPPDATA "VisionEval\Workbench\downloads")
)

$ErrorActionPreference = "Stop"
$rVersion = "4.5.3"
$releaseTag = "VE-40-RC7"
$releaseCommit = "7852dc58fad460ff279f5eebf4dd55fe191470ad"
$rInstallerName = "R-$rVersion-win.exe"
$rInstallerSha256 = "768AE31BB0B6056DEF5B1A9789A7DC49306BD037D69B0A99CDD90183AA0C1A31"
$runtimeArchiveName = "VE-Installer_WinLibrary-R4.5_2026-09-07.zip"
$runtimeArchiveSha256 = "01A3F58EE5EB0AB40113CC8835CA99AB1D060B89FF9B442B41C35CE93708155D"

function Get-CanonicalPath([string]$Path) {
    $expanded = [IO.Path]::GetFullPath([Environment]::ExpandEnvironmentVariables($Path))
    if (Test-Path -LiteralPath $expanded) { $expanded = (Resolve-Path -LiteralPath $expanded).Path }
    return $expanded.TrimEnd('\')
}

$VeHome = Get-CanonicalPath $VeHome
$VeRuntime = Get-CanonicalPath $VeRuntime
$homePrefix = "$($VeHome.ToLowerInvariant())\"
$runtimePrefix = "$($VeRuntime.ToLowerInvariant())\"
if ($VeHome.Equals($VeRuntime, [StringComparison]::OrdinalIgnoreCase) -or
    $VeHome.ToLowerInvariant().StartsWith($runtimePrefix) -or
    $VeRuntime.ToLowerInvariant().StartsWith($homePrefix)) {
    throw "VE_HOME and VE_RUNTIME must be separate folders; neither can be inside the other."
}

$rRoot = Join-Path $env:LOCALAPPDATA "Programs\R\R-$rVersion"
$rscript = @(
    (Join-Path $rRoot "bin\Rscript.exe"),
    (Join-Path $env:ProgramFiles "R\R-$rVersion\bin\Rscript.exe"),
    (Join-Path $env:ProgramFiles "R\R-$rVersion\bin\x64\Rscript.exe")
) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $rscript) { $rscript = Join-Path $rRoot "bin\Rscript.exe" }
$rInstaller = Join-Path $DownloadDirectory $rInstallerName
$runtimeArchive = Join-Path $DownloadDirectory $runtimeArchiveName
$extractRoot = Join-Path $DownloadDirectory "VE-RC7-extracted"

New-Item -ItemType Directory -Force -Path $DownloadDirectory | Out-Null
$library = $null
$stagedLibrary = $null
$previousLibrary = $null
$activatedLibrary = $false
try {
    if (-not (Test-Path -LiteralPath $rscript)) {
        Invoke-WebRequest "https://cran.r-project.org/bin/windows/base/old/$rVersion/$rInstallerName" -OutFile $rInstaller
        if ((Get-FileHash $rInstaller -Algorithm SHA256).Hash -ne $rInstallerSha256) {
            throw "The R installer checksum does not match the certified manifest."
        }
        $arguments = "/CURRENTUSER /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /DIR=`"$rRoot`""
        $installed = Start-Process $rInstaller -ArgumentList $arguments -Wait -PassThru -WindowStyle Hidden
        if ($installed.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $rscript)) {
            throw "R $rVersion installation failed."
        }
    }

    Invoke-WebRequest "https://github.com/VisionEval/VisionEval-4/releases/download/$releaseTag/$runtimeArchiveName" -OutFile $runtimeArchive
    if ((Get-FileHash $runtimeArchive -Algorithm SHA256).Hash -ne $runtimeArchiveSha256) {
        throw "The VisionEval runtime archive checksum does not match the certified manifest."
    }
    Remove-Item -LiteralPath $extractRoot -Recurse -Force -ErrorAction SilentlyContinue
    Expand-Archive -LiteralPath $runtimeArchive -DestinationPath $extractRoot
    $veStart = Get-ChildItem -LiteralPath $extractRoot -Filter DESCRIPTION -Recurse -File |
        Where-Object { $_.Directory.Name -eq "VEStart" } |
        Select-Object -First 1
    if (-not $veStart) { throw "The VisionEval archive does not contain VEStart." }
    $packageRoot = $veStart.Directory.Parent.FullName
    $libraryParent = Join-Path $VeHome "ve-lib"
    $library = Join-Path $libraryParent "4.5"
    $stagedLibrary = Join-Path $libraryParent (".4.5.installing-" + [guid]::NewGuid().ToString("N"))
    $previousLibrary = Join-Path $libraryParent (".4.5.previous-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Force -Path $libraryParent, $stagedLibrary, $VeRuntime, (Join-Path $VeRuntime "models") | Out-Null
    Copy-Item -Path (Join-Path $packageRoot "*") -Destination $stagedLibrary -Recurse -Force
    if (Test-Path -LiteralPath $library) { Move-Item -LiteralPath $library -Destination $previousLibrary }
    Move-Item -LiteralPath $stagedLibrary -Destination $library
    $activatedLibrary = $true

    $homeUnix = $VeHome.Replace('\', '/')
    $runtimeUnix = $VeRuntime.Replace('\', '/')
    $environment = "VE_HOME=`"$homeUnix`"`nVE_RUNTIME=`"$runtimeUnix`""
    $environment | Set-Content -Encoding utf8 (Join-Path $VeRuntime ".Renviron")
    $environment | Set-Content -Encoding utf8 (Join-Path $VeHome ".Renviron")
    @"
ve.home <- Sys.getenv("VE_HOME")
ve.runtime <- Sys.getenv("VE_RUNTIME")
.libPaths(c(file.path(ve.home, "ve-lib", "4.5"), .libPaths()))
suppressPackageStartupMessages(library(VEStart))
startVisionEval(ve.home=ve.home, ve.runtime=ve.runtime, overwrite=FALSE)
"@ | Set-Content -Encoding utf8 (Join-Path $VeRuntime ".Rprofile")
    "R version $rVersion" | Set-Content -Encoding utf8 (Join-Path $VeRuntime "r.version")
    @"
repository=https://github.com/VisionEval/VisionEval-4
tag=$releaseTag
commit=$releaseCommit
r_version=$rVersion
distribution=official-visioneval-windows-library
compatibility_patch=none
"@ | Set-Content -Encoding utf8 (Join-Path $VeHome "WORKBENCH-RELEASE")
    if (Test-Path -LiteralPath $previousLibrary) { Remove-Item -LiteralPath $previousLibrary -Recurse -Force }
    Write-Host "VisionEval $releaseTag is ready."
    Write-Host "VE_HOME=$VeHome"
    Write-Host "VE_RUNTIME=$VeRuntime"
    Write-Host "Rscript=$rscript"
} catch {
    if ($previousLibrary -and (Test-Path -LiteralPath $previousLibrary)) {
        if ($library -and (Test-Path -LiteralPath $library)) { Remove-Item -LiteralPath $library -Recurse -Force }
        Move-Item -LiteralPath $previousLibrary -Destination $library
    } elseif ($activatedLibrary -and $library -and (Test-Path -LiteralPath $library)) {
        Remove-Item -LiteralPath $library -Recurse -Force
    }
    throw
} finally {
    if ($stagedLibrary -and (Test-Path -LiteralPath $stagedLibrary)) { Remove-Item -LiteralPath $stagedLibrary -Recurse -Force }
    Remove-Item -LiteralPath $rInstaller, $runtimeArchive -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $extractRoot -Recurse -Force -ErrorAction SilentlyContinue
}
