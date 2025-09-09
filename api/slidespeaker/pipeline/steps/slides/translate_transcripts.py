"""Presentation transcript translation step for SlideSpeaker.

This module handles the translation of presentation slide transcripts for both voice and subtitle generation.
"""

from typing import Any

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.services.translation_service import TranslationService

translation_service = TranslationService()


async def translate_voice_transcripts_step(
    file_id: str, target_language: str = "english"
) -> None:
    """
    Translate presentation slide transcripts for voice generation.

    Args:
        file_id: Unique identifier for the file
        target_language: Target language for translation
    """
    await state_manager.update_step_status(
        file_id, "translate_voice_transcripts", "processing"
    )
    logger.info(
        f"Translating presentation slide transcripts for voice generation for file: {file_id}"
    )

    try:
        # Translate transcripts using the shared translation utility
        translated_transcripts = await _translate_transcripts(
            file_id, target_language, use_revised_scripts=True
        )

        # Store translated transcripts in state in the expected format
        await state_manager.update_step_status(
            file_id, "translate_voice_transcripts", "completed", translated_transcripts
        )

        logger.info(
            f"Translated voice transcripts for {len(translated_transcripts)} slides for file: {file_id}"
        )

    except Exception as e:
        logger.error(
            f"Failed to translate presentation voice transcripts for file {file_id}: {e}"
        )
        # Mark step as failed
        await state_manager.update_step_status(
            file_id, "translate_voice_transcripts", "failed", {"error": str(e)}
        )
        raise


async def translate_subtitle_transcripts_step(
    file_id: str, target_language: str = "english"
) -> None:
    """
    Translate presentation slide transcripts for subtitle generation.

    Args:
        file_id: Unique identifier for the file
        target_language: Target language for translation
    """
    await state_manager.update_step_status(
        file_id, "translate_subtitle_transcripts", "processing"
    )
    logger.info(
        f"Translating presentation slide transcripts for subtitle generation for file: {file_id}"
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
            f"Translated subtitle transcripts for {len(translated_transcripts)} slides for file: {file_id}"
        )

    except Exception as e:
        logger.error(
            f"Failed to translate presentation subtitle transcripts for file {file_id}: {e}"
        )
        # Mark step as failed
        await state_manager.update_step_status(
            file_id, "translate_subtitle_transcripts", "failed", {"error": str(e)}
        )
        raise


async def _get_scripts_for_translation(
    file_id: str, use_revised_scripts: bool = True
) -> list[dict[str, Any]]:
    """
    Get presentation slide scripts for translation from state.

    Args:
        file_id: Unique identifier for the file
        use_revised_scripts: Whether to prioritize revised scripts over generated scripts

    Returns:
        List of script dictionaries with slide_number and script content
    """
    # Get current state to retrieve scripts
    state = await state_manager.get_state(file_id)
    if not state:
        raise ValueError(f"No state found for file {file_id}")

    scripts = []

    # If use_revised_scripts is True, try to get revised scripts first
    if use_revised_scripts:
        revised_scripts_data = (
            state.get("steps", {}).get("revise_transcripts", {}).get("data")
        )

        # If we have revised scripts, use them
        if (
            revised_scripts_data
            and isinstance(revised_scripts_data, list)
            and len(revised_scripts_data) > 0
        ):
            scripts = revised_scripts_data
            logger.info("Using revised transcripts for translation")

    # If no revised scripts or not using revised scripts, fall back to generated scripts
    if not scripts:
        # Get scripts from the generate_transcripts step data
        generated_scripts_data = (
            state.get("steps", {}).get("generate_transcripts", {}).get("data")
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

    return scripts


async def _translate_transcripts(
    file_id: str,
    target_language: str,
    source_language: str = "english",
    use_revised_scripts: bool = True,
) -> list[dict[str, Any]]:
    """
    Translate presentation slide transcripts.

    Args:
        file_id: Unique identifier for the file
        target_language: Target language for translation
        source_language: Source language of transcripts (default: english)

    Returns:
        List of translated transcript dictionaries
    """
    # Get transcripts for translation
    scripts = await _get_scripts_for_translation(file_id, use_revised_scripts)

    # Convert transcripts to the format expected by translation service
    transcripts_to_translate = []
    for i, script_data in enumerate(scripts):
        transcripts_to_translate.append(
            {"slide_number": str(i + 1), "script": script_data.get("script", "")}
        )

    # Translate transcripts using the translation service
    translated_scripts = await translation_service.translate_scripts(
        transcripts_to_translate, source_language, target_language
    )

    logger.info(
        f"Translated transcripts for {len(translated_scripts)} slides for file: {file_id}"
    )

    return translated_scripts
