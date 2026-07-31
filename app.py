"""AI Root Cause Coach — Streamlit application.

A local-first tool that turns vague operational problems into a structured
root cause analysis package (5 Whys, fishbone, cause/evidence matrix,
countermeasures, verification plan, and an A3-style report).

Run with:
    streamlit run app.py
"""

import pandas as pd
import streamlit as st

from src import config, db, exporters
from src.config import MODE_TEMPLATE, MODE_LLM
from src.providers import get_provider
from src.sample_data import SAMPLE_PROBLEMS, sample_titles
from src.utils import as_bullets, safe_filename
from src.validators import validate_inputs

CATEGORIES = [
    "Quality",
    "Safety",
    "Delivery",
    "Process",
    "Productivity",
    "Customer impact",
    "Tooling",
    "Data",
    "Communication",
    "Other",
]

# Input fields grouped into logical sections for a cleaner form layout.
# Each field is (key, label, widget_type). Order is preserved in the UI.
FIELD_GROUPS = [
    ("Problem definition", [
        ("problem_statement", "Problem statement", "text_area"),
        ("what_happened", "What happened", "text_area"),
        ("where_happened", "Where it happened", "text_input"),
        ("when_happened", "When it happened", "text_input"),
        ("frequency", "Frequency (how often)", "text_input"),
    ]),
    ("Impact & symptoms", [
        ("impact", "Business or operational impact", "text_area"),
        ("symptoms", "Symptoms observed (one per line)", "text_area"),
        ("risks", "Risks if not solved", "text_area"),
    ]),
    ("Facts & evidence", [
        ("known_facts", "Known facts (one per line)", "text_area"),
        ("suspected_causes", "Suspected causes (one per line)", "text_area"),
        ("evidence", "Evidence available (one per line)", "text_area"),
    ]),
    ("Context & history", [
        ("people", "People or teams involved", "text_input"),
        ("process_step", "Process step where issue appears", "text_input"),
        ("containment", "Current containment action", "text_area"),
        ("workaround", "Current workaround", "text_area"),
        ("previous_attempts", "Previous attempts to fix it", "text_area"),
    ]),
    ("Outcome", [
        ("desired_outcome", "Desired outcome", "text_area"),
        ("notes", "Notes", "text_area"),
    ]),
]

st.set_page_config(
    page_title="AI Root Cause Coach",
    page_icon="🧭",
    layout="wide",
)

db.init_db()


# --- Session state helpers ----------------------------------------------------

def _init_state():
    if "package" not in st.session_state:
        st.session_state.package = None
    if "form_values" not in st.session_state:
        st.session_state.form_values = {}
    if "gen_mode" not in st.session_state:
        st.session_state.gen_mode = MODE_TEMPLATE
    if "saved_flash" not in st.session_state:
        st.session_state.saved_flash = None


def _load_sample(index):
    st.session_state.form_values = dict(SAMPLE_PROBLEMS[index])


def _score_badge(label, score, status, color):
    st.markdown(
        f"""
        <div style="border:1px solid #d0d7de;border-radius:8px;padding:12px;">
            <div style="font-size:0.8rem;color:#57606a;">{label}</div>
            <div style="font-size:1.8rem;font-weight:700;color:{color};">{score}/100</div>
            <div style="font-size:0.85rem;color:{color};">{status}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _risk_badge(rec):
    st.markdown(
        f"""
        <div style="border:1px solid #d0d7de;border-radius:8px;padding:12px;">
            <div style="font-size:0.8rem;color:#57606a;">Recurrence Risk</div>
            <div style="font-size:1.8rem;font-weight:700;color:{rec['color']};">{rec['level']}</div>
            <div style="font-size:0.85rem;color:{rec['color']};">Score {rec['score']}/100</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# --- Rendering ----------------------------------------------------------------

def render_scorecards(package):
    conf, mat, rec = package["confidence"], package["maturity"], package["recurrence"]
    c1, c2, c3 = st.columns(3)
    with c1:
        _score_badge("Root Cause Confidence", conf["score"], conf["status"], conf["color"])
    with c2:
        _score_badge("Problem-Solving Maturity", mat["score"], mat["status"], mat["color"])
    with c3:
        _risk_badge(rec)

    with st.expander("Why these scores? (transparent breakdown)"):
        b1, b2, b3 = st.columns(3)
        with b1:
            st.caption("Confidence factors")
            st.dataframe(
                pd.DataFrame(conf["breakdown"].items(), columns=["Factor", "Points"]),
                use_container_width=True, hide_index=True,
            )
        with b2:
            st.caption("Maturity factors")
            st.dataframe(
                pd.DataFrame(mat["breakdown"].items(), columns=["Factor", "Points"]),
                use_container_width=True, hide_index=True,
            )
        with b3:
            st.caption("Recurrence factors")
            st.dataframe(
                pd.DataFrame(rec["breakdown"].items(), columns=["Factor", "Points"]),
                use_container_width=True, hide_index=True,
            )


def render_package(package):
    render_scorecards(package)

    if package.get("coaching"):
        st.info("**Coaching notes**\n\n" + as_bullets(package["coaching"]))

    with st.expander("1. Executive Summary", expanded=True):
        st.write(package["executive_summary"])
    with st.expander("2. Refined Problem Statement"):
        st.write(package["refined_problem_statement"])
    with st.expander("3. Problem Scope"):
        st.markdown(package["problem_scope"])
    with st.expander("4. Impact Summary"):
        st.markdown(package["impact_summary"])
    with st.expander("5. Containment Plan"):
        st.markdown(as_bullets(package["containment_plan"]))
    with st.expander("6. 5 Whys Analysis", expanded=True):
        for w in package["five_whys"]:
            st.markdown(f"**{w['level']}. {w['question']}** {w['because']}")
    with st.expander("7. Fishbone Analysis"):
        for category, causes in package["fishbone"].items():
            st.markdown(f"**{category}**")
            st.markdown(as_bullets(causes))
    with st.expander("8. Cause and Evidence Matrix", expanded=True):
        st.dataframe(pd.DataFrame(package["cause_evidence_matrix"]), use_container_width=True)
    with st.expander("9. Likely Root Cause Hypothesis", expanded=True):
        st.warning(package["root_cause_hypothesis"])
    with st.expander("10. Contributing Factors"):
        st.markdown(as_bullets(package["contributing_factors"]))
    with st.expander("11. Countermeasure Plan"):
        st.dataframe(pd.DataFrame(package["countermeasures"]), use_container_width=True)
    with st.expander("12. Action Item Tracker"):
        st.dataframe(pd.DataFrame(package["action_items"]), use_container_width=True)
    with st.expander("13. Verification Plan"):
        st.dataframe(pd.DataFrame(package["verification_plan"]), use_container_width=True)
    with st.expander("14. Risk of Recurrence Assessment"):
        st.markdown(f"**Level:** {package['recurrence']['level']}")
        st.write(package["recurrence"]["message"])
        st.dataframe(
            pd.DataFrame(
                package["recurrence"]["breakdown"].items(),
                columns=["Factor", "Points"],
            ),
            use_container_width=True,
        )
    with st.expander("15. A3-Style Problem Solving Report"):
        st.markdown(package["a3_report"])
    with st.expander("16. Lessons Learned"):
        st.markdown(as_bullets(package["lessons_learned"]))
    with st.expander("17. Prevention Checklist"):
        st.markdown(as_bullets(package["prevention_checklist"]))
    with st.expander("18. Final Problem-Solving Summary", expanded=True):
        st.success(package["final_summary"])

    render_exports(package)


def render_exports(package):
    st.subheader("Export")
    base = safe_filename(package.get("title", "root_cause"))
    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button(
            "📄 Full package (Markdown)",
            data=exporters.to_markdown(package),
            file_name=f"{base}_package.md",
            mime="text/markdown",
            use_container_width=True,
        )
        st.download_button(
            "5 Whys (CSV)",
            data=exporters.five_whys_csv(package),
            file_name=f"{base}_five_whys.csv",
            mime="text/csv",
            use_container_width=True,
        )
        st.download_button(
            "Fishbone (CSV)",
            data=exporters.fishbone_csv(package),
            file_name=f"{base}_fishbone.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col2:
        st.download_button(
            "Cause/Evidence Matrix (CSV)",
            data=exporters.matrix_csv(package),
            file_name=f"{base}_cause_evidence.csv",
            mime="text/csv",
            use_container_width=True,
        )
        st.download_button(
            "Root Causes (CSV)",
            data=exporters.root_causes_csv(package),
            file_name=f"{base}_root_causes.csv",
            mime="text/csv",
            use_container_width=True,
        )
        st.download_button(
            "Countermeasures (CSV)",
            data=exporters.countermeasures_csv(package),
            file_name=f"{base}_countermeasures.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col3:
        st.download_button(
            "Action Items (CSV)",
            data=exporters.action_items_csv(package),
            file_name=f"{base}_action_items.csv",
            mime="text/csv",
            use_container_width=True,
        )
        st.download_button(
            "Verification Plan (CSV)",
            data=exporters.verification_csv(package),
            file_name=f"{base}_verification.csv",
            mime="text/csv",
            use_container_width=True,
        )


# --- Tabs ---------------------------------------------------------------------

def tab_input():
    st.subheader("Define the problem")
    st.caption(
        "Fields marked * are required. More facts and evidence produce a "
        "stronger, higher-confidence analysis. Tip: load a sample from the "
        "sidebar to see a fully worked example."
    )

    fv = st.session_state.form_values
    with st.form("problem_form"):
        col_a, col_b = st.columns(2)
        with col_a:
            title = st.text_input(
                "Problem title *",
                value=fv.get("title", ""),
                placeholder="Short, specific name for the problem",
            )
        with col_b:
            category = st.selectbox(
                "Problem category *",
                CATEGORIES,
                index=CATEGORIES.index(fv["category"])
                if fv.get("category") in CATEGORIES
                else 0,
            )

        values = {"title": title, "category": category}
        for group_name, fields in FIELD_GROUPS:
            st.markdown(f"**{group_name}**")
            i = 0
            while i < len(fields):
                key, label, widget = fields[i]
                if widget == "text_area":
                    values[key] = st.text_area(label, value=fv.get(key, ""), height=90)
                    i += 1
                    continue
                # Pair two consecutive single-line inputs side by side.
                nxt = fields[i + 1] if i + 1 < len(fields) else None
                if nxt and nxt[2] == "text_input":
                    c1, c2 = st.columns(2)
                    with c1:
                        values[key] = st.text_input(label, value=fv.get(key, ""))
                    with c2:
                        values[nxt[0]] = st.text_input(nxt[1], value=fv.get(nxt[0], ""))
                    i += 2
                else:
                    values[key] = st.text_input(label, value=fv.get(key, ""))
                    i += 1
            st.divider()

        submitted = st.form_submit_button(
            "Generate Root Cause Package", use_container_width=True, type="primary"
        )

    if submitted:
        st.session_state.form_values = values
        is_valid, missing, warnings = validate_inputs(values)
        if not is_valid:
            st.error(
                "Please complete the required field(s): " + ", ".join(missing)
            )
        if warnings:
            with st.expander(
                f"⚠️ {len(warnings)} suggestion(s) to strengthen your analysis",
                expanded=not is_valid,
            ):
                for w in warnings:
                    st.markdown(f"- {w}")
        if is_valid:
            provider = get_provider(st.session_state.gen_mode)
            result = provider.generate_root_cause_analysis(values)
            package = result["package"]
            package["generation_mode"] = result["mode"]
            st.session_state.package = package
            if result.get("notice"):
                st.warning(result["notice"])
            st.success(
                f"Root cause package generated in {result['mode']}. Open the "
                "**Generated Analysis** tab to review and export it."
            )


def tab_generated():
    st.subheader("Generated Analysis")
    package = st.session_state.package
    if not package:
        st.info("Generate a package from the **Input** tab to see results here.")
        return

    st.caption(f"Generation Mode: **{package.get('generation_mode', MODE_TEMPLATE)}**")

    if st.button("💾 Save Analysis", type="primary"):
        new_id = db.save_analysis(package)
        st.session_state.saved_flash = new_id
        st.success(f"Saved as analysis #{new_id}. View it in the **Saved Analyses** tab.")

    render_package(package)


def tab_saved():
    st.subheader("Saved Analyses")
    analyses = db.get_all_analyses()
    if not analyses:
        st.info("No saved analyses yet. Generate and save one to build history.")
        return

    options = {
        f"#{a['id']} — {a['title']} ({a['category']})": a["id"] for a in analyses
    }
    choice = st.selectbox("Select an analysis", list(options.keys()))
    selected_id = options[choice]
    record = db.get_analysis(selected_id)

    col1, col2 = st.columns([3, 1])
    with col1:
        st.caption(f"Created: {record['created_at']}")
    with col2:
        if st.button("🗑️ Delete", use_container_width=True):
            db.delete_analysis(selected_id)
            st.success("Deleted. Refreshing…")
            st.rerun()

    render_package(record["package"])


def tab_dashboard():
    st.subheader("Dashboard")
    m = db.get_dashboard_metrics()
    if m["total"] == 0:
        st.info("No data yet. Save analyses to populate the dashboard.")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Analyses", m["total"])
    c2.metric("Avg Confidence", f"{m['avg_confidence']}/100")
    c3.metric("Avg Maturity", f"{m['avg_maturity']}/100")
    c4.metric("High Recurrence Risk", m["high_recurrence_count"])

    c5, _ = st.columns(2)
    c5.metric("Open Action Items", m["open_action_items"])

    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown("**Problems by Category**")
        if m["by_category"]:
            df = pd.DataFrame(
                sorted(m["by_category"].items(), key=lambda x: x[1], reverse=True),
                columns=["Category", "Count"],
            ).set_index("Category")
            st.bar_chart(df)
    with col_right:
        st.markdown("**Common Cause Categories (Fishbone)**")
        if m["common_causes"]:
            df = pd.DataFrame(
                sorted(m["common_causes"].items(), key=lambda x: x[1], reverse=True),
                columns=["Cause Category", "Count"],
            ).set_index("Cause Category")
            st.bar_chart(df)
        else:
            st.caption("Save more analyses to reveal common cause categories.")


# --- Main ---------------------------------------------------------------------

def main():
    _init_state()

    st.title("🧭 AI Root Cause Coach")
    st.caption(
        "Turn vague operational problems into structured root cause analysis — "
        "5 Whys, fishbone, cause/evidence matrix, countermeasures, and A3 report."
    )

    with st.sidebar:
        st.header("Generation Mode")
        requested_mode = st.radio(
            "Mode",
            [MODE_TEMPLATE, MODE_LLM],
            index=0 if st.session_state.gen_mode == MODE_TEMPLATE else 1,
            help=(
                "Template Engine Mode runs fully locally with no API key. "
                "LLM Enhanced Mode is future-ready and falls back to Template "
                "Engine Mode when no LLM_API_KEY is configured."
            ),
        )
        st.session_state.gen_mode = requested_mode

        effective_mode, notice = config.resolve_mode(requested_mode)
        if notice:
            st.warning(notice)
        st.success(f"Generation Mode: {effective_mode}")

        st.divider()
        st.header("Load a sample problem")
        sample_choice = st.selectbox("Sample", ["—"] + sample_titles())
        if st.button("Load sample into form", use_container_width=True):
            if sample_choice != "—":
                _load_sample(sample_titles().index(sample_choice))
                st.success("Sample loaded. Open the Input tab and Generate.")
        st.divider()
        st.caption(
            "Local-first · No API key required · Generic sample data only. "
            "Data is stored in `data/root_cause_coach.db`."
        )

    tabs = st.tabs(
        ["📝 Input", "📊 Generated Analysis", "🗂️ Saved Analyses", "📈 Dashboard"]
    )
    with tabs[0]:
        tab_input()
    with tabs[1]:
        tab_generated()
    with tabs[2]:
        tab_saved()
    with tabs[3]:
        tab_dashboard()


if __name__ == "__main__":
    main()
