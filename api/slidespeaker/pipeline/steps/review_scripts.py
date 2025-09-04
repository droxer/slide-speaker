"""
Review scripts step for the presentation pipeline.
"""

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.processing.script_reviewer import ScriptReviewer

script_reviewer = ScriptReviewer()


async def review_scripts_step(
    file_id: str, language: str = "english", is_subtitle: bool = False
) -> None:
    """Review and refine all generated scripts for consistency and smooth flow"""
    step_name = "review_subtitle_scripts" if is_subtitle else "review_scripts"
    step_display_name = (
        "Reviewing subtitle scripts"
        if is_subtitle
        else "Reviewing and refining scripts"
    )
    await state_manager.update_step_status(file_id, step_name, "processing")
    logger.info(f"Starting {step_display_name} for file: {file_id}")
    state = await state_manager.get_state(file_id)

    # Check for task cancellation before starting
    if state and state.get("task_id"):
        from slidespeaker.core.task_queue import task_queue

        if await task_queue.is_task_cancelled(state["task_id"]):
            logger.info(f"Task {state['task_id']} was cancelled during script review")
            await state_manager.mark_failed(file_id)
            return

    # Get generated scripts from the appropriate step
    source_step = "generate_subtitle_scripts" if is_subtitle else "generate_scripts"
    scripts = []
    if (
        state
        and "steps" in state
        and source_step in state["steps"]
        and state["steps"][source_step]["data"] is not None
    ):
        scripts = state["steps"][source_step]["data"]

    if not scripts:
        raise ValueError("No scripts data available for review")

    # Review and refine scripts for consistency
    reviewed_scripts = await script_reviewer.revise_scripts(scripts, language)

    await state_manager.update_step_status(
        file_id, step_name, "completed", reviewed_scripts
    )
    logger.info(
        f"Stage '{step_display_name}' completed successfully "
        f"with {len(reviewed_scripts)} scripts"
    )
