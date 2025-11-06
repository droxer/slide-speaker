"""
Tests for the podcast coordinator pipeline.
"""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from slidespeaker.pipeline.podcast.coordinator import (
    PodcastPipeline,
    _get_audio_dialogue_data,
    _get_script_dialogue_data,
    _podcast_step_name,
    _podcast_steps,
    extract_podcast_dialogue_from_state,
)


@pytest.mark.asyncio
async def test_podcast_steps_english_only():
    """Test podcast steps when no translation is needed (English only)."""
    steps = _podcast_steps(None, "english")
    expected = [
        "generate_podcast_script",
        "generate_podcast_audio",
        "generate_podcast_subtitles",
        "compose_podcast",
    ]
    assert steps == expected


@pytest.mark.asyncio
async def test_podcast_steps_with_translation():
    """Test podcast steps when translation is needed."""
    steps = _podcast_steps("spanish", "english")
    expected = [
        "generate_podcast_script",
        "translate_podcast_script",
        "generate_podcast_audio",
        "generate_podcast_subtitles",
        "compose_podcast",
    ]
    assert steps == expected


def test_podcast_step_name():
    """Test podcast step display names."""
    assert (
        _podcast_step_name("generate_podcast_script")
        == "Generating podcast script (two speakers)"
    )
    assert _podcast_step_name("unknown_step") == "unknown_step"


def test_get_audio_dialogue_data_success():
    """Test getting dialogue data from audio step."""
    steps = {
        "generate_podcast_audio": {
            "status": "completed",
            "data": {
                "dialogue": [{"speaker": "Host", "text": "Hello"}],
                "host_voice": "voice1",
                "guest_voice": "voice2",
                "dialogue_language": "spanish",
                "total_duration": 120.5,
            },
        }
    }

    result = _get_audio_dialogue_data(steps)
    assert result is not None
    assert result["dialogue"] == [{"speaker": "Host", "text": "Hello"}]
    assert result["language"] == "spanish"
    assert result["total_duration"] == 120.5


def test_get_audio_dialogue_data_missing():
    """Test getting dialogue data when audio step is not completed."""
    steps = {"generate_podcast_audio": {"status": "failed", "data": {}}}

    result = _get_audio_dialogue_data(steps)
    assert result is None


def test_get_audio_dialogue_data_segment_metadata():
    """Test getting dialogue from segment_metadata fallback."""
    steps = {
        "generate_podcast_audio": {
            "status": "completed",
            "data": {"segment_metadata": [{"speaker": "Guest", "text": "Good point"}]},
        }
    }

    result = _get_audio_dialogue_data(steps)
    assert result is not None
    assert result["dialogue"] == [{"speaker": "Guest", "text": "Good point"}]


def test_get_script_dialogue_data_translated():
    """Test getting dialogue from translated script."""
    steps = {
        "translate_podcast_script": {
            "status": "completed",
            "data": [{"speaker": "Host", "text": "translated"}],
        }
    }

    result = _get_script_dialogue_data(steps, "spanish", "voice1", "voice2")
    assert result is not None
    assert result["dialogue"] == [{"speaker": "Host", "text": "translated"}]
    assert result["language"] == "spanish"


def test_get_script_dialogue_data_original():
    """Test getting dialogue from original script."""
    steps = {
        "translate_podcast_script": {"status": "failed", "data": []},
        "generate_podcast_script": {
            "status": "completed",
            "data": [{"speaker": "Host", "text": "original"}],
        },
    }

    result = _get_script_dialogue_data(steps, "spanish", "voice1", "voice2")
    assert result is not None
    assert result["dialogue"] == [{"speaker": "Host", "text": "original"}]
    assert result["language"] == "english"


def test_extract_podcast_dialogue_from_state_with_audio():
    """Test extracting dialogue with audio data available."""
    state = {
        "steps": {
            "generate_podcast_audio": {
                "status": "completed",
                "data": {
                    "dialogue": [{"speaker": "Host", "text": "Audio dialogue"}],
                    "dialogue_language": "french",
                },
            }
        }
    }

    result = extract_podcast_dialogue_from_state(state)
    assert result is not None
    assert result["language"] == "french"
    assert result["dialogue"] == [{"speaker": "Host", "text": "Audio dialogue"}]


def test_extract_podcast_dialogue_from_state_translated_script():
    """Test extracting dialogue from translated script when audio not available."""
    state = {
        "steps": {
            "generate_podcast_audio": {"status": "failed", "data": {}},
            "translate_podcast_script": {
                "status": "completed",
                "data": [{"speaker": "Guest", "text": "Translated script"}],
            },
        },
        "podcast_transcript_language": "spanish",
    }

    result = extract_podcast_dialogue_from_state(state)
    assert result is not None
    assert result["language"] == "spanish"
    assert result["dialogue"] == [{"speaker": "Guest", "text": "Translated script"}]


def test_extract_podcast_dialogue_from_state_empty_state():
    """Test extracting dialogue from empty state."""
    result = extract_podcast_dialogue_from_state({})
    assert result is None


@pytest.mark.asyncio
async def test_podcast_pipeline_initialization():
    """Test podcast pipeline initialization."""
    pipeline = PodcastPipeline(
        file_id="test123",
        file_path=Path("/tmp/test.pdf"),
        voice_language="spanish",
        transcript_language="french",
    )

    assert pipeline.file_id == "test123"
    assert pipeline.voice_language == "spanish"
    assert pipeline.transcript_language == "french"


@pytest.mark.asyncio
async def test_podcast_pipeline_execute_pipeline():
    """Test the full podcast pipeline execution."""
    with patch(
        "slidespeaker.pipeline.podcast.coordinator.state_manager"
    ) as mock_state_manager:
        # Mock the async methods of state_manager
        mock_state_manager.get_state = AsyncMock(
            return_value={"generate_podcast": False}
        )
        mock_state_manager.save_state = AsyncMock()
        mock_state_manager.add_error = AsyncMock()
        mock_state_manager.mark_failed = AsyncMock()
        mock_state_manager.mark_completed = AsyncMock()

        with (
            patch("slidespeaker.core.task_queue.task_queue") as mock_task_queue,
            patch(
                "slidespeaker.pipeline.podcast.coordinator.pdf_segment_content_step"
            ) as mock_segment_step,
        ):
            # Mock the task queue to not be cancelled
            mock_task_queue.is_task_cancelled.return_value = False

            # Mock the steps to do nothing
            mock_segment_step.return_value = None

            # Create a pipeline and run it
            pipeline = PodcastPipeline(
                file_id="test123",
                file_path=Path("/tmp/test.pdf"),
                voice_language="spanish",
                transcript_language="french",
            )

            # Mock the _execute_step method to avoid actual step execution
            pipeline._execute_step = AsyncMock(return_value=True)
            pipeline._check_and_handle_prerequisites = AsyncMock(return_value=True)

            await pipeline.execute_pipeline()

            # Verify state was updated
            mock_state_manager.save_state.assert_called()
            # Verify steps were executed
            assert pipeline._execute_step.called
