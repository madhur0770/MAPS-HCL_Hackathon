# Shared helper: live progress bar with percent and time left (no hidden log files).
$script:StepT0 = Get-Date
function Show-Step {
    param([int]$Index, [int]$Total, [string]$Name)
    $el = ((Get-Date) - $script:StepT0).TotalSeconds
    $left = if ($Index -gt 0) { [int]($el / $Index * ($Total - $Index)) } else { 0 }
    $pct = [int](100 * $Index / $Total)
    Write-Progress -Activity "Ujjwal Rail" -Status ("[{0}/{1}] {2}  (~{3}s left)" -f $Index, $Total, $Name, $left) -PercentComplete $pct
    $bar = ("#" * [int](28 * $Index / $Total)).PadRight(28, ".")
    Write-Host ("[{0}] {1,3}% {2}/{3} ~{4}s left  {5}" -f $bar, $pct, $Index, $Total, $left, $Name) -ForegroundColor Cyan
}
