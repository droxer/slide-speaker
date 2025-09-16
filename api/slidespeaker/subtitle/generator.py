"""
Subtitle generation module for SlideSpeaker (subtitle package).

Generates SRT and VTT subtitles from scripts and audio, using
multilingual sentence splitting and locale-aware timing allocation.
"""

import math
from datetime import timedelta
from pathlib import Path
from typing import Any

from loguru import logger

from ..audio import AudioGenerator
from ..configs.locales import locale_utils
from .text_segmentation import split_sentences
from .timing import calculate_chunk_durations


class SubtitleGenerator:
    """Generate SRT and VTT subtitle files from scripts and audio files"""

    def __init__(self) -> None:
        # Reuse shared audio duration helper to avoid duplication
        self.audio_generator = AudioGenerator()

    def generate_subtitles(
        self,
        scripts: list[dict[str, Any]],
        audio_files: list[Path],
        video_path: Path,
        language: str = "english",
    ) -> tuple[str, str]:
        """
        Generate SRT and VTT subtitle files

        Args:
            scripts: List of script dictionaries with slide_number and script content
            audio_files: List of audio file paths corresponding to each script
            video_path: Path to the final video file (used for naming subtitles)
            language: Language of the subtitles

        Returns:
            Tuple of (srt_path, vtt_path) paths to generated subtitle files
        """
        try:
            logger.info(
                f"Generating subtitles for {len(scripts)} scripts and {len(audio_files)} audio files"
            )
            # Validate inputs
            if not scripts:
                logger.warning("No scripts provided for subtitle generation")
                scripts = []

            if not audio_files:
                logger.warning("No audio files provided for subtitle generation")
                audio_files = []

            # Filter out empty scripts
            valid_scripts = []
            valid_audio_files = []

            for i, script_data in enumerate(scripts):
                script_text = (
                    script_data.get("script", "").strip() if script_data else ""
                )
                if script_text:
                    valid_scripts.append(script_data)
                    # Match with corresponding audio file if available
                    if i < len(audio_files):
                        valid_audio_files.append(audio_files[i])
                    else:
                        # Use a dummy path if no audio file is available
                        valid_audio_files.append(
                            Path(f"/tmp/dummy_audio_{len(valid_audio_files)}.mp3")
                        )

            if not valid_scripts:
                logger.warning("No valid scripts found for subtitle generation")
                # Create empty subtitle files
                srt_path = video_path.with_suffix(".srt")
                vtt_path = video_path.with_suffix(".vtt")

                # Write empty SRT file with header only
                with open(srt_path, "w", encoding="utf-8") as f:
                    f.write("")

                # Write empty VTT file with header only
                with open(vtt_path, "w", encoding="utf-8") as f:
                    f.write("WEBVTT\n\n")

                logger.info(f"Created empty subtitle files: {srt_path}, {vtt_path}")
                return str(srt_path), str(vtt_path)

            logger.info(f"Generating subtitles for {len(valid_scripts)} valid scripts")

            # Generate SRT subtitles
            srt_content = self._generate_srt_content(
                valid_scripts, valid_audio_files, language
            )
            srt_path = video_path.with_suffix(".srt")

            # Write SRT file
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(srt_content)

            # Generate VTT subtitles
            vtt_content = self._generate_vtt_content(
                valid_scripts, valid_audio_files, language
            )
            vtt_path = video_path.with_suffix(".vtt")

            # Write VTT file
            with open(vtt_path, "w", encoding="utf-8") as f:
                f.write(vtt_content)

            logger.info(f"Generated subtitles for {len(valid_scripts)} scripts")
            logger.info(f"SRT path: {srt_path}")
            logger.info(f"VTT path: {vtt_path}")

            # Verify files were created
            import os

            if os.path.exists(srt_path):
                logger.info(
                    f"SRT file created successfully, size: {os.path.getsize(srt_path)} bytes"
                )
            else:
                logger.error(f"Failed to create SRT file at {srt_path}")

            if os.path.exists(vtt_path):
                logger.info(
                    f"VTT file created successfully, size: {os.path.getsize(vtt_path)} bytes"
                )
            else:
                logger.error(f"Failed to create VTT file at {vtt_path}")

            return str(srt_path), str(vtt_path)

        except Exception as e:
            logger.error(f"Error generating subtitles: {e}")
            raise

    def _generate_srt_content(
        self,
        scripts: list[dict[str, Any]],
        audio_files: list[Path],
        language: str = "english",
    ) -> str:
        """
        Generate SRT subtitle content with text splitting for reasonable length
        """
        if not scripts or not audio_files:
            return ""

        logger.info(f"Generating SRT content for language: {language}")

        srt_lines = []
        start_time = timedelta(seconds=0)
        subtitle_number = 1
        max_cue_seconds = self._max_cue_seconds(language)

        for _i, (script_data, audio_path) in enumerate(
            zip(scripts, audio_files, strict=False)
        ):
            script_text = script_data.get("script", "").strip()
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

                # Split overly long cues by punctuation first; fall back to time slices
                total_secs = max(
                    0.0, (chunk_end_time - chunk_start_time).total_seconds()
                )
                if total_secs <= max_cue_seconds + 1e-3:
                    start_timestamp = self._format_srt_timestamp(chunk_start_time)
                    end_timestamp = self._format_srt_timestamp(chunk_end_time)
                    srt_lines.append(str(subtitle_number))
                    srt_lines.append(f"{start_timestamp} --> {end_timestamp}")
                    srt_lines.append(chunk)
                    srt_lines.append("")
                    subtitle_number += 1
                else:
                    parts = self._split_for_cue(chunk, language)
                    if len(parts) <= 1:
                        # Split by time only, repeating text
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
                            start_timestamp = self._format_srt_timestamp(seg_start)
                            end_timestamp = self._format_srt_timestamp(seg_end)
                            srt_lines.append(str(subtitle_number))
                            srt_lines.append(f"{start_timestamp} --> {end_timestamp}")
                            srt_lines.append(chunk)
                            srt_lines.append("")
                            subtitle_number += 1
                    else:
                        # Allocate time proportionally to parts; cap each part by max_cue_seconds
                        # and merge ultra-short cues (<0.9s) into neighbors where possible.
                        raw_durs = calculate_chunk_durations(
                            total_secs, parts, chunk, language
                        )
                        min_cue = 0.9
                        # Merge small parts forward into subsequent parts
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
                        last_seg_end: timedelta | None = None
                        for p_text, p_dur in zip(
                            merged_parts, merged_durs, strict=False
                        ):
                            remaining = p_dur
                            while remaining > 1e-6:
                                seg_dur = min(remaining, max_cue_seconds)
                                # Avoid creating a tiny tail; absorb into this segment
                                if 0 < remaining - seg_dur < min_cue:
                                    seg_dur = remaining
                                seg_end = cursor + timedelta(seconds=seg_dur)
                                # If this segment is ultra-short and we have
                                # a previous segment, merge into previous
                                if (
                                    last_seg_end is not None
                                    and seg_dur < min_cue
                                    and len(srt_lines) >= 4
                                ):
                                    # Merge by extending previous segment end and appending text
                                    # Previous block starts 4 lines earlier: [num, timing, text, blank]
                                    prev_timing_idx = len(srt_lines) - 3
                                    prev_text_idx = len(srt_lines) - 2
                                    # Extend previous end timestamp
                                    prev_timing = srt_lines[prev_timing_idx]
                                    # prev_timing format: "HH:MM:SS,mmm --> HH:MM:SS,mmm"
                                    new_prev_timing = (
                                        prev_timing.split(" --> ")[0]
                                        + " --> "
                                        + self._format_srt_timestamp(seg_end)
                                    )
                                    srt_lines[prev_timing_idx] = new_prev_timing
                                    # Append text
                                    srt_lines[prev_text_idx] = (
                                        srt_lines[prev_text_idx] + " " + p_text
                                    ).strip()
                                else:
                                    start_timestamp = self._format_srt_timestamp(cursor)
                                    end_timestamp = self._format_srt_timestamp(seg_end)
                                    srt_lines.append(str(subtitle_number))
                                    srt_lines.append(
                                        f"{start_timestamp} --> {end_timestamp}"
                                    )
                                    srt_lines.append(p_text)
                                    srt_lines.append("")
                                    subtitle_number += 1
                                last_seg_end = seg_end
                                cursor = seg_end
                                remaining -= seg_dur

                start_time = chunk_end_time

        return "\n".join(srt_lines)

    def _generate_vtt_content(
        self,
        scripts: list[dict[str, Any]],
        audio_files: list[Path],
        language: str = "english",
    ) -> str:
        """Generate VTT subtitle content with text splitting for reasonable length"""
        if not scripts or not audio_files:
            return "WEBVTT\n\n"

        logger.info(f"Generating VTT content for language: {language}")

        lang_code = locale_utils.get_locale_code(language)
        vtt_lines = [f"WEBVTT Language: {lang_code}", ""]
        start_time = timedelta(seconds=0)
        max_cue_seconds = self._max_cue_seconds(language)

        for _i, (script_data, audio_path) in enumerate(
            zip(scripts, audio_files, strict=False)
        ):
            script_text = script_data.get("script", "").strip()
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

                # Split overly long cues by punctuation first; fall back to time slices
                total_secs = max(
                    0.0, (chunk_end_time - chunk_start_time).total_seconds()
                )
                if total_secs <= max_cue_seconds + 1e-3:
                    start_timestamp = self._format_vtt_timestamp(chunk_start_time)
                    end_timestamp = self._format_vtt_timestamp(chunk_end_time)
                    vtt_lines.append(f"{start_timestamp} --> {end_timestamp}")
                    vtt_lines.append(chunk)
                    vtt_lines.append("")
                else:
                    parts = self._split_for_cue(chunk, language)
                    if len(parts) <= 1:
                        # Split by time only, repeating text
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
                            start_timestamp = self._format_vtt_timestamp(seg_start)
                            end_timestamp = self._format_vtt_timestamp(seg_end)
                            vtt_lines.append(f"{start_timestamp} --> {end_timestamp}")
                            vtt_lines.append(chunk)
                            vtt_lines.append("")
                    else:
                        # Allocate time proportionally to parts; cap each part by max_cue_seconds
                        # and merge ultra-short cues (<0.9s) into neighbors where possible.
                        raw_durs = calculate_chunk_durations(
                            total_secs, parts, chunk, language
                        )
                        min_cue = 0.9
                        # Merge small parts forward into subsequent parts
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
                        last_text_idx: int | None = None
                        for p_text, p_dur in zip(
                            merged_parts, merged_durs, strict=False
                        ):
                            remaining = p_dur
                            while remaining > 1e-6:
                                seg_dur = min(remaining, max_cue_seconds)
                                if 0 < remaining - seg_dur < min_cue:
                                    seg_dur = remaining
                                const_seg_end = cursor + timedelta(seconds=seg_dur)
                                start_timestamp = self._format_vtt_timestamp(cursor)
                                end_timestamp = self._format_vtt_timestamp(
                                    const_seg_end
                                )

                                # If this segment is ultra-short and there is a prior cue, merge text and extend timing
                                if seg_dur < min_cue and last_text_idx is not None:
                                    # Update previous timing end
                                    timing_idx = last_text_idx - 1
                                    prev_timing = vtt_lines[timing_idx]
                                    vtt_lines[timing_idx] = (
                                        prev_timing.split(" --> ")[0]
                                        + " --> "
                                        + end_timestamp
                                    )
                                    # Append text
                                    vtt_lines[last_text_idx] = (
                                        vtt_lines[last_text_idx] + " " + p_text
                                    ).strip()
                                else:
                                    vtt_lines.append(
                                        f"{start_timestamp} --> {end_timestamp}"
                                    )
                                    vtt_lines.append(p_text)
                                    vtt_lines.append("")
                                    last_text_idx = len(vtt_lines) - 2

                                cursor = const_seg_end
                                remaining -= seg_dur

                start_time = chunk_end_time

        return "\n".join(vtt_lines)

    def _max_cue_seconds(self, language: str | None) -> float:
        """
        Maximum duration per subtitle cue, language-aware if needed.
        Keep cues reasonably short for readability and syncing.
        """
        lang = (language or "").lower()
        if lang in {"simplified_chinese", "traditional_chinese", "japanese", "korean"}:
            return 5.5
        if lang in {"thai"}:
            return 6.0
        return 7.0

    def _split_for_cue(self, text: str, language: str) -> list[str]:
        """Split cue text into smaller parts for long cues.
        Uses language-aware sentence splitting with stricter fallback lengths.
        """
        lang = (language or "").lower()
        if lang in {"simplified_chinese", "traditional_chinese", "japanese", "korean"}:
            # Tighter fallback for dense scripts
            parts = split_sentences(text, max_fallback_len=25)
        elif lang in {"thai"}:
            parts = split_sentences(text, max_fallback_len=30)
        else:
            parts = split_sentences(text, max_fallback_len=40)
        return [p for p in parts if p and p.strip()]

    def _split_text_for_subtitles(self, text: str, language: str) -> list[str]:
        # Use the shared sentence splitter with fallback chunk length tailored
        # Slightly shorter fallback for readability
        chunks = split_sentences(text, max_fallback_len=60)
        if chunks:
            return chunks
        return [text]

    def _format_srt_timestamp(self, td: timedelta) -> str:
        total_seconds = td.total_seconds()
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        milliseconds = int((total_seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

    def _format_vtt_timestamp(self, td: timedelta) -> str:
        total_seconds = td.total_seconds()
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        milliseconds = int((total_seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
