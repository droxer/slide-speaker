"""
Avatar Service Interface (video package)
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
        """Generate avatar video from script"""
        raise NotImplementedError

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the avatar service is available/configured"""
        raise NotImplementedError

    @abstractmethod
    def get_supported_options(self) -> dict[str, Any]:
        """Get supported configuration options for this service"""
        raise NotImplementedError
