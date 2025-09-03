from datetime import timedelta
from pathlib import Path
from typing import Any

from loguru import logger

from ..utils.locales import locale_utils


class SubtitleGenerator:
    """Generate SRT and VTT subtitle files from scripts and audio files"""

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

            logger.info(f"Attempting to write SRT file to: {srt_path}")
            logger.info(f"SRT content length: {len(srt_content)} characters")

            # Write SRT file
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(srt_content)

            # Generate VTT subtitles
            vtt_content = self._generate_vtt_content(
                valid_scripts, valid_audio_files, language
            )
            vtt_path = video_path.with_suffix(".vtt")

            logger.info(f"Attempting to write VTT file to: {vtt_path}")
            logger.info(f"VTT content length: {len(vtt_content)} characters")

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
        Generate SRT subtitle content

        Args:
            scripts: List of script dictionaries with slide_number and script content
            audio_files: List of audio file paths corresponding to each script
            language: Language of the subtitles

        Returns:
            SRT formatted subtitle content as string
        """
        if not scripts or not audio_files:
            return ""

        # Log the language being used for debugging
        logger.info(f"Generating SRT content for language: {language}")

        srt_lines = []
        start_time = timedelta(seconds=0)
        subtitle_number = 1

        for _i, (script_data, audio_path) in enumerate(
            zip(scripts, audio_files, strict=False)
        ):
            # Get script content
            script_text = script_data.get("script", "").strip()
            if not script_text:
                continue

            # Calculate duration from audio file
            duration = (
                self._get_audio_duration(audio_path) if audio_path.exists() else 5.0
            )

            # Calculate end time
            end_time = start_time + timedelta(seconds=duration)

            # Format timestamps (SRT format: HH:MM:SS,mmm)
            start_timestamp = self._format_srt_timestamp(start_time)
            end_timestamp = self._format_srt_timestamp(end_time)

            # Add subtitle entry
            srt_lines.append(str(subtitle_number))  # Subtitle number
            srt_lines.append(f"{start_timestamp} --> {end_timestamp}")  # Time range
            srt_lines.append(script_text)  # Subtitle text
            srt_lines.append("")  # Empty line separator

            # Update subtitle number and start time for next subtitle
            subtitle_number += 1
            start_time = end_time

        return "\n".join(srt_lines)

    def _generate_vtt_content(
        self,
        scripts: list[dict[str, Any]],
        audio_files: list[Path],
        language: str = "english",
    ) -> str:
        """
        Generate VTT subtitle content

        Args:
            scripts: List of script dictionaries with slide_number and script content
            audio_files: List of audio file paths corresponding to each script
            language: Language of the subtitles

        Returns:
            VTT formatted subtitle content as string
        """
        if not scripts or not audio_files:
            return "WEBVTT\n\n"

        # Log the language being used for debugging
        logger.info(f"Generating VTT content for language: {language}")

        # Include language in VTT header for better compatibility
        lang_code = locale_utils.get_locale_code(language)
        vtt_lines = [f"WEBVTT Language: {lang_code}", ""]  # VTT header with language
        start_time = timedelta(seconds=0)

        for _i, (script_data, audio_path) in enumerate(
            zip(scripts, audio_files, strict=False)
        ):
            # Get script content
            script_text = script_data.get("script", "").strip()
            if not script_text:
                continue

            # Calculate duration from audio file
            duration = (
                self._get_audio_duration(audio_path) if audio_path.exists() else 5.0
            )

            # Calculate end time
            end_time = start_time + timedelta(seconds=duration)

            # Format timestamps (VTT format: HH:MM:SS.mmm)
            start_timestamp = self._format_vtt_timestamp(start_time)
            end_timestamp = self._format_vtt_timestamp(end_time)

            # Add subtitle entry
            vtt_lines.append(f"{start_timestamp} --> {end_timestamp}")  # Time range
            vtt_lines.append(script_text)  # Subtitle text
            vtt_lines.append("")  # Empty line separator

            # Update start time for next subtitle
            start_time = end_time

        return "\n".join(vtt_lines)

    def _get_audio_duration(self, audio_path: Path) -> float:
        """
        Get duration of audio file using ffprobe

        Args:
            audio_path: Path to audio file

        Returns:
            Duration in seconds
        """
        try:
            import json
            import subprocess

            # Use ffprobe to get audio duration
            cmd = [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(audio_path),
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            data = json.loads(result.stdout)

            # Try to get duration from format first
            if "format" in data and "duration" in data["format"]:
                return float(data["format"]["duration"])

            # If not in format, check streams
            if "streams" in data:
                for stream in data["streams"]:
                    if "duration" in stream:
                        return float(stream["duration"])

            # Default to 5 seconds if we can't determine duration
            return 5.0

        except Exception as e:
            logger.warning(f"Could not determine audio duration for {audio_path}: {e}")
            return 5.0  # Default to 5 seconds

    def _format_srt_timestamp(self, td: timedelta) -> str:
        """
        Format timedelta as SRT timestamp (HH:MM:SS,mmm)

        Args:
            td: Timedelta object

        Returns:
            Formatted timestamp string
        """
        total_seconds = td.total_seconds()
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        milliseconds = int((total_seconds % 1) * 1000)

        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

    def _format_vtt_timestamp(self, td: timedelta) -> str:
        """
        Format timedelta as VTT timestamp (HH:MM:SS.mmm)

        Args:
            td: Timedelta object

        Returns:
            Formatted timestamp string
        """
        total_seconds = td.total_seconds()
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        milliseconds = int((total_seconds % 1) * 1000)

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
