"""
PDF transcript translation step for SlideSpeaker.

This module handles the translation of PDF chapter transcripts for both voice and subtitle generation.
"""

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.pipeline.steps.common.transcript_translator import (
    get_pdf_subtitle_transcripts,
    get_pdf_voice_transcripts,
    translate_transcripts_common,
)


async def translate_voice_transcripts_step(
    file_id: str, source_language: str = "english", target_language: str = "english"
) -> None:
    """
    Translate PDF chapter transcripts for voice generation.

    This function translates the revised PDF chapter transcripts to the target language
    for voice generation. It ensures the translated content maintains proper flow
    and is suitable for AI avatar presentation.
    """
    if source_language.lower() == target_language.lower():
        logger.info(
            f"Source and target languages are the same ({target_language}), skipping translation"
        )
        # Just copy the source data to the target state key
        state = await state_manager.get_state(file_id)
        if state and "steps" in state:
            source_data = None
            # Try to get revised transcripts first
            if (
                "revise_pdf_transcripts" in state["steps"]
                and state["steps"]["revise_pdf_transcripts"].get("status")
                == "completed"
                and state["steps"]["revise_pdf_transcripts"].get("data") is not None
            ):
                source_data = state["steps"]["revise_pdf_transcripts"]["data"]
            # Fall back to original segmented content
            elif (
                "segment_pdf_content" in state["steps"]
                and state["steps"]["segment_pdf_content"].get("data") is not None
            ):
                source_data = state["steps"]["segment_pdf_content"]["data"]

            if source_data:
                await state_manager.update_step_status(
                    file_id, "translate_voice_transcripts", "completed", source_data
                )
                logger.info(
                    "Copied source transcripts to translation step (no translation needed)"
                )
                return

        await state_manager.update_step_status(
            file_id, "translate_voice_transcripts", "completed", []
        )
        return

    await translate_transcripts_common(
        file_id=file_id,
        source_language=source_language,
        target_language=target_language,
        get_source_transcripts_func=get_pdf_voice_transcripts,
        state_key="translate_voice_transcripts",
    )


async def translate_subtitle_transcripts_step(
    file_id: str, source_language: str = "english", target_language: str = "english"
) -> None:
    """
    Translate PDF chapter transcripts for subtitle generation.

    This function translates the PDF chapter transcripts to the target language
    for subtitle generation. It ensures the translated content is properly timed
    and formatted for subtitle display.
    """
    if source_language.lower() == target_language.lower():
        logger.info(
            f"Source and target languages are the same ({target_language}), skipping subtitle translation"
        )
        # Just copy the source data to the target state key
        state = await state_manager.get_state(file_id)
        if state and "steps" in state:
            source_data = None
            # Try to get revised transcripts first
            if (
                "revise_pdf_transcripts" in state["steps"]
                and state["steps"]["revise_pdf_transcripts"].get("status")
                == "completed"
                and state["steps"]["revise_pdf_transcripts"].get("data") is not None
            ):
                source_data = state["steps"]["revise_pdf_transcripts"]["data"]
            # Fall back to original segmented content
            elif (
                "segment_pdf_content" in state["steps"]
                and state["steps"]["segment_pdf_content"].get("data") is not None
            ):
                source_data = state["steps"]["segment_pdf_content"]["data"]

            if source_data:
                await state_manager.update_step_status(
                    file_id, "translate_subtitle_transcripts", "completed", source_data
                )
                logger.info(
                    "Copied source transcripts to subtitle translation step (no translation needed)"
                )
                return

        await state_manager.update_step_status(
            file_id, "translate_subtitle_transcripts", "completed", []
        )
        return

    await translate_transcripts_common(
        file_id=file_id,
        source_language=source_language,
        target_language=target_language,
        get_source_transcripts_func=get_pdf_subtitle_transcripts,
        state_key="translate_subtitle_transcripts",
    )


async def translate_transcripts_step(
    file_id: str, source_language: str = "english", target_language: str = "english"
) -> None:
    """
    Translate PDF chapter transcripts for both voice and subtitle generation.

    This function translates the PDF chapter transcripts to the target language
    for both voice generation and subtitle generation.
    """
    # Translate for voice generation
    await translate_voice_transcripts_step(file_id, source_language, target_language)

    # Translate for subtitle generation
    await translate_subtitle_transcripts_step(file_id, source_language, target_language)


__all__ = [
    "translate_subtitle_transcripts_step",
    "translate_voice_transcripts_step",
]
