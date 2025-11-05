"""Unit tests for the Gemini LLM client image generation helpers."""

from __future__ import annotations

import base64
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pytest

from slidespeaker.llm import gemini_client


@pytest.fixture(autouse=True)
def _patch_gemini_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure the Gemini client sees fake credentials during tests."""
    monkeypatch.setattr(
        gemini_client.config, "google_gemini_api_key", "test-key", raising=False
    )
    monkeypatch.setattr(
        gemini_client.config,
        "google_gemini_endpoint",
        "https://example.com",
        raising=False,
    )
    monkeypatch.setattr(
        gemini_client.config, "google_gemini_timeout", 0.0, raising=False
    )
    monkeypatch.setattr(gemini_client.config, "google_gemini_retries", 1, raising=False)
    monkeypatch.setattr(
        gemini_client.config, "google_gemini_backoff", 0.01, raising=False
    )


def _data_uri_payload() -> bytes:
    return base64.b64decode(base64.b64encode(b"image-bytes"))


@dataclass
class _Image:
    image_bytes: bytes
    mime_type: str = "image/png"


@dataclass
class _GeneratedImage:
    image: _Image


class _ImagesResponse:
    def __init__(self, payload: bytes) -> None:
        self.generated_images = [_GeneratedImage(_Image(payload))]


class _MockModels:
    def __init__(
        self,
        record: dict[str, Any],
        response_factory: Callable[[], _ImagesResponse],
        *,
        delay_seconds: float = 0.0,
    ) -> None:
        self._record = record
        self._response_factory = response_factory
        self._delay = delay_seconds

    def generate_images(
        self, *, model: str, prompt: str, config: dict[str, Any] | None = None
    ) -> _ImagesResponse:
        self._record["model"] = model
        self._record["prompt"] = prompt
        self._record["config"] = dict(config or {})
        if self._delay > 0:
            time.sleep(self._delay)
        return self._response_factory()


class _MockClient:
    def __init__(
        self,
        *,
        record: dict[str, Any],
        response_factory: Callable[[], _ImagesResponse],
        delay_seconds: float = 0.0,
        **kwargs: Any,
    ) -> None:
        record["client_kwargs"] = kwargs
        self.models = _MockModels(record, response_factory, delay_seconds=delay_seconds)


def test_image_generate_sets_aspect_ratio(monkeypatch: pytest.MonkeyPatch) -> None:
    record: dict[str, Any] = {}

    def _response_factory() -> _ImagesResponse:
        return _ImagesResponse(_data_uri_payload())

    monkeypatch.setattr(
        gemini_client.genai,
        "Client",
        lambda **kwargs: _MockClient(
            record=record, response_factory=_response_factory, **kwargs
        ),
    )

    client = gemini_client.GeminiLLMClient()
    images = client.image_generate(
        "A mountain landscape",
        model="models/imagen-4.0-generate-001",
        size="1792x1024",
        timeout=2.4,
    )

    assert images and images[0].startswith("data:image/png;base64,")
    config_payload = record["config"]
    assert config_payload["number_of_images"] == 1
    assert config_payload["output_mime_type"] == "image/png"
    assert config_payload["aspect_ratio"] == "16:9"
    assert config_payload["http_options"]["timeout"] == 2


def test_image_generate_without_known_aspect_ratio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record: dict[str, Any] = {}

    def _response_factory() -> _ImagesResponse:
        return _ImagesResponse(_data_uri_payload())

    monkeypatch.setattr(
        gemini_client.genai,
        "Client",
        lambda **kwargs: _MockClient(
            record=record, response_factory=_response_factory, **kwargs
        ),
    )

    client = gemini_client.GeminiLLMClient()
    images = client.image_generate(
        "Prompt", model="models/imagen-4.0-generate-001", size="1800x1200"
    )

    assert images and images[0].startswith("data:image/png;base64,")
    config_payload = record["config"]
    assert "aspect_ratio" not in config_payload
    assert "http_options" not in config_payload


def test_image_generate_raises_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    record: dict[str, Any] = {}

    def _response_factory() -> _ImagesResponse:
        return _ImagesResponse(_data_uri_payload())

    def _client_factory(**kwargs: Any) -> _MockClient:
        return _MockClient(
            record=record,
            response_factory=_response_factory,
            delay_seconds=0.2,
            **kwargs,
        )

    monkeypatch.setattr(gemini_client.genai, "Client", _client_factory)

    client = gemini_client.GeminiLLMClient()
    with pytest.raises(TimeoutError):
        client.image_generate(
            "Slow prompt",
            model="models/imagen-4.0-generate-001",
            size="1024x768",
            timeout=0.05,
            retries=1,
        )
