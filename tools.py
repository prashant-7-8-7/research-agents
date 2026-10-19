from ddgs import DDGS
import httpx
import trafilatura

AD_MARKERS = ("bing.com/aclick", "duckduckgo.com/y.js", "/aclk?", "doubleclick.net")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

def web_search(query, n=5):
    try:
        res = DDGS().text(query, max_results=n + 5)
    except Exception as e:
        print("  search failed:", e)
        return []
    out = []
    for r in res:
        url = r.get("href", "")
        if not url or any(m in url for m in AD_MARKERS):
            continue
        out.append({"title": r.get("title", ""), "url": url, "body": r.get("body", "")})
        if len(out) >= n:
            break
    return out

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
