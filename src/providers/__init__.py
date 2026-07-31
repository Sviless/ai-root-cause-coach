"""Provider package: pluggable generation backends.

The app calls a provider through the common interface in `base_provider.py`
instead of calling template functions directly. This makes it easy to add a
future LLM-backed provider without changing the UI, exporters, or storage.
"""

from src.config import MODE_TEMPLATE, MODE_LLM
from src.providers.template_provider import TemplateProvider
from src.providers.llm_provider import LLMProvider

__all__ = ["get_provider", "TemplateProvider", "LLMProvider"]


def get_provider(mode):
    """Return a provider instance for the requested generation mode.

    Unknown modes default to Template Engine Mode so the app always works.
    """
    if mode == MODE_LLM:
        return LLMProvider()
    return TemplateProvider()
