"""
HeyGen Avatar Service (video package)
"""

import asyncio
from pathlib import Path
from typing import Any

import requests
from loguru import logger

from slidespeaker.configs.config import config

from .interface import AvatarInterface


class HeyGenAvatarService(AvatarInterface):
    def __init__(self) -> None:
        self.api_key = config.heygen_api_key
        self.api_url = "https://api.heygen.com/v2"
        self.default_avatar_id = "Judy"
        self.default_voice_id = "1bd001e7e50f421d891986aad5158bc8"

    async def generate_avatar_video(
        self, script: str, output_path: Path, **kwargs: Any
    ) -> bool:
        if not self.is_available():
            raise ValueError(
                "HeyGen API key not configured. Please set HEYGEN_API_KEY in your .env file"
            )

        avatar_id = kwargs.get("avatar_id", self.default_avatar_id)
        voice_id = kwargs.get("voice_id", self.default_voice_id)

        logger.info(f"Generating HeyGen avatar video with {len(script)} characters")

        try:
            task_id = await self._create_talking_avatar_task(
                script, avatar_id, voice_id
            )
            logger.info(f"HeyGen task created with ID: {task_id}")

            video_url = await self._wait_for_task_completion(task_id)
            logger.info(f"HeyGen video ready at: {video_url}")

            await self._download_video(video_url, output_path)
            logger.info(f"HeyGen video downloaded to: {output_path}")
            return True
        except Exception as e:
            logger.error(f"HeyGen API Error: {e}")
            raise

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key != "your_heygen_api_key_here")

    def get_supported_options(self) -> dict[str, Any]:
        return {
            "avatars": ["Judy", "Anna", "Brian", "Emma"],
            "voices": ["1bd001e7e50f421d891986aad5158bc8"],
            "features": ["talking_avatar", "custom_background", "hd_quality"],
        }

    async def _create_talking_avatar_task(
        self, script: str, avatar_id: str, voice_id: str
    ) -> str:
        url = f"{self.api_url}/video/generate"
        headers = {"X-Api-Key": self.api_key, "Content-Type": "application/json"}

        payload = {
            "video_inputs": [
                {
                    "character": {
                        "type": "avatar",
                        "avatar_id": avatar_id,
                        "avatar_style": "normal",
                    },
                    "voice": {
                        "type": "text",
                        "input_text": script,
                        "voice_id": voice_id,
                    },
                    "background": {"type": "color", "value": "#FFFFFF"},
                }
            ],
            "dimension": {"width": 1280, "height": 720},
            "test": True,
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return str(data["data"]["task_id"])
        except Exception as e:
            logger.error(f"HeyGen task creation failed: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text[:500]}")
            raise

    async def _wait_for_task_completion(
        self, task_id: str, max_retries: int = 30
    ) -> str:
        url = f"{self.api_url}/video/task/{task_id}"
        headers = {"X-Api-Key": self.api_key}

        for _attempt in range(max_retries):
            try:
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                status = str(data["data"]["status"])

                if status == "completed":
                    return str(data["data"]["video_url"])
                elif status == "failed":
                    raise Exception(
                        f"HeyGen task failed: {data.get('error', 'Unknown error')}"
                    )

                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Error checking HeyGen task status: {e}")
                await asyncio.sleep(2)

        raise Exception("HeyGen task timeout")

    async def _download_video(self, video_url: str, output_path: Path) -> None:
        try:
            response = requests.get(video_url, stream=True)
            response.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        except Exception as e:
            logger.error(f"Error downloading HeyGen video: {e}")
            raise
