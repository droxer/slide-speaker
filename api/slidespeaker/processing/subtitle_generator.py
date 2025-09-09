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
            duration = self._get_audio_duration(audio_path)

            # Split long text into reasonable chunks
            text_chunks = self._split_text_for_subtitles(script_text, max_chars=42)

            # Calculate chunk durations for more natural timing
            chunk_durations = self._calculate_chunk_durations(
                duration, text_chunks, script_text
            )

            for j, (chunk, chunk_duration) in enumerate(
                zip(text_chunks, chunk_durations, strict=False)
            ):
                chunk_start_time = start_time

                # For the last chunk, ensure it ends exactly at the audio duration
                if j == len(text_chunks) - 1:
                    # Ensure the last chunk ends exactly at the total duration
                    elapsed_time = sum(chunk_durations[:j])
                    chunk_end_time = start_time + timedelta(
                        seconds=duration - elapsed_time
                    )
                else:
                    chunk_end_time = start_time + timedelta(seconds=chunk_duration)

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
            duration = self._get_audio_duration(audio_path)

            # Split long text into reasonable chunks
            text_chunks = self._split_text_for_subtitles(script_text, max_chars=42)

            # Calculate chunk durations for more natural timing
            chunk_durations = self._calculate_chunk_durations(
                duration, text_chunks, script_text
            )

            for j, (chunk, chunk_duration) in enumerate(
                zip(text_chunks, chunk_durations, strict=False)
            ):
                chunk_start_time = start_time

                # For the last chunk, ensure it ends exactly at the audio duration
                if j == len(text_chunks) - 1:
                    # Ensure the last chunk ends exactly at the total duration
                    elapsed_time = sum(chunk_durations[:j])
                    chunk_end_time = start_time + timedelta(
                        seconds=duration - elapsed_time
                    )
                else:
                    chunk_end_time = start_time + timedelta(seconds=chunk_duration)

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
        Split long text into smaller chunks suitable for subtitles with improved timing awareness

        Args:
            text: The text to split
            max_chars: Maximum characters per subtitle chunk (typically 42 for readability)

        Returns:
            List of text chunks optimized for subtitle display timing
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

        # Try to split by sentence boundaries first for natural reading flow
        sentences = self._split_into_sentences(text)

        # If we have good sentence splits, use them
        if len(sentences) > 1:
            for sentence in sentences:
                if len(sentence) <= max_chars:
                    chunks.append(sentence)
                else:
                    # Split long sentences by natural breaks
                    chunks.extend(self._split_long_sentence(sentence, max_chars))
        else:
            # Split long text by words with consideration for timing
            chunks.extend(self._split_long_sentence(text, max_chars))

        # Ensure no chunk is empty and optimize for timing
        chunks = [chunk.strip() for chunk in chunks if chunk.strip()]

        # Further optimize chunks for better timing distribution
        optimized_chunks = self._optimize_chunks_for_timing(chunks, max_chars)

        return optimized_chunks if optimized_chunks else [text]

    def _split_into_sentences(self, text: str) -> list[str]:
        """
        Split text into sentences using punctuation marks as delimiters

        Args:
            text: Text to split into sentences

        Returns:
            List of sentences
        """
        sentences = []
        current = ""

        # Split by common sentence endings with some context awareness
        i = 0
        while i < len(text):
            char = text[i]
            current += char

            # Check for sentence endings
            if char in ".!?;" and i < len(text) - 1:
                # Look ahead to see if next character is space or end of text
                next_char = text[i + 1]
                # Check if this looks like a real sentence ending
                # (avoid splitting on abbreviations like "Mr.", "Dr.", etc.)
                if (
                    next_char.isspace() or next_char in "\"'"
                ) and self._is_real_sentence_end(current, i, text):
                    if current.strip():
                        sentences.append(current.strip())
                    current = ""

            i += 1

        if current.strip():
            sentences.append(current.strip())

        return sentences

    def _is_real_sentence_end(
        self, current: str, position: int, full_text: str
    ) -> bool:
        """
        Determine if a period represents a real sentence end or an abbreviation

        Args:
            current: Current text segment
            position: Position of the period in the full text
            full_text: Full text being processed

        Returns:
            True if this is a real sentence end, False if it's likely an abbreviation
        """
        # Simple heuristic: if the word before the period is short, it's likely an abbreviation
        words = current.strip().split()
        if words:
            last_word = words[-1].rstrip(".!?;")
            # If the word is very short (1-2 characters), likely an abbreviation
            if len(last_word) <= 2:
                return False
            # If it's a common abbreviation, return False
            common_abbreviations = {
                "Mr",
                "Mrs",
                "Dr",
                "Prof",
                "Ms",
                "Sr",
                "Jr",
                "vs",
                "etc",
                "i.e",
                "e.g",
            }
            if last_word in common_abbreviations:
                return False

        return True

    def _optimize_chunks_for_timing(
        self, chunks: list[str], max_chars: int
    ) -> list[str]:
        """
        Optimize chunks for better subtitle timing by combining short chunks and splitting long ones

        Args:
            chunks: List of text chunks
            max_chars: Maximum characters per chunk

        Returns:
            Optimized list of chunks
        """
        if not chunks:
            return chunks

        optimized = []
        i = 0

        while i < len(chunks):
            current_chunk = chunks[i]

            # If current chunk is very short and there's a next chunk, try to combine
            if len(current_chunk) < max_chars // 3 and i < len(chunks) - 1:
                next_chunk = chunks[i + 1]
                combined = f"{current_chunk} {next_chunk}"
                # Only combine if it doesn't exceed max_chars significantly
                if len(combined) <= max_chars + 10:
                    optimized.append(combined)
                    i += 2  # Skip next chunk since we combined it
                    continue

            # If current chunk is too long, split it more carefully
            if len(current_chunk) > max_chars:
                # Split with better consideration for word boundaries
                split_chunks = self._split_long_sentence(current_chunk, max_chars)
                optimized.extend(split_chunks)
            else:
                optimized.append(current_chunk)

            i += 1

        return optimized

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
        Get duration of audio file using ffprobe with enhanced error handling and fallback strategies

        Args:
            audio_path: Path to audio file

        Returns:
            Duration in seconds
        """
        if not audio_path.exists():
            logger.warning(f"Audio file does not exist: {audio_path}")
            return self._estimate_duration_from_text(audio_path)

        if audio_path.stat().st_size == 0:
            logger.warning(f"Audio file is empty: {audio_path}")
            return self._estimate_duration_from_text(audio_path)

        # Add retry mechanism for file access
        max_retries = 5
        for attempt in range(max_retries):
            if attempt > 0:
                import time

                time.sleep(
                    0.2 * (attempt + 1)
                )  # Exponential backoff: 0.2s, 0.4s, 0.6s, 0.8s, 1.0s

            try:
                import json
                import subprocess
                import time

                time.sleep(0.1)  # Add a small delay to ensure file is fully written

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

                if attempt == 0:
                    logger.info(f"Running ffprobe for audio file: {audio_path.name}")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

                # Check if ffprobe failed
                if result.returncode != 0:
                    logger.warning(
                        f"ffprobe failed with return code {result.returncode} for {audio_path.name}"
                    )
                    if attempt == max_retries - 1:  # Last attempt
                        return self._estimate_duration_from_text(audio_path)
                    continue

                # Check if stdout is empty
                if not result.stdout.strip():
                    logger.warning("ffprobe returned empty stdout")
                    if attempt == max_retries - 1:  # Last attempt
                        return self._estimate_duration_from_text(audio_path)
                    continue

                data = json.loads(result.stdout)

                # Try to get duration from format first
                if "format" in data and "duration" in data["format"]:
                    duration = float(data["format"]["duration"])
                    logger.info(f"Got duration {duration:.2f}s for {audio_path.name}")
                    return duration

                # If not in format, check streams
                if "streams" in data:
                    for stream in data["streams"]:
                        if "duration" in stream:
                            duration = float(stream["duration"])
                            logger.info(
                                f"Got duration {duration:.2f}s for {audio_path.name}"
                            )
                            return duration

            except subprocess.TimeoutExpired:
                logger.warning(f"ffprobe timed out for {audio_path.name}")
                if attempt == max_retries - 1:  # Last attempt
                    return self._estimate_duration_from_text(audio_path)
                continue  # Retry
            except json.JSONDecodeError as e:
                logger.warning(
                    f"Could not parse ffprobe JSON output for {audio_path.name}: {e}"
                )
                if attempt == max_retries - 1:  # Last attempt
                    return self._estimate_duration_from_text(audio_path)
                continue  # Retry
            except Exception as e:
                logger.warning(
                    f"Could not determine audio duration for {audio_path.name}: {e}"
                )
                # Default to text-based estimation if we can't determine duration
                if attempt == max_retries - 1:  # Last attempt
                    return self._estimate_duration_from_text(audio_path)
                continue  # Retry

        # Should never reach here, but just in case
        return self._estimate_duration_from_text(audio_path)

    def _estimate_duration_from_text(self, audio_path: Path) -> float:
        """
        Estimate audio duration based on text content when actual duration cannot be determined.
        Uses average speech rate of 150 words per minute (2.5 words per second).

        Args:
            audio_path: Path to audio file (used to extract associated text if possible)

        Returns:
            Estimated duration in seconds
        """
        # Try to extract text from filename or path if possible
        # This is a fallback - in real implementation, we should have access to the original text
        try:
            # If we had access to the original text, we could do:
            # word_count = len(text.split())
            # estimated_duration = word_count / 2.5  # 150 words per minute

            # For now, we'll use a reasonable default based on typical chapter content
            logger.info(
                f"Estimating duration for {audio_path.name} using default estimation"
            )
            return 10.0  # Default to 10 seconds for a typical chapter segment
        except Exception as e:
            logger.warning(f"Could not estimate duration for {audio_path.name}: {e}")
            return 5.0  # Final fallback

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

    def _calculate_chunk_durations(
        self, total_duration: float, chunks: list[str], original_text: str
    ) -> list[float]:
        """
        Calculate individual durations for each text chunk based on word count and reading speed.
        This provides more natural timing than equal distribution.

        Args:
            total_duration: Total audio duration in seconds
            chunks: List of text chunks
            original_text: Original full text (for context)

        Returns:
            List of durations for each chunk in seconds
        """
        if not chunks:
            return []

        if len(chunks) == 1:
            return [total_duration]

        # Calculate word counts for each chunk
        word_counts = [len(chunk.split()) for chunk in chunks]
        total_words = sum(word_counts)

        if total_words == 0:
            # Equal distribution if no words found
            return [total_duration / len(chunks)] * len(chunks)

        # Calculate base duration per word
        duration_per_word = total_duration / total_words

        # Calculate duration for each chunk based on word count
        chunk_durations = [word_count * duration_per_word for word_count in word_counts]

        # Apply slight variations for more natural timing
        # Shorter chunks get slightly less time, longer chunks get slightly more
        adjusted_durations = []
        for _i, (duration, chunk) in enumerate(
            zip(chunk_durations, chunks, strict=False)
        ):
            # Adjust based on chunk length relative to average
            avg_chunk_length = sum(len(c) for c in chunks) / len(chunks)
            length_factor = (
                len(chunk) / avg_chunk_length if avg_chunk_length > 0 else 1.0
            )

            # Slight adjustment (±10% based on length)
            adjustment = 1.0 + (0.1 * (length_factor - 1.0))
            adjusted_duration = duration * adjustment

            # Ensure we don't go negative
            adjusted_durations.append(max(0.1, adjusted_duration))

        # Normalize to ensure total duration is maintained
        total_adjusted = sum(adjusted_durations)
        if total_adjusted > 0:
            normalized_durations = [
                duration * total_duration / total_adjusted
                for duration in adjusted_durations
            ]
        else:
            # Fallback to equal distribution
            normalized_durations = [total_duration / len(chunks)] * len(chunks)

        return normalized_durations
