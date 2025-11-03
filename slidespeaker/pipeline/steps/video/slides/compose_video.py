"""
Compose final video step for the presentation pipeline.

This module composes the final presentation video by combining slide images,
audio files, avatar videos, and subtitles. It handles both full-featured
presentations with avatars and simpler image+audio presentations.
"""

from pathlib import Path

from slidespeaker.pipeline.steps.common.video_composer import (
    compose_video,
    get_slide_audio_files,
    get_slide_images,
    get_slide_subtitle_files,
)


async def compose_video_step(file_id: str, file_path: Path) -> None:
    """
    Compose the final presentation video from slide components.

    This function combines slide images, audio files, avatar videos (if available),
    and subtitle files into a single MP4 video file. It handles proper synchronization
    of all elements and applies appropriate transitions between slides.
    """
    await compose_video(
        file_id=file_id,
        get_audio_files_func=get_slide_audio_files,
        get_subtitle_files_func=get_slide_subtitle_files,
        get_slide_images_func=get_slide_images,
        state_key="compose_video",
        is_pdf=False,
    )


__all__ = ["compose_video_step"]
