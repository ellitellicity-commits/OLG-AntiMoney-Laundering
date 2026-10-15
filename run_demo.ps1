# One-command demo start (Windows PowerShell), from the repo root:
#   .\run_demo.ps1            # build data if missing, then start the API
#   .\run_demo.ps1 -Rebuild   # regenerate everything first
param([switch]$Rebuild)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path .venv)) {
    python -m venv .venv
    .\.venv\Scripts\python -m pip install -q -r requirements.txt
}
$py = ".\.venv\Scripts\python"

if ($Rebuild -or -not (Test-Path data\scores\alerts.json) -or -not (Test-Path data\features\player_features.parquet)) {
    & $py -m backend.pipeline.run_all
}
Write-Host "API:       http://127.0.0.1:8000/docs"
Write-Host "Dashboard: open frontend/index.html (or: python -m http.server 5500 --directory frontend)"
& $py -m uvicorn backend.app.main:app --port 8000
