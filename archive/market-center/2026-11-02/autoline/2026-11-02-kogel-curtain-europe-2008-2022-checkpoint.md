# Autoline collection checkpoint — 2026-11-02

## Scope

- Source: Autoline
- Brand/body: Kögel curtain-side semi-trailer
- Region: Europe
- Year of manufacture: 2008–2022
- Sort: Placed on (newest first)
- Verified result page: https://autoline.info/-/curtain-side-semi-trailers/Kogel/Europe--c1083tm2636cgrp1?ym=2008%3A2022
- Live filtered count: 206 ads (the unfiltered Europe result showed 260 during this session; prior planning estimate ~263 is dynamic/stale).

## Collection state

- Page 1 captured: 25/25 result cards.
- Page 2 captured: 25/25 result cards; exact listing URLs were read from the live result-page links.
- Page 3 captured: 25/25 result cards; exact URLs and card data were read from the live page. Two detail pages were checked for tax, registration and equipment.
- Page 4 captured: 25/25 result cards; exact URLs and card data were read from the live page.
- Page 5 captured: 25/25 result cards; exact URLs and card data were read from the live page. One card is explicitly classified by Autoline as rental; its €8,000 is retained with a rental type and marked to exclude from sale-price comparisons.
- Page 6 captured: 25/25 result cards; one auction is preserved as auction and its displayed €3,300 is recorded as a starting bid.
- Total captured: 206/206 result cards (9 of 9 pages). Source data is in `autoline/data/kogel-curtain-europe-2008-2022.ndjson`.
- Cards were used first for price, year, type, seller, location, axles and any visible tags. Detail cards were opened selectively for complete URLs/platform IDs and characteristics not available on the result card.
- Eight records on page 1, nine records on page 2 and two records on page 3 received detail verification. Platform IDs, full first-registration dates, explicit net-price labels, axle brands/lift axles, and VINs were added only where visible on the detail page.
- A title fragment such as “VIN 370” or a detail-page field containing only “080” is not stored as a VIN. Full VIN is stored only when Autoline explicitly exposed a complete value.
- Tax basis is null unless the detail page explicitly marked the displayed asking price as net or provided net/gross prices.
- URL IDs are the listing URL suffixes and remain distinct from Autoline’s alphanumeric listing IDs and sellers’ stock references.
- Dataset is source-specific and will remain separate from the canonical SHM analytics data until the later integration/adapter step. Asking prices are not realized SHM transactions. No price history was overwritten.

## Resume point

- Filter: verified Europe / Kögel / curtain-side semi-trailer / manufacture years 2008–2022.
- Pages 1–9 processed; all 206 result cards captured. URL-ID/URL audit found no duplicates; optional yes/no fields have valid boolean/null values.
- Nineteen listings received detail verification: 8 from page 1, 9 from page 2 and 2 from page 3.
- One rental and one auction listing are retained with separate listing types; exclude them from sale-price comparisons.
- Next: begin the Krone curtain-side semi-trailer filter for Europe / years 2008–2022 in a separate Autoline source dataset. Keep brand datasets separate until the later analytics-center integration step.
- Analytics: not calculated.
- No CAPTCHA or access-control bypass was used.


## Canonical raw integration

- Canonical source file: `data/raw/autoline_kogel.ndjson`
- 206 observations converted to the SHM Market Center source schema; 206 classified as `semi_trailer`, 199 sale-price records eligible for sale-market analytics, 7 excluded from sale-price analytics because they are an auction, rental, or have no numeric asking price.
- Original capture file remains at `autoline/data/kogel-curtain-europe-2008-2022.ndjson` as source-page capture provenance. The canonical file has one observation per listing, keeps the observed price in an append-only `price_history`, and leaves first/last seen dates at 2026-11-02 pending future monitoring.


## Canonical data-quality review (2026-11-02)

- All required source-schema keys are present on every observation; nullable values remain explicit as `null`.
- No duplicate `source_listing_id` or URL values; all construction years are within the requested 2008–2022 range.
- Each record’s latest `price_history` entry matches its current observed price and currency.
- Similar seller/model/year/price fingerprints are kept as separate listings unless stronger identity evidence (same source ID/URL, VIN, or stock number) supports a relisting link. Do not merge on matching specifications alone.
