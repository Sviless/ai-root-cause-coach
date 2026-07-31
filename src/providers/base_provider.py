"""Base provider interface for root cause analysis generation."""

from abc import ABC, abstractmethod


class BaseProvider(ABC):
    """Common interface every generation provider must implement.

    Implementations return a dict with a stable shape so the UI, exporters, and
    storage never need to know which provider produced the analysis:

        {
            "package": <dict>,   # the full root cause package (18 sections)
            "mode":    <str>,    # the mode actually used to generate it
            "notice":  <str|None>,  # optional user-facing message (e.g. fallback)
        }
    """

    #: Human-readable provider/mode name, e.g. "Template Engine Mode".
    name = "Base Provider"

    @abstractmethod
    def generate_root_cause_analysis(self, input_data):
        """Generate a root cause package from the user's input dict."""
        raise NotImplementedError
