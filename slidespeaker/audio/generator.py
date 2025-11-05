"""
Audio generator for SlideSpeaker (audio package).

Centralizes text preparation for TTS, including optional translation of
podcast dialogue to the requested audio (voice) language.
"""

import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from slidespeaker.configs.config import config
from slidespeaker.llm import chat_completion

from .tts_factory import TTSFactory
from .tts_interface import TTSInterface

# System prompt for translating podcast dialogue for TTS
PODCAST_TRANSLATION_SYSTEM_PROMPT = (
    "You are a precise translator for podcast dialogues. "
    "Translate the text to the target language while strictly "
    "preserving speaker labels and structure. Output only lines that start with "
    "'Host:' or 'Guest:'. Do not add notes or labels; return only the translated "
    "dialogue lines. Avoid any references to visuals or slides; focus purely on "
    "content. Do NOT include any standalone labels like 'Transition:'; if present "
    "in the source, incorporate the idea into the Host/Guest line without the label."
)


class AudioGenerator:
    """Generator for text-to-speech audio files"""

    def __init__(self) -> None:
        try:
            self.tts_service: TTSInterface | None = TTSFactory.create_service(
                config.tts_model
            )
        except Exception as e:
            print(f"Warning: Could not initialize TTS service: {e}")
            self.tts_service = None

    async def generate_audio(
        self,
        text: str,
        output_path: str,
        language: str = "english",
        voice: str | None = None,
    ) -> bool:
        if not self.tts_service:
            print("Error: TTS service not available")
            return False
        if not text.strip():
            return False
        try:
            output_path_obj = Path(output_path)
            output_path_obj.parent.mkdir(parents=True, exist_ok=True)
            await self.tts_service.generate_speech(
                text, output_path_obj, language, voice
            )
            return output_path_obj.exists() and output_path_obj.stat().st_size > 0
        except Exception as e:
            print(f"Error generating audio: {e}")
            return False

    # ----------------------- Dialogue preparation utils -----------------------

    @staticmethod
    def _strip_transition_label(text: Any | None) -> str:
        t = str(text or "").strip()
        t = re.sub(r"^(transition)\s*[:\-—–]\s*", "", t, flags=re.IGNORECASE)
        return t.strip()

    @staticmethod
    def _build_translate_prompt(
        dialogue: list[dict[str, Any]], target_language: str
    ) -> str:
        lines: list[str] = []
        lines.append(
            f"Translate the following Host/Guest dialogue into {target_language}.\n"
            "Keep each line on its own, prefixing with 'Host:' or 'Guest:' exactly as given.\n"
            "Return plain text lines only, one per line, no numbering or extra text.\n"
        )
        lines.append("\nDialogue:\n")
        for item in dialogue:
            sp = (item.get("speaker") or "Host").strip()
            tx = (item.get("text") or "").strip()
            if tx:
                lines.append(f"{sp}: {tx}")
        return "\n".join(lines)

    def translate_dialogue(
        self, dialogue: list[dict[str, Any]], target_language: str
    ) -> list[dict[str, str]]:
        """Translate Host/Guest dialogue into target_language, preserving labels."""
        if (target_language or "").lower() in ("", "english"):
            return [
                {
                    "speaker": (d.get("speaker") or "Host"),
                    "text": self._strip_transition_label(d.get("text")),
                }
                for d in (dialogue or [])
                if (d.get("text") or "").strip()
            ]
        # Build prompt with a module-level system prompt for clarity and reuse
        prompt = self._build_translate_prompt(dialogue, target_language)
        try:
            content = chat_completion(
                model=config.translation_model,
                messages=[
                    {"role": "system", "content": PODCAST_TRANSLATION_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            )
            lines = [ln.strip() for ln in str(content or "").split("\n") if ln.strip()]
            out: list[dict[str, str]] = []
            for ln in lines:
                role = (
                    "Host"
                    if ln.lower().startswith("host:")
                    else ("Guest" if ln.lower().startswith("guest:") else None)
                )
                text = ln.split(":", 1)[1].strip() if ":" in ln else ln
                text = self._strip_transition_label(text)
                if role and text:
                    out.append({"speaker": role, "text": text})
            return (
                out
                if out
                else [
                    {
                        "speaker": (d.get("speaker") or "Host"),
                        "text": self._strip_transition_label(d.get("text")),
                    }
                    for d in (dialogue or [])
                    if (d.get("text") or "").strip()
                ]
            )
        except Exception:
            return [
                {
                    "speaker": (d.get("speaker") or "Host"),
                    "text": self._strip_transition_label(d.get("text")),
                }
                for d in (dialogue or [])
                if (d.get("text") or "").strip()
            ]

    def prepare_dialogue_for_audio(
        self,
        base_dialogue_en: list[dict[str, Any]],
        translated_dialogue: list[dict[str, Any]] | None,
        transcript_language: str | None,
        voice_language: str,
    ) -> list[dict[str, str]]:
        """Return dialogue in the exact voice language for TTS.

        - If voice is English -> use base English dialogue.
        - If transcript dialogue exists in the same language as voice -> reuse it.
        - Otherwise, translate base English to the voice language.
        """
        vlang = (voice_language or "english").lower()
        tlang = (transcript_language or "").lower()
        if vlang == "english":
            return [
                {
                    "speaker": (d.get("speaker") or "Host"),
                    "text": self._strip_transition_label(d.get("text")),
                }
                for d in (base_dialogue_en or [])
                if (d.get("text") or "").strip()
            ]
        if translated_dialogue and tlang == vlang:
            return [
                {
                    "speaker": (d.get("speaker") or "Host"),
                    "text": self._strip_transition_label(d.get("text")),
                }
                for d in (translated_dialogue or [])
                if (d.get("text") or "").strip()
            ]
        # Need a translation specifically for the TTS voice language
        return self.translate_dialogue(base_dialogue_en or [], vlang)

    def _get_audio_duration(self, audio_path: Path) -> float:
        try:
            if not audio_path.exists() or audio_path.stat().st_size == 0:
                return self._estimate_duration_from_text(audio_path)
            max_retries = 5
            for attempt in range(max_retries):
                if attempt > 0:
                    time.sleep(0.2 * (attempt + 1))
                try:
                    time.sleep(0.1)
                    cmd = [
                        "ffprobe",
                        "-v",
                        "quiet",
                        "-print_format",
                        "json",
                        "-show_format",
                        "-show_streams",
                        str(audio_path),
                    ]
                    result = subprocess.run(
                        cmd, capture_output=True, text=True, timeout=15
                    )
                    if result.returncode != 0:
                        if attempt == max_retries - 1:
                            return self._fallback_audio_duration(audio_path)
                        continue
                    if not result.stdout.strip():
                        if attempt == max_retries - 1:
                            return self._fallback_audio_duration(audio_path)
                        continue
                    data = json.loads(result.stdout)
                    if "format" in data and "duration" in data["format"]:
                        return float(data["format"]["duration"])
                    if "streams" in data:
                        for stream in data["streams"]:
                            if "duration" in stream:
                                return float(stream["duration"])
                except subprocess.TimeoutExpired:
                    if attempt == max_retries - 1:
                        return self._fallback_audio_duration(audio_path)
                    continue
                except json.JSONDecodeError:
                    if attempt == max_retries - 1:
                        return self._fallback_audio_duration(audio_path)
                    continue
                except Exception:
                    if attempt == max_retries - 1:
                        return self._fallback_audio_duration(audio_path)
                    continue
        except Exception:
            return self._fallback_audio_duration(audio_path)
        return self._fallback_audio_duration(audio_path)

    def _estimate_duration_from_text(self, _audio_path: Path) -> float:
        try:
            return 10.0
        except Exception:
            return 5.0

    def _fallback_audio_duration(self, audio_path: Path) -> float:
        """Attempt secondary strategies to measure audio duration."""
        try:
            from moviepy import AudioFileClip

            with AudioFileClip(str(audio_path)) as clip:
                duration = float(getattr(clip, "duration", 0.0) or 0.0)
                if duration > 0:
                    return duration
        except Exception:
            pass
        return self._estimate_duration_from_text(audio_path)

    def get_supported_voices(self, language: str = "english") -> list[str]:
        if not self.tts_service:
            return []
        try:
            return self.tts_service.get_supported_voices(language)
        except Exception as e:
            print(f"Error getting supported voices: {e}")
            return []

    def is_available(self) -> bool:
        if not self.tts_service:
            return False
        try:
            return self.tts_service.is_available()
        except Exception:
            return False
