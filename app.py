import streamlit as st
from main import run
from pdf_export import md_to_pdf

st.set_page_config(page_title="Research Agents", layout="wide")
st.title("Multi-Agent Research System")
st.caption("Planner, Researcher, Critic and Writer agents running locally with Ollama")

topic = st.text_input("Research topic", placeholder="Edge AI for smart cities")
go = st.button("Run research", type="primary")

if go:
    if not topic.strip():
        st.warning("Enter a topic first.")
    else:
        with st.status("Agents are working... this takes about 5-12 minutes", expanded=True) as status:
            report, path = run(topic.strip(), log=lambda m: st.text(m))
            status.update(label="Done", state="complete")
        if report:
            st.session_state["report"] = report
            st.session_state["name"] = path.stem
            try:
                st.session_state["pdf"] = md_to_pdf(report)
            except Exception:
                st.session_state["pdf"] = None

if "report" in st.session_state:
    c1, c2, _ = st.columns([1, 1, 4])
    c1.download_button(
        "Download .md", st.session_state["report"],
        file_name=st.session_state["name"] + ".md",
    )
    if st.session_state.get("pdf"):
        c2.download_button(
            "Download PDF", st.session_state["pdf"],
            file_name=st.session_state["name"] + ".pdf",
            mime="application/pdf",
        )
    st.markdown(st.session_state["report"])
