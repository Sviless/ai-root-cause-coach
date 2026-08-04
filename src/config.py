"""Configuration and environment handling.

Reads environment variables to decide whether an optional LLM provider is
available. The API key is never printed, logged, or returned to callers — only
a boolean "is it configured?" is exposed.

The app runs fully without any environment variables (Template Engine Mode).
"""

import os

# Canonical, user-facing mode names used across the app.
MODE_TEMPLATE = "Template Engine Mode"
MODE_LLM = "LLM Enhanced Mode"


def _load_dotenv(path=".env"):
    """Load simple KEY=VALUE pairs from a local .env file if one exists.

    Values already present in the real environment take precedence. This keeps
    a convenient .env workflow without adding a third-party dependency.
    """
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except OSError:
        # A missing or unreadable .env file must never break the app.
        pass


_load_dotenv()


def has_llm_api_key():
    """True when an LLM API key is configured. The key itself is never exposed."""
    return bool(_read_llm_api_key())


def _read_llm_api_key():
    """Internal: return the configured LLM API key (GEMINI_API_KEY or LLM_API_KEY).

    Kept private so the key is only read where a request is actually made. It is
    never printed, logged, or returned by any public helper.
    """
    return (
        os.getenv("GEMINI_API_KEY", "").strip()
        or os.getenv("LLM_API_KEY", "").strip()
    )


def get_llm_provider_name():
    """Selected LLM provider: gemini | openai | azure | claude.

    If LLM_PROVIDER is set it wins. Otherwise, when only a GEMINI_API_KEY is
    present the provider defaults to "gemini" so the app works out of the box.
    """
    explicit = os.getenv("LLM_PROVIDER", "").strip().lower()
    if explicit:
        return explicit
    if os.getenv("GEMINI_API_KEY", "").strip():
        return "gemini"
    return "openai"


def get_llm_model():
    """Optional model name (LLM_MODEL or GEMINI_MODEL); empty means provider default."""
    return (
        os.getenv("LLM_MODEL", "").strip()
        or os.getenv("GEMINI_MODEL", "").strip()
    )


def resolve_mode(requested):
    """Return (effective_mode, notice) for a requested generation mode.

    Falls back to Template Engine Mode when LLM Enhanced Mode is requested but
    no API key is configured.
    """
    if requested == MODE_LLM and not has_llm_api_key():
        return (
            MODE_TEMPLATE,
            "LLM Enhanced Mode is not configured. The app will use Template "
            "Engine Mode instead.",
        )
    return requested, None
