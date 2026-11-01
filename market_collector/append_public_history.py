import json
from pathlib import Path

SNAPSHOT=Path("data/latest_market.json")
HISTORY=Path("data/public_observations.ndjson")

if not SNAPSHOT.exists():
    raise SystemExit(0)

data=json.loads(SNAPSHOT.read_text(encoding="utf-8"))
existing=set()
if HISTORY.exists():
    for line in HISTORY.read_text(encoding="utf-8").splitlines():
        try:
            r=json.loads(line)
            existing.add((r.get("source"),r.get("url"),r.get("observed_at"),r.get("price_original")))
        except Exception:
            pass

new=[]
for x in data.get("listings",[]):
    key=(x.get("source"),x.get("url"),x.get("observed_at"),x.get("price_original"))
    if key in existing:
        continue
    new.append({
        "source":x.get("source"),
        "url":x.get("url"),
        "observed_at":x.get("observed_at"),
        "brand":x.get("brand"),
        "model":x.get("model"),
        "year":x.get("year"),
        "country":x.get("country"),
        "price_original":x.get("price_original"),
        "currency":x.get("currency"),
        "tax_basis":x.get("tax_basis"),
        "vin":x.get("vin"),
        "vin_ref":x.get("vin_ref"),
    })

if new:
    HISTORY.parent.mkdir(parents=True,exist_ok=True)
    with HISTORY.open("a",encoding="utf-8") as f:
        for r in new:
            f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+"\n")
print(json.dumps({"history_appended":len(new)},ensure_ascii=False))
