import os
import asyncio
import requests
import json
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

class AvatarService:
    def __init__(self):
        self.api_key = os.getenv("HEYGEN_API_KEY")
        self.api_url = "https://api.heygen.com/v2"
    
    async def generate_avatar_video(self, script: str, output_path: Path, 
                                  avatar_id: Optional[str] = None, 
                                  voice_id: Optional[str] = None):
        if not self.api_key or self.api_key == 'your_heygen_api_key_here':
            raise ValueError("HeyGen API key not configured. Please set HEYGEN_API_KEY in your .env file")
        
        avatar_id = avatar_id or "Judy"  # Default avatar
        voice_id = voice_id or "1bd001e7e50f421d891986aad5158bc8"  # Default voice
        
        logger.info(f"Generating avatar video with {len(script)} characters")
        logger.debug(f"API Key: {self.api_key[:10]}... (length: {len(self.api_key)})")
        
        try:
            # Create talking avatar task
            task_id = await self._create_talking_avatar_task(script, avatar_id, voice_id)
            logger.info(f"Task created with ID: {task_id}")
            
            # Wait for task completion and download video
            video_url = await self._wait_for_task_completion(task_id)
            logger.info(f"Video ready at: {video_url}")
            
            await self._download_video(video_url, output_path)
            logger.info(f"Video downloaded to: {output_path}")
            
        except Exception as e:
            logger.error(f"API Error: {e}")
            logger.error("Please check:")
            logger.error("1. Your HEYGEN_API_KEY is valid and properly configured")
            logger.error("2. You have access to HeyGen API v2")
            logger.error("3. The API endpoints are correct")
            raise
    
    async def _create_talking_avatar_task(self, script: str, avatar_id: str, voice_id: str) -> str:
        url = f"{self.api_url}/video/generate"
        headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "video_inputs": [
                {
                    "character": {
                        "type": "avatar",
                        "avatar_id": avatar_id,
                        "avatar_style": "normal"
                    },
                    "voice": {
                        "type": "text",
                        "input_text": script,
                        "voice_id": voice_id
                    },
                    "background": {
                        "type": "color",
                        "value": "#FFFFFF"
                    }
                }
            ],
            "dimension": {
                "width": 1280,
                "height": 720
            },
            "test": True  # Remove in production
        }
        
        logger.debug(f"POST {url}")
        logger.debug(f"Payload keys: {list(payload.keys())}")
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            logger.debug(f"Response status: {response.status_code}")
            
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"Response data keys: {list(data.keys()) if isinstance(data, dict) else 'not dict'}")
            
            return data["data"]["task_id"]
            
        except Exception as e:
            logger.error(f"API error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response headers: {dict(e.response.headers)}")
                logger.error(f"Response text: {e.response.text[:500]}")
            raise
    
    async def _wait_for_task_completion(self, task_id: str, max_retries: int = 30) -> str:
        url = f"{self.api_url}/video/task/{task_id}"
        headers = {
            "X-Api-Key": self.api_key
        }
        
        for _ in range(max_retries):
            try:
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                status = data["data"]["status"]
                
                if status == "completed":
                    return data["data"]["video_url"]
                elif status == "failed":
                    raise Exception(f"HeyGen task failed: {data.get('error', 'Unknown error')}")
                
                await asyncio.sleep(2)  # Wait 2 seconds before checking again
                
            except Exception as e:
                logger.error(f"Error checking task status: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    logger.error(f"Response status: {e.response.status_code}")
                    logger.error(f"Response text: {e.response.text}")
                await asyncio.sleep(2)
        
        raise Exception("HeyGen task timeout")
    
    async def _download_video(self, video_url: str, output_path: Path):
        try:
            response = requests.get(video_url, stream=True)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        
        except Exception as e:
            logger.error(f"Error downloading video: {e}")
            raise