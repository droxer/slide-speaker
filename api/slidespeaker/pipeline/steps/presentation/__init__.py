"""
Presentation processing steps for SlideSpeaker.

This module contains individual processing steps for the presentation pipeline.
"""

from .analyze_slides import analyze_slides_step
from .compose_video import compose_video_step
from .convert_slides import convert_slides_step
from .extract_slides import extract_slides_step
from .generate_audio import generate_audio_step
from .generate_avatar import generate_avatar_step
from .generate_scripts import generate_scripts_step
from .generate_subtitles import generate_subtitles_step
from .review_scripts import review_scripts_step

__all__ = [
    "extract_slides_step",
    "convert_slides_step",
    "analyze_slides_step",
    "generate_scripts_step",
    "review_scripts_step",
    "generate_audio_step",
    "generate_avatar_step",
    "generate_subtitles_step",
    "compose_video_step",
]
