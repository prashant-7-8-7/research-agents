import json
import re
from llm import ask

def extract_json_list(text):
    m = re.search(r"\[.*?\]", text, re.S)
    if not m:
        return []
    try:
        return [x for x in json.loads(m.group(0)) if isinstance(x, str)]
    except Exception:
        return []

PLANNER_SYS = (
    "You are a research planner. Break the topic into 3 or 4 specific, searchable "
    "sub-questions that together cover it well. "
    "Reply with ONLY a JSON list of strings, nothing else."
)

RESEARCHER_SYS = (
    "You are a careful researcher. Answer the question in 3 to 5 sentences using ONLY "
    "the numbered sources given. Cite every claim like [1] or [2]. "
    "If the sources do not answer the question, say so. Never invent facts."
)

CRITIC_SYS = (
    "You are a strict research critic. Read the topic and the notes. "
    "If important aspects are missing or claims are weak, reply with ONLY a JSON list "
    "of at most 2 new search questions that would fill the gaps. "
    "If the notes cover the topic well, reply with only the word APPROVED."
)

WRITER_SYS = (
    "You are a research writer. Write a clear report in Markdown using ONLY the notes given. "
    "Structure: a short Summary, then Key Findings with a heading per theme, then Open Questions. "
    "Keep the citation numbers like [1] exactly as they appear in the notes. "
    "Do not add a sources section. Do not invent facts."
)

def planner(topic):
    return extract_json_list(ask(PLANNER_SYS, "Topic: " + topic))[:4]

def researcher(question, results):
    ctx = "\n\n".join(
        "[" + str(r["n"]) + "] " + r["title"] + "\n" + r["body"] for r in results
    )
    return ask(RESEARCHER_SYS, "Question: " + question + "\n\nSources:\n" + ctx)

def critic(topic, notes):
    out = ask(CRITIC_SYS, "Topic: " + topic + "\n\nNotes:\n" + "\n\n".join(notes)[:10000])
    return extract_json_list(out)[:2]

def writer(topic, notes):
    return ask(
        WRITER_SYS,
        "Topic: " + topic + "\n\nNotes:\n" + "\n\n".join(notes)[:12000],
        max_tokens=2500,
    )
