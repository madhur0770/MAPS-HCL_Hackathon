# Run every check (data, tests, red-team, evaluation) with a live progress bar:  .\scripts\check_all.ps1
Set-Location (Split-Path $PSScriptRoot)
$py = if (Test-Path .\.venv\Scripts\python.exe) { ".\.venv\Scripts\python.exe" } else { "python" }
& $py scripts\check_all.py
exit $LASTEXITCODE
