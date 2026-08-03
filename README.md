# 🧭 AI Root Cause Coach

[![Live Demo](https://img.shields.io/badge/%E2%96%B6%20Live%20Demo-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://ai-root-cause-coach.streamlit.app/)

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.32%2B-FF4B4B?logo=streamlit&logoColor=white)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
![Last Commit](https://img.shields.io/github/last-commit/Sviless/ai-root-cause-coach)
![Code Size](https://img.shields.io/github/languages/code-size/Sviless/ai-root-cause-coach)

**▶️ Try it live: https://ai-root-cause-coach.streamlit.app/**

Turn vague operational, engineering, quality, process, or productivity problems
into a structured, evidence-based root cause analysis — locally, with no API key
required.

AI Root Cause Coach guides you through problem definition, containment, evidence
collection, 5 Whys, fishbone analysis, cause validation, countermeasures,
follow-up verification, and lessons learned. It produces an A3-style report,
transparent scores, and clean exports.

> **Local-first · No API key · Portfolio-safe.** Ships with **Template Engine
> Mode** (local Python templates and rules) and is architected to later support
> an optional **LLM Enhanced Mode**.

---

## Problem this tool solves

Teams often jump from symptoms straight to solutions. The result is recurring
issues, weak corrective actions, and repeated firefighting. AI Root Cause Coach
slows the leap from symptom to solution and enforces a disciplined,
process-focused path from problem to *validated* root cause to verified
countermeasure.

## Why structured root cause analysis matters

- **Symptoms ≠ causes.** Fixing a symptom lets the problem return.
- **Evidence beats opinion.** Confidence should track the quality of evidence.
- **Containment is temporary.** Countermeasures must address the validated cause.
- **Prevention needs ownership.** Safeguards fail without an owner and a review
  cadence.
- **Process focus, not blame.** Durable fixes come from improving the system.

## Key features

- **Guided input form** capturing 20 problem attributes.
- **One-click generation** of an 18-section root cause package.
- **Process-focused 5 Whys** that avoids blame and ends in a clearly-labeled
  root cause *hypothesis*.
- **Fishbone analysis** across 8 categories.
- **Cause & evidence matrix** with validation methods and next steps.
- **Countermeasure plan, action item tracker, and verification plan.**
- **Transparent scoring:** root cause confidence, problem-solving maturity, and
  recurrence risk — each with a visible breakdown.
- **Coaching messages** that reinforce good problem-solving discipline.
- **Exports:** full package to Markdown; CSV for 5 Whys, fishbone, cause/evidence
  matrix, root causes, countermeasures, action items, and verification plan.
- **Save & review** analyses in local SQLite.
- **Dashboard** with totals, averages, recurrence risk, open actions, and charts.

## Technology stack

- **Python** — core logic
- **Streamlit** — user interface
- **SQLite** — local storage
- **pandas** — data handling and CSV export
- **Streamlit built-in charts** — dashboard visualizations

## Folder structure

```
ai-root-cause-coach/
├── app.py                  # Streamlit UI: form, tabs, outputs, dashboard
├── requirements.txt
├── README.md
├── .env.example            # template for LLM Enhanced Mode (no real keys)
├── .gitignore
├── run.bat                 # double-click launcher (Windows)
├── data/
│   └── root_cause_coach.db # created automatically on first run
├── outputs/                # optional destination for exported files
└── src/
    ├── config.py           # env handling + mode resolution (key never exposed)
    ├── template_engine.py  # Template Engine Mode generation logic
    ├── db.py               # SQLite storage + dashboard metrics
    ├── exporters.py        # Markdown + CSV exporters
    ├── scoring.py          # confidence, maturity, recurrence scoring
    ├── validators.py       # input validation + quality checks
    ├── sample_data.py      # generic, portfolio-safe sample problems
    ├── utils.py            # text cleanup, list parsing, formatting helpers
    └── providers/          # pluggable generation backends
        ├── __init__.py         # get_provider(mode) factory
        ├── base_provider.py    # provider interface
        ├── template_provider.py# wraps Template Engine Mode
        └── llm_provider.py     # future-ready LLM provider (safe fallback)
```

## Setup instructions

```powershell
# 1. (Optional) create a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt
```

## How to run the app

```powershell
streamlit run app.py
```

Streamlit opens the app in your browser. Everything runs locally — no internet
access, API key, or secrets required.

## Generation Modes

The app uses a clean provider architecture with two modes. The app calls a
provider through a common interface (`src/providers/base_provider.py`) instead
of calling template functions directly, so a future LLM backend can be added
without changing the UI, exporters, or storage.

**Template Engine Mode** (default)
- Local-first; **no API key required**.
- Uses built-in Lean problem-solving rules, scoring logic, 5 Whys, fishbone
  categories, and A3 templates.
- Portfolio-safe and fully offline.

**LLM Enhanced Mode** (future-ready)
- Future-ready architecture; reads an `LLM_API_KEY` from the environment.
- Provider-neutral so it can later connect to OpenAI, Azure OpenAI, Claude, or
  another LLM provider.
- **Not required for the application to run.** If no `LLM_API_KEY` is
  configured, the app automatically falls back to Template Engine Mode and shows
  a friendly notice. No external API call is made yet — the single place to add
  one is `_call_llm()` in `src/providers/llm_provider.py`.

### Run in Template Engine Mode

```powershell
streamlit run app.py
```

### Prepare for LLM Enhanced Mode

Create a `.env` file (copy from `.env.example`) or set an environment variable:

```
LLM_API_KEY=your_key_here
LLM_PROVIDER=openai   # or azure, claude, ...
```

> **Important:** Do not include a real key in the repository and do not commit
> `.env` files. `.env` is already listed in `.gitignore`. The API key is never
> printed, logged, or displayed by the app.

## Example use case

1. In the sidebar, load the **"Nightly data pipeline finishes late"** sample.
2. Open the **Input** tab and click **Generate Root Cause Package**.
3. Review the **Generated Analysis** tab:
   - The 5 Whys chain moves from "job finished late" toward a *system-level*
     hypothesis (a missing, owned safeguard for the process step).
   - The cause & evidence matrix flags which evidence is still missing.
   - Confidence, maturity, and recurrence-risk badges summarize package strength.
4. Click **Save Analysis**, then open the **Dashboard** to see aggregate metrics.
5. Export the full Markdown package or individual CSVs for your tracker.

## Portfolio value

This project demonstrates creative problem solving for a common tech-company
pain point (jumping to solutions) and shows product thinking, clean modular
Python, local data persistence, transparent scoring logic, and thoughtful UX —
all portfolio-safe with only generic sample data.

## Possible future enhancements

- **LLM Enhanced Mode** (optional, key-gated) to enrich 5 Whys and narratives
- CSV or Excel issue import
- PDF and DOCX export
- Image upload for screenshots or problem evidence
- RAG-based evidence review
- Source attribution
- Countermeasure effectiveness tracking
- Multi-user support
- Cloud deployment

## Resume bullets

- Built a local-first AI Root Cause Coach using Python, Streamlit, SQLite, and
  Lean problem-solving methods to transform vague operational issues into
  structured 5 Whys, fishbone diagrams, cause/evidence matrices, countermeasure
  plans, and A3-style reports.
- Developed a template-driven problem-solving application that improves root
  cause discipline by scoring evidence quality, problem definition clarity,
  recurrence risk, and corrective action maturity.
- Designed a portfolio-safe AI-assisted operational excellence tool with
  Template Engine Mode, structured exports, dashboard metrics, and future-ready
  architecture for LLM-enhanced root cause analysis.
- Built an AI Root Cause Coach with local Template Engine Mode and LLM-ready
  provider architecture to guide structured problem solving, 5 Whys analysis,
  fishbone analysis, cause/evidence validation, countermeasure planning, and
  A3-style reporting.

---

## How Template Engine Mode works

Template Engine Mode generates the entire package using deterministic Python
templates and rules in `src/template_engine.py` — no external APIs. Small,
focused generator functions each produce one part of the package (refined
statement, containment plan, 5 Whys, fishbone, cause/evidence matrix, root cause
hypothesis, countermeasures, action items, verification plan, A3 report, lessons,
prevention checklist, and summaries). The orchestrator `generate_package()`
composes them, then computes scores. Because each generator is isolated, a future
**LLM Enhanced Mode** can replace individual generators without changing the
package shape consumed by the UI and exporters.

## How root cause confidence is calculated

`src/scoring.py → score_confidence()` sums transparent factors (max 100):

| Factor | Max |
|---|---|
| Problem statement clarity (word count tiers) | 15 |
| Evidence quality (items provided) | 15 |
| Frequency clarity | 10 |
| Impact clarity | 10 |
| Containment clarity | 10 |
| Known facts count | 15 |
| Cause/evidence alignment (matrix rows with support) | 10 |
| Previous attempts documented | 5 |
| Validation method defined | 10 |

Status: **80–100 Strong Hypothesis**, **50–79 Moderate Hypothesis**,
**0–49 Weak Hypothesis / More Evidence Needed**.

## How problem-solving maturity is calculated

`score_maturity()` rewards a complete, disciplined package (max 100): clear
problem definition, fact-based analysis, containment defined, root cause
hypothesis identified, countermeasures defined, owners assigned, verification
plan defined, recurrence prevention included, and lessons learned captured.

Status: **80–100 Strong Package**, **50–79 Needs Improvement**,
**0–49 Incomplete Package**.

## How recurrence risk is calculated

`score_recurrence()` raises risk for: frequent/unknown frequency, prior fixes
that did not hold, high impact, no containment in place, and low root cause
confidence. The score maps to **Low (0–29)**, **Medium (30–59)**, and
**High (60–100)**, each with guidance.

## How to describe this project on a resume

Use any of the resume bullets above. In short: *a portfolio-safe, local-first
operational excellence tool that applies Lean problem-solving (5 Whys, fishbone,
A3) with transparent confidence, maturity, and recurrence-risk scoring, built in
Python/Streamlit/SQLite and architected for a future LLM-enhanced mode.*

---

## License

Released under the [MIT License](LICENSE) © 2026 Gustavo Angulo.
