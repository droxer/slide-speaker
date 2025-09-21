"""
Generate subtitles step for the presentation pipeline.

This module generates subtitle files (SRT and VTT formats) from the transcripts.
It creates timed subtitles that can be used with the final presentation video,
supporting multiple languages and automatic timing based on audio durations.
"""

from slidespeaker.pipeline.steps.common.subtitle_generator import (
    generate_subtitles_common,
    get_slide_audio_files,
    get_slide_subtitles_transcripts,
)


async def generate_subtitles_step(file_id: str, language: str = "english") -> None:
    """
    Generate subtitles from transcripts in SRT and VTT formats.

    This function creates timed subtitle files for the presentation video.
    It uses either subtitle-specific transcripts (when audio and subtitle languages differ)
    or regular transcripts, and synchronizes subtitles with audio durations when available.
    The function supports multiple languages and generates both SRT and VTT formats.
    """
    await generate_subtitles_common(
        file_id=file_id,
        language=language,
        get_transcripts_func=get_slide_subtitles_transcripts,
        get_audio_files_func=get_slide_audio_files,
        state_key="generate_subtitles",
        is_pdf=False,
    )


__all__ = ["generate_subtitles_step"]
