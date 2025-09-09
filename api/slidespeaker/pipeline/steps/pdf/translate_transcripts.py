"""PDF transcript translation step for SlideSpeaker.

This module handles the translation of PDF chapter transcripts for both voice and subtitle generation.
"""

from typing import Any

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.services.translation_service import TranslationService

translation_service = TranslationService()


async def translate_subtitle_transcripts_step(
    file_id: str, target_language: str = "english"
) -> None:
    """
    Translate PDF chapter transcripts for subtitle generation.

    Args:
        file_id: Unique identifier for the file
        target_language: Target language for translation
    """
    await state_manager.update_step_status(
        file_id, "translate_subtitle_transcripts", "processing"
    )
    logger.info(
        f"Translating PDF chapter transcripts for subtitle generation for file: {file_id}"
    )

    try:
        # Translate transcripts using the shared translation utility
        translated_transcripts = await _translate_transcripts(
            file_id, target_language, use_revised_scripts=True
        )

        # Store translated transcripts in state
        await state_manager.update_step_status(
            file_id,
            "translate_subtitle_transcripts",
            "completed",
            translated_transcripts,
        )

        logger.info(
            f"Translated subtitle transcripts for {len(translated_transcripts)} chapters for file: {file_id}"
        )

    except Exception as e:
        logger.error(
            f"Failed to translate PDF subtitle transcripts for file {file_id}: {e}"
        )
        # Mark step as failed
        await state_manager.update_step_status(
            file_id, "translate_subtitle_transcripts", "failed", {"error": str(e)}
        )
        raise


async def translate_voice_transcripts_step(
    file_id: str, target_language: str = "english"
) -> None:
    """
    Translate PDF chapter transcripts for voice generation.

    Args:
        file_id: Unique identifier for the file
        target_language: Target language for translation
    """
    await state_manager.update_step_status(
        file_id, "translate_voice_transcripts", "processing"
    )
    logger.info(
        f"Translating PDF chapter transcripts for voice generation for file: {file_id}"
    )

    try:
        # Translate transcripts using the shared translation utility
        translated_transcripts = await _translate_transcripts(
            file_id, target_language, use_revised_scripts=True
        )

        # Update state with translated transcripts in the expected format
        await state_manager.update_step_status(
            file_id, "translate_voice_transcripts", "completed", translated_transcripts
        )

        logger.info(
            f"Translated transcripts for {len(translated_transcripts)} chapters for file: {file_id}"
        )

    except Exception as e:
        logger.error(
            f"Failed to translate PDF voice transcripts for file {file_id}: {e}"
        )
        # Mark step as failed
        await state_manager.update_step_status(
            file_id, "translate_voice_transcripts", "failed", {"error": str(e)}
        )
        raise


async def _translate_transcripts(
    file_id: str,
    target_language: str,
    source_language: str = "english",
    use_revised_scripts: bool = True,
) -> list[dict[str, Any]]:
    """
    Translate PDF chapter transcripts.

    Args:
        file_id: Unique identifier for the file
        target_language: Target language for translation
        source_language: Source language of transcripts (default: english)

    Returns:
        List of translated transcript dictionaries
    """
    # Get chapters for transcript translation
    chapters = await _get_scripts_for_translation(file_id, use_revised_scripts)

    # Convert chapters to the format expected by translation service
    transcripts_to_translate = []
    for i, chapter in enumerate(chapters):
        transcripts_to_translate.append(
            {"slide_number": str(i + 1), "script": chapter.get("script", "")}
        )

    logger.debug(
        f"Prepared {len(transcripts_to_translate)} transcripts for translation"
    )

    # Translate transcripts using the translation service
    translated_scripts = await translation_service.translate_scripts(
        transcripts_to_translate, source_language, target_language
    )

    logger.info(
        f"Translated transcripts for {len(translated_scripts)} chapters for file: {file_id}"
    )

    return translated_scripts


async def _get_scripts_for_translation(
    file_id: str, use_revised_scripts: bool = True
) -> list[dict[str, Any]]:
    """
    Get PDF chapter scripts for translation from state.

    Args:
        file_id: Unique identifier for the file
        use_revised_scripts: Whether to prioritize revised scripts over original segmented content

    Returns:
        List of chapter/script dictionaries with slide_number and script content
    """
    # Get current state to retrieve chapters
    state = await state_manager.get_state(file_id)
    if not state:
        raise ValueError(f"No state found for file {file_id}")

    chapters = []

    # If use_revised_scripts is True, try to get revised scripts first
    if use_revised_scripts:
        revised_scripts_data = (
            state.get("steps", {}).get("revise_pdf_transcripts", {}).get("data")
        )
        logger.debug(
            f"Revised scripts data type: {type(revised_scripts_data)}, "
            f"length: {len(revised_scripts_data) if isinstance(revised_scripts_data, list) else 'N/A'}"
        )

        # If we have revised scripts, use them
        if (
            revised_scripts_data
            and isinstance(revised_scripts_data, list)
            and len(revised_scripts_data) > 0
        ):
            chapters = revised_scripts_data
            logger.info("Using revised transcripts for translation")

    # If no revised scripts or not using revised scripts, fall back to original segmented content
    if not chapters:
        # Get chapters from the segment_pdf_content step data
        segment_content_data = (
            state.get("steps", {}).get("segment_pdf_content", {}).get("data")
        )
        logger.debug(
            f"Segment content data type: {type(segment_content_data)}, value: {segment_content_data}"
        )

        if segment_content_data is None:
            # Check if the segment step actually completed
            segment_step_status = (
                state.get("steps", {})
                .get("segment_pdf_content", {})
                .get("status", "unknown")
            )
            logger.error(f"Segment PDF content step status: {segment_step_status}")
            raise ValueError(
                f"No chapter data found for file {file_id} - segment_pdf_content step status: {segment_step_status}"
            )

        # Extract chapters from the data
        if isinstance(segment_content_data, list):
            chapters = segment_content_data
        else:
            # Handle case where data might be a dict or other structure
            chapters = (
                segment_content_data if isinstance(segment_content_data, list) else []
            )

    return chapters
