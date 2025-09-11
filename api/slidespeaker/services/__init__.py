"""
Service components for SlideSpeaker
"""

# No direct exports - use factory patterns instead
# Import factory classes for convenience
from slidespeaker.translation import TranslationService
from slidespeaker.video.avatar import AvatarFactory

__all__ = ["AvatarFactory", "TranslationService"]
