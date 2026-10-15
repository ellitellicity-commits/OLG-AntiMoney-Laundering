# One-command demo (Windows PowerShell): venv -> dependencies -> pipeline -> API + dashboard.
#   .\run_demo.ps1                 full run (about 3 minutes for the pipeline)
#   .\run_demo.ps1 -SkipPipeline   reuse existing data/ outputs
#   .\run_demo.ps1 -Port 8001      serve on another port
# If scripts are blocked: powershell -ExecutionPolicy Bypass -File .\run_demo.ps1
param([switch]$SkipPipeline, [int]$Port = 8000)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "Creating virtual environment in .venv"
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Could not create .venv (is Python on PATH?)" }
}
Write-Host "Installing dependencies"
& $py -m pip install -q -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

if (-not $SkipPipeline) {
    foreach ($step in "generate_data", "build_features", "train_model", "detect", "cross_seed", "validate") {
        Write-Host "`n== $step ==" -ForegroundColor Cyan
        & $py "backend\pipeline\$step.py"
        if ($LASTEXITCODE -ne 0) { throw "$step.py failed" }
    }
}

$url = "http://127.0.0.1:$Port"
Write-Host "`nStarting API on $url (Ctrl+C to stop)" -ForegroundColor Cyan
$server = Start-Process -FilePath $py -ArgumentList "-m", "uvicorn", "backend.app.main:app", "--port", $Port `
    -NoNewWindow -PassThru
try {
    $ready = $false
    for ($i = 0; $i -lt 90 -and -not $ready; $i++) {
        Start-Sleep -Seconds 1
        try { $ready = (Invoke-RestMethod "$url/health").status -eq "ok" } catch { }
        if ($server.HasExited) { throw "The API exited during startup; see the output above." }
    }
    if (-not $ready) { throw "The API did not become ready within 90 seconds." }
    Write-Host "Dashboard: $url/app/    API docs: $url/docs" -ForegroundColor Green
    Start-Process "$url/app/"
    Wait-Process -Id $server.Id
} finally {
    if (-not $server.HasExited) { Stop-Process -Id $server.Id -Force }
}
