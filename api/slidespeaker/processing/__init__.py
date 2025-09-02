"""
Processing components for SlideSpeaker
"""

# Processing modules
from .slide_extractor import SlideExtractor
from .script_generator import ScriptGenerator
from .video_composer import VideoComposer
from .subtitle_generator import SubtitleGenerator
from .video_previewer import VideoPreviewer
from .image_generator import ImageGenerator

__all__ = [
    'SlideExtractor',
    'ScriptGenerator',
    'VideoComposer',
    'SubtitleGenerator',
    'VideoPreviewer',
    'ImageGenerator'
]