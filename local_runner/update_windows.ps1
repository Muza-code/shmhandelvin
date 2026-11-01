$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Base = "https://raw.githubusercontent.com/Muza-code/shmhandelvin/main"
$Files = @(
  "market_collector/collector.py",
  "market_collector/config.json",
  "local_runner/run_windows.ps1"
)

$Backup = Join-Path $Root ("local_runner\backup-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
New-Item -ItemType Directory -Force -Path $Backup | Out-Null

foreach ($Rel in $Files) {
  $Local = Join-Path $Root ($Rel -replace "/", "\")
  if (Test-Path $Local) {
    $Dest = Join-Path $Backup ($Rel -replace "/", "_")
    Copy-Item $Local $Dest -Force
  }

  $Url = "$Base/$Rel"
  $Tmp = "$Local.tmp"
  Write-Host "Updating $Rel ..."
  Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile $Tmp
  Move-Item $Tmp $Local -Force
}

Write-Host ""
Write-Host "Update complete."
Write-Host "Backup: $Backup"
Write-Host ""
Write-Host "Starting one test collection..."
& (Join-Path $PSScriptRoot "run_windows.ps1")
