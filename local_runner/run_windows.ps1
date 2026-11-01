$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$OutDir = Join-Path $RepoRoot ("local_out\" + $Stamp)
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

python market_collector\collector.py --config market_collector\config.json --out $OutDir

Write-Host "SHM collector finished."
Write-Host ("Output: " + $OutDir)
Write-Host "This local runner does not automatically publish private SHM data."
