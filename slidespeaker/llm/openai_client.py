"""
OpenAI LLM client implementation for the pluggable LLM interface.
"""

from __future__ import annotations

import time
from collections.abc import Iterable
from typing import Any, cast

from loguru import logger
from openai import OpenAI

from slidespeaker.configs.config import config

from .base import ChatMessages, LLMClient, to_openai_messages


class OpenAILLMClient(LLMClient):
    def __init__(self) -> None:
        api_key = config.openai_api_key
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI client")
        if config.openai_base_url:
            self._client = OpenAI(api_key=api_key, base_url=config.openai_base_url)
        else:
            self._client = OpenAI(api_key=api_key)

    def chat_completion(
        self,
        messages: ChatMessages,
        model: str,
        *,
        retries: int | None = None,
        backoff: float | None = None,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> str:
        cli = cast(Any, self._client)
        r = config.openai_retries if retries is None else retries
        b = config.openai_backoff if backoff is None else backoff
        t = config.openai_timeout if timeout is None else timeout
        payload = to_openai_messages(messages)
        last_err: Exception | None = None
        for attempt in range(r):
            try:
                resp = cli.chat.completions.create(
                    model=model,
                    messages=payload,
                    timeout=t,
                    **kwargs,
                )
                return (resp.choices[0].message.content or "") if resp.choices else ""
            except Exception as e:
                last_err = e
                if attempt == r - 1:
                    raise
                time.sleep(b * (2**attempt))
        if last_err:
            raise last_err
        return ""

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
        cli = cast(Any, self._client)
        r = config.openai_retries if retries is None else retries
        b = config.openai_backoff if backoff is None else backoff
        t = config.openai_timeout if timeout is None else timeout
        result: list[str] = []
        last_err: Exception | None = None
        for attempt in range(r):
            try:
                size_to_use = _normalize_openai_image_size(model, size)
                if size_to_use != size:
                    logger.debug(
                        "Adjusted OpenAI image size from %s to %s for model=%s",
                        size,
                        size_to_use,
                        model,
                    )
                resp = cli.images.generate(
                    model=model, prompt=prompt, size=size_to_use, n=n, timeout=t
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
        self,
        model: str,
        voice: str,
        input_text: str,
        *,
        retries: int | None = None,
        backoff: float | None = None,
        timeout: float | None = None,
    ) -> Iterable[bytes]:
        cli = cast(Any, self._client)
        r = config.openai_retries if retries is None else retries
        b = config.openai_backoff if backoff is None else backoff
        t = config.openai_timeout if timeout is None else timeout
        last_err: Exception | None = None
        for attempt in range(r):
            try:
                resp = cli.audio.speech.create(
                    model=model, voice=voice, input=input_text, timeout=t
                )
                if hasattr(resp, "iter_bytes"):
                    return cast(Iterable[bytes], resp.iter_bytes())
                payload = None
                for attr in ("content", "data", "body"):
                    if hasattr(resp, attr):
                        payload = getattr(resp, attr)
                        break
                if isinstance(payload, bytes | bytearray):
                    data_bytes = (
                        payload if isinstance(payload, bytes) else bytes(payload)
                    )

                    def _single(data: bytes) -> Iterable[bytes]:
                        yield data

                    return _single(data_bytes)
                raw = bytes(resp)

                def _single2(buf: bytes) -> Iterable[bytes]:
                    yield buf

                return _single2(raw)
            except Exception as e:
                last_err = e
                if attempt == r - 1:
                    raise
                time.sleep(b * (2**attempt))
        if last_err:
            raise last_err
        return iter(())


def _normalize_openai_image_size(model: str, size: str) -> str:
    """
    Adjust requested OpenAI image size to a supported value.

    Handles mismatched aspect ratios by picking the closest supported option.
    """

    model_key = model.lower()
    allowed = _allowed_sizes_for_model(model_key)
    requested = (size or "").lower()
    if requested in allowed:
        return requested

    if requested == "auto" and "auto" in allowed:
        return "auto"

    def _fallback() -> str:
        if "1024x1024" in allowed:
            return "1024x1024"
        return next(iter(allowed))

    if "x" in requested:
        try:
            width_str, height_str = requested.split("x", 1)
            width = float(int(width_str))
            height = float(int(height_str))
            if width > 0 and height > 0:
                ratio = width / height
                if ratio >= 1.2:
                    if "1536x1024" in allowed:
                        return "1536x1024"
                    if "auto" in allowed:
                        return "auto"
                elif ratio <= 0.85:
                    if "1024x1536" in allowed:
                        return "1024x1536"
                    if "auto" in allowed:
                        return "auto"
        except (ValueError, ZeroDivisionError):
            pass

    return _fallback()


def _allowed_sizes_for_model(model: str) -> set[str]:
    if "gpt-image-1" in model:
        return {"1024x1024", "1024x1536", "1536x1024", "auto"}
    if "dall-e-3" in model:
        return {"1024x1024"}
    if "dall-e-2" in model or "dall-e" in model:
        return {"256x256", "512x512", "1024x1024"}
    return {"1024x1024"}
