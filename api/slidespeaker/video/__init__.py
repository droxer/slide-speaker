"""
Video package for SlideSpeaker.

Exports video composition and preview utilities, and avatar factory for convenience.
"""

from .avatar import AvatarFactory
from .composer import VideoComposer
from .previewer import VideoPreviewer

__all__ = ["VideoComposer", "VideoPreviewer", "AvatarFactory"]
