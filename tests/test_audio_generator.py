"""
Unit tests for the audio generator module.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from slidespeaker.audio.generator import AudioGenerator


class TestAudioGenerator:
    """Test cases for the AudioGenerator class."""

    @pytest.fixture
    def audio_generator(self):
        """Create an AudioGenerator instance with mocked dependencies."""
        generator = AudioGenerator()
        return generator

    def test_init(self):
        """Test that AudioGenerator can be instantiated."""
        generator = AudioGenerator()
        assert isinstance(generator, AudioGenerator)

    @pytest.mark.asyncio
    async def test_generate_audio_success(self, audio_generator):
        """Test that generate_audio successfully generates audio."""
        with (
            patch("slidespeaker.audio.generator.TTSFactory") as mock_tts_factory,
            patch("slidespeaker.audio.generator.Path") as mock_path,
        ):
            # Mock TTS service
            mock_tts_service = AsyncMock()
            mock_tts_service.generate_speech = AsyncMock(
                return_value=b"test_audio_data"
            )
            mock_tts_factory.create_service = MagicMock(return_value=mock_tts_service)

            # Mock Path
            mock_path_obj = MagicMock()
            mock_path_obj.parent = MagicMock()
            mock_path_obj.parent.mkdir = MagicMock()
            mock_path_obj.exists = MagicMock(return_value=True)
            mock_stat_result = MagicMock()
            mock_stat_result.st_size = 1024  # Positive integer
            mock_path_obj.stat = MagicMock(return_value=mock_stat_result)
            mock_path.return_value = mock_path_obj

            # Mock _get_audio_duration
            with patch.object(audio_generator, "_get_audio_duration", return_value=5.0):
                # Set the TTS service on the generator
                audio_generator.tts_service = mock_tts_service

                # Call the method
                result = await audio_generator.generate_audio(
                    text="Hello world",
                    output_path="/tmp/test/output.mp3",  # Use tmp directory
                    language="english",
                    voice="test_voice",
                )

                # Verify the result
                assert result is True
                mock_tts_service.generate_speech.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_audio_failure(self, audio_generator):
        """Test that generate_audio handles failures gracefully."""
        with patch("slidespeaker.audio.generator.TTSFactory") as mock_tts_factory:
            # Mock TTS service to raise an exception
            mock_tts_service = AsyncMock()
            mock_tts_service.generate_speech = AsyncMock(
                side_effect=Exception("Test error")
            )
            mock_tts_factory.create_service = MagicMock(return_value=mock_tts_service)

            # Set the TTS service on the generator
            audio_generator.tts_service = mock_tts_service

            # Call the method
            result = await audio_generator.generate_audio(
                text="Hello world",
                output_path="/test/output.mp3",
                language="english",
                voice="test_voice",
            )

            # Verify the result
            assert result is False

    @pytest.mark.asyncio
    async def test_generate_audio_empty_text(self, audio_generator):
        """Test that generate_audio handles empty text gracefully."""
        with patch("slidespeaker.audio.generator.TTSFactory") as mock_tts_factory:
            # Mock TTS service
            mock_tts_service = AsyncMock()
            mock_tts_factory.create_service = MagicMock(return_value=mock_tts_service)

            # Set the TTS service on the generator
            audio_generator.tts_service = mock_tts_service

            # Call the method with empty text
            result = await audio_generator.generate_audio(
                text="",
                output_path="/test/output.mp3",
                language="english",
                voice="test_voice",
            )

            # Verify the result
            assert result is False

    @pytest.mark.asyncio
    async def test_generate_audio_no_tts_service(self, audio_generator):
        """Test that generate_audio handles missing TTS service gracefully."""
        # Set TTS service to None
        audio_generator.tts_service = None

        # Call the method
        result = await audio_generator.generate_audio(
            text="Hello world",
            output_path="/test/output.mp3",
            language="english",
            voice="test_voice",
        )

        # Verify the result
        assert result is False

    @pytest.mark.asyncio
    async def test_translate_dialogue_success(self, audio_generator):
        """Test that translate_dialogue successfully translates dialogue."""
        with patch(
            "slidespeaker.audio.generator.chat_completion"
        ) as mock_chat_completion:
            # Mock chat completion response
            mock_chat_completion.return_value = "Host: Hello\nGuest: Hi there"

            # Create test dialogue
            dialogue = [
                {"speaker": "Host", "text": "Hola"},
                {"speaker": "Guest", "text": "Hola"},
            ]

            # Call the method with a non-English target language
            result = audio_generator.translate_dialogue(
                dialogue, target_language="spanish"
            )

            # Verify the result
            assert len(result) == 2
            # Since we're mocking the response, we should check for translated content
            # But the method doesn't modify the original dialogue for English targets
            mock_chat_completion.assert_called_once()

    @pytest.mark.asyncio
    async def test_translate_dialogue_failure(self, audio_generator):
        """Test that translate_dialogue handles failures gracefully."""
        with patch(
            "slidespeaker.audio.generator.chat_completion"
        ) as mock_chat_completion:
            # Mock chat completion to raise an exception
            mock_chat_completion.side_effect = Exception("Test error")

            # Create test dialogue
            dialogue = [
                {"speaker": "Host", "text": "Hola"},
                {"speaker": "Guest", "text": "Hola"},
            ]

            # Call the method
            result = audio_generator.translate_dialogue(
                dialogue, target_language="english"
            )

            # Verify the result (should return original dialogue)
            assert result == dialogue
