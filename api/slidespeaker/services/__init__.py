"""
Service components for SlideSpeaker
"""

# No direct exports - use factory patterns instead
# Import factory classes for convenience
from .tts_factory import TTSFactory
from .avatar_factory import AvatarFactory

__all__ = ["TTSFactory", "AvatarFactory"]