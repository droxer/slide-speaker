"""Google Gemini LLM client implementation using the google-genai SDK."""

from __future__ import annotations

import base64
import io
import threading
import time
from collections.abc import Callable, Iterable
from typing import Any

from google import genai
from google.genai import types as genai_types

from slidespeaker.configs.config import config

from .base import ChatMessages, LLMClient, to_gemini_messages


class GeminiLLMClient(LLMClient):
    """LLM client backed by Google Gemini models via the official SDK."""

    def __init__(self) -> None:
        api_key = config.google_gemini_api_key
        if not api_key:
            raise ValueError("GOOGLE_GEMINI_API_KEY is required for Gemini client")

        http_options: dict[str, Any] = {}
        if config.google_gemini_endpoint:
            http_options["base_url"] = config.google_gemini_endpoint
        if config.google_gemini_timeout:
            http_options["timeout"] = int(max(1, round(config.google_gemini_timeout)))

        self._client = genai.Client(
            api_key=api_key,
            http_options=http_options or None,
        )
        self._timeout = config.google_gemini_timeout
        self._retries = config.google_gemini_retries
        self._backoff = config.google_gemini_backoff

    def _prepare_contents(
        self, messages: ChatMessages
    ) -> tuple[list[dict[str, Any]] | None, list[dict[str, Any]]]:
        gemini_messages = to_gemini_messages(messages)
        contents: list[dict[str, Any]] = []
        system_parts: list[dict[str, Any]] = []
        for message in gemini_messages:
            role = message["role"]
            if role == "system":
                system_parts.extend(message["parts"])
                continue
            contents.append({"role": role, "parts": message["parts"]})
        system_instruction = None
        if system_parts:
            system_instruction = [{"role": "system", "parts": system_parts}]
        return system_instruction, contents

    def _build_generation_config(self, options: dict[str, Any]) -> dict[str, Any]:
        if not options:
            return {}
        allowed_keys = {
            "temperature",
            "top_p",
            "top_k",
            "max_output_tokens",
            "stop_sequences",
            "candidate_count",
            "presence_penalty",
            "frequency_penalty",
            "seed",
            "response_mime_type",
            "response_modalities",
            "response_schema",
            "response_json_schema",
            "automatic_function_calling",
            "thinking_config",
        }
        return {
            key: value
            for key, value in options.items()
            if key in allowed_keys and value is not None
        }

    def _http_options(self, timeout: float | None) -> dict[str, Any] | None:
        if timeout is None or timeout <= 0:
            return None
        return {"timeout": int(max(1, round(timeout)))}

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
        r = self._retries if retries is None else retries
        b = self._backoff if backoff is None else backoff
        t = self._timeout if timeout is None else timeout
        system_instruction, contents = self._prepare_contents(messages)

        options = dict(kwargs)
        safety_settings = options.pop("safety_settings", None)
        base_config = self._build_generation_config(options)
        if system_instruction:
            base_config["system_instruction"] = system_instruction
        if safety_settings is not None:
            base_config["safety_settings"] = safety_settings

        last_err: Exception | None = None
        for attempt in range(r):
            try:
                config_payload = dict(base_config)
                http_options = self._http_options(t)
                if http_options:
                    config_payload["http_options"] = http_options

                response = self._client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=config_payload or None,
                )
                text = _extract_text(response)
                if text is not None:
                    return text
                return ""
            except Exception as err:
                last_err = err
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
        r = self._retries if retries is None else retries
        b = self._backoff if backoff is None else backoff
        t = self._timeout if timeout is None else timeout

        candidate_count = max(1, int(n))
        config_payload: dict[str, Any] = {
            "number_of_images": candidate_count,
            "output_mime_type": "image/png",
        }

        aspect_ratio = _size_to_aspect_ratio(size)
        if aspect_ratio:
            config_payload["aspect_ratio"] = aspect_ratio

        last_err: Exception | None = None
        for attempt in range(r):
            try:
                http_options = self._http_options(t)
                if http_options:
                    config_payload["http_options"] = http_options

                response = _run_with_timeout(
                    lambda: self._client.models.generate_images(
                        model=model, prompt=prompt, config=config_payload
                    ),
                    timeout=t,
                )
                images = _convert_generated_images(response, default_mime="image/png")
                if images:
                    return images[:candidate_count]
                return []
            except Exception as err:
                last_err = err
                if attempt == r - 1:
                    raise
                time.sleep(b * (2**attempt))
            finally:
                config_payload.pop("http_options", None)
        if last_err:
            raise last_err
        return []

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
        raise NotImplementedError("Text-to-speech is not yet supported for Gemini")


_KNOWN_ASPECT_RATIOS = {
    "1:1": 1.0,
    "4:3": 4.0 / 3.0,
    "3:4": 3.0 / 4.0,
    "16:9": 16.0 / 9.0,
    "9:16": 9.0 / 16.0,
}


def _size_to_aspect_ratio(size: str) -> str | None:
    try:
        width_str, height_str = size.lower().split("x", 1)
        width = float(int(width_str))
        height = float(int(height_str))
        if width <= 0 or height <= 0:
            return None
    except (ValueError, TypeError):
        return None

    ratio = width / height
    best_name: str | None = None
    best_delta = 0.12
    for name, value in _KNOWN_ASPECT_RATIOS.items():
        delta = abs(value - ratio)
        if delta < best_delta:
            best_delta = delta
            best_name = name
    return best_name


def _extract_text(response: genai_types.GenerateContentResponse) -> str | None:
    text = getattr(response, "text", None)
    if isinstance(text, str) and text:
        return text

    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) if content is not None else None
        if not parts:
            continue
        for part in parts:
            part_text = getattr(part, "text", None)
            if part_text is None and isinstance(part, dict):
                part_text = part.get("text")
            if part_text:
                return str(part_text)
    return None


def _convert_generated_images(
    response: genai_types.GenerateImagesResponse, *, default_mime: str
) -> list[str]:
    images: list[str] = []
    generated_images = getattr(response, "generated_images", None) or []

    for generated in generated_images:
        image_obj = getattr(generated, "image", None)
        if image_obj is None:
            continue

        mime_type = getattr(image_obj, "mime_type", None) or default_mime
        image_bytes = getattr(image_obj, "image_bytes", None)

        if image_bytes:
            encoded = base64.b64encode(
                bytes(image_bytes)
                if isinstance(image_bytes, bytearray)
                else image_bytes
            ).decode("ascii")
            images.append(f"data:{mime_type};base64,{encoded}")
            continue

        loaded_image = getattr(image_obj, "_loaded_image", None)
        if loaded_image is not None:
            buffer = io.BytesIO()
            image_format = (mime_type.split("/", 1)[-1] or "png").upper()
            loaded_image.save(buffer, format=image_format)
            encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
            images.append(f"data:{mime_type};base64,{encoded}")
            continue

        inline_data = getattr(image_obj, "inline_data", None)
        if inline_data is not None:
            data_uri = _inline_to_data_uri(inline_data, fallback_mime=mime_type)
            if data_uri:
                images.append(data_uri)

    if images:
        return images

    return _extract_legacy_images(response)


def _extract_legacy_images(response: Any) -> list[str]:
    images: list[str] = []
    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) if content is not None else None
        for part in parts or []:
            inline_data = getattr(part, "inline_data", None)
            if inline_data:
                data_uri = _inline_to_data_uri(inline_data, fallback_mime="image/png")
                if data_uri:
                    images.append(data_uri)
                    continue
            file_data = getattr(part, "file_data", None)
            if file_data:
                file_uri = getattr(file_data, "file_uri", None)
                if file_uri:
                    images.append(str(file_uri))
    return images


def _inline_to_data_uri(
    inline_data: Any, *, fallback_mime: str = "image/png"
) -> str | None:
    data = getattr(inline_data, "data", None)
    if data is None and isinstance(inline_data, dict):
        data = inline_data.get("data")
    if data is None:
        return None
    mime_type = getattr(inline_data, "mime_type", None)
    if mime_type is None and isinstance(inline_data, dict):
        mime_type = inline_data.get("mime_type")
    mime_type = mime_type or fallback_mime

    if isinstance(data, bytes | bytearray):
        encoded = base64.b64encode(bytes(data)).decode("ascii")
    else:
        encoded = str(data)
        if encoded.startswith("data:"):
            return encoded
        if not _is_base64(encoded):
            try:
                encoded = base64.b64encode(encoded.encode("utf-8")).decode("ascii")
            except Exception:
                return None
    return f"data:{mime_type};base64,{encoded}"


def _is_base64(value: str) -> bool:
    try:
        base64.b64decode(value, validate=True)
        return True
    except Exception:
        return False


def _run_with_timeout(func: Callable[[], Any], timeout: float | None) -> Any:
    """
    Execute a synchronous Gemini API call, enforcing a wall-clock timeout.

    The Gemini SDK occasionally ignores the request timeout and can block the worker
    thread indefinitely. Running the call in a daemon thread keeps the main worker
    responsive even when the SDK hangs.
    """

    if timeout is None or timeout <= 0:
        return func()

    result: dict[str, Any] = {}
    error: list[BaseException] = []
    finished = threading.Event()

    def _runner() -> None:
        try:
            result["value"] = func()
        except BaseException as exc:  # pragma: no cover - escalated to caller
            error.append(exc)
        finally:
            finished.set()

    thread = threading.Thread(target=_runner, name="gemini-call", daemon=True)
    thread.start()
    if not finished.wait(timeout):
        raise TimeoutError(f"Gemini image generation timed out after {timeout} seconds")

    thread.join()
    if error:
        raise error[0]
    return result.get("value")
