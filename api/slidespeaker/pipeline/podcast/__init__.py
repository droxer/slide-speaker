"""
Podcast pipeline coordinator.

Currently supports generating a podcast (MP3) from PDF inputs.
"""

from .coordinator import from_pdf

__all__ = ["from_pdf"]
