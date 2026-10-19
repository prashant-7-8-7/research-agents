import streamlit as st
from main import run

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
            st.download_button("Download report (.md)", report, file_name=path.name)
            st.markdown(report)
