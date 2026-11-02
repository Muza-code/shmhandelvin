from __future__ import annotations
import json, os, requests

KEY=os.getenv("REEF_API_KEY","").strip()
if not KEY:
    raise SystemExit("REEF_API_KEY missing")

URL="https://api.reefapi.com/mobile-de/v1/search"
H={"x-api-key":KEY,"content-type":"application/json","User-Agent":"SHM-Coverage-Probe-V2/1.0"}

TARGET=241
variants=[]

base_common={"year_min":2008,"year_max":2022,"page":1,"page_size":100,"language":"de"}

for vehicle_type in ("truck",None):
    for key,value in [
        ("query","Kögel"),
        ("query","Koegel"),
        ("query","Kogel"),
        ("query","Kögel Sattelauflieger"),
        ("query","Kögel Pritsche Plane"),
        ("query","Kögel Auflieger"),
        ("make","Kögel"),
        ("make","Koegel"),
        ("make","Kogel"),
    ]:
        p=dict(base_common)
        if vehicle_type:
            p["vehicle_type"]=vehicle_type
        p[key]=value
        variants.append((vehicle_type,key,value,p))

seen=set()
results=[]
for vehicle_type,key,value,payload in variants:
    sig=json.dumps(payload,sort_keys=True,ensure_ascii=False)
    if sig in seen: continue
    seen.add(sig)
    try:
        r=requests.post(URL,headers=H,json=payload,timeout=30)
        body=r.json()
    except Exception as e:
        print("ERROR",vehicle_type,key,value,str(e))
        continue
    if not body.get("ok"):
        err=body.get("error") or {}
        print("INVALID",vehicle_type,key,value,err.get("code"),err.get("message"))
        continue
    d=body.get("data") or {}
    total=d.get("total_results")
    count=d.get("count") or len(d.get("results") or d.get("listings") or d.get("items") or [])
    applied=d.get("filters_applied")
    delta=abs(total-TARGET) if isinstance(total,int) else 999999
    results.append((delta,total,count,vehicle_type,key,value,applied))
    print("VALID",f"vehicle_type={vehicle_type}",f"{key}={value!r}","total=",total,"count=",count,"delta=",delta,"filters=",applied)

print()
print("TOP MATCHES")
for row in sorted(results,key=lambda x:x[0])[:10]:
    delta,total,count,vehicle_type,key,value,applied=row
    print(json.dumps({
        "total_results":total,
        "delta_vs_241":delta,
        "vehicle_type":vehicle_type,
        "filter":key,
        "value":value,
        "count_page1":count,
        "filters_applied":applied
    },ensure_ascii=False))
