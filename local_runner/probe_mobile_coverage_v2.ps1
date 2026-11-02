param()
$ErrorActionPreference="Stop"
$RepoRoot=Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
if (-not $env:REEF_API_KEY) {
  $k=[Environment]::GetEnvironmentVariable("REEF_API_KEY","User")
  if (-not $k) {
    $f=Join-Path $PSScriptRoot "reefapi_key.txt"
    if (Test-Path $f) { $k=(Get-Content $f -Raw).Trim() }
  }
  if ($k) { $env:REEF_API_KEY=$k }
}
if (-not $env:REEF_API_KEY) { throw "REEF_API_KEY not found" }
python market_collector\mobile_coverage_probe_v2.py
