from __future__ import annotations

import base64
import os
from pathlib import Path

import pytest

os.environ.setdefault("GOOGLE_GEMINI_TIMEOUT", "60")
os.environ.setdefault("GOOGLE_GEMINI_RETRIES", "3")
os.environ.setdefault("GOOGLE_GEMINI_BACKOFF", "0.5")
os.environ.setdefault("STORAGE_PROVIDER", "local")
os.environ.setdefault("PROXY_CLOUD_MEDIA", "false")

from slidespeaker.configs import config as global_config
from slidespeaker.image.llm import LLMImageGenerator


@pytest.mark.asyncio
async def test_download_image_supports_data_uri(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(global_config.config, "image_provider", "google", raising=False)
    monkeypatch.setattr(
        global_config.config, "google_gemini_api_key", "test-key", raising=False
    )

    generator = LLMImageGenerator()
    payload = base64.b64encode(b"binary-image").decode("ascii")
    uri = f"data:image/png;base64,{payload}"
    output_path = tmp_path / "generated.png"

    await generator._download_image(uri, output_path)

    assert output_path.read_bytes() == b"binary-image"
