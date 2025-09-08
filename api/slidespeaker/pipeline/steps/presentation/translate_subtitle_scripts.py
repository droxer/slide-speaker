"""Presentation subtitle script translation step for SlideSpeaker.

This module handles the translation of presentation slide scripts for subtitle generation.
"""

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.services.translation_service import TranslationService

translation_service = TranslationService()


async def translate_subtitle_scripts_step(
    file_id: str, target_language: str = "english"
) -> None:
    """
    Translate presentation slide scripts for subtitle generation.

    Args:
        file_id: Unique identifier for the file
        target_language: Target language for translation
    """
    await state_manager.update_step_status(
        file_id, "translate_subtitle_scripts", "processing"
    )
    logger.info(
        f"Translating presentation slide scripts for subtitle generation for file: {file_id}"
    )

    try:
        # Get current state to retrieve scripts
        state = await state_manager.get_state(file_id)
        if not state:
            raise ValueError(f"No state found for file {file_id}")

        # Check for reviewed scripts first (priority)
        reviewed_scripts_data = (
            state.get("steps", {}).get("review_scripts", {}).get("data")
        )

        # If no reviewed scripts, fall back to generated scripts
        if (
            reviewed_scripts_data
            and isinstance(reviewed_scripts_data, list)
            and len(reviewed_scripts_data) > 0
        ):
            scripts = reviewed_scripts_data
            logger.info("Using reviewed scripts for subtitle translation")
        else:
            # Get scripts from the generate_scripts step data
            generated_scripts_data = (
                state.get("steps", {}).get("generate_scripts", {}).get("data")
            )
            if not generated_scripts_data:
                raise ValueError(f"No script data found for file {file_id}")

            # Extract scripts from the data
            if isinstance(generated_scripts_data, list):
                scripts = generated_scripts_data
            else:
                scripts = (
                    generated_scripts_data
                    if isinstance(generated_scripts_data, list)
                    else []
                )

        if not scripts:
            raise ValueError(f"No scripts found for file {file_id}")

        # Convert scripts to the format expected by translation service
        scripts_to_translate = []
        for i, script_data in enumerate(scripts):
            scripts_to_translate.append(
                {"slide_number": str(i + 1), "script": script_data.get("script", "")}
            )

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
            f"Translated subtitle scripts for {len(translated_scripts)} slides for file: {file_id}"
        )

    except Exception as e:
        logger.error(
            f"Failed to translate presentation subtitle scripts for file {file_id}: {e}"
        )
        # Mark step as failed
        await state_manager.update_step_status(
            file_id, "translate_subtitle_scripts", "failed", {"error": str(e)}
        )
        raise
