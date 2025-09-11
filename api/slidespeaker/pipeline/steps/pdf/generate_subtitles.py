"""
PDF subtitle generation step for SlideSpeaker.

This module handles the generation of subtitles for PDF chapters using transcripts.
"""

from slidespeaker.pipeline.steps.common.subtitle_generator import (
    generate_subtitles_common,
    get_pdf_audio_files,
    get_pdf_subtitles_transcripts,
)


async def generate_subtitles_step(file_id: str, language: str = "english") -> None:
    """
    Generate subtitles for PDF chapters using transcripts.

    Args:
        file_id: Unique identifier for the file
        language: Language for subtitle generation
    """
    await generate_subtitles_common(
        file_id=file_id,
        language=language,
        get_transcripts_func=get_pdf_subtitles_transcripts,
        get_audio_files_func=get_pdf_audio_files,
        state_key="generate_pdf_subtitles",
        is_pdf=True,
    )
