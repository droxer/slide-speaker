"""
Video pipeline coordinator for SlideSpeaker (PDF and Slides sources).

Provides two entry points:
- from_pdf(...): video processing for PDF inputs
- from_slide(...): video processing for PPT/PPTX inputs

Podcast generation is handled in the separate podcast pipeline.
"""

from pathlib import Path

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.core.task_queue import task_queue

# PDF steps (video)
from ..steps.video.pdf import (
    compose_video_step as pdf_compose_video_step,
)
from ..steps.video.pdf import (
    generate_audio_step as pdf_generate_audio_step,
)
from ..steps.video.pdf import (
    generate_frames_step as pdf_generate_frames_step,
)
from ..steps.video.pdf import (
    generate_subtitles_step as pdf_generate_subtitles_step,
)
from ..steps.video.pdf import (
    revise_transcripts_step as pdf_revise_transcripts_step,
)
from ..steps.video.pdf import (
    segment_content_step as pdf_segment_content_step,
)
from ..steps.video.pdf import (
    translate_subtitle_transcripts_step as pdf_translate_subs_step,
)
from ..steps.video.pdf import (
    translate_voice_transcripts_step as pdf_translate_voice_step,
)

# Slides steps (video)
from ..steps.video.slides import (
    analyze_slides_step,
    convert_slides_step,
    extract_slides_step,
    generate_avatar_step,
    generate_transcripts_step,
)
from ..steps.video.slides import (
    compose_video_step as slide_compose_video_step,
)
from ..steps.video.slides import (
    generate_audio_step as slide_generate_audio_step,
)
from ..steps.video.slides import (
    generate_subtitles_step as slide_generate_subtitles_step,
)
from ..steps.video.slides import (
    revise_transcripts_step as slide_revise_transcripts_step,
)
from ..steps.video.slides import (
    translate_subtitle_transcripts_step as slide_translate_subs_step,
)
from ..steps.video.slides import (
    translate_voice_transcripts_step as slide_translate_voice_step,
)

# ------------------------- PDF Coordinator (from_pdf) -------------------------


def _pdf_step_name(
    step: str, voice_language: str | None, subtitle_language: str | None
) -> str:
    base = {
        "segment_pdf_content": "Segmenting PDF content into chapters",
        "revise_pdf_transcripts": "Revising and refining chapter transcripts",
        "translate_voice_transcripts": "Translating voice transcripts",
        "translate_subtitle_transcripts": "Translating subtitle transcripts",
        "generate_pdf_chapter_images": "Generating chapter images",
        "generate_pdf_audio": "Generating chapter audio",
        "generate_pdf_subtitles": "Generating subtitles",
        "compose_video": "Composing final video",
    }
    if step in ("translate_voice_transcripts", "translate_subtitle_transcripts"):
        vl = (voice_language or "english").lower()
        sl = (subtitle_language or vl).lower()
        if vl == sl and vl != "english":
            return "Translating transcripts"
    return base.get(step, step)


def _pdf_steps(
    voice_language: str,
    subtitle_language: str | None,
    generate_subtitles: bool,
    generate_video: bool,
) -> list[str]:
    steps: list[str] = ["segment_pdf_content", "revise_pdf_transcripts"]
    if voice_language.lower() != "english":
        steps.append("translate_voice_transcripts")
    if subtitle_language and subtitle_language.lower() != "english":
        steps.append("translate_subtitle_transcripts")
    if generate_video:
        steps.extend(["generate_pdf_chapter_images", "generate_pdf_audio"])
        if generate_subtitles:
            steps.append("generate_pdf_subtitles")
        steps.append("compose_video")
    return steps


async def from_pdf(
    file_id: str,
    file_path: Path,
    voice_language: str = "english",
    subtitle_language: str | None = None,
    generate_subtitles: bool = True,
    generate_video: bool = True,
    task_id: str | None = None,
) -> None:
    logger.info(f"Initiating video generation (PDF) for file: {file_id}")
    logger.info(
        f"Voice language: {voice_language}, Subtitle language: {subtitle_language}"
    )
    logger.info(
        f"Generate subtitles: {generate_subtitles}, Generate video: {generate_video}"
    )

    if task_id and await task_queue.is_task_cancelled(task_id):
        logger.info(f"Task {task_id} was cancelled before processing started")
        await state_manager.mark_cancelled(file_id)
        return

    # Initialize/refresh state flags relevant to video
    state = await state_manager.get_state(file_id)
    if state:
        state["voice_language"] = voice_language
        state["subtitle_language"] = subtitle_language
        state["generate_avatar"] = False
        state["generate_subtitles"] = generate_subtitles
        state["generate_video"] = generate_video
        if task_id:
            state["task_id"] = task_id
        await state_manager.save_state(file_id, state)

    if task_id:
        logger.info(f"=== Starting PDF video processing for task {task_id} ===")

    steps_order = _pdf_steps(
        voice_language, subtitle_language, generate_subtitles, generate_video
    )

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

            # Mark processing (unified status)
            if task_id:
                await state_manager.update_step_status_by_task(
                    task_id, step_name, "processing"
                )
            else:
                await state_manager.update_step_status(file_id, step_name, "processing")
            logger.info(
                "=== Task %s - Executing: %s ===",
                task_id,
                _pdf_step_name(step_name, voice_language, subtitle_language),
            )

            if step_name == "segment_pdf_content":
                await pdf_segment_content_step(file_id, file_path, "english")
            elif step_name == "revise_pdf_transcripts":
                await pdf_revise_transcripts_step(file_id, "english")
            elif step_name == "translate_voice_transcripts":
                await pdf_translate_voice_step(
                    file_id, source_language="english", target_language=voice_language
                )
            elif step_name == "translate_subtitle_transcripts":
                await pdf_translate_subs_step(
                    file_id,
                    source_language="english",
                    target_language=subtitle_language or "english",
                )
            elif step_name == "generate_pdf_chapter_images":
                await pdf_generate_frames_step(file_id, voice_language)
            elif step_name == "generate_pdf_audio":
                await pdf_generate_audio_step(file_id, voice_language)
            elif step_name == "generate_pdf_subtitles":
                await pdf_generate_subtitles_step(
                    file_id, subtitle_language or "english"
                )
            elif step_name == "compose_video":
                await pdf_compose_video_step(file_id)

            # Mark completed
            if task_id:
                await state_manager.update_step_status_by_task(
                    task_id, step_name, "completed", data=None
                )
            else:
                await state_manager.update_step_status(
                    file_id, step_name, "completed", data=None
                )

        if generate_video:
            await state_manager.mark_completed(file_id)
            logger.info(f"All PDF video processing steps completed for file {file_id}")
    except Exception as e:
        logger.error(f"PDF video processing failed at step {step_name}: {e}")
        await state_manager.update_step_status(file_id, step_name, "failed")
        await state_manager.add_error(file_id, str(e), step_name)
        await state_manager.mark_failed(file_id)
        raise


# ----------------------- Slides Coordinator (from_slide) ----------------------


def _slide_step_name(step: str) -> str:
    base = {
        "extract_slides": "Extracting slides",
        "convert_slides": "Converting slides to images",
        "analyze_slides": "Analyzing slide content",
        "generate_transcripts": "Generating transcripts",
        "revise_transcripts": "Revising transcripts",
        "generate_audio": "Generating audio",
        "generate_avatar": "Generating avatar",
        "generate_subtitles": "Generating subtitles",
        "compose_video": "Composing final video",
        "translate_voice_transcripts": "Translating voice transcripts",
        "translate_subtitle_transcripts": "Translating subtitle transcripts",
    }
    return base.get(step, step)


def _slide_steps(
    generate_avatar: bool,
    generate_subtitles: bool,
) -> list[str]:
    steps: list[str] = [
        "extract_slides",
        "convert_slides",
        "analyze_slides",
        "generate_transcripts",
        "revise_transcripts",
        "generate_audio",
    ]
    if generate_avatar:
        steps.append("generate_avatar")
    if generate_subtitles:
        steps.append("generate_subtitles")
    steps.append("compose_video")
    return steps


async def from_slide(
    file_id: str,
    file_path: Path,
    file_ext: str,
    voice_language: str = "english",
    subtitle_language: str | None = None,
    generate_avatar: bool = True,
    generate_subtitles: bool = True,
    task_id: str | None = None,
) -> None:
    logger.info(f"Starting slides video processing for file {file_id}")
    logger.info(
        f"Voice language: {voice_language}, Subtitle language: {subtitle_language}"
    )
    logger.info(
        f"Generate avatar: {generate_avatar}, Generate subtitles: {generate_subtitles}"
    )

    if task_id and await task_queue.is_task_cancelled(task_id):
        logger.info(f"Task {task_id} was cancelled before processing started")
        await state_manager.mark_cancelled(file_id)
        return

    steps_order = _slide_steps(generate_avatar, generate_subtitles)

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
                f"=== Task {task_id} - Executing: {_slide_step_name(step_name)} ==="
            )

            if step_name == "extract_slides":
                await extract_slides_step(file_id, file_path, file_ext)
            elif step_name == "convert_slides":
                await convert_slides_step(file_id, file_path, file_ext)
            elif step_name == "analyze_slides":
                await analyze_slides_step(file_id)
            elif step_name == "generate_transcripts":
                await generate_transcripts_step(file_id, voice_language)
            elif step_name == "revise_transcripts":
                await slide_revise_transcripts_step(file_id, voice_language)
            elif step_name == "translate_voice_transcripts":
                await slide_translate_voice_step(
                    file_id, source_language="english", target_language=voice_language
                )
            elif step_name == "translate_subtitle_transcripts":
                await slide_translate_subs_step(
                    file_id,
                    source_language="english",
                    target_language=subtitle_language or "english",
                )
            elif step_name == "generate_audio":
                await slide_generate_audio_step(file_id, voice_language)
            elif step_name == "generate_avatar":
                await generate_avatar_step(file_id)
            elif step_name == "generate_subtitles":
                await slide_generate_subtitles_step(
                    file_id, subtitle_language or "english"
                )
            elif step_name == "compose_video":
                await slide_compose_video_step(file_id, file_path)

            if task_id:
                await state_manager.update_step_status_by_task(
                    task_id, step_name, "completed", data=None
                )
            else:
                await state_manager.update_step_status(
                    file_id, step_name, "completed", data=None
                )

        await state_manager.mark_completed(file_id)
        logger.info(f"All slides video processing steps completed for file {file_id}")
    except Exception as e:
        logger.error(f"Slides video processing failed at step {step_name}: {e}")
        await state_manager.update_step_status(file_id, step_name, "failed")
        await state_manager.add_error(file_id, str(e), step_name)
        await state_manager.mark_failed(file_id)
        raise
