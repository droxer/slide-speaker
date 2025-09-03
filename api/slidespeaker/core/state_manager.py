import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import redis.asyncio as redis
from dotenv import load_dotenv

load_dotenv()


class RedisStateManager:
    def __init__(self) -> None:
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=int(os.getenv("REDIS_DB", 0)),
            password=os.getenv("REDIS_PASSWORD", None),
            decode_responses=True,
            socket_timeout=5.0,  # Add timeout to prevent hanging
        )

    def _get_key(self, file_id: str) -> str:
        return f"ai_slider:state:{file_id}"

    async def create_state(
        self,
        file_id: str,
        file_path: Path,
        file_ext: str,
        audio_language: str = "english",
        subtitle_language: str | None = None,
        generate_avatar: bool = True,
        generate_subtitles: bool = True,
    ) -> dict[str, Any]:
        """Create initial state for a file processing"""
        # Initialize steps - conditionally include subtitle script steps based on language needs
        steps = {
            "extract_slides": {"status": "pending", "data": None},
            "convert_slides_to_images": {"status": "pending", "data": None},
            "analyze_slide_images": {"status": "pending", "data": None},
            "generate_scripts": {"status": "pending", "data": None},
            "review_scripts": {"status": "pending", "data": None},
            "generate_audio": {"status": "pending", "data": None},
            "generate_avatar_videos": {
                "status": "pending" if generate_avatar else "skipped",
                "data": None,
            },
            "generate_subtitles": {
                "status": "pending",  # Always generate subtitles
                "data": None,
            },
            "compose_video": {"status": "pending", "data": None},
        }

        # Only include subtitle script generation steps if languages are different
        # Default to audio language if subtitle language is not specified
        effective_subtitle_language = (
            subtitle_language if subtitle_language is not None else audio_language
        )
        if audio_language != effective_subtitle_language:
            steps.update(
                {
                    "generate_subtitle_scripts": {"status": "pending", "data": None},
                    "review_subtitle_scripts": {"status": "pending", "data": None},
                }
            )

        state: dict[str, Any] = {
            "file_id": file_id,
            "file_path": str(file_path),
            "file_ext": file_ext,
            "audio_language": audio_language,
            "subtitle_language": subtitle_language,
            "generate_avatar": generate_avatar,
            "generate_subtitles": generate_subtitles,
            "status": "uploaded",
            "current_step": "extract_slides",
            "steps": steps,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "errors": [],
        }
        await self._save_state(file_id, state)
        return state

    async def get_state(self, file_id: str) -> dict[str, Any] | None:
        """Get current state for a file"""
        key = self._get_key(file_id)
        state_json = await self.redis_client.get(key)
        if state_json:
            return cast(dict[str, Any], json.loads(state_json))
        return None

    async def update_step_status(
        self, file_id: str, step_name: str, status: str, data: Any = None
    ) -> None:
        """Update status of a specific step"""
        state = await self.get_state(file_id)
        if state:
            state["steps"][step_name]["status"] = status
            if data is not None:
                state["steps"][step_name]["data"] = data
            state["updated_at"] = datetime.now().isoformat()
            state["current_step"] = step_name
            await self._save_state(file_id, state)

    async def add_error(self, file_id: str, error: str, step: str) -> None:
        """Add error to state"""
        state = await self.get_state(file_id)
        if state:
            state["errors"].append(
                {"step": step, "error": error, "timestamp": datetime.now().isoformat()}
            )
            state["updated_at"] = datetime.now().isoformat()
            await self._save_state(file_id, state)

    async def mark_completed(self, file_id: str) -> None:
        """Mark processing as completed"""
        state = await self.get_state(file_id)
        if state:
            state["status"] = "completed"
            state["updated_at"] = datetime.now().isoformat()
            await self._save_state(file_id, state)

    async def mark_failed(self, file_id: str) -> None:
        """Mark processing as failed"""
        state = await self.get_state(file_id)
        if state:
            state["status"] = "failed"
            state["updated_at"] = datetime.now().isoformat()
            await self._save_state(file_id, state)

    async def _save_state(self, file_id: str, state: dict[str, Any]) -> None:
        """Save state to Redis"""
        key = self._get_key(file_id)
        await self.redis_client.set(key, json.dumps(state), ex=86400)  # 24h expiration


# Global state manager instance
state_manager = RedisStateManager()
