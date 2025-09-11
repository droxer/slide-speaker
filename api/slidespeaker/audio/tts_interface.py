"""
TTS Service Interface
Abstract base class for Text-to-Speech services

This module defines the interface that all TTS service implementations must follow.
It provides a consistent API for generating speech from text with support for
multiple languages and voices.
"""

from abc import ABC, abstractmethod
from pathlib import Path


class TTSInterface(ABC):
    """Abstract interface for TTS services"""

    @abstractmethod
    async def generate_speech(
        self,
        text: str,
        output_path: Path,
        language: str = "english",
        voice: str | None = None,
    ) -> None:
        """
        Generate speech from text and save to output_path

        Args:
            text: Text to convert to speech
            output_path: Path to save the generated audio file
            language: Language of the text (default: "english")
            voice: Specific voice to use (default: service-specific default)
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the TTS service is available/configured

        Returns:
            True if the service is properly configured and available, False otherwise
        """
        pass

    @abstractmethod
    def get_supported_voices(self, language: str = "english") -> list[str]:
        """
        Get list of supported voices for a language

        Args:
            language: Language to get voices for (default: "english")

        Returns:
            List of supported voice identifiers
        """
        pass
