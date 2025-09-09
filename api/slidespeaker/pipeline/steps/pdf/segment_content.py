"""
PDF content segmentation step for SlideSpeaker.

This module handles the segmentation of PDF content into chapters.
"""

from pathlib import Path

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.processing.pdf_analyzer import PDFAnalyzer


async def segment_content_step(
    file_id: str, file_path: Path, language: str = "english"
) -> None:
    """
    Segment PDF content into chapters.

    Args:
        file_id: Unique identifier for the file
        file_path: Path to the PDF file
        language: Language for content analysis
    """
    await state_manager.update_step_status(file_id, "segment_pdf_content", "processing")
    logger.info(f"Segmenting PDF content into chapters for file: {file_id}")

    try:
        # Create PDF analyzer
        analyzer = PDFAnalyzer()

        # Analyze and segment PDF content
        chapters = await analyzer.analyze_and_segment(str(file_path), language)

        # Log chapter data for debugging
        logger.debug(f"Generated {len(chapters)} chapters for file {file_id}")
        if chapters:
            logger.debug(
                f"First chapter keys: {chapters[0].keys() if hasattr(chapters[0], 'keys') else type(chapters[0])}"
            )
            logger.debug(f"First chapter sample: {str(chapters[0])[:200]}...")

        # Store chapters in state
        await state_manager.update_step_status(
            file_id, "segment_pdf_content", "completed", chapters
        )
        logger.info(f"Segmented PDF into {len(chapters)} chapters for file: {file_id}")

    except Exception as e:
        logger.error(f"Failed to segment PDF content for file {file_id}: {e}")
        logger.error(f"File path: {file_path}, exists: {file_path.exists()}")
        raise
