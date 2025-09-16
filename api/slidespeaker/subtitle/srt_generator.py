"""
SRT subtitle content generator.

Formats cues into SRT text.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any

from .cues import CueBuilder


def _format_srt_timestamp(td: timedelta) -> str:
    total_seconds = td.total_seconds()
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    milliseconds = int((total_seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def generate_srt_content(
    scripts: list[dict[str, Any]], audio_files: list[Path], language: str
) -> str:
    builder = CueBuilder()
    cues = builder.build_cues(scripts, audio_files, language)
    lines: list[str] = []
    for idx, (start_td, end_td, text) in enumerate(cues, start=1):
        lines.append(str(idx))
        lines.append(
            f"{_format_srt_timestamp(start_td)} --> {_format_srt_timestamp(end_td)}"
        )
        lines.append(text)
        lines.append("")
    return "\n".join(lines)
