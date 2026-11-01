# SHM Market Collector

Automated public/authorized-source collector for SHM's European semi-trailer market intelligence system.

## Scope
- Brands: Kögel, Krone, Schmitz Cargobull, Schwarzmüller
- Years: 2008-2021; 2021 has priority
- Preserve source URL, source ID, observed time, asking price, tax basis when explicit, construction year, first registration, VIN when visible, axle maker, lift axle, pallet box and other evidence.
- Unknown values stay unknown. A failed request is an access event, not a sale.

## Execution
The GitHub Actions workflow runs twice daily and also supports manual runs. Each run writes:
- `out/listings.ndjson`
- `out/access_events.ndjson`
- `out/summary.json`

If repository secrets `SHM_INGEST_URL` and `SHM_INGEST_TOKEN` are configured, the run also POSTs the normalized batch to SHM's private ingest endpoint. Without them, collection still runs and the result is retained as a workflow artifact.

## Optional mobile.de API
Set repository secrets `MOBILEDE_USERNAME` and `MOBILEDE_PASSWORD` only after SHM has valid Search API access. The implementation uses HTTP Basic authentication and the official JSON media type. The Search API has a 2,000-result pagination ceiling per query, so the collector splits requests by country, brand and construction year.

## Security
Do not commit API keys, passwords, SHM purchase/sale benchmarks or transaction data. Secrets belong in GitHub Actions secrets or the private SHM database.
