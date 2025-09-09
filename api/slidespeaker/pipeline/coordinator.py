"""
Pipeline coordinator for SlideSpeaker processing.

This module coordinates the presentation processing pipeline by delegating to
specialized coordinators for PDF and PPT/PPTX files. It provides state-aware
processing that can resume from any step and handles task cancellation.
"""

from pathlib import Path

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.core.task_queue import task_queue

# Import specialized coordinators
from .pdf_coordinator import process_pdf_file
from .slide_coordinator import process_slide_file


async def accept_task(
    file_id: str,
    file_path: Path,
    file_ext: str,
    voice_language: str = "english",
    subtitle_language: str | None = None,
    generate_avatar: bool = True,
    generate_subtitles: bool = True,
    task_id: str | None = None,
) -> None:
    """
    State-aware processing that delegates to specialized coordinators based on file type.

    This function orchestrates the complete presentation processing workflow by
    delegating to specialized coordinators for PDF and PPT/PPTX files.
    """
    # Don't default subtitle language to audio language - preserve user selection
    # subtitle_language remains as provided (could be None)

    logger.info(
        f"Initiating AI presentation generation for file: {file_id}, format: {file_ext}"
    )
    logger.info(
        f"Voice language: {voice_language}, Subtitle language: {subtitle_language}"
    )
    logger.info(
        f"Generate avatar: {generate_avatar}, Generate subtitles: {generate_subtitles}"
    )

    # Log file validation
    if not file_path.exists():
        logger.warning(f"File path does not exist: {file_path}")
    elif not file_path.is_file():
        logger.warning(f"File path is not a regular file: {file_path}")

    # Check if task has been cancelled before starting (if task_id provided)
    if task_id and await task_queue.is_task_cancelled(task_id):
        logger.info(f"Task {task_id} was cancelled before processing started")
        await state_manager.mark_cancelled(file_id)
        return

    # Initialize state
    state = await state_manager.get_state(file_id)
    if not state:
        await state_manager.create_state(
            file_id,
            file_path,
            file_ext,
            file_path.name,
            voice_language,
            subtitle_language,
            "hd",  # video_resolution (default to HD)
            generate_avatar,
            generate_subtitles,
        )
        state = await state_manager.get_state(file_id)
        # Store task_id in state for easier access
        if task_id and state:
            state["task_id"] = task_id
            await state_manager._save_state(file_id, state)
    else:
        # Update existing state with new parameters (in case they've changed)
        if state:
            state["voice_language"] = voice_language
            state["subtitle_language"] = subtitle_language
            state["generate_avatar"] = generate_avatar
            state["generate_subtitles"] = generate_subtitles
            # Store task_id in state for easier access
            if task_id:
                state["task_id"] = task_id
            await state_manager._save_state(file_id, state)

    # Delegate to specialized coordinators based on file type
    if file_ext.lower() == ".pdf":
        # Use PDF-specific coordinator
        await process_pdf_file(
            file_id,
            file_path,
            voice_language,
            subtitle_language,
            generate_subtitles,
            task_id,
        )
    else:
        # Use PPT/PPTX-specific coordinator
        await process_slide_file(
            file_id,
            file_path,
            file_ext,
            voice_language,
            subtitle_language,
            generate_avatar,
            generate_subtitles,
            task_id,
        )
