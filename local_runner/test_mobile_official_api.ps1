param()
$ErrorActionPreference="Stop"
$RepoRoot=Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

foreach ($name in @("MOBILEDE_USERNAME","MOBILEDE_PASSWORD")) {
  if (-not (Get-Item "Env:$name" -ErrorAction SilentlyContinue)) {
    $v=[Environment]::GetEnvironmentVariable($name,"User")
    if ($v) { Set-Item "Env:$name" $v }
  }
}
python market_collector\test_mobile_official_api.py
