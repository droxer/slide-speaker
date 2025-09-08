"""Presentation voice script translation step for SlideSpeaker.

This module handles the translation of presentation slide scripts for voice generation.
"""

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.services.translation_service import TranslationService

translation_service = TranslationService()


async def translate_voice_scripts_step(
    file_id: str, target_language: str = "english"
) -> None:
    """
    Translate presentation slide scripts for voice generation.

    Args:
        file_id: Unique identifier for the file
        target_language: Target language for translation
    """
    await state_manager.update_step_status(
        file_id, "translate_voice_scripts", "processing"
    )
    logger.info(
        f"Translating presentation slide scripts for voice generation for file: {file_id}"
    )

    try:
        # Get current state to retrieve scripts
        state = await state_manager.get_state(file_id)
        if not state:
            raise ValueError(f"No state found for file {file_id}")

        # Get scripts from the review_scripts step data (priority) or generate_scripts step
        reviewed_scripts_data = (
            state.get("steps", {}).get("review_scripts", {}).get("data")
        )

        if (
            reviewed_scripts_data
            and isinstance(reviewed_scripts_data, list)
            and len(reviewed_scripts_data) > 0
        ):
            scripts = reviewed_scripts_data
            logger.info("Using reviewed scripts for voice translation")
        else:
            # Fall back to generated scripts
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

        # Store translated scripts in state in the expected format
        await state_manager.update_step_status(
            file_id, "translate_voice_scripts", "completed", translated_scripts
        )

        logger.info(
            f"Translated voice scripts for {len(translated_scripts)} slides for file: {file_id}"
        )

    except Exception as e:
        logger.error(
            f"Failed to translate presentation voice scripts for file {file_id}: {e}"
        )
        # Mark step as failed
        await state_manager.update_step_status(
            file_id, "translate_voice_scripts", "failed", {"error": str(e)}
        )
        raise
