"""
VTT subtitle content generator.

Formats cues into VTT text with language header.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any

from ..configs.locales import locale_utils
from .cues import CueBuilder


def _format_vtt_timestamp(td: timedelta) -> str:
    total_seconds = td.total_seconds()
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    milliseconds = int((total_seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


def generate_vtt_content(
    scripts: list[dict[str, Any]], audio_files: list[Path], language: str
) -> str:
    builder = CueBuilder()
    cues = builder.build_cues(scripts, audio_files, language)
    lang_code = locale_utils.get_locale_code(language)
    lines: list[str] = [f"WEBVTT Language: {lang_code}", ""]
    for start_td, end_td, text in cues:
        lines.append(
            f"{_format_vtt_timestamp(start_td)} --> {_format_vtt_timestamp(end_td)}"
        )
        lines.append(text)
        lines.append("")
    return "\n".join(lines)
