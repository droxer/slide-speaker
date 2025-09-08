"""
PDF script review step for SlideSpeaker.

This module handles the review and refinement of PDF chapter scripts for consistency,
flow, and quality. It ensures that the presentation has a coherent narrative
and that scripts are appropriately formatted for AI avatar delivery with smooth transitions.
"""

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.processing.script_reviewer import ScriptReviewer

script_reviewer = ScriptReviewer()


async def review_scripts_step(file_id: str, language: str = "english") -> None:
    """
    Review and refine PDF chapter scripts for consistency and smooth flow.

    This function uses AI language models to review and improve the generated scripts.
    It ensures consistent tone, proper transitions between chapters, and appropriate
    formatting for AI avatar delivery. The review process also handles
    positioning of opening/closing statements correctly for smooth transitions.

    Args:
        file_id: Unique identifier for the file
        language: Language for script review
    """
    await state_manager.update_step_status(file_id, "review_pdf_scripts", "processing")
    logger.info(f"Reviewing PDF chapter scripts for file: {file_id}")

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

        # Convert chapters to the format expected by script reviewer
        scripts_to_review = []
        for i, chapter in enumerate(chapters):
            scripts_to_review.append(
                {"slide_number": str(i + 1), "script": chapter.get("script", "")}
            )

        # Review scripts using the shared script reviewer for smooth transitions
        reviewed_scripts = await script_reviewer.revise_scripts(
            scripts_to_review, language
        )

        # Update chapters with reviewed scripts
        updated_chapters = []
        for i, chapter in enumerate(chapters):
            updated_chapter = chapter.copy()
            if i < len(reviewed_scripts):
                updated_chapter["script"] = reviewed_scripts[i].get(
                    "script", chapter.get("script", "")
                )
            updated_chapters.append(updated_chapter)

        # Store reviewed chapters in the review_pdf_scripts step
        await state_manager.update_step_status(
            file_id, "review_pdf_scripts", "completed", updated_chapters
        )

        logger.info(
            f"Reviewed scripts for {len(updated_chapters)} chapters for file: {file_id} with smooth transitions"
        )

    except Exception as e:
        logger.error(f"Failed to review PDF scripts for file {file_id}: {e}")
        # Mark step as failed
        await state_manager.update_step_status(
            file_id, "review_pdf_scripts", "failed", {"error": str(e)}
        )
        raise
