param(
    [string]$Workspace = (Join-Path $env:USERPROFILE "VisionEval Workbench Workspace"),
    [int]$Port = 3000,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot
$backend = Join-Path $projectRoot "dist\visioneval-workbench-backend.exe"
$veRuntimeHome = Join-Path $projectRoot ".tools\VisionEval"
$veRscript = Join-Path $projectRoot ".tools\R-4.5.1\bin\Rscript.exe"

if (-not (Test-Path -LiteralPath $backend)) {
    throw "The Windows backend has not been built. Run .\.venv\Scripts\python.exe packaging\build_backend.py first."
}
if (-not (Test-Path -LiteralPath $veRscript) -or -not (Test-Path -LiteralPath (Join-Path $veRuntimeHome "WORKBENCH-RELEASE"))) {
    throw "The native VisionEval runtime is incomplete. See the Windows Installation and Runtime wiki guide."
}

$env:PORT = [string]$Port
$env:VISIONEVAL_WORKSPACE_ROOT = $Workspace
$env:VISIONEVAL_RUNTIME_ADAPTER = "native"
$env:VISIONEVAL_RUNTIME = $veRuntimeHome
$env:VE_RUNTIME = $veRuntimeHome
$env:VISIONEVAL_HOME = $veRuntimeHome
$env:VE_HOME = $veRuntimeHome
$env:RSCRIPT = $veRscript
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
