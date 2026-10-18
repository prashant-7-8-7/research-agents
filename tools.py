from ddgs import DDGS

AD_MARKERS = ("bing.com/aclick", "duckduckgo.com/y.js", "/aclk?", "doubleclick.net")

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
