# One-time setup on Windows (no Docker needed):  .\scripts\setup.ps1
$ErrorActionPreference = "Stop"
. "$PSScriptRoot\_progress.ps1"
Set-Location (Split-Path $PSScriptRoot)
$steps = @("Check Python", "Create virtual environment", "Install packages", "Generate data", "Run all checks")
$i = 0
Show-Step (++$i) $steps.Count $steps[0]
$py = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $py) { Write-Host "Python 3.10+ not found. Install it from python.org and run again." -ForegroundColor Red; exit 1 }
python --version
Show-Step (++$i) $steps.Count $steps[1]
if (-not (Test-Path .venv)) { python -m venv .venv }
Show-Step (++$i) $steps.Count $steps[2]
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
Show-Step (++$i) $steps.Count $steps[3]
& .\.venv\Scripts\python.exe scripts\generate_data.py
Show-Step (++$i) $steps.Count $steps[4]
& .\.venv\Scripts\python.exe scripts\check_all.py
Write-Host "Setup done. Start the app with  .\scripts\run_local.ps1" -ForegroundColor Green
