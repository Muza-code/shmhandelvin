import json
from collections import Counter
from pathlib import Path
from datetime import datetime, timezone

OUT=Path("out")
TARGET=Path("data/latest_market.json")
MOBILE_DISCOVERY=Path("data/mobile_de_discovery.json")

def infer_asset_type(x):
    v=x.get("asset_type")
    if v:
        return v
    text=" ".join(str(x.get(k) or "") for k in ("model","body_type")).lower()
    if "swap body" in text or "wechselbrücke" in text or "wechselbruecke" in text:
        return "swap_body"
    if "drawbar trailer" in text or "central axle" in text or "tandem trailer" in text:
        return "trailer"
    return "semi_trailer"

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
    y=dict(x)
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
    catalogue[key]={
        "brand":r.get("brand"),"model":r.get("title"),
        "year":r.get("market_year"),"year_basis":r.get("year_basis"),
        "construction_year":r.get("construction_year"),"first_registration_year":r.get("first_registration_year"),
        "body_type":r.get("body_type"),"asset_type":r.get("asset_type") or "semi_trailer",
        "country":r.get("country"),"seller":r.get("seller"),
        "price_net_eur":r.get("price_amount") if r.get("tax_basis")=="net" else None,
        "price_original":r.get("price_amount"),"currency":r.get("price_currency"),"tax_basis":r.get("tax_basis"),
        "vin":r.get("vin"),"vin_ref":(r.get("vin_refs") or [None])[0],
        "features":features,"source":r.get("source"),"status":"unknown","url":r.get("url"),
        "observed_at":observed,
        "first_seen_at":previous.get("first_seen_at") or previous.get("observed_at") or observed,
        "last_seen_at":observed,
        "seen_this_run":True
    }

listings=list(catalogue.values())

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
    if x["asset_type"]!="semi_trailer":
        continue
    key=(x.get("brand"),x.get("year"),x.get("body_type") or "other")
    if not key[0] or not key[1]: continue
    g=groups.setdefault(key,{"net_prices":[],"ask_eur":[],"cards":0,"vin":0,"construction_known":0,"sources":set(),"countries":set()})
    g["cards"]+=1
    if x.get("construction_year") is not None: g["construction_known"]+=1
    if x.get("vin") or x.get("vin_ref"): g["vin"]+=1
    if x.get("source"): g["sources"].add(x["source"])
    if x.get("country"): g["countries"].add(x["country"])
    p=x.get("price_net_eur")
    if isinstance(p,(int,float)): g["net_prices"].append(float(p))
    ask=x.get("price_original")
    if x.get("currency")=="EUR" and isinstance(ask,(int,float)): g["ask_eur"].append(float(ask))
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
    "stats":{
        "listings":len(listings),
        "semitrailers":sum(infer_asset_type(x)=="semi_trailer" for x in listings),
        "active":sum(bool(x.get("seen_this_run")) for x in listings),
        "seen_this_run":sum(bool(x.get("seen_this_run")) for x in listings),
        "vin_found":sum(bool(x.get("vin") or x.get("vin_ref")) for x in listings),
        "sources":len(sources)
    },
    "coverage":coverage,
    "segments":segments,
    "listings":listings
}
TARGET.parent.mkdir(parents=True,exist_ok=True)
TARGET.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(data["stats"],ensure_ascii=False))
