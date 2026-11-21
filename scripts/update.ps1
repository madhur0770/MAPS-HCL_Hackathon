# Brings in the newest code that Claude put in D:\HCL_Hackathon (train_final*.bundle):  .\scripts\update.ps1
# Safe to run any time: your regenerated report files are set aside, nothing else is touched.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot)
$steps = @("Find newest bundle", "Set aside local report files", "Pull new code", "Run all checks")
function Step($i, $name) { $pct = [int](100 * $i / $steps.Count); Write-Progress -Activity "update" -Status "$name ($i/$($steps.Count))" -PercentComplete $pct; Write-Host ("[{0}/{1}] {2}" -f $i, $steps.Count, $name) -ForegroundColor Cyan }
Step 1 $steps[0]
$b = Get-ChildItem (Split-Path (Get-Location)) -Filter "train_final*.bundle" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $b) { Write-Host "No train_final*.bundle found next to the repo folder." -ForegroundColor Red; exit 1 }
Write-Host "Using $($b.Name)"
Step 2 $steps[1]
git stash push -q -m "auto-update" 2>$null
Step 3 $steps[2]
git pull --ff-only $b.FullName
git stash drop -q 2>$null
Step 4 $steps[3]
python scripts\check_all.py
Write-Progress -Activity "update" -Completed
