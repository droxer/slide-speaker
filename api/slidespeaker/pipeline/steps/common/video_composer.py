"""
Shared video composition logic for SlideSpeaker pipeline steps.

This module provides common functionality for composing videos from slide components
in both PDF and presentation slide processing pipelines.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from loguru import logger

from slidespeaker.configs.config import config, get_storage_provider
from slidespeaker.core.state_manager import state_manager
from slidespeaker.storage.paths import output_storage_uri
from slidespeaker.video import VideoComposer


async def compose_video(
    file_id: str,
    state_key: str,
    get_audio_files_func: Callable[[str], Any],
    get_subtitle_files_func: Callable[[str], Any],
    get_slide_images_func: Callable[[str], Any],
    is_pdf: bool = False,
) -> tuple[str, str]:
    """
    Compose video using shared logic.

    Args:
        file_id: Unique identifier for the file
        state_key: State key to update (e.g., "compose_video" or "compose_pdf_video")
        get_audio_files_func: Function to retrieve audio files
        get_subtitle_files_func: Function to retrieve subtitle files
        get_slide_images_func: Function to retrieve slide images
        is_pdf: Whether this is for PDF processing

    Returns:
        Tuple of (local_video_path, storage_url)

    Raises:
        ValueError: If required files are not available
    """
    await state_manager.update_step_status(file_id, state_key, "processing")
    logger.info(f"Starting video composition for file: {file_id}")

    try:
        # Get required files from state
        audio_files = await get_audio_files_func(file_id)
        subtitle_data = await get_subtitle_files_func(file_id)
        slide_images = await get_slide_images_func(file_id)

        if not audio_files:
            # Fallback: scan local output directory for per-slide audio files
            try:
                audio_dir = config.output_dir / file_id / "audio"
                if audio_dir.exists():
                    found = sorted(str(p) for p in audio_dir.glob("*.mp3"))
                    if found:
                        audio_files = found
            except Exception:
                pass
            if not audio_files:
                raise ValueError("No audio files available for video composition")

        # Prepare output directory for intermediate assets
        work_dir = config.output_dir / file_id
        work_dir.mkdir(exist_ok=True, parents=True)

        # Resolve final storage key/path prior to composition
        state = await state_manager.get_state(file_id)
        _, storage_key, storage_uri = output_storage_uri(
            file_id,
            state=state if isinstance(state, dict) else None,
            segments=("video", "final.mp4"),
        )

        final_video_path = config.output_dir / storage_key
        final_video_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate video using shared composer
        composer = VideoComposer()

        # Get subtitle files (SRT and VTT) if available
        subtitle_files = []
        if isinstance(subtitle_data, dict) and "subtitle_files" in subtitle_data:
            subtitle_files = [
                Path(p) for p in subtitle_data["subtitle_files"] if Path(p).exists()
            ]
        elif isinstance(subtitle_data, list):
            subtitle_files = [Path(p) for p in subtitle_data if Path(p).exists()]

        # Filter to only include SRT files for video embedding
        srt_files = [f for f in subtitle_files if f.suffix.lower() == ".srt"]

        logger.info(
            f"Composing video with {len(audio_files)} audio files, "
            f"{len(srt_files)} subtitle files, and {len(slide_images)} slide images"
        )

        # Compose the video
        await composer.compose_video(
            slide_images=[Path(img) for img in slide_images],
            avatar_videos=[],  # TODO: Add avatar video support
            audio_files=[Path(audio) for audio in audio_files],
            output_path=final_video_path,
        )

        if not final_video_path.exists():
            raise ValueError(f"Failed to compose video: {final_video_path}")

        # Upload to storage (use task-id based key if available, otherwise file_id)
        storage_provider = get_storage_provider()
        storage_url = storage_provider.upload_file(
            str(final_video_path), storage_key, "video/mp4"
        )

        # Store in state
        video_data = {
            "local_path": str(final_video_path),
            "storage_url": storage_url,
            "storage_key": storage_key,
            "storage_uri": storage_uri,
        }

        await state_manager.update_step_status(
            file_id, state_key, "completed", video_data
        )

        if state and isinstance(state, dict):
            artifacts = dict(state.get("artifacts") or {})
            artifacts["final_video"] = {
                "local_path": str(final_video_path),
                "storage_key": storage_key,
                "storage_uri": storage_uri,
                "content_type": "video/mp4",
            }
            state["artifacts"] = artifacts
            await state_manager.save_state(file_id, state)

        logger.info(f"Video composition completed: {final_video_path}")
        return str(final_video_path), storage_url

    except Exception as e:
        logger.error(f"Failed to compose video: {e}")
        await state_manager.update_step_status(
            file_id, state_key, "failed", {"error": str(e)}
        )
        raise


async def get_pdf_audio_files(file_id: str) -> list[str]:
    """Get audio files for PDF video composition."""
    state = await state_manager.get_state(file_id)
    audio_files = []

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
            audio_files = [audio_data] if Path(audio_data).exists() else []
        else:
            # Fallback for old format or unexpected data structure
            audio_files = audio_data if isinstance(audio_data, list) else []

    return audio_files


async def get_pdf_subtitle_files(file_id: str) -> Any:
    """Get subtitle files for PDF video composition."""
    state = await state_manager.get_state(file_id)

    if (
        state
        and "steps" in state
        and "generate_pdf_subtitles" in state["steps"]
        and "data" in state["steps"]["generate_pdf_subtitles"]
        and state["steps"]["generate_pdf_subtitles"]["data"] is not None
    ):
        return state["steps"]["generate_pdf_subtitles"]["data"]

    return []


async def get_pdf_slide_images(file_id: str) -> list[str]:
    """Get slide images for PDF video composition."""
    state = await state_manager.get_state(file_id)
    slide_images: list[str] = []

    # PDF pipeline generates chapter images in the `generate_pdf_chapter_images` step
    if (
        state
        and "steps" in state
        and "generate_pdf_chapter_images" in state["steps"]
        and state["steps"]["generate_pdf_chapter_images"]["data"] is not None
    ):
        data = state["steps"]["generate_pdf_chapter_images"]["data"]
        # Expected shape: { "local_paths": [str, ...], "storage_urls": [...] }
        if isinstance(data, dict) and "local_paths" in data:
            paths = data.get("local_paths")
            if isinstance(paths, list):
                slide_images = [p for p in paths if isinstance(p, str)]
        # Backward-compatibility: if data is already a list of paths
        elif isinstance(data, list):
            slide_images = [p for p in data if isinstance(p, str)]

    return slide_images


async def get_slide_audio_files(file_id: str) -> list[str]:
    """Get audio files for slide video composition."""
    state = await state_manager.get_state(file_id)
    audio_files = []

    if (
        state
        and "steps" in state
        and "generate_audio" in state["steps"]
        and "data" in state["steps"]["generate_audio"]
        and state["steps"]["generate_audio"]["data"] is not None
    ):
        audio_files = state["steps"]["generate_audio"]["data"]

    return audio_files


async def get_slide_subtitle_files(file_id: str) -> Any:
    """Get subtitle files for slide video composition."""
    state = await state_manager.get_state(file_id)

    if (
        state
        and "steps" in state
        and "generate_subtitles" in state["steps"]
        and "data" in state["steps"]["generate_subtitles"]
        and state["steps"]["generate_subtitles"]["data"] is not None
    ):
        return state["steps"]["generate_subtitles"]["data"]

    return []


async def get_slide_images(file_id: str) -> list[str]:
    """Get slide images for slide video composition."""
    state = await state_manager.get_state(file_id)
    slide_images = []

    if (
        state
        and "steps" in state
        and "convert_slides_to_images" in state["steps"]
        and "data" in state["steps"]["convert_slides_to_images"]
        and state["steps"]["convert_slides_to_images"]["data"] is not None
    ):
        slide_images = state["steps"]["convert_slides_to_images"]["data"]

    return slide_images
