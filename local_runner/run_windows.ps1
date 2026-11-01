param(
  [string]$Sources = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

# Refresh persisted API credentials into this PowerShell process.
# This matters when a key was saved from another PowerShell process.
if (-not $env:REEF_API_KEY) {
  $savedReefKey = [Environment]::GetEnvironmentVariable("REEF_API_KEY", "User")
  if (-not $savedReefKey) {
    $reefFile = Join-Path $PSScriptRoot "reefapi_key.txt"
    if (Test-Path $reefFile) {
      $savedReefKey = (Get-Content $reefFile -Raw).Trim()
    }
  }
  if ($savedReefKey) { $env:REEF_API_KEY = $savedReefKey }
}
if (-not $env:MOBILEDE_USERNAME) {
  $savedMobileUser = [Environment]::GetEnvironmentVariable("MOBILEDE_USERNAME", "User")
  if ($savedMobileUser) { $env:MOBILEDE_USERNAME = $savedMobileUser }
}
if (-not $env:MOBILEDE_PASSWORD) {
  $savedMobilePass = [Environment]::GetEnvironmentVariable("MOBILEDE_PASSWORD", "User")
  if ($savedMobilePass) { $env:MOBILEDE_PASSWORD = $savedMobilePass }
}

$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$OutDir = Join-Path $RepoRoot ("local_out\" + $Stamp)
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$oldFilter = $env:SHM_SOURCE_NAMES
if ($Sources) { $env:SHM_SOURCE_NAMES = $Sources }
try {
  python market_collector\collector.py --config market_collector\config.json --out $OutDir
}
finally {
  if ($null -eq $oldFilter) { Remove-Item Env:SHM_SOURCE_NAMES -ErrorAction SilentlyContinue }
  else { $env:SHM_SOURCE_NAMES = $oldFilter }
}

Write-Host "SHM collector finished."
Write-Host ("Output: " + $OutDir)
Write-Host "This local runner does not automatically publish private SHM data."
