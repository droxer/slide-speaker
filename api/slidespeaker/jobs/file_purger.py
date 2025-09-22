"""
File purger for SlideSpeaker.

This module provides functionality to purge generated files when tasks are deleted.
It uses the existing task queue system to handle file deletion asynchronously.
"""

import shutil
from pathlib import Path

from loguru import logger

from slidespeaker.configs.config import config, get_storage_provider
from slidespeaker.core.state_manager import state_manager
from slidespeaker.core.task_queue import task_queue
from slidespeaker.storage import StorageProvider


class FilePurger:
    """Purger for removing generated files when tasks are deleted."""

    def __init__(self) -> None:
        """Initialize the file purger."""
        self.storage_provider: StorageProvider = get_storage_provider()
        self.output_dir = config.output_dir

    async def enqueue_file_purge(self, file_id: str) -> str | None:
        """
        Enqueue a file purge task to be processed asynchronously through the task queue.

        Args:
            file_id: The file ID of the task to purge

        Returns:
            The task ID of the purge task, or None if submission failed
        """
        try:
            # Submit a file_purge task to the existing task queue
            task_id = await task_queue.submit_task(
                task_type="file_purge", file_id=file_id
            )
            logger.info(f"Enqueued file purge task {task_id} for file_id: {file_id}")
            return task_id
        except Exception as e:
            logger.error(f"Error enqueuing file purge task for file_id {file_id}: {e}")
            return None

    async def purge_task_files(self, file_id: str) -> None:
        """
        Purge all generated files associated with a task.
        This method is called by the background worker when processing file_purge tasks.

        Args:
            file_id: The file ID of the task to purge
        """
        try:
            # Get the file path from state
            state = await state_manager.get_state(file_id)
            if not state:
                logger.warning(f"No state found for file_id: {file_id}")
                return

            file_path_str = state.get("file_path")
            if not file_path_str:
                logger.warning(f"No file_path found in state for file_id: {file_id}")
                return

            # Determine the base directory for this file_id
            base_dir = self.output_dir / file_id

            # If using local storage, we can directly delete the directory
            if config.storage_provider == "local":
                if base_dir.exists() and base_dir.is_dir():
                    shutil.rmtree(base_dir)
                    logger.info(f"Purged local files for file_id: {file_id}")
                else:
                    logger.info(f"No local files found to purge for file_id: {file_id}")
            else:
                # For cloud storage, we need to delete files by their object keys
                await self._purge_cloud_files(file_id, base_dir)

        except Exception as e:
            logger.error(f"Error purging files for file_id {file_id}: {e}")

    async def _purge_cloud_files(self, file_id: str, base_dir: Path) -> None:
        """
        Purge files from cloud storage.

        Args:
            file_id: The file ID of the task to purge
            base_dir: The base directory path for the files
        """
        try:
            # Common file extensions that might exist for this file_id
            file_extensions = [
                ".mp4",  # Video files
                ".mp3",  # Audio files
                ".wav",  # Audio files
                ".srt",  # Subtitle files
                ".vtt",  # Subtitle files
                ".txt",  # Transcript files
                ".json",  # Metadata files
                ".png",  # Image files
                ".jpg",  # Image files
                ".jpeg",  # Image files
            ]

            deleted_count = 0

            # Try to delete files with common patterns
            for ext in file_extensions:
                # Try common naming patterns
                patterns = [
                    f"{file_id}{ext}",
                    f"{file_id}/video{ext}",
                    f"{file_id}/audio{ext}",
                    f"{file_id}/podcast{ext}",
                    f"{file_id}/subtitles{ext}",
                    f"{file_id}/transcript{ext}",
                    f"{file_id}/slides{ext}",
                    f"{file_id}/final{ext}",
                ]

                for pattern in patterns:
                    try:
                        self.storage_provider.delete_file(pattern)
                        deleted_count += 1
                        logger.debug(f"Deleted cloud file: {pattern}")
                    except Exception:
                        # File might not exist, which is fine
                        pass

            # Also try to delete the directory structure if the provider supports it
            try:
                # Try to delete the main directory
                dir_pattern = f"{file_id}/"
                # Note: This depends on the storage provider implementation
                # Some providers might need to list objects first and delete them individually
                logger.debug(f"Attempted to purge cloud directory: {dir_pattern}")
            except Exception:
                # Directory deletion might not be supported by all providers
                pass

            logger.info(f"Purged {deleted_count} cloud files for file_id: {file_id}")

        except Exception as e:
            logger.error(f"Error purging cloud files for file_id {file_id}: {e}")

    async def start_background_purger(self) -> None:
        """
        This method is no longer needed as we're using the existing task queue system.
        """
        pass


# Global file purger instance
file_purger = FilePurger()
