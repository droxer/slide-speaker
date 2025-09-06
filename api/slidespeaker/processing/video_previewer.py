"""
Video preview generation module for SlideSpeaker.

This module generates preview data for completed videos, including video information
and subtitle content for use in the web interface.
"""

from pathlib import Path
from typing import Any

from loguru import logger

from ..storage import StorageProvider
from ..utils.config import get_storage_provider as global_get_storage_provider
from ..utils.locales import locale_utils

# Storage provider will be initialized lazily when needed
_storage_provider = None


def get_storage_provider() -> StorageProvider:
    """Get storage provider instance (lazy initialization)."""
    global _storage_provider
    if _storage_provider is None:
        _storage_provider = global_get_storage_provider()
    return _storage_provider


class VideoPreviewer:
    """Generate preview data for videos with subtitles"""

    def generate_preview_data(
        self,
        file_id: str,
        subtitle_language: str = "english",
    ) -> dict[str, Any]:
        """
        Generate preview data including video info and subtitle content

        Args:
            file_id: The file ID of the generated video
            output_dir: Directory where files are stored
            subtitle_language: Language of the subtitles

        Returns:
            Dictionary with preview information
        """
        try:
            # Check if video exists
            video_key = f"{file_id}_final.mp4"
            if not get_storage_provider().file_exists(video_key):
                raise FileNotFoundError(f"Video file not found: {video_key}")

            # Get video info using storage provider for consistency
            storage = get_storage_provider()
            video_url = storage.get_file_url(video_key)

            video_info = {
                "file_id": file_id,
                "video_url": video_url,
                "file_name": f"presentation_{file_id}.mp4",
                # File size is not easily available for cloud storage without downloading
                "file_size": 0,  # Will be populated by the client when video is loaded
            }

            # Check for subtitles with locale-aware filenames
            subtitle_info = {}
            locale_code = locale_utils.get_locale_code(subtitle_language)
            srt_key = f"{file_id}_final_{locale_code}.srt"
            vtt_key = f"{file_id}_final_{locale_code}.vtt"

            # Try locale-aware filenames first, then fall back to legacy format
            srt_exists = get_storage_provider().file_exists(srt_key)
            vtt_exists = get_storage_provider().file_exists(vtt_key)

            # Fall back to legacy format if locale-aware doesn't exist
            if not srt_exists:
                legacy_srt_key = f"{file_id}_final.srt"
                if get_storage_provider().file_exists(legacy_srt_key):
                    srt_key = legacy_srt_key
                    srt_exists = True

            if not vtt_exists:
                legacy_vtt_key = f"{file_id}_final.vtt"
                if get_storage_provider().file_exists(legacy_vtt_key):
                    vtt_key = legacy_vtt_key
                    vtt_exists = True

            logger.info(
                f"Checking for subtitle files: SRT={srt_exists}, VTT={vtt_exists}"
            )

            if srt_exists:
                try:
                    srt_content = get_storage_provider().download_bytes(srt_key)
                    subtitle_info["srt_content"] = srt_content.decode("utf-8")
                    # Use storage provider for consistent URL generation
                    subtitle_info["srt_url"] = storage.get_file_url(srt_key)
                    logger.info("SRT file found and read successfully")
                except Exception as e:
                    logger.error(f"Error reading SRT file: {e}")

            if vtt_exists:
                try:
                    vtt_content = get_storage_provider().download_bytes(vtt_key)
                    subtitle_info["vtt_content"] = vtt_content.decode("utf-8")
                    # Use storage provider for consistent URL generation
                    subtitle_info["vtt_url"] = storage.get_file_url(vtt_key)
                    logger.info("VTT file found and read successfully")
                except Exception as e:
                    logger.error(f"Error reading VTT file: {e}")

            # Get subtitle tracks for HTML5 video
            subtitle_tracks = self.get_subtitle_tracks(file_id, subtitle_language)

            # Generate preview data
            preview_data = {
                "video": video_info,
                "subtitles": subtitle_info,
                "subtitle_tracks": subtitle_tracks,
                "preview_available": True,
                "timestamp": Path.cwd()
                .stat()
                .st_mtime,  # Use current dir mtime as timestamp
            }

            return preview_data

        except Exception as e:
            print(f"Preview generation error: {e}")
            return {"preview_available": False, "error": str(e)}

    def get_subtitle_tracks(
        self,
        file_id: str,
        subtitle_language: str = "english",
    ) -> list[dict[str, Any]]:
        """
        Get available subtitle tracks for a video

        Args:
            file_id: The file ID of the generated video
            output_dir: Directory where files are stored
            subtitle_language: Language of the subtitles

        Returns:
            List of subtitle track information
        """
        tracks = []
        lang_code = locale_utils.get_locale_code(subtitle_language)

        logger.info(
            f"Getting subtitle tracks for file_id={file_id}, language={subtitle_language}, lang_code={lang_code}"
        )

        storage = get_storage_provider()

        # Check for SRT subtitle track with locale-aware filename
        srt_key = f"{file_id}_final_{lang_code}.srt"
        srt_exists = get_storage_provider().file_exists(srt_key)

        # Fall back to legacy format if locale-aware doesn't exist
        if not srt_exists:
            legacy_srt_key = f"{file_id}_final.srt"
            if get_storage_provider().file_exists(legacy_srt_key):
                srt_key = legacy_srt_key
                srt_exists = True

        logger.info(f"Checking SRT file: {srt_key}, exists: {srt_exists}")
        if srt_exists:
            # Use storage provider for consistent URL generation
            srt_url = storage.get_file_url(srt_key)
            tracks.append(
                {
                    "kind": "subtitles",
                    "label": f"Subtitles ({subtitle_language.title()})",
                    "src": srt_url,
                    "srclang": lang_code,
                    "default": False,
                }
            )
            logger.info(f"Added SRT track: srclang={lang_code}, url={srt_url}")

        # Check for VTT subtitle track with locale-aware filename
        vtt_key = f"{file_id}_final_{lang_code}.vtt"
        vtt_exists = get_storage_provider().file_exists(vtt_key)

        # Fall back to legacy format if locale-aware doesn't exist
        if not vtt_exists:
            legacy_vtt_key = f"{file_id}_final.vtt"
            if get_storage_provider().file_exists(legacy_vtt_key):
                vtt_key = legacy_vtt_key
                vtt_exists = True

        logger.info(f"Checking VTT file: {vtt_key}, exists: {vtt_exists}")
        if vtt_exists:
            # Use storage provider for consistent URL generation
            vtt_url = storage.get_file_url(vtt_key)
            tracks.append(
                {
                    "kind": "subtitles",
                    "label": f"Subtitles ({subtitle_language.title()})",
                    "src": vtt_url,
                    "srclang": lang_code,
                    "default": True,
                }
            )
            logger.info(f"Added VTT track: srclang={lang_code}, url={vtt_url}")

        logger.info(f"Returning {len(tracks)} subtitle tracks")
        return tracks
