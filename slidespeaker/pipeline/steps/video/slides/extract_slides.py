"""
Extract slides step for the presentation pipeline.

This module handles the extraction of content from presentation files (PDF, PPTX, PPT).
It parses the presentation file and extracts text content from each slide for further processing.
"""

from pathlib import Path

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.document import SlideExtractor

slide_processor = SlideExtractor()


async def extract_slides_step(file_id: str, file_path: Path, file_ext: str) -> None:
    """
    Extract slides from the presentation file.

    This function parses the presentation file (PDF, PPTX, or PPT) and extracts
    text content from each slide. The extracted content is stored in the processing state
    for use in subsequent pipeline steps.
    """
    await state_manager.update_step_status(file_id, "extract_slides", "processing")
    logger.debug(f"Extracting slides for file: {file_id}")
    slides = await slide_processor.extract_slides(file_path, file_ext)
    logger.debug(f"Extracted {len(slides)} slides for file: {file_id}")
    await state_manager.update_step_status(
        file_id, "extract_slides", "completed", slides
    )
    logger.debug(
        f"Stage 'Extracting presentation content' completed "
        f"successfully with {len(slides)} slides"
    )

    # Verify state was updated
    updated_state = await state_manager.get_state(file_id)
    if (
        updated_state
        and updated_state["steps"]["extract_slides"]["status"] == "completed"
    ):
        logger.debug(f"Successfully updated extract_slides to completed for {file_id}")
    else:
        logger.error(f"Failed to update extract_slides state for {file_id}")


__all__ = ["extract_slides_step"]
