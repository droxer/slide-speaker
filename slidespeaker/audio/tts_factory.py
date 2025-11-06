"""
TTS Service Factory
Factory pattern implementation for creating TTS service instances

This module implements the factory pattern for creating Text-to-Speech service
instances. It supports multiple TTS providers (OpenAI, ElevenLabs) and handles
service availability checking and configuration validation.
"""

from .elevenlabs_tts import ElevenLabsTTSService
from .openai_tts import OpenAITTSService
from .tts_interface import TTSInterface


class TTSFactory:
    """Factory for creating TTS service instances"""

    _services: dict[str, type[TTSInterface]] = {
        "openai": OpenAITTSService,
        "elevenlabs": ElevenLabsTTSService,
    }

    @classmethod
    def create_service(cls, model_spec: str | None = None) -> TTSInterface:
        """
        Create a TTS service instance based on configuration

        Args:
            model_spec: Optional model specification, defaults to config.tts_model

        Returns:
            TTSInterface implementation instance

        Raises:
            ValueError: If service name is invalid or service is not available
        """
        provider_part, _, _ = model_spec.partition("/")

        provider_part = provider_part.lower()

        if provider_part not in cls._services:
            raise ValueError(
                f"Unknown TTS service: {provider_part}. "
                f"Available services: {list(cls._services.keys())}"
            )

        return cls._services[provider_part]()

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
