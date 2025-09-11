"""Video preview generation module (video package)."""

from pathlib import Path
from typing import Any, cast

from loguru import logger

from slidespeaker.storage import StorageProvider
from slidespeaker.utils.config import (
    get_storage_provider as global_get_storage_provider,
)
from slidespeaker.utils.locales import locale_utils

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
            # Prefer new naming without _final, fallback to legacy
            storage = get_storage_provider()
            video_key = (
                f"{file_id}.mp4"
                if storage.file_exists(f"{file_id}.mp4")
                else f"{file_id}_final.mp4"
            )
            if not storage.file_exists(video_key):
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
            srt_key = f"{file_id}_{locale_code}.srt"
            vtt_key = f"{file_id}_{locale_code}.vtt"
            srt_exists = get_storage_provider().file_exists(srt_key)
            vtt_exists = get_storage_provider().file_exists(vtt_key)
            if not srt_exists:
                legacy_srt_key = f"{file_id}_final_{locale_code}.srt"
                if get_storage_provider().file_exists(legacy_srt_key):
                    srt_key = legacy_srt_key
                    srt_exists = True
                else:
                    legacy_srt2 = f"{file_id}_final.srt"
                    if get_storage_provider().file_exists(legacy_srt2):
                        srt_key = legacy_srt2
                        srt_exists = True
            if not vtt_exists:
                legacy_vtt_key = f"{file_id}_final_{locale_code}.vtt"
                if get_storage_provider().file_exists(legacy_vtt_key):
                    vtt_key = legacy_vtt_key
                    vtt_exists = True
                else:
                    legacy_vtt2 = f"{file_id}_final.vtt"
                    if get_storage_provider().file_exists(legacy_vtt2):
                        vtt_key = legacy_vtt2
                        vtt_exists = True
            logger.info(
                f"Checking for subtitle files: SRT={srt_exists}, VTT={vtt_exists}"
            )
            if srt_exists:
                try:
                    srt_content = get_storage_provider().download_bytes(srt_key)
                    subtitle_info["srt_content"] = srt_content.decode("utf-8")
                    subtitle_info["srt_url"] = storage.get_file_url(srt_key)
                except Exception as e:
                    logger.error(f"Error reading SRT file: {e}")
            if vtt_exists:
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
        srt_key = f"{file_id}_{lang_code}.srt"
        if get_storage_provider().file_exists(srt_key):
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
        vtt_key = f"{file_id}_{lang_code}.vtt"
        if get_storage_provider().file_exists(vtt_key):
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
