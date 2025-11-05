#!/usr/bin/env python3
"""CLI helpers to verify the shared LLM interface."""

from __future__ import annotations

import argparse
import base64
import importlib
import sys
import urllib.request
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import cast

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))
for dotenv_name in (".env", ".env.local"):
    candidate = ROOT_DIR / dotenv_name
    if candidate.exists():
        load_dotenv(candidate, override=False)

_console_utils = importlib.import_module("scripts._console_utils")
_llm_base = importlib.import_module("slidespeaker.llm.base")
_llm_provider = importlib.import_module("slidespeaker.llm.provider")
config = importlib.import_module("slidespeaker.configs.config").config

get_console = _console_utils.get_console
status_label = _console_utils.status_label
to_gemini_messages = _llm_base.to_gemini_messages
to_openai_messages = _llm_base.to_openai_messages
ChatMessages = _llm_base.ChatMessages
GeminiChatMessage = _llm_base.GeminiChatMessage
OpenAIChatMessage = _llm_base.OpenAIChatMessage
_get_llm = _llm_provider._get_llm
llm_chat_completion = _llm_provider.chat_completion
llm_image_generate = _llm_provider.image_generate
llm_tts_stream = _llm_provider.tts_speech_stream

console = get_console()

PROVIDERS = ("openai", "google")
LLM_METHODS = ("chat_completion", "image_generate", "tts_speech_stream")


def _verify_gemini_to_openai() -> tuple[bool, str | None]:
    """Ensure Gemini-style messages convert into OpenAI payloads."""
    gemini_messages: ChatMessages = [
        cast(
            GeminiChatMessage,
            {"role": "system", "parts": [{"text": "Follow instructions strictly."}]},
        ),
        cast(
            GeminiChatMessage,
            {
                "role": "user",
                "parts": [
                    {"text": "Describe the attached picture."},
                    {
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": "https://example.com/image.png",
                        }
                    },
                ],
            },
        ),
    ]

    try:
        normalized = to_openai_messages(gemini_messages)
    except Exception as exc:  # noqa: BLE001
        return False, f"Conversion raised: {exc}"

    if len(normalized) != 2:
        return False, f"Expected 2 messages, got {len(normalized)}."

    second = normalized[1]
    content = second.get("content")
    if not isinstance(content, list) or len(content) != 2:
        return False, "Second message should have both text and image parts."

    content_types = [part.get("type") for part in content if isinstance(part, dict)]
    if content_types != ["text", "image_url"]:
        return False, f"Unexpected content types: {content_types}."

    image_payload = content[1].get("image_url") if isinstance(content[1], dict) else {}
    if not isinstance(image_payload, dict) or "url" not in image_payload:
        return False, "Image part missing 'image_url.url'."

    return True, None


def _verify_openai_to_gemini() -> tuple[bool, str | None]:
    """Ensure OpenAI-style messages convert into Gemini payloads."""
    openai_messages: ChatMessages = [
        cast(
            OpenAIChatMessage,
            {"role": "system", "content": "Be concise and factual."},
        ),
        cast(
            OpenAIChatMessage,
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Provide a fun fact."},
                    {
                        "type": "image_url",
                        "image_url": {"url": "https://example.com/diagram.png"},
                    },
                ],
            },
        ),
        cast(
            OpenAIChatMessage,
            {"role": "assistant", "content": "Here is a relevant fact."},
        ),
    ]

    try:
        normalized = to_gemini_messages(openai_messages)
    except Exception as exc:  # noqa: BLE001
        return False, f"Conversion raised: {exc}"

    if len(normalized) != 3:
        return False, f"Expected 3 messages, got {len(normalized)}."

    if normalized[0]["role"] != "system":
        return False, "System role should remain 'system'."

    user_parts = normalized[1]["parts"]
    if len(user_parts) != 2:
        return False, "User message should include two parts."

    if "inline_data" not in user_parts[1]:
        return False, "Image payload should convert to inline_data."

    assistant_role = normalized[2]["role"]
    if assistant_role != "model":
        return False, f"Assistant role should map to 'model', got '{assistant_role}'."

    assistant_parts = normalized[2]["parts"]
    if not assistant_parts or "text" not in assistant_parts[0]:
        return False, "Assistant content should include a text part."

    return True, None


def _verify_message_conversions() -> bool:
    console.print("[bold cyan]Message normalization[/]")
    checks: Iterable[tuple[str, Callable[[], tuple[bool, str | None]]]] = (
        ("Gemini → OpenAI", _verify_gemini_to_openai),
        ("OpenAI → Gemini", _verify_openai_to_gemini),
    )

    all_ok = True
    for label, check in checks:
        ok, detail = check()
        mark = (
            status_label("OK", "bold green") if ok else status_label("FAIL", "bold red")
        )
        console.print(mark, label)
        if not ok and detail:
            console.print(f"  {detail}")
        all_ok = all_ok and ok
    return all_ok


def _normalize_model(candidate: str | None, fallback: str) -> str:
    base = fallback if "/" in fallback else f"openai/{fallback}"
    provider_prefix = base.split("/", 1)[0]
    model = (candidate or "").strip()
    if not model:
        return base
    if "/" in model:
        return model
    return f"{provider_prefix}/{model}"


def _default_chat_model() -> str:
    fallback = f"openai/{config.openai_model}"
    for candidate in (
        getattr(config, "script_generate_model", None),
        getattr(config, "script_model", None),
        getattr(config, "openai_model", None),
    ):
        if candidate:
            return _normalize_model(candidate, fallback)
    return fallback


def _default_image_model() -> str:
    google_default = f"google/{config.google_image_model}"
    openai_default = f"openai/{config.openai_image_model}"
    candidate = getattr(config, "image_generation_model", None)
    if candidate:
        normalized = candidate.lower()
        if "/" in normalized:
            provider = normalized.split("/", 1)[0]
            base = (
                google_default if provider in {"google", "gemini"} else openai_default
            )
        elif normalized.startswith("imagen"):
            base = google_default
        else:
            base = openai_default
        return _normalize_model(candidate, base)
    if getattr(config, "google_gemini_api_key", None):
        return google_default
    return openai_default


def _default_tts_model() -> str:
    fallback = f"openai/{config.openai_tts_model}"
    candidate = getattr(config, "tts_model", None)
    if candidate:
        return _normalize_model(candidate, fallback)
    return fallback


def _default_tts_voice(provider: str) -> str:
    explicit = getattr(config, "tts_voice", None)
    if explicit:
        return explicit
    if provider == "elevenlabs":
        return getattr(config, "elevenlabs_voice_id", None) or "Rachel"
    if provider == "google":
        return getattr(config, "google_tts_voice", None) or "polyglot-1"
    return getattr(config, "openai_tts_voice", None) or "alloy"


def _normalize_providers(raw: Sequence[str] | None) -> list[str]:
    if not raw:
        return list(PROVIDERS)
    normalized: list[str] = []
    for name in raw:
        lowered = name.strip().lower()
        if not lowered:
            continue
        if lowered == "gemini":
            lowered = "google"
        normalized.append(lowered)
    return normalized or list(PROVIDERS)


def _verify_provider_interfaces(providers: Sequence[str]) -> bool:
    console.print("[bold cyan]Provider interface[/]")
    all_ok = True
    for provider in providers:
        try:
            client = _get_llm(provider)
        except ValueError as exc:
            console.print(status_label("FAIL", "bold red"), f"{provider}: {exc}")
            all_ok = False
            continue
        except Exception as exc:  # noqa: BLE001
            console.print(
                status_label("FAIL", "bold red"), f"{provider}: unexpected error {exc}"
            )
            all_ok = False
            continue

        console.print(status_label(provider.upper(), "bold blue"))
        for method in LLM_METHODS:
            member = getattr(client, method, None)
            ok = callable(member)
            mark = (
                status_label("OK", "bold green")
                if ok
                else status_label("FAIL", "bold red")
            )
            console.print(mark, f"{provider}.{method}")
            all_ok = all_ok and ok
    return all_ok


def _save_image(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if url.startswith("data:"):
        header, _, payload = url.partition(",")
        if ";base64" not in header or not payload:
            raise ValueError("Unsupported data URI")
        destination.write_bytes(base64.b64decode(payload))
        return
    with urllib.request.urlopen(url) as response:
        destination.write_bytes(response.read())


def cmd_chat(args: argparse.Namespace) -> int:
    model = _normalize_model(args.model, _default_chat_model())
    messages: list[OpenAIChatMessage] = []
    if args.system:
        messages.append({"role": "system", "content": args.system})
    messages.append({"role": "user", "content": args.prompt})
    console.print(status_label("INFO", "bold blue"), f"Using model {model}")
    try:
        reply = llm_chat_completion(messages, model=model, timeout=args.timeout)
    except Exception as exc:  # noqa: BLE001
        console.print(status_label("FAIL", "bold red"), f"Chat request failed: {exc}")
        return 1
    if reply:
        console.print(status_label("OK", "bold green"), reply)
    else:
        console.print(status_label("OK", "bold green"), "[dim]<empty response>[/]")
    return 0


def cmd_image(args: argparse.Namespace) -> int:
    model = _normalize_model(args.model, _default_image_model())
    console.print(status_label("INFO", "bold blue"), f"Using model {model}")
    try:
        urls = llm_image_generate(
            prompt=args.prompt,
            model=model,
            size=args.size,
            n=args.count,
            timeout=args.timeout,
        )
    except Exception as exc:  # noqa: BLE001
        console.print(status_label("FAIL", "bold red"), f"Image request failed: {exc}")
        return 1

    if not urls:
        console.print(status_label("FAIL", "bold red"), "No image URLs returned.")
        return 1

    save_path = Path(args.save).expanduser().resolve() if args.save else None
    for idx, url in enumerate(urls, start=1):
        console.print(status_label("OK", "bold green"), f"[{idx}] {url}")
        if save_path:
            target = save_path
            if args.count > 1 or save_path.is_dir() or not save_path.suffix:
                directory = save_path if save_path.is_dir() else save_path.parent
                directory.mkdir(parents=True, exist_ok=True)
                target = directory / f"image_{idx}.png"
            try:
                _save_image(url, target)
                console.print(status_label("SAVE", "bold cyan"), str(target))
            except Exception as exc:  # noqa: BLE001
                console.print(
                    status_label("WARN", "bold yellow"),
                    f"Failed to save image {idx}: {exc}",
                )
    return 0


def cmd_tts(args: argparse.Namespace) -> int:
    model = _normalize_model(args.model, _default_tts_model())
    provider = model.split("/", 1)[0]
    voice = args.voice or _default_tts_voice(provider)
    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    console.print(status_label("INFO", "bold blue"), f"Using model {model}")
    console.print(status_label("INFO", "bold blue"), f"Voice {voice}")

    try:
        stream = llm_tts_stream(
            model=model,
            voice=voice,
            input_text=args.text,
            timeout=args.timeout,
        )
        with output_path.open("wb") as fh:
            for chunk in stream:
                fh.write(chunk)
    except Exception as exc:  # noqa: BLE001
        console.print(status_label("FAIL", "bold red"), f"TTS request failed: {exc}")
        return 1

    console.print(status_label("OK", "bold green"), f"Audio saved to {output_path}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    providers = _normalize_providers(args.providers)
    run_messages = not args.providers_only
    run_providers = not args.messages_only

    overall_ok = True
    if run_messages:
        overall_ok = _verify_message_conversions() and overall_ok
    else:
        console.print(
            status_label("SKIP", "bold yellow"),
            "Skipping message normalization checks.",
        )

    if run_providers:
        overall_ok = _verify_provider_interfaces(providers) and overall_ok
    else:
        console.print(
            status_label("SKIP", "bold yellow"), "Skipping provider interface checks."
        )

    return 0 if overall_ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LLM validation utilities.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    chat_parser = subparsers.add_parser(
        "chat",
        help="Send a quick chat completion request.",
    )
    chat_parser.add_argument("prompt", help="User prompt to send to the model.")
    chat_parser.add_argument(
        "--system",
        help="Optional system instruction.",
    )
    chat_parser.add_argument(
        "--model",
        help="Model specification (defaults to configured script model).",
    )
    chat_parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Optional request timeout override (seconds).",
    )
    chat_parser.set_defaults(func=cmd_chat)

    image_parser = subparsers.add_parser(
        "image",
        help="Generate an image and optionally save the result.",
    )
    image_parser.add_argument("prompt", help="Prompt describing the desired image.")
    image_parser.add_argument(
        "--model",
        help="Model specification (defaults to configured image model).",
    )
    image_parser.add_argument(
        "--size",
        default="1792x1024",
        help="Image size hint (default: 1792x1024).",
    )
    image_parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="Number of images to request (default: 1).",
    )
    image_parser.add_argument(
        "--save",
        help="Optional path to save images. Directory when requesting multiple.",
    )
    image_parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Optional request timeout override (seconds).",
    )
    image_parser.set_defaults(func=cmd_image)

    tts_parser = subparsers.add_parser(
        "tts",
        help="Generate speech audio for quick testing.",
    )
    tts_parser.add_argument("text", help="Input text to convert to speech.")
    tts_parser.add_argument(
        "--model",
        help="TTS model specification (defaults to configured TTS model).",
    )
    tts_parser.add_argument(
        "--voice",
        help="Voice identifier (provider-specific).",
    )
    tts_parser.add_argument(
        "--output",
        default="output/llm_cli_tts.wav",
        help="Path to save the generated audio (default: output/llm_cli_tts.wav).",
    )
    tts_parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Optional request timeout override (seconds).",
    )
    tts_parser.set_defaults(func=cmd_tts)

    verify_parser = subparsers.add_parser(
        "verify",
        help="Validate message conversions and provider interface implementation.",
    )
    verify_parser.add_argument(
        "--providers",
        nargs="+",
        metavar="NAME",
        help="Provider names to validate (default: openai google).",
    )
    verify_parser.add_argument(
        "--messages-only",
        action="store_true",
        help="Only run message normalization checks.",
    )
    verify_parser.add_argument(
        "--providers-only",
        action="store_true",
        help="Only run interface checks for providers.",
    )

    verify_parser.set_defaults(func=cmd_verify)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
