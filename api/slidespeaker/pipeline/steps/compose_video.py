"""
Compose final video step for the presentation pipeline.
"""

import os
from pathlib import Path
from typing import Any
from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.processing.video_composer import VideoComposer
from slidespeaker.processing.video_previewer import VideoPreviewer
from slidespeaker.processing.subtitle_generator import SubtitleGenerator
from slidespeaker.utils.config import config

video_composer = VideoComposer()
subtitle_generator = SubtitleGenerator()
video_previewer = VideoPreviewer()


async def compose_video_step(file_id: str, file_path: Path) -> None:
    """Compose the final video from all components"""
    await state_manager.update_step_status(file_id, "compose_video", "processing")
    logger.info(f"Starting final video composition for file: {file_id}")
    state = await state_manager.get_state(file_id)

    # Check for task cancellation before starting
    if state and state.get("task_id"):
        from slidespeaker.core.task_queue import task_queue

        if await task_queue.is_task_cancelled(state["task_id"]):
            logger.info(
                f"Task {state['task_id']} was cancelled during video composition"
            )
            await state_manager.mark_failed(file_id)
            return

    # Comprehensive null checking for all required data
    slide_images_data = []
    avatar_videos_data = []
    audio_files_data = []
    scripts_data: list[dict[str, Any]] = []

    if (
        state
        and "steps" in state
        and "convert_slides_to_images" in state["steps"]
        and state["steps"]["convert_slides_to_images"]["data"] is not None
    ):
        slide_images_data = state["steps"]["convert_slides_to_images"]["data"]

    if (
        state
        and "steps" in state
        and "generate_avatar_videos" in state["steps"]
        and state["steps"]["generate_avatar_videos"]["data"] is not None
    ):
        avatar_videos_data = state["steps"]["generate_avatar_videos"]["data"]

    if (
        state
        and "steps" in state
        and "generate_audio" in state["steps"]
        and state["steps"]["generate_audio"]["data"] is not None
    ):
        audio_files_data = state["steps"]["generate_audio"]["data"]

    # Get scripts for subtitle generation
    # Use subtitle-specific scripts if they exist (when languages differ)
    if state and "steps" in state:
        # Check if subtitle scripts exist (languages are different)
        if (
            "review_subtitle_scripts" in state["steps"]
            and state["steps"]["review_subtitle_scripts"]["data"] is not None
        ):
            scripts_data = state["steps"]["review_subtitle_scripts"]["data"]
            logger.info("Using subtitle-specific scripts for subtitle generation")
        # Fall back to regular scripts if subtitle scripts don't exist
        elif (
            "review_scripts" in state["steps"]
            and state["steps"]["review_scripts"]["data"] is not None
        ):
            scripts_data = state["steps"]["review_scripts"]["data"]
            logger.info("Using regular scripts for subtitle generation")

    # Get subtitle language and generation flag from state
    subtitle_language = None
    generate_subtitles = True
    if state and "subtitle_language" in state:
        subtitle_language = state["subtitle_language"]  # Preserve user selection
    # Default to audio language if subtitle language not specified
    if subtitle_language is None and state and "audio_language" in state:
        subtitle_language = state["audio_language"]
    if state and "generate_subtitles" in state:
        generate_subtitles = state["generate_subtitles"]

    logger.info(
        f"Subtitle settings - Language: {subtitle_language}, "
        f"Generate: {generate_subtitles}"
    )

    # Validate all required data exists
    if not slide_images_data:
        raise ValueError("No slide images data available for video composition")
    # Audio files are optional - we can create a video without them

    slide_images = [Path(p) for p in slide_images_data]
    audio_files = [Path(p) for p in audio_files_data]

    # Use absolute path to ensure consistency with main.py
    final_video_path = config.output_dir / f"{file_id}_final.mp4"

    # Generate subtitles before composing video (if enabled)
    if scripts_data and generate_subtitles:
        try:
            logger.info(
                f"Generating subtitles for {len(scripts_data)} scripts in "
                f"language: {subtitle_language}"
            )
            logger.info(f"Final video path: {final_video_path}")

            # Check for task cancellation during subtitle generation
            if state and state.get("task_id"):
                from slidespeaker.core.task_queue import task_queue

                if await task_queue.is_task_cancelled(state["task_id"]):
                    logger.info(
                        f"Task {state['task_id']} was cancelled during "
                        f"subtitle generation"
                    )
                    await state_manager.mark_failed(file_id)
                    return

            # If we have no audio files, we need to provide estimated durations
            if not audio_files_data:
                logger.info(
                    "No audio files available, using estimated durations for subtitles"
                )
                # Create a list of dummy paths for estimated durations (5 seconds each)
                estimated_audio_files = [
                    Path(f"/tmp/dummy_audio_{i}.mp3") for i in range(len(scripts_data))
                ]
                srt_path, vtt_path = subtitle_generator.generate_subtitles(
                    scripts_data,
                    estimated_audio_files,
                    final_video_path,
                    str(subtitle_language) if subtitle_language else "english",
                )
            else:
                srt_path, vtt_path = subtitle_generator.generate_subtitles(
                    scripts_data,
                    audio_files,
                    final_video_path,
                    str(subtitle_language) if subtitle_language else "english"
                )
            logger.info(f"Generated subtitles: {srt_path}, {vtt_path}")

            # Verify files were created
            if os.path.exists(srt_path):
                srt_size = os.path.getsize(srt_path)
                logger.info(
                    f"SRT file created successfully: {srt_path}, size: {srt_size} bytes"
                )
                # Log first few lines for debugging
                try:
                    with open(srt_path, encoding="utf-8") as f:
                        first_lines = f.read(500)
                        logger.info(f"SRT file first 500 chars: {first_lines}")
                except Exception as e:
                    logger.error(f"Error reading SRT file: {e}")
            else:
                logger.error(f"SRT file not found: {srt_path}")

            if os.path.exists(vtt_path):
                vtt_size = os.path.getsize(vtt_path)
                logger.info(
                    f"VTT file created successfully: {vtt_path}, size: {vtt_size} bytes"
                )
                # Log first few lines for debugging
                try:
                    with open(vtt_path, encoding="utf-8") as f:
                        first_lines = f.read(500)
                        logger.info(f"VTT file first 500 chars: {first_lines}")
                except Exception as e:
                    logger.error(f"Error reading VTT file: {e}")
            else:
                logger.error(f"VTT file not found: {vtt_path}")
        except Exception as e:
            logger.error(f"Failed to generate subtitles: {e}")
            import traceback
            logger.error(f"Subtitle generation traceback: {traceback.format_exc()}")
            # If subtitles generation fails, we should raise an exception
            # to prevent continuing with the video composition
            raise Exception(f"Failed to generate subtitles: {e}") from e

    # Check if avatar generation was enabled and completed
    avatar_generation_enabled = True
    if state and "generate_avatar" in state:
        avatar_generation_enabled = state["generate_avatar"]

    # Use avatar videos if available and enabled, otherwise create simple video
    if avatar_videos_data and avatar_generation_enabled:
        logger.info("Avatar videos found, creating full presentation with avatars")
        avatar_videos = [Path(p) for p in avatar_videos_data]
        # Check for task cancellation before video composition
        if state and state.get("task_id"):
            from slidespeaker.core.task_queue import task_queue

            if await task_queue.is_task_cancelled(state["task_id"]):
                logger.info(
                    f"Task {state['task_id']} was cancelled during "
                    f"avatar video composition"
                )
                await state_manager.mark_failed(file_id)
                return
        await video_composer.compose_video(
            slide_images, avatar_videos, audio_files, final_video_path
        )
    else:
        if avatar_generation_enabled:
            logger.warning(
                "No avatar videos available, creating simple "
                "presentation without avatars"
            )
        else:
            logger.info(
                "Avatar generation disabled, creating simple presentation without avatars"
            )

        # Check for task cancellation before video composition
        if state and state.get("task_id"):
            from slidespeaker.core.task_queue import task_queue

            if await task_queue.is_task_cancelled(state["task_id"]):
                logger.info(
                    f"Task {state['task_id']} was cancelled during simple video composition"
                )
                await state_manager.mark_failed(file_id)
                return

        # Create video based on whether we have audio files or not
        if audio_files_data:
            await video_composer.create_simple_video(
                slide_images, audio_files, final_video_path
            )
        else:
            logger.info("No audio files available, creating images-only video")
            await video_composer.create_images_only_video(
                slide_images, final_video_path
            )

    await state_manager.update_step_status(
        file_id, "compose_video", "completed", str(final_video_path)
    )
    logger.info("Stage 'Composing final presentation' completed successfully")
    await state_manager.mark_completed(file_id)

    # Generate preview data
    try:
        preview_data = video_previewer.generate_preview_data(
            file_id, config.output_dir, str(subtitle_language) if subtitle_language else "english"
        )
        logger.info(f"Generated preview data: {preview_data}")
    except Exception as e:
        logger.error(f"Failed to generate preview data: {e}")

    # Cleanup temporary files
    temp_files = audio_files + slide_images
    if avatar_videos_data:
        avatar_videos = [Path(p) for p in avatar_videos_data]
        temp_files += avatar_videos

    for temp_file in temp_files:
        if Path(temp_file).exists():
            Path(temp_file).unlink()

    if Path(file_path).exists():
        Path(file_path).unlink()