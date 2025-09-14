"""
LLM package exposing a provider-agnostic facade.

Backed by OpenAI today, with extension points for other vendors.
"""

from .provider import chat_completion, get_llm, image_generate, tts_speech_stream

__all__ = ["get_llm", "chat_completion", "image_generate", "tts_speech_stream"]
