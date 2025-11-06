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
    generate_podcast_subtitles_step,
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
    steps.extend(
        ["generate_podcast_audio", "generate_podcast_subtitles", "compose_podcast"]
    )
    return steps


def _podcast_step_name(step: str) -> str:
    base = {
        "generate_podcast_script": "Generating podcast script (two speakers)",
        "translate_podcast_script": "Translating podcast script",
        "generate_podcast_audio": "Generating podcast audio",
        "generate_podcast_subtitles": "Creating podcast subtitles",
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
    total_duration: float | None = None
    source = "generate_podcast_audio"
    try:
        ga = steps.get("generate_podcast_audio") or {}
        ga_status = ga.get("status")
        ga_data = ga.get("data")
        if ga_status == "completed" and isinstance(ga_data, dict):
            host_voice = ga_data.get("host_voice")
            guest_voice = ga_data.get("guest_voice")
            dlg = ga_data.get("dialogue")
            if (
                (not isinstance(dlg, list) or not dlg)
                and isinstance(ga_data.get("segment_metadata"), list)
                and ga_data["segment_metadata"]
            ):
                dlg = ga_data["segment_metadata"]
            lang = ga_data.get("dialogue_language")
            if isinstance(lang, str) and lang.strip():
                audio_dialogue_language = lang.strip().lower()
            if isinstance(dlg, list) and dlg:
                audio_dialogue = dlg
            td = ga_data.get("total_duration")
            if isinstance(td, int | float):
                total_duration = max(float(td), 0.0)
    except Exception:
        logger.info(
            "extract_podcast_dialogue_from_state: unable to read audio dialogue"
        )

    def sanitize(
        items: list[dict[str, Any]] | None,
        *,
        host_voice_fallback: str | None = None,
        guest_voice_fallback: str | None = None,
    ) -> tuple[list[dict[str, Any]], float]:
        sanitized: list[dict[str, Any]] = []
        timeline_cursor = 0.0
        latest_end = 0.0
        for item in items or []:
            if not isinstance(item, dict):
                continue
            speaker = str(item.get("speaker", "")).strip() or "Speaker"
            text = _strip_transition_label(item.get("text", ""))
            if not text:
                continue
            voice = item.get("voice")
            voice_str = (
                voice.strip() if isinstance(voice, str) and voice.strip() else None
            )

            normalized_speaker = speaker.lower()
            if not voice_str:
                if normalized_speaker.startswith("host") and host_voice_fallback:
                    voice_str = host_voice_fallback.strip()
                elif normalized_speaker.startswith("guest") and guest_voice_fallback:
                    voice_str = guest_voice_fallback.strip()

            start = item.get("start")
            end = item.get("end")
            duration = item.get("duration")

            start_val = float(start) if isinstance(start, int | float) else None
            end_val = float(end) if isinstance(end, int | float) else None
            duration_val = (
                float(duration) if isinstance(duration, int | float) else None
            )

            if duration_val is not None:
                duration_val = max(duration_val, 0.0)

            if start_val is None:
                start_val = timeline_cursor
            if end_val is None and duration_val is not None:
                end_val = start_val + duration_val
            if duration_val is None and end_val is not None:
                duration_val = max(end_val - start_val, 0.0)
            if duration_val is None:
                duration_val = 5.0
            if end_val is None:
                end_val = start_val + duration_val

            timeline_cursor = max(timeline_cursor, end_val)
            latest_end = max(latest_end, end_val)

            entry: dict[str, Any] = {
                "speaker": speaker,
                "text": text,
                "start": start_val,
                "end": end_val,
                "duration": duration_val,
            }
            if voice_str:
                entry["voice"] = voice_str
            segment_file = item.get("segment_file")
            if isinstance(segment_file, str) and segment_file.strip():
                entry["segment_file"] = segment_file.strip()
            sanitized.append(entry)
        return sanitized, latest_end

    dialogue = sanitize(
        audio_dialogue,
        host_voice_fallback=host_voice if isinstance(host_voice, str) else None,
        guest_voice_fallback=guest_voice if isinstance(guest_voice, str) else None,
    )
    dialogue_items, audio_total = dialogue
    normalized_target = str(target_language or "english").strip().lower()
    if dialogue_items and (
        audio_dialogue_language is None
        or audio_dialogue_language == normalized_target
        or (
            normalized_target == "english"
            and (audio_dialogue_language or "english") == "english"
        )
    ):
        if total_duration is None:
            total_duration = audio_total
        if audio_dialogue_language:
            language = audio_dialogue_language
        return {
            "dialogue": dialogue_items,
            "host_voice": host_voice,
            "guest_voice": guest_voice,
            "language": language,
            "source": source,
            "total_duration": total_duration,
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
        sanitized_dialogue, fallback_total = sanitize(
            fallback_dialogue if isinstance(fallback_dialogue, list) else [],
            host_voice_fallback=host_voice if isinstance(host_voice, str) else None,
            guest_voice_fallback=guest_voice if isinstance(guest_voice, str) else None,
        )
        if sanitized_dialogue:
            return {
                "dialogue": sanitized_dialogue,
                "host_voice": host_voice,
                "guest_voice": guest_voice,
                "language": fallback_language,
                "source": fallback_source,
                "total_duration": fallback_total or None,
            }

    logger.info("extract_podcast_dialogue_from_state: no dialogue found")
    return None


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

        script_payload = extract_podcast_dialogue_from_state(state)
        logger.info(f"Script payload extracted: {script_payload is not None}")
        if script_payload:
            logger.info(
                f"Script payload language: {script_payload.get('language')}, "
                f"dialogue length: {len(script_payload.get('dialogue', []))}"
            )
        if not script_payload:
            logger.debug(
                f"No podcast content generated for file_id: {file_id}; skipping storage save"
            )
            return

        storage_provider = get_storage_provider()
        # Use podcast-specific filename to avoid conflict with video transcripts
        base_id = task_id if isinstance(task_id, str) and task_id else file_id

        script_url = None
        vtt_url = None
        srt_url = None
        vtt_local_path = None
        srt_local_path = None

        subtitles_step = (
            state.get("steps", {}).get("generate_podcast_subtitles")
            if isinstance(state, dict)
            else None
        )
        subtitles_data = (
            subtitles_step.get("data")
            if isinstance(subtitles_step, dict)
            and isinstance(subtitles_step.get("data"), dict)
            else None
        )
        if subtitles_data:
            for candidate in subtitles_data.get("storage_urls") or []:
                if isinstance(candidate, str):
                    if candidate.endswith(".vtt"):
                        vtt_url = candidate
                    elif candidate.endswith(".srt"):
                        srt_url = candidate
            for candidate in subtitles_data.get("subtitle_files") or []:
                if isinstance(candidate, str):
                    if candidate.endswith(".vtt") and not vtt_local_path:
                        vtt_local_path = candidate
                    elif candidate.endswith(".srt") and not srt_local_path:
                        srt_local_path = candidate

        if script_payload and script_payload.get("dialogue"):
            script_key = f"{base_id}_podcast_script.json"
            logger.info(f"Saving podcast script JSON key: {script_key}")
            script_bytes = json.dumps(
                script_payload, ensure_ascii=False, separators=(",", ":")
            ).encode("utf-8")
            script_url = storage_provider.upload_bytes(
                script_bytes, script_key, "application/json"
            )
            if not vtt_url and vtt_local_path:
                try:
                    vtt_key = f"{base_id}_podcast_transcript.vtt"
                    logger.info(
                        "Storing podcast transcript VTT using existing subtitle file: %s",
                        vtt_local_path,
                    )
                    vtt_url = storage_provider.upload_file(
                        str(vtt_local_path), vtt_key, "text/vtt"
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.error(
                        "Failed to publish podcast VTT transcript from subtitles: %s",
                        exc,
                    )

        # Save URLs to state for reference
        state = await state_manager.get_state(file_id)
        logger.info(f"State retrieved for saving storage URLs: {state is not None}")
        if state and "steps" in state:
            steps = state["steps"]
            pod_step = steps.get("generate_podcast_script")
            audio_step = steps.get("generate_podcast_audio")
            if pod_step and isinstance(pod_step, dict):
                if script_url:
                    pod_step["script_storage_url"] = script_url
                if vtt_url:
                    pod_step["vtt_storage_url"] = vtt_url
                if srt_url:
                    pod_step["srt_storage_url"] = srt_url
            if audio_step and isinstance(audio_step, dict):
                data = audio_step.get("data") or {}
                if isinstance(data, dict):
                    if script_url:
                        data["script_storage_url"] = script_url
                    if vtt_url:
                        data["vtt_storage_url"] = vtt_url
                    if srt_url:
                        data["srt_storage_url"] = srt_url
                    subtitles_payload = dict(data.get("subtitles") or {})
                    if vtt_url or vtt_local_path:
                        subtitles_payload["vtt"] = vtt_url or vtt_local_path
                    if srt_url or srt_local_path:
                        subtitles_payload["srt"] = srt_url or srt_local_path
                    if subtitles_payload:
                        data["subtitles"] = subtitles_payload
                    audio_step["data"] = data
            if pod_step or audio_step:
                await state_manager.save_state(file_id, state)

        if script_url:
            logger.info(f"Podcast script JSON saved to storage: {script_url}")
        if vtt_url:
            logger.info(f"Podcast transcript VTT available at: {vtt_url}")
        if srt_url:
            logger.info(f"Podcast transcript SRT available at: {srt_url}")
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
            elif step_name == "generate_podcast_subtitles":
                await generate_podcast_subtitles_step(file_id)
            elif step_name == "compose_podcast":
                await compose_podcast_step(file_id)

            # Do not overwrite step outputs here; each step is responsible
            # for marking its own completion and persisting data.

        # Save podcast transcript to storage
        logger.info(
            f"Calling _save_podcast_transcript_to_storage with file_id: {file_id}, task_id: {task_id}"
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
