"""
Centralized LLM client initialization.

- Provides a singleton OpenAI-compatible client configured with API key and
  optional base URL (for OpenAI-compatible providers).
"""

from __future__ import annotations

import time
from collections.abc import Iterable
from typing import Any, cast

from openai import OpenAI

from slidespeaker.configs.config import config

_openai_client: OpenAI | None = None


def get_openai_client() -> OpenAI:
    """Return a singleton OpenAI client configured from environment.

    Uses `OPENAI_API_KEY` and optional `OPENAI_BASE_URL` (or `OPENAI_API_BASE`).
    """
    global _openai_client
    if _openai_client is not None:
        return _openai_client

    api_key = config.openai_api_key
    if not api_key:
        raise ValueError("OPENAI_API_KEY is required for OpenAI client")

    if getattr(config, "openai_base_url", None):
        _openai_client = OpenAI(api_key=api_key, base_url=config.openai_base_url)
    else:
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


def chat_completion(
    messages: list[dict[str, object]],
    model: str,
    *,
    retries: int | None = None,
    backoff: float | None = None,
    timeout: float | None = None,
    **kwargs: Any,
) -> str:
    """Create a chat completion and return the message content string.

    Args:
        messages: OpenAI chat messages array
        model: Model name
        **kwargs: Additional params (temperature, max_tokens, etc.)
    Returns:
        The assistant message content (string, may be empty)
    """
    cli = cast(Any, get_openai_client())
    last_err: Exception | None = None
    r = config.openai_retries if retries is None else retries
    b = config.openai_backoff if backoff is None else backoff
    t = config.openai_timeout if timeout is None else timeout
    for attempt in range(r):
        try:
            resp = cli.chat.completions.create(
                model=model, messages=messages, timeout=t, **kwargs
            )
            return (resp.choices[0].message.content or "") if resp.choices else ""
        except Exception as e:  # transient errors: retry
            last_err = e
            if attempt == r - 1:
                raise
            time.sleep(b * (2**attempt))
    # Should not reach here
    if last_err:
        raise last_err
    return ""


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
    """Generate images and return a list of URLs or data URIs.

    Prefers URLs when available; falls back to base64 data when provided.
    """
    cli = cast(Any, get_openai_client())
    result: list[str] = []
    last_err: Exception | None = None
    r = config.openai_retries if retries is None else retries
    b = config.openai_backoff if backoff is None else backoff
    t = config.openai_timeout if timeout is None else timeout
    for attempt in range(r):
        try:
            resp = cli.images.generate(
                model=model, prompt=prompt, size=size, n=n, timeout=t
            )
            for d in getattr(resp, "data", []) or []:
                url = getattr(d, "url", None)
                if url:
                    result.append(url)
                    continue
                b64 = getattr(d, "b64_json", None)
                if b64:
                    result.append(f"data:image/png;base64,{b64}")
            return result
        except Exception as e:
            last_err = e
            if attempt == r - 1:
                raise
            time.sleep(b * (2**attempt))
    if last_err:
        raise last_err
    return result


def tts_speech_stream(
    model: str,
    voice: str,
    input_text: str,
    *,
    retries: int | None = None,
    backoff: float | None = None,
    timeout: float | None = None,
) -> Iterable[bytes]:
    """Create TTS speech and return an iterator of bytes."""
    cli = cast(Any, get_openai_client())
    last_err: Exception | None = None
    r = config.openai_retries if retries is None else retries
    b = config.openai_backoff if backoff is None else backoff
    t = config.openai_timeout if timeout is None else timeout
    for attempt in range(r):
        try:
            resp = cli.audio.speech.create(
                model=model, voice=voice, input=input_text, timeout=t
            )
            # Prefer streaming iterator if available
            if hasattr(resp, "iter_bytes"):
                return cast(Iterable[bytes], resp.iter_bytes())
            # Fall back to reading a bytes payload if present
            payload = None
            for attr in ("content", "data", "body"):
                if hasattr(resp, attr):
                    payload = getattr(resp, attr)
                    break
            if isinstance(payload, (bytes | bytearray)):
                data_bytes = payload if isinstance(payload, bytes) else bytes(payload)

                def _single(data: bytes) -> Iterable[bytes]:
                    yield data

                return _single(data_bytes)
            # As a last resort, try to serialize
            try:
                raw = bytes(resp)

                def _single2(buf: bytes) -> Iterable[bytes]:
                    yield buf

                return _single2(raw)
            except Exception as err:
                # No usable payload; raise to trigger retry
                raise RuntimeError(
                    "TTS response has no stream or bytes payload"
                ) from err
        except Exception as e:
            last_err = e
            if attempt == r - 1:
                raise
            time.sleep(b * (2**attempt))
    if last_err:
        raise last_err
    return iter(())
