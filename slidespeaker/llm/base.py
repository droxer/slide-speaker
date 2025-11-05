from __future__ import annotations

import abc
from collections.abc import Iterable, Sequence
from typing import Any, Literal, NotRequired, TypedDict, cast

MessageRole = Literal["system", "user", "assistant", "tool"]


class OpenAIImageURL(TypedDict):
    url: str


class OpenAITextContent(TypedDict):
    type: Literal["text"]
    text: str


class OpenAIImageContent(TypedDict):
    type: Literal["image_url"]
    image_url: OpenAIImageURL


OpenAIContentPart = OpenAITextContent | OpenAIImageContent


class GeminiInlineData(TypedDict):
    mime_type: str
    data: str


class GeminiTextPart(TypedDict):
    text: str


class GeminiInlineDataPart(TypedDict):
    inline_data: GeminiInlineData


class GeminiFunctionCall(TypedDict):
    name: str
    args: dict[str, Any]


class GeminiFunctionCallPart(TypedDict):
    function_call: GeminiFunctionCall


GeminiPart = GeminiTextPart | GeminiInlineDataPart | GeminiFunctionCallPart


class GeminiChatMessage(TypedDict):
    role: MessageRole
    parts: list[GeminiPart]


class OpenAIChatMessage(TypedDict, total=False):
    role: MessageRole
    content: str | list[OpenAIContentPart]
    name: NotRequired[str]
    tool_call_id: NotRequired[str]
    tool_calls: NotRequired[Any]


ChatMessage = OpenAIChatMessage | GeminiChatMessage
ChatMessages = Sequence[ChatMessage]


def to_openai_messages(messages: ChatMessages) -> list[OpenAIChatMessage]:
    """Normalize chat messages into OpenAI-compatible payloads."""

    normalized: list[OpenAIChatMessage] = []
    for message in messages:
        if "content" in message:
            normalized.append(cast(OpenAIChatMessage, dict(message)))
            continue
        if "parts" not in message:
            raise ValueError("Chat message must include either 'content' or 'parts'.")
        parts: list[OpenAIContentPart] = []
        for part in cast(GeminiChatMessage, message)["parts"]:
            if "text" in part:
                parts.append({"type": "text", "text": part["text"]})
            elif "inline_data" in part:
                inline = part["inline_data"]
                if inline["mime_type"].startswith("image/"):
                    parts.append(
                        {
                            "type": "image_url",
                            "image_url": {"url": inline["data"]},
                        }
                    )
                else:
                    raise ValueError(
                        "Unsupported inline data for conversion to OpenAI payload."
                    )
            elif "function_call" in part:
                raise ValueError(
                    "Function call parts are not supported for OpenAI conversion."
                )
            else:
                raise ValueError("Unsupported Gemini part for OpenAI conversion.")
        normalized.append(
            cast(
                OpenAIChatMessage,
                {
                    "role": cast(GeminiChatMessage, message)["role"],
                    "content": parts,
                },
            )
        )
    return normalized


def _map_role_to_gemini(role: MessageRole) -> MessageRole:
    if role == "assistant":
        return "model"
    return role


def to_gemini_messages(messages: ChatMessages) -> list[GeminiChatMessage]:
    """Normalize chat messages into Google Gemini payloads."""

    normalized: list[GeminiChatMessage] = []
    for message in messages:
        if "parts" in message:
            gemini_msg = cast(GeminiChatMessage, dict(message))
            gemini_msg["role"] = _map_role_to_gemini(gemini_msg["role"])
            normalized.append(gemini_msg)
            continue
        if "content" not in message:
            raise ValueError("Chat message must include either 'content' or 'parts'.")
        content = cast(OpenAIChatMessage, message)["content"]
        parts: list[GeminiPart] = []
        if isinstance(content, str):
            if content:
                parts.append({"text": content})
        elif isinstance(content, list):
            for part in content:
                part_type = part.get("type") if isinstance(part, dict) else None
                if part_type == "text":
                    parts.append({"text": cast(str, part.get("text", ""))})
                elif part_type == "image_url":
                    image_url = (
                        part.get("image_url") if isinstance(part, dict) else None
                    )
                    if isinstance(image_url, dict) and "url" in image_url:
                        parts.append(
                            {
                                "inline_data": {
                                    "mime_type": "image/png",
                                    "data": cast(str, image_url["url"]),
                                }
                            }
                        )
                    else:
                        raise ValueError(
                            "Image part missing 'image_url.url' for Gemini conversion."
                        )
                else:
                    raise ValueError(
                        f"Unsupported OpenAI content part type '{part_type}' for Gemini."
                    )
        else:
            raise ValueError("Unsupported OpenAI content type for Gemini conversion.")
        normalized.append(
            {
                "role": _map_role_to_gemini(cast(OpenAIChatMessage, message)["role"]),
                "parts": parts,
            }
        )
    return normalized


class LLMClient(abc.ABC):
    """Abstract LLM client interface used by the app."""

    @abc.abstractmethod
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
