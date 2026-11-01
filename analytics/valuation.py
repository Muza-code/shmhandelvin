from __future__ import annotations

import json
import math
import os
from pathlib import Path
from statistics import median

PUBLIC_DATA = Path(os.getenv("SHM_MARKET_JSON", "data/latest_market.json"))
PRIVATE_ANCHORS = Path(os.getenv("SHM_PRIVATE_ANCHORS_FILE", "private/valuation_anchors.json"))


def _load(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def public_market():
    return _load(PUBLIC_DATA, {"listings": [], "segments": []})


def private_anchors():
    # Never silently substitute zeroes for missing business costs/anchors.
    return _load(PRIVATE_ANCHORS, {"anchors": [], "cost_rules": []})


def _feature_set(x):
    return {str(v).strip().lower() for v in (x.get("features") or []) if v}


def comparable_score(target, row):
    if target.get("brand") != row.get("brand"):
        return -999
    score = 0
    if target.get("year") == row.get("year"):
        score += 6
    elif target.get("year") and row.get("year") and abs(int(target["year"]) - int(row["year"])) == 1:
        score += 2
    if target.get("body_type") and target.get("body_type") == row.get("body_type"):
        score += 5
    tf = _feature_set(target)
    rf = _feature_set(row)
    score += min(5, len(tf & rf))
    if target.get("country") and target.get("country") == row.get("country"):
        score += 1
    return score


def comparable_market(target, minimum_score=10):
    data = public_market()
    candidates = []
    for row in data.get("listings", []):
        p = row.get("price_net_eur")
        if not isinstance(p, (int, float)):
            continue
        sc = comparable_score(target, row)
        if sc >= minimum_score:
            candidates.append((sc, row))

    candidates.sort(key=lambda z: (-z[0], z[1].get("price_net_eur", math.inf)))
    rows = [r for _, r in candidates]
    prices = sorted(float(r["price_net_eur"]) for r in rows)
    if not prices:
        return {"n": 0, "median_net_eur": None, "q1_net_eur": None, "rows": []}

    def percentile(p):
        if len(prices) == 1:
            return prices[0]
        k = (len(prices) - 1) * p
        lo = int(k)
        hi = min(lo + 1, len(prices) - 1)
        return round(prices[lo] + (prices[hi] - prices[lo]) * (k - lo), 2)

    return {
        "n": len(rows),
        "median_net_eur": round(median(prices), 2),
        "q1_net_eur": percentile(0.25),
        "q3_net_eur": percentile(0.75),
        "sources": len({r.get("source") for r in rows if r.get("source")}),
        "countries": len({r.get("country") for r in rows if r.get("country")}),
        "rows": rows[:50],
    }


def matching_anchors(target):
    p = private_anchors()
    out = []
    for a in p.get("anchors", []):
        if a.get("brand") and a["brand"] != target.get("brand"):
            continue
        if a.get("year") and int(a["year"]) != int(target.get("year") or -1):
            continue
        if a.get("body_type") and a["body_type"] != target.get("body_type"):
            continue
        required = {str(x).lower() for x in a.get("required_features", [])}
        if required and not required.issubset(_feature_set(target)):
            continue
        out.append(a)
    return out


def evaluate(target, transport_to_wyhl_eur=None, post_arrival_costs_eur=None, target_profit_eur=None):
    market = comparable_market(target)
    anchors = matching_anchors(target)

    resale_refs = [
        float(a["amount_eur"])
        for a in anchors
        if a.get("anchor_type") in {"expert_resale_floor", "actual_sale"} and isinstance(a.get("amount_eur"), (int, float))
    ]
    delivered_buy_refs = [
        float(a["amount_eur"])
        for a in anchors
        if a.get("anchor_type") in {"known_delivered_buy", "actual_purchase"} and isinstance(a.get("amount_eur"), (int, float))
    ]

    # Conservative resale is deliberately not invented if no SHM/private anchor exists.
    conservative_resale = min(resale_refs) if resale_refs else None
    profit = float(target_profit_eur) if target_profit_eur is not None else None

    conditional_max_delivered = None
    operational_max_delivered = None
    max_seller_price = None

    if conservative_resale is not None and profit is not None:
        conditional_max_delivered = conservative_resale - profit
        if post_arrival_costs_eur is not None:
            operational_max_delivered = conditional_max_delivered - float(post_arrival_costs_eur)
            if transport_to_wyhl_eur is not None:
                max_seller_price = operational_max_delivered - float(transport_to_wyhl_eur)

    return {
        "target": target,
        "market": {k: v for k, v in market.items() if k != "rows"},
        "matched_anchor_count": len(anchors),
        "known_delivered_buy_refs_eur": delivered_buy_refs,
        "conservative_resale_eur": conservative_resale,
        "target_profit_eur": profit,
        "transport_to_wyhl_eur": transport_to_wyhl_eur,
        "post_arrival_costs_eur": post_arrival_costs_eur,
        "conditional_max_buy_delivered_wyhl_eur": conditional_max_delivered,
        "operational_max_buy_delivered_wyhl_eur": operational_max_delivered,
        "max_seller_price_eur": max_seller_price,
        "missing": [
            name for name, value in [
                ("private_resale_anchor", conservative_resale),
                ("target_profit", profit),
                ("post_arrival_costs", post_arrival_costs_eur),
                ("transport_to_wyhl", transport_to_wyhl_eur),
            ] if value is None
        ],
    }
