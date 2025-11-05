"""
Generate podcast subtitle artifacts (SRT/VTT) based on timed dialogue metadata.
"""

from __future__ import annotations

import math
from typing import Any

from loguru import logger

from slidespeaker.configs.config import config, get_storage_provider
from slidespeaker.core.state_manager import state_manager
from slidespeaker.storage.paths import output_storage_uri


def _clean_voice(value: Any) -> str | None:
    if isinstance(value, str):
        trimmed = value.strip()
        if trimmed:
            return trimmed
    return None


def _seconds_to_srt_ts(value: float) -> str:
    total_ms = max(int(round(value * 1000)), 0)
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, millis = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def _seconds_to_vtt_ts(value: float) -> str:
    total_ms = max(int(round(value * 1000)), 0)
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, millis = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def _normalize_dialogue_entry(
    entry: dict[str, Any],
    host_voice: str | None,
    guest_voice: str | None,
) -> dict[str, Any] | None:
    text = _clean_voice(entry.get("text")) or str(entry.get("text") or "").strip()
    if not text:
        return None
    speaker = str(entry.get("speaker") or "").strip() or "Speaker"
    voice = _clean_voice(entry.get("voice"))
    normalized = speaker.lower()
    if not voice:
        if normalized.startswith("host") and host_voice:
            voice = host_voice
        elif normalized.startswith("guest") and guest_voice:
            voice = guest_voice
    label = voice or speaker
    start = entry.get("start")
    end = entry.get("end")
    duration = entry.get("duration")
    start_seconds = float(start) if isinstance(start, int | float) else None
    end_seconds = float(end) if isinstance(end, int | float) else None
    duration_seconds = float(duration) if isinstance(duration, int | float) else None
    if start_seconds is None:
        start_seconds = 0.0
    if math.isnan(start_seconds) or start_seconds < 0:
        start_seconds = 0.0
    if end_seconds is None and duration_seconds is not None:
        end_seconds = start_seconds + max(duration_seconds, 0.5)
    if end_seconds is None:
        # Default to 5 seconds if no timing hint available.
        end_seconds = start_seconds + max(duration_seconds or 5.0, 0.5)
    if end_seconds <= start_seconds:
        end_seconds = start_seconds + max(duration_seconds or 1.0, 0.5)
    normalized_entry = {
        "label": label,
        "text": text,
        "start": start_seconds,
        "end": end_seconds,
        "speaker": speaker,
    }
    if voice:
        normalized_entry["voice"] = voice
    return normalized_entry


def _render_srt(dialogue: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for idx, item in enumerate(dialogue, start=1):
        start_ts = _seconds_to_srt_ts(item["start"])
        end_ts = _seconds_to_srt_ts(item["end"])
        lines.append(f"{idx}")
        lines.append(f"{start_ts} --> {end_ts}")
        lines.append(f"{item['label']}: {item['text']}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _render_vtt(dialogue: list[dict[str, Any]]) -> str:
    lines: list[str] = ["WEBVTT", ""]
    for idx, item in enumerate(dialogue, start=1):
        start_ts = _seconds_to_vtt_ts(item["start"])
        end_ts = _seconds_to_vtt_ts(item["end"])
        lines.append(f"{idx}")
        lines.append(f"{start_ts} --> {end_ts}")
        lines.append(f"{item['label']}: {item['text']}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


async def generate_podcast_subtitles_step(file_id: str) -> None:
    await state_manager.update_step_status(
        file_id, "generate_podcast_subtitles", "processing"
    )
    logger.info(f"Generating podcast subtitles for file {file_id}")

    state = await state_manager.get_state(file_id)
    if not state or "steps" not in state:
        logger.warning(
            "State missing or malformed when generating podcast subtitles for %s",
            file_id,
        )
        await state_manager.update_step_status(
            file_id,
            "generate_podcast_subtitles",
            "completed",
            {"subtitle_files": [], "storage_urls": []},
        )
        return

    steps = state["steps"]
    subtitle_language: str | None = None
    transcript_dialogue: list[dict[str, Any]] = []

    if isinstance(state, dict):
        for candidate in (
            state.get("podcast_transcript_language"),
            state.get("subtitle_language"),
            state.get("voice_language"),
        ):
            if isinstance(candidate, str) and candidate.strip():
                subtitle_language = candidate.strip()
                break

    if isinstance(steps, dict):
        translation_step = steps.get("translate_podcast_script")
        if (
            isinstance(translation_step, dict)
            and translation_step.get("status") == "completed"
            and isinstance(translation_step.get("data"), list)
        ):
            transcript_dialogue = [
                {
                    "speaker": str(item.get("speaker") or "").strip(),
                    "text": str(item.get("text") or "").strip(),
                }
                for item in translation_step.get("data") or []
                if isinstance(item, dict)
            ]

        if not transcript_dialogue:
            script_step = steps.get("generate_podcast_script")
            if (
                isinstance(script_step, dict)
                and script_step.get("status") == "completed"
                and isinstance(script_step.get("data"), list)
            ):
                transcript_dialogue = [
                    {
                        "speaker": str(item.get("speaker") or "").strip(),
                        "text": str(item.get("text") or "").strip(),
                    }
                    for item in script_step.get("data") or []
                    if isinstance(item, dict)
                ]

    if not subtitle_language:
        subtitle_language = "english"

    audio_step = (
        steps.get("generate_podcast_audio") if isinstance(steps, dict) else None
    )
    dialogue_items: list[dict[str, Any]] = []
    host_voice = None
    guest_voice = None

    if isinstance(audio_step, dict):
        audio_data = (
            audio_step.get("data") if isinstance(audio_step.get("data"), dict) else {}
        )
        host_voice = _clean_voice(audio_data.get("host_voice"))
        guest_voice = _clean_voice(audio_data.get("guest_voice"))
        if isinstance(audio_data.get("dialogue"), list) and audio_data["dialogue"]:
            dialogue_items = list(audio_data["dialogue"])
        elif (
            isinstance(audio_data.get("segment_metadata"), list)
            and audio_data["segment_metadata"]
        ):
            dialogue_items = list(audio_data["segment_metadata"])

    if not dialogue_items:
        logger.warning(
            "No audio dialogue metadata available for podcast subtitles (file_id=%s)",
            file_id,
        )
        await state_manager.update_step_status(
            file_id,
            "generate_podcast_subtitles",
            "completed",
            {"subtitle_files": [], "storage_urls": []},
        )
        return

    if host_voice is None:
        host_voice = _clean_voice(state.get("podcast_host_voice"))
    if guest_voice is None:
        guest_voice = _clean_voice(state.get("podcast_guest_voice"))

    normalized_dialogue: list[dict[str, Any]] = []
    for entry in dialogue_items:
        if not isinstance(entry, dict):
            continue
        normalized = _normalize_dialogue_entry(entry, host_voice, guest_voice)
        if normalized:
            normalized_dialogue.append(normalized)

    if not normalized_dialogue:
        logger.warning(
            "Dialogue entries could not be normalized for podcast subtitles (file_id=%s)",
            file_id,
        )
        await state_manager.update_step_status(
            file_id,
            "generate_podcast_subtitles",
            "completed",
            {"subtitle_files": [], "storage_urls": []},
        )
        return

    if transcript_dialogue:
        min_len = min(len(normalized_dialogue), len(transcript_dialogue))
        for idx in range(min_len):
            transcript_entry = transcript_dialogue[idx]
            text_value = transcript_entry.get("text")
            if isinstance(text_value, str) and text_value.strip():
                normalized_dialogue[idx]["text"] = text_value.strip()
            speaker_value = transcript_entry.get("speaker")
            if isinstance(speaker_value, str) and speaker_value.strip():
                normalized_dialogue[idx]["speaker"] = speaker_value.strip()
        if len(transcript_dialogue) != len(normalized_dialogue):
            logger.warning(
                "Podcast subtitle dialogue length mismatch for %s: transcript=%s, timed=%s",
                file_id,
                len(transcript_dialogue),
                len(normalized_dialogue),
            )

    work_dir = config.output_dir / file_id / "podcast" / "subtitles"
    work_dir.mkdir(parents=True, exist_ok=True)

    srt_path = work_dir / "dialogue.srt"
    vtt_path = work_dir / "dialogue.vtt"

    srt_body = _render_srt(normalized_dialogue)
    vtt_body = _render_vtt(normalized_dialogue)

    srt_path.write_text(srt_body, encoding="utf-8")
    vtt_path.write_text(vtt_body, encoding="utf-8")

    storage_provider = get_storage_provider()
    state_snapshot = await state_manager.get_state(file_id)

    _, srt_key, srt_uri = output_storage_uri(
        file_id,
        state=state_snapshot if isinstance(state_snapshot, dict) else None,
        segments=("podcast", "subtitles", "dialogue.srt"),
    )
    _, vtt_key, vtt_uri = output_storage_uri(
        file_id,
        state=state_snapshot if isinstance(state_snapshot, dict) else None,
        segments=("podcast", "subtitles", "dialogue.vtt"),
    )

    subtitle_urls: list[str] = []
    storage_keys: list[str] = []
    storage_uris: list[str] = []

    try:
        srt_url = storage_provider.upload_file(str(srt_path), srt_key, "text/plain")
        vtt_url = storage_provider.upload_file(str(vtt_path), vtt_key, "text/vtt")
        subtitle_urls.extend([srt_url, vtt_url])
        storage_keys.extend([srt_key, vtt_key])
        storage_uris.extend([srt_uri, vtt_uri])
        logger.info(
            "Uploaded podcast subtitles for %s: %s, %s", file_id, srt_url, vtt_url
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to upload podcast subtitles for {file_id}: {exc}")
        if config.storage_provider != "local":
            await state_manager.update_step_status(
                file_id,
                "generate_podcast_subtitles",
                "failed",
                {
                    "error": "podcast_subtitle_upload_failed",
                    "detail": str(exc),
                    "storage_keys": {"srt": srt_key, "vtt": vtt_key},
                },
            )
            raise
        subtitle_urls = [str(srt_path), str(vtt_path)]

    step_data = {
        "subtitle_files": [str(srt_path), str(vtt_path)],
        "storage_urls": subtitle_urls,
        "storage_keys": storage_keys,
        "storage_uris": storage_uris,
        "dialogue_entries": normalized_dialogue,
        "subtitle_language": subtitle_language,
    }

    await state_manager.update_step_status(
        file_id, "generate_podcast_subtitles", "completed", step_data
    )

    if state_snapshot and isinstance(state_snapshot, dict):
        artifacts = dict(state_snapshot.get("artifacts") or {})
        podcast_artifacts = dict(artifacts.get("podcast") or {})
        podcast_artifacts["subtitles"] = {
            "srt": {
                "local_path": str(srt_path),
                "storage_key": storage_keys[0] if storage_keys else None,
                "storage_uri": storage_uris[0] if storage_uris else None,
            },
            "vtt": {
                "local_path": str(vtt_path),
                "storage_key": storage_keys[1] if len(storage_keys) > 1 else None,
                "storage_uri": storage_uris[1] if len(storage_uris) > 1 else None,
            },
        }
        artifacts["podcast"] = podcast_artifacts
        state_snapshot["artifacts"] = artifacts
        await state_manager.save_state(file_id, state_snapshot)

    logger.info("Podcast subtitles generated successfully for %s", file_id)
