"""PDF voice script translation step for SlideSpeaker.

This module handles the translation of PDF chapter scripts for voice generation.
"""

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.services.translation_service import TranslationService

translation_service = TranslationService()


async def translate_voice_scripts_step(
    file_id: str, target_language: str = "english"
) -> None:
    """
    Translate PDF chapter scripts for voice generation.

    Args:
        file_id: Unique identifier for the file
        target_language: Target language for translation
    """
    await state_manager.update_step_status(
        file_id, "translate_voice_scripts", "processing"
    )
    logger.info(
        f"Translating PDF chapter scripts for voice generation for file: {file_id}"
    )

    try:
        # Get current state to retrieve chapters
        state = await state_manager.get_state(file_id)
        if not state:
            raise ValueError(f"No state found for file {file_id}")

        # Get chapters from the segment_pdf_content step data
        segment_content_data = (
            state.get("steps", {}).get("segment_pdf_content", {}).get("data")
        )
        if not segment_content_data:
            raise ValueError(f"No chapter data found for file {file_id}")

        # Extract chapters from the data
        if isinstance(segment_content_data, list):
            chapters = segment_content_data
        else:
            chapters = (
                segment_content_data if isinstance(segment_content_data, list) else []
            )

        if not chapters:
            raise ValueError(f"No chapters found for file {file_id}")

        # Convert chapters to the format expected by translation service
        scripts_to_translate = []
        for i, chapter in enumerate(chapters):
            scripts_to_translate.append(
                {"slide_number": str(i + 1), "script": chapter.get("script", "")}
            )

        # Source language is always English for translation steps
        source_language = "english"

        # Translate scripts using the translation service
        translated_scripts = await translation_service.translate_scripts(
            scripts_to_translate, source_language, target_language
        )

        # Update state with translated scripts in the expected format
        await state_manager.update_step_status(
            file_id, "translate_voice_scripts", "completed", translated_scripts
        )

        logger.info(
            f"Translated scripts for {len(translated_scripts)} chapters for file: {file_id}"
        )

    except Exception as e:
        logger.error(f"Failed to translate PDF voice scripts for file {file_id}: {e}")
        # Mark step as failed
        await state_manager.update_step_status(
            file_id, "translate_voice_scripts", "failed", {"error": str(e)}
        )
        raise
