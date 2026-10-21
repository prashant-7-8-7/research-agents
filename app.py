"""Research Agents | Streamlit workspace (run from the project folder).

Requires only the packages already in requirements.txt. The research pipeline is
unchanged; it still writes Markdown and source snapshots under reports/.
"""
from __future__ import annotations

import html
import json
import os
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)  # main.run() writes to a relative reports/ directory.

from llm import MODEL  # noqa: E402
from main import run  # noqa: E402
from pdf_export import md_to_pdf  # noqa: E402
from verifier import extract_claims, verify_report  # noqa: E402

REPORTS = ROOT / "reports"

st.set_page_config(
    page_title="Research Studio · Local AI",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
:root { color-scheme: dark; }
.stApp { background: #0b1020; color: #eaf0ff; }
[data-testid="stSidebar"] { background: #10182b; border-right: 1px solid #293550; }
[data-testid="stHeader"] { background: rgba(11,16,32,.94); }
.block-container { max-width: 1190px; padding-top: 2.4rem; padding-bottom: 4rem; }
h1,h2,h3 { letter-spacing: -.035em; }
[data-testid="stMetric"] { background: #141d32; border: 1px solid #2a3753;
  border-radius: 15px; padding: 14px 18px; min-height: 116px; }
[data-testid="stMetricLabel"] { color: #adbbd1; }
[data-testid="stMetricValue"] { color: #f4f7ff; }
[data-testid="stForm"], [data-testid="stVerticalBlockBorderWrapper"] > div {
  border-radius: 16px;
}
.stButton button[kind="primary"], .stDownloadButton button[kind="primary"] {
  background: linear-gradient(100deg,#6773f6,#4eaecc); border: 0; color: white;
  font-weight: 650; border-radius: 10px;
}
.stButton button, .stDownloadButton button { border-radius: 10px; }
.hero { padding: 26px 29px 24px; background:
 radial-gradient(circle at 85% 0%, rgba(79,175,211,.20), transparent 45%),
 linear-gradient(125deg,#172548,#11192f 66%); border:1px solid #2b3b60;
 border-radius: 22px; margin-bottom: 22px; }
.hero-kicker { color:#9ac7e3; letter-spacing:.14em; font-size:.75rem;
 font-weight:750; margin-bottom:7px; }
.hero-title { font-size: clamp(2rem,4vw,3.05rem); font-weight:780; letter-spacing:-.05em;
 line-height:1.1; margin: 0 0 10px; color:#f4f7ff; }
.hero-sub { color:#b7c4d8; max-width:750px; margin:0 0 14px; line-height:1.55; }
.pill { display:inline-block; font-size:.74rem; padding:5px 10px; border-radius:50px;
 color:#bfd6ec; background:#22304b; border:1px solid #344760; margin-right:7px; margin-top:4px; }
.pipeline { display:flex; gap:8px; flex-wrap:wrap; margin: 14px 0 10px; }
.pipe-step { font-size:.82rem; color:#bccbe0; background:#172239; border:1px solid #2b3952;
 border-radius:9px; padding:8px 12px; }
.pipe-step b { color:#b8bffe; margin-right:5px; }
.small-note { color:#a9b9d0; font-size:.86rem; line-height:1.5; }
.stage-note { background:#18243b; border-left:3px solid #69bcda;
 border-radius:7px; padding:9px 12px; color:#d9e9f7; margin:5px 0; }
.source-note { overflow-wrap:anywhere; }
</style>
""",
    unsafe_allow_html=True,
)


def report_files() -> list[Path]:
    REPORTS.mkdir(exist_ok=True)
    return sorted(REPORTS.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)


def report_title(path: Path) -> str:
    try:
        first = path.read_text(encoding="utf-8").splitlines()[0].strip()
        return first.lstrip("# ").strip()[:76] or path.stem.replace("-", " ").title()
    except (OSError, UnicodeError, IndexError):
        return path.stem.replace("-", " ").title()


def read_sources(path: Path) -> dict[int, dict]:
    snapshot = path.with_suffix(".sources.json")
    if not snapshot.exists():
        return {}
    try:
        raw = json.loads(snapshot.read_text(encoding="utf-8"))
        return {int(k): v for k, v in raw.items() if isinstance(v, dict)}
    except (ValueError, OSError, TypeError):
        return {}


def run_summary(logs: list[str]) -> tuple[int, int] | None:
    for line in reversed(logs):
        m = re.search(r"Verification:\s*(\d+) of (\d+) cited claims supported", line)
        if m:
            return int(m.group(1)), int(m.group(2))
    return None


def flag_from_logs(claim: str, logs: list[str]) -> str:
    """Display aid, NOT a machine-readable verification verdict."""
    for line in logs:
        stripped = line.strip()
        if not (stripped.startswith("UNSUPPORTED ") or stripped.startswith("CANT VERIFY ")):
            continue
        m = re.search(r"\]\s*:\s*(.*)", stripped)
        if m and len(m.group(1)) >= 12 and claim.startswith(m.group(1)):
            return "Flagged in run log"
    return "No flag in run log"


def stage_for_log(line: str, previous: tuple[str, int]) -> tuple[str, int]:
    if line.startswith("[Planner]"):
        return "Planner · building research questions", 12
    if line.startswith("[Researcher]"):
        return "Researcher · collecting evidence", 35
    if line.startswith("[Critic]"):
        return "Critic · reviewing gaps", 57
    if line.startswith("[Writer]"):
        return "Writer · drafting the report", 75
    if line.startswith("[Verifier]"):
        return "Verifier · checking cited claims", 88
    if line.startswith("Verification:"):
        return "Verifier · compiling results", 96
    if line.startswith("Saved to"):
        return "Report saved", 100
    return previous


@st.cache_data(show_spinner=False)
def pdf_data(markdown_text: str) -> bytes:
    return md_to_pdf(markdown_text)


if "runs" not in st.session_state:
    st.session_state["runs"] = {}
if "rechecks" not in st.session_state:
    st.session_state["rechecks"] = {}

with st.sidebar:
    st.markdown("### ◈ Research Studio")
    st.caption("A local-first research workspace")
    st.divider()
    st.markdown("**Engine**")
    st.code(MODEL, language=None)
    st.caption("Ollama · Runs locally · No paid model API")
    if st.button("Check Ollama connection", use_container_width=True):
        try:
            import ollama

            response = ollama.list()
            models = getattr(response, "models", None)
            if models is None:
                models = response.get("models", [])
            installed = [getattr(m, "model", None) or (m.get("name") if isinstance(m, dict) else "") for m in models]
            if MODEL in installed:
                st.success(f"Ready · {MODEL} installed")
            else:
                st.warning(f"Ollama responded, but {MODEL} was not found. Check 'ollama list'.")
        except Exception as exc:
            st.error("Cannot reach Ollama. Start the Ollama application and retry.")
            st.caption(str(exc))
    st.divider()
    st.markdown("**Workspace**")
    st.caption("Four agents → verification → source-backed reports")
    st.caption("Local GPU: RTX 3050 · 6 GB VRAM  |  System RAM: 16 GB")
    st.caption("Web search needs an internet connection. PDF/Markdown exports run locally.")
    st.divider()
    st.caption("⚠ The Verifier can make mistakes. Flagged statements remain in exported reports until manually edited.")

st.markdown(
    '<section class="hero">'
    '<div class="hero-kicker">LOCAL RESEARCH INTELLIGENCE</div>'
    '<div class="hero-title">From question to cited report.</div>'
    '<div class="hero-sub">Plan a topic, research real sources, critique the findings, and '
    'inspect what the local Verifier could and could not support.</div>'
    '<span class="pill">◆ Ollama-powered</span>'
    '<span class="pill">◈ Multi-agent workflow</span>'
    '<span class="pill">◎ Free & local</span>'
    '</section>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="pipeline">'
    '<span class="pipe-step"><b>01</b> Planner</span>'
    '<span class="pipe-step"><b>02</b> Researcher</span>'
    '<span class="pipe-step"><b>03</b> Critic</span>'
    '<span class="pipe-step"><b>04</b> Writer</span>'
    '<span class="pipe-step"><b>05</b> Verifier</span>'
    '</div>',
    unsafe_allow_html=True,
)

with st.form("research_form", clear_on_submit=False, border=True):
    st.markdown("#### Start a new research run")
    topic = st.text_input(
        "Research topic",
        placeholder="e.g. The future of green hydrogen production in India",
        max_chars=220,
    )
    config_col, info_col = st.columns([1, 2], vertical_alignment="bottom")
    with config_col:
        rounds = st.select_slider("Maximum research rounds", options=[1, 2], value=2)
    with info_col:
        st.caption("1 round is a faster demonstration; 2 rounds allow Critic follow-up research.")
    start = st.form_submit_button("Run multi-agent research", type="primary", use_container_width=True)
    st.caption("Running an identical topic again replaces its existing report and local source snapshot.")

if start:
    if not topic.strip():
        st.warning("Enter a research topic to begin.")
    else:
        events: list[str] = []
        phase = ("Starting the local pipeline", 3)
        report = None
        path = None
        with st.status("Agents are working", state="running", expanded=True) as process:
            bar = st.empty()
            phase_box = st.empty()
            console = st.empty()
            bar.progress(3, text="Starting local research")

            def on_log(message: str):
                nonlocal_stage = stage_for_log(str(message), on_log.phase)
                on_log.phase = (nonlocal_stage[0], max(nonlocal_stage[1], on_log.phase[1]))
                events.append(str(message))
                phase_box.markdown(
                    '<div class="stage-note">' + html.escape(nonlocal_stage[0]) + '</div>',
                    unsafe_allow_html=True,
                )
                bar.progress(on_log.phase[1], text=nonlocal_stage[0])
                console.code("\n".join(events[-9:]), language=None)

            on_log.phase = phase
            try:
                report, path = run(topic.strip(), rounds=rounds, log=on_log)
                if report and path:
                    bar.progress(100, text="Completed")
                    process.update(label="Research completed — open your report below", state="complete", expanded=False)
                else:
                    process.update(label="No report was generated", state="error", expanded=True)
            except Exception as exc:
                process.update(label="Research stopped — see the error below", state="error", expanded=True)
                st.error("The pipeline encountered an error. Existing saved reports were not removed.")
                st.exception(exc)

        if report and path:
            absolute = str(Path(path).resolve())
            st.session_state["active_report"] = absolute
            st.session_state["rechecks"].pop(absolute, None)  # Old decisions are stale after overwrite.
            st.session_state["runs"][absolute] = {
                "events": events,
                "summary": run_summary(events),
                "finished": datetime.now().strftime("%d %b %Y, %I:%M %p"),
            }
            st.success("Report created. Review flagged claims before sharing it.")

st.markdown("### Research library")
files = report_files()
if not files:
    st.info("No reports yet. Start with a topic above to create your first research report.")
    st.stop()

preferred = st.session_state.get("active_report")
selected_index = next((i for i, p in enumerate(files) if str(p.resolve()) == preferred), 0)
selected = st.selectbox(
    "Open a saved report",
    files,
    index=selected_index,
    format_func=report_title,
)
st.session_state["active_report"] = str(selected.resolve())
report_text = selected.read_text(encoding="utf-8")
body = report_text.partition("## Sources")[0]
source_info = read_sources(selected)
claims = extract_claims(body)
run_data = st.session_state["runs"].get(str(selected.resolve()), {})
summary = run_data.get("summary")
rechecked = st.session_state["rechecks"].get(str(selected.resolve()))

m1, m2, m3, m4 = st.columns(4)
m1.metric("Cited claims", len(claims))
m2.metric("Captured sources", len(source_info))
if rechecked is not None:
    accepted_count = sum(bool(item[2]) for item in rechecked)
    m3.metric("Verifier accepted", f"{accepted_count}/{len(rechecked)}")
elif summary:
    m3.metric("Verifier accepted", f"{summary[0]}/{summary[1]}")
else:
    m3.metric("Verifier accepted", "Not recorded")
m4.metric("Saved reports", len(files))

report_tab, sources_tab, verify_tab, activity_tab = st.tabs(
    ["📄 Report", "🔗 Sources", "🛡️ Verification", "⚡ Activity"]
)

with report_tab:
    st.caption("Draft output. Unsupported statements are not automatically removed.")
    d1, d2, _ = st.columns([1, 1, 3])
    d1.download_button(
        "Download Markdown",
        data=report_text,
        file_name=selected.name,
        mime="text/markdown",
        use_container_width=True,
    )
    try:
        data = pdf_data(report_text)
        if data.startswith(b"%PDF"):
            d2.download_button(
                "Download PDF", data=data, file_name=selected.stem + ".pdf",
                mime="application/pdf", use_container_width=True,
            )
        else:
            d2.caption("PDF export returned an invalid file.")
    except Exception:
        d2.caption("PDF export unavailable; Markdown download still works.")
    st.divider()
    st.markdown(report_text)

with sources_tab:
    st.caption("These are saved source snapshots, not a guarantee that each cited claim is supported.")
    if not source_info:
        st.info("The matching .sources.json file is missing. Source snapshots are intentionally excluded from GitHub.")
    else:
        ids = sorted(source_info)
        source_id = st.selectbox("Choose a numbered reference", ids, format_func=lambda n: f"[{n}]  {urlparse(source_info[n].get('url', '')).netloc or 'Unknown source'}")
        item = source_info[source_id]
        url = str(item.get("url", ""))
        content = str(item.get("text", ""))
        st.markdown(f"**Source [{source_id}]**")
        st.caption(f"Captured text: {len(content):,} characters")
        if urlparse(url).scheme in ("https", "http") and urlparse(url).netloc:
            st.link_button("Open original source ↗", url)
        else:
            st.code(url or "No URL saved", language=None)
        st.text_area("Saved evidence text", value=content or "No source text was captured.", height=285, disabled=True)

with verify_tab:
    st.caption("A supported result is a model judgment, not an independent fact-check. Results can vary between runs.")
    if not source_info:
        st.warning("Reverification needs the matching local .sources.json file.")
    else:
        if st.button("Recheck this report with local Ollama", key="recheck_button"):
            by_n = {n: str(info.get("text", "")) for n, info in source_info.items()}
            messages: list[str] = []
            with st.status("Rechecking cited claims with Ollama", expanded=True) as check_status:
                details = st.empty()

                def checker_log(message: str):
                    messages.append(str(message))
                    details.code("\n".join(messages[-8:]), language=None)

                try:
                    rechecked = verify_report(body, by_n, log=checker_log)
                    st.session_state["rechecks"][str(selected.resolve())] = rechecked
                    check_status.update(label="Recheck finished", state="complete", expanded=False)
                except Exception as exc:
                    check_status.update(label="Recheck failed", state="error", expanded=True)
                    st.error("Could not complete this recheck.")
                    st.exception(exc)
        if rechecked is not None:
            rows = [
                {"Claim": c, "Citations": ", ".join(f"[{n}]" for n in ns),
                 "Result": "Accepted by Verifier" if good else "Flagged / uncertain"}
                for c, ns, good in rechecked
            ]
            st.dataframe(rows, hide_index=True, use_container_width=True, height=360)
            st.caption("These are fresh structured Verifier decisions for this session.")
        elif run_data:
            rows = [
                {"Claim": claim, "Citations": ", ".join(f"[{n}]" for n in ns),
                 "Run log": flag_from_logs(claim, run_data["events"])}
                for claim, ns in claims
            ]
            st.dataframe(rows, hide_index=True, use_container_width=True, height=360)
            st.caption("Log-derived labels are indicative. Use 'Recheck' for structured results; it reruns the local model.")
        else:
            st.info("This older report has no verification session data loaded. Choose 'Recheck' to inspect it using your local model.")

with activity_tab:
    if run_data:
        st.caption(f"Latest run in this session: {run_data['finished']}")
        st.code("\n".join(run_data["events"]), language=None)
    else:
        st.info("Live agent logs are retained during this Streamlit session. Start a new run to see them here.")

st.markdown(
    '<p class="small-note">Research Studio runs on your own computer. Web research requires internet; '
    'local model calls and downloads do not require paid APIs. Review evidence before publishing.</p>',
    unsafe_allow_html=True,
)
