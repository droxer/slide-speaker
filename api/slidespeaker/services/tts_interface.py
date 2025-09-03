"""
TTS Service Interface
Abstract base class for Text-to-Speech services
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
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the TTS service is available/configured"""
        pass

    @abstractmethod
    def get_supported_voices(self, language: str = "english") -> list[str]:
        """Get list of supported voices for a language"""
        pass
