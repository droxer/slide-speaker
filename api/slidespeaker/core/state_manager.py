"""
State management module for SlideSpeaker.
This module provides Redis-based state management for tracking presentation processing tasks.
It maintains the status of each step in the processing pipeline and handles state transitions.
"""

import json
from contextlib import suppress
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

    def _get_task_key(self, task_id: str) -> str:
        """Generate Redis key for a task-alias to state"""
        return f"ss:state:task:{task_id}"

    def _get_task2file_key(self, task_id: str) -> str:
        return f"ss:task2file:{task_id}"

    def _get_file2task_key(self, file_id: str) -> str:
        return f"ss:file2task:{file_id}"

    def _get_file2tasks_set_key(self, file_id: str) -> str:
        return f"ss:file2tasks:{file_id}"

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
        generate_video: bool = True,
        generate_podcast: bool = False,
        task_id: str | None = None,
    ) -> dict[str, Any]:
        """Create initial state for a file processing task"""
        # Initialize steps based on file type
        if file_ext.lower() == ".pdf":
            # PDF-specific steps
            # Avatar is not applicable for PDF
            generate_avatar = False
            steps = {
                "segment_pdf_content": {"status": "pending", "data": None},
                "revise_pdf_transcripts": {"status": "pending", "data": None},
            }

            # Video path (optional)
            if generate_video:
                steps.update(
                    {
                        "generate_pdf_chapter_images": {
                            "status": "pending",
                            "data": None,
                        },
                        "generate_pdf_audio": {"status": "pending", "data": None},
                        "generate_pdf_subtitles": {
                            "status": "pending" if generate_subtitles else "skipped",
                            "data": None,
                        },
                        "compose_video": {"status": "pending", "data": None},
                    }
                )

            # Optional podcast steps
            if generate_podcast:
                steps.update(
                    {
                        "generate_podcast_script": {"status": "pending", "data": None},
                    }
                )
                if voice_language.lower() != "english":
                    steps["translate_podcast_script"] = {
                        "status": "pending",
                        "data": None,
                    }
                steps.update(
                    {
                        "generate_podcast_audio": {"status": "pending", "data": None},
                        "compose_podcast": {"status": "pending", "data": None},
                    }
                )

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

        # Derive explicit task_type and source for UI and analytics
        source = "pdf" if file_ext.lower() == ".pdf" else "slides"
        if generate_video and generate_podcast:
            task_type = "both"
        elif generate_podcast and not generate_video:
            task_type = "podcast"
        else:
            task_type = "video"

        state: dict[str, Any] = {
            "file_id": file_id,
            "file_path": str(file_path),
            "file_ext": file_ext,
            "filename": filename,
            "source": source,
            "voice_language": voice_language,
            "subtitle_language": subtitle_language,
            "video_resolution": video_resolution,
            "generate_avatar": generate_avatar,
            "generate_subtitles": generate_subtitles,
            "generate_video": generate_video,
            "generate_podcast": generate_podcast,
            "task_type": task_type,
            "status": "uploaded",
            "current_step": "segment_pdf_content"
            if file_ext.lower() == ".pdf"
            else "extract_slides",
            "steps": steps,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "errors": [],
        }
        if task_id:
            state["task_id"] = task_id
        # If task-scoped, store task-first and bind mappings; otherwise store by file-id
        if task_id:
            try:
                # Bind mappings and mirror state under task key
                await self.bind_task(file_id, task_id)
                # Store state only under task alias for new runs (do not persist file-id state)
                state["task_id"] = task_id
                await self.redis_client.set(
                    self._get_task_key(task_id), json.dumps(state), ex=86400
                )
            except Exception:
                # Fall back to file-id state on error
                await self._save_state(file_id, state)
        else:
            await self._save_state(file_id, state)
        return state

    async def get_state(self, file_id: str) -> dict[str, Any] | None:
        """Get current state for a file processing task"""
        # Prefer task-based alias if we have a mapping
        try:
            task_id = await self.redis_client.get(self._get_file2task_key(file_id))
            if task_id:
                tkey = self._get_task_key(cast(str, task_id))
                tjson = await self.redis_client.get(tkey)
                if tjson:
                    return cast(dict[str, Any], json.loads(tjson))
        except Exception:
            pass
        # Fall back to file-id state
        key = self._get_key(file_id)
        state_json = await self.redis_client.get(key)
        if state_json:
            return cast(dict[str, Any], json.loads(state_json))
        return None

    async def update_step_status_by_task(
        self, task_id: str, step_name: str, status: str, data: Any = None
    ) -> None:
        """Update a step status using task-id as the primary key."""
        st = await self.get_state_by_task(task_id)
        if not st:
            return
        if "steps" in st and step_name in st["steps"]:
            st["steps"][step_name]["status"] = status
            if data is not None:
                st["steps"][step_name]["data"] = data
            st["updated_at"] = datetime.now().isoformat()
            st["current_step"] = step_name
            # Ensure task_id present
            st["task_id"] = task_id
            # Save under task alias (and mirror to file-id if available)
            await self.redis_client.set(
                self._get_task_key(task_id), json.dumps(st), ex=86400
            )
            fid = st.get("file_id")
            if isinstance(fid, str) and fid:
                await self._save_state(fid, st)

    async def mark_completed_by_task(self, task_id: str) -> None:
        st = await self.get_state_by_task(task_id)
        if not st:
            return
        st["status"] = "completed"
        st["updated_at"] = datetime.now().isoformat()
        await self.redis_client.set(
            self._get_task_key(task_id), json.dumps(st), ex=86400
        )
        fid = st.get("file_id")
        if isinstance(fid, str) and fid:
            await self._save_state(fid, st)

    async def mark_failed_by_task(self, task_id: str) -> None:
        st = await self.get_state_by_task(task_id)
        if not st:
            return
        st["status"] = "failed"
        st["updated_at"] = datetime.now().isoformat()
        await self.redis_client.set(
            self._get_task_key(task_id), json.dumps(st), ex=86400
        )
        fid = st.get("file_id")
        if isinstance(fid, str) and fid:
            await self._save_state(fid, st)

    async def mark_cancelled_by_task(
        self, task_id: str, cancelled_step: str | None = None
    ) -> None:
        st = await self.get_state_by_task(task_id)
        if not st:
            return
        st["status"] = "cancelled"
        st["updated_at"] = datetime.now().isoformat()
        if cancelled_step and cancelled_step in st.get("steps", {}):
            st["steps"][cancelled_step]["status"] = "cancelled"
        for _name, step_data in st.get("steps", {}).items():
            if step_data.get("status") in ("processing", "in_progress", "pending"):
                step_data["status"] = "cancelled"
        await self.redis_client.set(
            self._get_task_key(task_id), json.dumps(st), ex=86400
        )
        fid = st.get("file_id")
        if isinstance(fid, str) and fid:
            await self._save_state(fid, st)

    async def get_state_by_task(self, task_id: str) -> dict[str, Any] | None:
        """Get state using a task_id alias.

        Looks up a direct task-state key, then resolves to file_id via mapping.
        """
        # Try direct task-state mirror first
        tkey = self._get_task_key(task_id)
        state_json = await self.redis_client.get(tkey)
        if state_json:
            return cast(dict[str, Any], json.loads(state_json))
        # Resolve mapping to file_id
        fid = await self.redis_client.get(self._get_task2file_key(task_id))
        if fid:
            return await self.get_state(cast(str, fid))
        return None

    async def get_file_id_by_task(self, task_id: str) -> str | None:
        """Return file_id if we have a mapping for this task_id."""
        fid = await self.redis_client.get(self._get_task2file_key(task_id))
        return cast(str | None, fid)

    async def bind_task(
        self, file_id: str, task_id: str, ttl_seconds: int = 60 * 60 * 24 * 30
    ) -> None:
        """Bind a task_id to a file_id and mirror state under a task key for easy lookup."""
        await self.redis_client.set(
            self._get_task2file_key(task_id), file_id, ex=ttl_seconds
        )
        # Backward-compat single mapping (keep, but don't rely on it for multi-tasks)
        await self.redis_client.set(
            self._get_file2task_key(file_id), task_id, ex=ttl_seconds
        )
        # Multi-task set mapping (preferred)
        try:
            _ = await self.redis_client.sadd(
                self._get_file2tasks_set_key(file_id), task_id
            )  # type: ignore[misc]
            await self.redis_client.expire(
                self._get_file2tasks_set_key(file_id), ttl_seconds
            )
        except Exception:
            pass
        # Mirror state under a task-key (best-effort)
        st = await self.get_state(file_id)
        if st is not None:
            st["task_id"] = task_id
            await self.redis_client.set(
                self._get_task_key(task_id), json.dumps(st), ex=86400
            )
        # Proactively delete legacy file-id state key; task alias is the source of truth
        with suppress(Exception):
            await self.redis_client.delete(self._get_key(file_id))

    async def unbind_task(self, file_id: str | None, task_id: str) -> int:
        """Remove task_id from file2tasks set; return remaining count."""
        if not file_id:
            return 0
        try:
            await self.redis_client.srem(self._get_file2tasks_set_key(file_id), task_id)  # type: ignore
            remaining = await self.redis_client.scard(
                self._get_file2tasks_set_key(file_id)
            )  # type: ignore
            return int(remaining or 0)
        except Exception:
            return 0

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
        """Update status of a specific processing step (task-first)."""
        state = await self.get_state(file_id)
        if not state:
            logger.warning(
                f"Cannot update step status for non-existent state: {file_id}"
            )
            return
        if step_name not in state.get("steps", {}):
            logger.warning(f"Step {step_name} not found in state for file {file_id}")
            return
        old_status = state["steps"][step_name]["status"]
        state["steps"][step_name]["status"] = status
        if data is not None:
            state["steps"][step_name]["data"] = data
        state["updated_at"] = datetime.now().isoformat()
        state["current_step"] = step_name
        task_id = state.get("task_id")
        if isinstance(task_id, str) and task_id:
            await self.redis_client.set(
                self._get_task_key(task_id), json.dumps(state), ex=86400
            )
        else:
            await self._save_state(file_id, state)
        logger.debug(
            f"Step {step_name} status updated from '{old_status}' to '{status}' for file {file_id}"
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
        """Mark processing as completed successfully (task-first)"""
        state = await self.get_state(file_id)
        if not state:
            return
        old_status = state.get("status")
        state["status"] = "completed"
        state["updated_at"] = datetime.now().isoformat()
        task_id = state.get("task_id")
        if isinstance(task_id, str) and task_id:
            await self.redis_client.set(
                self._get_task_key(task_id), json.dumps(state), ex=86400
            )
        else:
            await self._save_state(file_id, state)
        logger.info(
            f"Processing marked as completed for file {file_id} (was {old_status})"
        )

    async def mark_failed(self, file_id: str) -> None:
        """Mark processing as failed with errors (task-first)"""
        state = await self.get_state(file_id)
        if not state:
            return
        old_status = state.get("status")
        state["status"] = "failed"
        state["updated_at"] = datetime.now().isoformat()
        task_id = state.get("task_id")
        if isinstance(task_id, str) and task_id:
            await self.redis_client.set(
                self._get_task_key(task_id), json.dumps(state), ex=86400
            )
        else:
            await self._save_state(file_id, state)
        logger.error(
            f"Processing marked as failed for file {file_id} (was {old_status})"
        )

    async def mark_cancelled(
        self, file_id: str, cancelled_step: str | None = None
    ) -> None:
        """Mark processing as cancelled by user (task-first)"""
        state = await self.get_state(file_id)
        if not state:
            return
        old_status = state.get("status")
        state["status"] = "cancelled"
        state["updated_at"] = datetime.now().isoformat()
        if cancelled_step and cancelled_step in state.get("steps", {}):
            state["steps"][cancelled_step]["status"] = "cancelled"
        for _step_name, step_data in state.get("steps", {}).items():
            if step_data.get("status") in ("processing", "in_progress", "pending"):
                step_data["status"] = "cancelled"
        task_id = state.get("task_id")
        if isinstance(task_id, str) and task_id:
            await self.redis_client.set(
                self._get_task_key(task_id), json.dumps(state), ex=86400
            )
        else:
            await self._save_state(file_id, state)
        logger.info(
            f"Processing marked as cancelled for file {file_id} (was {old_status})"
        )

    async def _save_state(self, file_id: str, state: dict[str, Any]) -> None:
        """Save state to Redis with 24-hour expiration"""
        key = self._get_key(file_id)
        # If state carries a task_id, prefer task-alias as the sole source of truth
        task_id = state.get("task_id") if isinstance(state, dict) else None
        if isinstance(task_id, str) and task_id:
            await self.redis_client.set(
                self._get_task_key(task_id), json.dumps(state), ex=86400
            )
            # Proactively remove legacy file-id state to avoid cross-run bleed-through
            with suppress(Exception):
                await self.redis_client.delete(key)
        else:
            # Legacy path: no task_id available; write by file-id
            await self.redis_client.set(
                key, json.dumps(state), ex=86400
            )  # 24h expiration

    # Public wrapper to avoid external modules calling the private method directly
    async def save_state(self, file_id: str, state: dict[str, Any]) -> None:
        await self._save_state(file_id, state)


# Global state manager instance
state_manager = RedisStateManager()
