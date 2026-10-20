# Multi-Agent Research System with Claim Verification

A local-LLM research assistant that plans a topic, searches the web, critiques its findings, writes a cited report, and **checks cited claims against collected source text**.

The project began as a four-agent research pipeline. Its verification checks were later **moved into plain code** in `verifier.py`, where rule-based checks work alongside repeated local-model judgements. The aim is to make unsupported claims more visible—not to guarantee that every reported fact is correct.

> **Status:** Working prototype and research experiment. The Verifier currently logs its decisions; it does **not** automatically edit or remove unsupported sentences from the saved report.

## Features

- **Four collaborating agents:** Planner, Researcher, Critic and Writer.
- **Live web research:** DuckDuckGo-based search through `ddgs`, full-page extraction with `trafilatura`, and search-snippet fallback when pages cannot be read.
- **Iterative research:** The Critic can request follow-up research, with up to two research rounds by default.
- **Cited Markdown reports:** Numbered references such as `[1]` and a list of source URLs.
- **Claim Verifier:** Checks cited sentences against saved source text, with numeric, negation, direction-of-change and entity-name checks plus repeated local-model votes.
- **Transparent verification output:** Reports the number of cited claims accepted and prints cases it could not verify.
- **Streamlit interface:** Run research in a browser and download Markdown or PDF output.
- **Local inference:** Runs its language model with Ollama; internet access is still required for live web searches.

## How it works

```text
Research topic
      |
      v
   Planner  ---> searchable questions
      |
      v
  Researcher ---> web search + page extraction + numbered sources
      ^
      |   follow-up questions (up to 2 research rounds)
    Critic
      |
      v
    Writer  ---> cited report draft
      |
      v
   Verifier ---> rule-based checks + repeated local-model decisions
      |                |
      |                +--> logs supported / cannot-verify claims
      v
  reports/<topic>.md   and   reports/<topic>.sources.json (local only)
```

| Component | Responsibility |
| --- | --- |
| **Planner** | Breaks the topic into focused research questions. |
| **Researcher** | Searches for information, reads available pages and records cited notes. |
| **Critic** | Reviews coverage and proposes follow-up questions when gaps remain. |
| **Writer** | Produces the Markdown report using numbered citations. |
| **Verifier** | Checks cited sentences against the source text collected during research. It is a post-writing verification stage, not a fifth research agent. |

## How the Verifier works

`main.py` collects source text while researching and passes the final draft to `verify_report()` in `verifier.py`. The Verifier extracts sentences containing citations and looks up the corresponding source text.

The checks include:

1. **Source presence:** Flags claims for which no cited source text is available.
2. **Numbers:** Looks for figures from the claim in the cited text (including handling of some formatted numbers and ranges).
3. **Negation:** Flags certain negation words that appear in the claim but not in its sources.
4. **Named entities:** Flags certain capitalized names that cannot be found in the cited source text.
5. **Direction and meaning:** Uses the local model to judge support, direction words such as *increase/decrease*, and true/false-style prompts. Several votes are used to limit dependence on a single model response.

A failed or uncertain check is treated as **not verified**. This is intentionally conservative, but does not make the Verifier a formal proof system. Heuristics can reject correct statements or accept unsupported ones. Claims without numbered citations are not included in the cited-claim check.

**Important:** Verification results are printed to the console or Streamlit status area. The report file itself is still written from the Writer's original draft. Review flagged claims before using a report as a factual source.

## Project structure

| Path | Purpose |
| --- | --- |
| `main.py` | Orchestrates the pipeline, calls verification, and writes reports/source snapshots. |
| `agents.py` | Prompts and functions for Planner, Researcher, Critic and Writer. |
| `llm.py` | Ollama model-call wrapper and generation settings. |
| `tools.py` | Search, source filtering and web-page extraction. |
| `verifier.py` | Claim extraction and verification logic. |
| `app.py` | Streamlit browser interface with report downloads. |
| `pdf_export.py` | Converts Markdown into PDF for the web interface. |
| `run_verify.py` | Rechecks a generated report against its local `.sources.json` file. |
| `test_verifier.py` | Quick sanity tests for claim checking and citation extraction. |
| `planted_v2.py` | Experimental numeric-change and wording-swap tests. |
| `planted_heldout.py` | Experimental negation and entity-swap tests. |
| `spot_check.py` | Prints randomly sampled cited claims and corresponding source URLs for manual review. |
| `requirements.txt` | Python dependencies captured for the project environment. |
| `reports/` | Example Markdown reports and locally generated output. |
| `screenshots/` | Project screenshots, where available. |

## Requirements

- Python 3.10 or newer.
- [Ollama](https://ollama.com/) installed and running.
- The Ollama model configured in `llm.py` (the current repository uses `qwen2.5:7b`).
- Internet connection for searching and retrieving webpages.
- Sufficient RAM/VRAM for the chosen local model. The project was developed on a laptop with an RTX 3050 (6 GB VRAM) and 16 GB RAM; smaller models may be required on more limited hardware.

Local inference does not require a paid hosted-model API key. The project uses `ddgs` for web searches without a paid search API, though search availability/rate limits and local hardware/network costs still apply.

## Setup (Windows PowerShell)

```powershell
# Install and start Ollama separately, then download the model:
ollama pull qwen2.5:7b

git clone https://github.com/prashant-7-8-7/research-agents.git
cd research-agents
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

On macOS/Linux, activate the environment with `source venv/bin/activate`.

## Run research

From the activated environment:

```powershell
python main.py "Electric vehicle charging infrastructure in India"
```

The console shows the research stages and the Verifier's accepted/total cited-claim count. A report is written to `reports/<topic>.md`. The associated `reports/<topic>.sources.json` contains the source text used for checking it.

To use the browser interface:

```powershell
streamlit run app.py
```

Open the local URL shown by Streamlit (typically `http://localhost:8501`), enter a topic, and run the pipeline. When finished, download the Markdown or PDF report.

## Verification and experimental tests

A basic smoke test:

```powershell
python test_verifier.py
python -c "import main; print('ok')"
```

To recheck a report, **first generate it locally** so its matching `.sources.json` file exists:

```powershell
python run_verify.py reports/electric-vehicle-charging-infrastructure-in-india.md
```

To perform the planted-error experiments using that report and its source snapshot:

```powershell
python planted_v2.py reports/electric-vehicle-charging-infrastructure-in-india.md
python planted_heldout.py reports/electric-vehicle-charging-infrastructure-in-india.md
```

The planted tests deliberately change a numeric value, a direction word, a negation or an entity name, then check whether the Verifier rejects the altered claim. They skip examples where the unchanged original claim was not accepted. The results depend on the underlying report, saved source text and local-model responses.

### What these tests establish—and what they do not

- The quick sanity check has produced expected `True`, `False` and extracted-citation output in the local development session.
- Planted-error tests exercise the rejection logic with deliberately changed claims; they are **not** a representative benchmark of all real-world hallucinations.
- The evaluation samples were small. A report about EV charging was used during tuning, so it should **not** be treated as an independent held-out evaluation.
- An entity swap is most reliably caught if the substituted name is missing from the source. A name that already appears in the source can still be misused.
- Some rejected claims from previous trial runs (approximately nine) were not manually read, so they cannot be counted as confirmed false claims.

No overall accuracy, precision or recall percentage is claimed here without a separately preserved, manually labelled test set and its actual run logs. Use the scripts to generate reproducible figures for your own setup.

## Source snapshots and reproducibility

The `.gitignore` excludes `reports/*.sources.json`. These files may include substantial text collected from third-party websites, so they are not published in this repository.

As a result, **the example `.md` files alone are not enough to reproduce source-backed verification or planted-error experiments**. Generate a fresh report with `python main.py "<topic>"` to create a matching `.sources.json` locally, then run `run_verify.py`, `planted_v2.py` or `planted_heldout.py` on that report.

The exact source content, search results and model outputs may change between runs. The `requirements.txt` pins the Python environment used for development, but it does not pin external webpages or search results.

## Known limitations

- **Unsupported claims remain in output:** The current Verifier logs flags, but does not rewrite or delete flagged sentences in the saved Markdown/PDF report.
- **Limited coverage:** Only sentences with recognized numbered citations are checked; uncited statements and some sentence/citation formats may escape extraction.
- **Evidence mismatch:** Checking whether a number, negation or entity string appears in a source is not equivalent to checking the full logical relationship. Source text may contain contradictory or unrelated mentions.
- **False positives and false negatives:** The local LLM is stochastic and can disagree with itself. Repeated voting reduces some variability but does not eliminate mistakes.
- **Page retrieval limitations:** Some publishers block automatic extraction, leaving shorter search snippets as the available evidence.
- **Report-dependent evaluation:** Existing experiments are small and not a blinded, manually adjudicated benchmark. In particular, the EV report was involved in tuning.
- **Source snapshot availability:** Source `.json` files are intentionally excluded from GitHub, preventing direct reproduction of the example results from the repository alone.
- **Code maintenance:** `verifier.py` currently contains earlier function definitions superseded by later definitions; refactoring should be tested carefully to avoid changing behaviour.

## Roadmap

- Preserve machine-readable verification decisions and attach them to each report.
- Optionally mark or remove unsupported claims **with review**, rather than silently publishing them.
- Consolidate overwritten definitions in `verifier.py` and add deterministic regression tests.
- Build a larger, manually labelled held-out benchmark with per-error-category results.
- Improve handling of multi-source claims, entities already present in the source, and numerical comparisons.

## Tech stack

Python · Ollama · Qwen 2.5 7B · Streamlit · ddgs · httpx · trafilatura · Markdown · xhtml2pdf

## Author

[prashant-7-8-7](https://github.com/prashant-7-8-7)
