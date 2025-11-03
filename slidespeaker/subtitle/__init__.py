"""
Subtitle package for SlideSpeaker.

Provides subtitle generation, sentence segmentation, and timing utilities.
"""

from .generator import SubtitleGenerator
from .text_segmentation import split_sentences
from .timing import calculate_chunk_durations

__all__ = [
    "SubtitleGenerator",
    "split_sentences",
    "calculate_chunk_durations",
]
