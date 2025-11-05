"""Tests for OpenAI LLM client helper functions."""

from __future__ import annotations

import pytest

from slidespeaker.llm.openai_client import (
    _allowed_sizes_for_model,
    _normalize_openai_image_size,
)


@pytest.mark.parametrize(
    ("model", "requested", "expected"),
    [
        ("gpt-image-1", "1792x1024", "1536x1024"),
        ("gpt-image-1", "1024x1536", "1024x1536"),
        ("gpt-image-1", "auto", "auto"),
        ("gpt-image-1", "512x1024", "1024x1536"),
        ("dall-e-2", "1792x1024", "1024x1024"),
        ("dall-e-3", "1792x1024", "1024x1024"),
        ("custom-model", "2048x1024", "1024x1024"),
    ],
)
def test_normalize_openai_image_size(model: str, requested: str, expected: str) -> None:
    assert _normalize_openai_image_size(model, requested) == expected


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        ("gpt-image-1", {"1024x1024", "1024x1536", "1536x1024", "auto"}),
        ("dall-e-3", {"1024x1024"}),
        ("dall-e-2", {"256x256", "512x512", "1024x1024"}),
        ("something-else", {"1024x1024"}),
    ],
)
def test_allowed_sizes_for_model(model: str, expected: set[str]) -> None:
    assert _allowed_sizes_for_model(model) == expected
