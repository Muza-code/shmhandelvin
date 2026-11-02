from __future__ import annotations
import json, os, re, sys
import requests

KEY=os.getenv("REEF_API_KEY","").strip()
if not KEY:
    raise SystemExit("REEF_API_KEY missing")

BASE="https://api.reefapi.com/mobile-de/v1"
HEAD={"x-api-key":KEY,"content-type":"application/json","User-Agent":"SHM-Mobile-Coverage-Probe/1.0"}

def call(action,payload):
    r=requests.post(f"{BASE}/{action}",headers=HEAD,json=payload,timeout=30)
    try: body=r.json()
    except Exception: body={"ok":False,"error":{"message":r.text[:1000]}}
    return r.status_code,body

def norm(s):
    s=str(s or "").lower().strip()
    for a,b in (("ä","ae"),("ö","oe"),("ü","ue"),("ß","ss")):
        s=s.replace(a,b)
    return re.sub(r"[^a-z0-9]+","",s)

print("SHM mobile.de coverage probe")
print("Target control: Kögel + Pritsche/Plane + Erstzulassung 2008-2022 ~= 241 results")
print()

# 1) Resolve Kögel make under truck
status,makes=call("makes",{"vehicle_type":"truck"})
make_id=None
make_label=None
if makes.get("ok"):
    data=makes.get("data") or {}
    rows=data.get("makes") or data.get("items") or data.get("results") or (data if isinstance(data,list) else [])
    for m in rows if isinstance(rows,list) else []:
        if not isinstance(m,dict): continue
        name=m.get("name") or m.get("label") or m.get("make")
        if norm(name) in {"koegel","kogel"}:
            make_id=m.get("id") or m.get("make_id") or m.get("value") or name
            make_label=name
            break
print("make:",make_label or "not resolved","id:",make_id)

# 2) Baseline: broad Kögel 2008-2022
base={"vehicle_type":"truck","year_min":2008,"year_max":2022,"page":1,"page_size":100,"language":"de"}
if make_id: base["make"]=str(make_id)
else: base["query"]="Koegel"

status,body=call("search",base)
if body.get("ok"):
    d=body.get("data") or {}
    print("BASELINE total_results:",d.get("total_results"),"count:",d.get("count") or len(d.get("listings") or d.get("results") or []))
else:
    print("BASELINE ERROR:",json.dumps(body.get("error"),ensure_ascii=False))

# 3) Ask validator for valid body_type values using deliberately invalid value.
probe=dict(base)
probe["body_type"]="__SHM_PROBE_INVALID__"
_,invalid=call("search",probe)
err=invalid.get("error") or {}
msg=str(err.get("message") or err)
print()
print("body_type validator:",msg)

# Pull likely enum tokens from validator message, then try only plausible tarp/platform/curtain values.
tokens=[]
for token in re.findall(r"[A-Za-z][A-Za-z0-9_+-]{2,40}",msg):
    low=token.lower()
    if any(k in low for k in ("curtain","tarp","tarpa","platform","flatbed","plane","pritsche")):
        if token not in tokens: tokens.append(token)

# Fallback candidates if validator does not enumerate values.
fallback=["curtainsider","flatbed","flatbed_tarpaulin","platform","tarpaulin","pritsche_plane"]
for x in fallback:
    if x not in tokens: tokens.append(x)

print("candidate body_type values:",tokens[:12])
print()

best=None
tested=0
for bt in tokens[:12]:
    q=dict(base); q["body_type"]=bt
    _,ans=call("search",q)
    if not ans.get("ok"):
        e=ans.get("error") or {}
        if (e.get("code") or "")=="INVALID_PARAM":
            continue
        print("ERROR",bt,json.dumps(e,ensure_ascii=False))
        continue
    tested+=1
    d=ans.get("data") or {}
    total=d.get("total_results")
    print("VALID",bt,"total_results:",total,"has_more:",d.get("has_more"))
    if isinstance(total,int):
        delta=abs(total-241)
        if best is None or delta<best[0]:
            best=(delta,bt,total)
    if tested>=4:
        break

print()
if best:
    print("BEST_MATCH body_type:",best[1],"total_results:",best[2],"delta_vs_241:",best[0])
else:
    print("No valid body_type candidate found automatically.")
    print("Next fallback is query-based pagination, but do not use it for analytics until coverage is calibrated.")
