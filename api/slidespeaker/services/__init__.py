"""
Service components for SlideSpeaker
"""

# Service modules
from .avatar_service import AvatarService
from .avatar_service_alt import AvatarServiceAlt
from .avatar_service_unified import UnifiedAvatarService
from .tts_service import TTSService
from .vision_service import VisionService

__all__ = [
    'AvatarService',
    'AvatarServiceAlt',
    'UnifiedAvatarService',
    'TTSService',
    'VisionService'
]