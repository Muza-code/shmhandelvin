# SHM local Windows runner

Some marketplaces block GitHub/datacenter IP addresses even when a real Chromium browser is used. This runner executes the same collector from a normal SHM Windows PC and therefore uses the office/home internet connection.

## One-time setup
1. Clone/download this repository on the Windows PC.
2. Install Python 3.12+ and enable **Add Python to PATH**.
3. Right-click PowerShell and run as Administrator.
4. Run:
   `powershell -ExecutionPolicy Bypass -File .\local_runner\setup_windows.ps1`

The setup installs dependencies + Chromium and creates Windows Task Scheduler runs at 06:20 and 18:20 local time.

## Important
- It does not bypass CAPTCHA, login or access controls.
- If a site presents a challenge, the collector records the source as blocked.
- No SHM purchase/sale prices or credentials are committed to the public repository.
- The next step is a private ingest endpoint so local results can upload directly to the SHM Market Center.
