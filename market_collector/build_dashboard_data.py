import json
from collections import Counter
from pathlib import Path
from datetime import datetime, timezone

OUT=Path("out")
TARGET=Path("data/latest_market.json")

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
if not rows:
    # Preserve last good catalogue if a crawl yields nothing; only refresh coverage/status.
    listings=old.get("listings",[])
else:
    listings=[]
    for r in rows:
        features=[]
        for key,label in [
            ("axle_maker",None),("lift_axle","Lift axle"),("pallet_box","Pallet box"),
            ("code_xl","Code XL"),("mega","Mega"),("coil","Coil"),("joloda","Joloda"),("huckepack","Huckepack/P400")
        ]:
            v=r.get(key)
            if key=="axle_maker" and v: features.append(str(v))
            elif v is True: features.append(label)
        listings.append({
            "brand":r.get("brand"),"model":r.get("title"),"year":r.get("construction_year"),
            "country":r.get("country"),"seller":r.get("seller"),"price_net_eur":r.get("price_amount") if r.get("tax_basis")=="net" else None,
            "price_original":r.get("price_amount"),"currency":r.get("price_currency"),"tax_basis":r.get("tax_basis"),
            "vin":r.get("vin"),"vin_ref":(r.get("vin_refs") or [None])[0],
            "features":features,"source":r.get("source"),"status":"unknown","url":r.get("url"),
            "observed_at":r.get("observed_at")
        })

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
    key=(x.get("brand"),x.get("year"))
    if not key[0] or not key[1]: continue
    g=groups.setdefault(key,{"prices":[],"cards":0,"vin":0,"sources":set(),"countries":set()})
    g["cards"]+=1
    if x.get("vin") or x.get("vin_ref"): g["vin"]+=1
    if x.get("source"): g["sources"].add(x["source"])
    if x.get("country"): g["countries"].add(x["country"])
    p=x.get("price_net_eur")
    if isinstance(p,(int,float)): g["prices"].append(float(p))
for (brand,year),g in groups.items():
    ps=g["prices"]
    segments.append({
        "brand":brand,"year":year,"cards":g["cards"],"priced":len(ps),"vin_found":g["vin"],
        "sources":len(g["sources"]),"countries":len(g["countries"]),
        "q1_net_eur":percentile(ps,.25),"median_net_eur":percentile(ps,.5),"q3_net_eur":percentile(ps,.75)
    })
segments.sort(key=lambda x:(x["brand"],-x["year"]))

data={
    "updated_at":datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z"),
    "stats":{
        "listings":len(listings),
        "active":None,
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
