import os
import asyncio
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from loguru import logger

from slidespeaker.image_service import ImageService
from slidespeaker.tts_service import TTSService
from slidespeaker.video_composer import VideoComposer

load_dotenv()

class AvatarServiceAlt:
    """
    Alternative avatar service using DALL-E images + ElevenLabs TTS
    instead of HeyGen avatar videos
    """
    
    def __init__(self):
        self.image_service = ImageService()
        self.tts_service = TTSService()
        self.video_composer = VideoComposer()
    
    async def generate_slide_video(self, script: str, output_path: Path, 
                                 slide_content: Optional[str] = None,
                                 voice_id: Optional[str] = None,
                                 image_style: str = "professional"):
        """
        Generate a video slide with DALL-E image and ElevenLabs audio
        """
        try:
            logger.info(f"Generating alternative avatar video for {len(script)} chars")
            
            # Create temporary files
            temp_dir = output_path.parent / "temp"
            temp_dir.mkdir(exist_ok=True)
            
            audio_path = temp_dir / f"audio_{output_path.stem}.mp3"
            image_path = temp_dir / f"image_{output_path.stem}.png"
            
            # Generate audio with OpenAI TTS (ElevenLabs fallback)
            logger.info("Generating audio with OpenAI TTS...")
            try:
                await self.tts_service.generate_speech(
                    script, audio_path, provider="openai"
                )
            except Exception as e:
                logger.warning(f"OpenAI TTS failed, trying ElevenLabs: {e}")
                await self.tts_service.generate_speech(
                    script, audio_path, provider="elevenlabs", voice_id=voice_id
                )
            
            # Generate image with DALL-E
            logger.info("Generating image with DALL-E...")
            content_for_image = slide_content or self._extract_keywords(script)
            await self.image_service.generate_presentation_image(
                content_for_image, image_path, style=image_style
            )
            
            # Compose video with static image and audio
            logger.info("Composing video...")
            await self.video_composer.create_slide_video(
                image_path, audio_path, output_path
            )
            
            # Cleanup temp files
            await self._cleanup_temp_files([audio_path, image_path])
            
            logger.info(f"Alternative avatar video complete: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Alternative avatar generation error: {e}")
            # Cleanup on error
            await self._cleanup_temp_files([
                temp_dir / f"audio_{output_path.stem}.mp3",
                temp_dir / f"image_{output_path.stem}.png"
            ])
            raise
    
    def _extract_keywords(self, text: str, max_words: int = 10) -> str:
        """Extract keywords from script for image generation"""
        # Simple keyword extraction - first few words
        words = text.split()
        return ' '.join(words[:max_words])
    
    async def _cleanup_temp_files(self, file_paths):
        """Cleanup temporary files"""
        for file_path in file_paths:
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception as e:
                logger.warning(f"Could not cleanup {file_path}: {e}")
    
    async def generate_simple_slide(self, script: str, output_path: Path,
                                  voice_id: Optional[str] = None,
                                  bg_color: str = "#f0f4f8"):
        """
        Generate a simple slide with solid background (fast fallback)
        """
        try:
            logger.info(f"Generating simple slide for {len(script)} chars")
            
            temp_dir = output_path.parent / "temp"
            temp_dir.mkdir(exist_ok=True)
            
            audio_path = temp_dir / f"audio_simple_{output_path.stem}.mp3"
            image_path = temp_dir / f"bg_simple_{output_path.stem}.png"
            
            # Generate audio with OpenAI TTS
            await self.tts_service.generate_speech(
                script, audio_path, provider="openai"
            )
            
            # Generate simple background
            await self.image_service.generate_simple_background(image_path, bg_color)
            
            # Compose video
            await self.video_composer.create_slide_video(image_path, audio_path, output_path)
            
            # Cleanup
            await self._cleanup_temp_files([audio_path, image_path])
            
            logger.info(f"Simple slide complete: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Simple slide generation error: {e}")
            await self._cleanup_temp_files([
                temp_dir / f"audio_simple_{output_path.stem}.mp3",
                temp_dir / f"bg_simple_{output_path.stem}.png"
            ])
            raise