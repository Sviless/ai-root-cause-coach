"""Utility helpers for text cleanup, list parsing, and formatting.

These helpers are intentionally small and dependency-free so that every
other module can rely on consistent text handling.
"""

import re
from datetime import datetime


def clean_text(value):
    """Return a stripped string for any input (None becomes empty string)."""
    if value is None:
        return ""
    return str(value).strip()


def non_empty(value):
    """True when a value contains real (non-whitespace) content."""
    return bool(clean_text(value))


def parse_list(text):
    """Split multi-line or delimited text into a clean list of items.

    Accepts newlines, semicolons, or common bullet markers as separators.
    """
    if not text:
        return []
    parts = re.split(r"[\n;]+", str(text))
    items = []
    for part in parts:
        cleaned = part.strip().lstrip("-*•").strip()
        if cleaned:
            items.append(cleaned)
    return items


def first_sentence(text, fallback=""):
    """Return the first sentence of a block of text."""
    text = clean_text(text)
    if not text:
        return fallback
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return sentences[0] if sentences and sentences[0] else fallback


def truncate(text, length=140):
    """Shorten text to a maximum length with an ellipsis."""
    text = clean_text(text)
    if len(text) <= length:
        return text
    return text[:length].rstrip() + "..."


def as_bullets(items, empty="_None provided_"):
    """Render a list of items as Markdown bullets."""
    if not items:
        return empty
    return "\n".join(f"- {item}" for item in items)


def now_iso():
    """Current timestamp as a readable string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def safe_filename(text, default="root_cause"):
    """Convert arbitrary text into a filesystem-safe file name fragment."""
    text = clean_text(text) or default
    text = re.sub(r"[^A-Za-z0-9_-]+", "_", text).strip("_")
    return (text or default)[:60]


def contains_any(text, keywords):
    """True when the lowercased text contains any of the keywords."""
    text = clean_text(text).lower()
    return any(keyword in text for keyword in keywords)
