"""
Generate audio step for the presentation pipeline.

This module generates text-to-speech audio files from the reviewed scripts.
It uses configurable TTS services (OpenAI, ElevenLabs) to create natural-sounding
voice audio for each slide in the presentation.
"""

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.services.tts_factory import TTSFactory
from slidespeaker.utils.config import config


async def generate_audio_step(file_id: str, language: str = "english") -> None:
    """
    Generate audio from scripts using TTS services.

    This function converts the reviewed presentation scripts into audio files
    using text-to-speech technology. It supports multiple TTS providers through
    a factory pattern and includes error handling for individual slide processing.
    The function includes periodic cancellation checks for responsive task management.
    """
    await state_manager.update_step_status(file_id, "generate_audio", "processing")
    logger.info(f"Starting audio generation for file: {file_id}")
    state = await state_manager.get_state(file_id)

    # Check for task cancellation before starting
    if state and state.get("task_id"):
        from slidespeaker.core.task_queue import task_queue

        if await task_queue.is_task_cancelled(state["task_id"]):
            logger.info(
                f"Task {state['task_id']} was cancelled during audio generation"
            )
            await state_manager.mark_cancelled(file_id, cancelled_step="generate_audio")
            return

    # Comprehensive null checking for scripts data
    scripts = []
    if (
        state
        and "steps" in state
        and "review_scripts" in state["steps"]
        and state["steps"]["review_scripts"]["data"] is not None
    ):
        scripts = state["steps"]["review_scripts"]["data"]

    if not scripts:
        raise ValueError("No scripts data available for audio generation")

    audio_files = []
    for i, script_data in enumerate(scripts):
        # Check for task cancellation periodically
        if i % 2 == 0 and state and state.get("task_id"):  # Check every 2 slides
            from slidespeaker.core.task_queue import task_queue

            if await task_queue.is_task_cancelled(state["task_id"]):
                logger.info(
                    f"Task {state['task_id']} was cancelled during audio generation"
                )
                await state_manager.mark_cancelled(
                    file_id, cancelled_step="generate_audio"
                )
                return

        # Additional null check for individual script data
        if script_data and "script" in script_data and script_data["script"]:
            script_text = script_data["script"].strip()
            if script_text:  # Only generate audio if script is not empty
                audio_path = config.output_dir / f"{file_id}_slide_{i + 1}.mp3"
                try:
                    # Create TTS service using factory
                    tts_service = TTSFactory.create_service()

                    # Get supported voices for language
                    voices = tts_service.get_supported_voices(language)
                    voice = voices[0] if voices else None

                    await tts_service.generate_speech(
                        script_text, audio_path, language=language, voice=voice
                    )
                    audio_files.append(str(audio_path))
                    logger.info(f"Generated audio for slide {i + 1}: {audio_path}")
                except Exception as e:
                    logger.error(f"Failed to generate audio for slide {i + 1}: {e}")
                    raise
            else:
                logger.warning(
                    f"Skipping audio generation for slide {i + 1} due to empty script"
                )
        else:
            logger.warning(
                f"Skipping audio generation for slide {i + 1} due to "
                f"missing or empty script data"
            )

    await state_manager.update_step_status(
        file_id, "generate_audio", "completed", audio_files
    )
    logger.info(
        f"Stage 'Synthesizing voice audio' completed successfully with "
        f"{len(audio_files)} audio files"
    )

    # Verify state was updated
    updated_state = await state_manager.get_state(file_id)
    if (
        updated_state
        and updated_state["steps"]["generate_audio"]["status"] == "completed"
    ):
        logger.info(f"Successfully updated generate_audio to completed for {file_id}")
        logger.info(f"Audio files: {audio_files}")
    else:
        logger.error(f"Failed to update generate_audio state for {file_id}")
