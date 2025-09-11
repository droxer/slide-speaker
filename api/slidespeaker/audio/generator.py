"""
Audio generator for SlideSpeaker (audio package).
"""

import json
import subprocess
import time
from pathlib import Path

from .tts_factory import TTSFactory
from .tts_interface import TTSInterface


class AudioGenerator:
    """Generator for text-to-speech audio files"""

    def __init__(self) -> None:
        try:
            self.tts_service: TTSInterface | None = TTSFactory.create_service()
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
            print("Warning: Empty text provided for audio generation")
            return False
        try:
            output_path_obj = Path(output_path)
            output_path_obj.parent.mkdir(parents=True, exist_ok=True)
            await self.tts_service.generate_speech(
                text, output_path_obj, language, voice
            )
            if output_path_obj.exists():
                file_size = output_path_obj.stat().st_size
                print(f"Generated audio file: {output_path_obj} ({file_size} bytes)")
                duration = self._get_audio_duration(output_path_obj)
                if duration > 0:
                    print(f"Audio duration: {duration:.2f} seconds")
                    word_count = len(text.split())
                    if duration > 0:
                        wpm = (word_count / duration) * 60
                        print(f"Speech rate: {wpm:.0f} words per minute")
                        if wpm < 100 or wpm > 300:
                            print(
                                f"Warning: Unusual speech rate detected ({wpm:.0f} WPM)"
                            )
            else:
                print(f"Warning: Audio file was not created at {output_path_obj}")
            return True
        except Exception as e:
            print(f"Error generating audio: {e}")
            return False

    def _get_audio_duration(self, audio_path: Path) -> float:
        try:
            if not audio_path.exists() or audio_path.stat().st_size == 0:
                print(f"Warning: Audio file unavailable or empty: {audio_path}")
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
                    if attempt == 0:
                        print(f"Info: Running ffprobe for {audio_path.name}")
                    result = subprocess.run(
                        cmd, capture_output=True, text=True, timeout=15
                    )
                    if result.returncode != 0:
                        if attempt == max_retries - 1:
                            return self._estimate_duration_from_text(audio_path)
                        continue
                    if not result.stdout.strip():
                        if attempt == max_retries - 1:
                            return self._estimate_duration_from_text(audio_path)
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
                        return self._estimate_duration_from_text(audio_path)
                    continue
                except json.JSONDecodeError:
                    if attempt == max_retries - 1:
                        return self._estimate_duration_from_text(audio_path)
                    continue
                except Exception:
                    if attempt == max_retries - 1:
                        return self._estimate_duration_from_text(audio_path)
                    continue
        except Exception:
            return self._estimate_duration_from_text(audio_path)
        return self._estimate_duration_from_text(audio_path)

    def _estimate_duration_from_text(self, _audio_path: Path) -> float:
        try:
            return 10.0
        except Exception:
            return 5.0

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
