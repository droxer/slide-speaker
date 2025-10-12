"""
Podcast pipeline coordinator (from PDF sources).

Generates a two-person conversation podcast based on PDF chapter segmentation.
"""

import json
import re
from contextlib import suppress
from pathlib import Path
from typing import Any

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.core.task_queue import task_queue

from ..helpers import (
    check_and_handle_cancellation,
    check_and_handle_failure,
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
    logger.info(
        f"_podcast_steps: target_transcript_language={target_transcript_language}, "
        f"fallback_voice_language={fallback_voice_language}, target={target}"
    )
    if target != "english":
        steps.append("translate_podcast_script")
        logger.info(f"Added translate_podcast_script step for target={target}")
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


def extract_podcast_dialogue_from_state(
    state: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Return sanitized podcast dialogue metadata from pipeline state."""
    if not state or "steps" not in state:
        logger.info("extract_podcast_dialogue_from_state: missing state or steps")
        return None

    steps = state["steps"]
    host_voice = None
    guest_voice = None
    target_language = (
        (
            state.get("podcast_transcript_language")
            or state.get("voice_language")
            or "english"
        )
        if isinstance(state, dict)
        else "english"
    )
    language = target_language

    # Prefer dialogue captured during audio generation
    audio_dialogue: list[dict[str, Any]] | None = None
    audio_dialogue_language: str | None = None
    source = "generate_podcast_audio"
    try:
        ga = steps.get("generate_podcast_audio") or {}
        ga_status = ga.get("status")
        ga_data = ga.get("data")
        if ga_status == "completed" and isinstance(ga_data, dict):
            host_voice = ga_data.get("host_voice")
            guest_voice = ga_data.get("guest_voice")
            dlg = ga_data.get("dialogue")
            lang = ga_data.get("dialogue_language")
            if isinstance(lang, str) and lang.strip():
                audio_dialogue_language = lang.strip().lower()
            if isinstance(dlg, list) and dlg:
                audio_dialogue = dlg
    except Exception:
        logger.info(
            "extract_podcast_dialogue_from_state: unable to read audio dialogue"
        )

    def sanitize(items: list[dict[str, Any]] | None) -> list[dict[str, str]]:
        sanitized: list[dict[str, str]] = []
        for item in items or []:
            if not isinstance(item, dict):
                continue
            speaker = str(item.get("speaker", "")).strip() or "Speaker"
            text = _strip_transition_label(item.get("text", ""))
            if not text:
                continue
            sanitized.append({"speaker": speaker, "text": text})
        return sanitized

    dialogue = sanitize(audio_dialogue)
    normalized_target = str(target_language or "english").strip().lower()
    if dialogue and (
        audio_dialogue_language is None
        or audio_dialogue_language == normalized_target
        or (
            normalized_target == "english"
            and (audio_dialogue_language or "english") == "english"
        )
    ):
        if audio_dialogue_language:
            language = audio_dialogue_language
        return {
            "dialogue": dialogue,
            "host_voice": host_voice,
            "guest_voice": guest_voice,
            "language": language,
            "source": source,
        }

    # Fallback to translated script or original English script
    fallback_step = None
    fallback_source = None
    fallback_language = language  # Default to the state-derived language

    logger.info("Extract_podcast_dialogue: Checking for translated script...")
    translated = steps.get("translate_podcast_script")
    if isinstance(translated, dict) and translated.get("status") == "completed":
        logger.info("Using translated script data")
        fallback_step = translated
        fallback_source = "translate_podcast_script"
        # If we have a translated script, the language should be the target translation language
        # which is stored in podcast_transcript_language or voice_language
        fallback_language = (
            state.get("podcast_transcript_language")
            or state.get("voice_language")
            or language
        )
    else:
        logger.info(
            "Translated script not found or not completed, checking for original English script..."
        )
        original = steps.get("generate_podcast_script")
        if isinstance(original, dict) and original.get("status") == "completed":
            logger.info("Using original English script data")
            fallback_step = original
            fallback_source = "generate_podcast_script"
            # If we're using the original script, it's always in English
            fallback_language = "english"
        else:
            logger.info("Original English script not found or not completed")

    if fallback_step:
        fallback_dialogue = fallback_step.get("data")
        sanitized_dialogue = sanitize(
            fallback_dialogue if isinstance(fallback_dialogue, list) else []
        )
        if sanitized_dialogue:
            return {
                "dialogue": sanitized_dialogue,
                "host_voice": host_voice,
                "guest_voice": guest_voice,
                "language": fallback_language,
                "source": fallback_source,
            }

    logger.info("extract_podcast_dialogue_from_state: no dialogue found")
    return None


def _build_podcast_conversation_markdown(
    state: dict[str, Any], task_id: str | None = None
) -> str | None:
    """Build podcast conversation markdown from state data."""
    logger.info(f"_build_podcast_conversation_markdown called with task_id: {task_id}")
    if not state or "steps" not in state:
        logger.info("No state or steps found")
        return None

    logger.info(f"Steps keys: {list(state['steps'].keys())}")
    payload = extract_podcast_dialogue_from_state(state)
    if not payload:
        logger.info("No payload extracted from state")
        return None

    logger.info(
        f"Extracted payload language: {payload.get('language')}, source: {payload.get('source')}"
    )

    data = payload.get("dialogue") or []
    host_voice = payload.get("host_voice")
    guest_voice = payload.get("guest_voice")

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
        if md_content:
            logger.info(f"Markdown content preview: {md_content[:200]}...")
        script_payload = extract_podcast_dialogue_from_state(state)
        logger.info(f"Script payload extracted: {script_payload is not None}")
        if script_payload:
            logger.info(
                f"Script payload language: {script_payload.get('language')}, "
                f"dialogue length: {len(script_payload.get('dialogue', []))}"
            )
        if not md_content and not script_payload:
            logger.debug(
                f"No podcast content generated for file_id: {file_id}; skipping storage save"
            )
            return

        storage_provider = get_storage_provider()
        # Use podcast-specific filename to avoid conflict with video transcripts
        base_id = task_id if isinstance(task_id, str) and task_id else file_id

        markdown_url = None
        if md_content:
            transcript_key = f"{base_id}_podcast_transcript.md"
            logger.info(f"Saving podcast transcript markdown key: {transcript_key}")
            markdown_url = storage_provider.upload_bytes(
                md_content.encode("utf-8"), transcript_key, "text/markdown"
            )

        script_url = None
        if script_payload and script_payload.get("dialogue"):
            script_key = f"{base_id}_podcast_script.json"
            logger.info(f"Saving podcast script JSON key: {script_key}")
            script_bytes = json.dumps(
                script_payload, ensure_ascii=False, separators=(",", ":")
            ).encode("utf-8")
            script_url = storage_provider.upload_bytes(
                script_bytes, script_key, "application/json"
            )

        # Save URLs to state for reference
        state = await state_manager.get_state(file_id)
        logger.info(f"State retrieved for saving storage URLs: {state is not None}")
        if state and "steps" in state:
            steps = state["steps"]
            pod_step = steps.get("generate_podcast_script")
            audio_step = steps.get("generate_podcast_audio")
            if pod_step and isinstance(pod_step, dict):
                if markdown_url:
                    pod_step["markdown_storage_url"] = markdown_url
                if script_url:
                    pod_step["script_storage_url"] = script_url
            if audio_step and isinstance(audio_step, dict):
                data = audio_step.get("data") or {}
                if isinstance(data, dict) and script_url:
                    data["script_storage_url"] = script_url
                    audio_step["data"] = data
            if pod_step or audio_step:
                await state_manager.save_state(file_id, state)

        if markdown_url:
            logger.info(f"Podcast transcript saved to storage: {markdown_url}")
        if script_url:
            logger.info(f"Podcast script JSON saved to storage: {script_url}")
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
    logger.info(f"Podcast steps order: {steps_order}")
    logger.info(
        f"transcript_language: {transcript_language}, voice_language: {voice_language}"
    )

    try:
        for step_name in steps_order:
            # Check for failure state before proceeding with any step
            if await check_and_handle_failure(file_id, step_name, task_id):
                logger.error(
                    f"Pipeline already failed before step {step_name}, exiting"
                )
                return
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
