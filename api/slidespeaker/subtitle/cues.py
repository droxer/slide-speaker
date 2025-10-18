"""
Shared cue-building utilities for subtitle generation.

Builds timed cues from scripts and audio with language-aware splitting,
duration allocation, and short-cue merging.
"""

from __future__ import annotations

import math
import re
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
        if not scripts:
            return cues
        start_time = timedelta(seconds=0)
        max_cue_seconds = self._max_cue_seconds(language)
        audio_paths = list(audio_files or [])

        for idx, script_data in enumerate(scripts):
            script_text = script_data.get("script", "").strip() if script_data else ""
            if not script_text:
                continue
            audio_path = audio_paths[idx] if idx < len(audio_paths) else None
            duration = self._resolve_duration(audio_path, script_text)
            # Ensure we have a minimum duration to prevent timestamp issues
            duration = max(0.5, duration)
            if duration <= 0:
                logger.warning(f"Skipping segment with zero duration at index {idx}")
                continue
            text_chunks = self._normalize_chunks(
                self._split_text_for_subtitles(script_text, language)
            )
            chunk_durations = calculate_chunk_durations(
                duration, text_chunks, script_text, language
            )
            # Ensure no chunk durations are zero to prevent duplicate timestamps
            min_chunk_duration = 0.1
            chunk_durations = [max(min_chunk_duration, dur) for dur in chunk_durations]
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

                # Ensure chunk end time is after start time to prevent zero-duration cues
                min_cue_duration = 0.1
                if chunk_end_time <= chunk_start_time:
                    chunk_end_time = chunk_start_time + timedelta(
                        seconds=min_cue_duration
                    )

                total_secs = max(
                    0.1, (chunk_end_time - chunk_start_time).total_seconds()
                )
                if total_secs <= max_cue_seconds + 1e-3:
                    self._append_cue(cues, chunk_start_time, chunk_end_time, chunk)
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
                            # Ensure segment end time is after start time
                            if seg_end <= seg_start:
                                seg_end = seg_start + timedelta(seconds=0.1)
                            self._append_cue(cues, seg_start, seg_end, chunk)
                    else:
                        raw_durs = calculate_chunk_durations(
                            total_secs, parts, chunk, language
                        )
                        # Ensure no durations are zero
                        min_duration = 0.1
                        raw_durs = [max(min_duration, dur) for dur in raw_durs]

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
                                merged_durs.append(max(min_duration, acc_dur))
                                acc_text = ""
                                acc_dur = 0.0
                        if acc_text:
                            merged_parts.append(acc_text)
                            merged_durs.append(max(min_duration, acc_dur))

                        cursor = chunk_start_time
                        for p_text, p_dur in zip(
                            merged_parts, merged_durs, strict=False
                        ):
                            remaining = max(0.1, p_dur)
                            while remaining > 1e-6:
                                seg_dur = min(remaining, max_cue_seconds)
                                if 0 < remaining - seg_dur < min_cue:
                                    seg_dur = remaining
                                seg_end = cursor + timedelta(seconds=seg_dur)
                                # Ensure segment end time is after start time
                                if seg_end <= cursor:
                                    seg_end = cursor + timedelta(seconds=0.1)
                                self._append_cue(cues, cursor, seg_end, p_text)
                                cursor = seg_end
                                remaining -= seg_dur
                start_time = max(start_time, chunk_end_time)
        logger.info(f"Built {len(cues)} cues for subtitles")
        return cues

    def _resolve_duration(self, audio_path: Path | None, script_text: str) -> float:
        cleaned_text = (script_text or "").strip()
        estimated = self._estimate_duration_from_text(cleaned_text)
        min_reasonable = max(1.0, estimated * 0.35)
        if audio_path:
            try:
                duration = float(self.audio_generator._get_audio_duration(audio_path))
                # Treat implausibly short clips as invalid and fall back to textual estimate
                if duration < min_reasonable:
                    return estimated
                return max(0.5, duration)
            except Exception:
                pass
        return max(1.0, estimated)

    def _estimate_duration_from_text(self, text: str) -> float:
        if not text:
            return 1.5

        compact = re.sub(r"\s+", "", text)
        char_count = max(1, len(compact))
        is_cjk = bool(
            re.search(
                r"[\u3040-\u30FF\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\uAC00-\uD7AF]",
                compact,
            )
        )

        if is_cjk:
            avg_chars_per_sec = 5.0  # slower rate for logographic scripts
            estimated = char_count / avg_chars_per_sec
            return max(2.0, estimated)

        tokens = re.findall(r"[A-Za-z0-9']+", text)
        word_count = max(1, len(tokens) or len(text.split()))
        avg_words_per_sec = 2.6  # ~156 WPM
        estimated = word_count / avg_words_per_sec
        return max(1.5, estimated)

    def _normalize_chunks(self, chunks: list[str]) -> list[str]:
        """Merge redundant or punctuation-only chunks to avoid duplicate cues."""
        normalized: list[str] = []
        for chunk in chunks:
            chunk = (chunk or "").strip()
            if not chunk:
                continue
            if re.fullmatch(r"[。！？?!,.、；;：:…·—\-]+", chunk):
                if normalized:
                    normalized[-1] = f"{normalized[-1].rstrip()}{chunk}"
                else:
                    normalized.append(chunk)
                continue
            if normalized and chunk == normalized[-1]:
                continue
            normalized.append(chunk)
        return normalized

    def _append_cue(
        self,
        cues: list[tuple[timedelta, timedelta, str]],
        start: timedelta,
        end: timedelta,
        text: str,
    ) -> None:
        """Append a cue, merging with previous one when text repeats."""
        cleaned_text = text.strip()
        if not cleaned_text:
            return
        if end <= start:
            end = start + timedelta(seconds=0.1)
        if cues and cues[-1][2] == cleaned_text:
            prev_start, prev_end, prev_text = cues[-1]
            cues[-1] = (prev_start, max(prev_end, end), prev_text)
        else:
            cues.append((start, end, cleaned_text))

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
