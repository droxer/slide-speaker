"""
Extract slides step for the presentation pipeline.
"""

from pathlib import Path
from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.processing.slide_extractor import SlideExtractor

slide_processor = SlideExtractor()


async def extract_slides_step(file_id: str, file_path: Path, file_ext: str) -> None:
    """Extract slides from the presentation file"""
    await state_manager.update_step_status(file_id, "extract_slides", "processing")
    logger.info(f"Extracting slides for file: {file_id}")
    slides = await slide_processor.extract_slides(file_path, file_ext)
    logger.info(f"Extracted {len(slides)} slides for file: {file_id}")
    await state_manager.update_step_status(
        file_id, "extract_slides", "completed", slides
    )
    logger.info(
        f"Stage 'Extracting presentation content' completed "
        f"successfully with {len(slides)} slides"
    )

    # Verify state was updated
    updated_state = await state_manager.get_state(file_id)
    if (
        updated_state
        and updated_state["steps"]["extract_slides"]["status"] == "completed"
    ):
        logger.info(f"Successfully updated extract_slides to completed for {file_id}")
    else:
        logger.error(f"Failed to update extract_slides state for {file_id}")