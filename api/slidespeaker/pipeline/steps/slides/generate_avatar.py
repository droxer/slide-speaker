"""
Generate avatar videos step for the presentation pipeline.

This module generates AI avatar videos from the reviewed scripts.
It uses configurable avatar services (HeyGen, DALL-E) to create
animated avatar presentations for each slide in the presentation.
"""

from loguru import logger

from slidespeaker.configs.config import config, get_storage_provider
from slidespeaker.core.state_manager import state_manager
from slidespeaker.video.avatar import AvatarFactory

# Get storage provider instance
storage_provider = get_storage_provider()


async def generate_avatar_step(file_id: str) -> None:
    """
    Generate avatar videos from scripts using AI avatar services.

    This function creates AI avatar videos for each slide using the reviewed scripts.
    It supports multiple avatar providers through a factory pattern and includes
    error handling for individual slide processing. The function can be disabled
    via configuration and includes periodic cancellation checks.
    """
    await state_manager.update_step_status(
        file_id, "generate_avatar_videos", "processing"
    )
    logger.info(f"Starting avatar video generation for file: {file_id}")
    state = await state_manager.get_state(file_id)

    # Check for task cancellation before starting
    if state and state.get("task_id"):
        from slidespeaker.core.task_queue import task_queue

        if await task_queue.is_task_cancelled(state["task_id"]):
            logger.info(
                f"Task {state['task_id']} was cancelled during avatar video generation"
            )
            await state_manager.mark_cancelled(
                file_id, cancelled_step="generate_avatar_videos"
            )
            return

    # Check if avatar generation is enabled
    generate_avatar = True
    if state and "generate_avatar" in state:
        generate_avatar = state["generate_avatar"]

    # If avatar generation is disabled, skip this step
    if not generate_avatar:
        logger.info("Avatar generation disabled, skipping avatar video generation")
        await state_manager.update_step_status(
            file_id, "generate_avatar_videos", "completed", []
        )
        logger.info("Stage 'Creating AI presenter videos' skipped (disabled)")
        return

    # Comprehensive null checking for transcripts data
    scripts = []
    if (
        state
        and "steps" in state
        and "revise_transcripts" in state["steps"]
        and state["steps"]["revise_transcripts"]["data"] is not None
    ):
        scripts = state["steps"]["revise_transcripts"]["data"]

    if not scripts:
        raise ValueError("No transcripts data available for avatar video generation")

    avatar_videos = []
    failed_slides = []

    for i, script_data in enumerate(scripts):
        # Check for task cancellation periodically
        if i % 2 == 0 and state and state.get("task_id"):  # Check every 2 slides
            from slidespeaker.core.task_queue import task_queue

            if await task_queue.is_task_cancelled(state["task_id"]):
                logger.info(
                    f"Task {state['task_id']} was cancelled during "
                    f"avatar video generation"
                )
                await state_manager.mark_cancelled(
                    file_id, cancelled_step="generate_avatar_videos"
                )
                return

        # Additional null check for individual script data
        if script_data and "script" in script_data and script_data["script"]:
            video_path = config.output_dir / f"{file_id}_avatar_{i + 1}.mp4"
            try:
                # Create avatar service using factory
                avatar_service = AvatarFactory.create_service()

                await avatar_service.generate_avatar_video(
                    script_data["script"],
                    video_path,
                )

                # Keep avatar videos local - only final files should be uploaded to cloud storage
                avatar_videos.append(str(video_path))
                logger.info(f"Generated avatar video for slide {i + 1}: {video_path}")

            except Exception as e:
                logger.error(f"Failed to generate avatar video for slide {i + 1}: {e}")
                failed_slides.append(i + 1)
                # Continue with other slides instead of failing completely
                continue

    # If all slides failed, raise an error
    if len(failed_slides) == len(scripts):
        raise Exception(
            f"Failed to generate avatar videos for all slides: {failed_slides}"
        )

    # Log partial failures
    if failed_slides:
        logger.warning(
            f"Failed to generate avatar videos for slides: {failed_slides}. "
            f"Continuing with remaining slides."
        )

    await state_manager.update_step_status(
        file_id, "generate_avatar_videos", "completed", avatar_videos
    )
    logger.info(
        f"Stage 'Creating AI presenter videos' completed successfully with "
        f"{len(avatar_videos)} videos"
    )

    # Verify state was updated
    updated_state = await state_manager.get_state(file_id)
    if (
        updated_state
        and updated_state["steps"]["generate_avatar_videos"]["status"] == "completed"
    ):
        logger.info(
            f"Successfully updated generate_avatar_videos to completed for {file_id}"
        )
        logger.info(f"Avatar videos: {avatar_videos}")
        if failed_slides:
            logger.info(f"Failed slides: {failed_slides}")
    else:
        logger.error(f"Failed to update generate_avatar_videos state for {file_id}")
