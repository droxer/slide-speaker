"""
Generate podcast audio segments (Host/Guest) from dialogue.

Emits per-line MP3 segments and optionally uploads them via storage provider.
"""

from pathlib import Path

from loguru import logger

from slidespeaker.audio.generator import AudioGenerator
from slidespeaker.configs.config import config, get_storage_provider
from slidespeaker.core.state_manager import state_manager


async def generate_podcast_audio_step(file_id: str, language: str = "english") -> None:
    await state_manager.update_step_status(
        file_id, "generate_podcast_audio", "processing"
    )
    logger.info(f"Generating podcast audio for file {file_id}")

    st = await state_manager.get_state(file_id)
    dialogue: list[dict[str, str]] = []
    if st and st.get("steps"):
        if st["steps"].get("translate_podcast_script") and st["steps"][
            "translate_podcast_script"
        ].get("data"):
            dialogue = st["steps"]["translate_podcast_script"]["data"] or []
        elif st["steps"].get("generate_podcast_script") and st["steps"][
            "generate_podcast_script"
        ].get("data"):
            dialogue = st["steps"]["generate_podcast_script"].get("data") or []

    if not dialogue:
        logger.warning("No podcast dialogue found; skipping audio generation")
        await state_manager.update_step_status(
            file_id, "generate_podcast_audio", "completed", []
        )
        return

    work_dir = config.output_dir / file_id / "podcast"
    work_dir.mkdir(parents=True, exist_ok=True)

    ag = AudioGenerator()
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

    # Optionally upload segments
    uploaded_urls: list[str] = []
    try:
        sp = get_storage_provider()
        for p in segment_paths:
            key = f"{file_id}_podcast_segment_{Path(p).name}"
            url = sp.upload_file(p, key, "audio/mpeg")
            uploaded_urls.append(url)
    except Exception:
        pass

    await state_manager.update_step_status(
        file_id,
        "generate_podcast_audio",
        "completed",
        {
            "segments": segment_paths,
            "storage_urls": uploaded_urls,
            "host_voice": host_voice,
            "guest_voice": guest_voice,
        },
    )
