"""
PDF content analysis step for SlideSpeaker.

This module handles additional analysis of PDF content using the PDFAnalyzer.
"""

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.processing.pdf_analyzer import PDFAnalyzer


async def analyze_content_step(file_id: str, language: str = "english") -> None:
    """
    Perform additional analysis on PDF content and enhance chapters.

    Args:
        file_id: Unique identifier for the file
        language: Language for content analysis
    """
    await state_manager.update_step_status(file_id, "analyze_pdf_content", "processing")
    logger.info(f"Analyzing PDF content for file: {file_id}")

    try:
        # Create PDF analyzer
        analyzer = PDFAnalyzer()

        # Get chapters from state (segmented in previous step)
        state = await state_manager.get_state(file_id)
        chapters = []
        if (
            state
            and "steps" in state
            and "segment_pdf_content" in state["steps"]
            and state["steps"]["segment_pdf_content"]["data"] is not None
        ):
            chapters = state["steps"]["segment_pdf_content"]["data"]

        if not chapters:
            raise ValueError("No chapter data available for analysis")

        # Perform additional analysis on the chapters using PDFAnalyzer
        analysis_results = await analyzer.analyze_chapters(chapters, language)
        logger.info(f"Analyzed {len(chapters)} chapters for file: {file_id}")

        # Enhance chapters with analysis results
        enhanced_chapters = []
        for i, chapter in enumerate(chapters):
            enhanced_chapter = chapter.copy()
            # Add analysis data to each chapter
            if "chapters" in analysis_results and i < len(analysis_results["chapters"]):
                chapter_analysis = analysis_results["chapters"][i]
                enhanced_chapter["analysis"] = chapter_analysis
            enhanced_chapters.append(enhanced_chapter)

        # Update the segment_pdf_content step with enhanced chapters
        await state_manager.update_step_status(
            file_id, "segment_pdf_content", "completed", enhanced_chapters
        )

        # Mark analysis step as completed with analysis results
        await state_manager.update_step_status(
            file_id, "analyze_pdf_content", "completed", analysis_results
        )
        logger.info(
            f"PDF content analysis and enhancement completed for file: {file_id}"
        )

    except Exception as e:
        logger.error(f"Failed to analyze PDF content for file {file_id}: {e}")
        raise
