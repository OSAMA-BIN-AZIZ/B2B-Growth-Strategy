param(
    [string]$RepoDir = (Get-Location).Path,
    [string]$PythonPath = "python",
    [int]$IntervalMinutes = 10,
    [string]$TaskName = "B2B-Retry-Worker"
)

$ActionArgs = "-m app.workers.retry_worker --limit 20 --delay-minutes $IntervalMinutes"
$Action = New-ScheduledTaskAction -Execute $PythonPath -Argument $ActionArgs -WorkingDirectory $RepoDir
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) `
    -RepetitionDuration ([TimeSpan]::MaxValue)

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Description "Run B2B WeChat retry worker" -Force
Write-Host "Scheduled task '$TaskName' created."
