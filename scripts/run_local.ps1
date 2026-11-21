# Start the app (React UI + API on http://localhost:8000):  .\scripts\run_local.ps1
# Add -Streamlit to also start the old Streamlit UI on port 8501.
param([switch]$Streamlit)
$ErrorActionPreference = "Stop"
. "$PSScriptRoot\_progress.ps1"
Set-Location (Split-Path $PSScriptRoot)
$py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { Write-Host "Run .\scripts\setup.ps1 first." -ForegroundColor Red; exit 1 }
if (-not (Test-Path app\static\index.html)) { Write-Host "React build missing (app\static). Run: cd ui-react; npm install; npm run build" -ForegroundColor Red; exit 1 }
# Ollama is used automatically when it is running (language understanding + vector search). Force off with: $env:MOCK_LLM="true"
if (-not $env:MOCK_LLM) {
    try { Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 2 | Out-Null; $env:MOCK_LLM = "false"; Write-Host "Ollama found: model understanding and vector search are ON" -ForegroundColor Green }
    catch { $env:MOCK_LLM = "true"; Write-Host "Ollama not running: rule-based mode (start Ollama and re-run to turn the model + vector search on)" -ForegroundColor Yellow }
}
# free port 8000 if an older copy of the app is still running
Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
$steps = @("Generate data", "Start app")
$i = 0
Show-Step (++$i) $steps.Count $steps[0]; & $py scripts\generate_data.py
Show-Step (++$i) $steps.Count $steps[1]
Write-Host "Open  http://localhost:8000   (API docs: /docs)   Ctrl+C to stop" -ForegroundColor Green
if ($Streamlit) {
    $ui = Start-Process $py -ArgumentList "-m streamlit run ui\streamlit_app.py --server.port 8501" -PassThru -NoNewWindow
}
try { & $py -m uvicorn app.main:app --port 8000 } finally { if ($ui) { Stop-Process -Id $ui.Id -ErrorAction SilentlyContinue } }
