"""
ElevenLabs TTS Service Implementation

This module provides an implementation of the TTS interface using ElevenLabs' text-to-speech API.
It supports multiple voices and high-quality speech synthesis through the ElevenLabs platform.
"""

import os
from pathlib import Path

import requests
from loguru import logger

from .tts_interface import TTSInterface


class ElevenLabsTTSService(TTSInterface):
    """ElevenLabs TTS implementation"""

    def __init__(self) -> None:
        """Initialize the ElevenLabs TTS service with API configuration"""
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        self.base_url = "https://api.elevenlabs.io/v1"
        self.default_voice_id = os.getenv(
            "ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"
        )  # Default voice

    async def generate_speech(
        self,
        text: str,
        output_path: Path,
        language: str = "english",
        voice: str | None = None,
    ) -> None:
        """Generate speech using ElevenLabs TTS"""
        if not text or not text.strip():
            raise ValueError("Text is empty or contains only whitespace")

        if not self.api_key:
            raise ValueError("ElevenLabs API key not configured")

        # Use provided voice or default
        voice_id = voice or self.default_voice_id

        url = f"{self.base_url}/text-to-speech/{voice_id}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key,
        }

        data = {
            "text": text.strip(),
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5,
            },
        }

        try:
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            response = requests.post(url, headers=headers, json=data, stream=True)
            response.raise_for_status()

            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)

            logger.info(f"Generated ElevenLabs TTS: {output_path}")

        except requests.exceptions.RequestException as e:
            logger.error(f"ElevenLabs TTS API error: {e}")
            raise
        except Exception as e:
            logger.error(f"ElevenLabs TTS error: {e}")
            raise

    def is_available(self) -> bool:
        """Check if ElevenLabs TTS is available"""
        return bool(self.api_key)

    def get_supported_voices(self, language: str = "english") -> list[str]:
        """Get supported ElevenLabs voices (simplified for interface)"""
        # In a real implementation, this would fetch from ElevenLabs API
        # For now, return some common voice IDs
        voices = {
            "english": [
                "21m00Tcm4TlvDq8ikWAM",  # Rachel
                "AZnzlk1XvdvUeBnXmlld",  # Domi
                "EXAVITQu4vr4xnSDxMaL",  # Bella
                "ErXwobaYiN019PkySvjV",  # Antoni
                "MF3mGyEYCl7XYWbV9V6O",  # Elli
            ],
            "chinese": [
                "g5CIjZEefAph4nQFvHAz",  # Chinese Female
                "CYw3kZ02Hs0563khs1Fj",  # Chinese Male
            ],
            "simplified_chinese": [
                "g5CIjZEefAph4nQFvHAz",  # Chinese Female
                "CYw3kZ02Hs0563khs1Fj",  # Chinese Male
            ],
            "traditional_chinese": [
                "g5CIjZEefAph4nQFvHAz",  # Chinese Female
                "CYw3kZ02Hs0563khs1Fj",  # Chinese Male
            ],
            "japanese": [
                "pFZP5JQG7iQjIQuC4Bku",  # Japanese Female
                "VR6AewLTigWG4xSOukaG",  # Japanese Male
            ],
        }

        return voices.get(language, [self.default_voice_id])
