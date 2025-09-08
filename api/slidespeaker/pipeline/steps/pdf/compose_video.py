"""
PDF video composition step for SlideSpeaker.

This module handles the composition of the final video from PDF chapters.
"""

from pathlib import Path

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.processing.video_composer import VideoComposer
from slidespeaker.utils.config import get_storage_provider

video_composer = VideoComposer()

# Get storage provider instance
storage_provider = get_storage_provider()


async def compose_video_step(file_id: str) -> None:
    """
    Compose the final video from PDF chapters.

    Args:
        file_id: Unique identifier for the file
    """
    await state_manager.update_step_status(file_id, "compose_pdf_video", "in_progress")
    logger.info(f"Composing final video from PDF chapters for file: {file_id}")

    try:
        # Get state to retrieve image paths, audio paths, and subtitle paths
        state = await state_manager.get_state(file_id)

        # Extract data from previous steps with proper null checking
        image_paths_data = []
        audio_paths_data = []
        subtitle_paths_data = []

        if (
            state
            and "steps" in state
            and "generate_pdf_chapter_images" in state["steps"]
            and state["steps"]["generate_pdf_chapter_images"]["data"] is not None
        ):
            image_data = state["steps"]["generate_pdf_chapter_images"]["data"]
            # Handle both old format (list of strings) and new format (dict with local_paths)
            if isinstance(image_data, dict) and "local_paths" in image_data:
                image_paths_data = image_data["local_paths"]
            else:
                image_paths_data = image_data

        if (
            state
            and "steps" in state
            and "generate_pdf_audio" in state["steps"]
            and state["steps"]["generate_pdf_audio"]["data"] is not None
        ):
            audio_data = state["steps"]["generate_pdf_audio"]["data"]
            # Handle both old format (list of strings) and new format (dict with local_paths)
            if isinstance(audio_data, dict) and "local_paths" in audio_data:
                audio_paths_data = audio_data["local_paths"]
            else:
                audio_paths_data = audio_data

        if (
            state
            and "steps" in state
            and "generate_pdf_subtitles" in state["steps"]
            and state["steps"]["generate_pdf_subtitles"]["data"] is not None
        ):
            subtitle_data = state["steps"]["generate_pdf_subtitles"]["data"]
            # Check if we have final combined subtitles
            if isinstance(subtitle_data, dict) and "final_subtitles" in subtitle_data:
                final_subtitle_data = subtitle_data["final_subtitles"]
                # Use final combined subtitles if available
                if "local_paths" in final_subtitle_data:
                    subtitle_paths_data = final_subtitle_data["local_paths"]
                else:
                    # Fallback to chapter subtitles if final subtitles not available
                    if "local_paths" in subtitle_data:
                        subtitle_paths_data = subtitle_data["local_paths"]
                    else:
                        subtitle_paths_data = (
                            subtitle_data["local_paths"]
                            if isinstance(subtitle_data, dict)
                            and "local_paths" in subtitle_data
                            else []
                        )
            else:
                # Handle old format (list of strings) and new format (dict with local_paths)
                if isinstance(subtitle_data, dict) and "local_paths" in subtitle_data:
                    subtitle_paths_data = subtitle_data["local_paths"]
                else:
                    subtitle_paths_data = subtitle_data

        # Convert to Path objects
        image_paths = [Path(p) for p in image_paths_data] if image_paths_data else []
        audio_paths = [Path(p) for p in audio_paths_data] if audio_paths_data else []
        subtitle_paths = (
            [Path(p) for p in subtitle_paths_data] if subtitle_paths_data else []
        )

        # Validate that we have image paths (minimum requirement)
        if not image_paths:
            logger.error(
                f"No image paths found for PDF video composition for file {file_id}"
            )
            logger.error(f"State data: {state}")
            raise ValueError("No image paths available for PDF video composition")

        # Prepare segments for video composition
        segments = []

        # Handle segments based on whether we have audio files or not
        if audio_paths:
            # We have audio files, so create segments with audio
            # First segment is the title slide with no audio (5 seconds duration)
            if image_paths:
                title_segment = {
                    "image": str(image_paths[0]),  # Title slide is first
                    "duration": 5.0,  # 5 seconds for title slide
                }
                segments.append(title_segment)

            # Add segments for each chapter with audio
            audio_index = 0
            subtitle_index = 0
            # Start from index 1 for chapter slides (0 is title slide)
            for i in range(1, len(image_paths)):
                if audio_index < len(audio_paths):
                    segment: dict[str, object] = {
                        "image": str(image_paths[i]),
                        "audio": str(audio_paths[audio_index]),
                    }
                    if subtitle_paths and subtitle_index < len(subtitle_paths):
                        segment["subtitle"] = str(subtitle_paths[subtitle_index])
                    segments.append(segment)
                    audio_index += 1
                    subtitle_index += 1
        else:
            # No audio files, create simple image-only segments
            for i, image_path in enumerate(image_paths):
                if i == 0:
                    # Title slide with 5 seconds duration
                    segment = {"image": str(image_path), "duration": 5.0}
                else:
                    # Chapter slides with default 5 seconds duration
                    segment = {"image": str(image_path), "duration": 5.0}
                segments.append(segment)

        # Validate that we have segments to compose
        if not segments:
            logger.error(
                f"No segments created for PDF video composition for file {file_id}"
            )
            logger.error(
                f"Image paths: {len(image_paths)}, Audio paths: {len(audio_paths)}, "
                f"Subtitle paths: {len(subtitle_paths)}"
            )
            raise ValueError("No segments provided for video composition")
        work_dir = Path("output") / file_id
        output_path = work_dir / f"{file_id}_final.mp4"
        await video_composer.compose_video_from_segments(segments, str(output_path))

        # Upload final video to storage provider
        try:
            object_key = f"{file_id}_final.mp4"
            storage_url = storage_provider.upload_file(
                str(output_path), object_key, "video/mp4"
            )
            logger.info(f"Uploaded final video to storage: {storage_url}")

            # Store the storage URL instead of local path
            await state_manager.update_step_status(
                file_id, "compose_pdf_video", "completed", storage_url
            )
        except Exception as e:
            logger.error(f"Failed to upload video to storage: {e}")
            # Fallback to local path if storage upload fails
            await state_manager.update_step_status(
                file_id, "compose_pdf_video", "completed", str(output_path)
            )

        logger.info(f"Final video composed and uploaded: {output_path}")

    except Exception as e:
        logger.error(f"Failed to compose PDF video for file {file_id}: {e}")
        raise
