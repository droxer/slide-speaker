"""
State management module for SlideSpeaker.
This module provides Redis-based state management for tracking presentation processing tasks.
It maintains the status of each step in the processing pipeline and handles state transitions.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from loguru import logger

from slidespeaker.configs.config import config


class RedisStateManager:
    """Redis-based state manager for tracking presentation processing tasks"""

    def __init__(self) -> None:
        """Initialize the state manager with a Redis client connection"""
        from slidespeaker.configs.redis_config import RedisConfig

        self.redis_client = RedisConfig.get_redis_client()

    def _get_key(self, file_id: str) -> str:
        """Generate Redis key for a file's state"""
        return f"ss:state:{file_id}"

    async def create_state(
        self,
        file_id: str,
        file_path: Path,
        file_ext: str,
        filename: str | None = None,
        voice_language: str = "english",
        subtitle_language: str | None = None,
        video_resolution: str = "hd",
        generate_avatar: bool = True,
        generate_subtitles: bool = True,
    ) -> dict[str, Any]:
        """Create initial state for a file processing task"""
        # Initialize steps based on file type
        if file_ext.lower() == ".pdf":
            # PDF-specific steps
            steps = {
                "segment_pdf_content": {"status": "pending", "data": None},
                "revise_pdf_transcripts": {"status": "pending", "data": None},
                "generate_pdf_chapter_images": {"status": "pending", "data": None},
                "generate_pdf_audio": {"status": "pending", "data": None},
                "generate_pdf_subtitles": {
                    "status": "pending" if generate_subtitles else "skipped",
                    "data": None,
                },
                "compose_video": {"status": "pending", "data": None},
            }

            # Add translation steps if needed
            if voice_language.lower() != "english":
                steps["translate_voice_transcripts"] = {
                    "status": "pending",
                    "data": None,
                }
            if subtitle_language and subtitle_language.lower() != "english":
                steps["translate_subtitle_transcripts"] = {
                    "status": "pending",
                    "data": None,
                }
        else:
            # Presentation-specific steps (.ppt, .pptx, etc.)
            steps = {
                "extract_slides": {"status": "pending", "data": None},
                "convert_slides_to_images": {"status": "pending", "data": None},
                "analyze_slide_images": {
                    "status": "pending" if config.enable_visual_analysis else "skipped",
                    "data": None,
                },
                "generate_transcripts": {"status": "pending", "data": None},
                "revise_transcripts": {"status": "pending", "data": None},
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

            # Add translation steps
            if voice_language.lower() != "english":
                steps["translate_voice_transcripts"] = {
                    "status": "pending",
                    "data": None,
                }
            if subtitle_language and subtitle_language.lower() != "english":
                steps["translate_subtitle_transcripts"] = {
                    "status": "pending",
                    "data": None,
                }

            # Only include subtitle script generation steps if languages are different
            # Default to audio language if subtitle language is not specified
            effective_subtitle_language = (
                subtitle_language if subtitle_language is not None else voice_language
            )
            if voice_language != effective_subtitle_language:
                steps.update(
                    {
                        "generate_subtitle_transcripts": {
                            "status": "pending",
                            "data": None,
                        },
                    }
                )

        state: dict[str, Any] = {
            "file_id": file_id,
            "file_path": str(file_path),
            "file_ext": file_ext,
            "filename": filename,
            "voice_language": voice_language,
            "subtitle_language": subtitle_language,
            "video_resolution": video_resolution,
            "generate_avatar": generate_avatar,
            "generate_subtitles": generate_subtitles,
            "status": "uploaded",
            "current_step": "segment_pdf_content"
            if file_ext.lower() == ".pdf"
            else "extract_slides",
            "steps": steps,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "errors": [],
        }
        await self._save_state(file_id, state)
        return state

    async def get_state(self, file_id: str) -> dict[str, Any] | None:
        """Get current state for a file processing task"""
        key = self._get_key(file_id)
        state_json = await self.redis_client.get(key)
        if state_json:
            return cast(dict[str, Any], json.loads(state_json))
        return None

    async def get_step_status(
        self, file_id: str, step_name: str
    ) -> dict[str, Any] | None:
        """Get the status of a specific processing step"""
        state = await self.get_state(file_id)
        if state and "steps" in state and step_name in state["steps"]:
            return dict(state["steps"][step_name])
        return None

    async def update_step_status(
        self, file_id: str, step_name: str, status: str, data: Any = None
    ) -> None:
        """Update status of a specific processing step"""
        state = await self.get_state(file_id)
        if state:
            if step_name in state["steps"]:
                old_status = state["steps"][step_name]["status"]
                state["steps"][step_name]["status"] = status
                if data is not None:
                    state["steps"][step_name]["data"] = data
                state["updated_at"] = datetime.now().isoformat()
                state["current_step"] = step_name
                await self._save_state(file_id, state)
                logger.debug(
                    f"Step {step_name} status updated from '{old_status}' to '{status}' for file {file_id}"
                )
            else:
                logger.warning(
                    f"Step {step_name} not found in state for file {file_id}"
                )
        else:
            logger.warning(
                f"Cannot update step status for non-existent state: {file_id}"
            )

    async def add_error(self, file_id: str, error: str, step: str) -> None:
        """Add error to state for a specific processing step"""
        logger.warning(
            f"Adding error to state for file {file_id}, step {step}: {error}"
        )
        state = await self.get_state(file_id)
        if state:
            state["errors"].append(
                {"step": step, "error": error, "timestamp": datetime.now().isoformat()}
            )
            state["updated_at"] = datetime.now().isoformat()
            await self._save_state(file_id, state)
            logger.info(
                f"Error added to state for file {file_id}, now has {len(state['errors'])} errors"
            )

    async def mark_completed(self, file_id: str) -> None:
        """Mark processing as completed successfully"""
        state = await self.get_state(file_id)
        if state:
            old_status = state["status"]
            state["status"] = "completed"
            state["updated_at"] = datetime.now().isoformat()
            await self._save_state(file_id, state)
            logger.info(
                f"Processing marked as completed for file {file_id} (was {old_status})"
            )

    async def mark_failed(self, file_id: str) -> None:
        """Mark processing as failed with errors"""
        state = await self.get_state(file_id)
        if state:
            old_status = state["status"]
            state["status"] = "failed"
            state["updated_at"] = datetime.now().isoformat()
            await self._save_state(file_id, state)
            logger.error(
                f"Processing marked as failed for file {file_id} (was {old_status})"
            )

    async def mark_cancelled(
        self, file_id: str, cancelled_step: str | None = None
    ) -> None:
        """Mark processing as cancelled by user"""
        state = await self.get_state(file_id)
        if state:
            old_status = state["status"]
            state["status"] = "cancelled"
            state["updated_at"] = datetime.now().isoformat()

            # Mark the current step as cancelled if provided
            if cancelled_step and cancelled_step in state["steps"]:
                state["steps"][cancelled_step]["status"] = "cancelled"

            # Mark any pending steps as cancelled
            for _step_name, step_data in state["steps"].items():
                if (
                    step_data["status"] == "in_progress"
                    or step_data["status"] == "pending"
                ):
                    step_data["status"] = "cancelled"

            await self._save_state(file_id, state)
            logger.info(
                f"Processing marked as cancelled for file {file_id} (was {old_status})"
            )

    async def _save_state(self, file_id: str, state: dict[str, Any]) -> None:
        """Save state to Redis with 24-hour expiration"""
        key = self._get_key(file_id)
        await self.redis_client.set(key, json.dumps(state), ex=86400)  # 24h expiration


# Global state manager instance
state_manager = RedisStateManager()
