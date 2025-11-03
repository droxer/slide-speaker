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

    # Select two voices for host/guest
    try:
        voices = ag.get_supported_voices(language) or []
        host_voice = voices[0] if len(voices) > 0 else "alloy"
        guest_voice = voices[1] if len(voices) > 1 else "onyx"
    except Exception:
        host_voice, guest_voice = "alloy", "onyx"
    logger.info(f"Selected voices for podcast: host={host_voice}, guest={guest_voice}")

    segment_paths: list[str] = []
    for idx, line in enumerate(dialogue, start=1):
        speaker = (line.get("speaker") or "Host").lower()
        text = (line.get("text") or "").strip()
        if not text:
            continue
        voice = host_voice if speaker.startswith("host") else guest_voice
        out_path = work_dir / f"segment_{idx:03d}.mp3"
        ok = await ag.generate_audio(
            text, str(out_path), language=language, voice=voice
        )
        if ok:
            segment_paths.append(str(out_path))

    # Do NOT upload per-segment MP3s for PDF podcasts; only final composed MP3 is stored
    uploaded_urls: list[str] = []

    await state_manager.update_step_status(
        file_id,
        "generate_podcast_audio",
        "completed",
        {
            "segments": segment_paths,
            "storage_urls": uploaded_urls,
            "host_voice": host_voice,
            "guest_voice": guest_voice,
            "dialogue": dialogue,
            "dialogue_language": language,
        },
    )
