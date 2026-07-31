"""Template Engine Mode: local, rule-based root cause analysis generation.

This module turns raw problem inputs into a complete, structured root cause
package. It uses deterministic Python templates and rules (no external APIs).

The architecture is intentionally split into small generator functions so a
future "LLM Enhanced Mode" can swap individual generators without changing the
package shape consumed by the UI and exporters.
"""

import re

from src import scoring
from src.utils import (
    clean_text,
    non_empty,
    parse_list,
    first_sentence,
    now_iso,
)

FISHBONE_CATEGORIES = [
    "People",
    "Process",
    "Tools or Technology",
    "Materials or Inputs",
    "Environment",
    "Measurement or Data",
    "Communication",
    "Management System",
]

# Hints used to seed fishbone candidate causes from the available inputs.
_FISHBONE_HINTS = {
    "People": "Skill, training, or capacity gaps in the process step",
    "Process": "Missing, unclear, or unfollowed process standard",
    "Tools or Technology": "Tool limitations, configuration, or automation gaps",
    "Materials or Inputs": "Input quality, volume, or availability issues",
    "Environment": "Workload, timing, or environmental conditions",
    "Measurement or Data": "Data accuracy, monitoring, or metric gaps",
    "Communication": "Handoff, notification, or information-sharing gaps",
    "Management System": "Ownership, review cadence, or control gaps",
}

SYMPTOM_TERMS = ["slow", "broken", "error", "crash", "fails", "down", "late", "wrong"]

# Category-tailored gap themes. Each tuple is (detection gap, standard gap) and
# is used to escalate the 5 Whys toward a system-level root cause hypothesis
# while keeping the language process-focused (never blaming individuals).
CATEGORY_GAPS = {
    "Quality": (
        "a verification check in the process step did not detect the defect condition",
        "the quality standard for this step was undefined or applied inconsistently",
    ),
    "Data": (
        "an automated data check did not flag the condition before it propagated",
        "there was no defined data validation or monitoring standard for this step",
    ),
    "Delivery": (
        "there was no early signal when the step was at risk of missing its target",
        "there was no defined checkpoint or lead-time standard for this step",
    ),
    "Process": (
        "the process step had no built-in check to confirm it was done correctly",
        "the process standard was unclear, so the step depended on individual effort",
    ),
    "Productivity": (
        "the bottleneck in the workflow was not made visible early enough",
        "there was no standard way of working to prevent the slowdown",
    ),
    "Customer impact": (
        "the issue was not caught by an internal check before it reached the customer",
        "there was no defined guardrail protecting the customer-facing step",
    ),
    "Tooling": (
        "the tool or configuration had no safeguard to prevent the failure mode",
        "there was no standard for validating tool configuration or changes",
    ),
    "Communication": (
        "the information was not shared at the handoff where it was needed",
        "there was no standard for what to communicate, when, and to whom",
    ),
    "Safety": (
        "a safeguard that should have prevented the condition was missing or bypassed",
        "there was no clear standard defining the required safe condition",
    ),
}

_DEFAULT_GAP = (
    "the control that should have caught the condition was missing or inconsistent",
    "there was no clear standard, so the step relied on individual effort",
)

# Keywords used to route observations into the correct fishbone category.
FISHBONE_KEYWORDS = {
    "People": ["training", "skill", "capacity", "staff", "workload", "people",
               "team", "experience", "manual", "overloaded", "turnover"],
    "Process": ["process", "step", "procedure", "standard", "workflow",
                "handoff", "approval", "checklist", "review", "steps"],
    "Tools or Technology": ["tool", "system", "software", "automation", "config",
                            "script", "query", "pipeline", "server", "hardware",
                            "job", "integration"],
    "Materials or Inputs": ["input", "material", "supply", "dependency",
                            "upstream", "volume", "raw"],
    "Environment": ["environment", "timing", "schedule", "load", "peak",
                    "overlap", "condition", "network"],
    "Measurement or Data": ["metric", "measure", "data", "monitor", "log",
                            "threshold", "report", "accuracy", "dashboard"],
    "Communication": ["communication", "notify", "notification", "inform",
                      "update", "status", "documentation", "doc", "unclear"],
    "Management System": ["owner", "ownership", "policy", "governance",
                          "priority", "management", "cadence", "responsibility"],
}


# --- Refinement ---------------------------------------------------------------

def refine_problem_statement(inputs):
    """Produce a tightened, fact-based restatement of the problem."""
    title = clean_text(inputs.get("title")) or "Problem"
    what = first_sentence(inputs.get("what_happened")) or clean_text(
        inputs.get("problem_statement")
    )
    where = clean_text(inputs.get("where_happened"))
    when = clean_text(inputs.get("when_happened"))
    frequency = clean_text(inputs.get("frequency"))
    impact = first_sentence(inputs.get("impact"))

    parts = [f"{title}."]
    if what:
        parts.append(f"Observed condition: {what}.")
    location_time = ", ".join(p for p in [where, when] if p)
    if location_time:
        parts.append(f"Context: {location_time}.")
    if frequency:
        parts.append(f"Frequency: {frequency}.")
    if impact:
        parts.append(f"Impact: {impact}.")
    return " ".join(parts)


def build_problem_scope(inputs):
    """Describe what is in and out of scope based on the inputs."""
    where = clean_text(inputs.get("where_happened")) or "Not specified"
    step = clean_text(inputs.get("process_step")) or "Not specified"
    people = clean_text(inputs.get("people")) or "Not specified"
    when = clean_text(inputs.get("when_happened")) or "Not specified"
    return (
        f"- **Where:** {where}\n"
        f"- **Process step:** {step}\n"
        f"- **Teams involved:** {people}\n"
        f"- **Timeframe:** {when}\n"
        "- **Out of scope:** Unrelated systems and steps that show no evidence "
        "of contributing to this problem."
    )


def build_impact_summary(inputs):
    """Summarize the operational and business impact."""
    impact = clean_text(inputs.get("impact")) or "Not specified"
    frequency = clean_text(inputs.get("frequency")) or "Not specified"
    risks = clean_text(inputs.get("risks")) or "Not specified"
    return (
        f"- **Current impact:** {impact}\n"
        f"- **Frequency:** {frequency}\n"
        f"- **Risk if unresolved:** {risks}"
    )


# --- Containment --------------------------------------------------------------

def build_containment_plan(inputs):
    """Return a short containment plan (temporary protective actions)."""
    plan = []
    current = clean_text(inputs.get("containment"))
    workaround = clean_text(inputs.get("workaround"))
    if current:
        plan.append(f"Continue current containment: {current}")
    if workaround:
        plan.append(f"Maintain interim workaround: {workaround}")
    plan.append(
        "Communicate status to affected teams and customers while the root "
        "cause is investigated."
    )
    plan.append(
        "Track occurrences so the impact is visible until a validated "
        "countermeasure is in place."
    )
    if not current and not workaround:
        plan.insert(
            0,
            "Define an immediate protective action to limit impact (no "
            "containment was provided).",
        )
    return plan


# --- 5 Whys -------------------------------------------------------------------

def generate_five_whys(inputs):
    """Generate a logical, process-focused 5 Whys chain.

    Levels 1-2 use the user's own observations when available; levels 3-5
    escalate toward a system-level root cause hypothesis using category-tailored
    process, control, standard, and management-system gaps. The chain never
    blames individuals.
    """
    problem = (
        first_sentence(inputs.get("problem_statement"))
        or clean_text(inputs.get("title"))
        or "the problem"
    )
    step = clean_text(inputs.get("process_step")) or "the affected process step"
    category = clean_text(inputs.get("category"))

    seeds = parse_list(inputs.get("suspected_causes")) or parse_list(
        inputs.get("symptoms")
    )
    seed0 = seeds[0] if len(seeds) > 0 else f"the condition in {step} was not detected in time"
    seed1 = (
        seeds[1]
        if len(seeds) > 1
        else f"{step} did not include a check that would catch this condition"
    )

    detection_gap, standard_gap = CATEGORY_GAPS.get(category, _DEFAULT_GAP)

    chain = [
        {
            "level": 1,
            "question": f"Why did this happen? ({problem})",
            "because": f"Because {seed0}.",
        },
        {
            "level": 2,
            "question": "Why did that occur?",
            "because": f"Because {seed1}.",
        },
        {
            "level": 3,
            "question": "Why was that not prevented earlier?",
            "because": f"Because {detection_gap}.",
        },
        {
            "level": 4,
            "question": "Why was that safeguard missing or inconsistent?",
            "because": f"Because {standard_gap}.",
        },
        {
            "level": 5,
            "question": "Why did the standard or safeguard not exist?",
            "because": (
                "Because the management system did not establish, assign an "
                "owner for, and regularly review a safeguard for this process "
                "step (root cause hypothesis)."
            ),
        },
    ]
    return chain


# --- Fishbone -----------------------------------------------------------------

def _route_to_category(text):
    """Return the fishbone category whose keywords best match the text."""
    text_l = text.lower()
    best, best_hits = None, 0
    for category, keywords in FISHBONE_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in text_l)
        if hits > best_hits:
            best, best_hits = category, hits
    return best


def generate_fishbone(inputs):
    """Generate candidate causes for each of the 8 fishbone categories.

    User observations are routed to the category their wording best matches, so
    each bone reflects the actual problem instead of a fixed template. Bones
    with no match keep a guiding prompt so none appear empty.
    """
    pool = (
        parse_list(inputs.get("suspected_causes"))
        + parse_list(inputs.get("symptoms"))
        + parse_list(inputs.get("known_facts"))
    )
    people = clean_text(inputs.get("people"))

    fishbone = {category: [] for category in FISHBONE_CATEGORIES}
    for item in pool:
        category = _route_to_category(item)
        if category and item not in fishbone[category]:
            fishbone[category].append(item)

    if people:
        note = f"Consider workload/training for: {people}"
        if note not in fishbone["People"]:
            fishbone["People"].append(note)

    for category in FISHBONE_CATEGORIES:
        if not fishbone[category]:
            fishbone[category].append(f"Explore: {_FISHBONE_HINTS[category]}")
    return fishbone


# --- Cause / evidence matrix --------------------------------------------------

def _match_evidence(cause, evidence_items):
    """Return the evidence item whose wording best overlaps with the cause."""
    cause_words = set(re.findall(r"[a-z]{4,}", cause.lower()))
    best, best_hits = None, 0
    for item in evidence_items:
        item_words = set(re.findall(r"[a-z]{4,}", item.lower()))
        hits = len(cause_words & item_words)
        if hits > best_hits:
            best, best_hits = item, hits
    return best if best_hits > 0 else None


def generate_cause_evidence_matrix(inputs):
    """Build a cause-and-evidence matrix, matching evidence to causes by wording."""
    causes = (
        parse_list(inputs.get("suspected_causes"))
        or parse_list(inputs.get("symptoms"))
        or ["The process step lacks a verification control"]
    )
    evidence_items = parse_list(inputs.get("evidence"))

    matrix = []
    for cause in causes[:6]:
        supporting = _match_evidence(cause, evidence_items)
        has_support = supporting is not None
        matrix.append(
            {
                "Potential Cause": cause,
                "Evidence Supporting": supporting or "Not yet collected",
                "Evidence Missing": (
                    "Independent confirmation from a second source"
                    if has_support
                    else "Baseline/trend data and a controlled comparison"
                ),
                "Validation Method": (
                    "Review data/logs, reproduce the condition, or run a "
                    "controlled comparison"
                ),
                "Confidence Level": "Medium" if has_support else "Low",
                "Recommended Next Step": (
                    "Seek a second confirming source, then act"
                    if has_support
                    else "Collect the missing evidence before choosing a "
                    "permanent countermeasure"
                ),
            }
        )
    return matrix


# --- Root cause + contributing factors ---------------------------------------

def build_root_cause_hypothesis(inputs, five_whys):
    """Derive the root cause hypothesis from the end of the 5 Whys chain."""
    final_because = five_whys[-1]["because"] if five_whys else ""
    step = clean_text(inputs.get("process_step")) or "the affected process step"
    return (
        f"Hypothesis: The problem persists because {step} lacks a defined, "
        f"owned, and regularly reviewed safeguard. {final_because} "
        "This remains a hypothesis until validated with the evidence identified "
        "in the cause-and-evidence matrix."
    )


def build_contributing_factors(inputs):
    """List plausible contributing factors (not the primary root cause)."""
    factors = []
    if non_empty(inputs.get("frequency")):
        factors.append("Frequency indicates a systemic rather than one-off condition.")
    if non_empty(inputs.get("previous_attempts")):
        factors.append(
            "Prior fixes addressed symptoms, allowing the pattern to return."
        )
    if not parse_list(inputs.get("evidence")):
        factors.append("Limited evidence slows accurate cause validation.")
    if non_empty(inputs.get("workaround")):
        factors.append(
            "Reliance on a manual workaround may mask the underlying condition."
        )
    if not factors:
        factors.append(
            "No strong contributing factors identified from the current inputs."
        )
    return factors


# --- Countermeasures / actions / verification --------------------------------

def build_countermeasures(inputs, root_cause):
    """Propose process-focused countermeasures tied to the validated cause."""
    step = clean_text(inputs.get("process_step")) or "the affected process step"
    return [
        {
            "Countermeasure": (
                f"Define and document a clear standard for {step}, including the "
                "check that would catch this condition."
            ),
            "Type": "Corrective",
            "Addresses": "Missing standard (root cause hypothesis)",
            "Owner": "Process owner (assign)",
            "Target Date": "TBD",
        },
        {
            "Countermeasure": (
                "Add a verification or monitoring control that flags the "
                "condition automatically before it reaches the customer."
            ),
            "Type": "Preventive",
            "Addresses": "Missing control / late detection",
            "Owner": "Process owner (assign)",
            "Target Date": "TBD",
        },
        {
            "Countermeasure": (
                "Establish a periodic review so the safeguard stays effective as "
                "conditions change."
            ),
            "Type": "Systemic",
            "Addresses": "Management-system / ownership gap",
            "Owner": "Team lead (assign)",
            "Target Date": "TBD",
        },
    ]


def build_action_items(inputs, matrix, countermeasures):
    """Create a trackable action item list from validation + countermeasures."""
    actions = []
    counter = 1

    for row in matrix[:3]:
        actions.append(
            {
                "ID": f"A{counter}",
                "Action": f"Validate cause: {row['Potential Cause']} "
                f"({row['Validation Method']}).",
                "Owner": "Assign",
                "Priority": "High",
                "Due Date": "TBD",
                "Status": "Open",
            }
        )
        counter += 1

    for cm in countermeasures:
        actions.append(
            {
                "ID": f"A{counter}",
                "Action": cm["Countermeasure"],
                "Owner": cm["Owner"],
                "Priority": "Medium",
                "Due Date": cm["Target Date"],
                "Status": "Open",
            }
        )
        counter += 1
    return actions


def build_verification_plan(inputs):
    """Define how the team will confirm the countermeasures actually worked."""
    outcome = clean_text(inputs.get("desired_outcome")) or (
        "The problem no longer recurs"
    )
    return [
        {
            "Verification Item": "Recurrence rate",
            "Method": "Track occurrences after the countermeasure is in place",
            "Frequency": "Weekly for 4-6 weeks",
            "Success Criteria": "No recurrence during the monitoring window",
            "Owner": "Assign",
        },
        {
            "Verification Item": "Desired outcome achieved",
            "Method": f"Confirm against the target: {outcome}",
            "Frequency": "At review checkpoints",
            "Success Criteria": "Target consistently met",
            "Owner": "Assign",
        },
        {
            "Verification Item": "Control effectiveness",
            "Method": "Audit that the new standard/check is followed",
            "Frequency": "Monthly",
            "Success Criteria": "Control applied consistently with no gaps",
            "Owner": "Assign",
        },
    ]


# --- Coaching -----------------------------------------------------------------

def generate_coaching(inputs, confidence_score):
    """Return process-focused coaching messages tailored to the inputs."""
    messages = [
        "Avoid jumping directly to solutions until the cause is validated.",
        "Use process-focused language and avoid assigning blame.",
    ]

    suspected = " ".join(parse_list(inputs.get("suspected_causes"))).lower()
    if any(term in suspected for term in SYMPTOM_TERMS):
        messages.append("This appears to be a symptom, not a root cause.")

    if not parse_list(inputs.get("evidence")):
        messages.append(
            "The issue may require more evidence before selecting permanent "
            "countermeasures."
        )

    if non_empty(inputs.get("containment")) or non_empty(inputs.get("workaround")):
        messages.append(
            "A containment action is temporary. A countermeasure should address "
            "the validated cause."
        )

    if confidence_score < 50:
        messages.append(
            "Confidence is low: treat the current root cause as a hypothesis and "
            "gather more facts before acting."
        )
    return messages


# --- A3 report ----------------------------------------------------------------

def build_a3_report(inputs, package):
    """Render a concise A3-style problem-solving report as Markdown."""
    conf = package["confidence"]
    mat = package["maturity"]
    rec = package["recurrence"]
    whys = "\n".join(
        f"{w['level']}. {w['question']} {w['because']}" for w in package["five_whys"]
    )
    countermeasures = "\n".join(
        f"- {c['Countermeasure']} _({c['Type']})_" for c in package["countermeasures"]
    )
    background = (
        clean_text(inputs.get("problem_statement"))
        or clean_text(inputs.get("title"))
        or "Not specified."
    )
    current = clean_text(inputs.get("what_happened")) or "See problem statement."
    impact = clean_text(inputs.get("impact")) or "Not specified."
    target = clean_text(inputs.get("desired_outcome")) or (
        "Eliminate recurrence of the problem."
    )
    containment = "; ".join(package.get("containment_plan", [])[:2]) or "None defined."

    return (
        "**A3 Problem-Solving Report**\n\n"
        f"**1. Background:** {background}\n\n"
        f"**2. Current Condition:** {current} _Impact:_ {impact}\n\n"
        f"**3. Target / Goal:** {target}\n\n"
        f"**4. Containment (temporary):** {containment}\n\n"
        f"**5. Root Cause Analysis (5 Whys):**\n{whys}\n\n"
        f"**6. Root Cause Hypothesis:** {package['root_cause_hypothesis']}\n\n"
        f"**7. Countermeasures:**\n{countermeasures}\n\n"
        "**8. Verification Plan:** Assign owners and due dates, validate the "
        "cause with the identified evidence, then confirm countermeasure "
        "effectiveness before closing.\n\n"
        f"**9. Follow-up / Scorecard:** Confidence {conf['score']}/100 "
        f"({conf['status']}); Maturity {mat['score']}/100 ({mat['status']}); "
        f"Recurrence risk {rec['level']}."
    )


# --- Section text builders ----------------------------------------------------

def build_executive_summary(inputs, package):
    conf = package["confidence"]
    rec = package["recurrence"]
    title = clean_text(inputs.get("title")) or "This problem"
    return (
        f"{title} is analyzed here using structured root cause methods. "
        f"The current root cause is a **{conf['status'].lower()}** "
        f"(confidence {conf['score']}/100) and recurrence risk is "
        f"**{rec['level']}**. The package below defines containment, a 5 Whys "
        "chain, fishbone analysis, a cause-and-evidence matrix, countermeasures, "
        "and a verification plan. Validate the root cause with evidence before "
        "committing to permanent countermeasures."
    )


def build_lessons_learned(inputs):
    return [
        "Separate symptoms from causes before choosing countermeasures.",
        "Containment protects the process; countermeasures fix the validated cause.",
        "Evidence quality drives confidence in the root cause hypothesis.",
        "A safeguard needs an owner and a review cadence to stay effective.",
    ]


def build_prevention_checklist(inputs):
    return [
        "Is there a documented standard for the affected process step?",
        "Is there a control that detects this condition early?",
        "Are owners assigned for the standard and the control?",
        "Is there a scheduled review to keep the safeguard effective?",
        "Is recurrence being monitored with a clear success criterion?",
        "Were lessons learned shared with related teams?",
    ]


def build_final_summary(inputs, package):
    conf = package["confidence"]
    mat = package["maturity"]
    rec = package["recurrence"]
    return (
        "This root cause package moves the problem from symptom to a validated "
        "hypothesis with clear next steps. "
        f"Root cause confidence is {conf['score']}/100 ({conf['status']}), "
        f"problem-solving maturity is {mat['score']}/100 ({mat['status']}), and "
        f"recurrence risk is {rec['level']}. "
        "The strongest next action is to collect the missing evidence, confirm "
        "the cause, assign owners and dates, and verify that the countermeasures "
        "hold before closing the problem."
    )


# --- Orchestrator -------------------------------------------------------------

def generate_package(inputs):
    """Generate the full structured root cause package from user inputs."""
    package = {
        "title": clean_text(inputs.get("title")) or "Untitled Problem",
        "category": clean_text(inputs.get("category")) or "Other",
        "created_at": now_iso(),
        "inputs": dict(inputs),
    }

    # Structured analysis components.
    package["refined_problem_statement"] = refine_problem_statement(inputs)
    package["problem_scope"] = build_problem_scope(inputs)
    package["impact_summary"] = build_impact_summary(inputs)
    package["containment_plan"] = build_containment_plan(inputs)
    package["five_whys"] = generate_five_whys(inputs)
    package["fishbone"] = generate_fishbone(inputs)
    package["cause_evidence_matrix"] = generate_cause_evidence_matrix(inputs)
    package["root_cause_hypothesis"] = build_root_cause_hypothesis(
        inputs, package["five_whys"]
    )
    package["contributing_factors"] = build_contributing_factors(inputs)
    package["countermeasures"] = build_countermeasures(
        inputs, package["root_cause_hypothesis"]
    )
    package["action_items"] = build_action_items(
        inputs, package["cause_evidence_matrix"], package["countermeasures"]
    )
    package["verification_plan"] = build_verification_plan(inputs)
    package["lessons_learned"] = build_lessons_learned(inputs)
    package["prevention_checklist"] = build_prevention_checklist(inputs)

    # Scores (depend on the structured components above).
    package["confidence"] = scoring.score_confidence(
        inputs, package["cause_evidence_matrix"]
    )
    package["recurrence"] = scoring.score_recurrence(
        inputs, package["confidence"]["score"]
    )
    package["maturity"] = scoring.score_maturity(inputs, package)

    # Narrative sections (depend on scores).
    package["executive_summary"] = build_executive_summary(inputs, package)
    package["coaching"] = generate_coaching(inputs, package["confidence"]["score"])
    package["a3_report"] = build_a3_report(inputs, package)
    package["final_summary"] = build_final_summary(inputs, package)

    return package
