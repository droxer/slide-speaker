"""
Compose final video step for the presentation pipeline.

This module composes the final presentation video by combining slide images,
audio files, avatar videos, and subtitles. It handles both full-featured
presentations with avatars and simpler image+audio presentations.
"""

from pathlib import Path

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.processing.video_composer import VideoComposer
from slidespeaker.processing.video_previewer import VideoPreviewer
from slidespeaker.utils.config import config, get_storage_provider

video_composer = VideoComposer()
video_previewer = VideoPreviewer()

# Resolve storage provider during upload to honor current config


async def compose_video_step(file_id: str, file_path: Path) -> None:
    """
    Compose the final video from all presentation components.

    This function creates the final presentation video by combining slide images,
    audio files, avatar videos (if available), and subtitles. It supports both
    full-featured presentations with AI avatars and simpler image+audio presentations.
    The function includes comprehensive error handling and cleanup of temporary files.
    """
    await state_manager.update_step_status(file_id, "compose_video", "in_progress")
    logger.info(f"Starting final video composition for file: {file_id}")
    state = await state_manager.get_state(file_id)
    logger.info(
        f"Compose video step started - current step: {state.get('current_step', 'unknown') if state else 'no state'}"
    )

    # Check for task cancellation before starting
    if state and state.get("task_id"):
        from slidespeaker.core.task_queue import task_queue

        if await task_queue.is_task_cancelled(state["task_id"]):
            logger.info(
                f"Task {state['task_id']} was cancelled during video composition"
            )
            await state_manager.mark_cancelled(file_id, cancelled_step="compose_video")
            return

    # Comprehensive null checking for all required data
    slide_images_data = []
    avatar_videos_data = []
    audio_files_data = []

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

    # Get subtitle language from state for preview generation
    subtitle_language = None
    if state and "subtitle_language" in state:
        subtitle_language = state["subtitle_language"]  # Preserve user selection
    # Default to audio language if subtitle language not specified
    if subtitle_language is None and state and "audio_language" in state:
        subtitle_language = state["audio_language"]

    # Validate all required data exists
    if not slide_images_data:
        logger.error(f"No slide images data found for file {file_id}")
        logger.error(f"State data: {state}")
        raise ValueError("No slide images data available for video composition")

    logger.info(f"Found {len(slide_images_data)} slide images for composition")
    # Audio files are optional - we can create a video without them

    slide_images = [Path(p) for p in slide_images_data]
    audio_files = [Path(p) for p in audio_files_data]

    # Use absolute path to ensure consistency with main.py
    final_video_path = config.output_dir / f"{file_id}_final.mp4"

    # Check if avatar generation was enabled and completed
    avatar_generation_enabled = True
    if state and "generate_avatar" in state:
        avatar_generation_enabled = state["generate_avatar"]

    try:
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
                    await state_manager.mark_cancelled(
                        file_id, cancelled_step="compose_video"
                    )
                    return

            logger.info(
                f"Composing video with {len(slide_images)} slides, {len(avatar_videos)} avatars, "
                f"{len(audio_files)} audio files"
            )
            # Get video resolution from state
            video_resolution = state.get("video_resolution", "hd") if state else "hd"

            await video_composer.compose_video(
                slide_images,
                avatar_videos,
                audio_files,
                final_video_path,
                video_resolution,
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
                    await state_manager.mark_cancelled(
                        file_id, cancelled_step="compose_video"
                    )
                    return

            # Create video based on whether we have audio files or not
            if audio_files_data:
                # Filter out any invalid audio files
                valid_audio_files = []
                for audio_file in audio_files:
                    is_valid, error_msg = video_composer._validate_audio_file(
                        audio_file
                    )
                    if is_valid:
                        valid_audio_files.append(audio_file)
                    else:
                        logger.warning(f"Skipping invalid audio file: {error_msg}")

                if valid_audio_files:
                    logger.info(
                        f"Creating simple video with {len(slide_images)} slides and "
                        f"{len(valid_audio_files)} valid audio files"
                    )
                    # Get video resolution from state
                    video_resolution = (
                        state.get("video_resolution", "hd") if state else "hd"
                    )

                    await video_composer.create_video_with_audio(
                        slide_images,
                        valid_audio_files,
                        final_video_path,
                        video_resolution,
                    )
                else:
                    logger.warning(
                        "No valid audio files found, creating images-only video"
                    )
                    # Get video resolution from state
                    video_resolution = (
                        state.get("video_resolution", "hd") if state else "hd"
                    )

                    await video_composer.create_images_only_video(
                        slide_images, final_video_path, video_resolution
                    )
            else:
                logger.info(
                    f"Creating images-only video with {len(slide_images)} slides"
                )
                # Get video resolution from state
                video_resolution = (
                    state.get("video_resolution", "hd") if state else "hd"
                )

                await video_composer.create_images_only_video(
                    slide_images, final_video_path, video_resolution
                )
    except Exception as e:
        logger.error(f"Video composition failed: {e}")
        raise

    # Upload final video to storage provider
    try:
        object_key = f"{file_id}_final.mp4"
        storage_provider = get_storage_provider()
        storage_url = storage_provider.upload_file(
            str(final_video_path), object_key, "video/mp4"
        )
        logger.info(f"Uploaded final video to storage: {storage_url}")

        # Store the storage URL instead of local path
        await state_manager.update_step_status(
            file_id, "compose_video", "completed", storage_url
        )
    except Exception as e:
        logger.error(f"Failed to upload video to storage: {e}")
        # Fallback to local path if storage upload fails
        await state_manager.update_step_status(
            file_id, "compose_video", "completed", str(final_video_path)
        )

    logger.info("Stage 'Composing final presentation' completed successfully")
    await state_manager.mark_completed(file_id)

    # Generate preview data
    try:
        preview_data = video_previewer.generate_preview_data(
            file_id,
            str(subtitle_language) if subtitle_language else "english",
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
