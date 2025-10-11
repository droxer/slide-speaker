"""
Podcast pipeline coordinator (from PDF sources).

Generates a two-person conversation podcast based on PDF chapter segmentation.
"""

import re
from contextlib import suppress
from pathlib import Path
from typing import Any

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.core.task_queue import task_queue

from ..helpers import (
    check_and_handle_cancellation,
    fetch_step_state,
    set_step_status_processing,
)
from ..steps.podcast.pdf import (
    compose_podcast_step,
    generate_podcast_audio_step,
    generate_podcast_script_step,
    translate_podcast_script_step,
)
from ..steps.video.pdf import segment_content_step as pdf_segment_content_step


def _podcast_steps(
    target_transcript_language: str | None, fallback_voice_language: str
) -> list[str]:
    """Determine ordered steps for podcast pipeline.

    Always generate the script in English first. Include a translation step when the
    desired transcript language (transcript_language if provided, else voice_language)
    differs from English. Then generate the audio using the voice language and compose.
    """
    steps: list[str] = ["generate_podcast_script"]
    target = (
        target_transcript_language or fallback_voice_language or "english"
    ).lower()
    if target != "english":
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


def _strip_transition_label(text: str) -> str:
    t = str(text or "").strip()
    t = re.sub(r"^(transition)\s*[:\-—–]\s*", "", t, flags=re.IGNORECASE)
    return t.strip()


def _build_podcast_conversation_markdown(
    state: dict[str, Any], task_id: str | None = None
) -> str | None:
    """Build podcast conversation markdown from state data."""
    logger.info(f"_build_podcast_conversation_markdown called with task_id: {task_id}")
    if not state or "steps" not in state:
        logger.info("No state or steps found")
        return None

    steps = state["steps"]
    logger.info(f"Steps keys: {list(steps.keys())}")
    # Prefer translated podcast script when present; fallback to original
    pod_translated = steps.get("translate_podcast_script")
    pod_original = steps.get("generate_podcast_script")
    logger.info(f"translate_podcast_script step: {pod_translated}")
    logger.info(f"generate_podcast_script step: {pod_original}")
    chosen = None
    if pod_translated and pod_translated.get("status") == "completed":
        chosen = pod_translated
    elif pod_original and pod_original.get("status") == "completed":
        chosen = pod_original
    if not chosen:
        logger.info("No completed podcast script (translated or original) found")
        return None

    data = chosen.get("data") or []
    logger.info(f"Podcast data: {data}")
    if not isinstance(data, list) or not data:
        logger.info("Podcast data is not a list or is empty")
        return None

    # Try to fetch voices from podcast audio step
    host_voice = None
    guest_voice = None
    try:
        ga = steps.get("generate_podcast_audio") or {}
        if (ga.get("status") == "completed") and isinstance(ga.get("data"), dict):
            host_voice = (
                (ga["data"].get("host_voice") or None)
                if isinstance(ga["data"], dict)
                else None
            )
            guest_voice = (
                (ga["data"].get("guest_voice") or None)
                if isinstance(ga["data"], dict)
                else None
            )
    except Exception:
        pass

    # Build conversation-style Markdown
    lines: list[str] = ["# Podcast Conversation\n"]
    for item in data:
        if isinstance(item, dict):
            raw_speaker = str(item.get("speaker", "")).strip().lower()
            speaker_label = "Speaker"
            if raw_speaker.startswith("host"):
                # Prefer VoiceId first, then Role; both capitalized
                speaker_label = (
                    f"{str(host_voice).strip().title()} (Host)"
                    if host_voice
                    else "Host"
                )
            elif raw_speaker.startswith("guest"):
                speaker_label = (
                    f"{str(guest_voice).strip().title()} (Guest)"
                    if guest_voice
                    else "Guest"
                )
            else:
                # Fallback to provided speaker label, title-cased
                speaker_label = item.get("speaker") or "Speaker"
                speaker_label = str(speaker_label).strip().title()
            text = _strip_transition_label(item.get("text", ""))
            if text:
                lines.append(f"**{speaker_label}:** {text}")

    return "\n\n".join(lines).strip() + "\n"


async def _save_podcast_transcript_to_storage(
    file_id: str, task_id: str | None = None
) -> None:
    """Save podcast transcript to storage with task_id naming."""
    logger.info(
        f"_save_podcast_transcript_to_storage called with file_id: {file_id}, task_id: {task_id}"
    )
    try:
        from slidespeaker.configs.config import get_storage_provider

        state = await state_manager.get_state(file_id)
        logger.info(f"State retrieved: {state is not None}")
        if not state:
            logger.debug(f"No state found for file_id: {file_id}")
            return

        md_content = _build_podcast_conversation_markdown(state, task_id)
        logger.info(f"Markdown content generated: {md_content is not None}")
        if not md_content:
            logger.debug(f"No markdown content generated for file_id: {file_id}")
            return

        storage_provider = get_storage_provider()
        # Use podcast-specific filename to avoid conflict with video transcripts
        base_id = task_id if isinstance(task_id, str) and task_id else file_id
        object_key = f"{base_id}_podcast_transcript.md"
        logger.info(
            f"Saving podcast transcript with base_id: {base_id}, object_key: {object_key}"
        )
        url = storage_provider.upload_bytes(
            md_content.encode("utf-8"), object_key, "text/markdown"
        )

        # Save URL to state
        state = await state_manager.get_state(file_id)
        logger.info(f"State retrieved for saving URL: {state is not None}")
        if state and "steps" in state:
            steps = state["steps"]
            logger.info(f"Steps in state: {list(steps.keys())}")
            pod_step = steps.get("generate_podcast_script")
            logger.info(f"generate_podcast_script step for saving URL: {pod_step}")
            if pod_step and isinstance(pod_step, dict):
                logger.info(
                    "Saving markdown_storage_url to generate_podcast_script step"
                )
                pod_step["markdown_storage_url"] = url
                await state_manager.save_state(file_id, state)
            else:
                logger.info(
                    f"generate_podcast_script step not found or not dict: {pod_step}"
                )

        logger.info(f"Podcast transcript saved to storage: {url}")
    except Exception as e:
        logger.error(f"Failed to save podcast transcript to storage: {e}")
        logger.exception(e)


async def from_pdf(
    file_id: str,
    file_path: Path,
    voice_language: str = "english",
    transcript_language: str | None = None,
    task_id: str | None = None,
) -> None:
    logger.info(f"Starting podcast generation (PDF) for file {file_id}")
    logger.info(f"Task ID: {task_id}")
    logger.info(f"Task ID type: {type(task_id)}")
    logger.info(f"Task ID is valid string: {isinstance(task_id, str) and task_id}")

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

    steps_order = _podcast_steps(transcript_language, voice_language)

    try:
        for step_name in steps_order:
            if await check_and_handle_cancellation(file_id, step_name, task_id):
                return

            st = await fetch_step_state(file_id, step_name)
            if st and st.get("status") == "completed":
                logger.info(f"Skipping already completed step: {step_name}")
                continue

            await set_step_status_processing(file_id, step_name, task_id)
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

            # Do not overwrite step outputs here; each step is responsible
            # for marking its own completion and persisting data.

        # Save podcast transcript to storage
        logger.info(
            f"Calling _save_podcast_transcript_to_storage with file_id: {file_id}, task_id: {task_id}"
        )
        logger.info(f"Task ID at save time: {task_id}")
        logger.info(f"Task ID type at save time: {type(task_id)}")
        logger.info(
            f"Task ID is valid string at save time: {isinstance(task_id, str) and task_id}"
        )
        await _save_podcast_transcript_to_storage(file_id, task_id)

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
