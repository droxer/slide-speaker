"""
Audio generator for SlideSpeaker.

This module provides a simplified interface for generating text-to-speech audio
from text content. It wraps the TTS factory and handles audio generation with
proper error handling and fallback mechanisms.
"""

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

            return True
        except Exception as e:
            print(f"Error generating audio: {e}")
            return False

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
