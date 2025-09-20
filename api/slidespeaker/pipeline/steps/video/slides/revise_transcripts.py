"""
Revise transcripts step for the presentation pipeline.

This module refines generated transcripts for each slide, improving flow,
clarity, and structure for delivery.
"""

from slidespeaker.pipeline.steps.common.transcript_reviser import (
    get_slide_transcripts_for_revision,
    revise_transcripts_common,
)


async def revise_transcripts_step(
    file_id: str, language: str = "english", task_id: str | None = None
) -> None:
    await revise_transcripts_common(
        file_id=file_id,
        language=language,
        get_transcripts_func=get_slide_transcripts_for_revision,
        state_key="revise_transcripts",
        task_id=task_id,
    )


__all__ = ["revise_transcripts_step"]
