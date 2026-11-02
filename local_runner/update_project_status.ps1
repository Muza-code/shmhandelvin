param(
  [string]$RepoRoot = ""
)

$ErrorActionPreference = "Stop"
if (-not $RepoRoot) { $RepoRoot = Split-Path -Parent $PSScriptRoot }
Set-Location $RepoRoot

$Now = Get-Date -Format "yyyy-MM-dd HH:mm:ss K"
$StatusPath = Join-Path $RepoRoot "PROJECT_STATUS_LOCAL.md"
$DataPath = Join-Path $RepoRoot "data\latest_market.json"

$lines = New-Object System.Collections.Generic.List[string]
$lines.Add("# SHM Market Center - Local Recovery Status")
$lines.Add("")
$lines.Add("Auto-generated on: $Now")
$lines.Add("")
$lines.Add("> This file is generated automatically. In a new ChatGPT conversation, upload this file and say: Continue SHM Market Center from this status file.")
$lines.Add("")
$lines.Add("## Repository")
$lines.Add("")
$lines.Add("- Repository: Muza-code/shmhandelvin")
$lines.Add("- Local root: $RepoRoot")

try {
  $head = (git rev-parse --short HEAD 2>$null)
  if ($head) { $lines.Add("- Local git commit: $head") }
} catch {}

$lines.Add("")
$lines.Add("## Market Center snapshot")
$lines.Add("")

if (Test-Path $DataPath) {
  try {
    $d = Get-Content $DataPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $lines.Add("- Dataset updated_at: $($d.updated_at)")
    $lines.Add("- Listings: $($d.stats.listings)")
    $lines.Add("- Semitrailers: $($d.stats.semitrailers)")
    $lines.Add("- Active / seen this run: $($d.stats.active)")
    $lines.Add("- VIN/ref found: $($d.stats.vin_found)")
    $lines.Add("- Sources: $($d.stats.sources)")

    $lines.Add("")
    $lines.Add("### Coverage")
    $lines.Add("")
    foreach ($c in $d.coverage) {
      $lines.Add("- $($c.source): $($c.state_label) - $($c.note)")
    }

    $lines.Add("")
    $lines.Add("### Priority 2021 segments")
    $lines.Add("")
    foreach ($s in ($d.segments | Where-Object { $_.year -eq 2021 } | Sort-Object brand,body_type)) {
      $lines.Add("- $($s.brand) / $($s.body_type): cards=$($s.cards), priced=$($s.priced), Q1=$($s.q1_ask_eur), median=$($s.median_ask_eur), Q3=$($s.q3_ask_eur), sources=$($s.sources), countries=$($s.countries)")
    }
  } catch {
    $lines.Add("- Could not parse data/latest_market.json: $($_.Exception.Message)")
  }
} else {
  $lines.Add("- data/latest_market.json not found yet.")
}

$lines.Add("")
$lines.Add("## Latest local collector run")
$lines.Add("")
$latest = Get-ChildItem (Join-Path $RepoRoot "local_out") -Directory -ErrorAction SilentlyContinue |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1

if ($latest) {
  $lines.Add("- Folder: $($latest.Name)")
  $summary = Join-Path $latest.FullName "summary.json"
  if (Test-Path $summary) {
    try {
      $s = Get-Content $summary -Raw -Encoding UTF8 | ConvertFrom-Json
      $lines.Add("- Started: $($s.started_at)")
      $lines.Add("- Finished: $($s.finished_at)")
      $lines.Add("- Listings: $($s.listings)")
      $lines.Add("- VIN found: $($s.vin_found)")
      if ($s.by_brand) {
        foreach ($p in $s.by_brand.PSObject.Properties) {
          $lines.Add("- $($p.Name): $($p.Value)")
        }
      }
      $lines.Add("- Access events: $($s.access_events)")
    } catch {
      $lines.Add("- Could not parse latest summary.json.")
    }
  }
} else {
  $lines.Add("- No local runs found.")
}

$lines.Add("")
$lines.Add("## Important project rules")
$lines.Add("")
$lines.Add("- Prefer free/low-cost data sources. Do not buy APIs without explicit approval.")
$lines.Add("- Keep asking prices separate from negotiated/auction/actual SHM prices.")
$lines.Add("- Full VIN only when explicitly visible; partial refs stay separate.")
$lines.Add("- Keep Baujahr separate from first-registration proxy.")
$lines.Add("- Do not mix semi-trailers, trailers and swap bodies.")
$lines.Add("- Do not bypass CAPTCHA or anti-bot protections.")
$lines.Add("- Never store API keys, passwords or private SHM transaction data in this recovery file.")

$lines.Add("")
$lines.Add("## Current implementation")
$lines.Add("")
$lines.Add("- Local Windows collector: working")
$lines.Add("- GitHub Actions collector: working")
$lines.Add("- Market Center dashboard: implemented")
$lines.Add("- ReefAPI/mobile.de: working on free-tier pilot")
$lines.Add("- Local run -> canonical Market Center dataset bridge: implemented, verify end-to-end output")
$lines.Add("")
$lines.Add("## Next priorities")
$lines.Add("")
$lines.Add("1. Verify full local run updates data/latest_market.json.")
$lines.Add("2. Merge latest ReefAPI/OLX observations into canonical analytics.")
$lines.Add("3. Improve seller/location/VAT/year evidence/duplicate handling.")
$lines.Add("4. Produce clean 2021 analytics for Kögel, Krone, Schmitz Cargobull and Schwarzmüller.")
$lines.Add("5. Add private SHM Max Buy/headroom logic without exposing private data.")
$lines.Add("")
$lines.Add("## How to continue in a new ChatGPT chat")
$lines.Add("")
$lines.Add("Upload this file and say:")
$lines.Add("")
$lines.Add('> Continue SHM Market Center from PROJECT_STATUS_LOCAL.md. Inspect Muza-code/shmhandelvin and continue from the current state. Do not rebuild from scratch.')

[System.IO.File]::WriteAllLines($StatusPath, $lines, [System.Text.UTF8Encoding]::new($false))
Write-Host "Recovery status updated: $StatusPath"
