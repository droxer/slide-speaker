"""
Generate audio step for the presentation pipeline.

This module generates text-to-speech audio files from the reviewed transcripts.
It uses configurable TTS services (OpenAI, ElevenLabs) to create natural-sounding
voice audio for each slide in the presentation.
"""

from slidespeaker.pipeline.steps.common.audio_generator import (
    generate_audio_common,
    get_slide_transcripts,
)


async def generate_audio_step(file_id: str, language: str = "english") -> None:
    """
    Generate audio from transcripts using TTS services.

    This function converts the reviewed presentation transcripts into audio files
    using text-to-speech technology. It supports multiple TTS providers through
    a factory pattern and includes error handling for individual slide processing.
    The function includes periodic cancellation checks for responsive task management.
    """
    await generate_audio_common(
        file_id=file_id,
        get_transcripts_func=get_slide_transcripts,
        state_key="generate_audio",
        is_pdf=False,
    )


__all__ = ["generate_audio_step"]
