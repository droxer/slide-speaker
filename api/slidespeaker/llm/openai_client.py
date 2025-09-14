"""
OpenAI LLM client implementation for the pluggable LLM interface.
"""

from __future__ import annotations

import time
from collections.abc import Iterable
from typing import Any, cast

from openai import OpenAI

from slidespeaker.configs.config import config

from .base import LLMClient


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
        messages: list[dict[str, object]],
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
        last_err: Exception | None = None
        for attempt in range(r):
            try:
                resp = cli.chat.completions.create(
                    model=model, messages=messages, timeout=t, **kwargs
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
                if isinstance(payload, (bytes | bytearray)):
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
