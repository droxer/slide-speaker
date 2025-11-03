"""
Avatar Service Factory (video package)
"""

from slidespeaker.configs.config import config

from .heygen import HeyGenAvatarService
from .interface import AvatarInterface


class AvatarFactory:
    """Factory for creating avatar service instances"""

    _services: dict[str, type[AvatarInterface]] = {
        "heygen": HeyGenAvatarService,
    }

    @classmethod
    def create_service(cls, service_name: str | None = None) -> AvatarInterface:
        if service_name is None:
            service_name = config.avatar_service

        if service_name not in cls._services:
            raise ValueError(
                f"Unknown avatar service: {service_name}. Available: {list(cls._services.keys())}"
            )

        service_class = cls._services[service_name]
        service_instance = service_class()

        if not service_instance.is_available():
            raise ValueError(
                f"Avatar service '{service_name}' is not properly configured."
            )

        return service_instance

    @classmethod
    def get_available_services(cls) -> dict[str, type[AvatarInterface]]:
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

    @classmethod
    def get_fallback_service(cls) -> AvatarInterface:
        return HeyGenAvatarService()
