"""
Pipeline coordinator for SlideSpeaker processing.

This module coordinates the presentation processing pipeline by delegating to
specialized coordinators for PDF and PPT/PPTX files. It provides state-aware
processing that can resume from any step and handles task cancellation.
"""

from pathlib import Path
from typing import TypedDict

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.core.task_queue import task_queue

# Import specialized coordinators
from .podcast import from_pdf as podcast_from_pdf
from .video import from_pdf as video_from_pdf
from .video import from_slide as video_from_slide


class NormalizedLanguages(TypedDict):
    voice: str
    subtitle: str | None
    transcript: str | None


async def accept_task(
    file_id: str,
    file_path: Path,
    file_ext: str,
    source_type: str | None = None,
    voice_language: str = "english",
    subtitle_language: str | None = None,
    transcript_language: str | None = None,
    generate_avatar: bool = False,
    generate_subtitles: bool = True,
    generate_podcast: bool = False,
    generate_video: bool = True,
    voice_id: str | None = None,
    podcast_host_voice: str | None = None,
    podcast_guest_voice: str | None = None,
    task_id: str | None = None,
) -> None:
    """
    State-aware processing that delegates to specialized coordinators based on file type.

    This function orchestrates the complete presentation processing workflow by
    delegating to specialized coordinators for PDF and PPT/PPTX files.
    """
    normalized = _normalize_languages(
        voice_language, subtitle_language, transcript_language
    )
    voice_lang = normalized["voice"]
    subtitle_lang = normalized["subtitle"]
    transcript_lang = normalized["transcript"]

    src = _validate_source(source_type, file_ext)
    _log_task_start(
        file_id=file_id,
        file_ext=file_ext,
        source_type=src,
        voice_language=voice_lang,
        subtitle_language=subtitle_lang,
        generate_avatar=generate_avatar,
        generate_subtitles=generate_subtitles,
        generate_podcast=generate_podcast,
        generate_video=generate_video,
        file_path=file_path,
    )

    if task_id and await task_queue.is_task_cancelled(task_id):
        logger.info(f"Task {task_id} was cancelled before processing started")
        await state_manager.mark_cancelled(file_id)
        return

    await _ensure_initial_state(
        file_id=file_id,
        file_path=file_path,
        file_ext=file_ext,
        voice_language=voice_lang,
        subtitle_language=subtitle_lang,
        transcript_language=transcript_lang,
        generate_avatar=generate_avatar,
        generate_subtitles=generate_subtitles,
        generate_video=generate_video,
        generate_podcast=generate_podcast,
        voice_id=voice_id,
        podcast_host_voice=podcast_host_voice,
        podcast_guest_voice=podcast_guest_voice,
        task_id=task_id,
    )

    if src == "pdf":
        await _run_pdf_pipelines(
            file_id=file_id,
            file_path=file_path,
            voice_language=voice_lang,
            subtitle_language=subtitle_lang,
            transcript_language=transcript_lang,
            generate_subtitles=generate_subtitles,
            generate_video=generate_video,
            generate_podcast=generate_podcast,
            task_id=task_id,
        )
    else:
        await _run_slide_pipeline(
            file_id=file_id,
            file_path=file_path,
            file_ext=file_ext,
            voice_language=voice_lang,
            subtitle_language=subtitle_lang,
            generate_avatar=generate_avatar,
            generate_subtitles=generate_subtitles,
            generate_video=generate_video,
            task_id=task_id,
        )


def _normalize_languages(
    voice_language: str,
    subtitle_language: str | None,
    transcript_language: str | None,
) -> NormalizedLanguages:
    from slidespeaker.configs.locales import locale_utils

    voice = locale_utils.normalize_language(voice_language)
    subtitle = (
        locale_utils.normalize_language(subtitle_language)
        if subtitle_language is not None
        else None
    )
    transcript = (
        locale_utils.normalize_language(transcript_language)
        if transcript_language is not None
        else None
    )
    return {"voice": voice, "subtitle": subtitle, "transcript": transcript}


def _validate_source(source_type: str | None, file_ext: str) -> str:
    if not source_type or str(source_type).lower() not in {"pdf", "slides"}:
        raise ValueError(
            f"source_type is required and must be 'pdf' or 'slides' (got: {source_type!r} for file_ext {file_ext})"
        )
    return str(source_type).lower()


def _log_task_start(
    *,
    file_id: str,
    file_ext: str,
    source_type: str,
    voice_language: str,
    subtitle_language: str | None,
    generate_avatar: bool,
    generate_subtitles: bool,
    generate_podcast: bool,
    generate_video: bool,
    file_path: Path,
) -> None:
    logger.info(
        "Initiating AI presentation generation for file: %s, format: %s, source_type: %s",
        file_id,
        file_ext,
        source_type,
    )
    logger.debug(
        "Voice language: %s, Subtitle language: %s",
        voice_language,
        subtitle_language,
    )
    if file_ext.lower() == ".pdf":
        logger.debug(
            "Generate subtitles: %s, Generate podcast: %s, Generate video: %s",
            generate_subtitles,
            generate_podcast,
            generate_video,
        )
    else:
        logger.debug(
            "Generate avatar: %s, Generate subtitles: %s, Generate podcast: %s",
            generate_avatar,
            generate_subtitles,
            generate_podcast,
        )

    if not file_path.exists():
        logger.warning("File path does not exist: %s", file_path)
    elif not file_path.is_file():
        logger.warning("File path is not a regular file: %s", file_path)


async def _ensure_initial_state(
    *,
    file_id: str,
    file_path: Path,
    file_ext: str,
    voice_language: str,
    subtitle_language: str | None,
    transcript_language: str | None,
    generate_avatar: bool,
    generate_subtitles: bool,
    generate_video: bool,
    generate_podcast: bool,
    voice_id: str | None,
    podcast_host_voice: str | None,
    podcast_guest_voice: str | None,
    task_id: str | None,
) -> None:
    # Get current state
    state = await state_manager.get_state(file_id)
    if not state:
        await state_manager.create_state(
            file_id,
            file_path,
            file_ext,
            file_path.name,
            voice_language,
            subtitle_language,
            transcript_language,
            "hd",
            generate_avatar,
            generate_subtitles,
            generate_video,
            generate_podcast,
            voice_id=voice_id,
            podcast_host_voice=podcast_host_voice,
            podcast_guest_voice=podcast_guest_voice,
        )
        state = await state_manager.get_state(file_id)

    if state:
        state["voice_language"] = voice_language
        state["subtitle_language"] = subtitle_language
        state["generate_avatar"] = generate_avatar
        state["generate_subtitles"] = generate_subtitles
        state["generate_podcast"] = generate_podcast
        state["generate_video"] = generate_video
        if transcript_language is not None:
            state["podcast_transcript_language"] = transcript_language
        if task_id:
            state["task_id"] = task_id

        task_kwargs = (
            state.get("task_kwargs")
            if isinstance(state.get("task_kwargs"), dict)
            else {}
        )
        task_config = (
            state.get("task_config")
            if isinstance(state.get("task_config"), dict)
            else {}
        )

        task_kwargs = dict(task_kwargs)
        task_config = dict(task_config)

        task_kwargs.update(
            {
                "voice_language": voice_language,
                "subtitle_language": subtitle_language,
                "transcript_language": transcript_language,
                "video_resolution": state.get("video_resolution", "hd"),
                "generate_avatar": generate_avatar,
                "generate_subtitles": generate_subtitles,
                "generate_video": generate_video,
                "generate_podcast": generate_podcast,
            }
        )
        task_config.update(task_kwargs)

        if isinstance(voice_id, str) and voice_id.strip():
            trimmed_voice = voice_id.strip()
            state["voice_id"] = trimmed_voice
            task_kwargs["voice_id"] = trimmed_voice
            task_config["voice_id"] = trimmed_voice
        elif not generate_video:
            state.pop("voice_id", None)
            task_kwargs.pop("voice_id", None)
            task_config.pop("voice_id", None)

        if isinstance(podcast_host_voice, str) and podcast_host_voice.strip():
            trimmed_host = podcast_host_voice.strip()
            state["podcast_host_voice"] = trimmed_host
            task_kwargs["podcast_host_voice"] = trimmed_host
            task_config["podcast_host_voice"] = trimmed_host
        elif not generate_podcast:
            state.pop("podcast_host_voice", None)
            task_kwargs.pop("podcast_host_voice", None)
            task_config.pop("podcast_host_voice", None)

        if isinstance(podcast_guest_voice, str) and podcast_guest_voice.strip():
            trimmed_guest = podcast_guest_voice.strip()
            state["podcast_guest_voice"] = trimmed_guest
            task_kwargs["podcast_guest_voice"] = trimmed_guest
            task_config["podcast_guest_voice"] = trimmed_guest
        elif not generate_podcast:
            state.pop("podcast_guest_voice", None)
            task_kwargs.pop("podcast_guest_voice", None)
            task_config.pop("podcast_guest_voice", None)

        # Update steps as needed
        steps = state.get("steps")
        if isinstance(steps, dict):
            if generate_podcast:
                steps.setdefault(
                    "generate_podcast_subtitles",
                    {"status": "pending", "data": None},
                )
            else:
                steps.pop("generate_podcast_subtitles", None)

        state["task_kwargs"] = task_kwargs
        state["task_config"] = task_config

        await state_manager.save_state(file_id, state)


async def _run_pdf_pipelines(
    *,
    file_id: str,
    file_path: Path,
    voice_language: str,
    subtitle_language: str | None,
    transcript_language: str | None,
    generate_subtitles: bool,
    generate_video: bool,
    generate_podcast: bool,
    task_id: str | None,
) -> None:
    logger.info(
        "PDF processing - generate_video: %s, generate_podcast: %s",
        generate_video,
        generate_podcast,
    )
    if generate_video:
        logger.info("Starting video pipeline for PDF file %s", file_id)
        await video_from_pdf(
            file_id,
            file_path,
            voice_language,
            subtitle_language,
            generate_subtitles,
            generate_video,
            task_id,
        )
    if generate_podcast:
        logger.info("Starting podcast pipeline for PDF file %s", file_id)
        await podcast_from_pdf(
            file_id,
            file_path,
            voice_language,
            transcript_language,
            task_id,
        )


async def _run_slide_pipeline(
    *,
    file_id: str,
    file_path: Path,
    file_ext: str,
    voice_language: str,
    subtitle_language: str | None,
    generate_avatar: bool,
    generate_subtitles: bool,
    generate_video: bool,
    task_id: str | None,
) -> None:
    await video_from_slide(
        file_id,
        file_path,
        file_ext,
        voice_language,
        subtitle_language,
        generate_avatar,
        generate_subtitles,
        generate_video,
        task_id,
    )
