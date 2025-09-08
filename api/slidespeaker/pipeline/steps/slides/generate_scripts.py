"""
Generate scripts step for the presentation pipeline.

This module generates AI-powered presentation scripts for each slide.
It uses the extracted slide content and visual analysis to create
natural, engaging scripts suitable for AI avatar presentation.
"""

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.processing.script_generator import ScriptGenerator

script_generator = ScriptGenerator()


async def generate_scripts_step(
    file_id: str, language: str = "english", is_subtitle: bool = False
) -> None:
    """
    Generate scripts for each slide using AI language models.

    This function creates presentation scripts for each slide using OpenAI's GPT models.
    It combines the extracted slide text content with visual analysis to generate
    engaging, natural-sounding scripts that are suitable for AI avatar presentation.
    The function includes periodic cancellation checks for responsive task management.
    """
    step_name = "generate_subtitle_scripts" if is_subtitle else "generate_scripts"
    await state_manager.update_step_status(file_id, step_name, "processing")
    state = await state_manager.get_state(file_id)

    # Comprehensive null checking for slides data
    slides = []
    if (
        state
        and "steps" in state
        and "extract_slides" in state["steps"]
        and state["steps"]["extract_slides"]["data"] is not None
    ):
        slides = state["steps"]["extract_slides"]["data"]

    # Get image analyses if available
    image_analyses = []
    if (
        state
        and "steps" in state
        and "analyze_slide_images" in state["steps"]
        and state["steps"]["analyze_slide_images"]["data"] is not None
    ):
        image_analyses = state["steps"]["analyze_slide_images"]["data"]

    if not slides:
        raise ValueError("No slides data available for script generation")

    scripts = []
    for i, slide_content in enumerate(slides):
        # Check for task cancellation periodically
        if i % 3 == 0 and state and state.get("task_id"):  # Check every 3 slides
            from slidespeaker.core.task_queue import task_queue

            if await task_queue.is_task_cancelled(state["task_id"]):
                logger.info(
                    f"Task {state['task_id']} was cancelled during script generation"
                )
                await state_manager.mark_cancelled(file_id, cancelled_step=step_name)
                return

        # Get image analysis for this slide if available
        image_analysis = None
        if image_analyses and i < len(image_analyses):
            image_analysis = (
                image_analyses[i].get("analysis") if image_analyses[i] else None
            )

        script = await script_generator.generate_script(
            slide_content, image_analysis, language
        )
        scripts.append({"slide_number": i + 1, "script": script})

    await state_manager.update_step_status(file_id, step_name, "completed", scripts)
