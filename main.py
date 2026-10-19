import argparse
import re
from pathlib import Path
from tools import web_search, fetch_page
from agents import planner, researcher, critic, writer
from verifier import verify_report, extract_claims

def research_question(q, sources, notes, log):
    results = web_search(q, 6)
    if not results:
        return
    pages = 0
    for r in results:
        if pages < 3:
            text = fetch_page(r["url"])
            if len(text) > len(r["body"]):
                r["body"] = text
                pages += 1
        if r["url"] not in sources:
            sources[r["url"]] = {"n": len(sources) + 1, "title": r["title"], "text": ""}
        if len(r["body"]) > len(sources[r["url"]]["text"]):
            sources[r["url"]]["text"] = r["body"]
        r["n"] = sources[r["url"]]["n"]
    log("    read " + str(pages) + " full pages, " + str(len(results) - pages) + " snippets")
    notes.append("Q: " + q + "\n" + researcher(q, results))

def run(topic, rounds=2, log=print):
    sources, notes = {}, []
    log("[Planner] planning...")
    questions = planner(topic)
    if not questions:
        log("Planner returned no questions. Try rewording the topic.")
        return None, None
    for q in questions:
        log("  - " + q)
    for i in range(1, rounds + 1):
        for q in questions:
            log("[Researcher] round " + str(i) + " : " + q)
            research_question(q, sources, notes, log)
        log("[Critic] checking notes...")
        questions = critic(topic, notes)
        if not questions:
            log("  approved")
            break
        log("  gaps found: " + "; ".join(questions))
    log("[Writer] writing report...")
    body = writer(topic, notes)
    if not extract_claims(body):
        log('  Writer dropped citations, retrying once...')
        body = writer(topic, notes)

    by_n = {v["n"]: v["text"] for v in sources.values()}
    results = verify_report(body, by_n, log)
    ok = sum(1 for _, _, good in results if good)
    if results:
        log("Verification: " + str(ok) + " of " + str(len(results)) + " cited claims supported ("
            + str(round(100 * ok / len(results))) + "%)")
        for claim, nums, good in results:
            if not good:
                log("  UNSUPPORTED " + str(nums) + ": " + claim[:150])

    refs = "\n".join(
        "[" + str(v["n"]) + "] " + v["title"][:90] + " - " + url
        for url, v in sorted(sources.items(), key=lambda kv: kv[1]["n"])
    )
    report = "# " + topic + "\n\n" + body + "\n\n## Sources\n\n" + refs + "\n"
    Path("reports").mkdir(exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")[:50]
    path = Path("reports") / (slug + ".md")
    path.write_text(report, encoding="utf-8")
    log("Saved to " + str(path))
    return report, path

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("topic")
    a = ap.parse_args()
    run(a.topic)

