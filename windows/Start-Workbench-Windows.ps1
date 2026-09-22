param(
    [string]$Workspace = (Join-Path $env:USERPROFILE "VisionEval Workbench Workspace"),
    [string]$VeRuntime = (Join-Path $env:LOCALAPPDATA "VisionEval\VE_Runtime"),
    [string]$VeHome = (Join-Path $env:USERPROFILE "VE_Home"),
    [string]$Rscript = (Join-Path $env:LOCALAPPDATA "Programs\R\R-4.5.3\bin\Rscript.exe"),
    [int]$Port = 3000,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot
$backend = Join-Path $projectRoot "dist\visioneval-workbench-backend.exe"

if (-not (Test-Path -LiteralPath $backend)) {
    throw "The Windows backend has not been built. Run .\.venv\Scripts\python.exe packaging\build_backend.py first."
}
if (-not (Test-Path -LiteralPath $Rscript) -or -not (Test-Path -LiteralPath (Join-Path $VeHome "ve-lib"))) {
    throw "The native VisionEval runtime is incomplete. Open Workbench setup or see the Windows Installation and Runtime guide."
}

$runtimePath = [IO.Path]::GetFullPath($VeRuntime).TrimEnd('\')
$homePath = [IO.Path]::GetFullPath($VeHome).TrimEnd('\')
if ($runtimePath -eq $homePath -or $runtimePath.StartsWith($homePath + '\', [StringComparison]::OrdinalIgnoreCase) -or $homePath.StartsWith($runtimePath + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw "VE_RUNTIME and VE_HOME must be separate folders; neither can be inside the other."
}

$env:PORT = [string]$Port
$env:VISIONEVAL_WORKSPACE_ROOT = $Workspace
$env:VISIONEVAL_RUNTIME_ADAPTER = "native"
$env:VISIONEVAL_RUNTIME = $runtimePath
$env:VE_RUNTIME = $runtimePath
$env:VISIONEVAL_HOME = $homePath
$env:VE_HOME = $homePath
$env:RSCRIPT = [IO.Path]::GetFullPath($Rscript)
$env:VISIONEVAL_RUNTIME_ENABLED = "false"

$process = Start-Process -FilePath $backend -PassThru -WindowStyle Hidden
try {
    $ready = $false
    for ($attempt = 0; $attempt -lt 120; $attempt++) {
        try {
            Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health" | Out-Null
            $ready = $true
            break
        } catch {
            Start-Sleep -Milliseconds 250
        }
    }
    if (-not $ready) { throw "The Workbench backend did not become ready." }
    if (-not $NoBrowser) { Start-Process "http://127.0.0.1:$Port" }
    Write-Host "VisionEval Workbench is running at http://127.0.0.1:$Port"
    Write-Host "Press Ctrl+C to stop it."
    Wait-Process -Id $process.Id
} finally {
    if (-not $process.HasExited) { Stop-Process -Id $process.Id }
}
