"""
Processing components for SlideSpeaker
"""

# PDF processing components
from .audio_generator import AudioGenerator

# Presentation processing components
from .image_generator import ImageGenerator
from .image_generator import ImageGenerator as PDFImageGenerator
from .image_generator import ImageGenerator as SharedImageGenerator
from .pdf_analyzer import PDFAnalyzer
from .script_generator import ScriptGenerator
from .script_reviewer import ScriptReviewer
from .slide_extractor import SlideExtractor
from .subtitle_generator import SubtitleGenerator
from .video_composer import VideoComposer
from .video_previewer import VideoPreviewer

__all__ = [
    # PDF processing
    "PDFAnalyzer",
    "PDFImageGenerator",
    # Presentation processing
    "SlideExtractor",
    "ScriptGenerator",
    "ScriptReviewer",
    "ImageGenerator",
    # Shared components
    "AudioGenerator",
    "SharedImageGenerator",
    "SubtitleGenerator",
    "VideoComposer",
    "VideoPreviewer",
]
