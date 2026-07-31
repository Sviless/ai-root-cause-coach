"""Input validation and problem-statement quality checks.

The goal is to catch missing information and gently coach the user toward a
clearer, more fact-based problem definition before analysis runs.
"""

from src.utils import clean_text, non_empty, parse_list, contains_any

# Fields that must be present before a meaningful analysis can be generated.
REQUIRED_FIELDS = {
    "title": "Problem title",
    "category": "Problem category",
    "problem_statement": "Problem statement",
    "what_happened": "What happened",
    "impact": "Business or operational impact",
}

# Words that usually signal a solution or a symptom rather than a problem.
SOLUTION_TERMS = ["should", "need to", "must", "just", "simply", "fix it by", "add more"]
SYMPTOM_TERMS = ["slow", "broken", "error", "crash", "fails", "down", "late", "wrong"]
VAGUE_TERMS = ["stuff", "things", "somehow", "whatever", "bad", "weird"]


def validate_inputs(inputs):
    """Validate inputs.

    Returns a tuple: (is_valid, missing_labels, warnings).
    """
    missing = [
        label
        for key, label in REQUIRED_FIELDS.items()
        if not non_empty(inputs.get(key))
    ]
    warnings = quality_warnings(inputs)
    return (len(missing) == 0, missing, warnings)


def quality_warnings(inputs):
    """Return a list of non-blocking coaching warnings about input quality."""
    warnings = []

    statement = clean_text(inputs.get("problem_statement"))
    if statement and len(statement.split()) < 6:
        warnings.append(
            "Problem statement is very short. Add detail about what is happening, "
            "where, and how often."
        )

    if statement and contains_any(statement, SOLUTION_TERMS):
        warnings.append(
            "The problem statement may contain a solution. Describe the problem "
            "first; countermeasures come after the cause is validated."
        )

    if contains_any(statement, VAGUE_TERMS) or contains_any(
        inputs.get("what_happened"), VAGUE_TERMS
    ):
        warnings.append(
            "Some wording is vague. Replace general terms with specific, "
            "observable facts."
        )

    if not parse_list(inputs.get("evidence")):
        warnings.append(
            "No evidence was provided. Evidence strengthens the root cause "
            "hypothesis and raises the confidence score."
        )

    if not non_empty(inputs.get("frequency")):
        warnings.append(
            "Frequency is missing. How often the problem occurs helps assess "
            "recurrence risk."
        )

    if not non_empty(inputs.get("containment")):
        warnings.append(
            "No containment action was provided. Containment protects the "
            "customer or process while the root cause is investigated."
        )

    if not parse_list(inputs.get("known_facts")):
        warnings.append(
            "No known facts were listed. Fact-based analysis prevents jumping "
            "to conclusions."
        )

    return warnings
