"""
Transcript utility functions.

Provides sanitization helpers to remove references to visual UI elements
from generated transcripts, keeping narration content-focused.
"""

import re

_UI_PHRASES = [
    r"\bon (this|the) slide(s)?\b",
    r"\bin (this|the) slide(s)?\b",
    r"\bon the screen\b",
    r"\bas (shown|displayed)( here)?\b",
    r"\bas you can see( here)?\b",
    r"\bhere we (can )?see\b",
    r"\bin the following slide\b",
    r"\bthe (diagram|chart|graph|image|picture|visual|table)\b",
]

_UI_REGEX = re.compile("|".join(_UI_PHRASES), flags=re.IGNORECASE)


def sanitize_transcript(text: str) -> str:
    """Remove common references to visual UI elements from transcript text.

    The sanitizer is conservative: it removes phrases like
    "on this slide", "as shown", "as you can see", and noun phrases like
    "the chart" that typically precede a visual reference. It then tidies
    excess whitespace.
    """
    if not text:
        return text
    # Remove UI phrases
    cleaned = _UI_REGEX.sub("", text)
    # Collapse extra spaces and stray punctuation spacing
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
    cleaned = re.sub(r"\(\s+\)", "()", cleaned)
    return cleaned.strip()
