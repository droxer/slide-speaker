"""
Subtitle generation module for SlideSpeaker.

This module generates timed subtitle files (SRT and VTT formats) from presentation scripts.
It synchronizes subtitles with audio durations when available and supports multiple languages.
"""

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
        Generate SRT subtitle content with text splitting for reasonable length

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

            # Split long text into reasonable chunks
            text_chunks = self._split_text_for_subtitles(script_text, max_chars=42)

            # Calculate time per chunk
            time_per_chunk = duration / len(text_chunks)

            for chunk in text_chunks:
                chunk_start_time = start_time
                chunk_end_time = start_time + timedelta(seconds=time_per_chunk)

                # Format timestamps (SRT format: HH:MM:SS,mmm)
                start_timestamp = self._format_srt_timestamp(chunk_start_time)
                end_timestamp = self._format_srt_timestamp(chunk_end_time)

                # Add subtitle entry
                srt_lines.append(str(subtitle_number))
                srt_lines.append(f"{start_timestamp} --> {end_timestamp}")
                srt_lines.append(chunk)
                srt_lines.append("")

                # Update for next subtitle
                subtitle_number += 1
                start_time = chunk_end_time

        return "\n".join(srt_lines)

    def _generate_vtt_content(
        self,
        scripts: list[dict[str, Any]],
        audio_files: list[Path],
        language: str = "english",
    ) -> str:
        """
        Generate VTT subtitle content with text splitting for reasonable length

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

            # Split long text into reasonable chunks
            text_chunks = self._split_text_for_subtitles(script_text, max_chars=42)

            # Calculate time per chunk
            time_per_chunk = duration / len(text_chunks)

            for chunk in text_chunks:
                chunk_start_time = start_time
                chunk_end_time = start_time + timedelta(seconds=time_per_chunk)

                # Format timestamps (VTT format: HH:MM:SS.mmm)
                start_timestamp = self._format_vtt_timestamp(chunk_start_time)
                end_timestamp = self._format_vtt_timestamp(chunk_end_time)

                # Add subtitle entry
                vtt_lines.append(f"{start_timestamp} --> {end_timestamp}")
                vtt_lines.append(chunk)
                vtt_lines.append("")

                # Update start time for next subtitle
                start_time = chunk_end_time

        return "\n".join(vtt_lines)

    def _split_text_for_subtitles(self, text: str, max_chars: int = 42) -> list[str]:
        """
        Split long text into smaller chunks suitable for subtitles

        Args:
            text: The text to split
            max_chars: Maximum characters per subtitle chunk

        Returns:
            List of text chunks
        """
        if not text:
            return []

        # Clean and normalize text
        text = text.strip()

        # If text is short enough, return as single chunk
        if len(text) <= max_chars:
            return [text]

        # Split by sentences first, then by word boundaries
        chunks = []

        # Try to split by sentence boundaries first
        sentences = []
        current = ""

        # Split by common sentence endings
        for char in text:
            current += char
            if char in ".!?;" and len(current.strip()) > 20:
                if current.strip():
                    sentences.append(current.strip())
                current = ""

        if current.strip():
            sentences.append(current.strip())

        # If we have good sentence splits, use them
        if len(sentences) > 1:
            for sentence in sentences:
                if len(sentence) <= max_chars:
                    chunks.append(sentence)
                else:
                    # Split long sentences by comma or space
                    chunks.extend(self._split_long_sentence(sentence, max_chars))
        else:
            # Split long text by words
            chunks.extend(self._split_long_sentence(text, max_chars))

        # Ensure no chunk is empty
        chunks = [chunk.strip() for chunk in chunks if chunk.strip()]

        return chunks if chunks else [text]

    def _split_long_sentence(self, sentence: str, max_chars: int) -> list[str]:
        """Split a long sentence by word boundaries"""
        words = sentence.split()
        chunks = []
        current = ""

        for word in words:
            if len(current + " " + word) <= max_chars:
                if current:
                    current += " " + word
                else:
                    current = word
            else:
                if current:
                    chunks.append(current)
                current = word

                # If single word is too long, split it
                if len(current) > max_chars:
                    # Split by character count
                    for i in range(0, len(current), max_chars):
                        chunks.append(current[i : i + max_chars])
                    current = ""

        if current:
            chunks.append(current)

        return chunks

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

    async def generate_subtitles_for_text(
        self,
        text: str,
        duration: float,
        output_path: Path,
        language: str = "english",
    ) -> tuple[str, str]:
        """
        Generate SRT and VTT subtitle files for a single text with a given duration.

        Args:
            text: Text content for subtitles
            duration: Duration in seconds for the subtitle
            output_path: Path to save the subtitle files (without extension)
            language: Language of the subtitles

        Returns:
            Tuple of (srt_path, vtt_path) paths to generated subtitle files
        """
        try:
            if not text.strip():
                logger.warning("Empty text provided for subtitle generation")
                # Create empty subtitle files
                srt_path = output_path.with_suffix(".srt")
                vtt_path = output_path.with_suffix(".vtt")

                # Write empty SRT file with header only
                with open(srt_path, "w", encoding="utf-8") as f:
                    f.write("")

                # Write empty VTT file with header only
                with open(vtt_path, "w", encoding="utf-8") as f:
                    f.write("WEBVTT\n\n")

                logger.info(f"Created empty subtitle files: {srt_path}, {vtt_path}")
                return str(srt_path), str(vtt_path)

            logger.info(f"Generating subtitles for text with duration {duration}s")

            # Generate SRT content
            srt_content = self._generate_srt_content_for_text(text, duration, language)
            srt_path = output_path.with_suffix(".srt")

            logger.info(f"Attempting to write SRT file to: {srt_path}")
            logger.info(f"SRT content length: {len(srt_content)} characters")

            # Write SRT file
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(srt_content)

            # Generate VTT content
            vtt_content = self._generate_vtt_content_for_text(text, duration, language)
            vtt_path = output_path.with_suffix(".vtt")

            logger.info(f"Attempting to write VTT file to: {vtt_path}")
            logger.info(f"VTT content length: {len(vtt_content)} characters")

            # Write VTT file
            with open(vtt_path, "w", encoding="utf-8") as f:
                f.write(vtt_content)

            logger.info("Generated subtitles for text")
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
            logger.error(f"Error generating subtitles for text: {e}")
            raise

    def _generate_srt_content_for_text(
        self,
        text: str,
        duration: float,
        language: str = "english",
    ) -> str:
        """
        Generate SRT subtitle content for a single text with a given duration.

        Args:
            text: Text content for subtitles
            duration: Duration in seconds
            language: Language of the subtitles

        Returns:
            SRT formatted subtitle content as string
        """
        if not text.strip():
            return ""

        # Log the language being used for debugging
        logger.info(f"Generating SRT content for language: {language}")

        srt_lines = []

        # Split long text into reasonable chunks
        text_chunks = self._split_text_for_subtitles(text, max_chars=42)

        # Calculate time per chunk
        time_per_chunk = duration / len(text_chunks) if text_chunks else duration

        start_time = timedelta(seconds=0)
        subtitle_number = 1

        for chunk in text_chunks:
            chunk_start_time = start_time
            chunk_end_time = start_time + timedelta(seconds=time_per_chunk)

            # Format timestamps (SRT format: HH:MM:SS,mmm)
            start_timestamp = self._format_srt_timestamp(chunk_start_time)
            end_timestamp = self._format_srt_timestamp(chunk_end_time)

            # Add subtitle entry
            srt_lines.append(str(subtitle_number))
            srt_lines.append(f"{start_timestamp} --> {end_timestamp}")
            srt_lines.append(chunk)
            srt_lines.append("")

            # Update for next subtitle
            subtitle_number += 1
            start_time = chunk_end_time

        return "\n".join(srt_lines)

    def _generate_vtt_content_for_text(
        self,
        text: str,
        duration: float,
        language: str = "english",
    ) -> str:
        """
        Generate VTT subtitle content for a single text with a given duration.

        Args:
            text: Text content for subtitles
            duration: Duration in seconds
            language: Language of the subtitles

        Returns:
            VTT formatted subtitle content as string
        """
        if not text.strip():
            return "WEBVTT\n\n"

        # Log the language being used for debugging
        logger.info(f"Generating VTT content for language: {language}")

        # Include language in VTT header for better compatibility
        lang_code = locale_utils.get_locale_code(language)
        vtt_lines = [f"WEBVTT Language: {lang_code}", ""]  # VTT header with language

        # Split long text into reasonable chunks
        text_chunks = self._split_text_for_subtitles(text, max_chars=42)

        # Calculate time per chunk
        time_per_chunk = duration / len(text_chunks) if text_chunks else duration

        start_time = timedelta(seconds=0)

        for chunk in text_chunks:
            chunk_start_time = start_time
            chunk_end_time = start_time + timedelta(seconds=time_per_chunk)

            # Format timestamps (VTT format: HH:MM:SS.mmm)
            start_timestamp = self._format_vtt_timestamp(chunk_start_time)
            end_timestamp = self._format_vtt_timestamp(chunk_end_time)

            # Add subtitle entry
            vtt_lines.append(f"{start_timestamp} --> {end_timestamp}")
            vtt_lines.append(chunk)
            vtt_lines.append("")

            # Update start time for next subtitle
            start_time = chunk_end_time

        return "\n".join(vtt_lines)

    def combine_srt_files(self, srt_files: list[Path], output_path: Path) -> str:
        """
        Combine multiple SRT files into a single SRT file with adjusted timestamps.

        Args:
            srt_files: List of paths to SRT files to combine
            output_path: Path where the combined SRT file will be saved

        Returns:
            Path to the combined SRT file
        """
        try:
            combined_lines: list[str] = []
            current_time_offset = timedelta(seconds=0)

            for srt_file in srt_files:
                if not srt_file.exists():
                    logger.warning(f"SRT file not found: {srt_file}")
                    continue

                with open(srt_file, encoding="utf-8") as f:
                    content = f.read().strip()

                if not content:
                    continue

                # Parse SRT blocks and adjust timestamps
                blocks = content.split("\n\n")
                for block in blocks:
                    if not block.strip():
                        continue

                    lines = block.split("\n")
                    if len(lines) < 3:
                        continue

                    # First line is subtitle number (we'll renumber)
                    # Second line is timestamp
                    timestamp_line = lines[1]

                    # Parse timestamps
                    if " --> " in timestamp_line:
                        start_time_str, end_time_str = timestamp_line.split(" --> ")
                        start_time = self._parse_srt_timestamp(start_time_str.strip())
                        end_time = self._parse_srt_timestamp(end_time_str.strip())

                        # Adjust timestamps by current offset
                        adjusted_start = start_time + current_time_offset
                        adjusted_end = end_time + current_time_offset

                        # Format adjusted timestamps
                        formatted_start = self._format_srt_timestamp(adjusted_start)
                        formatted_end = self._format_srt_timestamp(adjusted_end)

                        # Renumber subtitle
                        subtitle_number = len(combined_lines) // 4 + 1

                        # Add to combined content
                        combined_lines.append(str(subtitle_number))
                        combined_lines.append(f"{formatted_start} --> {formatted_end}")
                        combined_lines.extend(lines[2:])  # Add subtitle text
                        combined_lines.append("")  # Empty line after each block

                # Update time offset with duration of current file
                file_duration = self._get_srt_file_duration(srt_file)
                current_time_offset += timedelta(seconds=file_duration)

            # Write combined content
            combined_content = "\n".join(combined_lines).strip()
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(combined_content)

            logger.info(f"Combined {len(srt_files)} SRT files into {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"Error combining SRT files: {e}")
            raise

    def combine_vtt_files(self, vtt_files: list[Path], output_path: Path) -> str:
        """
        Combine multiple VTT files into a single VTT file with adjusted timestamps.

        Args:
            vtt_files: List of paths to VTT files to combine
            output_path: Path where the combined VTT file will be saved

        Returns:
            Path to the combined VTT file
        """
        try:
            combined_lines: list[str] = ["WEBVTT", ""]  # VTT header
            current_time_offset = timedelta(seconds=0)

            for vtt_file in vtt_files:
                if not vtt_file.exists():
                    logger.warning(f"VTT file not found: {vtt_file}")
                    continue

                with open(vtt_file, encoding="utf-8") as f:
                    lines = f.readlines()

                # Skip header lines
                content_lines = []
                in_header = True
                for line in lines:
                    if in_header and (line.strip() == "" or line.startswith("WEBVTT")):
                        continue
                    else:
                        in_header = False
                        content_lines.append(line.rstrip())

                if not content_lines:
                    continue

                # Parse VTT blocks and adjust timestamps
                i = 0
                while i < len(content_lines):
                    line = content_lines[i]

                    # Skip empty lines
                    if not line.strip():
                        i += 1
                        continue

                    # Check if this is a timestamp line
                    if " --> " in line:
                        timestamp_line = line
                        # Parse timestamps
                        start_time_str, end_time_str = timestamp_line.split(" --> ")
                        start_time = self._parse_vtt_timestamp(start_time_str.strip())
                        end_time = self._parse_vtt_timestamp(end_time_str.strip())

                        # Adjust timestamps by current offset
                        adjusted_start = start_time + current_time_offset
                        adjusted_end = end_time + current_time_offset

                        # Format adjusted timestamps
                        formatted_start = self._format_vtt_timestamp(adjusted_start)
                        formatted_end = self._format_vtt_timestamp(adjusted_end)

                        # Add to combined content
                        combined_lines.append(f"{formatted_start} --> {formatted_end}")

                        # Add subtitle text (next lines until empty line)
                        i += 1
                        while i < len(content_lines) and content_lines[i].strip():
                            combined_lines.append(content_lines[i].rstrip())
                            i += 1
                        combined_lines.append("")  # Empty line after each block
                    else:
                        i += 1

                # Update time offset with duration of current file
                file_duration = self._get_vtt_file_duration(vtt_file)
                current_time_offset += timedelta(seconds=file_duration)

            # Write combined content
            combined_content = "\n".join(combined_lines).strip() + "\n"
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(combined_content)

            logger.info(f"Combined {len(vtt_files)} VTT files into {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"Error combining VTT files: {e}")
            raise

    def _parse_srt_timestamp(self, timestamp_str: str) -> timedelta:
        """
        Parse SRT timestamp format (HH:MM:SS,mmm) to timedelta.

        Args:
            timestamp_str: SRT timestamp string

        Returns:
            Timedelta object
        """
        try:
            # Handle SRT format: HH:MM:SS,mmm
            time_parts = timestamp_str.replace(",", ".").split(":")
            if len(time_parts) == 3:
                hours = int(time_parts[0])
                minutes = int(time_parts[1])
                seconds_milliseconds = time_parts[2].split(".")
                seconds = int(seconds_milliseconds[0])
                milliseconds = (
                    int(seconds_milliseconds[1]) if len(seconds_milliseconds) > 1 else 0
                )
                return timedelta(
                    hours=hours,
                    minutes=minutes,
                    seconds=seconds,
                    milliseconds=milliseconds,
                )
            return timedelta(seconds=0)
        except Exception:
            return timedelta(seconds=0)

    def _parse_vtt_timestamp(self, timestamp_str: str) -> timedelta:
        """
        Parse VTT timestamp format (HH:MM:SS.mmm) to timedelta.

        Args:
            timestamp_str: VTT timestamp string

        Returns:
            Timedelta object
        """
        try:
            # Handle VTT format: HH:MM:SS.mmm
            time_parts = timestamp_str.split(":")
            if len(time_parts) == 3:
                hours = int(time_parts[0])
                minutes = int(time_parts[1])
                seconds_milliseconds = time_parts[2].split(".")
                seconds = int(seconds_milliseconds[0])
                milliseconds = (
                    int(seconds_milliseconds[1]) if len(seconds_milliseconds) > 1 else 0
                )
                return timedelta(
                    hours=hours,
                    minutes=minutes,
                    seconds=seconds,
                    milliseconds=milliseconds,
                )
            return timedelta(seconds=0)
        except Exception:
            return timedelta(seconds=0)

    def _get_srt_file_duration(self, srt_file: Path) -> float:
        """
        Get the duration of an SRT file by parsing the last timestamp.

        Args:
            srt_file: Path to SRT file

        Returns:
            Duration in seconds
        """
        try:
            with open(srt_file, encoding="utf-8") as f:
                content = f.read().strip()

            if not content:
                return 0.0

            # Parse SRT blocks and find the latest end time
            blocks = content.split("\n\n")
            max_end_time = timedelta(seconds=0)

            for block in blocks:
                if not block.strip():
                    continue

                lines = block.split("\n")
                if len(lines) < 3:
                    continue

                # Second line is timestamp
                timestamp_line = lines[1]

                # Parse timestamps
                if " --> " in timestamp_line:
                    _start_time_str, end_time_str = timestamp_line.split(" --> ")
                    end_time = self._parse_srt_timestamp(end_time_str.strip())
                    if end_time > max_end_time:
                        max_end_time = end_time

            return max_end_time.total_seconds()
        except Exception as e:
            logger.warning(f"Could not determine SRT file duration for {srt_file}: {e}")
            return 5.0  # Default to 5 seconds

    def _get_vtt_file_duration(self, vtt_file: Path) -> float:
        """
        Get the duration of a VTT file by parsing the last timestamp.

        Args:
            vtt_file: Path to VTT file

        Returns:
            Duration in seconds
        """
        try:
            with open(vtt_file, encoding="utf-8") as f:
                lines = f.readlines()

            # Skip header lines
            content_lines = []
            in_header = True
            for line in lines:
                if in_header and (line.strip() == "" or line.startswith("WEBVTT")):
                    continue
                else:
                    in_header = False
                    content_lines.append(line)

            if not content_lines:
                return 0.0

            # Parse VTT blocks and find the latest end time
            max_end_time = timedelta(seconds=0)
            i = 0

            while i < len(content_lines):
                line = content_lines[i].strip()

                # Skip empty lines
                if not line:
                    i += 1
                    continue

                # Check if this is a timestamp line
                if " --> " in line:
                    timestamp_line = line
                    # Parse timestamps
                    _start_time_str, end_time_str = timestamp_line.split(" --> ")
                    end_time = self._parse_vtt_timestamp(end_time_str.strip())
                    if end_time > max_end_time:
                        max_end_time = end_time

                    # Skip subtitle text lines
                    i += 1
                    while i < len(content_lines) and content_lines[i].strip():
                        i += 1
                else:
                    i += 1

            return max_end_time.total_seconds()
        except Exception as e:
            logger.warning(f"Could not determine VTT file duration for {vtt_file}: {e}")
            return 5.0  # Default to 5 seconds
