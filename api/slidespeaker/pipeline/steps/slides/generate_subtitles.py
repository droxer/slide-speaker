"""
Generate subtitles step for the presentation pipeline.

This module generates subtitle files (SRT and VTT formats) from the scripts.
It creates timed subtitles that can be used with the final presentation video,
supporting multiple languages and automatic timing based on audio durations.
"""

from pathlib import Path
from typing import Any

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.processing.subtitle_generator import SubtitleGenerator
from slidespeaker.utils.config import config, get_storage_provider
from slidespeaker.utils.locales import locale_utils

subtitle_generator = SubtitleGenerator()

# Get storage provider instance
storage_provider = get_storage_provider()


async def generate_subtitles_step(file_id: str, language: str = "english") -> None:
    """
    Generate subtitles from scripts in SRT and VTT formats.

    This function creates timed subtitle files for the presentation video.
    It uses either subtitle-specific scripts (when audio and subtitle languages differ)
    or regular scripts, and synchronizes subtitles with audio durations when available.
    The function supports multiple languages and generates both SRT and VTT formats.
    """
    await state_manager.update_step_status(file_id, "generate_subtitles", "processing")
    logger.info(f"Starting subtitle generation for file: {file_id}")
    state = await state_manager.get_state(file_id)

    # Always generate subtitles
    # Get scripts for subtitle generation
    # Use translated subtitle scripts first, then subtitle-specific scripts,
    # then translated voice scripts, and finally regular scripts as fallback
    scripts_data: list[dict[str, Any]] = []
    if state and "steps" in state:
        # Check for translated subtitle scripts first
        if (
            "translate_subtitle_scripts" in state["steps"]
            and state["steps"]["translate_subtitle_scripts"]["data"] is not None
            and state["steps"]["translate_subtitle_scripts"].get("status")
            == "completed"
        ):
            scripts_data = state["steps"]["translate_subtitle_scripts"]["data"]
            logger.info("Using translated subtitle scripts for subtitle generation")
        # Check if subtitle scripts exist (languages are different)
        elif (
            "review_subtitle_scripts" in state["steps"]
            and state["steps"]["review_subtitle_scripts"]["data"] is not None
        ):
            scripts_data = state["steps"]["review_subtitle_scripts"]["data"]
            logger.info("Using subtitle-specific scripts for subtitle generation")
        # Check for translated voice scripts
        elif (
            "translate_voice_scripts" in state["steps"]
            and state["steps"]["translate_voice_scripts"]["data"] is not None
            and state["steps"]["translate_voice_scripts"].get("status") == "completed"
        ):
            scripts_data = state["steps"]["translate_voice_scripts"]["data"]
            logger.info("Using translated voice scripts for subtitle generation")
        # Fall back to regular scripts if subtitle scripts don't exist
        elif (
            "review_scripts" in state["steps"]
            and state["steps"]["review_scripts"]["data"] is not None
        ):
            scripts_data = state["steps"]["review_scripts"]["data"]
            logger.info("Using regular scripts for subtitle generation")

    if not scripts_data:
        logger.warning("No scripts data available for subtitle generation")
        await state_manager.update_step_status(
            file_id, "generate_subtitles", "completed", []
        )
        return

    # Get audio files for timing
    audio_files_data = []
    if (
        state
        and "steps" in state
        and "generate_audio" in state["steps"]
        and state["steps"]["generate_audio"]["data"] is not None
    ):
        audio_files_data = state["steps"]["generate_audio"]["data"]

    # Generate subtitle files
    try:
        video_path = config.output_dir / f"{file_id}_final.mp4"

        # If we have no audio files, we need to provide estimated durations
        if not audio_files_data:
            logger.info(
                "No audio files available, using estimated durations for subtitles"
            )
            # Create a list of dummy paths for estimated durations (5 seconds each)
            estimated_audio_files = [
                Path(f"/tmp/dummy_audio_{i}.mp3") for i in range(len(scripts_data))
            ]
            srt_path, vtt_path = subtitle_generator.generate_subtitles(
                scripts_data,
                estimated_audio_files,
                video_path,
                language,
            )
        else:
            audio_files = [Path(p) for p in audio_files_data]
            srt_path, vtt_path = subtitle_generator.generate_subtitles(
                scripts_data, audio_files, video_path, language
            )
        logger.info(f"Generated subtitles: {srt_path}, {vtt_path}")

        # Upload subtitle files to storage provider
        subtitle_urls = []
        try:
            # Include locale/language in filename to distinguish different language variants
            locale_code = locale_utils.get_locale_code(language)
            srt_key = f"{file_id}_final_{locale_code}.srt"
            vtt_key = f"{file_id}_final_{locale_code}.vtt"

            srt_url = storage_provider.upload_file(str(srt_path), srt_key, "text/plain")
            vtt_url = storage_provider.upload_file(str(vtt_path), vtt_key, "text/vtt")

            subtitle_urls = [srt_url, vtt_url]
            logger.info(f"Uploaded subtitles to storage: {srt_url}, {vtt_url}")
        except Exception as e:
            logger.error(f"Failed to upload subtitles to storage: {e}")
            # Fallback to local paths if storage upload fails
            subtitle_urls = [str(srt_path), str(vtt_path)]

        # Store the subtitle file URLs in the state
        await state_manager.update_step_status(
            file_id, "generate_subtitles", "completed", subtitle_urls
        )
        logger.info("Stage 'Generating subtitles' completed successfully")

    except Exception as e:
        logger.error(f"Failed to generate subtitles: {e}")
        import traceback

        logger.error(f"Subtitle generation traceback: {traceback.format_exc()}")
        await state_manager.update_step_status(
            file_id, "generate_subtitles", "failed", []
        )
        raise
