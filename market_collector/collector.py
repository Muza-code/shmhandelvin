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
VIN_LABEL_RE = re.compile(r"\b(?:VIN|FIN|chassis(?:\s*(?:no|nr|number))?)\b\s*(?:[:#-]\s*|\s+)([A-Z0-9-]{6,20})\b", re.I)
YEAR_RE = re.compile(r"(?<!\d)(20(?:0[8-9]|1\d|2[01]))(?!\d)")
PRICE_RE = re.compile(r"(?:€|EUR)\s*([0-9][0-9.,\s\u00a0\u202f]{2,14})", re.I)
PRICE_AFTER_RE = re.compile(r"([0-9][0-9.,\s\u00a0\u202f]{2,14})\s*(?:EUR|€)", re.I)
BRANDS = {
    "Kögel": re.compile(r"\b(?:KÖGEL|KOEGEL|KOGEL)\b", re.I),
    "Krone": re.compile(r"\bKRONE\b", re.I),
    "Schmitz Cargobull": re.compile(r"\b(?:SCHMITZ(?:\s+CARGOBULL)?|CARGOBULL)\b", re.I),
    "Schwarzmüller": re.compile(r"\b(?:SCHWARZM[ÜU]LLER|SCHWARZMUELLER)\b", re.I),
}
BODY_TYPES = [
    ("curtainsider", re.compile(r"curtain|tautliner|pritsche.?plane|plane|schiebeplane|open semitrailer with tarp", re.I)),
    ("reefer", re.compile(r"reefer|refrigerat|freezer|k[üu]hl|frigo", re.I)),
    ("box", re.compile(r"box semi|closed box|koffer", re.I)),
    ("tipper", re.compile(r"tipper|kipper|dump|kipp", re.I)),
    ("container_chassis", re.compile(r"container chassis|containerchassis|bdf|port 45|20ft|30ft|40ft|45ft", re.I)),
    ("flatbed_platform", re.compile(r"flatbed|platform|plattform|pritsche(?!.?plane)", re.I)),
    ("walking_floor", re.compile(r"walking floor|schubboden|moving floor", re.I)),
    ("low_loader", re.compile(r"low loader|deeploader|tieflader|semi deeploader", re.I)),
    ("tanker_silo", re.compile(r"tank|silo", re.I)),
    ("timber", re.compile(r"timber|log transport|holztransport", re.I)),
]

def body_type_of(text):
    for name,rx in BODY_TYPES:
        if rx.search(text or ""):
            return name
    return "other"

def asset_type_of(text):
    t=text or ""
    if re.search(r"swap\s*body|wechselbr[üu]cke|wechselbruecke",t,re.I):
        return "swap_body"
    if re.search(r"drawbar\s*trailer|central\s*axle|tandem\s*trailer|anh[äa]nger(?!.*auflieger)",t,re.I):
        return "trailer"
    return "semi_trailer"

COUNTRY_NAMES = {
    "Germany":"DE","Netherlands":"NL","Belgium":"BE","France":"FR","Spain":"ES",
    "Italy":"IT","Poland":"PL","Lithuania":"LT","Latvia":"LV","Estonia":"EE",
    "Austria":"AT","Czech Republic":"CZ","Hungary":"HU","Croatia":"HR",
    "Portugal":"PT","Denmark":"DK","Sweden":"SE","Norway":"NO","Finland":"FI",
    "Slovakia":"SK","Slovenia":"SI","Romania":"RO","Bulgaria":"BG"
}

FEATURES = {
    "saf": re.compile(r"\bSAF\b", re.I),
    "bpw": re.compile(r"\bBPW\b", re.I),
    "rotos": re.compile(r"\bROTOS\b", re.I),
    "lift_axle": re.compile(r"\b(?:lift\s*axle|liftachse|essieu\s+relevable|oś\s+podnoszona)\b", re.I),
    "pallet_box": re.compile(r"\b(?:pallet\s*box|palletbox|palettenkasten|palletkist|skrzynia\s+paletowa)\b", re.I),
    "code_xl": re.compile(r"\b(?:code\s*XL|DIN\s*EN\s*12642)\b", re.I),
    "mega": re.compile(r"\bMEGA\b", re.I),
    "coil": re.compile(r"\bCOIL\b", re.I),
    "joloda": re.compile(r"\bJOLODA\b", re.I),
    "huckepack": re.compile(r"\b(?:HUCKEPACK|P400)\b", re.I),
}

def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")

def clean(s):
    return re.sub(r"\s+", " ", s or "").strip()

def hash_text(s):
    return hashlib.sha256(s.encode("utf-8", errors="replace")).hexdigest()

def seller_from_jsonld(docs):
    names=[]
    def walk(v):
        if isinstance(v,dict):
            for k,z in v.items():
                if k.lower() in {"seller","dealer","vendor"} and isinstance(z,dict):
                    n=z.get("name")
                    if isinstance(n,str) and 2<=len(n.strip())<=120:
                        names.append(n.strip())
                walk(z)
        elif isinstance(v,list):
            for z in v: walk(z)
    walk(docs)
    return names[0] if names else None

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
    vals=set()
    for m in VIN_RE.finditer(text):
        v=m.group(1).upper()
        if "XXX" in v:
            continue
        if not any(ch.isdigit() for ch in v):
            continue
        vals.add(v)
    return sorted(vals)

def vin_refs_of(text):
    refs=[]
    for m in VIN_LABEL_RE.finditer(text):
        v=m.group(1).upper().strip("-")
        if not (6 <= len(v) <= 20):
            continue
        if not any(ch.isdigit() for ch in v):
            continue
        if v in {"000000","0000000","00000000"}:
            continue
        refs.append(v)
    return sorted(set(refs))

def price_of(text):
    matches=[]
    for rx in (PRICE_RE,PRICE_AFTER_RE):
        for m in rx.finditer(text or ""):
            matches.append((m.start(),m.group(1)))
    matches.sort(key=lambda z:z[0])
    for _,candidate in matches:
        raw=re.sub(r"[\s\u00a0\u202f]+","",candidate)
        raw=re.sub(r"[^0-9.,]","",raw)
        if not raw:
            continue
        # European/English marketplace prices commonly use . or , as thousands separators.
        if "," in raw and "." in raw:
            last=max(raw.rfind(","),raw.rfind("."))
            decimals=len(raw)-last-1
            if decimals in (1,2):
                raw=raw[:last].replace(",","").replace(".","")+"."+raw[last+1:]
            else:
                raw=raw.replace(",","").replace(".","")
        elif "," in raw:
            tail=len(raw)-raw.rfind(",")-1
            raw=raw.replace(",","") if tail==3 else raw.replace(",",".")
        elif "." in raw:
            tail=len(raw)-raw.rfind(".")-1
            raw=raw.replace(".","") if tail==3 else raw
        try: v=float(raw)
        except ValueError: continue
        if 1000 <= v <= 500000:
            return v
    return None

def tax_of(text):
    t=text.lower()
    if any(x in t for x in ["excl. vat","ex. vat","ex vat","zzgl. mwst","plus vat","netto","net price","hors taxe"]): return "net"
    if any(x in t for x in ["incl. vat","inkl. mwst","brutto"]): return "gross"
    return None

def html_record(source,url,html):
    soup=BeautifulSoup(html,"html.parser")
    title=clean(soup.title.get_text(" ",strip=True) if soup.title else "")
    if not title:
        h=soup.find(["h1","h2","h3","h4"])
        if h:
            title=clean(h.get_text(" ",strip=True))
    docs=[]
    for tag in soup.find_all("script",attrs={"type":"application/ld+json"}):
        try: docs.append(json.loads(tag.string or tag.get_text(" ",strip=True)))
        except Exception: pass
    alts=" ".join(clean(img.get("alt","")) for img in soup.find_all("img") if img.get("alt"))
    text=clean(" ".join([title,alts,soup.get_text(" ",strip=True),flatten(docs)]))
    url_text=url.replace("-", " ").replace("_", " ")
    brand=brand_of(url_text) or brand_of(text)
    if not brand:
        return None

    cy=None
    construction_patterns=[
        r"(?:construction year|year of construction|baujahr|year of manufacture|body construction year|body year|rok produkcji)\s*[:\-]?\s*(20\d{2})",
        r"(?:manufactured|manufacturing year)\s*[:\-]?\s*(20\d{2})",
    ]
    for pat in construction_patterns:
        m=re.search(pat,text,re.I)
        if m:
            y=int(m.group(1))
            if 2008 <= y <= 2021:
                cy=y
                break

    fr=None
    m=re.search(r"(?:first registration|initial registration|erstzulassung|première immatriculation|date of first registration)\s*[:\-]?\s*(?:\d{1,2}[./-])?(?:\d{1,2}[./-])?(20\d{2})",text,re.I)
    if m:
        y=int(m.group(1))
        if 2008 <= y <= 2021:
            fr=y

    url_years=sorted({int(y) for y in YEAR_RE.findall(url_text)})
    url_years=[y for y in url_years if 2008 <= y <= 2021]
    source_year=url_years[0] if url_years else None

    if cy is not None:
        market_year=cy
        year_basis="construction_year"
    elif source_year is not None:
        market_year=source_year
        year_basis="source_url_year"
    elif fr is not None:
        market_year=fr
        year_basis="first_registration_proxy"
    else:
        return None
    vins=vins_of(text)
    f={k:bool(rx.search(text)) for k,rx in FEATURES.items()}
    axle="SAF" if f["saf"] else "BPW" if f["bpw"] else "Schmitz ROTOS" if f["rotos"] else None
    body_type=body_type_of(" ".join([title,text]))
    asset_type=asset_type_of(" ".join([title,text]))
    stock=None
    m=re.search(r"(?:Info[- ]?no\.?|Info[- ]?Nr\.?|stock\s*(?:no|nr)\.?)\s*[:#]?\s*([A-Z0-9._/-]{3,40})",text,re.I)
    if m: stock=m.group(1)
    if not stock:
        ds=re.findall(r"(?<!\d)(\d{6,10})(?!\d)",url)
        stock=ds[-1] if ds else None
    seller=seller_from_jsonld(docs)
    if not seller:
        ms=re.search(r"([A-ZÀ-Ž0-9][A-Za-zÀ-ž0-9&.,'()\- ]{2,90}?)\s+Seller\s+for\s+\d+\s+(?:year|years|month|months)",text,re.I)
        if ms:
            seller=clean(ms.group(1))
    country=None
    for name,code in COUNTRY_NAMES.items():
        if re.search(r"\b"+re.escape(name)+r"\b",text,re.I):
            country=code
            break
    return {
        "source":source,"source_listing_id":stock,"url":url,"observed_at":now(),
        "title":title or None,"brand":brand,"construction_year":cy,"first_registration_year":fr,
        "market_year":market_year,"year_basis":year_basis,"source_year":source_year,"country":country,
        "vin":vins[0] if len(vins)==1 else None,"vin_candidates":vins,"vin_refs":vin_refs_of(text),
        "price_amount":price_of(text),"price_currency":"EUR" if re.search(r"€|\bEUR\b",text,re.I) else None,
        "tax_basis":tax_of(text),"axle_maker":axle,"body_type":body_type,
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
            resp = page.goto(url, wait_until='domcontentloaded', timeout=12000)
            status = resp.status if resp else None
            if status in (401, 403, 429):
                return status, None, page.url
            body = (page.locator('body').inner_text(timeout=5000) or '')[:3000].lower()
            if any(x in body for x in ['captcha', 'verify you are human', 'access denied', 'cloudflare challenge']):
                return 403, None, page.url
            page.wait_for_timeout(400)
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
    if r.status_code in (202,401,403,429):
        status,html,final_url=http.browser_html(url)
        if html:
            return 200,html,final_url,'browser'
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
                    if inc and not any(x in low for x in inc) and not re.search(r"\d{6,10}\.html(?:$|\?)",low): continue
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
                    candidates=[]
                    for depth in range(10):
                        if node is None:
                            break
                        txt=clean(node.get_text(" ",strip=True))
                        try:
                            detail_urls={
                                urljoin(final_url,z.get("href","")).split("?")[0]
                                for z in node.find_all("a",href=True)
                                if detail_rx.search(urljoin(final_url,z.get("href","")))
                            }
                        except Exception:
                            detail_urls=set()
                        if 80 <= len(txt) <= 7000 and (brand_of(txt) or src.get("source_segment")) and (YEAR_RE.search(txt) or src.get("target_year")) and len(detail_urls) <= 1:
                            score=0
                            if re.search(r"€|\\bEUR\\b",txt,re.I): score+=8
                            if re.search(r"price|preis|fixed price|netto|vat|mwst",txt,re.I): score+=4
                            if VIN_RE.search(txt) or VIN_LABEL_RE.search(txt): score+=2
                            score+=sum(1 for rx in FEATURES.values() if rx.search(txt))
                            score-=depth*0.15
                            candidates.append((score,len(txt),node))
                        node=node.parent
                    best=max(candidates,key=lambda z:(z[0],z[1]))[2] if candidates else None
                    if best is not None:
                        fragment=str(best)
                        if src.get("source_segment"):
                            fragment=f"<div>Source brand: {src['source_segment']}</div>"+fragment
                        if src.get("target_year"):
                            fragment=f"<div>Source filtered year: {src['target_year']}</div>"+fragment
                        rec=html_record(src["name"],key,fragment)
                        if rec:
                            if rec.get("market_year") is None and src.get("target_year"):
                                rec["market_year"]=int(src["target_year"])
                                rec["year_basis"]="source_filter_year"
                            rec["url"]=key
                            rows.append(rec)
                            card_seen.add(key)
                    continue

                low=full.lower()
                label=clean(a.get_text(" ",strip=True)).lower()
                pagination_label=bool(
                    re.fullmatch(r"\d{1,3}",label) or
                    label in {"next","next page","weiter","volgende","suivant","siguiente","następna",">","»","›"} or
                    re.search(r"[?&](?:page|p|pg)=\d+",full,re.I)
                )
                if index_tokens and any(t in low for t in index_tokens) and pagination_label and full not in seen and full not in queue:
                    queue.append(full)

        except Exception as e:
            events.append({"source":src["name"],"url":url,"observed_at":now(),"status":"fetch_error","error":str(e)[:500]})

    events.append({
        "source":src["name"],"url":None,"observed_at":now(),"status":"source_summary",
        "index_pages":len(seen),"cards_added":len(rows)-before,
        "detail_anchor_count":detail_anchor_count,"href_samples":href_samples
    })

def collect_planet_cards(http,src,rows,events):
    before=len(rows)
    for page_url in src.get("seed_pages",[]):
        try:
            status,html,final_url,mode=fetch_html(http,page_url)
            if status!=200 or not html:
                events.append({"source":src["name"],"url":page_url,"observed_at":now(),"status":"http_error","http_status":status,"mode":mode})
                continue
            soup=BeautifulSoup(html,"html.parser")
            full_text=clean(soup.get_text(" ",strip=True))
            seen_refs=set()
            debug_samples=0
            ref_nodes=soup.find_all(string=re.compile(r"Website\s*ref",re.I))
            for node in ref_nodes:
                holder=node.parent
                candidates=[]
                depth=0
                while holder is not None and depth<10:
                    txt=clean(holder.get_text(" ",strip=True))
                    if 100<=len(txt)<=9000 and brand_of(txt):
                        mref=re.search(r"Website\s*ref\.?\s*[:|]?\s*([0-9]{5,12})",txt,re.I)
                        if mref:
                            score=0
                            if re.search(r"€|\bEUR\b",txt,re.I): score+=6
                            if re.search(r"Bodywork|Make|Condition|Year|Country",txt,re.I): score+=6
                            if re.search(r"Axles|Airlift axle|Pallet trunk|VIN",txt,re.I): score+=3
                            score-=depth*0.1
                            candidates.append((score,len(txt),holder,mref.group(1)))
                    holder=holder.parent
                    depth+=1
                if not candidates:
                    continue
                _,_,best,ref=max(candidates,key=lambda z:(z[0],-z[1]))
                if ref in seen_refs:
                    continue
                seen_refs.add(ref)
                rec=html_record(src["name"],final_url+"#website-ref-"+ref,str(best))
                if rec:
                    marker=re.search(r"Website\\s*ref\\.?\\s*[:|]?\\s*"+re.escape(ref),full_text,re.I)
                    if marker:
                        before=full_text[max(0,marker.start()-5000):marker.start()]
                        after=full_text[marker.end():min(len(full_text),marker.end()+1800)]
                        if debug_samples < 2:
                            events.append({
                                "source":src["name"],"url":final_url,"observed_at":now(),
                                "status":"planet_context_sample","website_ref":ref,
                                "before_tail":before[-2800:],"after_head":after[:800]
                            })
                            debug_samples+=1
                        # Price is commonly in the listing header before the structured "Website ref" block.
                        if rec.get("price_amount") is None:
                            valid=[]
                            for rx in (PRICE_RE,PRICE_AFTER_RE):
                                for pm in rx.finditer(before):
                                    candidate=price_of(pm.group(0))
                                    if candidate is not None:
                                        valid.append((pm.start(),candidate))
                            valid.sort(key=lambda z:z[0])
                            if valid:
                                rec["price_amount"]=valid[-1][1]
                                rec["price_currency"]="EUR"
                        if rec.get("tax_basis") is None:
                            rec["tax_basis"]=tax_of(before[-700:]+" "+after[:400])
                        if not rec.get("seller"):
                            ms=re.search(r"([A-ZÀ-Ž0-9][A-Za-zÀ-ž0-9&.,'()\\- ]{2,90}?)\\s+Seller\\s+for\\s+\\d+\\s+(?:year|years|month|months)",before,re.I)
                            if ms:
                                rec["seller"]=clean(ms.group(1))
                    rec["source_listing_id"]=ref
                    rec["source_page_url"]=final_url
                    rows.append(rec)
            events.append({
                "source":src["name"],"url":final_url,"observed_at":now(),"status":"source_summary",
                "cards_added":len(rows)-before,"website_ref_nodes":len(ref_nodes)
            })
        except Exception as e:
            events.append({"source":src["name"],"url":page_url,"observed_at":now(),"status":"fetch_error","error":str(e)[:500]})

def collect_via_mobilis_cards(http,src,rows,events):
    before_total=len(rows)
    ref_rx=re.compile(r"(?:Website\s*ref|Ref\.\s*web|Réf\.\s*site|Ref\.\s*site)\s*[:|]?\s*([0-9]{5,12})",re.I)
    for page_url in src.get("seed_pages",[]):
        before=len(rows)
        try:
            if src.get("force_browser"):
                status,html,final_url=http.browser_html(page_url)
                mode="browser"
            else:
                status,html,final_url,mode=fetch_html(http,page_url)
            if status!=200 or not html:
                events.append({"source":src["name"],"url":page_url,"observed_at":now(),"status":"http_error","http_status":status,"mode":mode})
                continue
            soup=BeautifulSoup(html,"html.parser")
            full_text=clean(soup.get_text(" ",strip=True))
            seen_refs=set()
            ref_nodes=soup.find_all(string=re.compile(r"(?:Website\s*ref|Ref\.\s*web|Réf\.\s*site|Ref\.\s*site)",re.I))
            for node in ref_nodes:
                holder=node.parent
                candidates=[]
                depth=0
                while holder is not None and depth<12:
                    txt=clean(holder.get_text(" ",strip=True))
                    mref=ref_rx.search(txt)
                    if mref and 120<=len(txt)<=10000 and brand_of(txt):
                        score=0
                        if re.search(r"€|\bEUR\b",txt,re.I): score+=7
                        if re.search(r"Bodywork|Carrosserie|Make|Marque|Condition|Etat|Year|Année|Country|Pays",txt,re.I): score+=6
                        if re.search(r"Axles|Essieux|Airlift axle|Essieu relevable|Pallet|Coffre à palettes|VIN|Serial number",txt,re.I): score+=3
                        score-=depth*0.1
                        candidates.append((score,len(txt),holder,mref.group(1)))
                    holder=holder.parent
                    depth+=1
                if not candidates:
                    continue
                _,_,best,ref=max(candidates,key=lambda z:(z[0],-z[1]))
                if ref in seen_refs:
                    continue
                seen_refs.add(ref)
                rec=html_record(src["name"],final_url+"#website-ref-"+ref,str(best))
                if not rec:
                    continue
                marker=ref_rx.search(full_text)
                if rec.get("price_amount") is None:
                    # Search near this exact ref in the flattened page; price is typically before structured block.
                    pos=full_text.find(ref)
                    context=full_text[max(0,pos-2200):min(len(full_text),pos+1200)] if pos>=0 else ""
                    valid=[]
                    for rx in (PRICE_RE,PRICE_AFTER_RE):
                        for pm in rx.finditer(context):
                            candidate=price_of(pm.group(0))
                            if candidate is not None:
                                valid.append((pm.start(),candidate))
                    if valid:
                        valid.sort(key=lambda z:z[0])
                        rec["price_amount"]=valid[-1][1]
                        rec["price_currency"]="EUR"
                    if rec.get("tax_basis") is None:
                        if re.search(r"Ex\.\s*VAT|HT|sin IVA|Netto",context,re.I):
                            rec["tax_basis"]="net"
                rec["source_listing_id"]=ref
                rec["source_page_url"]=final_url
                rows.append(rec)
            events.append({
                "source":src["name"],"url":final_url,"observed_at":now(),"status":"source_summary",
                "cards_added":len(rows)-before,"website_ref_nodes":len(ref_nodes)
            })
        except Exception as e:
            events.append({"source":src["name"],"url":page_url,"observed_at":now(),"status":"fetch_error","error":str(e)[:500]})
    events.append({"source":src["name"],"url":None,"observed_at":now(),"status":"via_mobilis_total","cards_added":len(rows)-before_total})

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


def reef_mobile_record(source,item):
    raw=json.dumps(item,ensure_ascii=False,sort_keys=True)
    text=clean(flatten(item))
    brand=brand_of(text)
    if not brand:
        return None

    listing_id=item.get("listing_id") or item.get("id") or item.get("ad_id") or item.get("key")
    title=item.get("title") or item.get("headline") or item.get("model") or item.get("model_description")
    fr_raw=item.get("first_registration") or item.get("firstRegistration") or item.get("first_registration_date")
    fr=None
    if fr_raw:
        m=re.search(r"(20\d{2})",str(fr_raw))
        if m:
            y=int(m.group(1))
            if 2008<=y<=2021:
                fr=y

    cy=None
    for k in ("construction_year","constructionYear","year","year_of_construction"):
        v=item.get(k)
        if v is None:
            continue
        m=re.search(r"(20\d{2})",str(v))
        if m:
            y=int(m.group(1))
            if 2008<=y<=2021:
                cy=y
                break

    market_year=cy or fr
    if market_year is None:
        return None
    year_basis="construction_year" if cy else "first_registration_proxy"

    gross=item.get("price")
    net=item.get("price_net")
    amount=None
    tax_basis=None
    try:
        if net is not None:
            amount=float(net); tax_basis="net"
        elif gross is not None:
            amount=float(gross); tax_basis="gross"
    except Exception:
        amount=None

    seller=None
    for k in ("dealer_name","seller_name","seller","dealer"):
        v=item.get(k)
        if isinstance(v,str) and v.strip():
            seller=clean(v); break
        if isinstance(v,dict):
            for kk in ("name","company_name","company"):
                vv=v.get(kk)
                if vv:
                    seller=clean(str(vv)); break
        if seller: break

    location=None
    for k in ("location","town","city"):
        v=item.get(k)
        if isinstance(v,str) and v.strip():
            location=clean(v); break
        if isinstance(v,dict):
            vv=v.get("city") or v.get("town") or v.get("name")
            if vv:
                location=clean(str(vv)); break

    country=None
    for k in ("country","country_code","countryCode"):
        v=item.get(k)
        if isinstance(v,str) and len(v.strip()) in (2,3):
            country=v.strip().upper()[:2]
            break
    if country is None:
        for name,code in COUNTRY_NAMES.items():
            if re.search(r"\b"+re.escape(name)+r"\b",text,re.I):
                country=code; break

    vins=vins_of(text)
    feat={k:bool(rx.search(text)) for k,rx in FEATURES.items()}
    axle="SAF" if feat["saf"] else "BPW" if feat["bpw"] else "Schmitz ROTOS" if feat["rotos"] else None
    return {
        "source":source,
        "source_listing_id":str(listing_id) if listing_id is not None else None,
        "url":item.get("url") or item.get("listing_url") or (f"https://suchen.mobile.de/fahrzeuge/details.html?id={listing_id}" if listing_id else None),
        "observed_at":now(),
        "title":clean(str(title)) if title else None,
        "brand":brand,
        "construction_year":cy,
        "first_registration_year":fr,
        "market_year":market_year,
        "year_basis":year_basis,
        "source_year":None,
        "country":country,
        "seller":seller,
        "location":location,
        "vin":vins[0] if len(vins)==1 else None,
        "vin_candidates":vins,
        "vin_refs":vin_refs_of(text),
        "price_amount":amount,
        "price_currency":"EUR" if amount is not None else None,
        "tax_basis":tax_basis,
        "price_gross_eur":float(gross) if isinstance(gross,(int,float)) else None,
        "price_net_eur":float(net) if isinstance(net,(int,float)) else None,
        "vat_rate":item.get("vat_rate"),
        "vat_deductible":item.get("vat_deductible"),
        "previous_price_eur":item.get("previous_price"),
        "axle_maker":axle,
        "body_type":body_type_of(text),
        "asset_type":"semi_trailer",
        "lift_axle":True if feat["lift_axle"] else None,
        "pallet_box":True if feat["pallet_box"] else None,
        "code_xl":True if feat["code_xl"] else None,
        "mega":True if feat["mega"] else None,
        "coil":True if feat["coil"] else None,
        "joloda":True if feat["joloda"] else None,
        "huckepack":True if feat["huckepack"] else None,
        "raw_hash":hash_text(raw),
        "evidence_excerpt":text[:2000],
        "acquisition_mode":"third_party_api"
    }

def collect_reef_mobile(http,cfg,src,rows,events):
    key=os.getenv("REEF_API_KEY","").strip()
    endpoint="https://api.reefapi.com/mobile-de/v1/search"
    credits_url="https://api.reefapi.com/account/v1/credits"
    if not key:
        events.append({"source":src["name"],"url":endpoint,"observed_at":now(),"status":"not_configured","reason":"REEF_API_KEY missing"})
        return

    try:
        cr=http.s.get(credits_url,headers={"x-api-key":key,"User-Agent":UA},timeout=15)
        if cr.status_code==200:
            info=cr.json()
            remaining=info.get("remaining") if isinstance(info,dict) else None
            events.append({"source":src["name"],"url":credits_url,"observed_at":now(),"status":"credit_check","remaining_credits":remaining})
            floor=int(src.get("min_credits_to_run",40))
            if isinstance(remaining,(int,float)) and remaining<floor:
                events.append({"source":src["name"],"url":endpoint,"observed_at":now(),"status":"skipped_low_credits","remaining_credits":remaining,"minimum":floor})
                return
    except Exception as e:
        events.append({"source":src["name"],"url":credits_url,"observed_at":now(),"status":"credit_check_failed","error":str(e)[:300]})

    years=list(src.get("years") or cfg.get("years",{}).get("priority",[2021]))
    if src.get("rotate_historical_year"):
        historical=[y for y in range(cfg["years"]["min"],cfg["years"]["max"]+1) if y not in years]
        if historical:
            years=years+[historical[datetime.now(timezone.utc).timetuple().tm_yday % len(historical)]]

    page_size=int(src.get("page_size",100))
    max_pages=int(src.get("max_pages_per_query",2))
    headers={"x-api-key":key,"content-type":"application/json","User-Agent":UA}
    vehicle_type=src.get("vehicle_type","truck")

    # Resolve mobile.de's own make IDs first. ReefAPI validates make values
    # against this list, and trailer brands are not guaranteed to use the
    # spelling we use internally (e.g. Koegel/Kögel).
    makes_endpoint="https://api.reefapi.com/mobile-de/v1/makes"
    make_map={}
    try:
        mr=http.s.post(makes_endpoint,headers=headers,json={"vehicle_type":vehicle_type},timeout=30)
        mb=mr.json() if mr.status_code==200 else {}
        md=mb.get("data") or {}
        candidates=md.get("makes") or md.get("items") or md.get("results") or (md if isinstance(md,list) else [])
        def _norm_make(v):
            s=str(v or "").strip().lower()
            for a,b in (("ä","ae"),("ö","oe"),("ü","ue"),("ß","ss")):
                s=s.replace(a,b)
            return re.sub(r"[^a-z0-9]+","",s)
        aliases={
            "Kögel":["Kögel","Koegel","Kogel"],
            "Krone":["Krone"],
            "Schmitz Cargobull":["Schmitz Cargobull","Schmitz","Cargobull"],
            "Schwarzmüller":["Schwarzmüller","Schwarzmueller","Schwarzmuller"]
        }
        if isinstance(candidates,list):
            for brand in cfg["brands"]:
                wanted={_norm_make(x) for x in aliases.get(brand,[brand])}
                for m in candidates:
                    if not isinstance(m,dict):
                        continue
                    name=m.get("name") or m.get("label") or m.get("make")
                    mid=m.get("id") or m.get("make_id") or m.get("value")
                    nm=_norm_make(name)
                    if nm in wanted or any(w and (w in nm or nm in w) for w in wanted):
                        make_map[brand]=str(mid or name)
                        break
        events.append({"source":src["name"],"url":makes_endpoint,"observed_at":now(),"status":"makes_resolved","vehicle_type":vehicle_type,"resolved":make_map,"available_make_count":len(candidates) if isinstance(candidates,list) else None})
    except Exception as e:
        events.append({"source":src["name"],"url":makes_endpoint,"observed_at":now(),"status":"makes_lookup_failed","error":str(e)[:500]})

    search_aliases={
        "Kögel":["Koegel","Kogel","Kögel"],
        "Krone":["Krone"],
        "Schmitz Cargobull":["Schmitz","Schmitz Cargobull","Cargobull"],
        "Schwarzmüller":["Schwarzmueller","Schwarzmuller","Schwarzmüller"]
    }

    for brand in cfg["brands"]:
        for year in years:
            attempts=[]
            if brand in make_map:
                attempts.append(("make",make_map[brand]))
            for alias in search_aliases.get(brand,[brand]):
                if ("query",alias) not in attempts:
                    attempts.append(("query",alias))

            brand_done=False
            for mode,value in attempts:
                if brand_done:
                    break
                for page in range(1,max_pages+1):
                    payload={
                        "vehicle_type":vehicle_type,
                        "year_min":year,
                        "year_max":year,
                        "seller_type":"dealer",
                        "page":page,
                        "page_size":page_size,
                        "language":"en"
                    }
                    payload[mode]=value
                    try:
                        r=http.s.post(endpoint,headers=headers,json=payload,timeout=45)
                        if r.status_code!=200:
                            events.append({"source":src["name"],"url":endpoint,"observed_at":now(),"status":"http_error","http_status":r.status_code,"brand":brand,"year":year,"page":page,"search_mode":mode,"search_value":value,"text":r.text[:500]})
                            break
                        body=r.json()
                        if not body.get("ok",False):
                            events.append({"source":src["name"],"url":endpoint,"observed_at":now(),"status":"api_error","brand":brand,"year":year,"page":page,"search_mode":mode,"search_value":value,"error":body.get("error")})
                            break
                        data=body.get("data") or {}
                        items=data.get("results") or data.get("listings") or data.get("items") or []
                        before_count=len(rows)
                        for item in items:
                            if not isinstance(item,dict):
                                continue
                            rec=reef_mobile_record(src["name"],item)
                            if rec and rec.get("brand")==brand:
                                rows.append(rec)
                        added=len(rows)-before_count
                        sample_titles=[]
                        if added==0 and items:
                            for _it in items[:5]:
                                if isinstance(_it,dict):
                                    _t=_it.get("title") or _it.get("headline") or _it.get("model") or _it.get("model_description")
                                    if _t:
                                        sample_titles.append(clean(str(_t))[:180])
                        events.append({
                            "source":src["name"],"url":endpoint,"observed_at":now(),"status":"source_page",
                            "brand":brand,"year":year,"page":page,"search_mode":mode,"search_value":value,
                            "cards_added":added,
                            "items_seen":len(items),
                            "sample_titles":sample_titles,
                            "total_results":data.get("total_results"),
                            "record_count":(body.get("meta") or {}).get("record_count"),
                            "charged_credits":(body.get("meta") or {}).get("charged_credits"),
                            "remaining_credits":r.headers.get("X-Credits-Remaining")
                        })
                        if added>0:
                            brand_done=True
                            break
                        has_more=data.get("has_more")
                        if has_more is False or not items:
                            break
                    except Exception as e:
                        events.append({"source":src["name"],"url":endpoint,"observed_at":now(),"status":"fetch_error","brand":brand,"year":year,"page":page,"search_mode":mode,"search_value":value,"error":str(e)[:500]})
                        break

def write_ndjson(path,rows):
    with path.open("w",encoding="utf-8") as f:
        for r in rows:f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+"\n")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--config",required=True); ap.add_argument("--out",required=True); a=ap.parse_args()
    cfg=json.loads(Path(a.config).read_text(encoding="utf-8")); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    http=Http(); rows=[]; events=[]; started=now()
    runner_kind=os.getenv("SHM_RUNNER_KIND","local")
    source_filter={x.strip().lower() for x in os.getenv("SHM_SOURCE_NAMES","").split(",") if x.strip()}
    for src in cfg["sources"]:
        if source_filter and src.get("name","").lower() not in source_filter:
            events.append({"source":src["name"],"url":None,"observed_at":now(),"status":"skipped_by_source_filter"})
            continue
        if runner_kind=="github" and src.get("github_enabled") is False:
            events.append({"source":src["name"],"url":None,"observed_at":now(),"status":"skipped_on_github_runner"})
            continue
        if runner_kind!="github" and src.get("local_enabled") is False:
            events.append({"source":src["name"],"url":None,"observed_at":now(),"status":"skipped_on_local_runner"})
            continue
        if src["type"]=="sitemap": collect_sitemap(http,src,rows,events)
        elif src["type"]=="crawl_index": collect_index(http,src,rows,events)
        elif src["type"]=="index_cards": collect_index_cards(http,src,rows,events)
        elif src["type"]=="planet_cards": collect_planet_cards(http,src,rows,events)
        elif src["type"]=="via_mobilis_cards": collect_via_mobilis_cards(http,src,rows,events)
        elif src["type"]=="mobile_api": collect_mobile(http,cfg,src,rows,events)
        elif src["type"]=="reef_mobile_api": collect_reef_mobile(http,cfg,src,rows,events)
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
    (out/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    http.close()

if __name__=="__main__": main()
