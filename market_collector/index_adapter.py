from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

def discover_index_pages(http, source, events, now_func):
    seeds=list(source.get("seed_pages") or [])
    queue=seeds[:]
    seen=set()
    details=[]
    allow=set(source.get("allow_hosts") or [])
    index_tokens=[x.lower() for x in source.get("index_url_tokens") or []]
    detail_rx=re.compile(source.get("detail_url_regex", r"\d{6,10}\.html(?:$|\?)"), re.I)
    max_index=int(source.get("max_index_pages", 30))
    max_details=int(source.get("max_pages_per_run", 600))

    while queue and len(seen)<max_index and len(details)<max_details:
        url=queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        try:
            r=http.get(url)
            html=None
            final_url=r.url
            mode="http"
            status=r.status_code
            if r.status_code==200:
                html=r.text
            elif r.status_code in (401,403,429):
                status,html,final_url=http.browser_html(url)
                mode="browser"
            if status!=200 or not html:
                events.append({"source":source["name"],"url":url,"observed_at":now_func(),"status":"http_error","http_status":status,"mode":mode})
                continue
            soup=BeautifulSoup(html,"html.parser")
        except Exception as exc:
            events.append({"source":source["name"],"url":url,"observed_at":now_func(),"status":"fetch_error","error":str(exc)[:500]})
            continue

        for a in soup.find_all("a", href=True):
            full=urljoin(final_url,a["href"])
            p=urlparse(full)
            if allow and (p.hostname or "") not in allow:
                continue
            if detail_rx.search(full):
                details.append(full)
                if len(details)>=max_details:
                    break
                continue
            low=full.lower()
            if index_tokens and any(t in low for t in index_tokens) and full not in seen and full not in queue:
                queue.append(full)

    return list(dict.fromkeys(details))
