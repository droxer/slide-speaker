"""
SlideSpeaker - AI-powered presentation video generator

This package provides modules for converting PDF/PPTX presentations into
engaging video presentations with AI-generated narration and avatars.
"""

# Core components
from .core.state_manager import state_manager
from .core.task_manager import task_manager
from .core.task_queue import task_queue
from .pipeline.coordinator import process_presentation

# Public API
__all__ = ["task_queue", "task_manager", "state_manager", "process_presentation"]

# Package version
__version__ = "1.0.0"
