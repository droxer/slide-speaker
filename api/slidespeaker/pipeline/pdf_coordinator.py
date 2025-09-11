"""
PDF processing coordinator for SlideSpeaker.

This module coordinates the PDF processing pipeline by managing step execution,
state tracking, and error handling. It provides state-aware processing that
can resume from any step and handles task cancellation.
"""

from pathlib import Path

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.core.task_queue import task_queue

from .steps.pdf import (
    compose_video_step,
    generate_audio_step,
    generate_frames_step,
    generate_subtitles_step,
    revise_transcripts_step,
    segment_content_step,
)
from .steps.pdf.translate_transcripts import (
    translate_subtitle_transcripts_step,
    translate_voice_transcripts_step,
)


def _get_pdf_processing_steps(
    voice_language: str, subtitle_language: str | None, generate_subtitles: bool
) -> list[str]:
    """
    Get the ordered list of processing steps for PDF files.

    The steps are:
    1. Segment PDF content into chapters
    2. Generate and revise English transcripts first
    3. Translate transcripts if needed
    4. Generate chapter images
    5. Generate audio for chapters
    6. Generate subtitles (if requested)
    7. Compose final video
    """
    # Always generate English transcripts first
    steps_order = [
        "segment_pdf_content",
        "revise_pdf_transcripts",  # Revise English transcripts first
    ]

    # Add translation steps
    if voice_language.lower() != "english":
        steps_order.extend(["translate_voice_transcripts"])
    if subtitle_language and subtitle_language.lower() != "english":
        steps_order.extend(["translate_subtitle_transcripts"])

    # Continue with remaining steps
    steps_order.extend(
        [
            "generate_pdf_chapter_images",
            "generate_pdf_audio",
        ]
    )

    # Add subtitle generation step only if requested
    if generate_subtitles:
        steps_order.append("generate_pdf_subtitles")

    # Always add compose video step
    steps_order.append("compose_video")

    return steps_order


def _format_pdf_step_display_name(
    step_name: str, voice_language: str | None, subtitle_language: str | None
) -> str:
    """Return display label for PDF steps with unified translate label when appropriate."""
    base_names: dict[str, str] = {
        "segment_pdf_content": "Segmenting PDF content into chapters",
        "revise_pdf_transcripts": "Revising and refining chapter transcripts",
        "translate_voice_transcripts": "Translating voice transcripts",
        "translate_subtitle_transcripts": "Translating subtitle transcripts",
        "generate_pdf_chapter_images": "Generating chapter images",
        "generate_pdf_audio": "Generating chapter audio",
        "generate_pdf_subtitles": "Generating subtitles",
        "compose_video": "Composing final video",
    }
    if step_name in ("translate_voice_transcripts", "translate_subtitle_transcripts"):
        vl = (voice_language or "english").lower()
        sl = (subtitle_language or vl).lower()
        # Only use unified label when both languages are the same and not English
        if vl == sl and vl != "english":
            return "Translating transcripts"
        # Otherwise use specific labels
        elif step_name == "translate_voice_transcripts":
            return "Translating voice transcripts"
        else:
            return "Translating subtitle transcripts"
    return base_names.get(step_name, step_name)


async def _execute_pdf_step(
    file_id: str,
    file_path: Path,
    step_name: str,
    voice_language: str = "english",
    subtitle_language: str | None = None,
    task_id: str | None = None,
) -> None:
    """
    Execute a single step in the PDF processing pipeline.

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

    # Skip completed steps
    if state and state["steps"][step_name]["status"] == "completed":
        display_name = _format_pdf_step_display_name(
            step_name, voice_language, subtitle_language
        )
        logger.info(f"=== Task {task_id} - Stage already completed: {display_name} ===")
        return

    # Process pending, failed, or in_progress steps
    if state and state["steps"][step_name]["status"] in [
        "pending",
        "failed",
        "in_progress",
    ]:
        display_name = _format_pdf_step_display_name(
            step_name, voice_language, subtitle_language
        )
        logger.info(f"=== Task {task_id} - Executing stage: {display_name} ===")

        # Update step status to in_progress
        await state_manager.update_step_status(file_id, step_name, "in_progress")
        logger.info(f"Stage '{display_name}' status updated to in_progress")

        try:
            if task_id:
                logger.info(f"=== Task {task_id} - Started: {display_name} ===")

            # Execute the appropriate step
            if step_name == "segment_pdf_content":
                await segment_content_step(
                    file_id, file_path, "english"
                )  # Always use English first
            elif step_name == "revise_pdf_transcripts":
                await revise_transcripts_step(
                    file_id, "english"
                )  # Always revise English transcripts first
            elif step_name == "translate_voice_transcripts":
                # Translate for voice generation
                await translate_voice_transcripts_step(
                    file_id,
                    source_language="english",
                    target_language=voice_language,
                )
            elif step_name == "translate_subtitle_transcripts":
                # Translate for subtitle generation
                await translate_subtitle_transcripts_step(
                    file_id,
                    source_language="english",
                    target_language=subtitle_language or "english",
                )
            elif step_name == "generate_pdf_chapter_images":
                await generate_frames_step(file_id, voice_language)
            elif step_name == "generate_pdf_audio":
                await generate_audio_step(file_id, voice_language)
            elif step_name == "generate_pdf_subtitles":
                subtitle_lang = subtitle_language or voice_language
                await generate_subtitles_step(file_id, subtitle_lang)
            elif step_name == "compose_video":
                await compose_video_step(file_id)
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


async def process_pdf_file(
    file_id: str,
    file_path: Path,
    voice_language: str = "english",
    subtitle_language: str | None = None,
    generate_subtitles: bool = True,
    task_id: str | None = None,
) -> None:
    """
    State-aware processing that can resume from any step in the PDF pipeline.

    This function orchestrates the complete PDF processing workflow,
    managing each step's execution, tracking progress, and handling errors or cancellations.
    """
    logger.info(f"Initiating AI PDF generation for file: {file_id}")
    logger.info(
        f"Voice language: {voice_language}, Subtitle language: {subtitle_language}"
    )
    logger.info(f"Generate subtitles: {generate_subtitles}")

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
        # Create initial state for PDF processing
        await state_manager.create_state(
            file_id,
            file_path,
            ".pdf",
            file_path.name,
            voice_language,
            subtitle_language,
            "hd",  # video_resolution (default to HD)
            False,  # generate_avatar (not applicable for PDF)
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
            state["generate_avatar"] = False  # Not applicable for PDF
            state["generate_subtitles"] = generate_subtitles
            # Store task_id in state for easier access
            if task_id:
                state["task_id"] = task_id
            await state_manager._save_state(file_id, state)

    # Log initial state
    await _log_initial_pdf_state(file_id)

    if task_id:
        logger.info(f"=== Starting step-by-step processing for task {task_id} ===")

    # Define processing steps in order for PDF files
    steps_order = _get_pdf_processing_steps(
        voice_language, subtitle_language, generate_subtitles
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
                await _execute_pdf_step(
                    file_id,
                    file_path,
                    step_name,
                    voice_language,
                    subtitle_language,
                    task_id,
                )

                # Step completion handled inside _execute_pdf_step
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
        logger.error(f"AI PDF generation failed for file {file_id}: {e}")
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


async def _log_initial_pdf_state(file_id: str) -> None:
    """Log the initial processing state with human-readable step names"""
    state = await state_manager.get_state(file_id)
    if state:
        logger.info(f"Current processing status: {state['status']}")
        for step_name, step_data in state["steps"].items():
            display_name = _format_pdf_step_display_name(
                step_name,
                state.get("voice_language"),
                state.get("subtitle_language"),
            )
            status_text = step_data["status"]
            if status_text == "skipped":
                status_text = "Skipped (disabled)"
            logger.info(f"Stage '{display_name}': {status_text}")
    else:
        logger.info(f"No existing processing state found for {file_id}")
