from __future__ import annotations
import os, re, json, requests, sys

user=os.getenv("MOBILEDE_USERNAME","").strip()
pwd=os.getenv("MOBILEDE_PASSWORD","").strip()
if not user or not pwd:
    print("MOBILEDE_CREDENTIALS: NOT_CONFIGURED")
    raise SystemExit(2)

H={"Accept":"application/vnd.de.mobile.api+json","Accept-Language":"de"}

# Refdata does not require auth.
makes_url="https://services.mobile.de/refdata/classes/SemiTrailer/makes"
r=requests.get(makes_url,headers=H,timeout=20)
print("REFDATA_STATUS:",r.status_code)
if r.status_code!=200:
    print(r.text[:500])
    raise SystemExit(3)

body=r.json()
vals=body.get("values") or []
def norm(s):
    s=str(s or "").lower()
    for a,b in (("ä","ae"),("ö","oe"),("ü","ue"),("ß","ss")): s=s.replace(a,b)
    return re.sub(r"[^a-z0-9]+","",s)

kogel=None
for m in vals:
    if not isinstance(m,dict): continue
    key=m.get("name") or m.get("key") or m.get("id") or m.get("value")
    desc=m.get("description") or m.get("label") or key
    if norm(key) in {"koegel","kogel"} or norm(desc) in {"koegel","kogel"}:
        kogel=str(key); break
print("KOEGEL_MAKE_KEY:",kogel or "NOT_FOUND")
if not kogel:
    raise SystemExit(4)

params={
  "classification":f"refdata/classes/SemiTrailer/makes/{kogel}",
  "firstRegistrationDate.min":"2008-01",
  "firstRegistrationDate.max":"2022-12",
  "page.size":1,
  "page.number":1
}
url="https://services.mobile.de/search-api/search"
s=requests.get(url,params=params,auth=(user,pwd),headers=H,timeout=30)
print("SEARCH_STATUS:",s.status_code)
if s.status_code==200:
    d=s.json()
    print("TOTAL:",d.get("total"))
    print("MAX_PAGES:",d.get("maxPages"))
    print("ACCESS: OK")
else:
    print("ACCESS: DENIED_OR_NOT_ENABLED")
    print("RESPONSE:",s.text[:800])
