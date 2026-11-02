import json
import re
from collections import Counter
from pathlib import Path
from datetime import datetime, timezone

OUT=Path("out")
TARGET=Path("data/latest_market.json")
MOBILE_DISCOVERY=Path("data/mobile_de_discovery.json")
EXCLUSIONS_PATH=Path("data/raw/market_center_exclusions.json")
NON_CANONICAL_SOURCES={"mobile.de via ReefAPI"}

def condition_signals(x):
    text=" ".join(str(x.get(k) or "") for k in ("model","body_type","evidence_excerpt","description","exclusion_reason")).lower()
    flags=[]
    severe=[]
    if re.search(r"\\bunfall(?!frei)\\w*|\\baccident(?:[ -]+(?:damaged|damage|vehicle))\\b|\\bcrash(?:ed| damage)\\b|\\bwreck(?:ed)?\\b|rear[- ]end crash|b[uú]ran[áa]",text):
        flags.append("Аварийное повреждение указано в объявлении")
        severe.append("accident_damage")
    if re.search(r"no (?:registration )?(?:documents|papers)|without (?:registration )?(?:documents|papers)|documents? missing|bez\\s+tp\\b|no vehicle papers|without vehicle papers",text):
        flags.append("Документы отсутствуют или указаны как неполные")
        severe.append("missing_documents")
    if re.search(r"not roadworthy|non[- ]running|not running|does not run|nicht fahrbereit|не на ходу|non funziona",text):
        flags.append("Не на ходу / не допускается к эксплуатации по описанию")
        severe.append("not_roadworthy")
    if re.search(r"needs? repair|repair required|reparaturbedürftig|reparaturbeduerftig|needs? work|defekt|damaged|beschädigt|beschaedigt",text) and "Аварийное повреждение указано в объявлении" not in flags:
        flags.append("Требуется проверка ремонта/повреждений")
    tire=re.search(r"(?:tyre|tire|reifen|pneu)[^.%\\n]{0,45}(\\d{1,3})\\s*%",text)
    if tire:
        flags.append(f"Состояние шин в объявлении: {tire.group(1)}% — оценить замену")
    return flags,severe

def sanitize_suspicious_price(x):
    """Remove obvious year-as-price parsing errors from persisted catalogue rows."""
    p=x.get("price_original")
    if not isinstance(p,(int,float)):
        return x
    # In this vehicle catalogue a bare 4-digit calendar-year-sized amount is
    # never trusted as a market price. Old rows may predate price-confidence fields.
    if 1900 <= float(p) <= 2100 and float(p).is_integer():
        x["price_original"]=None
        x["price_net_eur"]=None
        x["currency"]=None
        x["tax_basis"]=None
        x["price_confidence"]="rejected"
        x["price_quality_flag"]="rejected_year_like_price"
    return x

def infer_asset_type(x):
    explicit=x.get("asset_type")
    if explicit in {"semi_trailer","swap_body","part_component","trailer","unknown_asset"}:
        return explicit
    text=" ".join(str(x.get(k) or "") for k in ("model","body_type")).lower()

    part_terms=[
        "kühlmaschine","kuehlmaschine","kühlaggregat","kuehlaggregat",
        "refrigeration unit","cooling unit","spare part","ersatzteil",
        "aggregat","kompressor","compressor","landing legs","stützen","stuetzen",
        "door assembly","tür komplett","tuer komplett","bumper","stoßstange","stossstange"
    ]
    if any(term in text for term in part_terms):
        return "part_component"

    swap_terms=[
        "wechselbrücke","wechselbruecke","swap body","wechselkoffer",
        "wechselcontainer","bdf wechsel","bdf container","bdf brücke","bdf bruecke"
    ]
    if any(term in text for term in swap_terms) or ("bdf" in text and "sattelauflieger" not in text and "semi" not in text):
        return "swap_body"

    trailer_terms=[
        "drawbar trailer","central axle","tandem trailer",
        "zentralachsanhänger","zentralachsanhaenger",
        "drehschemelanhänger","drehschemelanhaenger"
    ]
    if any(term in text for term in trailer_terms):
        return "trailer"

    semi_terms=[
        "sattelauflieger","semi-trailer","semitrailer",
        "auflieger","sattelanhänger","sattelanhaenger"
    ]
    if any(term in text for term in semi_terms):
        return "semi_trailer"

    return "unknown_asset"

def percentile(values,p):
    if not values: return None
    xs=sorted(values)
    if len(xs)==1: return xs[0]
    k=(len(xs)-1)*p
    lo=int(k); hi=min(lo+1,len(xs)-1)
    return round(xs[lo]+(xs[hi]-xs[lo])*(k-lo),2)

def read_ndjson(path):
    if not path.exists(): return []
    rows=[]
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try: rows.append(json.loads(line))
            except Exception: pass
    return rows

old={}
if TARGET.exists():
    try: old=json.loads(TARGET.read_text(encoding="utf-8"))
    except Exception: old={}

rows=read_ndjson(OUT/"listings.ndjson")
events=read_ndjson(OUT/"access_events.ndjson")

old_listings=old.get("listings",[]) if isinstance(old,dict) else []
catalogue={}
for x in old_listings:
    key=(x.get("source"),x.get("url"))
    if not key[0] or not key[1]:
        continue
    y=sanitize_suspicious_price(dict(x))
    y["asset_type"]=infer_asset_type(y)
    y.setdefault("first_seen_at",y.get("observed_at"))
    y.setdefault("last_seen_at",y.get("observed_at"))
    y["seen_this_run"]=False
    catalogue[key]=y

for r in rows:
    features=[]
    for key,label in [
        ("axle_maker",None),("lift_axle","Lift axle"),("pallet_box","Pallet box"),
        ("code_xl","Code XL"),("mega","Mega"),("coil","Coil"),("joloda","Joloda"),("huckepack","Huckepack/P400")
    ]:
        v=r.get(key)
        if key=="axle_maker" and v: features.append(str(v))
        elif v is True: features.append(label)

    key=(r.get("source"),r.get("url"))
    if not key[0] or not key[1]:
        continue
    previous=catalogue.get(key,{})
    observed=r.get("observed_at")
    new_row={
        "brand":r.get("brand"),"model":r.get("title"),
        "year":r.get("market_year"),"year_basis":r.get("year_basis"),
        "construction_year":r.get("construction_year"),"first_registration_year":r.get("first_registration_year"),
        "body_type":r.get("body_type"),"asset_type":previous.get("asset_type") or infer_asset_type({"model":r.get("title"),"body_type":r.get("body_type")}),
        "asset_evidence_score":r.get("asset_evidence_score"),
        "country":r.get("country"),"seller":r.get("seller"),
        "price_net_eur":r.get("price_amount") if r.get("tax_basis")=="net" and r.get("price_confidence") in (None,"medium","high") else None,
        "price_original":r.get("price_amount"),
        "currency":r.get("price_currency"),
        "tax_basis":r.get("tax_basis"),
        "price_confidence":r.get("price_confidence") or "legacy",
        "price_evidence":r.get("price_evidence"),
        "evidence_excerpt":r.get("evidence_excerpt"),
        "vin":r.get("vin"),"vin_ref":(r.get("vin_refs") or [None])[0],
        "features":features,"source":r.get("source"),"status":"unknown","url":r.get("url"),
        "observed_at":observed,
        "first_seen_at":previous.get("first_seen_at") or previous.get("observed_at") or observed,
        "last_seen_at":observed,
        "seen_this_run":True
    }
    catalogue[key]=sanitize_suspicious_price({**previous,**new_row})

listings=[]
for _x in catalogue.values():
    _y=sanitize_suspicious_price(dict(_x))
    _y["asset_type"]=infer_asset_type(_y)
    listings.append(_y)

# Apply the human-reviewed exclusion register after merging persistent and new rows.
# Keep source observations intact, but never use known components or damaged units
# as purchase opportunities or comparable prices.
exclusions={}
if EXCLUSIONS_PATH.exists():
    try:
        _doc=json.loads(EXCLUSIONS_PATH.read_text(encoding="utf-8"))
        exclusions={rule.get("url"):rule for rule in _doc.get("rules",[]) if rule.get("url")}
    except Exception:
        exclusions={}
for _y in listings:
    rule=exclusions.get(_y.get("url"))
    if not rule:
        continue
    if rule.get("asset_type_override"):
        _y["asset_type"]=rule["asset_type_override"]
    if rule.get("purchase_eligible") is False:
        _y["purchase_eligible"]=False
    if rule.get("analytics_eligible") is False:
        _y["analytics_eligible"]=False
    _y["exclusion_code"]=rule.get("exclusion_code")
    _y["exclusion_reason"]=rule.get("exclusion_reason")
    _y["asset_type"]=infer_asset_type(_y)

# Preserve source wording and surface explicit condition risks. Missing information
# stays unknown; it is never treated as evidence that a trailer is in good order.
for _y in listings:
    _y.setdefault("evidence_excerpt",None)
    flags,severe=condition_signals(_y)
    _y["condition_flags"]=flags
    _y["condition_status"]="risk_reported" if flags else "unknown"
    if severe:
        _y["purchase_eligible"]=False
        _y["analytics_eligible"]=False
        _y.setdefault("exclusion_code",severe[0])
        _y.setdefault("exclusion_reason","; ".join(flags))

sources=Counter(x.get("source") for x in listings if x.get("source"))
coverage=[]
for s in sorted(set(list(sources)+[e.get("source") for e in events if e.get("source")])):
    errs=[e for e in events if e.get("source")==s]
    state="live" if sources.get(s,0)>0 else "partial"
    note=f"{sources.get(s,0)} cards"
    if errs and not sources.get(s,0): note=f"{len(errs)} access events, no cards"
    coverage.append({"source":s,"state":state,"state_label":"работает" if state=="live" else "проверить","note":note})

segments=[]
groups={}
for x in listings:
    x["asset_type"]=infer_asset_type(x)
    if x.get("source") in NON_CANONICAL_SOURCES:
        continue
    if x["asset_type"]!="semi_trailer":
        continue
    if isinstance(x.get("asset_evidence_score"),(int,float)) and x.get("asset_evidence_score") < 4:
        continue
    key=(x.get("brand"),x.get("year"),x.get("body_type") or "other")
    if not key[0] or not key[1]: continue
    g=groups.setdefault(key,{"net_prices":[],"ask_eur":[],"cards":0,"vin":0,"construction_known":0,"sources":set(),"countries":set()})
    g["cards"]+=1
    if x.get("construction_year") is not None: g["construction_known"]+=1
    if x.get("vin") or x.get("vin_ref"): g["vin"]+=1
    if x.get("source"): g["sources"].add(x["source"])
    if x.get("country"): g["countries"].add(x["country"])
    price_ok=x.get("analytics_eligible") is not False and x.get("price_confidence") not in {"low","rejected"}
    p=x.get("price_net_eur")
    if price_ok and isinstance(p,(int,float)): g["net_prices"].append(float(p))
    ask=x.get("price_original")
    if price_ok and x.get("currency")=="EUR" and isinstance(ask,(int,float)): g["ask_eur"].append(float(ask))
for (brand,year,body_type),g in groups.items():
    ps=g["net_prices"]; asks=g["ask_eur"]
    segments.append({
        "brand":brand,"year":year,"body_type":body_type,"cards":g["cards"],
        "priced":len(asks),"net_priced":len(ps),"vin_found":g["vin"],
        "sources":len(g["sources"]),"countries":len(g["countries"]),"construction_year_known":g["construction_known"],
        "q1_ask_eur":percentile(asks,.25),"median_ask_eur":percentile(asks,.5),"q3_ask_eur":percentile(asks,.75),
        "q1_net_eur":percentile(ps,.25),"median_net_eur":percentile(ps,.5),"q3_net_eur":percentile(ps,.75)
    })
segments.sort(key=lambda x:(x["brand"],-x["year"],x["body_type"]))

discovery={}
if MOBILE_DISCOVERY.exists():
    try:
        discovery["mobile_de"]=json.loads(MOBILE_DISCOVERY.read_text(encoding="utf-8"))
    except Exception:
        discovery["mobile_de"]={"error":"unreadable discovery snapshot"}

data={
    "updated_at":datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z"),
    "discovery":discovery,
    "dataset_scope":"Combined source observations and collector catalogue. Cross-market duplicates are not automatically merged.",
    "analytics_method":{
        "asking_prices":"Segments use numeric EUR asking prices for semi-trailers, excluding rows explicitly marked ineligible or low/rejected confidence.",
        "net_prices":"Net statistics use only explicitly confirmed net prices.",
        "cross_market_duplicates":"Listings on different marketplaces remain separate source observations unless manually reconciled."
    },
    "stats":{
        "listings":len(listings),
        "semitrailers":sum(infer_asset_type(x)=="semi_trailer" for x in listings),
        "parts_components":sum(infer_asset_type(x)=="part_component" for x in listings),
        "swap_bodies":sum(infer_asset_type(x)=="swap_body" for x in listings),
        "trailers":sum(infer_asset_type(x)=="trailer" for x in listings),
        "unknown_assets":sum(infer_asset_type(x)=="unknown_asset" for x in listings),
        "strict_accepted":sum(x.get("source") not in NON_CANONICAL_SOURCES and x.get("purchase_eligible") is not False and infer_asset_type(x)=="semi_trailer" and (not isinstance(x.get("asset_evidence_score"),(int,float)) or x.get("asset_evidence_score")>=4) for x in listings),
        "purchase_eligible":sum(x.get("source") not in NON_CANONICAL_SOURCES and x.get("purchase_eligible") is not False and infer_asset_type(x)=="semi_trailer" and (not isinstance(x.get("asset_evidence_score"),(int,float)) or x.get("asset_evidence_score")>=4) for x in listings),
        "purchase_excluded":sum(x.get("purchase_eligible") is False for x in listings),
        "price_analytics_excluded":sum(x.get("analytics_eligible") is False for x in listings),
        "active":sum(x.get("status")=="active" for x in listings),
        "seen_this_run":sum(bool(x.get("seen_this_run")) for x in listings),
        "vin_found":sum(bool(x.get("vin") or x.get("vin_ref")) for x in listings),
        "sources":len(sources),
        "price_analytics_eligible":sum(x["priced"] for x in segments),
        "price_net_analytics_eligible":sum(x["net_priced"] for x in segments),
        "market_segments":len(segments)
    },
    "coverage":coverage,
    "segments":segments,
    "quarantine":[x for x in listings if infer_asset_type(x)!="semi_trailer"],
    "listings":listings
}
TARGET.parent.mkdir(parents=True,exist_ok=True)
TARGET.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(data["stats"],ensure_ascii=False))
