param(
  [int]$Port = 8765
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$Docs = Join-Path $RepoRoot "docs"
if (-not (Test-Path (Join-Path $Docs "index.html"))) {
  throw "Market Center docs/index.html not found."
}

$Url = "http://127.0.0.1:$Port/"

$alreadyListening = $false
try {
  $alreadyListening = [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
} catch {}

if (-not $alreadyListening) {
  Start-Process -FilePath "python" -ArgumentList @(
    "-m","http.server","$Port","--directory","$Docs"
  ) -WindowStyle Hidden
  Start-Sleep -Seconds 2
}

Start-Process $Url
Write-Host "SHM Market Center opened: $Url"
Write-Host "Refresh the browser page after new collector runs to see updated data."
