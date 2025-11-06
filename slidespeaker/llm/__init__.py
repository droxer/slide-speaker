"""
LLM package exposing a provider-agnostic facade.

Backed by OpenAI today, with extension points for other vendors.
"""

import abc
from collections.abc import Iterable

from slidespeaker.llm.base import ChatMessages

from .provider import _get_llm, chat_completion, image_generate, tts_speech_stream

__all__ = ["_get_llm", "chat_completion", "image_generate", "tts_speech_stream"]
