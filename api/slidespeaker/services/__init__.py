"""
Service components for SlideSpeaker
"""

# No direct exports - use factory patterns instead
# Import factory classes for convenience
from .avatar_factory import AvatarFactory
from .tts_factory import TTSFactory

__all__ = ["TTSFactory", "AvatarFactory"]
