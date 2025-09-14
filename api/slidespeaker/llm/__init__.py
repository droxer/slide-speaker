"""
LLM package providing centralized client initialization and helpers.

Currently supports OpenAI-compatible clients with optional base_url.
"""

from .client import (
    chat_completion,
    get_openai_client,
    image_generate,
    tts_speech_stream,
)

__all__ = [
    "get_openai_client",
    "chat_completion",
    "image_generate",
    "tts_speech_stream",
]
