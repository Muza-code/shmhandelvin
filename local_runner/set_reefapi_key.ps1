param(
  [Parameter(Mandatory=$true)][string]$ApiKey
)

$ErrorActionPreference = "Stop"

[Environment]::SetEnvironmentVariable("REEF_API_KEY", $ApiKey, "User")
$env:REEF_API_KEY = $ApiKey
Set-Content -Path (Join-Path $PSScriptRoot "reefapi_key.txt") -Value $ApiKey -NoNewline -Encoding ASCII

Write-Host "REEF_API_KEY saved for current Windows user and local runner."
Write-Host "Testing mobile.de via ReefAPI..."

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
& (Join-Path $PSScriptRoot "run_windows.ps1") -Sources "mobile.de via ReefAPI"
