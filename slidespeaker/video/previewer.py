"""Video preview generation module (video package)."""

from pathlib import Path
from typing import Any, cast

from loguru import logger

from slidespeaker.configs.config import (
    get_storage_provider as global_get_storage_provider,
)
from slidespeaker.configs.locales import locale_utils
from slidespeaker.storage import StorageProvider
from slidespeaker.storage.paths import output_object_key

_storage_provider = None


def get_storage_provider() -> StorageProvider:
    global _storage_provider
    if _storage_provider is None:
        _storage_provider = global_get_storage_provider()
    return _storage_provider


class VideoPreviewer:
    def generate_preview_data(
        self, file_id: str, subtitle_language: str = "english"
    ) -> dict[str, Any]:
        try:
            storage = get_storage_provider()
            video_candidates = [
                output_object_key(file_id, "video", "final.mp4"),
                f"{file_id}.mp4",
                f"{file_id}_final.mp4",
            ]
            video_key = next(
                (key for key in video_candidates if storage.file_exists(key)), None
            )
            if not video_key:
                raise FileNotFoundError(f"Video file not found: {video_key}")
            video_url = storage.get_file_url(video_key)
            video_info = {
                "file_id": file_id,
                "video_url": video_url,
                "file_name": f"presentation_{file_id}.mp4",
                "file_size": 0,
            }
            subtitle_info: dict[str, Any] = {}
            locale_code = locale_utils.get_locale_code(subtitle_language)
            srt_candidates = [
                output_object_key(file_id, "subtitles", f"{locale_code}.srt"),
                f"{file_id}_{locale_code}.srt",
                f"{file_id}_final_{locale_code}.srt",
                f"{file_id}_final.srt",
            ]
            vtt_candidates = [
                output_object_key(file_id, "subtitles", f"{locale_code}.vtt"),
                f"{file_id}_{locale_code}.vtt",
                f"{file_id}_final_{locale_code}.vtt",
                f"{file_id}_final.vtt",
            ]
            srt_key = next((k for k in srt_candidates if storage.file_exists(k)), None)
            vtt_key = next((k for k in vtt_candidates if storage.file_exists(k)), None)
            logger.info(
                f"Checking for subtitle files: SRT={bool(srt_key)}, VTT={bool(vtt_key)}"
            )
            if srt_key:
                try:
                    srt_content = get_storage_provider().download_bytes(srt_key)
                    subtitle_info["srt_content"] = srt_content.decode("utf-8")
                    subtitle_info["srt_url"] = storage.get_file_url(srt_key)
                except Exception as e:
                    logger.error(f"Error reading SRT file: {e}")
            if vtt_key:
                try:
                    vtt_content = get_storage_provider().download_bytes(vtt_key)
                    subtitle_info["vtt_content"] = vtt_content.decode("utf-8")
                    subtitle_info["vtt_url"] = storage.get_file_url(vtt_key)
                except Exception as e:
                    logger.error(f"Error reading VTT file: {e}")
            subtitle_tracks = self.get_subtitle_tracks(file_id, subtitle_language)
            return {
                "video": video_info,
                "subtitles": subtitle_info,
                "subtitle_tracks": subtitle_tracks,
                "preview_available": True,
                "timestamp": Path.cwd().stat().st_mtime,
            }
        except Exception as e:
            print(f"Preview generation error: {e}")
            return {"preview_available": False, "error": str(e)}

    def get_subtitle_tracks(
        self, file_id: str, subtitle_language: str = "english"
    ) -> list[dict[str, Any]]:
        tracks: list[dict[str, Any]] = []
        lang_code = locale_utils.get_locale_code(subtitle_language)
        logger.info(
            f"Getting subtitle tracks for file_id={file_id}, language={subtitle_language}, lang_code={lang_code}"
        )
        storage = get_storage_provider()
        srt_candidates = [
            output_object_key(file_id, "subtitles", f"{lang_code}.srt"),
            f"{file_id}_{lang_code}.srt",
        ]
        srt_key = next((k for k in srt_candidates if storage.file_exists(k)), None)
        if srt_key:
            try:
                srt_url = storage.get_file_url(srt_key)
                tracks.append(
                    {
                        "kind": "subtitles",
                        "src": srt_url,
                        "srclang": lang_code,
                        "label": locale_utils.get_display_name(subtitle_language),
                        "format": "srt",
                    }
                )
            except Exception as e:
                logger.error(f"Error processing SRT track: {e}")
        vtt_candidates = [
            output_object_key(file_id, "subtitles", f"{lang_code}.vtt"),
            f"{file_id}_{lang_code}.vtt",
        ]
        vtt_key = next((k for k in vtt_candidates if storage.file_exists(k)), None)
        if vtt_key:
            try:
                vtt_url = storage.get_file_url(vtt_key)
                tracks.append(
                    {
                        "kind": "subtitles",
                        "src": vtt_url,
                        "srclang": lang_code,
                        "label": locale_utils.get_display_name(subtitle_language),
                        "format": "vtt",
                        "default": cast(Any, True),
                    }
                )
            except Exception as e:
                logger.error(f"Error processing VTT track: {e}")
        return tracks


__all__ = ["VideoPreviewer"]
