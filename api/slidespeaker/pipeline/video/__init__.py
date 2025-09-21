"""
Video pipeline coordinators.

Exposes entry points for processing videos from PDF or Slides sources.
"""

from .coordinator import from_pdf, from_slide

__all__ = ["from_pdf", "from_slide"]
