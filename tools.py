from urllib.parse import urlparse
from ddgs import DDGS
import httpx
import trafilatura

AD_MARKERS = ("bing.com/aclick", "duckduckgo.com/y.js", "/aclk?", "doubleclick.net")
BLOCKED = ("sustainability-directory.com",)
TRUSTED = (
    ".gov", ".edu", "ieee.org", "mdpi.com", "sciencedirect.com", "springer.com",
    "nature.com", "arxiv.org", "acm.org", "wikipedia.org", "pv-magazine.com",
    "iea.org", "who.int", "europa.eu", "nih.gov", "nsf.gov",
)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

def domain(url):
    return urlparse(url).netloc.lower().replace("www.", "")

def rank(url):
    d = domain(url)
    return 0 if any(t in d for t in TRUSTED) else 1

def collect(query, out, per_domain, seen):
    try:
        res = DDGS().text(query, max_results=15)
    except Exception as e:
        print("  search failed:", e)
        return
    for r in res:
        url = r.get("href", "")
        if not url or url in seen or any(m in url for m in AD_MARKERS):
            continue
        d = domain(url)
        if any(b in d for b in BLOCKED) or per_domain.get(d, 0) >= 2:
            continue
        seen.add(url)
        per_domain[d] = per_domain.get(d, 0) + 1
        out.append({"title": r.get("title", ""), "url": url, "body": r.get("body", "")})

def web_search(query, n=5):
    out, per_domain, seen = [], {}, set()
    collect(query, out, per_domain, seen)
    if sum(1 for x in out if rank(x["url"]) == 0) < 2:
        collect(query + " research study review", out, per_domain, seen)
    out.sort(key=lambda x: rank(x["url"]))
    return out[:n]

def fetch_page(url, max_chars=2500):
    if url.lower().endswith(".pdf"):
        return ""
    try:
        r = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=15)
        if r.status_code != 200:
            return ""
        text = trafilatura.extract(r.text) or ""
        return text[:max_chars]
    except Exception:
        return ""
