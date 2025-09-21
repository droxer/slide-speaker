"""
LLM provider factory and module-level facade functions.
"""

from __future__ import annotations

from collections.abc import Iterable

from slidespeaker.configs.config import config

from .base import LLMClient
from .openai_client import OpenAILLMClient

_llm_client: LLMClient | None = None


def _get_llm() -> LLMClient:
    global _llm_client
    if _llm_client is not None:
        return _llm_client
    provider = (getattr(config, "llm_provider", None) or "openai").lower()
    if provider == "openai":
        _llm_client = OpenAILLMClient()
    elif provider == "google":
        # Placeholder for future Google AI implementation
        # from .google_client import GoogleLLMClient
        # _llm_singleton = GoogleLLMClient()
        raise NotImplementedError("Google AI provider not implemented yet")
    else:
        # Fallback to OpenAI for unknown providers
        _llm_client = OpenAILLMClient()
    return _llm_client


def chat_completion(
    messages: list[dict[str, object]],
    model: str,
    *,
    retries: int | None = None,
    backoff: float | None = None,
    timeout: float | None = None,
    **kwargs: dict[str, object],
) -> str:
    return _get_llm().chat_completion(
        messages, model, retries=retries, backoff=backoff, timeout=timeout, **kwargs
    )


def image_generate(
    prompt: str,
    model: str,
    size: str = "1792x1024",
    n: int = 1,
    *,
    retries: int | None = None,
    backoff: float | None = None,
    timeout: float | None = None,
) -> list[str]:
    return _get_llm().image_generate(
        prompt, model, size=size, n=n, retries=retries, backoff=backoff, timeout=timeout
    )


def tts_speech_stream(
    model: str,
    voice: str,
    input_text: str,
    *,
    retries: int | None = None,
    backoff: float | None = None,
    timeout: float | None = None,
) -> Iterable[bytes]:
    return _get_llm().tts_speech_stream(
        model, voice, input_text, retries=retries, backoff=backoff, timeout=timeout
    )
