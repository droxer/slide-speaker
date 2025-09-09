"""
Generate subtitles step for the presentation pipeline.

This module generates subtitle files (SRT and VTT formats) from the transcripts.
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

# Storage provider will be resolved at upload time to honor current config


async def generate_subtitles_step(file_id: str, language: str = "english") -> None:
    """
    Generate subtitles from transcripts in SRT and VTT formats.

    This function creates timed subtitle files for the presentation video.
    It uses either subtitle-specific transcripts (when audio and subtitle languages differ)
    or regular transcripts, and synchronizes subtitles with audio durations when available.
    The function supports multiple languages and generates both SRT and VTT formats.
    """
    await state_manager.update_step_status(file_id, "generate_subtitles", "processing")
    logger.info(f"Starting subtitle generation for file: {file_id}")
    state = await state_manager.get_state(file_id)

    # Always generate subtitles
    # Get transcripts for subtitle generation
    # Use translated subtitle transcripts first, then subtitle-specific transcripts,
    # then translated voice transcripts, and finally regular transcripts as fallback
    transcripts_data: list[dict[str, Any]] = []
    if state and "steps" in state:
        # Check for translated subtitle transcripts first
        if (
            "translate_subtitle_transcripts" in state["steps"]
            and state["steps"]["translate_subtitle_transcripts"]["data"] is not None
            and state["steps"]["translate_subtitle_transcripts"].get("status")
            == "completed"
        ):
            transcripts_data = state["steps"]["translate_subtitle_transcripts"]["data"]
            logger.info("Using translated subtitle transcripts for subtitle generation")
        # Check if subtitle transcripts exist (languages are different)
        elif (
            "revise_subtitle_transcripts" in state["steps"]
            and state["steps"]["revise_subtitle_transcripts"]["data"] is not None
        ):
            transcripts_data = state["steps"]["revise_subtitle_transcripts"]["data"]
            logger.info("Using subtitle-specific transcripts for subtitle generation")
        # Check for translated voice transcripts
        elif (
            "translate_voice_transcripts" in state["steps"]
            and state["steps"]["translate_voice_transcripts"]["data"] is not None
            and state["steps"]["translate_voice_transcripts"].get("status")
            == "completed"
        ):
            transcripts_data = state["steps"]["translate_voice_transcripts"]["data"]
            logger.info("Using translated voice transcripts for subtitle generation")
        # Fall back to regular transcripts if subtitle transcripts don't exist
        elif (
            "revise_transcripts" in state["steps"]
            and state["steps"]["revise_transcripts"]["data"] is not None
        ):
            transcripts_data = state["steps"]["revise_transcripts"]["data"]
            logger.info("Using regular transcripts for subtitle generation")

    if not transcripts_data:
        logger.warning("No transcripts data available for subtitle generation")
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

    # Generate subtitle files into intermediate debug folder
    try:
        # Use a stable intermediate folder structure: output/{file_id}/subtitles/
        work_dir = config.output_dir / file_id
        subtitle_dir = work_dir / "subtitles"
        subtitle_dir.mkdir(exist_ok=True, parents=True)

        # Include locale code in intermediate filenames for clarity
        locale_code = locale_utils.get_locale_code(language)
        intermediate_base = subtitle_dir / f"{file_id}_subtitles_{locale_code}.mp4"

        # If we have no audio files, we need to provide estimated durations
        if not audio_files_data:
            logger.info(
                "No audio files available, using estimated durations for subtitles"
            )
            # Create a list of dummy paths for estimated durations (5 seconds each)
            estimated_audio_files = [
                Path(f"/tmp/dummy_audio_{i}.mp3") for i in range(len(transcripts_data))
            ]
            srt_path, vtt_path = subtitle_generator.generate_subtitles(
                transcripts_data,
                estimated_audio_files,
                intermediate_base,
                language,
            )
        else:
            audio_files = [Path(p) for p in audio_files_data]
            srt_path, vtt_path = subtitle_generator.generate_subtitles(
                transcripts_data, audio_files, intermediate_base, language
            )
        logger.info(f"Generated subtitles: {srt_path}, {vtt_path}")

        # Upload subtitle files to storage provider
        subtitle_urls: list[str] = []
        storage_provider = get_storage_provider()
        try:
            # Include locale/language in storage filename to distinguish variants
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

        # Store both local paths and storage URLs (mirror PDF structure for consistency)
        storage_data = {
            "local_paths": [str(srt_path), str(vtt_path)],
            "storage_urls": subtitle_urls,
            "final_subtitles": {
                "local_paths": [str(srt_path), str(vtt_path)],
                "storage_urls": subtitle_urls,
            },
        }

        await state_manager.update_step_status(
            file_id, "generate_subtitles", "completed", storage_data
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
