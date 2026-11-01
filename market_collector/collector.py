from __future__ import annotations

import argparse, hashlib, json, os, re, time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from index_adapter import discover_index_pages

UA = "SHM-Market-Collector/0.1"
VIN_RE = re.compile(r"(?<![A-Z0-9])([A-HJ-NPR-Z0-9]{17})(?![A-Z0-9])", re.I)
VIN_LABEL_RE = re.compile(r"\b(?:VIN|FIN|chassis(?:\s*(?:no|nr|number))?)\s*[:#-]?\s*([A-Z0-9-]{6,20})\b", re.I)
YEAR_RE = re.compile(r"(?<!\\d)(20(?:0[8-9]|1\\d|2[01]))(?!\\d)")
PRICE_RE = re.compile(r"(?:€|EUR\\s*)\\s*([0-9]{1,3}(?:[.\\s][0-9]{3})*(?:,[0-9]{1,2})?|[0-9]{4,6})", re.I)
BRANDS = {
    "Kögel": re.compile(r"\\b(?:KÖGEL|KOEGEL|KOGEL)\\b", re.I),
    "Krone": re.compile(r"\\bKRONE\\b", re.I),
    "Schmitz Cargobull": re.compile(r"\\b(?:SCHMITZ(?:\\s+CARGOBULL)?|CARGOBULL)\\b", re.I),
    "Schwarzmüller": re.compile(r"\\b(?:SCHWARZM[ÜU]LLER|SCHWARZMUELLER)\\b", re.I),
}
FEATURES = {
    "saf": re.compile(r"\\bSAF\\b", re.I),
    "bpw": re.compile(r"\\bBPW\\b", re.I),
    "rotos": re.compile(r"\\bROTOS\\b", re.I),
    "lift_axle": re.compile(r"\\b(?:lift\\s*axle|liftachse|essieu\\s+relevable|oś\\s+podnoszona)\\b", re.I),
    "pallet_box": re.compile(r"\\b(?:pallet\\s*box|palletbox|palettenkasten|palletkist|skrzynia\\s+paletowa)\\b", re.I),
    "code_xl": re.compile(r"\\b(?:code\\s*XL|DIN\\s*EN\\s*12642)\\b", re.I),
    "mega": re.compile(r"\\bMEGA\\b", re.I),
    "coil": re.compile(r"\\bCOIL\\b", re.I),
    "joloda": re.compile(r"\\bJOLODA\\b", re.I),
    "huckepack": re.compile(r"\\b(?:HUCKEPACK|P400)\\b", re.I),
}

def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")

def clean(s):
    return re.sub(r"\\s+", " ", s or "").strip()

def hash_text(s):
    return hashlib.sha256(s.encode("utf-8", errors="replace")).hexdigest()

def flatten(x):
    out=[]
    def walk(v):
        if isinstance(v, dict):
            for k,z in v.items(): out.append(str(k)); walk(z)
        elif isinstance(v, list):
            for z in v: walk(z)
        elif v is not None: out.append(str(v))
    walk(x)
    return " ".join(out)

def brand_of(text):
    return next((b for b,r in BRANDS.items() if r.search(text)), None)

def vins_of(text):
    return sorted({m.group(1).upper() for m in VIN_RE.finditer(text)})

def vin_refs_of(text):
    refs=[]
    for m in VIN_LABEL_RE.finditer(text):
        v=m.group(1).upper().strip("-")
        if 6 <= len(v) <= 20:
            refs.append(v)
    return sorted(set(refs))

def price_of(text):
    for m in PRICE_RE.finditer(text):
        raw=m.group(1).replace(" ","")
        if "." in raw and "," not in raw: raw=raw.replace(".","")
        raw=raw.replace(",",".")
        try: v=float(raw)
        except ValueError: continue
        if 1000 <= v <= 500000: return v
    return None

def tax_of(text):
    t=text.lower()
    if any(x in t for x in ["excl. vat","zzgl. mwst","plus vat","netto","net price","hors taxe"]): return "net"
    if any(x in t for x in ["incl. vat","inkl. mwst","brutto"]): return "gross"
    return None

def html_record(source,url,html):
    soup=BeautifulSoup(html,"html.parser")
    title=clean(soup.title.get_text(" ",strip=True) if soup.title else "")
    docs=[]
    for tag in soup.find_all("script",attrs={"type":"application/ld+json"}):
        try: docs.append(json.loads(tag.string or tag.get_text(" ",strip=True)))
        except Exception: pass
    text=clean(" ".join([title,soup.get_text(" ",strip=True),flatten(docs)]))
    brand=brand_of(text)
    years=sorted({int(y) for y in YEAR_RE.findall(text)})
    years=[y for y in years if 2008 <= y <= 2021]
    if not brand or not years: return None
    cy=None
    m=re.search(r"(?:construction year|baujahr|year of manufacture|rok produkcji)\\s*[:\\-]?\\s*(20\\d{2})",text,re.I)
    if m: cy=int(m.group(1))
    else: cy=years[0]
    fr=None
    m=re.search(r"(?:first registration|initial registration|erstzulassung|première immatriculation)\\s*[:\\-]?\\s*(?:\\d{1,2}[./-])?(?:\\d{1,2}[./-])?(20\\d{2})",text,re.I)
    if m: fr=int(m.group(1))
    vins=vins_of(text)
    f={k:bool(rx.search(text)) for k,rx in FEATURES.items()}
    axle="SAF" if f["saf"] else "BPW" if f["bpw"] else "Schmitz ROTOS" if f["rotos"] else None
    stock=None
    m=re.search(r"(?:Info[- ]?no\\.?|Info[- ]?Nr\\.?|stock\\s*(?:no|nr)\\.?)\\s*[:#]?\\s*([A-Z0-9._/-]{3,40})",text,re.I)
    if m: stock=m.group(1)
    if not stock:
        ds=re.findall(r"(?<!\\d)(\\d{6,10})(?!\\d)",url)
        stock=ds[-1] if ds else None
    return {
        "source":source,"source_listing_id":stock,"url":url,"observed_at":now(),
        "title":title or None,"brand":brand,"construction_year":cy,"first_registration_year":fr,
        "vin":vins[0] if len(vins)==1 else None,"vin_candidates":vins,"vin_refs":vin_refs_of(text),
        "price_amount":price_of(text),"price_currency":"EUR" if re.search(r"€|\\bEUR\\b",text,re.I) else None,
        "tax_basis":tax_of(text),"axle_maker":axle,
        "lift_axle":True if f["lift_axle"] else None,"pallet_box":True if f["pallet_box"] else None,
        "code_xl":True if f["code_xl"] else None,"mega":True if f["mega"] else None,
        "coil":True if f["coil"] else None,"joloda":True if f["joloda"] else None,
        "huckepack":True if f["huckepack"] else None,
        "raw_hash":hash_text(html),"evidence_excerpt":text[:2000]
    }

class BrowserFetcher:
    def __init__(self):
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.launch(headless=True)
        self.context = self.browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/150 Safari/537.36',
            locale='de-DE',
            viewport={'width': 1440, 'height': 1000},
        )

    def get_html(self, url):
        page = self.context.new_page()
        try:
            resp = page.goto(url, wait_until='domcontentloaded', timeout=30000)
            status = resp.status if resp else None
            if status in (401, 403, 429):
                return status, None, page.url
            body = (page.locator('body').inner_text(timeout=5000) or '')[:3000].lower()
            if any(x in body for x in ['captcha', 'verify you are human', 'access denied', 'cloudflare challenge']):
                return 403, None, page.url
            page.wait_for_timeout(1200)
            return status or 200, page.content(), page.url
        finally:
            page.close()

    def close(self):
        try:
            self.context.close()
            self.browser.close()
            self._pw.stop()
        except Exception:
            pass

class Http:
    def __init__(self):
        self.s=requests.Session()
        self.s.headers.update({"User-Agent":UA,"Accept-Language":"en,de;q=0.8"})
        self.browser=None
    def get(self,url,**kw):
        return self.s.get(url,timeout=25,allow_redirects=True,**kw)
    def browser_html(self,url):
        if self.browser is None:
            self.browser=BrowserFetcher()
        return self.browser.get_html(url)
    def close(self):
        if self.browser:
            self.browser.close()

def fetch_html(http,url):
    r=http.get(url)
    if r.status_code==200:
        return 200,r.text,r.url,'http'
    if r.status_code in (401,403,429):
        status,html,final_url=http.browser_html(url)
        if html:
            return status or 200,html,final_url,'browser'
        return status or r.status_code,None,final_url,'browser_blocked'
    return r.status_code,None,r.url,'http'

def sitemap_locs(xml):
    root=ET.fromstring(xml)
    kind="index" if root.tag.lower().endswith("sitemapindex") else "urlset"
    return kind,[e.text.strip() for e in root.iter() if e.tag.lower().endswith("loc") and e.text]

def collect_sitemap(http,src,rows,events):
    queue=list(src.get("sitemaps",[])); seen=set(); pages=[]
    limit=int(src.get("max_pages_per_run",400)); allow=set(src.get("allow_hosts",[])); inc=[x.lower() for x in src.get("url_include",[])]
    while queue and len(pages)<limit:
        sm=queue.pop(0)
        if sm in seen: continue
        seen.add(sm)
        try:
            r=http.get(sm)
            if r.status_code!=200:
                events.append({"source":src["name"],"url":sm,"observed_at":now(),"status":"http_error","http_status":r.status_code}); continue
            kind,locs=sitemap_locs(r.text)
            if kind=="index": queue += [u for u in locs if u not in seen][:100]
            else:
                for u in locs:
                    if allow and (urlparse(u).hostname or "") not in allow: continue
                    low=u.lower()
                    if inc and not any(x in low for x in inc) and not re.search(r"\\d{6,10}\\.html(?:$|\\?)",low): continue
                    pages.append(u)
                    if len(pages)>=limit: break
        except Exception as e:
            events.append({"source":src["name"],"url":sm,"observed_at":now(),"status":"fetch_error","error":str(e)[:500]})
    for i,u in enumerate(dict.fromkeys(pages),1):
        try:
            status,html,final_url,mode=fetch_html(http,u)
            if status!=200 or not html:
                events.append({"source":src["name"],"url":u,"observed_at":now(),"status":"http_error","http_status":status,"mode":mode}); continue
            rec=html_record(src["name"],final_url,html)
            if rec: rows.append(rec)
        except Exception as e:
            events.append({"source":src["name"],"url":u,"observed_at":now(),"status":"fetch_error","error":str(e)[:500]})
        if i%40==0: time.sleep(.5)

def collect_index_cards(http,src,rows,events):
    from urllib.parse import urljoin, urlparse
    before=len(rows)
    queue=list(src.get("seed_pages") or [])
    seen=set()
    max_pages=int(src.get("max_index_pages",20))
    detail_rx=re.compile(src.get("detail_url_regex"), re.I)
    index_tokens=[x.lower() for x in src.get("index_url_tokens") or []]
    allow=set(src.get("allow_hosts") or [])
    card_seen=set()
    detail_anchor_count=0
    href_samples=[]

    while queue and len(seen)<max_pages:
        url=queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        try:
            if src.get("force_browser"):
                status,html,final_url=http.browser_html(url)
                mode="browser"
            else:
                status,html,final_url,mode=fetch_html(http,url)
            if status!=200 or not html:
                events.append({"source":src["name"],"url":url,"observed_at":now(),"status":"http_error","http_status":status,"mode":mode})
                continue

            soup=BeautifulSoup(html,"html.parser")
            anchors=soup.find_all("a",href=True)
            for a in anchors:
                full=urljoin(final_url,a["href"])
                host=urlparse(full).hostname or ""
                if allow and host not in allow:
                    continue

                if detail_rx.search(full):
                    detail_anchor_count += 1
                    if len(href_samples) < 20:
                        href_samples.append(full)
                    key=full.split("?")[0]
                    if key in card_seen:
                        continue
                    node=a
                    best=None
                    for _ in range(7):
                        if node is None:
                            break
                        txt=clean(node.get_text(" ",strip=True))
                        if 120 <= len(txt) <= 7000 and brand_of(txt) and YEAR_RE.search(txt):
                            best=node
                        node=node.parent
                    if best is not None:
                        rec=html_record(src["name"],key,str(best))
                        if rec:
                            rec["url"]=key
                            rows.append(rec)
                            card_seen.add(key)
                    continue

                low=full.lower()
                if index_tokens and any(t in low for t in index_tokens) and full not in seen and full not in queue:
                    queue.append(full)

        except Exception as e:
            events.append({"source":src["name"],"url":url,"observed_at":now(),"status":"fetch_error","error":str(e)[:500]})

    events.append({
        "source":src["name"],"url":None,"observed_at":now(),"status":"source_summary",
        "index_pages":len(seen),"cards_added":len(rows)-before,
        "detail_anchor_count":detail_anchor_count,"href_samples":href_samples
    })

def collect_index(http,src,rows,events):
    before=len(rows)
    pages=discover_index_pages(http,src,events,now)
    events.append({"source":src["name"],"url":None,"observed_at":now(),"status":"discovery_summary","detail_urls":len(pages)})
    for i,u in enumerate(pages,1):
        try:
            status,html,final_url,mode=fetch_html(http,u)
            if status!=200 or not html:
                events.append({"source":src["name"],"url":u,"observed_at":now(),"status":"http_error","http_status":status,"mode":mode}); continue
            rec=html_record(src["name"],final_url,html)
            if rec:
                rows.append(rec)
            else:
                sample=clean(BeautifulSoup(html,"html.parser").get_text(" ",strip=True))[:1800]
                events.append({"source":src["name"],"url":final_url,"observed_at":now(),"status":"detail_not_relevant_or_unparsed","mode":mode,"text_sample":sample})
        except Exception as e:
            events.append({"source":src["name"],"url":u,"observed_at":now(),"status":"fetch_error","error":str(e)[:500]})
        if i%40==0: time.sleep(.5)
    events.append({"source":src["name"],"url":None,"observed_at":now(),"status":"source_summary","detail_urls":len(pages),"cards_added":len(rows)-before})

def deep(obj,names):
    out=[]
    if isinstance(obj,dict):
        for k,v in obj.items():
            if k.lower() in names: out.append(v)
            out += deep(v,names)
    elif isinstance(obj,list):
        for v in obj: out += deep(v,names)
    return out

def mobile_record(source,key,ad):
    raw=json.dumps(ad,ensure_ascii=False,sort_keys=True); text=clean(flatten(ad))
    brand=brand_of(text); years=sorted({int(y) for y in YEAR_RE.findall(text) if 2008<=int(y)<=2021})
    if not brand or not years: return None
    cy=None
    for v in deep(ad,{"constructionyear","construction_year","year"}):
        try:
            y=int(str(v)[:4])
            if 2008<=y<=2021: cy=y; break
        except Exception: pass
    cy=cy or years[0]
    vins=vins_of(text); f={k:bool(rx.search(text)) for k,rx in FEATURES.items()}
    axle="SAF" if f["saf"] else "BPW" if f["bpw"] else "Schmitz ROTOS" if f["rotos"] else None
    prices=[]
    for v in deep(ad,{"consumerpriceamount","amount","price"}):
        try:
            x=float(v)
            if 1000<=x<=500000: prices.append(x)
        except Exception: pass
    return {
        "source":source,"source_listing_id":str(key),"url":f"https://suchen.mobile.de/fahrzeuge/details.html?id={key}",
        "observed_at":now(),"title":str((deep(ad,{"headline","title","modeldescription"}) or [None])[0]),
        "brand":brand,"construction_year":cy,"first_registration_year":None,
        "vin":vins[0] if len(vins)==1 else None,"vin_candidates":vins,"vin_refs":vin_refs_of(text),
        "price_amount":prices[0] if prices else None,"price_currency":"EUR","tax_basis":None,"axle_maker":axle,
        "lift_axle":True if f["lift_axle"] else None,"pallet_box":True if f["pallet_box"] else None,
        "code_xl":True if f["code_xl"] else None,"mega":True if f["mega"] else None,
        "coil":True if f["coil"] else None,"joloda":True if f["joloda"] else None,
        "huckepack":True if f["huckepack"] else None,"raw_hash":hash_text(raw),"evidence_excerpt":text[:2000]
    }

def collect_mobile(http,cfg,src,rows,events):
    user=os.getenv("MOBILEDE_USERNAME",""); pwd=os.getenv("MOBILEDE_PASSWORD","")
    if not user or not pwd:
        events.append({"source":src["name"],"url":"https://services.mobile.de/search-api/search","observed_at":now(),"status":"not_configured"}); return
    hist=[y for y in range(cfg["years"]["min"],cfg["years"]["max"]+1) if y not in cfg["years"].get("priority",[2021])]
    rotate=hist[datetime.now(timezone.utc).timetuple().tm_yday % len(hist)] if hist else None
    years=cfg["years"].get("priority",[2021])+([rotate] if rotate else [])
    headers={"Accept":"application/vnd.de.mobile.api+json","Accept-Language":"en"}; auth=(user,pwd); cap=int(src.get("max_ads_per_run",700)); n=0
    for country in src.get("countries",["DE"]):
      for brand in cfg["brands"]:
       for year in years:
        if n>=cap:return
        params={"classification":"refdata/classes/SemiTrailer","modelDescription":brand,"country":country,"constructionYear.min":year,"constructionYear.max":year,"page.size":min(100,src.get("page_size",100)),"page.number":1,"sort.field":"modificationTime","sort.order":"DESCENDING"}
        try:
            r=http.s.get("https://services.mobile.de/search-api/search",params=params,auth=auth,headers=headers,timeout=30)
            if r.status_code!=200:
                events.append({"source":src["name"],"url":r.url,"observed_at":now(),"status":"http_error","http_status":r.status_code}); continue
            ads=r.json().get("ads") or []
        except Exception as e:
            events.append({"source":src["name"],"url":"https://services.mobile.de/search-api/search","observed_at":now(),"status":"fetch_error","error":str(e)[:500]}); continue
        for ad in ads:
            if n>=cap:return
            key=ad.get("key") or ad.get("id") or ad.get("adKey")
            if not key: continue
            detail=ad
            try:
                d=http.s.get(f"https://services.mobile.de/search-api/ad/{key}",auth=auth,headers=headers,timeout=30)
                if d.status_code==200: detail=d.json()
            except Exception: pass
            rec=mobile_record(src["name"],key,detail)
            if rec: rows.append(rec); n+=1

def write_ndjson(path,rows):
    with path.open("w",encoding="utf-8") as f:
        for r in rows:f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+"\\n")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--config",required=True); ap.add_argument("--out",required=True); a=ap.parse_args()
    cfg=json.loads(Path(a.config).read_text(encoding="utf-8")); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    http=Http(); rows=[]; events=[]; started=now()
    runner_kind=os.getenv("SHM_RUNNER_KIND","local")
    for src in cfg["sources"]:
        if runner_kind=="github" and src.get("github_enabled") is False:
            events.append({"source":src["name"],"url":None,"observed_at":now(),"status":"skipped_on_github_runner"})
            continue
        if src["type"]=="sitemap": collect_sitemap(http,src,rows,events)
        elif src["type"]=="crawl_index": collect_index(http,src,rows,events)
        elif src["type"]=="index_cards": collect_index_cards(http,src,rows,events)
        elif src["type"]=="mobile_api": collect_mobile(http,cfg,src,rows,events)
    dedup={(r["source"],r.get("source_listing_id") or r["url"]):r for r in rows}; rows=list(dedup.values())
    summary={"started_at":started,"finished_at":now(),"listings":len(rows),"vin_found":sum(bool(r["vin_candidates"]) for r in rows),"by_brand":{b:sum(r["brand"]==b for r in rows) for b in cfg["brands"]},"access_events":len(events)}
    write_ndjson(out/"listings.ndjson",rows); write_ndjson(out/"access_events.ndjson",events)
    url=os.getenv("SHM_INGEST_URL",""); token=os.getenv("SHM_INGEST_TOKEN","")
    if url and token:
        try:
            q=requests.post(url,json={"schema_version":1,"summary":summary,"listings":rows,"access_events":events},headers={"Authorization":f"Bearer {token}","User-Agent":UA},timeout=60)
            summary["ingest"]={"configured":True,"ok":q.ok,"status_code":q.status_code,"response":q.text[:500]}
        except Exception as e: summary["ingest"]={"configured":True,"ok":False,"error":str(e)[:500]}
    else: summary["ingest"]={"configured":False}
    (out/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2,sort_keys=True)+"\\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    http.close()

if __name__=="__main__": main()
