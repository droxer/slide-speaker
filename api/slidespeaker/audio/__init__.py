"""
Audio package for SlideSpeaker.

Contains audio generation (TTS) utilities and helpers.
"""

from .generator import AudioGenerator
from .tts_factory import TTSFactory
from .tts_interface import TTSInterface

__all__ = ["AudioGenerator", "TTSFactory", "TTSInterface"]
