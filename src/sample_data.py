"""Generic, portfolio-safe sample problems.

None of these reference any real company, system, employee, or proprietary
process. They exist only to let users explore the app quickly.
"""

SAMPLE_PROBLEMS = [
    {
        "title": "Nightly data pipeline finishes late",
        "category": "Data",
        "problem_statement": (
            "The nightly reporting pipeline has been finishing after the 6:00 AM "
            "business deadline, so morning dashboards are not ready when teams "
            "start their day."
        ),
        "what_happened": (
            "The batch job that aggregates daily metrics completed at 7:40 AM "
            "instead of the expected 5:30 AM."
        ),
        "where_happened": "Scheduled batch reporting environment",
        "when_happened": "Observed over the last two weeks, worse on Mondays",
        "frequency": "Recurring, roughly 3-4 times per week",
        "impact": (
            "Morning stand-ups start without current numbers; teams make "
            "decisions on stale data, and support reports customer-facing delays."
        ),
        "symptoms": (
            "Job runtime increased from 90 minutes to over 4 hours\n"
            "Occasional retries on the aggregation step\n"
            "Dashboards show yesterday's data at 8:00 AM"
        ),
        "containment": (
            "Manually re-run the job at 5:00 AM and post a note when data is late."
        ),
        "known_facts": (
            "Runtime doubled after the reporting window grew\n"
            "No change to the server hardware\n"
            "Input volume increased about 40% this quarter"
        ),
        "suspected_causes": (
            "Growing input volume\n"
            "Inefficient aggregation query\n"
            "Overlap with another scheduled job"
        ),
        "evidence": (
            "Job runtime logs for the last 30 days\n"
            "Row-count trend showing input growth"
        ),
        "people": "Reporting team, platform on-call",
        "process_step": "Nightly aggregation and load step",
        "workaround": "Manual early re-run and a delayed-data banner",
        "previous_attempts": (
            "Increased the retry count last month; runtime did not improve."
        ),
        "desired_outcome": (
            "Pipeline reliably completes before 5:30 AM every business day."
        ),
        "risks": (
            "Continued stale dashboards erode trust in reporting and slow "
            "morning decisions."
        ),
        "notes": "Weekend runs are smaller and usually finish on time.",
    },
    {
        "title": "Repeated defects escaping to the customer",
        "category": "Quality",
        "problem_statement": (
            "The same category of defect keeps reaching customers even after "
            "individual fixes are shipped."
        ),
        "what_happened": (
            "Three similar customer-reported defects appeared in one month, all "
            "tied to unhandled edge cases in input validation."
        ),
        "where_happened": "Order intake workflow",
        "when_happened": "Across the last three release cycles",
        "frequency": "Recurring each release, 1-2 similar defects",
        "impact": (
            "Customers experience failed submissions; support handles repeat "
            "tickets and rework increases."
        ),
        "symptoms": (
            "Similar error signatures across releases\n"
            "Fixes address one case but not the pattern\n"
            "Regression tests do not cover the edge cases"
        ),
        "containment": "Add a temporary input check and monitor error rates.",
        "known_facts": (
            "Each defect passed existing automated tests\n"
            "No shared checklist for edge-case validation\n"
            "Fixes were made under time pressure"
        ),
        "suspected_causes": (
            "Missing standard for edge-case testing\n"
            "No pattern review after defects\n"
            "Inconsistent validation across modules"
        ),
        "evidence": (
            "Defect reports with error signatures\n"
            "Test coverage report for the intake module"
        ),
        "people": "Development team, quality reviewers",
        "process_step": "Pre-release validation and review",
        "workaround": "Manual spot-checks before release",
        "previous_attempts": (
            "Patched each defect individually; the pattern kept recurring."
        ),
        "desired_outcome": (
            "The defect pattern is prevented, not just individual instances."
        ),
        "risks": "Continued escapes damage customer trust and increase rework.",
        "notes": "Defects cluster around unusual but valid input combinations.",
    },
    {
        "title": "Onboarding takes too long for new team members",
        "category": "Process",
        "problem_statement": (
            "New team members take much longer than expected to become "
            "productive, and the onboarding steps are unclear."
        ),
        "what_happened": (
            "Recent joiners needed about six weeks to complete setup and their "
            "first independent task, versus a two-week target."
        ),
        "where_happened": "Team onboarding process",
        "when_happened": "Last three new hires",
        "frequency": "Every new hire",
        "impact": (
            "Delayed ramp-up reduces team capacity and frustrates new members."
        ),
        "symptoms": (
            "Setup steps are scattered across many places\n"
            "New members wait on access approvals\n"
            "No single owner for onboarding"
        ),
        "containment": "Assign a temporary onboarding buddy to each new hire.",
        "known_facts": (
            "No single onboarding checklist exists\n"
            "Access requests are handled ad hoc\n"
            "Documentation is outdated in places"
        ),
        "suspected_causes": (
            "Missing standardized onboarding process\n"
            "Unclear ownership\n"
            "Outdated documentation"
        ),
        "evidence": (
            "Time-to-first-task for the last three hires\n"
            "Feedback notes from new members"
        ),
        "people": "Team lead, onboarding buddies",
        "process_step": "New hire setup and first assignment",
        "workaround": "Buddies answer questions as they come up",
        "previous_attempts": (
            "Shared a document once, but it was not maintained."
        ),
        "desired_outcome": (
            "New members reach their first independent task within two weeks."
        ),
        "risks": "Slow onboarding limits growth and lowers early engagement.",
        "notes": "Access approvals are the most common blocker mentioned.",
    },
]


def get_sample(index=0):
    """Return a copy of a sample problem by index."""
    return dict(SAMPLE_PROBLEMS[index % len(SAMPLE_PROBLEMS)])


def sample_titles():
    """Return the list of sample problem titles for selection."""
    return [p["title"] for p in SAMPLE_PROBLEMS]
