"""
File purger for SlideSpeaker.

This module provides functionality to purge generated files when tasks are deleted.
It uses the existing task queue system to handle file deletion asynchronously and
collects storage keys from task state/artifacts to ensure complete cleanup.
"""

from __future__ import annotations

import shutil
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from loguru import logger

from slidespeaker.configs.config import config, get_storage_provider
from slidespeaker.core.state_manager import state_manager
from slidespeaker.core.task_queue import task_queue
from slidespeaker.storage import StorageProvider
from slidespeaker.storage.paths import (
    OUTPUTS_PREFIX,
    UPLOADS_PREFIX,
    object_key_from_uri,
    upload_object_key,
)


class FilePurger:
    """Purger for removing generated files when tasks are deleted."""

    def __init__(self) -> None:
        """Initialize the file purger."""
        self.storage_provider: StorageProvider = get_storage_provider()
        self.output_dir = config.output_dir

    async def enqueue_file_purge(
        self,
        file_id: str,
        *,
        target_task_id: str | None = None,
        file_ext: str | None = None,
        storage_keys: Iterable[str] | None = None,
        local_paths: Iterable[str] | None = None,
    ) -> str | None:
        """
        Enqueue a file purge task to be processed asynchronously through the task queue.

        Args:
            file_id: The file ID of the task to purge
            target_task_id: Optional task_id whose artifacts should be purged
            file_ext: Optional uploaded file extension hint
            storage_keys: Pre-collected storage object keys to delete
            local_paths: Pre-collected local filesystem paths to delete

        Returns:
            The task ID of the purge task, or None if submission failed
        """
        try:
            payload: dict[str, Any] = {"file_id": file_id}
            if target_task_id:
                payload["target_task_id"] = target_task_id
            if file_ext:
                payload["file_ext"] = file_ext
            if storage_keys:
                normalized_keys = {
                    key for k in storage_keys if (key := self._normalize_storage_key(k))
                }
                if normalized_keys:
                    payload["storage_keys"] = sorted(normalized_keys)
            if local_paths:
                normalized_paths = {
                    path for p in local_paths if (path := self._normalize_local_path(p))
                }
                if normalized_paths:
                    payload["local_paths"] = sorted(normalized_paths)

            task_id = await task_queue.submit_task(
                task_type="file_purge",
                **payload,
            )
            logger.info(
                "Enqueued file purge task %s for file_id=%s target_task_id=%s",
                task_id,
                file_id,
                target_task_id,
            )
            return task_id
        except Exception as e:
            logger.error(f"Error enqueuing file purge task for file_id {file_id}: {e}")
            return None

    async def collect_artifacts(
        self,
        file_id: str,
        *,
        task_id: str | None = None,
        file_ext: str | None = None,
        extra_storage_keys: Iterable[str] | None = None,
        extra_local_paths: Iterable[str] | None = None,
    ) -> tuple[set[str], set[str]]:
        """Collect storage keys and local paths associated with a file/task."""
        storage_keys: set[str] = set()
        local_paths: set[str] = set()

        if extra_storage_keys:
            for key in extra_storage_keys:
                normalized = self._normalize_storage_key(key)
                if normalized:
                    storage_keys.add(normalized)
        if extra_local_paths:
            for path in extra_local_paths:
                normalized = self._normalize_local_path(path)
                if normalized:
                    local_paths.add(normalized)

        # Initialize seen set to prevent infinite recursion
        seen = set()

        state = await state_manager.get_state(file_id)
        if not state and task_id:
            state = await state_manager.get_state_by_task(task_id)

        # Also collect artifacts from all tasks associated with this upload_id
        try:
            from slidespeaker.repository.task import get_tasks_by_upload_id

            associated_tasks = await get_tasks_by_upload_id(file_id)
            for task in associated_tasks:
                task_id_from_task = task.get("id") or task.get("task_id")
                if task_id_from_task and task_id_from_task != task_id:
                    task_state = await state_manager.get_state_by_task(
                        task_id_from_task
                    )
                    if task_state:
                        self._collect_from_obj(
                            task_state, storage_keys, local_paths, seen=seen
                        )
        except Exception as e:
            # If there's an error in getting associated tasks, continue with existing behavior
            logger.debug(f"Could not get associated tasks for file_id {file_id}: {e}")

        # Walk state/artifacts to capture storage keys and local paths
        if state:
            state_file_ext = state.get("file_ext")
            if isinstance(state_file_ext, str) and state_file_ext and not file_ext:
                file_ext = state_file_ext
            self._collect_from_obj(state, storage_keys, local_paths, seen=seen)

            # Include output directories for this file/task
            state_task_id = state.get("task_id")
            if isinstance(state_task_id, str) and state_task_id:
                local_paths.add(
                    str((self.output_dir / OUTPUTS_PREFIX / state_task_id).resolve())
                )

        if task_id:
            local_paths.add(str((self.output_dir / OUTPUTS_PREFIX / task_id).resolve()))

        # Always include file-level outputs directory
        local_paths.add(str((self.output_dir / OUTPUTS_PREFIX / file_id).resolve()))

        # Include uploaded source file key + path
        if file_ext:
            upload_key = upload_object_key(file_id, file_ext)
            storage_keys.add(upload_key)
            local_paths.add(str((self.output_dir / upload_key).resolve()))
        else:
            # Try to locate upload file locally when extension unknown
            upload_dir = self.output_dir / UPLOADS_PREFIX
            if upload_dir.exists():
                for candidate in upload_dir.glob(f"{file_id}.*"):
                    storage_keys.add(
                        str(candidate.relative_to(self.output_dir)).replace("\\", "/")
                    )
                    local_paths.add(str(candidate.resolve()))

        return storage_keys, local_paths

    async def purge_task_files(
        self,
        file_id: str,
        *,
        storage_keys: Iterable[str] | None = None,
        local_paths: Iterable[str] | None = None,
        target_task_id: str | None = None,
        file_ext: str | None = None,
    ) -> None:
        """
        Purge all generated files associated with a task/file.
        This method is called by the background worker when processing file_purge tasks.
        """
        try:
            collected_keys, collected_paths = await self.collect_artifacts(
                file_id,
                task_id=target_task_id,
                file_ext=file_ext,
                extra_storage_keys=storage_keys,
                extra_local_paths=local_paths,
            )

            if not collected_keys and not collected_paths:
                logger.info(
                    "No artifacts discovered for file_id=%s (task_id=%s)",
                    file_id,
                    target_task_id,
                )

            if config.storage_provider == "local":
                deleted_files = 0
                deleted_dirs = 0
                # Remove files first, then directories (longest path first)
                for path_str in sorted(collected_paths, key=len, reverse=True):
                    try:
                        path = Path(path_str)
                    except Exception:
                        continue
                    try:
                        if path.is_dir():
                            if path.exists():
                                shutil.rmtree(path, ignore_errors=True)
                                deleted_dirs += 1
                        else:
                            if path.exists():
                                path.unlink()
                                deleted_files += 1
                    except Exception as exc:
                        logger.debug(
                            "Failed to delete local artifact %s: %s", path_str, exc
                        )
                logger.info(
                    "Purged %s files and %s directories from local storage for file_id=%s",
                    deleted_files,
                    deleted_dirs,
                    file_id,
                )
            else:
                deleted_count = 0
                for key in sorted(collected_keys):
                    try:
                        self.storage_provider.delete_file(key)
                        deleted_count += 1
                    except Exception:
                        # Ignore missing objects or provider-specific errors
                        pass
                logger.info(
                    "Purged %s storage objects for file_id=%s (task_id=%s)",
                    deleted_count,
                    file_id,
                    target_task_id,
                )

        except Exception as e:
            logger.error(f"Error purging files for file_id {file_id}: {e}")

    def _collect_from_obj(
        self,
        obj: Any,
        storage_keys: set[str],
        local_paths: set[str],
        *,
        seen: set[int],
    ) -> None:
        """Recursively collect storage keys and local paths from an object graph."""
        obj_id = id(obj)
        if obj_id in seen:
            return
        seen.add(obj_id)

        if isinstance(obj, dict):
            for key, value in obj.items():
                lower = key.lower()
                if (
                    lower in {"storage_key", "object_key", "storage_path"}
                    or lower in {"storage_keys", "object_keys"}
                    or "storage_uri" in lower
                    or lower.endswith("_uri")
                ):
                    self._maybe_add_storage_key(value, storage_keys, local_paths, seen)
                elif lower.endswith("path") or "file_path" in lower:
                    self._maybe_add_local_path(value, storage_keys, local_paths, seen)
                else:
                    self._collect_from_obj(value, storage_keys, local_paths, seen=seen)
        elif isinstance(obj, (list, tuple, set)):
            for item in obj:
                self._collect_from_obj(item, storage_keys, local_paths, seen=seen)

    def _maybe_add_storage_key(
        self,
        value: Any,
        storage_keys: set[str],
        local_paths: set[str],
        seen: set[int],
    ) -> None:
        if isinstance(value, (list, tuple, set)):
            for item in value:
                self._maybe_add_storage_key(item, storage_keys, local_paths, seen)
            return
        if isinstance(value, dict):
            self._collect_from_obj(value, storage_keys, local_paths, seen=seen)
            return

        key = self._normalize_storage_key(value)
        if key:
            storage_keys.add(key)
            local_paths.add(str((self.output_dir / key).resolve()))

    def _maybe_add_local_path(
        self,
        value: Any,
        storage_keys: set[str],
        local_paths: set[str],
        seen: set[int],
    ) -> None:
        if isinstance(value, (list, tuple, set)):
            for item in value:
                self._maybe_add_local_path(item, storage_keys, local_paths, seen)
            return
        if isinstance(value, dict):
            self._collect_from_obj(value, storage_keys, local_paths, seen=seen)
            return

        normalized = self._normalize_local_path(value)
        if normalized:
            local_paths.add(normalized)
            # Attempt to infer storage key from local path
            try:
                rel = Path(normalized).relative_to(self.output_dir)
                storage_keys.add(str(rel).replace("\\", "/"))
            except Exception:
                pass

    def _normalize_storage_key(self, candidate: Any) -> str | None:
        if not isinstance(candidate, str):
            return None
        candidate = candidate.strip()
        if not candidate:
            return None

        for marker in ("uploads/", "outputs/"):
            if marker in candidate:
                idx = candidate.index(marker)
                segment = candidate[idx:].replace("\\", "/")
                return segment.lstrip("/")

        # Convert URIs to object keys
        key = object_key_from_uri(candidate)
        if key:
            return key.strip("/")

        # Treat relative storage keys directly
        if candidate.startswith(("uploads/", "outputs/")):
            return candidate.lstrip("/").replace("\\", "/")

        # Ignore obvious HTTP URLs or unsupported schemes
        if "://" in candidate:
            return None

        # Attempt to convert local path to relative key
        try:
            path = Path(candidate)
            if path.is_absolute():
                rel = path.relative_to(self.output_dir)
                return str(rel).replace("\\", "/")
            return candidate.replace("\\", "/")
        except Exception:
            return None

    def _normalize_local_path(self, candidate: Any) -> str | None:
        if not isinstance(candidate, str):
            return None
        candidate = candidate.strip()
        if not candidate:
            return None
        try:
            path = Path(candidate)
            if not path.is_absolute():
                path = (self.output_dir / candidate).resolve()
            return str(path)
        except Exception:
            return None


# Global file purger instance
file_purger = FilePurger()
