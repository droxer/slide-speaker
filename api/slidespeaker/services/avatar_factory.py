"""
Avatar Service Factory
Factory pattern implementation for creating avatar service instances
"""

import os

from .avatar_interface import AvatarInterface
from .dalle_avatar_service import DalleAvatarService
from .heygen_avatar_service import HeyGenAvatarService


class AvatarFactory:
    """Factory for creating avatar service instances"""

    _services: dict[str, type[AvatarInterface]] = {
        "heygen": HeyGenAvatarService,
        "dalle": DalleAvatarService,
    }

    @classmethod
    def create_service(cls, service_name: str | None = None) -> AvatarInterface:
        """
        Create an avatar service instance based on configuration

        Args:
            service_name: Optional service name override, defaults to env var

        Returns:
            AvatarInterface implementation instance

        Raises:
            ValueError: If service name is invalid or service is not available
        """
        if service_name is None:
            service_name = os.getenv("AVATAR_SERVICE", "dalle").lower()

        if service_name not in cls._services:
            raise ValueError(
                f"Unknown avatar service: {service_name}. "
                f"Available services: {list(cls._services.keys())}"
            )

        service_class = cls._services[service_name]
        service_instance = service_class()

        if not service_instance.is_available():
            raise ValueError(
                f"Avatar service '{service_name}' is not properly configured. "
                f"Please check your environment variables."
            )

        return service_instance

    @classmethod
    def get_available_services(cls) -> dict[str, type[AvatarInterface]]:
        """Get all available avatar service classes"""
        return cls._services.copy()

    @classmethod
    def get_configured_services(cls) -> dict[str, bool]:
        """
        Get configuration status for all avatar services

        Returns:
            Dictionary mapping service names to their configuration status
        """
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
        """
        Get the fallback service (DALL-E) which is always available

        Returns:
            AvatarInterface instance that's always available
        """
        return DalleAvatarService()
