"""
Avatar Service Interface
Abstract base class for avatar video generation services
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class AvatarInterface(ABC):
    """Abstract interface for avatar video generation services"""

    @abstractmethod
    async def generate_avatar_video(
        self,
        script: str,
        output_path: Path,
        **kwargs: Any,
    ) -> bool:
        """
        Generate avatar video from script

        Args:
            script: Text script for the avatar to speak
            output_path: Path to save the generated video
            **kwargs: Provider-specific parameters (avatar_id, voice_id, style, etc.)

        Returns:
            bool: True if generation was successful, False otherwise
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the avatar service is available/configured"""
        pass

    @abstractmethod
    def get_supported_options(self) -> dict[str, Any]:
        """
        Get supported configuration options for this service

        Returns:
            dict: Available options like avatars, voices, styles, etc.
        """
        pass
