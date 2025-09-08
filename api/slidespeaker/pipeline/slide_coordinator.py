"""
Slide processing coordinator for SlideSpeaker.

This module coordinates the slide processing pipeline by managing step execution,
state tracking, and error handling. It provides state-aware processing that
can resume from any step and handles task cancellation.
"""

from pathlib import Path

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.core.task_queue import task_queue

from .steps.slides import (
    analyze_slides_step,
    compose_video_step,
    convert_slides_step,
    extract_slides_step,
    generate_audio_step,
    generate_avatar_step,
    generate_scripts_step,
    generate_subtitles_step,
    review_scripts_step,
    translate_subtitle_scripts_step,
    translate_voice_scripts_step,
)


def _get_processing_steps(
    voice_language: str, subtitle_language: str | None, generate_avatar: bool
) -> list[str]:
    """
    Get the ordered list of processing steps based on parameters.

    The steps are dynamically determined based on user preferences such as
    language settings, avatar generation, and subtitle requirements.
    For non-English languages, we first generate English scripts, then translate them.
    """
    # Always generate English scripts first
    steps_order = [
        "extract_slides",
        "convert_slides_to_images",
        "analyze_slide_images",
        "generate_scripts",  # Generate English scripts first
        "review_scripts",  # Review English scripts first
    ]

    # Add translation steps for voice if language is not English
    if voice_language.lower() != "english":
        steps_order.extend(["translate_voice_scripts"])

    # Add translation steps for subtitles if subtitle language is specified and not English
    if subtitle_language and subtitle_language.lower() != "english":
        steps_order.extend(["translate_subtitle_scripts"])

    # Continue with audio generation using translated scripts (if applicable)
    steps_order.extend(["generate_audio"])

    # Add avatar generation step only if enabled
    if generate_avatar:
        steps_order.append("generate_avatar_videos")

    # Always add subtitle generation step
    steps_order.append("generate_subtitles")

    # Always add compose video step
    steps_order.append("compose_video")

    return steps_order


async def _execute_step(
    file_id: str,
    file_path: Path,
    file_ext: str,
    step_name: str,
    voice_language: str = "english",
    task_id: str | None = None,
) -> None:
    """
    Execute a single step in the slide pipeline.

    This function handles step execution with proper cancellation checking,
    state management, and error handling for each processing stage.
    """
    # Check for cancellation before processing the step
    if task_id and await task_queue.is_task_cancelled(task_id):
        logger.info(f"Task {task_id} was cancelled during step {step_name}")
        await state_manager.mark_failed(file_id)
        return

    # Get fresh state
    state = await state_manager.get_state(file_id)

    # Get subtitle language from state
    subtitle_language = None
    if state and "subtitle_language" in state:
        subtitle_language = state["subtitle_language"]
    # Default to audio language if subtitle language not specified
    if subtitle_language is None:
        subtitle_language = voice_language

    # Skip completed steps
    if state and state["steps"][step_name]["status"] == "completed":
        step_display_names = {
            "extract_slides": "Extracting presentation content",
            "convert_slides_to_images": "Converting slides to images",
            "analyze_slide_images": "Analyzing visual content",
            "generate_scripts": "Generating AI narratives",
            "generate_subtitle_scripts": "Generating subtitle narratives",
            "review_scripts": "Reviewing and refining scripts",
            "review_subtitle_scripts": "Reviewing subtitle scripts",
            "translate_voice_scripts": "Translating voice scripts",
            "translate_subtitle_scripts": "Translating subtitle scripts",
            "generate_audio": "Synthesizing voice audio",
            "generate_avatar_videos": "Creating AI presenter videos",
            "generate_subtitles": "Generating subtitles",
            "compose_video": "Composing final presentation",
        }
        display_name = step_display_names.get(step_name, step_name)
        logger.info(f"=== Task {task_id} - Stage already completed: {display_name} ===")
        return

    # Process pending, failed, or in_progress steps
    if state and state["steps"][step_name]["status"] in [
        "pending",
        "failed",
        "in_progress",
    ]:
        step_display_names = {
            "extract_slides": "Extracting presentation content",
            "convert_slides_to_images": "Converting slides to images",
            "analyze_slide_images": "Analyzing visual content",
            "generate_scripts": "Generating AI narratives",
            "generate_subtitle_scripts": "Generating subtitle narratives",
            "review_scripts": "Reviewing and refining scripts",
            "review_subtitle_scripts": "Reviewing subtitle scripts",
            "translate_voice_scripts": "Translating voice scripts",
            "translate_subtitle_scripts": "Translating subtitle scripts",
            "generate_audio": "Synthesizing voice audio",
            "generate_avatar_videos": "Creating AI presenter videos",
            "generate_subtitles": "Generating subtitles",
            "compose_video": "Composing final presentation",
        }
        display_name = step_display_names.get(step_name, step_name)
        logger.info(f"=== Task {task_id} - Executing stage: {display_name} ===")

        # Update step status to in_progress
        await state_manager.update_step_status(file_id, step_name, "in_progress")
        logger.info(f"Stage '{display_name}' status updated to in_progress")

        try:
            if task_id:
                logger.info(f"=== Task {task_id} - Started: {display_name} ===")

            # Execute the appropriate step
            if step_name == "extract_slides":
                await extract_slides_step(file_id, file_path, file_ext)
            elif step_name == "analyze_slide_images":
                await analyze_slides_step(file_id)
            elif step_name == "generate_scripts":
                # Always generate English scripts first
                await generate_scripts_step(file_id, "english")
            elif step_name == "generate_subtitle_scripts":
                await generate_scripts_step(
                    file_id, subtitle_language, is_subtitle=True
                )
            elif step_name == "review_scripts":
                # Always review English scripts first
                await review_scripts_step(file_id, "english")
            elif step_name == "review_subtitle_scripts":
                await review_scripts_step(file_id, subtitle_language, is_subtitle=True)
            elif step_name == "translate_voice_scripts":
                # Translate English scripts to voice language
                await translate_voice_scripts_step(file_id, voice_language)
            elif step_name == "translate_subtitle_scripts":
                # Translate English scripts to subtitle language
                await translate_subtitle_scripts_step(file_id, subtitle_language)
            elif step_name == "generate_audio":
                # Use translated scripts if available, otherwise use English scripts
                audio_language = voice_language
                await generate_audio_step(file_id, audio_language)
            elif step_name == "generate_avatar_videos":
                await generate_avatar_step(file_id)
            elif step_name == "generate_subtitles":
                await generate_subtitles_step(file_id, subtitle_language)
            elif step_name == "convert_slides_to_images":
                await convert_slides_step(file_id, file_path, file_ext)
            elif step_name == "compose_video":
                await compose_video_step(file_id, file_path)

            # Mark step as completed
            await state_manager.update_step_status(
                file_id, step_name, "completed", data=None
            )

            if task_id:
                logger.info(f"=== Task {task_id} - Completed: {display_name} ===")
        except Exception as e:
            if task_id:
                logger.error(f"=== Task {task_id} - Failed: {display_name} - {e} ===")
            raise


async def process_slide_file(
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
    State-aware processing that can resume from any step in the slide pipeline.

    This function orchestrates the complete slide processing workflow,
    managing each step's execution, tracking progress, and handling errors or cancellations.
    """
    # Don't default subtitle language to audio language - preserve user selection
    # subtitle_language remains as provided (could be None)

    logger.info(
        f"Initiating AI slide generation for file: {file_id}, format: {file_ext}"
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
            voice_language,
            subtitle_language,
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

    # Log initial state
    await _log_initial_state(file_id)

    if task_id:
        logger.info(f"=== Starting step-by-step processing for task {task_id} ===")

    # Define processing steps in order for PPT/PPTX files
    steps_order = _get_processing_steps(
        voice_language, subtitle_language, generate_avatar
    )

    try:
        # Process each step in order, skipping completed ones
        total_steps = len(steps_order)
        completed_steps = 0

        for step_index, step_name in enumerate(steps_order, 1):
            # Check for cancellation before processing each step
            if task_id and await task_queue.is_task_cancelled(task_id):
                logger.info(
                    f"Task {task_id} was cancelled during processing at step {step_name}"
                )
                await state_manager.mark_cancelled(file_id, cancelled_step=step_name)
                return

            # Get current step status
            step_status = await state_manager.get_step_status(file_id, step_name)
            if step_status and step_status.get("status") == "completed":
                logger.info(
                    f"Skipping already completed step: {step_name} ({step_index}/{total_steps})"
                )
                completed_steps += 1
                continue

            logger.info(
                f"Starting processing step: {step_name} ({step_index}/{total_steps})"
            )

            # Execute the step
            try:
                await _execute_step(
                    file_id, file_path, file_ext, step_name, voice_language, task_id
                )

                # Mark step as completed
                await state_manager.update_step_status(
                    file_id, step_name, "completed", data=None
                )
                completed_steps += 1
                logger.info(f"Completed step: {step_name} ({step_index}/{total_steps})")

            except Exception as step_error:
                logger.error(f"Step {step_name} failed: {step_error}")
                await state_manager.update_step_status(
                    file_id, step_name, "failed", data={"error": str(step_error)}
                )
                await state_manager.add_error(file_id, str(step_error), step_name)
                raise step_error

        # All steps completed successfully
        await state_manager.mark_completed(file_id)
        logger.info(f"All processing steps completed for file {file_id}")

        if task_id:
            logger.info(f"Task {task_id} processing completed successfully")

    except Exception as e:
        logger.error(f"AI slide generation failed for file {file_id}: {e}")
        logger.error(f"Error category: {type(e).__name__}")
        import traceback

        logger.error(f"Technical details: {traceback.format_exc()}")

        # Update error state
        current_step = "unknown"
        state = await state_manager.get_state(file_id)
        if state and "current_step" in state:
            current_step = state["current_step"]

        # Check if this was actually a cancellation
        task_id = state.get("task_id") if state else None
        was_cancelled = False
        if task_id and await task_queue.is_task_cancelled(task_id):
            was_cancelled = True

        try:
            if was_cancelled:
                await state_manager.mark_cancelled(file_id, cancelled_step=current_step)
                logger.info(f"Processing marked as cancelled for file {file_id}")
            else:
                await state_manager.update_step_status(file_id, current_step, "failed")
                await state_manager.add_error(file_id, str(e), current_step)
                await state_manager.mark_failed(file_id)
                logger.info(f"Processing marked as failed for file {file_id}")
        except Exception as inner_error:
            logger.error(f"Unable to update processing state: {inner_error}")

        # Don't cleanup on error - allow retry from last successful step


async def _log_initial_state(file_id: str) -> None:
    """Log the initial processing state with human-readable step names"""
    state = await state_manager.get_state(file_id)
    if state:
        logger.info(f"Current processing status: {state['status']}")
        for step_name, step_data in state["steps"].items():
            step_display_names = {
                "extract_slides": "Extracting slide content",
                "convert_slides_to_images": "Converting slides to images",
                "analyze_slide_images": "Analyzing visual content",
                "generate_scripts": "Generating AI narratives",
                "generate_subtitle_scripts": "Generating subtitle narratives",
                "review_scripts": "Reviewing and refining scripts",
                "review_subtitle_scripts": "Reviewing subtitle scripts",
                "translate_voice_scripts": "Translating voice scripts",
                "translate_subtitle_scripts": "Translating subtitle scripts",
                "generate_audio": "Synthesizing voice audio",
                "generate_avatar_videos": "Creating AI presenter videos",
                "generate_subtitles": "Generating subtitles",
                "compose_video": "Composing final presentation",
            }
            display_name = step_display_names.get(step_name, step_name)
            status_text = step_data["status"]
            if status_text == "skipped":
                status_text = "Skipped (disabled)"
            logger.info(f"Stage '{display_name}': {status_text}")
    else:
        logger.info(f"No existing processing state found for {file_id}")
