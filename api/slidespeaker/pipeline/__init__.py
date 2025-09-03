"""
Pipeline package for SlideSpeaker presentation processing.

This package contains the main processing pipeline and individual processing steps.
"""

from .coordinator import process_presentation

__all__ = ["process_presentation"]
