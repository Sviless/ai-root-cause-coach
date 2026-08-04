"""LLM Enhanced Mode provider.

Supports Google Gemini as a real LLM backend while keeping the app fully
functional without any API key. Behavior:

- If no API key is configured, it transparently falls back to Template Engine
  Mode and returns a friendly notice.
- If a Gemini API key is configured (GEMINI_API_KEY or LLM_API_KEY with
  LLM_PROVIDER=gemini), it calls the Gemini API, parses the structured JSON
  response, and overlays it onto a locally-generated base package. Scores stay
  locally computed for transparency. Any error (network, quota, bad JSON) falls
  back to Template Engine Mode with a clear notice, so the app never breaks.

The network call uses only the Python standard library (urllib), so no extra
dependency is required.
"""

import json
import urllib.error
import urllib.request

from src import config
from src.config import MODE_TEMPLATE, MODE_LLM
from src.providers.base_provider import BaseProvider
from src.providers.template_provider import TemplateProvider
from src.utils import clean_text

GEMINI_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent?key={key}"
)
DEFAULT_GEMINI_MODEL = "gemini-1.5-flash"

# Maps the LLM's snake_case fishbone keys to the display category names the UI
# and exporters expect.
_FISHBONE_KEY_MAP = {
    "people": "People",
    "process": "Process",
    "tools_or_technology": "Tools or Technology",
    "materials_or_inputs": "Materials or Inputs",
    "environment": "Environment",
    "measurement_or_data": "Measurement or Data",
    "communication": "Communication",
    "management_system": "Management System",
}


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


def _call_gemini(prompt, model, api_key, timeout=60):
    """Call the Gemini API and return the model's raw text response.

    Uses the standard-library HTTP client. Requests JSON output via
    response_mime_type so the model returns a single JSON object.
    """
    url = GEMINI_ENDPOINT.format(model=model, key=api_key)
    body = json.dumps(
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.4,
                "response_mime_type": "application/json",
            },
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))

    candidates = payload.get("candidates") or []
    if not candidates:
        raise ValueError("Gemini returned no candidates.")
    parts = candidates[0].get("content", {}).get("parts") or []
    text = "".join(part.get("text", "") for part in parts).strip()
    if not text:
        raise ValueError("Gemini returned an empty response.")
    return text


def _parse_json_object(text):
    """Parse a JSON object from the model text, tolerating code fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```", 2)[1] if "```" in cleaned[3:] else cleaned[3:]
        if cleaned.lstrip().lower().startswith("json"):
            cleaned = cleaned.lstrip()[4:]
    cleaned = cleaned.strip().strip("`").strip()
    return json.loads(cleaned)


def _as_str_list(value):
    """Coerce an LLM value into a clean list of non-empty strings."""
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    out = []
    for item in value:
        if isinstance(item, dict):
            item = " — ".join(str(v) for v in item.values() if str(v).strip())
        text = clean_text(str(item))
        if text:
            out.append(text)
    return out


def _titleize_rows(rows):
    """Turn LLM row dicts into display rows with Title Case headers."""
    if not isinstance(rows, list):
        return []
    out = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        out.append(
            {str(k).replace("_", " ").title(): clean_text(str(v)) for k, v in row.items()}
        )
    return out


def _map_five_whys(value):
    """Normalize LLM five_whys into [{level, question, because}]."""
    if not isinstance(value, list):
        return []
    out = []
    for i, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            continue
        question = clean_text(str(item.get("question", "")))
        because = clean_text(str(item.get("because", item.get("answer", ""))))
        if not question and not because:
            continue
        out.append(
            {
                "level": item.get("level", i),
                "question": question or f"Why? (level {i})",
                "because": because,
            }
        )
    return out


def _map_fishbone(value):
    """Map LLM snake_case fishbone dict to display-category -> [causes]."""
    if not isinstance(value, dict):
        return {}
    out = {}
    for raw_key, causes in value.items():
        display = _FISHBONE_KEY_MAP.get(str(raw_key).strip().lower())
        if not display:
            continue
        items = _as_str_list(causes)
        if items:
            out[display] = items
    return out


def apply_llm_package(base_package, llm_json):
    """Overlay Gemini's structured output onto a locally-generated base package.

    The base package guarantees every section, the correct sub-structures, and
    locally-computed scores. This function replaces narrative and structured
    content with the LLM's version wherever it provided usable data, and leaves
    the base value untouched otherwise. Scores are intentionally kept local for
    transparency.
    """
    if not isinstance(llm_json, dict):
        return base_package

    def _text(key):
        val = llm_json.get(key)
        return clean_text(val) if isinstance(val, str) and clean_text(val) else None

    text_map = {
        "executive_summary": "executive_summary",
        "refined_problem_statement": "refined_problem_statement",
        "problem_scope": "problem_scope",
        "impact_summary": "impact_summary",
        "likely_root_cause_hypothesis": "root_cause_hypothesis",
        "a3_style_report": "a3_report",
        "final_summary": "final_summary",
    }
    for src_key, dest_key in text_map.items():
        value = _text(src_key)
        if value:
            base_package[dest_key] = value

    list_map = {
        "containment_plan": "containment_plan",
        "contributing_factors": "contributing_factors",
        "lessons_learned": "lessons_learned",
        "prevention_checklist": "prevention_checklist",
    }
    for src_key, dest_key in list_map.items():
        items = _as_str_list(llm_json.get(src_key))
        if items:
            base_package[dest_key] = items

    five_whys = _map_five_whys(llm_json.get("five_whys"))
    if five_whys:
        base_package["five_whys"] = five_whys

    fishbone = _map_fishbone(llm_json.get("fishbone_analysis"))
    if fishbone:
        base_package["fishbone"] = fishbone

    row_map = {
        "cause_evidence_matrix": "cause_evidence_matrix",
        "countermeasure_plan": "countermeasures",
        "action_item_tracker": "action_items",
        "verification_plan": "verification_plan",
    }
    for src_key, dest_key in row_map.items():
        rows = _titleize_rows(llm_json.get(src_key))
        if rows:
            base_package[dest_key] = rows

    return base_package


class LLMProvider(BaseProvider):
    """LLM-backed provider. Falls back to Template Engine Mode when needed."""

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
                "Engine Mode instead. Set GEMINI_API_KEY to enable Gemini."
            )
            return result

        provider = config.get_llm_provider_name()

        # Only Gemini is wired to a real API today; other providers fall back.
        if provider != "gemini":
            result = self._fallback.generate_root_cause_analysis(input_data)
            result["mode"] = MODE_TEMPLATE
            result["notice"] = (
                f"Provider '{provider}' is not connected yet. Using Template "
                "Engine Mode. Set LLM_PROVIDER=gemini to use Gemini."
            )
            return result

        base = self._fallback.generate_root_cause_analysis(input_data)["package"]
        prompt = build_llm_prompt(input_data)
        model = config.get_llm_model() or DEFAULT_GEMINI_MODEL

        try:
            raw = _call_gemini(prompt, model, config._read_llm_api_key())
            llm_json = _parse_json_object(raw)
            package = apply_llm_package(base, llm_json)
            return {
                "package": package,
                "mode": MODE_LLM,
                "notice": (
                    f"Generated with Google Gemini ({model}). Scores are computed "
                    "locally for transparency."
                ),
            }
        except (urllib.error.URLError, urllib.error.HTTPError) as exc:
            reason = getattr(exc, "reason", exc)
            notice = (
                f"Could not reach Gemini ({reason}). Showing Template Engine Mode "
                "output instead."
            )
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            notice = (
                f"Gemini response could not be parsed ({exc}). Showing Template "
                "Engine Mode output instead."
            )

        return {"package": base, "mode": MODE_TEMPLATE, "notice": notice}

