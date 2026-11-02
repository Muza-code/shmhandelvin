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
- Captured pages 1–4: 100 listing cards, positions 1–25 on each page.
- De-duplication: source listing ID parsed from the URL; URL and ID are the keys. No repeated IDs were found when appending pages 2–4.
- Page 1 includes one auction listing; page 2 includes two auction listings; page 4 includes one auction listing without a numeric price on the card. Auction prices are kept separate by listing type and notes. “Price on request” is stored as null, never inferred.
- Page 4 position 10 title includes “5 PIECE”; detail review is pending to decide whether the listing represents a single eligible semi-trailer or a multi-unit bundle. Do not include in clean-market analysis until resolved.
- Page 4 position 8 is a coil liner, with lifting axle explicitly indicated in the title; preserved with `coil: true` and `lift_axle: true`.
- Detailed-card verification has not yet been started for Krone. Continue to use card data first; open detail pages only to resolve questionable listings or missing required characteristics.

## Current dataset notes

- Records preserve source, URL, URL-derived ID, brand/model, year, first registration (null unless explicit), listed price/currency, tax basis (null unless explicit), seller, country/location, axle count/brand, lift axle, pallet box, Code XL, Mega, coil, VIN (null unless explicit), listing type, observed date, page and position.
- Where a card shows weight, volume or suspension, the information is kept in notes. Do not move price history or overwrite previous observations during later monitoring.
- Category is Autoline’s “curtain side semi-trailer”; exclude BDF/swap bodies, parts, aggregates, and records proven to be something else from downstream analysis.

## Next resume step

1. Return to the filter URL and capture page 5, positions 1–25, keeping exact card URLs/IDs.
2. After finishing this 716-ad brand/category subset, move to the next brand in its own dataset.
3. Keep each source/brand capture separate until an integration step defines a canonical analytics schema; never merge by editing source rows in place.
