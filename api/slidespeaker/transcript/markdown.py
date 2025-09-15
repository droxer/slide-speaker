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
    Convert a sequence of transcript items to a strict Markdown document.

    Strict format required:
      # <file_name>

      ## <Section Title>
      <transcripts>

    Notes:
      - The document title is the original filename when provided.
      - Section title prefers the item's "title". If missing, it falls back to
        "{section_label} {number}".
      - Only the transcript text is emitted under each section; no extra labels
        (no Description/Key Points/Script lists).
    """
    # Title: prefer the provided filename; otherwise a neutral fallback
    title_text = (
        filename.strip() if isinstance(filename, str) and filename else "Transcripts"
    )
    lines: list[str] = [f"# {title_text}", ""]

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
        raw_title = str(item.get("title") or "").strip()
        header_title = raw_title if raw_title else f"{section_label} {number}"
        script = str(item.get("script") or "").strip()

        # Section header and body
        lines.append(f"## {header_title}")
        lines.append(script)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
