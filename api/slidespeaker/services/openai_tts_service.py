"""
OpenAI TTS Service Implementation

This module provides an implementation of the TTS interface using OpenAI's text-to-speech API.
It supports multiple voices and languages through the OpenAI TTS models.
"""

import os
from pathlib import Path

import openai
from loguru import logger

from .tts_interface import TTSInterface


class OpenAITTSService(TTSInterface):
    """OpenAI TTS implementation"""

    def __init__(self) -> None:
        """Initialize the OpenAI TTS service with API client and configuration"""
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_TTS_MODEL", "tts-1")
        self.default_voice = os.getenv("OPENAI_TTS_VOICE", "alloy")

    async def generate_speech(
        self,
        text: str,
        output_path: Path,
        language: str = "english",
        voice: str | None = None,
    ) -> None:
        """Generate speech using OpenAI TTS"""
        if not text or not text.strip():
            raise ValueError("Text is empty or contains only whitespace")

        # Language-specific voice mapping
        voice_mapping: dict[str, str] = {
            "english": "alloy",
            "chinese": "onyx",
            "japanese": "nova",
            "korean": "shimmer",
            "thai": "alloy",
        }

        use_voice = voice or voice_mapping.get(language, self.default_voice)

        try:
            response = self.client.audio.speech.create(
                model=self.model,
                voice=use_voice,
                input=text.strip(),
            )

            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            response.stream_to_file(output_path)
            logger.info(f"Generated OpenAI TTS: {output_path}")

        except Exception as e:
            logger.error(f"OpenAI TTS error: {e}")
            raise

    def is_available(self) -> bool:
        """Check if OpenAI TTS is available"""
        return bool(os.getenv("OPENAI_API_KEY"))

    def get_supported_voices(self, language: str = "english") -> list[str]:
        """Get supported OpenAI TTS voices"""
        all_voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

        # Language-specific recommendations
        language_voices = {
            "english": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
            "chinese": ["onyx", "alloy"],
            "japanese": ["nova", "alloy"],
            "korean": ["shimmer", "alloy"],
            "thai": ["alloy", "echo"],
        }

        return language_voices.get(language, all_voices)
