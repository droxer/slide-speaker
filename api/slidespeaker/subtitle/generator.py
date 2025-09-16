"""
Subtitle generation facade for SlideSpeaker.

Delegates SRT and VTT content creation to dedicated modules to avoid duplication.
"""

from pathlib import Path
from typing import Any

from loguru import logger

from .srt_generator import generate_srt_content
from .vtt_generator import generate_vtt_content


class SubtitleGenerator:
    """Generate SRT and VTT subtitle files from scripts and audio files."""

    def generate_subtitles(
        self,
        scripts: list[dict[str, Any]],
        audio_files: list[Path],
        video_path: Path,
        language: str = "english",
    ) -> tuple[str, str]:
        """
        Generate SRT and VTT subtitle files and write them next to `video_path`.

        Returns tuple of (srt_path, vtt_path) as strings.
        """
        try:
            logger.info(
                f"Generating subtitles for {len(scripts)} scripts and {len(audio_files)} audio files"
            )

            # Normalize inputs
            scripts = scripts or []
            audio_files = audio_files or []

            # Filter to scripts with non-empty text; align audio list by index
            valid_scripts: list[dict[str, Any]] = []
            valid_audio_files: list[Path] = []
            for i, script_data in enumerate(scripts):
                text = (script_data or {}).get("script", "").strip()
                if not text:
                    continue
                valid_scripts.append(script_data)
                if i < len(audio_files):
                    valid_audio_files.append(audio_files[i])

            srt_path = video_path.with_suffix(".srt")
            vtt_path = video_path.with_suffix(".vtt")

            if not valid_scripts:
                # Create empty subtitle files
                with open(srt_path, "w", encoding="utf-8") as f:
                    f.write("")
                with open(vtt_path, "w", encoding="utf-8") as f:
                    f.write("WEBVTT\n\n")
                logger.info(f"Created empty subtitle files: {srt_path}, {vtt_path}")
                return str(srt_path), str(vtt_path)

            # Build contents via dedicated modules
            srt_content = generate_srt_content(
                valid_scripts, valid_audio_files, language
            )
            vtt_content = generate_vtt_content(
                valid_scripts, valid_audio_files, language
            )

            # Write files
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(srt_content)
            with open(vtt_path, "w", encoding="utf-8") as f:
                f.write(vtt_content)

            logger.info(
                f"Generated subtitles: SRT={srt_path} (len={len(srt_content)}), VTT={vtt_path} (len={len(vtt_content)})"
            )

            return str(srt_path), str(vtt_path)

        except Exception as e:
            logger.error(f"Error generating subtitles: {e}")
            raise
