"""
Generate audio step for the presentation pipeline.
"""

from pathlib import Path
from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.services.tts_service import TTSService
from slidespeaker.utils.config import config

tts_service = TTSService()


async def generate_audio_step(file_id: str, language: str = "english") -> None:
    """Generate audio from scripts using TTS"""
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
            await state_manager.mark_failed(file_id)
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
                await state_manager.mark_failed(file_id)
                return

        # Additional null check for individual script data
        if script_data and "script" in script_data and script_data["script"]:
            script_text = script_data["script"].strip()
            if script_text:  # Only generate audio if script is not empty
                audio_path = config.output_dir / f"{file_id}_slide_{i + 1}.mp3"
                try:
                    # Try OpenAI first
                    await tts_service.generate_speech(
                        script_text, audio_path, provider="openai", language=language
                    )
                    audio_files.append(str(audio_path))
                    logger.info(f"Generated audio for slide {i + 1}: {audio_path}")
                except Exception as e:
                    logger.error(
                        f"Failed to generate audio with OpenAI for slide {i + 1}: {e}"
                    )
                    # Try ElevenLabs as fallback
                    try:
                        await tts_service.generate_speech(
                            script_text,
                            audio_path,
                            provider="elevenlabs",
                            language=language,
                        )
                        audio_files.append(str(audio_path))
                        logger.info(
                            f"Generated audio with ElevenLabs fallback for "
                            f"slide {i + 1}: {audio_path}"
                        )
                    except Exception as fallback_e:
                        logger.error(
                            f"Fallback to ElevenLabs also failed for "
                            f"slide {i + 1}: {fallback_e}"
                        )
                        raise Exception(
                            f"Failed to generate audio for slide {i + 1} "
                            f"with both providers: {e}"
                        ) from e
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