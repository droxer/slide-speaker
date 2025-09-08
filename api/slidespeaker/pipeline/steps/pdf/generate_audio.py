"""
PDF audio generation step for SlideSpeaker.

This module handles the generation of audio for PDF chapters.
"""

from pathlib import Path
from typing import Any

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.processing.audio_generator import AudioGenerator
from slidespeaker.utils.config import get_storage_provider

audio_generator = AudioGenerator()

# Get storage provider instance
storage_provider = get_storage_provider()


async def generate_audio_step(file_id: str, language: str = "english") -> None:
    """
    Generate audio for PDF chapters.

    Args:
        file_id: Unique identifier for the file
        language: Language for audio generation
    """
    await state_manager.update_step_status(file_id, "generate_pdf_audio", "processing")
    logger.info(f"Generating audio for PDF chapters for file: {file_id}")

    try:
        # Get chapters from state
        state = await state_manager.get_state(file_id)
        chapters: list[dict[str, Any]] = []
        if (
            state
            and "steps" in state
            and "segment_pdf_content" in state["steps"]
            and state["steps"]["segment_pdf_content"]["data"] is not None
        ):
            chapters = state["steps"]["segment_pdf_content"]["data"]

        if not chapters:
            raise ValueError("No chapter data available for audio generation")

        # Create working directory
        work_dir = Path("output") / file_id
        audio_dir = work_dir / "audio"
        audio_dir.mkdir(exist_ok=True, parents=True)

        # Generate audio for each chapter
        audio_local_paths = []
        for i, chapter in enumerate(chapters):
            script = chapter.get("script", "")
            if script:
                audio_path = audio_dir / f"chapter_{i + 1}.mp3"
                success = await audio_generator.generate_audio(
                    script, str(audio_path), language
                )
                if success:
                    audio_local_paths.append(audio_path)

        # For PDF processing, we only need local paths for subsequent steps
        # Final outputs (video and subtitles) will be uploaded to storage
        storage_data = {
            "local_paths": [str(path) for path in audio_local_paths],
            "storage_urls": [],  # No storage URLs for intermediate audio in PDF processing
        }

        # Store audio data in state
        await state_manager.update_step_status(
            file_id, "generate_pdf_audio", "completed", storage_data
        )

        logger.info(
            f"Generated {len(audio_local_paths)} audio files for file: {file_id}"
        )

    except Exception as e:
        logger.error(f"Failed to generate PDF audio for file {file_id}: {e}")
        raise
