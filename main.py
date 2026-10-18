import argparse
import re
from pathlib import Path
from tools import web_search
from agents import planner, researcher, critic, writer

def research_question(q, sources, notes):
    results = web_search(q)
    if not results:
        return
    for r in results:
        if r["url"] not in sources:
            sources[r["url"]] = {"n": len(sources) + 1, "title": r["title"]}
        r["n"] = sources[r["url"]]["n"]
    notes.append("Q: " + q + "\n" + researcher(q, results))

def run(topic, rounds=2):
    sources, notes = {}, []
    print("[Planner] planning...")
    questions = planner(topic)
    if not questions:
        print("Planner returned no questions. Try rewording the topic.")
        return
    for q in questions:
        print("  -", q)
    for i in range(1, rounds + 1):
        for q in questions:
            print("[Researcher] round", i, ":", q)
            research_question(q, sources, notes)
        print("[Critic] checking notes...")
        questions = critic(topic, notes)
        if not questions:
            print("  approved")
            break
        print("  gaps found:", questions)
    print("[Writer] writing report...")
    body = writer(topic, notes)
    refs = "\n".join(
        "[" + str(v["n"]) + "] " + v["title"] + " - " + url
        for url, v in sorted(sources.items(), key=lambda kv: kv[1]["n"])
    )
    report = "# " + topic + "\n\n" + body + "\n\n## Sources\n\n" + refs + "\n"
    Path("reports").mkdir(exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")[:50]
    path = Path("reports") / (slug + ".md")
    path.write_text(report, encoding="utf-8")
    print("\nSaved to", path)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("topic")
    a = ap.parse_args()
    run(a.topic)
