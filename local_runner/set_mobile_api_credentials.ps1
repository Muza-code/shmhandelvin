param(
  [Parameter(Mandatory=$true)][string]$Username,
  [Parameter(Mandatory=$true)][string]$Password
)

$ErrorActionPreference = "Stop"

[Environment]::SetEnvironmentVariable("MOBILEDE_USERNAME", $Username, "User")
[Environment]::SetEnvironmentVariable("MOBILEDE_PASSWORD", $Password, "User")

$env:MOBILEDE_USERNAME = $Username
$env:MOBILEDE_PASSWORD = $Password

Write-Host "mobile.de API credentials saved for current Windows user."
Write-Host "They will be available to future SHM Market Collector runs."
Write-Host "Testing official mobile.de Search API..."

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
& (Join-Path $PSScriptRoot "run_windows.ps1") -Sources "mobile.de Search API"
