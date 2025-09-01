import os
import asyncio
from pathlib import Path
from typing import Optional, Literal
from dotenv import load_dotenv
from loguru import logger

from slidespeaker.avatar_service import AvatarService
from slidespeaker.avatar_service_alt import AvatarServiceAlt

load_dotenv()

class UnifiedAvatarService:
    """
    Unified avatar service that can use either HeyGen or alternative (DALL-E + ElevenLabs)
    """
    
    def __init__(self):
        self.heygen_service = AvatarService()
        self.alt_service = AvatarServiceAlt()
    
    async def generate_avatar_video(self, script: str, output_path: Path, 
                                  provider: Literal["heygen", "alternative"] = "alternative",
                                  **kwargs):
        """
        Generate avatar video using specified provider
        
        Args:
            provider: "heygen" for HeyGen API, "alternative" for DALL-E + ElevenLabs
            **kwargs: Additional provider-specific parameters
        """
        
        if provider == "heygen":
            logger.info(f"Using HeyGen provider for avatar video")
            return await self._generate_with_heygen(script, output_path, **kwargs)
        elif provider == "alternative":
            logger.info(f"Using alternative provider (DALL-E + ElevenLabs) for avatar video")
            return await self._generate_with_alternative(script, output_path, **kwargs)
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    async def _generate_with_heygen(self, script: str, output_path: Path, **kwargs):
        """Generate using HeyGen API"""
        try:
            return await self.heygen_service.generate_avatar_video(
                script=script,
                output_path=output_path,
                avatar_id=kwargs.get('avatar_id'),
                voice_id=kwargs.get('voice_id')
            )
        except Exception as e:
            logger.error(f"HeyGen generation failed: {e}")
            
            # Fallback to alternative if HeyGen fails
            if kwargs.get('fallback_to_alternative', True):
                logger.warning("Falling back to alternative provider")
                return await self._generate_with_alternative(script, output_path, **kwargs)
            raise
    
    async def _generate_with_alternative(self, script: str, output_path: Path, **kwargs):
        """Generate using alternative provider"""
        try:
            # Use detailed version by default, fallback to simple if needed
            use_simple = kwargs.get('use_simple_background', False)
            
            if use_simple:
                return await self.alt_service.generate_simple_slide(
                    script=script,
                    output_path=output_path,
                    voice_id=kwargs.get('voice_id'),
                    bg_color=kwargs.get('bg_color', "#f0f4f8")
                )
            else:
                return await self.alt_service.generate_slide_video(
                    script=script,
                    output_path=output_path,
                    slide_content=kwargs.get('slide_content'),
                    voice_id=kwargs.get('voice_id'),
                    image_style=kwargs.get('image_style', "professional")
                )
                
        except Exception as e:
            logger.error(f"Alternative generation failed: {e}")
            raise
    
    async def get_available_providers(self):
        """Check which providers are available"""
        available = {"alternative": True}  # Alternative is always available
        
        # Check if HeyGen is configured
        heygen_key = os.getenv("HEYGEN_API_KEY")
        available["heygen"] = heygen_key and heygen_key != 'your_heygen_api_key_here'
        
        return available