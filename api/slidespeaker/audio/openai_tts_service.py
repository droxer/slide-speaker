"""
OpenAI TTS Service Implementation

This module provides an implementation of the TTS interface using OpenAI's text-to-speech API.
It supports multiple voices and languages through the OpenAI TTS models.
"""

from pathlib import Path

import openai
from loguru import logger

from slidespeaker.configs.config import config

from .tts_interface import TTSInterface


class OpenAITTSService(TTSInterface):
    """OpenAI TTS implementation"""

    def __init__(self) -> None:
        """Initialize the OpenAI TTS service with API client and configuration"""
        api_key = config.openai_api_key
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")

        self.client = openai.OpenAI(api_key=api_key)
        self.model = config.openai_tts_model
        self.default_voice = config.openai_tts_voice

        # Validate model
        valid_models = ["tts-1", "tts-1-hd", "gpt-4o-mini-tts"]
        if self.model not in valid_models:
            logger.warning(
                f"Invalid OpenAI TTS model '{self.model}'. "
                f"Using default 'tts-1'. Valid models: {valid_models}"
            )
            self.model = "tts-1"

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
            "simplified_chinese": "onyx",
            "traditional_chinese": "onyx",
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

            # Write response content to file
            with open(output_path, "wb") as f:
                for chunk in response.iter_bytes():
                    f.write(chunk)

            logger.info(f"Generated OpenAI TTS: {output_path}")

        except Exception as e:
            logger.error(f"OpenAI TTS error: {e}")
            raise

    def is_available(self) -> bool:
        """Check if OpenAI TTS is available"""
        return bool(config.openai_api_key)

    def get_supported_voices(self, language: str = "english") -> list[str]:
        """Get supported OpenAI TTS voices"""
        all_voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

        # Language-specific recommendations
        language_voices = {
            "english": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
            "chinese": ["onyx", "alloy"],
            "simplified_chinese": ["onyx", "alloy"],
            "traditional_chinese": ["onyx", "alloy"],
            "japanese": ["nova", "alloy"],
            "korean": ["shimmer", "alloy"],
            "thai": ["alloy", "echo"],
        }

        return language_voices.get(language, all_voices)
