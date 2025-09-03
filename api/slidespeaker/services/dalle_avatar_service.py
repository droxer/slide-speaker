"""
DALL-E + TTS Avatar Service Implementation
Alternative avatar service using DALL-E images and TTS audio
"""

from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from loguru import logger

from .avatar_interface import AvatarInterface
from ..processing.image_generator import ImageGenerator
from ..processing.video_composer import VideoComposer
from .tts_factory import TTSFactory

load_dotenv()


class DalleAvatarService(AvatarInterface):
    """DALL-E + TTS avatar video generation implementation"""

    def __init__(self) -> None:
        self.image_service = ImageGenerator()
        self.video_composer = VideoComposer()

    async def generate_avatar_video(
        self,
        script: str,
        output_path: Path,
        **kwargs: Any,
    ) -> bool:
        """Generate avatar video using DALL-E images and TTS audio"""
        try:
            logger.info(f"Generating DALL-E avatar video for {len(script)} characters")

            # Create temporary files
            temp_dir = output_path.parent / "temp"
            temp_dir.mkdir(exist_ok=True)

            audio_path = temp_dir / f"audio_{output_path.stem}.mp3"
            image_path = temp_dir / f"image_{output_path.stem}.png"

            # Generate audio using TTS service
            tts_service = TTSFactory.create_service()
            voices = tts_service.get_supported_voices(kwargs.get("language", "english"))
            voice = kwargs.get("voice_id") or (voices[0] if voices else None)

            await tts_service.generate_speech(
                script, audio_path, language=kwargs.get("language", "english"), voice=voice
            )

            # Generate image with DALL-E
            content_for_image = kwargs.get("slide_content") or self._extract_keywords(script)
            image_style = kwargs.get("image_style", "professional")
            
            if kwargs.get("use_simple_background", False):
                await self.image_service.generate_simple_background(image_path, 
                                                                  kwargs.get("bg_color", "#f0f4f8"))
            else:
                await self.image_service.generate_presentation_image(
                    content_for_image, image_path, style=image_style
                )

            # Compose video with static image and audio
            await self.video_composer.create_slide_video(image_path, audio_path, output_path)

            # Cleanup temp files
            await self._cleanup_temp_files([audio_path, image_path])

            logger.info(f"DALL-E avatar video complete: {output_path}")
            return True

        except Exception as e:
            logger.error(f"DALL-E avatar generation error: {e}")
            # Cleanup on error
            await self._cleanup_temp_files([audio_path, image_path])
            raise

    def is_available(self) -> bool:
        """DALL-E avatar service is always available if TTS is configured"""
        try:
            tts_service = TTSFactory.create_service()
            return tts_service.is_available()
        except Exception:
            return False

    def get_supported_options(self) -> dict[str, Any]:
        """Get supported DALL-E configuration options"""
        return {
            "avatars": ["generated_images"],  # Uses generated images instead of avatars
            "voices": "via_tts_service",  # Delegated to TTS service
            "features": ["dalle_images", "custom_backgrounds", "text_overlay"],
            "styles": ["professional", "modern", "creative", "minimal"],
        }

    def _extract_keywords(self, text: str, max_words: int = 10) -> str:
        """Extract keywords from script for image generation"""
        words = text.split()
        return " ".join(words[:max_words])

    async def _cleanup_temp_files(self, file_paths: list[Path]) -> None:
        """Cleanup temporary files"""
        for file_path in file_paths:
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception as e:
                logger.warning(f"Could not cleanup {file_path}: {e}")