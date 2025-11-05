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

from slidespeaker.configs.config import config
from slidespeaker.core.task_state import TaskErrorEntry, TaskState


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

    def _create_pdf_steps(
        self,
        file_ext: str,
        voice_language: str = "english",
        subtitle_language: str | None = None,
        transcript_language: str | None = None,
        generate_subtitles: bool = True,
        generate_video: bool = True,
        generate_podcast: bool = False,
    ) -> dict[str, dict[str, Any]]:
        """Create steps for PDF processing"""
        # PDF-specific steps
        steps = {
            "segment_pdf_content": {"status": "pending", "data": None},
        }

        # Only include revise_pdf_transcripts for video processing, not for podcast-only
        if generate_video:
            steps["revise_pdf_transcripts"] = {"status": "pending", "data": None}

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
            # Include transcript translation when transcript_language (preferred)
            # or voice_language differs from English
            effective_transcript_lang = (
                transcript_language or voice_language or "english"
            ).lower()
            if effective_transcript_lang != "english":
                steps["translate_podcast_script"] = {
                    "status": "pending",
                    "data": None,
                }
            steps.update(
                {
                    "generate_podcast_audio": {"status": "pending", "data": None},
                    "generate_podcast_subtitles": {"status": "pending", "data": None},
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

        return steps

    def _create_presentation_steps(
        self,
        voice_language: str = "english",
        subtitle_language: str | None = None,
        generate_avatar: bool = False,
        generate_subtitles: bool = True,
    ) -> dict[str, dict[str, Any]]:
        """Create steps for presentation processing"""
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

        if generate_subtitles:
            steps["generate_subtitle_transcripts"] = {
                "status": "pending",
                "data": None,
            }

        return steps

    def _determine_task_type_and_source(
        self,
        file_ext: str,
        generate_video: bool,
        generate_podcast: bool,
        source_type: str | None = None,
    ) -> tuple[str, str]:
        """Determine task type and source for UI and analytics"""
        source = source_type or ("pdf" if file_ext.lower() == ".pdf" else "slides")
        if generate_video and generate_podcast:
            task_type = "both"
        elif generate_podcast and not generate_video:
            task_type = "podcast"
        else:
            task_type = "video"

        return task_type, source

    async def create_state(
        self,
        file_id: str,
        file_path: Path,
        file_ext: str,
        filename: str | None = None,
        voice_language: str = "english",
        subtitle_language: str | None = None,
        transcript_language: str | None = None,
        video_resolution: str = "hd",
        generate_avatar: bool = False,
        generate_subtitles: bool = True,
        generate_video: bool = True,
        generate_podcast: bool = False,
        voice_id: str | None = None,
        podcast_host_voice: str | None = None,
        podcast_guest_voice: str | None = None,
        task_kwargs: dict[str, Any] | None = None,
        task_id: str | None = None,
        source_type: str | None = None,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Create initial state for a file processing task"""
        # Initialize steps based on file type
        if file_ext.lower() == ".pdf":
            # PDF-specific steps
            # Avatar is not applicable for PDF
            generate_avatar = False
            steps = self._create_pdf_steps(
                file_ext,
                voice_language,
                subtitle_language,
                transcript_language,
                generate_subtitles,
                generate_video,
                generate_podcast,
            )
            current_step = "segment_pdf_content"
        else:
            # Presentation-specific steps (.ppt, .pptx, etc.)
            steps = self._create_presentation_steps(
                voice_language, subtitle_language, generate_avatar, generate_subtitles
            )
            current_step = "extract_slides"

        # Derive explicit task_type and source for UI and analytics
        task_type, source = self._determine_task_type_and_source(
            file_ext, generate_video, generate_podcast, source_type
        )

        state: dict[str, Any] = {
            "file_id": file_id,
            "file_path": str(file_path),
            "file_ext": file_ext,
            "filename": filename,
            "source": source,
            "source_type": source,
            "voice_language": voice_language,
            "subtitle_language": subtitle_language,
            "podcast_transcript_language": transcript_language,
            "video_resolution": video_resolution,
            "generate_avatar": generate_avatar,
            "generate_subtitles": generate_subtitles,
            "generate_video": generate_video,
            "generate_podcast": generate_podcast,
            "task_type": task_type,
            "status": "uploaded",
            "current_step": current_step,
            "steps": steps,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "errors": [],
        }
        if task_id:
            state["task_id"] = task_id
        if user_id:
            state["user_id"] = user_id
        if isinstance(voice_id, str) and voice_id.strip():
            state["voice_id"] = voice_id.strip()
        if isinstance(podcast_host_voice, str) and podcast_host_voice.strip():
            state["podcast_host_voice"] = podcast_host_voice.strip()
        if isinstance(podcast_guest_voice, str) and podcast_guest_voice.strip():
            state["podcast_guest_voice"] = podcast_guest_voice.strip()

        safe_task_kwargs: dict[str, Any] = {
            "voice_language": voice_language,
            "subtitle_language": subtitle_language,
            "transcript_language": transcript_language,
            "video_resolution": video_resolution,
            "generate_avatar": generate_avatar,
            "generate_subtitles": generate_subtitles,
            "generate_video": generate_video,
            "generate_podcast": generate_podcast,
        }
        if isinstance(voice_id, str) and voice_id.strip():
            safe_task_kwargs["voice_id"] = voice_id.strip()
        if isinstance(podcast_host_voice, str) and podcast_host_voice.strip():
            safe_task_kwargs["podcast_host_voice"] = podcast_host_voice.strip()
        if isinstance(podcast_guest_voice, str) and podcast_guest_voice.strip():
            safe_task_kwargs["podcast_guest_voice"] = podcast_guest_voice.strip()
        if isinstance(task_kwargs, dict):
            for key in ("voice_id", "podcast_host_voice", "podcast_guest_voice"):
                val = task_kwargs.get(key)
                if isinstance(val, str) and val.strip():
                    safe_task_kwargs[key] = val.strip()

        state["task_kwargs"] = safe_task_kwargs.copy()
        state["task_config"] = safe_task_kwargs.copy()

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
        return TaskState.from_mapping(state)

    async def get_state(self, file_id: str) -> TaskState | None:
        """Get current state for a file processing task"""
        # Prefer task-based alias if we have a mapping
        try:
            task_id = await self.redis_client.get(self._get_file2task_key(file_id))
            if task_id:
                tkey = self._get_task_key(cast(str, task_id))
                tjson = await self.redis_client.get(tkey)
                if tjson:
                    return TaskState.from_mapping(json.loads(tjson))
        except Exception:
            pass
        # Fall back to file-id state
        key = self._get_key(file_id)
        state_json = await self.redis_client.get(key)
        if state_json:
            return TaskState.from_mapping(json.loads(state_json))
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
                self._get_task_key(task_id), json.dumps(st.to_dict()), ex=86400
            )
            fid = st.get("file_id")
            if isinstance(fid, str) and fid:
                await self._save_state(fid, st)

    async def reset_steps_from_task(
        self, task_id: str, start_step: str
    ) -> TaskState | None:
        """Reset a task's state so processing can resume from a specific step."""
        st = await self.get_state_by_task(task_id)
        if not st:
            return None

        steps = st.get("steps")
        if not isinstance(steps, dict) or start_step not in steps:
            return None

        steps_to_reset: list[str] = []
        encountered = False
        for name in steps:
            if name == start_step:
                encountered = True
            if encountered:
                steps_to_reset.append(name)

        if not steps_to_reset:
            return None

        for name in steps_to_reset:
            step_state = steps.get(name)
            if not isinstance(step_state, dict):
                continue
            if step_state.get("status") == "skipped":
                # Skip steps remain skipped
                continue
            step_state["status"] = "pending"
            if "data" in step_state:
                step_state["data"] = None

        existing_errors = st.get("errors")
        if isinstance(existing_errors, list):
            st["errors"] = [
                err for err in existing_errors if err.get("step") not in steps_to_reset
            ]

        st["status"] = "processing"
        st["current_step"] = start_step
        st["updated_at"] = datetime.now().isoformat()

        await self.redis_client.set(
            self._get_task_key(task_id), json.dumps(st.to_dict()), ex=86400
        )
        fid = st.get("file_id")
        if isinstance(fid, str) and fid:
            await self._save_state(fid, st)

        return st

    async def mark_completed_by_task(self, task_id: str) -> None:
        st = await self.get_state_by_task(task_id)
        if not st:
            return
        st["status"] = "completed"
        st["updated_at"] = datetime.now().isoformat()
        await self.redis_client.set(
            self._get_task_key(task_id), json.dumps(st.to_dict()), ex=86400
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
            self._get_task_key(task_id), json.dumps(st.to_dict()), ex=86400
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
            self._get_task_key(task_id), json.dumps(st.to_dict()), ex=86400
        )
        fid = st.get("file_id")
        if isinstance(fid, str) and fid:
            await self._save_state(fid, st)

    async def set_status_by_task(self, task_id: str, status: str) -> bool:
        """Set the top-level status for a task-managed state entry."""
        st = await self.get_state_by_task(task_id)
        if not st:
            return False
        st["status"] = status
        st["updated_at"] = datetime.now().isoformat()
        await self.redis_client.set(
            self._get_task_key(task_id), json.dumps(st.to_dict()), ex=86400
        )
        fid = st.get("file_id")
        if isinstance(fid, str) and fid:
            await self._save_state(fid, st)
        return True

    async def get_state_by_task(self, task_id: str) -> TaskState | None:
        """Get state using a task_id alias.

        Looks up a direct task-state key, then resolves to file_id via mapping.
        """
        # Try direct task-state mirror first
        tkey = self._get_task_key(task_id)
        state_json = await self.redis_client.get(tkey)
        if state_json:
            return TaskState.from_mapping(json.loads(state_json))
        # Resolve mapping to file_id
        fid = await self.redis_client.get(self._get_task2file_key(task_id))
        if fid:
            return await self.get_state(cast(str, fid))
        return None

    async def get_task_state(self, file_id: str) -> TaskState | None:
        """Return a structured TaskState for the provided file identifier."""
        return await self.get_state(file_id)

    async def get_task_state_by_task(self, task_id: str) -> TaskState | None:
        """Return a structured TaskState for the provided task identifier."""
        return await self.get_state_by_task(task_id)

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
                self._get_task_key(task_id), json.dumps(st.to_dict()), ex=86400
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
            return
        if step_name not in state.get("steps", {}):
            return
        state["steps"][step_name]["status"] = status
        if data is not None:
            state["steps"][step_name]["data"] = data
        state["updated_at"] = datetime.now().isoformat()
        state["current_step"] = step_name
        task_id = state.get("task_id")
        if isinstance(task_id, str) and task_id:
            await self.redis_client.set(
                self._get_task_key(task_id),
                json.dumps(state.to_dict()),
                ex=86400,
            )
        else:
            await self._save_state(file_id, state)

    async def add_error(self, file_id: str, error: str, step: str) -> None:
        """Add error to state for a specific processing step"""
        state = await self.get_state(file_id)
        if state:
            errors_list = list(state.get("errors", []))
            errors_list.append(
                TaskErrorEntry.from_mapping(
                    {
                        "step": step,
                        "error": error,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            )
            state["errors"] = errors_list
            state["updated_at"] = datetime.now().isoformat()
            await self._save_state(file_id, state)

    async def mark_completed(self, file_id: str) -> None:
        """Mark processing as completed successfully (task-first)"""
        state = await self.get_state(file_id)
        if not state:
            return
        state["status"] = "completed"
        state["updated_at"] = datetime.now().isoformat()
        task_id = state.get("task_id")
        if isinstance(task_id, str) and task_id:
            await self.redis_client.set(
                self._get_task_key(task_id),
                json.dumps(state.to_dict()),
                ex=86400,
            )
        else:
            await self._save_state(file_id, state)

    async def mark_failed(self, file_id: str) -> None:
        """Mark processing as failed with errors (task-first)"""
        state = await self.get_state(file_id)
        if not state:
            return
        state["status"] = "failed"
        state["updated_at"] = datetime.now().isoformat()
        task_id = state.get("task_id")
        if isinstance(task_id, str) and task_id:
            await self.redis_client.set(
                self._get_task_key(task_id),
                json.dumps(state.to_dict()),
                ex=86400,
            )
        else:
            await self._save_state(file_id, state)

    async def mark_cancelled(
        self, file_id: str, cancelled_step: str | None = None
    ) -> None:
        """Mark processing as cancelled by user (task-first)"""
        state = await self.get_state(file_id)
        if not state:
            return
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
                self._get_task_key(task_id),
                json.dumps(state.to_dict()),
                ex=86400,
            )
        else:
            await self._save_state(file_id, state)

    async def _save_state(
        self, file_id: str, state: dict[str, Any] | TaskState
    ) -> None:
        """Save state to Redis with 24-hour expiration"""
        key = self._get_key(file_id)
        payload = state.to_dict() if isinstance(state, TaskState) else state
        # If state carries a task_id, prefer task-alias as the sole source of truth
        task_id = payload.get("task_id") if isinstance(payload, dict) else None
        if isinstance(task_id, str) and task_id:
            await self.redis_client.set(
                self._get_task_key(task_id), json.dumps(payload), ex=86400
            )
            # Proactively remove legacy file-id state to avoid cross-run bleed-through
            with suppress(Exception):
                await self.redis_client.delete(key)
        else:
            # Legacy path: no task_id available; write by file-id
            await self.redis_client.set(
                key, json.dumps(payload), ex=86400
            )  # 24h expiration

    # Public wrapper to avoid external modules calling the private method directly
    async def save_state(self, file_id: str, state: dict[str, Any] | TaskState) -> None:
        await self._save_state(file_id, state)

    async def save_task_state(self, file_id: str, task_state: TaskState) -> None:
        """Persist a TaskState instance."""
        await self._save_state(file_id, task_state)


# Global state manager instance
state_manager = RedisStateManager()
