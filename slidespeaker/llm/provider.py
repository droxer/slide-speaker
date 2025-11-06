"""
LLM provider factory and module-level facade functions.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .base import ChatMessages, LLMClient
from .gemini_client import GeminiLLMClient
from .openai_client import OpenAILLMClient

_llm_clients: dict[str, LLMClient] = {}


def _get_llm(provider: str | None = None) -> LLMClient:
    prov = (provider or "openai").lower()
    if prov in _llm_clients:
        return _llm_clients[prov]

    if prov == "openai":
        client = OpenAILLMClient()
    elif prov in {"google", "gemini"}:
        client = GeminiLLMClient()
        prov = "google"
    else:
        raise ValueError(f"Unsupported provider: {prov}")

    _llm_clients[prov] = client
    return client


def _resolve_provider_and_model(model: str) -> tuple[str, str]:
    spec_provider, separator, spec_model = model.partition("/")
    if not separator:
        # No explicit provider prefix, default to OpenAI-compatible models.
        return "openai", spec_provider
    if not spec_model:
        raise ValueError(f"Invalid model specification '{model}'")
    return spec_provider.lower(), spec_model


def chat_completion(
    messages: ChatMessages,
    model: str,
    *,
    retries: int | None = None,
    backoff: float | None = None,
    timeout: float | None = None,
    **kwargs: Any,
) -> str:
    provider_name, model_name = _resolve_provider_and_model(model)
    return _get_llm(provider_name).chat_completion(
        messages,
        model_name,
        retries=retries,
        backoff=backoff,
        timeout=timeout,
        **kwargs,
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
    provider_name, model_name = _resolve_provider_and_model(model)
    return _get_llm(provider_name).image_generate(
        prompt,
        model_name,
        size=size,
        n=n,
        retries=retries,
        backoff=backoff,
        timeout=timeout,
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
    provider_name, model_name = _resolve_provider_and_model(model)
    voice_name = voice.split("/", 1)[1] if "/" in voice else voice
    return _get_llm(provider_name).tts_speech_stream(
        model_name,
        voice_name,
        input_text,
        retries=retries,
        backoff=backoff,
        timeout=timeout,
    )
