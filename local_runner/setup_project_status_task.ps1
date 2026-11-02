param(
  [string]$RepoRoot = ""
)

$ErrorActionPreference = "Stop"
if (-not $RepoRoot) { $RepoRoot = Split-Path -Parent $PSScriptRoot }

$Script = Join-Path $RepoRoot "local_runner\update_project_status.ps1"
if (-not (Test-Path $Script)) { throw "Missing $Script" }

$TaskName = "SHM Project Status Hourly"
$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument ('-NoProfile -ExecutionPolicy Bypass -File "' + $Script + '" -RepoRoot "' + $RepoRoot + '"')
$Trigger = New-ScheduledTaskTrigger -Once -At ((Get-Date).AddMinutes(1)) -RepetitionInterval (New-TimeSpan -Hours 1)
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "Updates SHM Market Center recovery status every hour" -Force | Out-Null

& $Script -RepoRoot $RepoRoot

Write-Host "Installed scheduled task: $TaskName"
Write-Host "Status file: $(Join-Path $RepoRoot 'PROJECT_STATUS_LOCAL.md')"
