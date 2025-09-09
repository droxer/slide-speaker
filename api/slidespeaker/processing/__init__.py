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
from .slide_extractor import SlideExtractor
from .subtitle_generator import SubtitleGenerator
from .transcript_generator import TranscriptGenerator
from .transcript_reviewer import TranscriptReviewer
from .video_composer import VideoComposer
from .video_previewer import VideoPreviewer

__all__ = [
    # PDF processing
    "PDFAnalyzer",
    "PDFImageGenerator",
    # Presentation processing
    "SlideExtractor",
    "TranscriptGenerator",
    "TranscriptReviewer",
    "ImageGenerator",
    # Shared components
    "AudioGenerator",
    "SharedImageGenerator",
    "SubtitleGenerator",
    "VideoComposer",
    "VideoPreviewer",
]
