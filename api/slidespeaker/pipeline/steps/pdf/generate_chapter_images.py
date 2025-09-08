"""
PDF chapter image generation step for SlideSpeaker.

This module handles the generation of slide-like images for PDF chapters.
"""

from pathlib import Path
from typing import Any

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.processing.image_generator import (
    ImageGenerator as SharedImageGenerator,
)
from slidespeaker.utils.config import get_storage_provider

image_generator = SharedImageGenerator()

# Get storage provider instance
storage_provider = get_storage_provider()


async def generate_chapter_images_step(file_id: str, language: str = "english") -> None:
    """
    Generate slide-like images for PDF chapters.

    Args:
        file_id: Unique identifier for the file
        language: Language for image generation
    """
    await state_manager.update_step_status(
        file_id, "generate_pdf_chapter_images", "processing"
    )
    logger.info(f"Generating slide-like images for PDF chapters for file: {file_id}")

    try:
        # Get chapters from state
        state = await state_manager.get_state(file_id)
        chapters: list[dict[str, Any]] = []
        if (
            state
            and "steps" in state
            and "segment_pdf_content" in state["steps"]
            and state["steps"]["segment_pdf_content"]["data"] is not None
        ):
            chapters = state["steps"]["segment_pdf_content"]["data"]

        logger.info(
            f"Retrieved {len(chapters)} chapters from state for file: {file_id}"
        )

        if not chapters:
            raise ValueError("No chapter data available for image generation")

        # Create working directory
        work_dir = Path("output") / file_id
        images_dir = work_dir / "images"
        images_dir.mkdir(exist_ok=True, parents=True)
        logger.info(f"Created images directory: {images_dir}")

        # Generate chapter images
        logger.info(f"Starting image generation for {len(chapters)} chapters")
        image_paths = await image_generator.generate_chapter_images(
            chapters, images_dir, language
        )
        logger.info(f"Generated {len(image_paths)} chapter images")

        # For PDF processing, we only need local paths for subsequent steps
        # Final outputs (video and subtitles) will be uploaded to storage
        storage_data = {
            "local_paths": [str(path) for path in image_paths],
            "storage_urls": [],  # No storage URLs for intermediate images in PDF processing
        }

        await state_manager.update_step_status(
            file_id, "generate_pdf_chapter_images", "completed", storage_data
        )

        logger.info(f"Generated {len(image_paths)} chapter images for file: {file_id}")

    except Exception as e:
        logger.error(f"Failed to generate PDF chapter images for file {file_id}: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        raise
