"""
Revise transcripts step for the presentation pipeline.

This module revises and refines the generated transcripts for consistency,
flow, and quality. It ensures appropriate formatting for AI avatar delivery.
"""

from slidespeaker.pipeline.steps.common.transcript_reviser import (
    get_slide_transcripts_for_revision,
    revise_transcripts_common,
)


async def revise_transcripts_step(
    file_id: str, language: str = "english", is_subtitle: bool = False
) -> None:
    """
    Revise and refine presentation transcripts for consistency and smooth flow.

    This function improves the flow and consistency of generated presentation transcripts,
    ensuring they are appropriately formatted for AI avatar delivery. It handles
    proper positioning of opening/closing statements and smooth transitions between slides.
    """
    await revise_transcripts_common(
        file_id=file_id,
        language=language,
        get_transcripts_func=get_slide_transcripts_for_revision,
        state_key="revise_transcripts",
    )
