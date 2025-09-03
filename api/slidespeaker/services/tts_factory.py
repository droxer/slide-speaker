"""
TTS Service Factory
Factory pattern implementation for creating TTS service instances
"""

import os

from .elevenlabs_tts_service import ElevenLabsTTSService
from .openai_tts_service import OpenAITTSService
from .tts_interface import TTSInterface


class TTSFactory:
    _services: dict[str, type[TTSInterface]] = {
        "openai": OpenAITTSService,
        "elevenlabs": ElevenLabsTTSService,
    }

    @classmethod
    def create_service(cls, service_name: str | None = None) -> TTSInterface:
        if service_name is None:
            service_name = os.getenv("TTS_SERVICE", "openai").lower()

        if service_name not in cls._services:
            raise ValueError(
                f"Unknown TTS service: {service_name}. "
                f"Available services: {list(cls._services.keys())}"
            )

        service_class = cls._services[service_name]
        service_instance = service_class()

        if not service_instance.is_available():
            raise ValueError(
                f"TTS service '{service_name}' is not properly configured. "
                f"Please check your environment variables."
            )

        return service_instance

    @classmethod
    def get_available_services(cls) -> dict[str, type[TTSInterface]]:
        """Get all available TTS service classes"""
        return cls._services.copy()

    @classmethod
    def get_configured_services(cls) -> dict[str, bool]:
        status = {}
        for name, service_class in cls._services.items():
            try:
                instance = service_class()
                status[name] = instance.is_available()
            except Exception:
                status[name] = False
        return status
