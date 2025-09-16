"""
Shared cue-building utilities for subtitle generation.

Builds timed cues from scripts and audio with language-aware splitting,
duration allocation, and short-cue merging.
"""

from __future__ import annotations

import math
from datetime import timedelta
from pathlib import Path
from typing import Any

from loguru import logger

from ..audio import AudioGenerator
from .text_segmentation import split_sentences
from .timing import calculate_chunk_durations


class CueBuilder:
    def __init__(self) -> None:
        self.audio_generator = AudioGenerator()

    def build_cues(
        self,
        scripts: list[dict[str, Any]],
        audio_files: list[Path],
        language: str,
    ) -> list[tuple[timedelta, timedelta, str]]:
        cues: list[tuple[timedelta, timedelta, str]] = []
        if not scripts or not audio_files:
            return cues
        start_time = timedelta(seconds=0)
        max_cue_seconds = self._max_cue_seconds(language)
        for _i, (script_data, audio_path) in enumerate(
            zip(scripts, audio_files, strict=False)
        ):
            script_text = script_data.get("script", "").strip() if script_data else ""
            if not script_text:
                continue
            duration = self.audio_generator._get_audio_duration(audio_path)
            text_chunks = self._split_text_for_subtitles(script_text, language)
            chunk_durations = calculate_chunk_durations(
                duration, text_chunks, script_text, language
            )
            for j, (chunk, chunk_duration) in enumerate(
                zip(text_chunks, chunk_durations, strict=False)
            ):
                chunk_start_time = start_time
                if j == len(text_chunks) - 1:
                    elapsed_time = sum(chunk_durations[:j])
                    chunk_end_time = start_time + timedelta(
                        seconds=duration - elapsed_time
                    )
                else:
                    chunk_end_time = start_time + timedelta(seconds=chunk_duration)

                total_secs = max(
                    0.0, (chunk_end_time - chunk_start_time).total_seconds()
                )
                if total_secs <= max_cue_seconds + 1e-3:
                    cues.append((chunk_start_time, chunk_end_time, chunk))
                else:
                    parts = self._split_for_cue(chunk, language)
                    if len(parts) <= 1:
                        segments = max(
                            2, int(math.ceil(total_secs / max(0.01, max_cue_seconds)))
                        )
                        seg_len = total_secs / segments
                        for s in range(segments):
                            seg_start = chunk_start_time + timedelta(
                                seconds=seg_len * s
                            )
                            seg_end = (
                                chunk_end_time
                                if s == segments - 1
                                else chunk_start_time
                                + timedelta(seconds=seg_len * (s + 1))
                            )
                            cues.append((seg_start, seg_end, chunk))
                    else:
                        raw_durs = calculate_chunk_durations(
                            total_secs, parts, chunk, language
                        )
                        min_cue = 0.9
                        merged_parts: list[str] = []
                        merged_durs: list[float] = []
                        acc_text = ""
                        acc_dur = 0.0
                        for p_text, p_dur in zip(parts, raw_durs, strict=False):
                            if not acc_text:
                                acc_text = p_text
                                acc_dur = p_dur
                            else:
                                acc_text = f"{acc_text} {p_text}".strip()
                                acc_dur += p_dur
                            if acc_dur >= min_cue:
                                merged_parts.append(acc_text)
                                merged_durs.append(acc_dur)
                                acc_text = ""
                                acc_dur = 0.0
                        if acc_text:
                            merged_parts.append(acc_text)
                            merged_durs.append(acc_dur)

                        cursor = chunk_start_time
                        for p_text, p_dur in zip(
                            merged_parts, merged_durs, strict=False
                        ):
                            remaining = p_dur
                            while remaining > 1e-6:
                                seg_dur = min(remaining, max_cue_seconds)
                                if 0 < remaining - seg_dur < min_cue:
                                    seg_dur = remaining
                                seg_end = cursor + timedelta(seconds=seg_dur)
                                cues.append((cursor, seg_end, p_text))
                                cursor = seg_end
                                remaining -= seg_dur
                start_time = chunk_end_time
        logger.info(f"Built {len(cues)} cues for subtitles")
        return cues

    def _max_cue_seconds(self, language: str | None) -> float:
        lang = (language or "").lower()
        if lang in {"simplified_chinese", "traditional_chinese", "japanese", "korean"}:
            return 5.5
        if lang in {"thai"}:
            return 6.0
        return 7.0

    def _split_for_cue(self, text: str, language: str) -> list[str]:
        lang = (language or "").lower()
        if lang in {"simplified_chinese", "traditional_chinese", "japanese", "korean"}:
            parts = split_sentences(text, max_fallback_len=25)
        elif lang in {"thai"}:
            parts = split_sentences(text, max_fallback_len=30)
        else:
            parts = split_sentences(text, max_fallback_len=40)
        return [p for p in parts if p and p.strip()]

    def _split_text_for_subtitles(self, text: str, language: str) -> list[str]:
        chunks = split_sentences(text, max_fallback_len=60)
        if chunks:
            return chunks
        return [text]
