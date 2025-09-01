import os
import asyncio
from pathlib import Path
from typing import Optional
from openai import OpenAI
import requests
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

class TTSService:
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
    
    async def generate_speech(self, text: str, output_path: Path, provider: str = "openai", 
                            voice: Optional[str] = None, voice_id: Optional[str] = None, 
                            language: str = "english"):
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if provider == "openai":
            await self._generate_openai_tts(text, output_path, voice, language)
        elif provider == "elevenlabs":
            await self._generate_elevenlabs_tts(text, output_path, voice_id)
        else:
            raise ValueError(f"Unsupported TTS provider: {provider}")
    
    async def _generate_openai_tts(self, text: str, output_path: Path, voice: Optional[str] = None, language: str = "english"):
        # Map languages to appropriate voices and models
        language_voices = {
            "english": "alloy",
            "chinese": "onyx",
            "japanese": "nova",
            "korean": "shimmer"
        }
        
        # Use language-specific voice if available, otherwise use default
        voice = voice or language_voices.get(language, "alloy")
        
        # Use appropriate model for better language support
        model = "tts-1"  # Default model
        if language in ["chinese", "japanese", "korean"]:
            model = "tts-1-hd"  # Higher quality model for non-English languages
        
        try:
            response = self.openai_client.audio.speech.create(
                model=model,
                voice=voice,
                input=text,
            )
            
            response.stream_to_file(output_path)
            
        except Exception as e:
            logger.error(f"OpenAI TTS error: {e}")
            raise
    
    async def _generate_elevenlabs_tts(self, text: str, output_path: Path, voice_id: Optional[str] = None):
        if not self.elevenlabs_api_key:
            raise ValueError("ElevenLabs API key not configured")
        
        voice_id = voice_id or "21m00Tcm4TlvDq8ikWAM"  # Default voice
        
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.elevenlabs_api_key
        }
        
        data = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, stream=True)
            
            if response.status_code != 200:
                raise Exception(f"ElevenLabs API error: {response.text}")
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
                        
        except Exception as e:
            logger.error(f"ElevenLabs TTS error: {e}")
            raise