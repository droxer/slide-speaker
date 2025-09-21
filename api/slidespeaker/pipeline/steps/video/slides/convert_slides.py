"""
Convert slides to images step for the presentation pipeline.

This module handles the conversion of presentation slides to image files.
It takes the extracted slide content and generates PNG images for each slide
that can be used in subsequent processing steps like visual analysis and video composition.
"""

from pathlib import Path

from loguru import logger

from slidespeaker.configs.config import config, get_storage_provider
from slidespeaker.core.state_manager import state_manager
from slidespeaker.document import SlideExtractor

slide_processor = SlideExtractor()

# Get storage provider instance
storage_provider = get_storage_provider()


async def convert_slides_step(file_id: str, file_path: Path, file_ext: str) -> None:
    """
    Convert slides to images for visual processing.

    This function converts each slide from the presentation file into a PNG image.
    These images are used for visual analysis and as backgrounds in the final video.
    The function includes periodic cancellation checks to allow for task interruption.
    """
    await state_manager.update_step_status(
        file_id, "convert_slides_to_images", "processing"
    )
    slide_images = []
    state = await state_manager.get_state(file_id)

    # Check for task cancellation before starting
    if state and state.get("task_id"):
        from slidespeaker.core.task_queue import task_queue

        if await task_queue.is_task_cancelled(state["task_id"]):
            logger.debug(
                f"Task {state['task_id']} was cancelled during slide conversion"
            )
            await state_manager.mark_cancelled(
                file_id, cancelled_step="convert_slides_to_images"
            )
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

    # Prepare intermediate images directory: output/{file_id}/images
    images_dir = config.output_dir / file_id / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    for i in range(len(slides)):
        # Check for task cancellation periodically
        if i % 5 == 0 and state and state.get("task_id"):  # Check every 5 slides
            from slidespeaker.core.task_queue import task_queue

            if await task_queue.is_task_cancelled(state["task_id"]):
                logger.debug(
                    f"Task {state['task_id']} was cancelled during slide conversion"
                )
                await state_manager.mark_cancelled(
                    file_id, cancelled_step="convert_slides_to_images"
                )
                return

        image_path = images_dir / f"slide_{i + 1}.png"
        await slide_processor.convert_to_image(Path(file_path), file_ext, i, image_path)

        # Keep slide images local - only final files should be uploaded to cloud storage
        slide_images.append(str(image_path))
        logger.debug(f"Converted slide {i + 1}: {image_path}")

    await state_manager.update_step_status(
        file_id, "convert_slides_to_images", "completed", slide_images
    )


__all__ = ["convert_slides_step"]
