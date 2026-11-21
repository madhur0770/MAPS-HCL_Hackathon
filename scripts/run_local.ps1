# Start the app (React UI + API on http://localhost:8000):  .\scripts\run_local.ps1
# Add -Streamlit to also start the old Streamlit UI on port 8501.
param([switch]$Streamlit)
$ErrorActionPreference = "Stop"
. "$PSScriptRoot\_progress.ps1"
Set-Location (Split-Path $PSScriptRoot)
$py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { Write-Host "Run .\scripts\setup.ps1 first." -ForegroundColor Red; exit 1 }
if (-not (Test-Path app\static\index.html)) { Write-Host "React build missing (app\static). Run: cd ui-react; npm install; npm run build" -ForegroundColor Red; exit 1 }
$env:MOCK_LLM = if ($env:MOCK_LLM) { $env:MOCK_LLM } else { "true" }
$steps = @("Generate data", "Start app")
$i = 0
Show-Step (++$i) $steps.Count $steps[0]; & $py scripts\generate_data.py
Show-Step (++$i) $steps.Count $steps[1]
Write-Host "Open  http://localhost:8000   (API docs: /docs)   Ctrl+C to stop" -ForegroundColor Green
if ($Streamlit) {
    $ui = Start-Process $py -ArgumentList "-m streamlit run ui\streamlit_app.py --server.port 8501" -PassThru -NoNewWindow
}
try { & $py -m uvicorn app.main:app --port 8000 } finally { if ($ui) { Stop-Process -Id $ui.Id -ErrorAction SilentlyContinue } }
