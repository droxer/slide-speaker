"""
Shared audio generation logic for SlideSpeaker pipeline steps.

This module provides common functionality for generating audio from transcripts
in both PDF and presentation slide processing pipelines.
"""

from collections.abc import Callable
from typing import Any

from loguru import logger

from slidespeaker.audio import AudioGenerator
from slidespeaker.core.state_manager import state_manager
from slidespeaker.utils.config import config


async def generate_audio_common(
    file_id: str,
    state_key: str,
    get_transcripts_func: Callable[[str], Any],
    is_pdf: bool = False,
) -> None:
    """
    Generate audio from transcripts using shared logic.

    Args:
        file_id: Unique identifier for the file
        state_key: State key to update (e.g., "generate_audio" or "generate_pdf_audio")
        get_transcripts_func: Function to retrieve transcripts data
        is_pdf: Whether this is for PDF processing

    Raises:
        ValueError: If no transcripts data is available
    """
    await state_manager.update_step_status(file_id, state_key, "processing")
    logger.info(f"Starting audio generation for file: {file_id}")

    # Get transcripts data
    transcripts = await get_transcripts_func(file_id)

    if not transcripts:
        raise ValueError("No transcripts data available for audio generation")

    # Prepare intermediate audio directory
    audio_dir = config.output_dir / file_id / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    audio_files = []
    audio_generator = AudioGenerator()

    # Determine default language from state (voice_language), fallback to English
    state = await state_manager.get_state(file_id)
    default_language = "english"
    if state and isinstance(state, dict):
        default_language = str(state.get("voice_language", default_language))

    for i, transcript_data in enumerate(transcripts):
        # Additional null check for individual transcript data
        if transcript_data and isinstance(transcript_data, dict):
            script_text = str(transcript_data.get("script", "") or "")
            if script_text.strip():
                try:
                    # Determine language and voice
                    language = str(transcript_data.get("language") or default_language)
                    file_prefix = "chapter" if is_pdf else "slide"

                    # Get appropriate voice for the language
                    voices = audio_generator.get_supported_voices(language)
                    voice = voices[0] if voices else None

                    # Generate audio
                    audio_path = audio_dir / f"{file_prefix}_{i + 1}.mp3"
                    await audio_generator.generate_audio(
                        script_text, str(audio_path), language=language, voice=voice
                    )

                    # Keep audio files local - only final files should be uploaded to cloud storage
                    audio_files.append(str(audio_path))
                    logger.info(
                        f"Generated audio for {file_prefix} {i + 1}: {audio_path}"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to generate audio for {file_prefix} {i + 1}: {e}"
                    )
                    raise
            else:
                logger.warning(
                    f"Skipping audio generation for {file_prefix} {i + 1} due to "
                    f"missing or empty transcript data"
                )

    await state_manager.update_step_status(file_id, state_key, "completed", audio_files)
    logger.info(
        f"Audio generation completed successfully with {len(audio_files)} files"
    )


async def get_pdf_transcripts(file_id: str) -> list[dict[str, Any]]:
    """Get transcripts for PDF processing."""
    state = await state_manager.get_state(file_id)
    chapters: list[dict[str, Any]] = []

    # Priority 1: use translated voice transcripts if present (ensures correct audio language)
    if (
        state
        and "steps" in state
        and "translate_voice_transcripts" in state["steps"]
        and "data" in state["steps"]["translate_voice_transcripts"]
        and state["steps"]["translate_voice_transcripts"]["data"]
    ):
        chapters = state["steps"]["translate_voice_transcripts"]["data"]
        logger.info("Using translated voice transcripts for PDF audio generation")
    # Priority 2: use revised English transcripts
    elif (
        state
        and "steps" in state
        and "revise_pdf_transcripts" in state["steps"]
        and "data" in state["steps"]["revise_pdf_transcripts"]
        and state["steps"]["revise_pdf_transcripts"]["data"]
    ):
        chapters = state["steps"]["revise_pdf_transcripts"]["data"]
        logger.info("Using revised transcripts for PDF audio generation")
    # Fallback: original chapters with English transcripts
    elif (
        state
        and "steps" in state
        and "segment_pdf_content" in state["steps"]
        and "data" in state["steps"]["segment_pdf_content"]
        and state["steps"]["segment_pdf_content"]["data"]
    ):
        # Fallback to original English transcripts
        chapters = state["steps"]["segment_pdf_content"]["data"]
        logger.info("Using original English transcripts for PDF audio generation")

    return chapters


async def get_slide_transcripts(file_id: str) -> list[dict[str, Any]]:
    """Get transcripts for slide processing."""
    state = await state_manager.get_state(file_id)
    transcripts = []

    # Check for translated voice transcripts first (for non-English audio)
    if (
        state
        and "steps" in state
        and "translate_voice_transcripts" in state["steps"]
        and "data" in state["steps"]["translate_voice_transcripts"]
        and state["steps"]["translate_voice_transcripts"]["data"]
    ):
        # Use translated voice transcripts if available (for non-English audio)
        transcripts = state["steps"]["translate_voice_transcripts"]["data"]
        logger.info("Using translated voice transcripts for audio generation")
    # Fallback to revised English transcripts
    elif (
        state
        and "steps" in state
        and "revise_transcripts" in state["steps"]
        and "data" in state["steps"]["revise_transcripts"]
        and state["steps"]["revise_transcripts"]["data"]
    ):
        # Use revised transcripts if available (better quality)
        transcripts = state["steps"]["revise_transcripts"]["data"]
        logger.info("Using revised English transcripts for audio generation")

    return transcripts
