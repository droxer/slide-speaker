"""
Audio generator for SlideSpeaker.

This module provides a simplified interface for generating text-to-speech audio
from text content. It wraps the TTS factory and handles audio generation with
proper error handling and fallback mechanisms.
"""

import json
import subprocess
from pathlib import Path

from slidespeaker.services.tts_factory import TTSFactory
from slidespeaker.services.tts_interface import TTSInterface


class AudioGenerator:
    """Generator for text-to-speech audio files"""

    def __init__(self) -> None:
        """Initialize the audio generator with a TTS service"""
        try:
            self.tts_service: TTSInterface | None = TTSFactory.create_service()
        except Exception as e:
            print(f"Warning: Could not initialize TTS service: {e}")
            self.tts_service = None

    async def generate_audio(
        self,
        text: str,
        output_path: str,
        language: str = "english",
        voice: str | None = None,
    ) -> bool:
        """
        Generate audio from text content.

        Args:
            text: Text to convert to speech
            output_path: Path to save the generated audio file
            language: Language of the text
            voice: Specific voice to use (optional)

        Returns:
            True if audio generation was successful, False otherwise
        """
        if not self.tts_service:
            print("Error: TTS service not available")
            return False

        if not text.strip():
            print("Warning: Empty text provided for audio generation")
            return False

        try:
            output_path_obj = Path(output_path)
            # Ensure the output directory exists
            output_path_obj.parent.mkdir(parents=True, exist_ok=True)

            # Generate speech
            await self.tts_service.generate_speech(
                text, output_path_obj, language, voice
            )

            # Verify the generated file and log its properties
            if output_path_obj.exists():
                file_size = output_path_obj.stat().st_size
                print(f"Generated audio file: {output_path_obj} ({file_size} bytes)")

                # Try to get audio duration for debugging
                duration = self._get_audio_duration(output_path_obj)
                if duration > 0:
                    print(f"Audio duration: {duration:.2f} seconds")
                    # Estimate words per minute for quality check
                    word_count = len(text.split())
                    if duration > 0:
                        wpm = (word_count / duration) * 60
                        print(f"Speech rate: {wpm:.0f} words per minute")

                        # Check if speech rate is reasonable (normal human speech is 150-160 WPM)
                        if wpm < 100 or wpm > 300:
                            print(
                                f"Warning: Unusual speech rate detected ({wpm:.0f} WPM)"
                            )
            else:
                print(f"Warning: Audio file was not created at {output_path_obj}")

            return True
        except Exception as e:
            print(f"Error generating audio: {e}")
            return False

    def _get_audio_duration(self, audio_path: Path) -> float:
        """
        Get duration of audio file using ffprobe for debugging purposes

        Args:
            audio_path: Path to audio file

        Returns:
            Duration in seconds, or 0.0 if cannot determine
        """
        try:
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

            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)

                # Try to get duration from format first
                if "format" in data and "duration" in data["format"]:
                    return float(data["format"]["duration"])

                # If not in format, check streams
                if "streams" in data:
                    for stream in data["streams"]:
                        if "duration" in stream:
                            return float(stream["duration"])

        except Exception:
            # Silently fail - this is just for debugging
            pass

        return 0.0

    def get_supported_voices(self, language: str = "english") -> list[str]:
        """
        Get list of supported voices for a language.

        Args:
            language: Language to get voices for

        Returns:
            List of supported voice identifiers
        """
        if not self.tts_service:
            return []

        try:
            return self.tts_service.get_supported_voices(language)
        except Exception as e:
            print(f"Error getting supported voices: {e}")
            return []

    def is_available(self) -> bool:
        """
        Check if the audio generator is available.

        Returns:
            True if the TTS service is properly configured and available
        """
        if not self.tts_service:
            return False

        try:
            return self.tts_service.is_available()
        except Exception:
            return False
