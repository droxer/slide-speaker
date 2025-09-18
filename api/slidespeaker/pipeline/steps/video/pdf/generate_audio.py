"""
PDF audio generation step for SlideSpeaker.

This module handles the generation of audio for PDF chapters using transcripts.
"""

from slidespeaker.pipeline.steps.common.audio_generator import (
    generate_audio_common,
    get_pdf_transcripts,
)


async def generate_audio_step(file_id: str, language: str = "english") -> None:
    """
    Generate audio for PDF chapters using transcripts.

    Args:
        file_id: Unique identifier for the file
        language: Language for audio generation
    """
    await generate_audio_common(
        file_id=file_id,
        get_transcripts_func=get_pdf_transcripts,
        state_key="generate_pdf_audio",
        is_pdf=True,
    )


__all__ = ["generate_audio_step"]
