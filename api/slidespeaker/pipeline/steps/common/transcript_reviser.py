"""
Shared transcript revision logic for SlideSpeaker pipeline steps.

This module provides common functionality for revising transcripts
in both PDF and presentation slide processing pipelines.
"""

from collections.abc import Callable
from typing import Any

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.transcript import TranscriptReviewer


async def revise_transcripts_common(
    file_id: str,
    state_key: str,
    get_transcripts_func: Callable[[str], Any],
    language: str = "english",
) -> None:
    """
    Revise transcripts using shared logic.

    Args:
        file_id: Unique identifier for the file
        state_key: State key to update (e.g., "revise_transcripts" or "revise_pdf_transcripts")
        get_transcripts_func: Function to retrieve transcripts data
        language: Target language for revision

    Raises:
        ValueError: If no transcripts data is available
    """
    await state_manager.update_step_status(file_id, state_key, "processing")
    logger.info(f"Starting transcript revision for file: {file_id}")

    # Get transcripts data
    original_transcripts = await get_transcripts_func(file_id)

    if not original_transcripts:
        logger.warning("No transcripts data available for revision")
        await state_manager.update_step_status(file_id, state_key, "completed", [])
        return

    try:
        # Use shared transcript reviewer
        reviewer = TranscriptReviewer()
        revised_transcripts = await reviewer.revise_transcripts(
            original_transcripts, language
        )

        await state_manager.update_step_status(
            file_id, state_key, "completed", revised_transcripts
        )
        logger.info(
            f"Transcript revision completed successfully with {len(revised_transcripts)} transcripts"
        )
    except Exception as e:
        logger.error(f"Failed to revise transcripts: {e}")
        await state_manager.update_step_status(
            file_id, state_key, "failed", {"error": str(e)}
        )
        raise


async def get_pdf_transcripts_for_revision(file_id: str) -> list[dict[str, Any]]:
    """Get transcripts for PDF revision."""
    state = await state_manager.get_state(file_id)
    chapters: list[dict[str, Any]] = []

    # Use generated PDF chapters for revision
    if (
        state
        and "steps" in state
        and "segment_pdf_content" in state["steps"]
        and "data" in state["steps"]["segment_pdf_content"]
        and state["steps"]["segment_pdf_content"]["data"] is not None
    ):
        chapters = state["steps"]["segment_pdf_content"]["data"]
        logger.info("Using generated PDF chapters for revision")

    return chapters


async def get_slide_transcripts_for_revision(file_id: str) -> list[dict[str, Any]]:
    """Get transcripts for slide revision."""
    state = await state_manager.get_state(file_id)
    transcripts: list[dict[str, Any]] = []

    # Use generated slide transcripts for revision
    if (
        state
        and "steps" in state
        and "generate_transcripts" in state["steps"]
        and "data" in state["steps"]["generate_transcripts"]
        and state["steps"]["generate_transcripts"]["data"] is not None
    ):
        transcripts = state["steps"]["generate_transcripts"]["data"]
        logger.info("Using generated slide transcripts for revision")

    return transcripts
