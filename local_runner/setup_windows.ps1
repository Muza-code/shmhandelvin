$ErrorActionPreference = "Stop"

Write-Host "SHM Market Collector - Windows setup"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  Write-Host "Python is not installed. Install Python 3.12+ from python.org and enable Add Python to PATH."
  exit 1
}

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

python -m pip install --upgrade pip
python -m pip install -r market_collector\requirements.txt
python -m playwright install chromium

$TaskName = "SHM Market Collector"
$Script = Join-Path $PSScriptRoot "run_windows.ps1"
$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Script`""
$Morning = New-ScheduledTaskTrigger -Daily -At "06:20"
$Evening = New-ScheduledTaskTrigger -Daily -At "18:20"
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

try {
  Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger @($Morning,$Evening) -Settings $Settings -Description "Collect public European trailer market data for SHM" -Force | Out-Null
  Write-Host "Scheduled task installed: $TaskName"
} catch {
  Write-Host "Could not create scheduled task without elevated rights. Run this script as Administrator, or run run_windows.ps1 manually."
}

Write-Host "Running first collection..."
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Script
