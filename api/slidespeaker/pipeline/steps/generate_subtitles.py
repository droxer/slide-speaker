"""
Generate subtitles step for the presentation pipeline.
"""

from pathlib import Path
from typing import Any
from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.processing.subtitle_generator import SubtitleGenerator
from slidespeaker.utils.config import config

subtitle_generator = SubtitleGenerator()


async def generate_subtitles_step(file_id: str, language: str = "english") -> None:
    """Generate subtitles from scripts"""
    await state_manager.update_step_status(file_id, "generate_subtitles", "processing")
    logger.info(f"Starting subtitle generation for file: {file_id}")
    state = await state_manager.get_state(file_id)

    # Always generate subtitles
    # Get scripts for subtitle generation
    # Use subtitle-specific scripts if they exist (when languages differ),
    # otherwise use regular scripts
    scripts_data: list[dict[str, Any]] = []
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

    if not scripts_data:
        logger.warning("No scripts data available for subtitle generation")
        await state_manager.update_step_status(
            file_id, "generate_subtitles", "completed", []
        )
        return

    # Get audio files for timing
    audio_files_data = []
    if (
        state
        and "steps" in state
        and "generate_audio" in state["steps"]
        and state["steps"]["generate_audio"]["data"] is not None
    ):
        audio_files_data = state["steps"]["generate_audio"]["data"]

    # Generate subtitle files
    try:
        video_path = config.output_dir / f"{file_id}_final.mp4"

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
                video_path,
                language,
            )
        else:
            audio_files = [Path(p) for p in audio_files_data]
            srt_path, vtt_path = subtitle_generator.generate_subtitles(
                scripts_data,
                audio_files,
                video_path,
                language
            )
        logger.info(f"Generated subtitles: {srt_path}, {vtt_path}")

        # Store the subtitle file paths in the state
        subtitle_files = [str(srt_path), str(vtt_path)]
        await state_manager.update_step_status(
            file_id, "generate_subtitles", "completed", subtitle_files
        )
        logger.info("Stage 'Generating subtitles' completed successfully")

    except Exception as e:
        logger.error(f"Failed to generate subtitles: {e}")
        import traceback
        logger.error(f"Subtitle generation traceback: {traceback.format_exc()}")
        await state_manager.update_step_status(
            file_id, "generate_subtitles", "failed", []
        )
        raise