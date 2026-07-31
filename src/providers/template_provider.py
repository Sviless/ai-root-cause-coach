"""Template Engine Mode provider.

Wraps the existing local generation logic (template_engine + scoring +
validators + utils). This is the default provider and requires no API key.
It preserves all 18 output sections of the root cause package.
"""

from src import template_engine
from src.config import MODE_TEMPLATE
from src.providers.base_provider import BaseProvider


class TemplateProvider(BaseProvider):
    """Local, rule-based provider — the default generation mode."""

    name = MODE_TEMPLATE

    def generate_root_cause_analysis(self, input_data):
        # Reuse the existing, fully-tested Template Engine Mode pipeline.
        package = template_engine.generate_package(input_data)
        return {"package": package, "mode": self.name, "notice": None}
