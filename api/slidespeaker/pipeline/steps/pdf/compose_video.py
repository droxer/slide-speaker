"""
PDF video composition step for SlideSpeaker.

This module handles the composition of the final video from PDF chapters.
"""

from slidespeaker.pipeline.steps.common.video_composer import (
    compose_video,
    get_pdf_audio_files,
    get_pdf_slide_images,
    get_pdf_subtitle_files,
)


async def compose_video_step(file_id: str) -> None:
    """
    Compose the final video from PDF chapters.

    Args:
        file_id: Unique identifier for the file
    """
    await compose_video(
        file_id=file_id,
        get_audio_files_func=get_pdf_audio_files,
        get_subtitle_files_func=get_pdf_subtitle_files,
        get_slide_images_func=get_pdf_slide_images,
        state_key="compose_video",
        is_pdf=True,
    )
