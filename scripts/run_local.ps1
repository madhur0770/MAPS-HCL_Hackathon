# Start API (port 8000) and UI (port 8501) without Docker:  .\scripts\run_local.ps1
$ErrorActionPreference = "Stop"
. "$PSScriptRoot\_progress.ps1"
Set-Location (Split-Path $PSScriptRoot)
$py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { Write-Host "Run .\scripts\setup.ps1 first." -ForegroundColor Red; exit 1 }
$env:MOCK_LLM = if ($env:MOCK_LLM) { $env:MOCK_LLM } else { "true" }
$steps = @("Generate data", "Start API", "Wait for API", "Start UI")
$i = 0
Show-Step (++$i) $steps.Count $steps[0]; & $py scripts\generate_data.py
Show-Step (++$i) $steps.Count $steps[1]
$api = Start-Process $py -ArgumentList "-m uvicorn app.main:app --port 8000" -PassThru -NoNewWindow
Show-Step (++$i) $steps.Count $steps[2]
for ($k = 0; $k -lt 30; $k++) { try { Invoke-RestMethod http://localhost:8000/health | Out-Null; break } catch { Start-Sleep 1 } }
Show-Step (++$i) $steps.Count $steps[3]
Write-Host "API: http://localhost:8000/docs   UI: http://localhost:8501   (Ctrl+C to stop)" -ForegroundColor Green
try { & $py -m streamlit run ui\streamlit_app.py --server.port 8501 } finally { Stop-Process -Id $api.Id -ErrorAction SilentlyContinue }
