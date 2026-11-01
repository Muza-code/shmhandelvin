param(
  [string]$Sources = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

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
