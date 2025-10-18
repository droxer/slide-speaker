"""
Shared audio generation logic for SlideSpeaker pipeline steps.

This module provides common functionality for generating audio from transcripts
in both PDF and presentation slide processing pipelines.
"""

from collections.abc import Callable
from typing import Any

from loguru import logger

from slidespeaker.audio import AudioGenerator
from slidespeaker.configs.config import config, get_storage_provider
from slidespeaker.core.state_manager import state_manager
from slidespeaker.storage.paths import output_storage_uri


async def generate_audio_common(
    file_id: str,
    state_key: str,
    get_transcripts_func: Callable[[str], Any],
    is_pdf: bool = False,
) -> None:
    """
    Generate audio from transcripts using shared logic.

    Args:
        file_id: Unique identifier for the file
        state_key: State key to update (e.g., "generate_audio" or "generate_pdf_audio")
        get_transcripts_func: Function to retrieve transcripts data
        is_pdf: Whether this is for PDF processing

    Raises:
        ValueError: If no transcripts data is available
    """
    await state_manager.update_step_status(file_id, state_key, "processing")
    logger.info(f"Starting audio generation for file: {file_id}")

    # Get transcripts data
    transcripts = await get_transcripts_func(file_id)

    if not transcripts:
        raise ValueError("No transcripts data available for audio generation")

    # Prepare intermediate audio directory
    audio_dir = config.output_dir / file_id / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    audio_files = []
    audio_generator = AudioGenerator()

    # Determine default language from state (voice_language), fallback to English
    state = await state_manager.get_state(file_id)
    default_language = "english"
    if state and isinstance(state, dict):
        default_language = str(state.get("voice_language", default_language))

    for i, transcript_data in enumerate(transcripts):
        # Additional null check for individual transcript data
        if transcript_data and isinstance(transcript_data, dict):
            script_text = str(transcript_data.get("script", "") or "")
            if script_text.strip():
                try:
                    # Determine language and voice
                    language = str(transcript_data.get("language") or default_language)
                    file_prefix = "chapter" if is_pdf else "slide"

                    # Get appropriate voice for the language
                    voices = audio_generator.get_supported_voices(language)
                    voice = voices[0] if voices else None

                    # Generate audio
                    logger.info(
                        f"Generating TTS for {file_prefix} {i + 1}: language={language}, voice={voice}"
                    )
                    audio_path = audio_dir / f"{file_prefix}_{i + 1}.mp3"
                    ok = await audio_generator.generate_audio(
                        script_text, str(audio_path), language=language, voice=voice
                    )

                    if ok and audio_path.exists() and audio_path.stat().st_size > 0:
                        # Keep audio files local - only final files should be uploaded to cloud storage
                        audio_files.append(str(audio_path))
                        logger.info(
                            f"Generated audio for {file_prefix} {i + 1}: {audio_path}"
                        )
                    else:
                        logger.error(
                            f"Audio generation failed for {file_prefix} {i + 1}; skipping file"
                        )
                except Exception as e:
                    logger.error(
                        f"Failed to generate audio for {file_prefix} {i + 1}: {e}"
                    )
                    raise
            else:
                logger.warning(
                    f"Skipping audio generation for {file_prefix} {i + 1} due to "
                    f"missing or empty transcript data"
                )

    await state_manager.update_step_status(file_id, state_key, "completed", audio_files)
    logger.info(
        f"Audio generation completed successfully with {len(audio_files)} files"
    )

    # Do NOT upload per-track audio files; only the final concatenated audio is uploaded below
    # This reduces storage usage and avoids exposing intermediate artifacts.

    # Create and upload a single final audio file by concatenating per-track MP3s
    try:
        if audio_files:
            storage_provider = get_storage_provider()
            # Resolve output storage location (task-first when available)
            base_id, storage_key, storage_uri = output_storage_uri(
                file_id,
                state=state if isinstance(state, dict) else None,
                segments=("audio", "final.mp3"),
            )

            # Concatenate files into a single MP3 under output dir (task-organized)
            local_dir = config.output_dir / "/".join(storage_key.split("/")[:-1])
            local_dir.mkdir(parents=True, exist_ok=True)
            final_local_path = config.output_dir / storage_key
            with open(final_local_path, "wb") as outfile:
                for ap in audio_files:
                    with open(ap, "rb") as infile:
                        while True:
                            chunk = infile.read(1024 * 256)
                            if not chunk:
                                break
                            outfile.write(chunk)

            # Upload to storage with task-id-based key when possible
            storage_provider.upload_file(
                str(final_local_path), storage_key, "audio/mpeg"
            )

            # Verify availability with a short retry loop (handles eventual consistency)
            ok = False
            try_count = 0
            import asyncio

            while try_count < 3:
                try_count += 1
                try:
                    if storage_provider.file_exists(storage_key):
                        ok = True
                        break
                except Exception:
                    # Ignore provider-specific head errors and retry
                    pass
                await asyncio.sleep(0.5 * (2 ** (try_count - 1)))

            if ok:
                logger.info(
                    f"Final audio uploaded and verified in storage: {storage_key}"
                )
            else:
                logger.warning(
                    f"Final audio upload could not be verified yet: {storage_key}. Using local fallback."
                )

            # Persist artifact metadata in state for downstream consumers
            if state and isinstance(state, dict):
                artifacts = dict(state.get("artifacts") or {})
                artifacts["final_audio"] = {
                    "local_path": str(final_local_path),
                    "storage_key": storage_key,
                    "storage_uri": storage_uri,
                    "content_type": "audio/mpeg",
                }
                state["artifacts"] = artifacts
                await state_manager.save_state(file_id, state)
    except Exception as e:  # noqa: BLE001 - escalate when remote storage is required
        logger.error(f"Failed to create/upload final audio: {e}")
        if config.storage_provider != "local":
            await state_manager.update_step_status(
                file_id,
                state_key,
                "failed",
                {
                    "error": "final_audio_upload_failed",
                    "detail": str(e),
                },
            )
            raise


async def get_pdf_transcripts(file_id: str) -> list[dict[str, Any]]:
    """Get transcripts for PDF processing."""
    state = await state_manager.get_state(file_id)
    chapters: list[dict[str, Any]] = []

    # Priority 1: use translated voice transcripts if present (ensures correct audio language)
    if (
        state
        and "steps" in state
        and "translate_voice_transcripts" in state["steps"]
        and "data" in state["steps"]["translate_voice_transcripts"]
        and state["steps"]["translate_voice_transcripts"]["data"]
    ):
        chapters = state["steps"]["translate_voice_transcripts"]["data"]
        logger.info("Using translated voice transcripts for PDF audio generation")
    # Priority 2: use revised English transcripts
    elif (
        state
        and "steps" in state
        and "revise_pdf_transcripts" in state["steps"]
        and "data" in state["steps"]["revise_pdf_transcripts"]
        and state["steps"]["revise_pdf_transcripts"]["data"]
    ):
        chapters = state["steps"]["revise_pdf_transcripts"]["data"]
        logger.info("Using revised transcripts for PDF audio generation")
    # Fallback: original chapters with English transcripts
    elif (
        state
        and "steps" in state
        and "segment_pdf_content" in state["steps"]
        and "data" in state["steps"]["segment_pdf_content"]
        and state["steps"]["segment_pdf_content"]["data"]
    ):
        # Fallback to original English transcripts
        chapters = state["steps"]["segment_pdf_content"]["data"]
        logger.info("Using original English transcripts for PDF audio generation")

    return chapters


async def get_slide_transcripts(file_id: str) -> list[dict[str, Any]]:
    """Get transcripts for slide processing."""
    state = await state_manager.get_state(file_id)
    transcripts = []

    # Check for translated voice transcripts first (for non-English audio)
    if (
        state
        and "steps" in state
        and "translate_voice_transcripts" in state["steps"]
        and "data" in state["steps"]["translate_voice_transcripts"]
        and state["steps"]["translate_voice_transcripts"]["data"]
    ):
        # Use translated voice transcripts if available (for non-English audio)
        transcripts = state["steps"]["translate_voice_transcripts"]["data"]
        logger.info("Using translated voice transcripts for audio generation")
    # Fallback to revised English transcripts
    elif (
        state
        and "steps" in state
        and "revise_transcripts" in state["steps"]
        and "data" in state["steps"]["revise_transcripts"]
        and state["steps"]["revise_transcripts"]["data"]
    ):
        # Use revised transcripts if available (better quality)
        transcripts = state["steps"]["revise_transcripts"]["data"]
        logger.info("Using revised English transcripts for audio generation")

    return transcripts
