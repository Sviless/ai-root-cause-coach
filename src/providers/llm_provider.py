"""LLM Enhanced Mode provider (future-ready).

This provider is prepared for a future connection to an external LLM but does
NOT make any network calls yet and does NOT require an API key for the app to
run. Behavior:

- If no LLM_API_KEY is configured, it transparently falls back to Template
  Engine Mode and returns a friendly notice.
- If an LLM_API_KEY is configured, it builds a strong, provider-neutral prompt
  (ready for OpenAI, Azure OpenAI, Claude, or another provider) and — until a
  real integration is added — still returns Template Engine Mode output as a
  preview, so the app always produces a complete package.

The single place to add a real API call is `_call_llm()`.
"""

from src import config
from src.config import MODE_TEMPLATE, MODE_LLM
from src.providers.base_provider import BaseProvider
from src.providers.template_provider import TemplateProvider
from src.utils import clean_text

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

# Target JSON structure the future LLM should return. This is a *parsing target*
# for a later integration: when `_call_llm()` is implemented, the model's JSON
# response can be mapped directly into the package shape used by the UI and
# exporters. The current version still displays Template Engine Mode text output,
# so this schema is forward-looking only and is embedded into the prompt.
TARGET_JSON_SCHEMA = """{
  "executive_summary": "",
  "refined_problem_statement": "",
  "problem_scope": "",
  "impact_summary": "",
  "containment_plan": [],
  "five_whys": [],
  "fishbone_analysis": {
    "people": [],
    "process": [],
    "tools_or_technology": [],
    "materials_or_inputs": [],
    "environment": [],
    "measurement_or_data": [],
    "communication": [],
    "management_system": []
  },
  "cause_evidence_matrix": [],
  "likely_root_cause_hypothesis": "",
  "contributing_factors": [],
  "countermeasure_plan": [],
  "action_item_tracker": [],
  "verification_plan": [],
  "recurrence_risk_assessment": "",
  "a3_style_report": "",
  "lessons_learned": [],
  "prevention_checklist": [],
  "final_summary": ""
}"""


def build_llm_prompt(input_data):
    """Build a structured, non-blaming prompt for a future LLM call.

    Provider-neutral: the same prompt works for OpenAI, Azure OpenAI, Claude,
    or another chat/completions API.

    The prompt asks the model to return a single JSON object matching
    TARGET_JSON_SCHEMA below. That schema is the *future parsing target*: when a
    real LLM integration is added, `_call_llm()` can parse this JSON straight
    into the package shape used by the UI and exporters. The current version
    still displays Template Engine Mode text output, so this schema is
    forward-looking only.
    """
    fields = "\n".join(
        f"- {key.replace('_', ' ').title()}: {clean_text(value)}"
        for key, value in input_data.items()
        if clean_text(value)
    )
    categories = "\n".join(f"  {i + 1}. {c}" for i, c in enumerate(FISHBONE_CATEGORIES))

    return f"""ROLE
You are an expert Lean problem-solving and root cause analysis coach, operational
excellence leader, and A3 thinking practitioner. Turn the problem below into a
rigorous, evidence-based root cause analysis.

TONE AND PRINCIPLES
- Use professional, process-focused, non-blaming language at all times.
- Never attribute the problem to individuals. Focus on gaps in process, system,
  tool, method, data, environment, training, communication, or control.
- Separate symptoms from causes. Mark the root cause as a HYPOTHESIS unless it is
  validated by evidence.
- Coaching reminders to reflect in the content:
  * Containment is temporary; it protects the process while the cause is
    investigated.
  * Countermeasures must address the validated root cause, not the symptom.
  * Do not commit to permanent countermeasures until the cause is evidence-backed.

PROBLEM INPUT
{fields}

ANALYSIS REQUIREMENTS
1. Define the problem clearly and refine a fact-based problem statement.
2. Generate a logical 5 Whys chain ending in a plausible, clearly-labeled root
   cause hypothesis.
3. Generate a fishbone (Ishikawa) analysis using EXACTLY these categories:
{categories}
4. Generate a cause-and-evidence matrix. Each row must include: potential cause,
   evidence supporting, evidence missing, validation method, confidence level,
   and recommended next step.
5. Provide a containment plan (temporary) AND a countermeasure plan (permanent,
   tied to the validated cause), plus an action item tracker and a verification
   plan to confirm effectiveness.
6. Provide recurrence-prevention actions and a prevention checklist.
7. Provide three scores from 0 to 100, each with a short rationale:
   - Root cause confidence
   - Problem-solving maturity
   - Recurrence risk
8. Provide an A3-style problem-solving report and lessons learned.

OUTPUT FORMAT
Return a SINGLE valid JSON object and nothing else (no markdown, no commentary).
Use this exact schema and key names. Use arrays where shown; use "" for text
fields when a value is unknown. Do not add or rename keys.

{TARGET_JSON_SCHEMA}

FIELD GUIDANCE
- "five_whys": array of objects like
  {{"level": 1, "question": "Why ...?", "because": "Because ..."}}.
- Each "fishbone_analysis" category is an array of short cause strings.
- "cause_evidence_matrix": array of objects with keys
  "potential_cause", "evidence_supporting", "evidence_missing",
  "validation_method", "confidence_level", "recommended_next_step".
- "countermeasure_plan": array of objects with keys
  "countermeasure", "type", "addresses", "owner", "target_date".
- "action_item_tracker": array of objects with keys
  "id", "action", "owner", "priority", "due_date", "status".
- "verification_plan": array of objects with keys
  "verification_item", "method", "frequency", "success_criteria", "owner".
- "recurrence_risk_assessment": a text summary that states the risk level
  (Low / Medium / High) and the reasoning.
- Include the three scores inside the relevant summaries (root cause confidence
  in the hypothesis/executive summary, maturity and recurrence risk in their
  summaries) so no score information is lost.

Keep every field non-blaming and process-focused."""


def _call_llm(prompt):
    """Placeholder for a real LLM API call. Not implemented yet.

    To connect a provider later, implement this function using the configured
    provider (config.get_llm_provider_name()) and the LLM_API_KEY from the
    environment (read via os.getenv inside the SDK, never hardcoded). Parse the
    response into the same package shape produced by template_engine, then
    return that package dict.

    Example (pseudo-code, do not enable without adding the dependency):

        provider = config.get_llm_provider_name()
        if provider == "openai":
            # from openai import OpenAI
            # client = OpenAI()  # reads OPENAI_API_KEY / LLM_API_KEY
            # response = client.chat.completions.create(...)
            ...
        elif provider == "azure":
            ...
        elif provider == "claude":
            ...
        # return parsed_package
    """
    raise NotImplementedError(
        "A real LLM integration has not been added yet. See _call_llm()."
    )


class LLMProvider(BaseProvider):
    """Future-ready provider. Falls back to Template Engine Mode when needed."""

    name = MODE_LLM

    def __init__(self):
        self._fallback = TemplateProvider()

    def generate_root_cause_analysis(self, input_data):
        # No API key: use Template Engine Mode and tell the user clearly.
        if not config.has_llm_api_key():
            result = self._fallback.generate_root_cause_analysis(input_data)
            result["mode"] = MODE_TEMPLATE
            result["notice"] = (
                "LLM Enhanced Mode is not configured. The app will use Template "
                "Engine Mode instead."
            )
            return result

        # API key present. Build the prompt for a future call. We deliberately
        # do NOT call an external service yet (no external dependency), so we
        # return Template Engine Mode output as a preview to keep the app fully
        # functional. Swap in `_call_llm(prompt)` when a provider is added.
        prompt = build_llm_prompt(input_data)
        # response_package = _call_llm(prompt)  # <-- enable in the future

        result = self._fallback.generate_root_cause_analysis(input_data)
        result["mode"] = MODE_LLM
        result["notice"] = (
            "LLM Enhanced Mode is prepared but not yet connected to a provider. "
            "Showing Template Engine Mode output as a preview."
        )
        result["prompt_preview"] = prompt
        return result
