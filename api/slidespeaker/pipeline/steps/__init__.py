"""
Pipeline steps for SlideSpeaker processing.

This module contains individual processing steps for both presentation and PDF pipelines.
"""

# Presentation processing steps
# PDF processing steps
from .pdf import (
    compose_video_step as compose_pdf_video_step,
)
from .pdf import (
    generate_audio_step as generate_pdf_audio_step,
)
from .pdf import (
    generate_frames_step as generate_pdf_chapter_images_step,
)
from .pdf import (
    generate_subtitles_step as generate_pdf_subtitles_step,
)
from .pdf import (
    segment_content_step as segment_pdf_content_step,
)
from .slides.analyze_slides import analyze_slides_step
from .slides.compose_video import compose_video_step
from .slides.convert_slides import convert_slides_step
from .slides.extract_slides import extract_slides_step
from .slides.generate_audio import generate_audio_step
from .slides.generate_avatar import generate_avatar_step
from .slides.generate_subtitles import generate_subtitles_step
from .slides.generate_transcripts import generate_transcripts_step
from .slides.revise_transcripts import revise_transcripts_step

__all__ = [
    # Presentation processing steps
    "extract_slides_step",
    "convert_slides_step",
    "analyze_slides_step",
    "generate_transcripts_step",
    "revise_transcripts_step",
    "generate_audio_step",
    "generate_avatar_step",
    "generate_subtitles_step",
    "compose_video_step",
    # PDF processing steps
    "segment_pdf_content_step",
    "generate_pdf_chapter_images_step",
    "generate_pdf_audio_step",
    "generate_pdf_subtitles_step",
    "compose_pdf_video_step",
]
