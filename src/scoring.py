"""Scoring logic for confidence, problem-solving maturity, and recurrence risk.

All scores are transparent: each function returns a breakdown so the UI can
show *why* a score was assigned. Language and factors are process-focused.
"""

from src.utils import clean_text, non_empty, parse_list, contains_any

# --- Status thresholds --------------------------------------------------------

CONFIDENCE_LEVELS = [
    (80, "Strong Hypothesis", "#1a7f37"),
    (50, "Moderate Hypothesis", "#bf8700"),
    (0, "Weak Hypothesis / More Evidence Needed", "#cf222e"),
]

MATURITY_LEVELS = [
    (80, "Strong Problem-Solving Package", "#1a7f37"),
    (50, "Needs Improvement", "#bf8700"),
    (0, "Incomplete Problem-Solving Package", "#cf222e"),
]

RECURRENCE_COLORS = {
    "Low": "#1a7f37",
    "Medium": "#bf8700",
    "High": "#cf222e",
}

HIGH_IMPACT_TERMS = [
    "high", "severe", "critical", "major", "significant", "outage",
    "safety", "customer", "revenue", "escalation", "sla",
]

FREQUENT_TERMS = [
    "daily", "every", "constant", "frequent", "often", "recurring",
    "multiple", "weekly", "hourly", "repeat", "again",
]


def _status_for(score, levels):
    for threshold, label, color in levels:
        if score >= threshold:
            return label, color
    return levels[-1][1], levels[-1][2]


# --- Confidence ---------------------------------------------------------------

def score_confidence(inputs, matrix=None):
    """Confidence (0-100) that the root cause hypothesis is well supported."""
    breakdown = {}

    statement = clean_text(inputs.get("problem_statement"))
    words = len(statement.split())
    breakdown["Problem statement clarity"] = (
        15 if words >= 15 else 10 if words >= 8 else 5 if words >= 3 else 0
    )

    evidence = parse_list(inputs.get("evidence"))
    breakdown["Evidence quality"] = min(15, len(evidence) * 5)

    breakdown["Frequency clarity"] = 10 if non_empty(inputs.get("frequency")) else 0
    breakdown["Impact clarity"] = 10 if non_empty(inputs.get("impact")) else 0
    breakdown["Containment clarity"] = 10 if non_empty(inputs.get("containment")) else 0

    facts = parse_list(inputs.get("known_facts"))
    breakdown["Known facts count"] = min(15, len(facts) * 5)

    # Cause / evidence alignment based on how many matrix rows have support.
    if matrix:
        supported = sum(
            1
            for row in matrix
            if row.get("Evidence Supporting", "").strip()
            and "not yet" not in row.get("Evidence Supporting", "").lower()
        )
        ratio = supported / len(matrix)
        breakdown["Cause/evidence alignment"] = round(10 * ratio)
    else:
        breakdown["Cause/evidence alignment"] = (
            10 if (parse_list(inputs.get("suspected_causes")) and evidence) else 0
        )

    breakdown["Previous attempts documented"] = (
        5 if non_empty(inputs.get("previous_attempts")) else 0
    )
    breakdown["Validation method defined"] = 10 if matrix else 0

    score = max(0, min(100, sum(breakdown.values())))
    status, color = _status_for(score, CONFIDENCE_LEVELS)
    return {"score": score, "status": status, "color": color, "breakdown": breakdown}


# --- Maturity -----------------------------------------------------------------

def score_maturity(inputs, package):
    """Problem-solving maturity (0-100) for the overall package."""
    breakdown = {}

    statement = clean_text(inputs.get("problem_statement"))
    words = len(statement.split())
    breakdown["Clear problem definition"] = (
        12 if words >= 8 and non_empty(inputs.get("what_happened"))
        else 6 if non_empty(statement) else 0
    )

    facts = parse_list(inputs.get("known_facts"))
    evidence = parse_list(inputs.get("evidence"))
    breakdown["Fact-based analysis"] = (
        11 if facts and evidence else 5 if (facts or evidence) else 0
    )

    breakdown["Containment defined"] = 11 if non_empty(inputs.get("containment")) else 0
    breakdown["Root cause hypothesis identified"] = (
        11 if package.get("root_cause_hypothesis") else 0
    )
    breakdown["Countermeasures defined"] = 11 if package.get("countermeasures") else 0
    breakdown["Owners assigned"] = 11 if non_empty(inputs.get("people")) else 0
    breakdown["Verification plan defined"] = 11 if package.get("verification_plan") else 0
    breakdown["Recurrence prevention included"] = (
        11 if package.get("prevention_checklist") else 0
    )
    breakdown["Lessons learned captured"] = 11 if package.get("lessons_learned") else 0

    score = max(0, min(100, sum(breakdown.values())))
    status, color = _status_for(score, MATURITY_LEVELS)
    return {"score": score, "status": status, "color": color, "breakdown": breakdown}


# --- Recurrence risk ----------------------------------------------------------

def score_recurrence(inputs, confidence_score):
    """Recurrence risk (0-100) mapped to Low / Medium / High."""
    breakdown = {}

    frequency = clean_text(inputs.get("frequency"))
    if contains_any(frequency, FREQUENT_TERMS):
        breakdown["Frequency"] = 30
    elif frequency:
        breakdown["Frequency"] = 10
    else:
        breakdown["Frequency"] = 15  # unknown frequency is itself a risk

    # A documented previous attempt that did not stop the problem raises risk.
    breakdown["Prior fixes did not hold"] = (
        20 if non_empty(inputs.get("previous_attempts")) else 0
    )

    impact = clean_text(inputs.get("impact"))
    if contains_any(impact, HIGH_IMPACT_TERMS):
        breakdown["Impact severity"] = 20
    elif impact:
        breakdown["Impact severity"] = 5
    else:
        breakdown["Impact severity"] = 10

    breakdown["No containment in place"] = (
        15 if not non_empty(inputs.get("containment")) else 0
    )

    if confidence_score < 50:
        breakdown["Low root cause confidence"] = 20
    elif confidence_score < 80:
        breakdown["Moderate root cause confidence"] = 10
    else:
        breakdown["Low root cause confidence"] = 0

    score = max(0, min(100, sum(breakdown.values())))
    level = "High" if score >= 60 else "Medium" if score >= 30 else "Low"
    color = RECURRENCE_COLORS[level]

    messages = {
        "High": "High recurrence risk. Prioritize validated countermeasures and "
                "verification before closing.",
        "Medium": "Moderate recurrence risk. Strengthen evidence and confirm "
                  "countermeasure effectiveness.",
        "Low": "Lower recurrence risk. Maintain the verification plan to keep it "
               "that way.",
    }
    return {
        "level": level,
        "score": score,
        "color": color,
        "message": messages[level],
        "breakdown": breakdown,
    }
