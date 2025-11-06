"""
Pipeline package for SlideSpeaker presentation processing.

This package contains the main processing pipeline and individual processing steps.
"""

from .base import BasePipeline
from .coordinator import accept_task

__all__ = ["accept_task", "BasePipeline"]
