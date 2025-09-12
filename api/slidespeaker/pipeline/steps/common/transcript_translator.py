"""
Shared transcript translation logic for SlideSpeaker pipeline steps.

This module provides common functionality for translating transcripts
in both PDF and presentation slide processing pipelines.
"""

from collections.abc import Callable
from typing import Any

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.services import TranslationService


async def translate_transcripts_common(
    file_id: str,
    state_key: str,
    get_source_transcripts_func: Callable[[str], Any],
    source_language: str,
    target_language: str,
) -> None:
    """
    Translate transcripts using shared logic.

    Args:
        file_id: Unique identifier for the file
        state_key: State key to update (e.g., "translate_voice_transcripts" or "translate_subtitle_transcripts")
        get_source_transcripts_func: Function to retrieve source transcripts data
        source_language: Source language of the transcripts
        target_language: Target language for translation

    Raises:
        ValueError: If no source transcripts are available
    """
    # Early return if no translation is needed
    if source_language.lower() == target_language.lower():
        logger.info("Source and target languages are the same, skipping translation")
        state = await state_manager.get_state(file_id)
        source_data = []

        # Copy source data to translation step
        if state and "steps" in state:
            if (
                "revise_pdf_transcripts" in state["steps"]
                and "data" in state["steps"]["revise_pdf_transcripts"]
                and state["steps"]["revise_pdf_transcripts"]["data"] is not None
            ):
                source_data = state["steps"]["revise_pdf_transcripts"]["data"]
            elif (
                "segment_pdf_content" in state["steps"]
                and "data" in state["steps"]["segment_pdf_content"]
                and state["steps"]["segment_pdf_content"]["data"] is not None
            ):
                source_data = state["steps"]["segment_pdf_content"]["data"]

            if source_data:
                await state_manager.update_step_status(
                    file_id, state_key, "completed", source_data
                )
                logger.info(
                    "Copied source transcripts to translation step (no translation needed)"
                )
                return

        await state_manager.update_step_status(file_id, state_key, "completed", [])
        return

    await state_manager.update_step_status(file_id, state_key, "processing")
    logger.info(f"Starting transcript translation for file: {file_id}")

    # Get source transcripts
    source_transcripts = await get_source_transcripts_func(file_id)

    if not source_transcripts:
        logger.warning("No source transcripts available for translation")
        await state_manager.update_step_status(file_id, state_key, "completed", [])
        return

    try:
        # Use shared translation service
        translator = TranslationService()
        # Ensure a provider is available if translation is required
        if source_language.lower() != target_language.lower():
            if (
                translator.provider == "openai"
                and getattr(translator, "client", None) is None
            ):
                msg = "Translation service not configured (missing OPENAI_API_KEY)."
                logger.error(msg)
                await state_manager.update_step_status(
                    file_id, state_key, "failed", {"error": msg}
                )
                return
            if translator.provider == "qwen" and not getattr(
                translator, "qwen_api_key", None
            ):
                msg = "Translation service not configured (missing QWEN_API_KEY)."
                logger.error(msg)
                await state_manager.update_step_status(
                    file_id, state_key, "failed", {"error": msg}
                )
                return
        translated_transcripts = translator.translate(
            source_transcripts, source_language, target_language
        )

        await state_manager.update_step_status(
            file_id, state_key, "completed", translated_transcripts
        )
        logger.info(
            f"Transcript translation completed successfully with {len(translated_transcripts)} transcripts"
        )
    except Exception as e:
        logger.error(f"Failed to translate transcripts: {e}")
        await state_manager.update_step_status(
            file_id, state_key, "failed", {"error": str(e)}
        )
        raise


async def get_pdf_voice_transcripts(file_id: str) -> list[dict[str, Any]]:
    """Get PDF transcripts for voice translation."""
    state = await state_manager.get_state(file_id)

    # Use revised PDF transcripts if available, otherwise fall back to original
    if (
        state
        and "steps" in state
        and "revise_pdf_transcripts" in state["steps"]
        and "data" in state["steps"]["revise_pdf_transcripts"]
        and state["steps"]["revise_pdf_transcripts"]["data"] is not None
    ):
        data = state["steps"]["revise_pdf_transcripts"]["data"]
        return data if data is not None else []
    elif (
        state
        and "steps" in state
        and "segment_pdf_content" in state["steps"]
        and "data" in state["steps"]["segment_pdf_content"]
        and state["steps"]["segment_pdf_content"]["data"] is not None
    ):
        data = state["steps"]["segment_pdf_content"]["data"]
        return data if data is not None else []

    return []


async def get_pdf_subtitle_transcripts(file_id: str) -> list[dict[str, Any]]:
    """Get PDF transcripts for subtitle translation."""
    # For PDF, we can use the same source as voice translation
    return await get_pdf_voice_transcripts(file_id)


async def get_slide_voice_transcripts(file_id: str) -> list[dict[str, Any]]:
    """Get slide transcripts for voice translation."""
    state = await state_manager.get_state(file_id)

    # Use revised slide transcripts if available, otherwise fall back to original
    if (
        state
        and "steps" in state
        and "revise_transcripts" in state["steps"]
        and "data" in state["steps"]["revise_transcripts"]
        and state["steps"]["revise_transcripts"]["data"] is not None
    ):
        data = state["steps"]["revise_transcripts"]["data"]
        return data if data is not None else []
    elif (
        state
        and "steps" in state
        and "generate_transcripts" in state["steps"]
        and "data" in state["steps"]["generate_transcripts"]
        and state["steps"]["generate_transcripts"]["data"] is not None
    ):
        data = state["steps"]["generate_transcripts"]["data"]
        return data if data is not None else []

    return []


async def get_slide_subtitle_transcripts(file_id: str) -> list[dict[str, Any]]:
    """Get slide transcripts for subtitle translation."""
    # For slides, we can use the same source as voice translation
    return await get_slide_voice_transcripts(file_id)
