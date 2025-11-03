"""
LLM package exposing a provider-agnostic facade.

Backed by OpenAI today, with extension points for other vendors.
"""

from .provider import _get_llm, chat_completion, image_generate, tts_speech_stream

__all__ = ["_get_llm", "chat_completion", "image_generate", "tts_speech_stream"]
