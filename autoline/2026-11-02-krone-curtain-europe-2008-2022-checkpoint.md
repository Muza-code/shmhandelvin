# Autoline checkpoint — Krone curtain side, Europe, 2008–2022

Date captured: 2026-11-02

## Scope and filter

- Source: Autoline
- Brand: Krone
- Category: curtain side semi-trailers
- Location: Europe
- Manufacture year: 2008–2022
- Filter URL: https://autoline.info/-/curtain-side-semi-trailers/Krone/Europe--c1083tm2641cgrp1?ym=2008%3A2022
- Observed live result count: 716 ads; 29 pages.
- “Placed on” sorting is shown on the results page and is used for this capture. Keep this sorting for subsequent daily new-listing monitoring.

## Saved progress

- Data file: `autoline/data/krone-curtain-europe-2008-2022.ndjson`
- Captured pages 1–13: 325 listing cards, positions 1–25 on each page.
- De-duplication: source listing ID parsed from the URL; URL and ID are the keys. No repeated IDs were found when appending pages 2–13.
- Page 1 includes one auction listing; page 2 includes two auction listings; page 4 includes one auction listing without a numeric price on the card. Auction prices are kept separate by listing type and notes. “Price on request” is stored as null, never inferred.
- Page 4 position 10 (ID 25092419584735323100) was checked on its detail page: it is one curtain-side semi-trailer. The €20,900 net price, €25,707 gross price, SAF axles, and XL Certificate were captured; seller description also mentions loading five trailers, but the advertised unit itself is a single trailer.
- Page 4 position 8 is a coil liner, with lifting axle explicitly indicated in the title; preserved with `coil: true` and `lift_axle: true`.
- Page 6 position 6 confirms a bundle of 3 trailers; preserve the displayed €7,900 net, but do not use it as a clean per-unit market price unless the basis is later clarified.
- Page 8 position 1 is marked “2 PIECES”; detail page provides one VIN and specs for a specific unit. Price remains null because the page says price on request.
- Page 11 position 13 is a rent ad; page 12 position 8 is priced at €700/month. Both rent ads use a separate listing type and are excluded from sale-price analysis.
- Three detail pages have been checked: the “5 PIECE” listing is one specific trailer; the “2 PIECES” listing has a single VIN and detailed specs; and the “3 x” listing is a three-trailer offer whose per-unit price basis is unclear. Continue to use card data first; open detail pages only to resolve questionable listings or missing required characteristics.

## Current dataset notes

- Records preserve source, URL, URL-derived ID, brand/model, year, first registration (null unless explicit), listed price/currency, tax basis (null unless explicit), seller, country/location, axle count/brand, lift axle, pallet box, Code XL, Mega, coil, VIN (null unless explicit), listing type, observed date, page and position.
- Where a card shows weight, volume or suspension, the information is kept in notes. Do not move price history or overwrite previous observations during later monitoring.
- Category is Autoline’s “curtain side semi-trailer”; exclude BDF/swap bodies, parts, aggregates, and records proven to be something else from downstream analysis.

## Next resume step

1. Return to the filter URL and capture page 14, positions 1–25, keeping exact card URLs/IDs.
2. After finishing this 716-ad brand/category subset, move to the next brand in its own dataset.
3. Keep each source/brand capture separate until an integration step defines a canonical analytics schema; never merge by editing source rows in place.


## Canonical raw integration

- Canonical source file: `data/raw/autoline_krone.ndjson` (same schema as the Kögel source file; retained separately by brand for the later combined database).
- 300 observations converted; 300 classified as `semi_trailer`, 278 priced sale records eligible for sale-market analytics; auctions, rentals, and unpriced ads remain separate/excluded from sale-price analysis.
- Original capture file remains at `autoline/data/krone-curtain-europe-2008-2022.ndjson` as source-page capture provenance. The canonical file has one observation per listing and initial price-history entries dated 2026-11-02.
- Resume at page 13; 13 of 29 pages captured (325 of 716 result cards).
