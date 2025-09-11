"""
Utilities for rendering transcripts to Markdown.

Provides helper functions to convert per-slide or per-chapter transcripts
into a single Markdown document and small fragments for intermediate state
persistence and potential UI display.
"""

from collections.abc import Iterable, Mapping
from typing import Any


def transcripts_to_markdown(
    items: Iterable[Mapping[str, Any]],
    *,
    section_label: str = "Slide",
    filename: str | None = None,
) -> str:
    """
    Convert a sequence of transcript items to a Markdown document.

    Each item is expected to contain either:
      - "slide_number" (int|str) or "chapter_number" (int|str) identifying the order
      - "script" (str) with the transcript text

    Args:
        items: Iterable of transcript dict-like objects
        section_label: Label to use for section headers (e.g., "Slide" or "Chapter")

    Returns:
        Markdown string with one section per item.
    """
    lines: list[str] = ["# Transcripts"]
    if filename:
        lines.extend(["", f"File: {filename}", ""])
    else:
        lines.append("")
    for idx, item in enumerate(items, 1):
        number = (
            str(item.get("slide_number"))
            if item.get("slide_number") is not None
            else (
                str(item.get("chapter_number"))
                if item.get("chapter_number") is not None
                else str(idx)
            )
        )
        title = str(item.get("title") or "").strip()
        description = str(item.get("description") or "").strip()
        key_points = item.get("key_points")
        if not isinstance(key_points, list):
            key_points = []
        script = str(item.get("script") or "").strip()

        # Section header: "<number> - <title>" (omit label prefix per request)
        header = f"{number} - {title}" if title else str(number)
        lines.append(f"## {header}")
        lines.append("")

        # Include details if present
        if description:
            lines.append(f"- Description: {description}")
        if key_points:
            lines.append("- Key Points:")
            for kp in key_points:
                lines.append(f"  - {str(kp)}")
        # Always include script, even if empty placeholder
        lines.append("- Script:")
        lines.append("")
        lines.append(script if script else "_(no content)_")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
