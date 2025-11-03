"""
Avatar subpackage for SlideSpeaker video package.
"""

from .factory import AvatarFactory
from .heygen import HeyGenAvatarService
from .interface import AvatarInterface

__all__ = ["AvatarFactory", "AvatarInterface", "HeyGenAvatarService"]
