"""PDF subtitle script translation step for SlideSpeaker.

This module handles the translation of PDF chapter scripts for subtitle generation.
"""

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.services.translation_service import TranslationService

translation_service = TranslationService()


async def translate_subtitle_scripts_step(
    file_id: str, target_language: str = "english"
) -> None:
    """
    Translate PDF chapter scripts for subtitle generation.

    Args:
        file_id: Unique identifier for the file
        target_language: Target language for translation
    """
    await state_manager.update_step_status(
        file_id, "translate_subtitle_scripts", "processing"
    )
    logger.info(
        f"Translating PDF chapter scripts for subtitle generation for file: {file_id}"
    )

    try:
        # Get current state to retrieve chapters
        state = await state_manager.get_state(file_id)
        if not state:
            raise ValueError(f"No state found for file {file_id}")

        # Log the state structure for debugging
        logger.debug(
            f"State structure for file {file_id}: {list(state.keys()) if state else 'None'}"
        )
        if state and "steps" in state:
            logger.debug(f"Available steps: {list(state['steps'].keys())}")

        # Check for reviewed scripts first (priority)
        reviewed_scripts_data = (
            state.get("steps", {}).get("review_pdf_scripts", {}).get("data")
        )
        logger.debug(
            f"Reviewed scripts data type: {type(reviewed_scripts_data)}, "
            f"length: {len(reviewed_scripts_data) if isinstance(reviewed_scripts_data, list) else 'N/A'}"
        )

        # If no reviewed scripts, fall back to original segmented content
        if (
            reviewed_scripts_data
            and isinstance(reviewed_scripts_data, list)
            and len(reviewed_scripts_data) > 0
        ):
            chapters = reviewed_scripts_data
            logger.info("Using reviewed scripts for subtitle translation")
        else:
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
                    segment_content_data
                    if isinstance(segment_content_data, list)
                    else []
                )

        if not chapters:
            raise ValueError(
                f"No chapters found for file {file_id} - chapters data is empty"
            )

        logger.info(f"Found {len(chapters)} chapters for translation")

        # Convert chapters to the format expected by translation service
        scripts_to_translate = []
        for i, chapter in enumerate(chapters):
            # Log chapter structure for debugging
            logger.debug(
                f"Chapter {i + 1} structure: {chapter.keys() if hasattr(chapter, 'keys') else type(chapter)}"
            )
            scripts_to_translate.append(
                {"slide_number": str(i + 1), "script": chapter.get("script", "")}
            )

        logger.debug(f"Prepared {len(scripts_to_translate)} scripts for translation")

        # Source language is always English for translation steps
        source_language = "english"

        # Translate scripts using the translation service
        translated_scripts = await translation_service.translate_scripts(
            scripts_to_translate, source_language, target_language
        )

        # Store translated scripts in state
        await state_manager.update_step_status(
            file_id, "translate_subtitle_scripts", "completed", translated_scripts
        )

        logger.info(
            f"Translated subtitle scripts for {len(translated_scripts)} chapters for file: {file_id}"
        )

    except Exception as e:
        logger.error(
            f"Failed to translate PDF subtitle scripts for file {file_id}: {e}"
        )
        # Mark step as failed
        await state_manager.update_step_status(
            file_id, "translate_subtitle_scripts", "failed", {"error": str(e)}
        )
        raise
