"""
Revise transcripts step for the presentation pipeline.

This module revises and refines the generated transcripts for consistency,
flow, and quality. It ensures that the presentation has a coherent narrative
and that transcripts are appropriately formatted for AI avatar delivery.
"""

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.processing.transcript_reviewer import TranscriptReviewer

transcript_reviewer = TranscriptReviewer()


async def revise_transcripts_step(
    file_id: str, language: str = "english", is_subtitle: bool = False
) -> None:
    """
    Revise and refine all generated transcripts for consistency and smooth flow.

    This function uses AI language models to revise and improve the generated transcripts.
    It ensures consistent tone, proper transitions between slides, and appropriate
    formatting for AI avatar presentation. The revise process also handles
    positioning of opening/closing statements correctly.
    """
    step_name = "revise_subtitle_transcripts" if is_subtitle else "revise_transcripts"
    step_display_name = (
        "Revising subtitle transcripts"
        if is_subtitle
        else "Revising and refining transcripts"
    )
    await state_manager.update_step_status(file_id, step_name, "processing")
    logger.info(f"Starting {step_display_name} for file: {file_id}")
    state = await state_manager.get_state(file_id)

    # Check for task cancellation before starting
    if state and state.get("task_id"):
        from slidespeaker.core.task_queue import task_queue

        if await task_queue.is_task_cancelled(state["task_id"]):
            logger.info(
                f"Task {state['task_id']} was cancelled during transcript revise"
            )
            await state_manager.mark_cancelled(file_id, cancelled_step=step_name)
            return

    # Get generated transcripts from the appropriate step
    source_step = (
        "generate_subtitle_transcripts" if is_subtitle else "generate_transcripts"
    )
    transcripts = []
    if (
        state
        and "steps" in state
        and source_step in state["steps"]
        and state["steps"][source_step]["data"] is not None
    ):
        transcripts = state["steps"][source_step]["data"]

    if not transcripts:
        raise ValueError("No transcripts data available for revise")

    # Revise and refine transcripts for consistency
    revised_transcripts = await transcript_reviewer.revise_transcripts(
        transcripts, language
    )

    await state_manager.update_step_status(
        file_id, step_name, "completed", revised_transcripts
    )
    logger.info(
        f"Stage '{step_display_name}' completed successfully "
        f"with {len(revised_transcripts)} transcripts"
    )
