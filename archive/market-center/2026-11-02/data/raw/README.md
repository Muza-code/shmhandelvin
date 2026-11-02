# SHM Market Center — raw source observations

Each NDJSON line is one source listing observation. Keep source files separate and append new observations rather than replacing prior price observations.

## Canonical fields

`source`, `source_listing_id`, `url`, `brand`, `model`, `asset_type`, `body_type`, `construction_year`, `first_registration_year`, `source_published_at`, `first_seen_at`, `last_seen_at`, `disappeared_at`, `status`, `seller`, `country`, `location`, `price_amount`, `price_currency`, `tax_basis`, `price_net_eur`, `price_gross_eur`, `axle_count`, `axle_maker`, `lift_axle`, `pallet_box`, `code_xl`, `mega`, `coil`, `joloda`, `huckepack`, `vin`, `vin_ref`, `stock_number`, `price_history`, `observed_at`, `evidence_excerpt`.

Unknown or unobserved values are null. Do not infer price, VIN, registration date, or equipment from context. `source_listing_id` uses the source URL's listing ID where available; preserve other source IDs in source-specific fields.

## Asset classification and market eligibility

- `semi_trailer` only when the source identifies the object as a semi-trailer / Sattelauflieger.
- Use `swap_body` for Wechselbrücke/BDF, `part_component` for parts or aggregates, `trailer` for an ordinary trailer, and `unknown_asset` with quarantine when uncertain.
- Rent and auction listings can be valid `semi_trailer` records; keep their `listing_type` separate and exclude them from sale-price analysis.
- Source-specific extras such as `listing_type`, `analytics_eligible`, `analytics_exclusion_reason`, `autoline_id`, `capture_page`, and `capture_position` preserve useful provenance without changing the canonical fields.

## Observation and price history

- Set `first_seen_at` on first successful observation; set `last_seen_at` each time a listing is still active.
- If absent from a later full scan, use `status: "disappeared"` and set `disappeared_at`; never label it sold without evidence.
- Append each observed price state to `price_history`; do not overwrite earlier values. A null price observation may record `price_state` such as `on_request` or `auction_price_not_shown`.
- Populate `price_net_eur` or `price_gross_eur` only when the basis is explicit in the source.

Autoline files are split by brand to keep captures resumable while remaining schema-compatible:
- `autoline_kogel.ndjson`
- `autoline_krone.ndjson`
