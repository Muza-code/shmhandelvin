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

## Browser workflow

- Keep browser usage lightweight: one results-list tab and one reusable detail tab, plus at most one service tab when needed (maximum 2–3 working tabs).
- Reuse the same detail tab for listings that need inspection, then return to the results list. Do not open a new tab per listing.
- Skip detail pages when the results card already provides enough required evidence. Close unneeded tabs periodically.

## Saved progress

- Data file: `autoline/data/krone-curtain-europe-2008-2022.ndjson`
- Captured pages 1–29: 725 result-card observations. Pages 1–14 had 350 unique IDs; page 15 added 25 repeat sightings; page 16 added 1 new ID and 24 repeats; page 17 added 23 new IDs and 2 repeats; pages 18, 19, and 20 added 25 new IDs each.
- De-duplication: source listing ID parsed from the URL; URL and ID are the keys. No repeated IDs were found on pages 2–14. Pages 15–19 contain 51 repeat sightings in total; repeat sightings are recorded as additional page observations without duplicate source rows.
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

1. Return to the filter URL and capture page 20, positions 1–25, keeping exact card URLs/IDs.
2. After finishing this 716-ad brand/category subset, move to the next brand in its own dataset.
3. Keep each source/brand capture separate until an integration step defines a canonical analytics schema; never merge by editing source rows in place.


## Canonical raw integration

- Canonical source file: `data/raw/autoline_krone.ndjson` (same schema as the Kögel source file; retained separately by brand for the later combined database).
- 671 unique source records classified as `semi_trailer`; 604 numeric-price sale records are eligible for sale-market analytics. The current capture has 725 page-card observations through page 29, including 54 repeat sightings. The other 67 comprise 9 auctions, 5 rentals, 53 sale ads excluded for no numeric asking price or duplicate/relisting/quality basis.
- Original capture file remains at `autoline/data/krone-curtain-europe-2008-2022.ndjson` as source-page capture provenance. The canonical file has one observation per listing and initial price-history entries dated 2026-11-02.
- Resume at page 30; pages 1–29 reviewed (725 card views; 671 unique IDs). Page 15 was all repeat sightings; page 16 added 1; page 17 added 23; pages 18–20 each added 25; page 21 added 22 new IDs and 3 repeats. P. Mostert listings with individual seller stock IDs are distinct units and their displayed per-unit prices are eligible; the page 18 10-unit inventory remains excluded because its unit-price basis is not explicit.


## Canonical data-quality review (2026-11-02)

- All required source-schema keys are present on every observation; nullable values remain explicit as `null`.
- No duplicate `source_listing_id` or URL values; all construction years are within the requested 2008–2022 range.
- Each record’s latest `price_history` entry matches its current observed price and currency.
- Similar seller/model/year/price fingerprints are kept as separate listings unless stronger identity evidence (same source ID/URL, VIN, or stock number) supports a relisting link. Do not merge on matching specifications alone.


## Continuation note (2026-11-02)

- Reused one list tab and one detail tab. Page 15: 25 cards, all repeat IDs; page 16: 1 new ID and 24 repeats; page 17: 23 new IDs and 2 repeats; pages 18–20: 25 new IDs each. Detail cards clarified registration dates, explicit net/gross basis, stock numbers and axle data. Near-identical listings with different stock numbers remain separate; the page 18 10-unit inventory remains excluded from price analytics because the price basis per unit is unclear.
- Publicly indexed Autoline material surfaced candidate ID `26090210215133557300`, but its indexed snippet showed €18,900 while the opened page snapshot showed €17,900 net / €22,017 gross. This candidate was not added or treated as current until the asking price and active status can be rechecked on the listing source.


- Page 20: 25 cards reviewed; all 25 source IDs were new. Two Gema units and two Equipped4U units retained as separate trailers based on distinct seller stock numbers. Four TIP records have separate listing IDs; title reference numbers retained in the model, not guessed as stock IDs. Details added explicit first registrations, net price basis, BPW/lift axle/pallet box where confirmed. Page 21 was subsequently completed; current resume page is 23.

- Page 21: 25 cards reviewed; 22 new source IDs and 3 repeats from page 20. The 4 regional listings at €19,400 share seller stock IMP-4998; one is retained for market analytics and 3 copies excluded, with a relisting group key. Two ads explicitly priced on request remain excluded. Detail checks confirmed a further Equipped4U unit (stock OP34GP, €6,985 net, 2016-05 first registration, BPW/lifting axle/pallet box) and BAS World unit (stock 70338834, €8,400 net, 2014-06 first registration). One regional clone’s listing card location (Romania) conflicts with linked detail (Serbia), noted and excluded. Next resume page: 22.

- Page 22: 25 cards reviewed; all 25 IDs new. One listing is explicitly price on request and excluded from price analytics; 24 numeric-price sale ads were added. TIP units retain listing IDs separately; title reference numbers are kept in model text, not assumed to be seller stock IDs. Next resume page: 23.

- Page 23: 25 new IDs. A four-country 2017 listing set shares seller stock IMP-4971; one copy is retained for analytics, three are excluded. Page 23’s 2018 €14,000 Mega copy shares stock IMP-3694 with a page 22 Romania listing; the earlier row is linked and the later regional copy excluded. Detail confirmed the Kel-Berg model under Krone brand (stock E16309) and explicit net prices. One on-request ad excluded. Next resume page: 24.

- Page 24: 25 new IDs; one price-on-request listing excluded from price analytics. Three KRONE USED units are distinct (seller stock F0929091, F0929085, F0929087). Gema details confirm three separate stock units (4962, 5059, 5421), explicit net prices, and first registration years; the prior Gema page 20 unit has a different stock ID 4964. Next resume page: 25.

- Page 25: 25 new IDs; 21 numeric-price ads eligible for market analysis, two price-on-request ads excluded, and two multi-unit offers (8 units, 3 units) excluded because no per-unit price is confirmed. Reused the same detail tab. Three KRONE USED items have distinct stock numbers; two SEMITRAILER 2017 offers remain distinct source listings because no shared unit identifier was visible. Next resume page: 26.

- Page 26: 25 new listing IDs/observations (23 sale, 1 auction, 1 rent). One price-on-request sale, a 5-unit bundled offer with conflicting €3,500 price block vs €18,000 + VAT for the set, and the auction/rent records are excluded from price medians. The €229,000 Krone L S24-1 was detail-verified as a semi-trailer at €229,000 net / €274,800 gross. Explicit auction VIN WKESD000000755222 was captured. Next resume page: 27.

- Page 27: 25 new IDs; two cards are price on request. A Romania regional clone shares seller stock IMP-4788 with the Hungary listing; one retained, one excluded. The two Danish 2013 curtainsiders are separate units with distinct stocks 0557054 and 0557052; prices explicitly net. Next resume page: 28.

- Page 28: 25 new IDs; 3 auction listings, one price-on-request listing, and 6 confirmed duplicate copies excluded from market analysis. Same stock IDs DO1042, DO1036, DO1035, LT0405 and DO1034 linked to earlier Romania listings; IMP-4771 linked between Hungary/Romania page 28. A distinct Latvian €7,750 unit and the separate Laslo listings with different stock IDs remain eligible. Next resume page: 29.

- Page 29: 25 new IDs; one price-on-request listing. A Laslo Truck Romania row shares stock DO1031 with the page 22 record and is excluded as a relisting; the original was updated with net/gross, first registration and BPW/Mega data. Two KRONE FRANCE €7,250 offers have distinct stock IDs 14086 and 14085 and remain separate. Next resume page: 30.
