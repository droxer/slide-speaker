"""
LLM interface definitions for pluggable providers.

Define a small surface area used across the app so we can support
multiple vendors (OpenAI today; Google AI, etc. later).
"""

from __future__ import annotations

import abc
from collections.abc import Iterable
from typing import Any


class LLMClient(abc.ABC):
    """Abstract LLM client interface used by the app."""

    @abc.abstractmethod
    def chat_completion(
        self,
        messages: list[dict[str, object]],
        model: str,
        *,
        retries: int | None = None,
        backoff: float | None = None,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> str:
        """Return assistant message content as string (may be empty)."""

    @abc.abstractmethod
    def image_generate(
        self,
        prompt: str,
        model: str,
        size: str = "1792x1024",
        n: int = 1,
        *,
        retries: int | None = None,
        backoff: float | None = None,
        timeout: float | None = None,
    ) -> list[str]:
        """Generate one or more images, return list of URLs or data URIs."""

    @abc.abstractmethod
    def tts_speech_stream(
        self,
        model: str,
        voice: str,
        input_text: str,
        *,
        retries: int | None = None,
        backoff: float | None = None,
        timeout: float | None = None,
    ) -> Iterable[bytes]:
        """Return an iterator of audio bytes for synthesized speech."""
