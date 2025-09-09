"""
PDF transcript revise step for SlideSpeaker.

This module handles the revise and refinement of PDF chapter transcripts for consistency,
flow, and quality. It ensures that the presentation has a coherent narrative
and that transcripts are appropriately formatted for AI avatar delivery with smooth transitions.
"""

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.processing.transcript_reviewer import TranscriptReviewer

transcript_reviewer = TranscriptReviewer()


async def revise_transcripts_step(file_id: str, language: str = "english") -> None:
    """
    Revise and refine PDF chapter transcripts for consistency and smooth flow.

    This function uses AI language models to revise and improve the generated transcripts.
    It ensures consistent tone, proper transitions between chapters, and appropriate
    formatting for AI avatar delivery. The revise process also handles
    positioning of opening/closing statements correctly for smooth transitions.

    Args:
        file_id: Unique identifier for the file
        language: Language for transcript revise
    """
    await state_manager.update_step_status(
        file_id, "revise_pdf_transcripts", "processing"
    )
    logger.info(f"Revising PDF chapter transcripts for file: {file_id}")

    try:
        # Get current state to retrieve chapters
        state = await state_manager.get_state(file_id)
        if not state:
            raise ValueError(f"No state found for file {file_id}")

        # Get chapters from the segment_pdf_content step data (correct step for PDF)
        segment_content_data = (
            state.get("steps", {}).get("segment_pdf_content", {}).get("data")
        )
        if not segment_content_data:
            raise ValueError(f"No chapter data found for file {file_id}")

        # Extract chapters from the data
        if isinstance(segment_content_data, list):
            chapters = segment_content_data
        else:
            chapters = (
                segment_content_data if isinstance(segment_content_data, list) else []
            )

        if not chapters:
            raise ValueError(f"No chapters found for file {file_id}")

        # Convert chapters to the format expected by transcript reviewer
        transcripts_to_review = []
        for i, chapter in enumerate(chapters):
            transcripts_to_review.append(
                {"slide_number": str(i + 1), "script": chapter.get("script", "")}
            )

        # Revise transcripts using the shared transcript reviewer for smooth transitions
        revised_transcripts = await transcript_reviewer.revise_transcripts(
            transcripts_to_review, language
        )

        # Update chapters with revised transcripts
        updated_chapters = []
        for i, chapter in enumerate(chapters):
            updated_chapter = chapter.copy()
            if i < len(revised_transcripts):
                updated_chapter["script"] = revised_transcripts[i].get(
                    "script", chapter.get("script", "")
                )
            updated_chapters.append(updated_chapter)

        # Store revised chapters in the revise_pdf_transcripts step
        await state_manager.update_step_status(
            file_id, "revise_pdf_transcripts", "completed", updated_chapters
        )

        logger.info(
            f"Revised transcripts for {len(updated_chapters)} chapters for file: {file_id} with smooth transitions"
        )

    except Exception as e:
        logger.error(f"Failed to revise PDF transcripts for file {file_id}: {e}")
        # Mark step as failed
        await state_manager.update_step_status(
            file_id, "revise_pdf_transcripts", "failed", {"error": str(e)}
        )
        raise
