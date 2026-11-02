param()

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$BackupDir = Join-Path $RepoRoot ("quarantine_backup\" + $Stamp)
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null

foreach ($p in @("data\latest_market.json","docs\latest_market.json","out\listings.ndjson","out\access_events.ndjson","out\summary.json")) {
  if (Test-Path $p) {
    Copy-Item $p (Join-Path $BackupDir ((Split-Path $p -Leaf))) -Force
  }
}

Write-Host "Old Market Center snapshot backed up to: $BackupDir"
Write-Host ""
Write-Host "Running a fresh strict collection from all currently enabled local sources..."

$env:SHM_SOURCE_NAMES = ""
try {
  & (Join-Path $PSScriptRoot "run_windows.ps1")
}
finally {
  Remove-Item Env:SHM_SOURCE_NAMES -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "Strict clean rebuild finished."
Write-Host "Old polluted snapshot remains only in quarantine_backup."
