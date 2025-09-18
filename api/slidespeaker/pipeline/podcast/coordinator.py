"""
Podcast pipeline coordinator (from PDF sources).

Generates a two-person conversation podcast based on PDF chapter segmentation.
"""

from contextlib import suppress
from pathlib import Path

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.core.task_queue import task_queue

from ..steps.podcast.pdf import (
    compose_podcast_step,
    generate_podcast_audio_step,
    generate_podcast_script_step,
    translate_podcast_script_step,
)
from ..steps.video.pdf import segment_content_step as pdf_segment_content_step


def _podcast_steps(voice_language: str) -> list[str]:
    steps: list[str] = ["generate_podcast_script"]
    if voice_language.lower() != "english":
        steps.append("translate_podcast_script")
    steps.extend(["generate_podcast_audio", "compose_podcast"])
    return steps


def _podcast_step_name(step: str) -> str:
    base = {
        "generate_podcast_script": "Generating 2-person podcast script",
        "translate_podcast_script": "Translating podcast script",
        "generate_podcast_audio": "Generating podcast audio (multi-voice)",
        "compose_podcast": "Composing final podcast (MP3)",
    }
    return base.get(step, step)


async def from_pdf(
    file_id: str,
    file_path: Path,
    voice_language: str = "english",
    transcript_language: str | None = None,
    task_id: str | None = None,
) -> None:
    logger.info(f"Starting podcast generation (PDF) for file {file_id}")

    if task_id and await task_queue.is_task_cancelled(task_id):
        logger.info(f"Task {task_id} was cancelled before processing started")
        await state_manager.mark_cancelled(file_id)
        return

    # Ensure base state exists (accept_task should have created it)
    st = await state_manager.get_state(file_id)
    if st:
        st["generate_podcast"] = True
        st["voice_language"] = voice_language
        if transcript_language:
            st["podcast_transcript_language"] = transcript_language
        await state_manager.save_state(file_id, st)

    # Ensure prerequisite PDF segmentation exists for podcast-only runs
    try:
        st_now = await state_manager.get_state(file_id)
        needs_segment = True
        if st_now and (steps := st_now.get("steps")):
            seg = steps.get("segment_pdf_content") if isinstance(steps, dict) else None
            if (
                seg
                and isinstance(seg, dict)
                and seg.get("status") == "completed"
                and seg.get("data")
            ):
                needs_segment = False
        if needs_segment:
            await pdf_segment_content_step(file_id, file_path, "english")
    except Exception as e:
        logger.error(f"Prerequisite PDF segmentation failed for podcast: {e}")
        await state_manager.add_error(file_id, str(e), "segment_pdf_content")
        await state_manager.mark_failed(file_id)
        raise

    steps_order = _podcast_steps(voice_language)

    try:
        for step_name in steps_order:
            if task_id and await task_queue.is_task_cancelled(task_id):
                logger.info(f"Task {task_id} was cancelled during step {step_name}")
                await state_manager.mark_cancelled(file_id, cancelled_step=step_name)
                return

            st = await state_manager.get_step_status(file_id, step_name)
            if st and st.get("status") == "completed":
                logger.info(f"Skipping already completed step: {step_name}")
                continue

            if task_id:
                await state_manager.update_step_status_by_task(
                    task_id, step_name, "processing"
                )
            else:
                await state_manager.update_step_status(file_id, step_name, "processing")
            logger.info(
                f"=== Task {task_id} - Executing: {_podcast_step_name(step_name)} ==="
            )

            if step_name == "generate_podcast_script":
                await generate_podcast_script_step(file_id, "english")
            elif step_name == "translate_podcast_script":
                await translate_podcast_script_step(
                    file_id,
                    source_language="english",
                    target_language=(transcript_language or voice_language),
                )
            elif step_name == "generate_podcast_audio":
                await generate_podcast_audio_step(file_id, voice_language)
            elif step_name == "compose_podcast":
                await compose_podcast_step(file_id)

            if task_id:
                await state_manager.update_step_status_by_task(
                    task_id, step_name, "completed", data=None
                )
            else:
                await state_manager.update_step_status(
                    file_id, step_name, "completed", data=None
                )

        # Mark overall processing as completed for podcast-only or combined runs
        with suppress(Exception):
            await state_manager.mark_completed(file_id)
        logger.info(f"All podcast processing steps completed for file {file_id}")
    except Exception as e:
        logger.error(f"Podcast processing failed at step {step_name}: {e}")
        await state_manager.update_step_status(file_id, step_name, "failed")
        await state_manager.add_error(file_id, str(e), step_name)
        await state_manager.mark_failed(file_id)
        raise
