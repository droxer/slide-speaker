"""
PDF transcript revise step for SlideSpeaker.

This module handles the revise and refinement of PDF chapter transcripts for consistency,
flow, and quality. It ensures appropriate formatting for AI avatar delivery with smooth transitions.
"""

from slidespeaker.pipeline.steps.common.transcript_reviser import (
    get_pdf_transcripts_for_revision,
    revise_transcripts_common,
)


async def revise_transcripts_step(file_id: str, language: str = "english") -> None:
    """
    Revise and refine PDF chapter transcripts for consistency and smooth flow.

    This function improves the flow and consistency of generated PDF chapter transcripts,
    ensuring they are appropriately formatted for AI avatar delivery with smooth transitions
    between chapters. It handles proper positioning of opening/closing statements.
    """
    await revise_transcripts_common(
        file_id=file_id,
        language=language,
        get_transcripts_func=get_pdf_transcripts_for_revision,
        state_key="revise_pdf_transcripts",
    )
