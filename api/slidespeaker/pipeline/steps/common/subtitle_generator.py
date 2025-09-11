"""
Shared subtitle generation logic for SlideSpeaker pipeline steps.

This module provides common functionality for generating subtitles from transcripts
in both PDF and presentation slide processing pipelines.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.subtitle import SubtitleGenerator
from slidespeaker.utils.config import config, get_storage_provider
from slidespeaker.utils.locales import locale_utils


async def generate_subtitles_common(
    file_id: str,
    state_key: str,
    get_transcripts_func: Callable[..., Any],
    get_audio_files_func: Callable[[str], Any],
    language: str = "english",
    is_pdf: bool = False,
) -> None:
    """
    Generate subtitles from transcripts using shared logic.

    Args:
        file_id: Unique identifier for the file
        state_key: State key to update (e.g., "generate_subtitles" or "generate_pdf_subtitles")
        get_transcripts_func: Function to retrieve transcripts data
        get_audio_files_func: Function to retrieve audio files data
        language: Target language for subtitles
        is_pdf: Whether this is for PDF processing

    Raises:
        ValueError: If no transcripts data is available
    """
    await state_manager.update_step_status(file_id, state_key, "processing")
    logger.info(f"Starting subtitle generation for file: {file_id}")

    # Get transcripts for subtitle generation
    # Pass language parameter if the function supports it
    try:
        transcripts_data = await get_transcripts_func(file_id, language)
    except TypeError:
        # Fallback for functions that don't accept language parameter
        transcripts_data = await get_transcripts_func(file_id)

    if not transcripts_data:
        logger.warning("No transcripts data available for subtitle generation")
        await state_manager.update_step_status(
            file_id, state_key, "completed", {"subtitle_files": [], "storage_urls": []}
        )
        return

    # Get audio files for timing
    audio_files_data = await get_audio_files_func(file_id)

    # Generate subtitle files
    try:
        work_dir = config.output_dir / file_id
        subtitle_dir = work_dir / "subtitles"
        subtitle_dir.mkdir(exist_ok=True, parents=True)

        # Include locale code in intermediate filenames for clarity
        locale_code = locale_utils.get_locale_code(language)
        intermediate_base = subtitle_dir / f"{file_id}_subtitles_{locale_code}.mp4"

        subtitle_generator = SubtitleGenerator()

        # Handle case where we have no audio files
        if not audio_files_data:
            logger.warning(
                "No audio files available for subtitle timing, using estimated durations"
            )
            # Create subtitles with estimated durations if no audio files are available
            srt_path, vtt_path = subtitle_generator.generate_subtitles(
                scripts=transcripts_data,
                audio_files=[],  # No audio files available
                video_path=Path(intermediate_base),
                language=language,
            )
        else:
            # Create subtitles with actual audio timing
            # Convert to Path objects and filter out non-existent files
            audio_paths = [Path(f) for f in audio_files_data if Path(f).exists()]
            srt_path, vtt_path = subtitle_generator.generate_subtitles(
                scripts=transcripts_data,
                audio_files=audio_paths,
                video_path=Path(intermediate_base),
                language=language,
            )

        logger.info(f"Generated subtitles: {srt_path}, {vtt_path}")

        # Upload subtitle files to storage provider
        subtitle_urls: list[str] = []
        storage_provider = get_storage_provider()
        try:
            srt_key = f"{file_id}_{locale_code}.srt"
            vtt_key = f"{file_id}_{locale_code}.vtt"

            srt_url = storage_provider.upload_file(str(srt_path), srt_key, "text/plain")
            vtt_url = storage_provider.upload_file(str(vtt_path), vtt_key, "text/vtt")

            subtitle_urls = [srt_url, vtt_url]
            logger.info(f"Uploaded subtitles to storage: {srt_url}, {vtt_url}")
        except Exception as storage_error:
            logger.error(f"Failed to upload subtitles to storage: {storage_error}")
            # Fallback to local paths if storage upload fails
            subtitle_urls = [str(srt_path), str(vtt_path)]

        # Store both local paths and storage URLs
        storage_data = {
            "subtitle_files": [str(srt_path), str(vtt_path)],
            "storage_urls": subtitle_urls,
        }

        await state_manager.update_step_status(
            file_id, state_key, "completed", storage_data
        )
        logger.info("Subtitle generation completed successfully")
    except Exception as e:
        logger.error(f"Failed to generate subtitles: {e}")
        import traceback

        logger.error(f"Subtitle generation traceback: {traceback.format_exc()}")
        await state_manager.update_step_status(
            file_id, state_key, "failed", {"error": str(e)}
        )
        raise


async def get_pdf_subtitles_transcripts(
    file_id: str, language: str = "english"
) -> list[dict[str, Any]]:
    """Get transcripts for PDF subtitle generation."""

    state = await state_manager.get_state(file_id)
    chapters: list[dict[str, Any]] = []

    # Determine which transcripts to use for subtitles based on language
    if state and "steps" in state:
        # If requesting English subtitles, prioritize English transcripts
        if language.lower() == "english":
            # Priority 1: Original English transcripts
            if (
                "segment_pdf_content" in state["steps"]
                and "data" in state["steps"]["segment_pdf_content"]
                and state["steps"]["segment_pdf_content"]["data"]
            ):
                chapters = state["steps"]["segment_pdf_content"]["data"]
                logger.info(
                    "Using original English transcripts for PDF subtitle generation"
                )
            # Priority 2: Translated subtitle transcripts (if they're English)
            elif (
                "translate_subtitle_transcripts" in state["steps"]
                and "data" in state["steps"]["translate_subtitle_transcripts"]
                and state["steps"]["translate_subtitle_transcripts"]["data"]
            ):
                # Check if these are English transcripts
                chapters = state["steps"]["translate_subtitle_transcripts"]["data"]
                logger.info(
                    f"Using translated subtitle transcripts for PDF subtitle generation (language: {language})"
                )
            # Priority 3: Translated voice transcripts (if they're English)
            elif (
                "translate_voice_transcripts" in state["steps"]
                and "data" in state["steps"]["translate_voice_transcripts"]
                and state["steps"]["translate_voice_transcripts"]["data"]
            ):
                # Check if these are English transcripts
                chapters = state["steps"]["translate_voice_transcripts"]["data"]
                logger.info(
                    f"Using translated voice transcripts for PDF subtitle generation (language: {language})"
                )
        else:
            # For non-English languages, prioritize translated transcripts
            # Priority 1: Use translated subtitle transcripts if available
            if (
                "translate_subtitle_transcripts" in state["steps"]
                and "data" in state["steps"]["translate_subtitle_transcripts"]
                and state["steps"]["translate_subtitle_transcripts"]["data"]
            ):
                chapters = state["steps"]["translate_subtitle_transcripts"]["data"]
                logger.info(
                    f"Using translated subtitle transcripts for PDF subtitle generation (language: {language})"
                )
            # Priority 2: Use translated voice transcripts as fallback
            elif (
                "translate_voice_transcripts" in state["steps"]
                and "data" in state["steps"]["translate_voice_transcripts"]
                and state["steps"]["translate_voice_transcripts"]["data"]
            ):
                chapters = state["steps"]["translate_voice_transcripts"]["data"]
                logger.info(
                    f"Using translated voice transcripts for PDF subtitle generation (language: {language})"
                )
            # Priority 3: Fall back to original chapters with English transcripts
            elif (
                "segment_pdf_content" in state["steps"]
                and "data" in state["steps"]["segment_pdf_content"]
                and state["steps"]["segment_pdf_content"]["data"]
            ):
                chapters = state["steps"]["segment_pdf_content"]["data"]
                logger.info(
                    "Using original English transcripts for PDF subtitle generation"
                )

    return chapters


async def get_slide_subtitles_transcripts(
    file_id: str, language: str = "english"
) -> list[dict[str, Any]]:
    """Get transcripts for slide subtitle generation."""

    state = await state_manager.get_state(file_id)
    transcripts_data: list[dict[str, Any]] = []

    # Determine which transcripts to use for subtitles based on language
    if state and "steps" in state:
        # If requesting English subtitles, prioritize English transcripts
        if language.lower() == "english":
            # Priority 1: Regular English transcripts
            if (
                "revise_transcripts" in state["steps"]
                and "data" in state["steps"]["revise_transcripts"]
                and state["steps"]["revise_transcripts"]["data"]
            ):
                transcripts_data = state["steps"]["revise_transcripts"]["data"]
                logger.info("Using regular English transcripts for subtitle generation")
            # Priority 2: Translated subtitle transcripts (if they're English)
            elif (
                "translate_subtitle_transcripts" in state["steps"]
                and "data" in state["steps"]["translate_subtitle_transcripts"]
                and state["steps"]["translate_subtitle_transcripts"]["data"]
            ):
                transcripts_data = state["steps"]["translate_subtitle_transcripts"][
                    "data"
                ]
                logger.info(
                    f"Using translated subtitle transcripts for subtitle generation (language: {language})"
                )
            # Priority 3: Translated voice transcripts (if they're English)
            elif (
                "translate_voice_transcripts" in state["steps"]
                and "data" in state["steps"]["translate_voice_transcripts"]
                and state["steps"]["translate_voice_transcripts"]["data"]
            ):
                transcripts_data = state["steps"]["translate_voice_transcripts"]["data"]
                logger.info(
                    f"Using translated voice transcripts for subtitle generation (language: {language})"
                )
        else:
            # For non-English languages, prioritize translated transcripts
            # Priority 1: Use translated subtitle transcripts if available
            if (
                "translate_subtitle_transcripts" in state["steps"]
                and "data" in state["steps"]["translate_subtitle_transcripts"]
                and state["steps"]["translate_subtitle_transcripts"]["data"]
            ):
                transcripts_data = state["steps"]["translate_subtitle_transcripts"][
                    "data"
                ]
                logger.info(
                    f"Using translated subtitle transcripts for subtitle generation (language: {language})"
                )
            # Priority 2: Use translated voice transcripts as fallback
            elif (
                "translate_voice_transcripts" in state["steps"]
                and "data" in state["steps"]["translate_voice_transcripts"]
                and state["steps"]["translate_voice_transcripts"]["data"]
            ):
                transcripts_data = state["steps"]["translate_voice_transcripts"]["data"]
                logger.info(
                    f"Using translated voice transcripts for subtitle generation (language: {language})"
                )
            # Priority 3: Fall back to regular English transcripts
            elif (
                "revise_transcripts" in state["steps"]
                and "data" in state["steps"]["revise_transcripts"]
                and state["steps"]["revise_transcripts"]["data"]
            ):
                transcripts_data = state["steps"]["revise_transcripts"]["data"]
                logger.info("Using regular English transcripts for subtitle generation")

    return transcripts_data


async def get_pdf_audio_files(file_id: str) -> list[str]:
    """Get audio files for PDF subtitle timing."""
    state = await state_manager.get_state(file_id)
    audio_files_data = []

    if (
        state
        and "steps" in state
        and "generate_pdf_audio" in state["steps"]
        and "data" in state["steps"]["generate_pdf_audio"]
        and state["steps"]["generate_pdf_audio"]["data"] is not None
    ):
        audio_data = state["steps"]["generate_pdf_audio"]["data"]
        # Handle both list format and legacy string format
        if isinstance(audio_data, str):
            # Legacy format - single string path
            audio_files_data = [audio_data] if Path(audio_data).exists() else []
        else:
            # Fallback for old format or unexpected data structure
            audio_files_data = audio_data if isinstance(audio_data, list) else []

    return audio_files_data


async def get_slide_audio_files(file_id: str) -> list[str]:
    """Get audio files for slide subtitle timing."""
    state = await state_manager.get_state(file_id)
    audio_files_data = []

    if (
        state
        and "steps" in state
        and "generate_audio" in state["steps"]
        and "data" in state["steps"]["generate_audio"]
        and state["steps"]["generate_audio"]["data"] is not None
    ):
        audio_files_data = state["steps"]["generate_audio"]["data"]

    return audio_files_data
