"""
Generate podcast audio segments (Host/Guest) from dialogue.

Emits per-line MP3 segments and optionally uploads them via storage provider.
"""

from loguru import logger

from slidespeaker.audio.generator import AudioGenerator
from slidespeaker.configs.config import config
from slidespeaker.core.state_manager import state_manager


async def generate_podcast_audio_step(file_id: str, language: str = "english") -> None:
    await state_manager.update_step_status(
        file_id, "generate_podcast_audio", "processing"
    )
    logger.info(f"Generating podcast audio for file {file_id}")

    ag = AudioGenerator()
    st = await state_manager.get_state(file_id)
    dialogue: list[dict[str, str]] = []
    transcript_lang = None
    if st and st.get("steps"):
        steps = st["steps"]
        # Base script is always English
        base_dialogue: list[dict[str, str]] = []
        if steps.get("generate_podcast_script") and steps[
            "generate_podcast_script"
        ].get("data"):
            base_dialogue = steps["generate_podcast_script"].get("data") or []
        # Existing translated transcript (might be in transcript language)
        translated_dialogue: list[dict[str, str]] = []
        if steps.get("translate_podcast_script") and steps[
            "translate_podcast_script"
        ].get("data"):
            translated_dialogue = steps["translate_podcast_script"].get("data") or []
        transcript_lang = (
            st.get("podcast_transcript_language")
            or st.get("subtitle_language")
            or st.get("voice_language")
            or "english"
        ).lower()

        # Prepare dialogue strictly for the audio (voice) language via AudioGenerator utilities
        dialogue = ag.prepare_dialogue_for_audio(
            base_dialogue_en=base_dialogue,
            translated_dialogue=translated_dialogue,
            transcript_language=transcript_lang,
            voice_language=language,
        )

    if not dialogue:
        logger.warning("No podcast dialogue found; skipping audio generation")
        await state_manager.update_step_status(
            file_id,
            "generate_podcast_audio",
            "completed",
            {
                "segments": [],
                "storage_urls": [],
                "host_voice": None,
                "guest_voice": None,
                "dialogue": [],
                "dialogue_language": language,
            },
        )
        return

    work_dir = config.output_dir / file_id / "podcast"
    work_dir.mkdir(parents=True, exist_ok=True)

    def _clean_voice(value: object) -> str | None:
        if isinstance(value, str):
            trimmed = value.strip()
            return trimmed or None
        return None

    preferred_host = _clean_voice(st.get("podcast_host_voice") if st else None)
    preferred_guest = _clean_voice(st.get("podcast_guest_voice") if st else None)
    if (not preferred_host or not preferred_guest) and st:
        task_config = st.get("task_config")
        if isinstance(task_config, dict):
            if not preferred_host:
                preferred_host = _clean_voice(task_config.get("podcast_host_voice"))
            if not preferred_guest:
                preferred_guest = _clean_voice(task_config.get("podcast_guest_voice"))
        task_kwargs = st.get("task_kwargs")
        if isinstance(task_kwargs, dict):
            if not preferred_host:
                preferred_host = _clean_voice(task_kwargs.get("podcast_host_voice"))
            if not preferred_guest:
                preferred_guest = _clean_voice(task_kwargs.get("podcast_guest_voice"))

    # Select two voices for host/guest
    try:
        voices = ag.get_supported_voices(language) or []
    except Exception:
        voices = []
    host_voice = preferred_host or (voices[0] if len(voices) > 0 else "alloy")
    guest_voice = preferred_guest or (
        voices[1] if len(voices) > 1 else ("onyx" if host_voice != "onyx" else "alloy")
    )

    if host_voice == guest_voice and voices:
        for candidate in voices:
            if candidate != host_voice:
                guest_voice = candidate
                break

    logger.info(f"Selected voices for podcast: host={host_voice}, guest={guest_voice}")

    segment_paths: list[str] = []
    segment_metadata: list[dict[str, object]] = []
    timed_dialogue: list[dict[str, object]] = []
    cumulative_start = 0.0

    def _duration_fallback(content: str) -> float:
        # Approximate speech rate (around 150 words per minute).
        words = max(len(content.split()), 1)
        approx = words / 2.5
        return max(approx, 2.0)

    for idx, line in enumerate(dialogue, start=1):
        raw_speaker = (line.get("speaker") or "Host").strip()
        text = (line.get("text") or "").strip()
        if not text:
            continue

        normalized = raw_speaker.lower()
        speaker_label = (
            "Host"
            if normalized.startswith("host")
            else (
                "Guest" if normalized.startswith("guest") else raw_speaker or "Speaker"
            )
        )
        voice = host_voice if normalized.startswith("host") else guest_voice
        out_path = work_dir / f"segment_{idx:03d}.mp3"
        ok = await ag.generate_audio(
            text, str(out_path), language=language, voice=voice
        )
        if not ok:
            continue

        duration = float(ag._get_audio_duration(out_path))  # noqa: SLF001 - internal helper
        if duration <= 0:
            duration = _duration_fallback(text)

        start_time = cumulative_start
        end_time = start_time + duration
        cumulative_start = end_time

        segment_paths.append(str(out_path))
        segment_metadata.append(
            {
                "segment_file": str(out_path),
                "voice": voice,
                "speaker": speaker_label,
                "start": start_time,
                "end": end_time,
                "duration": duration,
            }
        )
        timed_dialogue.append(
            {
                "speaker": speaker_label,
                "text": text,
                "voice": voice,
                "start": start_time,
                "end": end_time,
                "duration": duration,
                "segment_file": str(out_path),
            }
        )

    # Do NOT upload per-segment MP3s for PDF podcasts; only final composed MP3 is stored
    uploaded_urls: list[str] = []

    await state_manager.update_step_status(
        file_id,
        "generate_podcast_audio",
        "completed",
        {
            "segments": segment_paths,
            "segment_metadata": segment_metadata,
            "storage_urls": uploaded_urls,
            "host_voice": host_voice,
            "guest_voice": guest_voice,
            "dialogue": timed_dialogue,
            "dialogue_language": language,
            "total_duration": cumulative_start,
        },
    )
