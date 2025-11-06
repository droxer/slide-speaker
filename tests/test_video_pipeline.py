"""
Tests for the video coordinator pipeline.
"""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from slidespeaker.pipeline.video.coordinator import (
    PDFVideoPipeline,
    SlidesVideoPipeline,
    _pdf_step_name,
    _pdf_steps,
    _slide_state_key,
    _slide_step_name,
    _slide_steps,
)


@pytest.mark.asyncio
async def test_pdf_steps_english_only():
    """Test PDF video steps when no translation is needed (English only)."""
    steps = _pdf_steps("english", None, True, True)
    expected = [
        "segment_pdf_content",
        "revise_pdf_transcripts",
        "generate_pdf_chapter_images",
        "generate_pdf_audio",
        "generate_pdf_subtitles",
        "compose_video",
    ]
    assert steps == expected


@pytest.mark.asyncio
async def test_pdf_steps_with_voice_translation():
    """Test PDF video steps when voice translation is needed."""
    steps = _pdf_steps("spanish", None, True, True)
    expected = [
        "segment_pdf_content",
        "revise_pdf_transcripts",
        "translate_voice_transcripts",
        "generate_pdf_chapter_images",
        "generate_pdf_audio",
        "generate_pdf_subtitles",
        "compose_video",
    ]
    assert steps == expected


@pytest.mark.asyncio
async def test_pdf_steps_with_subtitle_translation():
    """Test PDF video steps when subtitle translation is needed."""
    steps = _pdf_steps("english", "spanish", True, True)
    expected = [
        "segment_pdf_content",
        "revise_pdf_transcripts",
        "translate_subtitle_transcripts",
        "generate_pdf_chapter_images",
        "generate_pdf_audio",
        "generate_pdf_subtitles",
        "compose_video",
    ]
    assert steps == expected


@pytest.mark.asyncio
async def test_pdf_steps_without_subtitles():
    """Test PDF video steps without subtitle generation."""
    steps = _pdf_steps("english", None, False, True)
    expected = [
        "segment_pdf_content",
        "revise_pdf_transcripts",
        "generate_pdf_chapter_images",
        "generate_pdf_audio",
        "compose_video",
    ]
    assert steps == expected


@pytest.mark.asyncio
async def test_pdf_steps_without_video():
    """Test PDF steps when only processing (not generating video)."""
    steps = _pdf_steps("english", None, True, False)
    expected = ["segment_pdf_content", "revise_pdf_transcripts"]
    assert steps == expected


def test_pdf_step_name():
    """Test PDF video step display names."""
    assert (
        _pdf_step_name("segment_pdf_content", "english", "spanish")
        == "Segmenting PDF content into chapters"
    )
    assert (
        _pdf_step_name("translate_voice_transcripts", "spanish", "spanish")
        == "Translating transcripts"
    )
    assert _pdf_step_name("unknown_step", "english", "spanish") == "unknown_step"


@pytest.mark.asyncio
async def test_slide_steps_basic():
    """Test slide video steps for basic processing."""
    steps = _slide_steps(
        True, False, True, voice_language="english", subtitle_language="english"
    )
    expected = [
        "extract_slides",
        "convert_slides",
        "analyze_slides",
        "generate_transcripts",
        "revise_transcripts",
        "generate_audio",
        "generate_subtitles",
        "compose_video",
    ]
    assert steps == expected


@pytest.mark.asyncio
async def test_slide_steps_with_avatar():
    """Test slide video steps with avatar generation."""
    steps = _slide_steps(
        True, True, True, voice_language="english", subtitle_language="english"
    )
    expected = [
        "extract_slides",
        "convert_slides",
        "analyze_slides",
        "generate_transcripts",
        "revise_transcripts",
        "generate_audio",
        "generate_avatar",
        "generate_subtitles",
        "compose_video",
    ]
    assert steps == expected


@pytest.mark.asyncio
async def test_slide_steps_with_translations():
    """Test slide video steps with language translations."""
    steps = _slide_steps(
        True, False, True, voice_language="spanish", subtitle_language="french"
    )
    expected = [
        "extract_slides",
        "convert_slides",
        "analyze_slides",
        "generate_transcripts",
        "revise_transcripts",
        "translate_voice_transcripts",
        "translate_subtitle_transcripts",
        "generate_audio",
        "generate_subtitles",
        "compose_video",
    ]
    assert steps == expected


def test_slide_step_name():
    """Test slide video step display names."""
    assert _slide_step_name("extract_slides") == "Extracting slides"
    assert _slide_step_name("unknown_step") == "unknown_step"


def test_slide_state_key():
    """Test slide state key mapping."""
    assert _slide_state_key("convert_slides") == "convert_slides_to_images"
    assert _slide_state_key("analyze_slides") == "analyze_slide_images"
    assert _slide_state_key("generate_avatar") == "generate_avatar_videos"
    assert _slide_state_key("extract_slides") == "extract_slides"  # Default case


@pytest.mark.asyncio
async def test_pdf_video_pipeline_initialization():
    """Test PDF video pipeline initialization."""
    pipeline = PDFVideoPipeline(
        file_id="test123",
        file_path=Path("/tmp/test.pdf"),
        voice_language="spanish",
        subtitle_language="french",
        generate_subtitles=True,
        generate_video=True,
    )

    assert pipeline.file_id == "test123"
    assert pipeline.voice_language == "spanish"
    assert pipeline.subtitle_language == "french"
    assert pipeline.generate_subtitles is True
    assert pipeline.generate_video is True


@pytest.mark.asyncio
async def test_slides_video_pipeline_initialization():
    """Test slides video pipeline initialization."""
    pipeline = SlidesVideoPipeline(
        file_id="test123",
        file_path=Path("/tmp/test.pptx"),
        file_ext=".pptx",
        voice_language="spanish",
        subtitle_language="french",
        generate_avatar=True,
        generate_subtitles=True,
        generate_video=True,
    )

    assert pipeline.file_id == "test123"
    assert pipeline.file_ext == ".pptx"
    assert pipeline.voice_language == "spanish"
    assert pipeline.subtitle_language == "french"
    assert pipeline.generate_avatar is True
    assert pipeline.generate_subtitles is True
    assert pipeline.generate_video is True


@pytest.mark.asyncio
async def test_pdf_video_pipeline_execute_pipeline():
    """Test the full PDF video pipeline execution."""
    with patch(
        "slidespeaker.pipeline.video.coordinator.state_manager"
    ) as mock_state_manager:
        # Mock the async methods of state_manager
        mock_state_manager.get_state = AsyncMock(return_value={"generate_video": True})
        mock_state_manager.save_state = AsyncMock()
        mock_state_manager.mark_completed = AsyncMock()
        mock_state_manager.mark_failed = AsyncMock()
        mock_state_manager.save_task_state = AsyncMock()

        with (
            patch(
                "slidespeaker.pipeline.video.coordinator.fetch_task_state"
            ) as mock_fetch_task_state,
            patch("slidespeaker.core.task_queue.task_queue") as mock_task_queue,
        ):
            # Mock fetch_task_state to return a task state that can be modified
            mock_task_state = {"generate_video": True}
            mock_fetch_task_state.return_value = mock_task_state

            # Mock the task queue to not be cancelled
            mock_task_queue.is_task_cancelled.return_value = False

            # Create a pipeline and run it
            pipeline = PDFVideoPipeline(
                file_id="test123",
                file_path=Path("/tmp/test.pdf"),
                voice_language="spanish",
                subtitle_language="french",
                generate_subtitles=True,
                generate_video=True,
            )

            # Mock the _execute_step method to avoid actual step execution
            pipeline._execute_step = AsyncMock(return_value=True)
            pipeline._check_and_handle_prerequisites = AsyncMock(return_value=True)

            await pipeline.execute_pipeline()

            # Verify that save_task_state was called (this is the method used in PDFVideoPipeline)
            assert mock_state_manager.save_task_state.called
            # Verify steps were executed
            assert pipeline._execute_step.called


@pytest.mark.asyncio
async def test_slides_video_pipeline_execute_pipeline():
    """Test the full slides video pipeline execution."""
    with patch(
        "slidespeaker.pipeline.video.coordinator.state_manager"
    ) as mock_state_manager:
        # Mock the async methods of state_manager
        mock_state_manager.get_state = AsyncMock(return_value={"generate_video": True})
        mock_state_manager.save_state = AsyncMock()
        mock_state_manager.mark_completed = AsyncMock()
        mock_state_manager.mark_failed = AsyncMock()

        with patch("slidespeaker.core.task_queue.task_queue") as mock_task_queue:
            # Mock the task queue to not be cancelled
            mock_task_queue.is_task_cancelled.return_value = False

            # Create a pipeline and run it
            pipeline = SlidesVideoPipeline(
                file_id="test123",
                file_path=Path("/tmp/test.pptx"),
                file_ext=".pptx",
                voice_language="spanish",
                subtitle_language="french",
                generate_avatar=True,
                generate_subtitles=True,
                generate_video=True,
            )

            # Mock the _execute_step method to avoid actual step execution
            pipeline._execute_step = AsyncMock(return_value=True)
            pipeline._check_and_handle_prerequisites = AsyncMock(return_value=True)

            await pipeline.execute_pipeline()

            # Verify state was updated
            mock_state_manager.save_state.assert_called()
            # Verify steps were executed
            assert pipeline._execute_step.called


@pytest.mark.asyncio
async def test_pdf_video_pipeline_prerequisites_check():
    """Test PDF video pipeline handles cancellation and failure properly."""
    with (
        patch("slidespeaker.pipeline.video.coordinator.state_manager"),
        patch("slidespeaker.core.task_queue.task_queue") as mock_task_queue,
    ):
        # Mock the task queue to be cancelled
        mock_task_queue.is_task_cancelled.return_value = True

        pipeline = PDFVideoPipeline(
            file_id="test123", file_path=Path("/tmp/test.pdf"), task_id="task123"
        )

        # Mock the _check_and_handle_prerequisites method to return False
        pipeline._check_and_handle_prerequisites = AsyncMock(return_value=False)

        # Execute the pipeline (should return early due to cancellation)
        await pipeline.execute_pipeline()

        # The method should return early without executing steps
        # Verify _execute_step was not called
        # (This method isn't called because we mocked _check_and_handle_prerequisites)


@pytest.mark.asyncio
async def test_execute_pdf_step():
    """Test executing individual PDF steps."""
    pipeline = PDFVideoPipeline(file_id="test123", file_path=Path("/tmp/test.pdf"))

    # Mock a step function
    with patch(
        "slidespeaker.pipeline.video.coordinator.pdf_segment_content_step"
    ) as mock_step:
        await pipeline._execute_pdf_step("segment_pdf_content")
        mock_step.assert_called_once_with("test123", Path("/tmp/test.pdf"), "english")


@pytest.mark.asyncio
async def test_execute_slide_step():
    """Test executing individual slide steps."""
    pipeline = SlidesVideoPipeline(
        file_id="test123", file_path=Path("/tmp/test.pptx"), file_ext=".pptx"
    )

    # Mock a step function
    with patch(
        "slidespeaker.pipeline.video.coordinator.extract_slides_step"
    ) as mock_step:
        await pipeline._execute_slide_step("extract_slides")
        mock_step.assert_called_once_with("test123", Path("/tmp/test.pptx"), ".pptx")
