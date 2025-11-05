"""
Shared subtitle generation logic for SlideSpeaker pipeline steps.

This module provides common functionality for generating subtitles from transcripts
in both PDF and presentation slide processing pipelines.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from loguru import logger

from slidespeaker.configs.config import config, get_storage_provider
from slidespeaker.configs.locales import locale_utils
from slidespeaker.core.state_manager import state_manager
from slidespeaker.storage.paths import output_storage_uri
from slidespeaker.subtitle import SubtitleGenerator


async def generate_subtitles_common(
    file_id: str,
    state_key: str,
    get_transcripts_func: Callable[..., Any],
    get_audio_files_func: Callable[[str], Any],
    language: str = "english",
    is_pdf: bool = False,
) -> None:
    """
    Generate subtitles from transcripts using shared logic.

    Args:
        file_id: Unique identifier for the file
        state_key: State key to update (e.g., "generate_subtitles" or "generate_pdf_subtitles")
        get_transcripts_func: Function to retrieve transcripts data
        get_audio_files_func: Function to retrieve audio files data
        language: Target language for subtitles
        is_pdf: Whether this is for PDF processing

    Raises:
        ValueError: If no transcripts data is available
    """
    await state_manager.update_step_status(file_id, state_key, "processing")
    logger.info(f"Starting subtitle generation for file: {file_id}")

    # Normalize target language to internal key
    from slidespeaker.configs.locales import locale_utils as _lu

    language = _lu.normalize_language(language)

    # Get transcripts for subtitle generation
    # Pass language parameter if the function supports it
    try:
        transcripts_data = await get_transcripts_func(file_id, language)
    except TypeError:
        # Fallback for functions that don't accept language parameter
        transcripts_data = await get_transcripts_func(file_id)

    if not transcripts_data:
        logger.warning("No transcripts data available for subtitle generation")
        await state_manager.update_step_status(
            file_id, state_key, "completed", {"subtitle_files": [], "storage_urls": []}
        )
        return

    # Get audio files for timing
    audio_files_data = await get_audio_files_func(file_id)
    if not audio_files_data:
        try:
            audio_dir = config.output_dir / file_id / "audio"
            if audio_dir.exists():
                fallback_audio = sorted(str(p) for p in audio_dir.glob("*.mp3"))
                if fallback_audio:
                    audio_files_data = fallback_audio
        except Exception:
            pass
    logger.debug(
        "Subtitle generation audio sources (file_id=%s): %s",
        file_id,
        audio_files_data,
    )

    # Generate subtitle files
    try:
        work_dir = config.output_dir / file_id
        subtitle_dir = work_dir / "subtitles"
        subtitle_dir.mkdir(exist_ok=True, parents=True)

        # Include locale code in intermediate filenames for clarity
        locale_code = locale_utils.get_locale_code(language)
        intermediate_base = subtitle_dir / f"{file_id}_subtitles_{locale_code}.mp4"

        subtitle_generator = SubtitleGenerator()

        # Handle case where we have no audio files
        if not audio_files_data:
            logger.warning(
                "No audio files available for subtitle timing, using estimated durations"
            )
            # Create subtitles with estimated durations if no audio files are available
            srt_path, vtt_path = subtitle_generator.generate_subtitles(
                scripts=transcripts_data,
                audio_files=[],  # No audio files available
                video_path=Path(intermediate_base),
                language=language,
            )
        else:
            # Create subtitles with actual audio timing
            # Convert to Path objects and filter out non-existent files
            audio_paths = [
                Path(str(f)).expanduser()
                for f in audio_files_data
                if isinstance(f, str | Path) and str(f).strip()
            ]
            srt_path, vtt_path = subtitle_generator.generate_subtitles(
                scripts=transcripts_data,
                audio_files=audio_paths,
                video_path=Path(intermediate_base),
                language=language,
            )

        logger.info(f"Generated subtitles: {srt_path}, {vtt_path}")

        # Upload subtitle files to storage provider
        storage_provider = get_storage_provider()
        state_snapshot = await state_manager.get_state(file_id)
        storage_keys: list[str]
        storage_uris: list[str]
        subtitle_urls: list[str]
        try:  # Upload generated subtitles to configured storage
            _, srt_key, srt_uri = output_storage_uri(
                file_id,
                state=state_snapshot if isinstance(state_snapshot, dict) else None,
                segments=("subtitles", f"{locale_code}.srt"),
            )
            _, vtt_key, vtt_uri = output_storage_uri(
                file_id,
                state=state_snapshot if isinstance(state_snapshot, dict) else None,
                segments=("subtitles", f"{locale_code}.vtt"),
            )

            srt_url = storage_provider.upload_file(str(srt_path), srt_key, "text/plain")
            vtt_url = storage_provider.upload_file(str(vtt_path), vtt_key, "text/vtt")

            subtitle_urls = [srt_url, vtt_url]
            storage_keys = [srt_key, vtt_key]
            storage_uris = [srt_uri, vtt_uri]
            logger.info(f"Uploaded subtitles to storage: {srt_url}, {vtt_url}")
        except Exception as storage_error:  # noqa: BLE001 - fail when remote storage is required
            logger.error(f"Failed to upload subtitles to storage: {storage_error}")
            if config.storage_provider != "local":
                await state_manager.update_step_status(
                    file_id,
                    state_key,
                    "failed",
                    {
                        "error": "subtitle_upload_failed",
                        "detail": str(storage_error),
                        "storage_keys": {"srt": srt_key, "vtt": vtt_key},
                    },
                )
                raise
            # Fallback to local paths when running with local storage provider
            subtitle_urls = [str(srt_path), str(vtt_path)]
            storage_keys = []
            storage_uris = []

        # Store both local paths and storage URLs
        storage_data = {
            "subtitle_files": [str(srt_path), str(vtt_path)],
            "storage_urls": subtitle_urls,
            "storage_keys": storage_keys,
            "storage_uris": storage_uris,
        }

        await state_manager.update_step_status(
            file_id, state_key, "completed", storage_data
        )
        logger.info("Subtitle generation completed successfully")

        if state_snapshot and isinstance(state_snapshot, dict):
            artifacts = dict(state_snapshot.get("artifacts") or {})
            subtitles_map = dict(artifacts.get("subtitles") or {})
            subtitles_map[locale_code] = {
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
            artifacts["subtitles"] = subtitles_map
            state_snapshot["artifacts"] = artifacts
            await state_manager.save_state(file_id, state_snapshot)
    except Exception as e:
        logger.error(f"Failed to generate subtitles: {e}")
        import traceback

        logger.error(f"Subtitle generation traceback: {traceback.format_exc()}")
        await state_manager.update_step_status(
            file_id, state_key, "failed", {"error": str(e)}
        )
        raise


async def get_pdf_subtitles_transcripts(
    file_id: str, language: str = "english"
) -> list[dict[str, Any]]:
    """Get transcripts for PDF subtitle generation."""

    state = await state_manager.get_state(file_id)
    chapters: list[dict[str, Any]] = []

    # Determine which transcripts to use for subtitles based on language
    source_key: str | None = None
    if state and "steps" in state:
        # If requesting English subtitles, prioritize English transcripts
        if language.lower() == "english":
            # Priority 1: Original English transcripts
            if (
                "segment_pdf_content" in state["steps"]
                and "data" in state["steps"]["segment_pdf_content"]
                and state["steps"]["segment_pdf_content"]["data"]
            ):
                chapters = state["steps"]["segment_pdf_content"]["data"]
                logger.info(
                    "Using original English transcripts for PDF subtitle generation"
                )
                source_key = "segment_pdf_content"
            # Priority 2: Translated subtitle transcripts (if they're English)
            elif (
                "translate_subtitle_transcripts" in state["steps"]
                and "data" in state["steps"]["translate_subtitle_transcripts"]
                and state["steps"]["translate_subtitle_transcripts"]["data"]
            ):
                # Check if these are English transcripts
                chapters = state["steps"]["translate_subtitle_transcripts"]["data"]
                logger.info(
                    f"Using translated subtitle transcripts for PDF subtitle generation (language: {language})"
                )
                source_key = "translate_subtitle_transcripts"
            # Priority 3: Translated voice transcripts (if they're English)
            elif (
                "translate_voice_transcripts" in state["steps"]
                and "data" in state["steps"]["translate_voice_transcripts"]
                and state["steps"]["translate_voice_transcripts"]["data"]
            ):
                # Check if these are English transcripts
                chapters = state["steps"]["translate_voice_transcripts"]["data"]
                logger.info(
                    f"Using translated voice transcripts for PDF subtitle generation (language: {language})"
                )
                source_key = "translate_voice_transcripts"
        else:
            # For non-English languages, prioritize translated transcripts
            # Priority 1: Use translated subtitle transcripts if available
            if (
                "translate_subtitle_transcripts" in state["steps"]
                and "data" in state["steps"]["translate_subtitle_transcripts"]
                and state["steps"]["translate_subtitle_transcripts"]["data"]
            ):
                chapters = state["steps"]["translate_subtitle_transcripts"]["data"]
                logger.info(
                    f"Using translated subtitle transcripts for PDF subtitle generation (language: {language})"
                )
                source_key = "translate_subtitle_transcripts"
            # Priority 2: Use translated voice transcripts as fallback
            elif (
                "translate_voice_transcripts" in state["steps"]
                and "data" in state["steps"]["translate_voice_transcripts"]
                and state["steps"]["translate_voice_transcripts"]["data"]
            ):
                chapters = state["steps"]["translate_voice_transcripts"]["data"]
                logger.info(
                    f"Using translated voice transcripts for PDF subtitle generation (language: {language})"
                )
                source_key = "translate_voice_transcripts"
            # Priority 3: Fall back to original chapters with English transcripts
            elif (
                "segment_pdf_content" in state["steps"]
                and "data" in state["steps"]["segment_pdf_content"]
                and state["steps"]["segment_pdf_content"]["data"]
            ):
                chapters = state["steps"]["segment_pdf_content"]["data"]
                logger.info(
                    "Using original English transcripts for PDF subtitle generation"
                )
                source_key = "segment_pdf_content"

    # Persist selection metadata for diagnostics
    try:
        if state is not None:
            state["subtitle_generation"] = {
                "pipeline": "pdf",
                "language": language,
                "source": source_key or "unknown",
            }
            await state_manager.save_state(file_id, state)
    except Exception:
        pass
    return chapters


async def get_slide_subtitles_transcripts(
    file_id: str, language: str = "english"
) -> list[dict[str, Any]]:
    """Get transcripts for slide subtitle generation."""

    state = await state_manager.get_state(file_id)
    transcripts_data: list[dict[str, Any]] = []

    # Determine which transcripts to use for subtitles based on language
    source_key: str | None = None
    if state and "steps" in state:
        # If requesting English subtitles, prioritize English transcripts
        if language.lower() == "english":
            # Priority 1: Regular English transcripts
            if (
                "revise_transcripts" in state["steps"]
                and "data" in state["steps"]["revise_transcripts"]
                and state["steps"]["revise_transcripts"]["data"]
            ):
                transcripts_data = state["steps"]["revise_transcripts"]["data"]
                logger.info("Using regular English transcripts for subtitle generation")
                source_key = "revise_transcripts"
            # Priority 2: Translated subtitle transcripts (if they're English)
            elif (
                "translate_subtitle_transcripts" in state["steps"]
                and "data" in state["steps"]["translate_subtitle_transcripts"]
                and state["steps"]["translate_subtitle_transcripts"]["data"]
            ):
                transcripts_data = state["steps"]["translate_subtitle_transcripts"][
                    "data"
                ]
                logger.info(
                    f"Using translated subtitle transcripts for subtitle generation (language: {language})"
                )
                source_key = "translate_subtitle_transcripts"
            # Priority 3: Translated voice transcripts (if they're English)
            elif (
                "translate_voice_transcripts" in state["steps"]
                and "data" in state["steps"]["translate_voice_transcripts"]
                and state["steps"]["translate_voice_transcripts"]["data"]
            ):
                transcripts_data = state["steps"]["translate_voice_transcripts"]["data"]
                logger.info(
                    f"Using translated voice transcripts for subtitle generation (language: {language})"
                )
                source_key = "translate_voice_transcripts"
        else:
            # For non-English languages, prioritize translated transcripts
            # Priority 1: Use translated subtitle transcripts if available
            if (
                "translate_subtitle_transcripts" in state["steps"]
                and "data" in state["steps"]["translate_subtitle_transcripts"]
                and state["steps"]["translate_subtitle_transcripts"]["data"]
            ):
                transcripts_data = state["steps"]["translate_subtitle_transcripts"][
                    "data"
                ]
                logger.info(
                    f"Using translated subtitle transcripts for subtitle generation (language: {language})"
                )
                source_key = "translate_subtitle_transcripts"
            # Priority 2: Use translated voice transcripts as fallback
            elif (
                "translate_voice_transcripts" in state["steps"]
                and "data" in state["steps"]["translate_voice_transcripts"]
                and state["steps"]["translate_voice_transcripts"]["data"]
            ):
                transcripts_data = state["steps"]["translate_voice_transcripts"]["data"]
                logger.info(
                    f"Using translated voice transcripts for subtitle generation (language: {language})"
                )
                source_key = "translate_voice_transcripts"
            # Priority 3: Fall back to regular English transcripts
            elif (
                "revise_transcripts" in state["steps"]
                and "data" in state["steps"]["revise_transcripts"]
                and state["steps"]["revise_transcripts"]["data"]
            ):
                transcripts_data = state["steps"]["revise_transcripts"]["data"]
                logger.info("Using regular English transcripts for subtitle generation")
                source_key = "revise_transcripts"

    # Persist selection metadata for diagnostics
    try:
        if state is not None:
            state["subtitle_generation"] = {
                "pipeline": "slides",
                "language": language,
                "source": source_key or "unknown",
            }
            await state_manager.save_state(file_id, state)
    except Exception:
        pass
    return transcripts_data


async def get_pdf_audio_files(file_id: str) -> list[str]:
    """Get audio files for PDF subtitle timing."""
    state = await state_manager.get_state(file_id)
    audio_files_data = []

    if (
        state
        and "steps" in state
        and "generate_pdf_audio" in state["steps"]
        and "data" in state["steps"]["generate_pdf_audio"]
        and state["steps"]["generate_pdf_audio"]["data"] is not None
    ):
        audio_data = state["steps"]["generate_pdf_audio"]["data"]
        # Handle both list format and legacy string format
        if isinstance(audio_data, str):
            # Legacy format - single string path
            audio_files_data = [audio_data] if Path(audio_data).exists() else []
        else:
            # Fallback for old format or unexpected data structure
            audio_files_data = audio_data if isinstance(audio_data, list) else []

    return audio_files_data


async def get_slide_audio_files(file_id: str) -> list[str]:
    """Get audio files for slide subtitle timing."""
    state = await state_manager.get_state(file_id)
    audio_files_data = []

    if (
        state
        and "steps" in state
        and "generate_audio" in state["steps"]
        and "data" in state["steps"]["generate_audio"]
        and state["steps"]["generate_audio"]["data"] is not None
    ):
        audio_files_data = state["steps"]["generate_audio"]["data"]

    return audio_files_data
