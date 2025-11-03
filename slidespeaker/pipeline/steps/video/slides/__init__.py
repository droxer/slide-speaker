"""
Video pipeline step facades for Slides (PPT/PPTX) inputs.

This package re-exports slide video-related steps from their original locations
to provide a stable, organized import surface for coordinators.
"""

from .analyze_slides import analyze_slides_step
from .compose_video import compose_video_step
from .convert_slides import convert_slides_step
from .extract_slides import extract_slides_step
from .generate_audio import generate_audio_step
from .generate_avatar import generate_avatar_step
from .generate_subtitles import generate_subtitles_step
from .generate_transcripts import generate_transcripts_step
from .revise_transcripts import revise_transcripts_step
from .translate_transcripts import (
    translate_subtitle_transcripts_step,
    translate_voice_transcripts_step,
)

__all__ = [
    "analyze_slides_step",
    "compose_video_step",
    "convert_slides_step",
    "extract_slides_step",
    "generate_audio_step",
    "generate_avatar_step",
    "generate_subtitles_step",
    "generate_transcripts_step",
    "revise_transcripts_step",
    "translate_subtitle_transcripts_step",
    "translate_voice_transcripts_step",
]
