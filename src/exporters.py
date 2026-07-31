"""Exporters: Markdown for the full package and CSV for structured tables."""

import pandas as pd

from src.utils import as_bullets, clean_text


# --- CSV exporters ------------------------------------------------------------

def _rows_to_csv(rows):
    """Convert a list of dicts to CSV text (empty-safe)."""
    if not rows:
        return ""
    return pd.DataFrame(rows).to_csv(index=False)


def five_whys_csv(package):
    rows = [
        {
            "Level": w["level"],
            "Question": w["question"],
            "Because": w["because"],
        }
        for w in package.get("five_whys", [])
    ]
    return _rows_to_csv(rows)


def fishbone_csv(package):
    rows = []
    for category, causes in package.get("fishbone", {}).items():
        for cause in causes:
            rows.append({"Category": category, "Potential Cause": cause})
    return _rows_to_csv(rows)


def matrix_csv(package):
    return _rows_to_csv(package.get("cause_evidence_matrix", []))


def action_items_csv(package):
    return _rows_to_csv(package.get("action_items", []))


def countermeasures_csv(package):
    return _rows_to_csv(package.get("countermeasures", []))


def verification_csv(package):
    return _rows_to_csv(package.get("verification_plan", []))


def root_causes_csv(package):
    """Root cause hypothesis plus contributing factors as a simple table."""
    rows = [{"Type": "Root Cause Hypothesis", "Description": package.get("root_cause_hypothesis", "")}]
    for factor in package.get("contributing_factors", []):
        rows.append({"Type": "Contributing Factor", "Description": factor})
    return _rows_to_csv(rows)


# --- Markdown exporter --------------------------------------------------------

def _five_whys_md(package):
    return "\n".join(
        f"{w['level']}. **{w['question']}** {w['because']}"
        for w in package.get("five_whys", [])
    )


def _fishbone_md(package):
    lines = []
    for category, causes in package.get("fishbone", {}).items():
        lines.append(f"**{category}**")
        lines.extend(f"- {c}" for c in causes)
        lines.append("")
    return "\n".join(lines).strip()


def _table_md(rows):
    if not rows:
        return "_None_"
    headers = list(rows[0].keys())
    md = ["| " + " | ".join(headers) + " |"]
    md.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        md.append(
            "| " + " | ".join(str(row.get(h, "")).replace("\n", " ") for h in headers) + " |"
        )
    return "\n".join(md)


def to_markdown(package):
    """Render the complete root cause package as a Markdown document."""
    conf = package.get("confidence", {})
    mat = package.get("maturity", {})
    rec = package.get("recurrence", {})

    sections = [
        f"# AI Root Cause Coach — {package.get('title', 'Untitled')}",
        f"*Category:* {package.get('category', 'Other')}  |  "
        f"*Generated:* {package.get('created_at', '')}  |  *Mode:* Template Engine Mode",
        "",
        "## Scorecard",
        f"- **Root Cause Confidence:** {conf.get('score', 0)}/100 — {conf.get('status', '')}",
        f"- **Problem-Solving Maturity:** {mat.get('score', 0)}/100 — {mat.get('status', '')}",
        f"- **Recurrence Risk:** {rec.get('level', '')} ({rec.get('score', 0)}/100)",
        "",
        "## 1. Executive Summary",
        package.get("executive_summary", ""),
        "",
        "## 2. Refined Problem Statement",
        package.get("refined_problem_statement", ""),
        "",
        "## 3. Problem Scope",
        package.get("problem_scope", ""),
        "",
        "## 4. Impact Summary",
        package.get("impact_summary", ""),
        "",
        "## 5. Containment Plan",
        as_bullets(package.get("containment_plan", [])),
        "",
        "## 6. 5 Whys Analysis",
        _five_whys_md(package),
        "",
        "## 7. Fishbone Analysis",
        _fishbone_md(package),
        "",
        "## 8. Cause and Evidence Matrix",
        _table_md(package.get("cause_evidence_matrix", [])),
        "",
        "## 9. Likely Root Cause Hypothesis",
        package.get("root_cause_hypothesis", ""),
        "",
        "## 10. Contributing Factors",
        as_bullets(package.get("contributing_factors", [])),
        "",
        "## 11. Countermeasure Plan",
        _table_md(package.get("countermeasures", [])),
        "",
        "## 12. Action Item Tracker",
        _table_md(package.get("action_items", [])),
        "",
        "## 13. Verification Plan",
        _table_md(package.get("verification_plan", [])),
        "",
        "## 14. Risk of Recurrence Assessment",
        f"**Level:** {rec.get('level', '')} ({rec.get('score', 0)}/100)\n\n{rec.get('message', '')}",
        "",
        "## 15. A3-Style Problem Solving Report",
        package.get("a3_report", ""),
        "",
        "## 16. Lessons Learned",
        as_bullets(package.get("lessons_learned", [])),
        "",
        "## 17. Prevention Checklist",
        as_bullets(package.get("prevention_checklist", [])),
        "",
        "## 18. Final Problem-Solving Summary",
        package.get("final_summary", ""),
        "",
        "---",
        "### Coaching Notes",
        as_bullets(package.get("coaching", [])),
    ]
    return "\n".join(clean_text(s) if isinstance(s, str) else s for s in sections)
