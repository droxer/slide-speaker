"""
PDF content segmentation step for SlideSpeaker.

This module handles the segmentation of PDF content into chapters.
"""

from pathlib import Path

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.document import PDFAnalyzer
from slidespeaker.transcript.markdown import transcripts_to_markdown


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

        # Log chapter data for debugging (reduce verbosity)
        logger.debug(f"Generated {len(chapters)} chapters for file {file_id}")
        if chapters and len(chapters) > 0:
            # Only log detailed info for first few chapters to reduce verbosity
            sample_size = min(3, len(chapters))
            logger.debug(f"Sample of first {sample_size} chapters for file {file_id}")

        # Store chapters in state
        await state_manager.update_step_status(
            file_id, "segment_pdf_content", "completed", chapters
        )
        # Persist Markdown view for segmented chapters
        try:
            state = await state_manager.get_state(file_id)
            if state and "steps" in state and "segment_pdf_content" in state["steps"]:
                md = transcripts_to_markdown(
                    chapters, section_label="Chapter", filename=state.get("filename")
                )
                state["steps"]["segment_pdf_content"]["markdown"] = md
                await state_manager.save_state(file_id, state)
        except Exception:
            pass
        logger.info(f"Segmented PDF into {len(chapters)} chapters for file: {file_id}")

    except Exception as e:
        logger.error(f"Failed to segment PDF content for file {file_id}: {e}")
        logger.error(f"File path: {file_path}, exists: {file_path.exists()}")
        raise


__all__ = ["segment_content_step"]
