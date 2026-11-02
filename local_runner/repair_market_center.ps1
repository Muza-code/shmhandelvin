param()

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$Base = "https://raw.githubusercontent.com/Muza-code/shmhandelvin/main"
$Files = @(
  "market_collector/build_dashboard_data.py",
  "docs/index.html",
  "docs/market_center.css",
  "templates/market_center.html",
  "static/market_center.css"
)

foreach ($Rel in $Files) {
  $Local = Join-Path $RepoRoot ($Rel -replace "/", "\")
  $Dir = Split-Path -Parent $Local
  if (-not (Test-Path $Dir)) { New-Item -ItemType Directory -Force -Path $Dir | Out-Null }
  Write-Host "Refreshing $Rel ..."
  Invoke-WebRequest -UseBasicParsing -Uri "$Base/$Rel" -OutFile $Local
}

Write-Host ""
Write-Host "Rebuilding Market Center from existing canonical/local data..."
python market_collector\build_dashboard_data.py
if ($LASTEXITCODE -ne 0) { throw "Market Center rebuild failed." }

Copy-Item "data\latest_market.json" "docs\latest_market.json" -Force

$d = Get-Content "data\latest_market.json" -Raw -Encoding UTF8 | ConvertFrom-Json
Write-Host ""
Write-Host ("Listings total: " + $d.stats.listings)
Write-Host ("Semitrailers: " + $d.stats.semitrailers)
Write-Host ("Excluded parts/components: " + $d.stats.parts_components)
Write-Host "Market Center repaired and refreshed."
Write-Host "Open/refresh: http://127.0.0.1:8765/"
