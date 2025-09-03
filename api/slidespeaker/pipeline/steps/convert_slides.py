"""
Convert slides to images step for the presentation pipeline.
"""

from pathlib import Path

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.processing.slide_extractor import SlideExtractor
from slidespeaker.utils.config import config

slide_processor = SlideExtractor()


async def convert_slides_step(file_id: str, file_path: Path, file_ext: str) -> None:
    """Convert slides to images"""
    await state_manager.update_step_status(
        file_id, "convert_slides_to_images", "processing"
    )
    slide_images = []
    state = await state_manager.get_state(file_id)

    # Check for task cancellation before starting
    if state and state.get("task_id"):
        from slidespeaker.core.task_queue import task_queue

        if await task_queue.is_task_cancelled(state["task_id"]):
            logger.info(
                f"Task {state['task_id']} was cancelled during slide conversion"
            )
            await state_manager.mark_failed(file_id)
            return

    # Safely get slides data with comprehensive null checking
    slides = []
    if (
        state
        and "steps" in state
        and "extract_slides" in state["steps"]
        and state["steps"]["extract_slides"]["data"] is not None
    ):
        slides = state["steps"]["extract_slides"]["data"]

    if not slides:
        raise ValueError("No slides data available for conversion to images")

    for i in range(len(slides)):
        # Check for task cancellation periodically
        if i % 5 == 0 and state and state.get("task_id"):  # Check every 5 slides
            from slidespeaker.core.task_queue import task_queue

            if await task_queue.is_task_cancelled(state["task_id"]):
                logger.info(
                    f"Task {state['task_id']} was cancelled during slide conversion"
                )
                await state_manager.mark_failed(file_id)
                return

        image_path = config.output_dir / f"{file_id}_slide_{i + 1}.png"
        await slide_processor.convert_to_image(Path(file_path), file_ext, i, image_path)
        slide_images.append(str(image_path))

    await state_manager.update_step_status(
        file_id, "convert_slides_to_images", "completed", slide_images
    )
