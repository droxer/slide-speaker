"""
Local filesystem storage implementation.

Provides local storage for backward compatibility and development.
"""

import logging
import shutil
from pathlib import Path

from . import StorageProvider

logger = logging.getLogger(__name__)


class LocalStorage(StorageProvider):
    """Local filesystem storage implementation."""

    def __init__(self, base_path: str | Path, base_url: str = "/"):
        """Initialize local storage.

        Args:
            base_path: Base directory for file storage
            base_url: Base URL for file access (for get_file_url)
        """
        self.base_path = Path(base_path)
        self.base_url = base_url
        self.base_path.mkdir(parents=True, exist_ok=True)

    def upload_file(
        self, file_path: str | Path, object_key: str, content_type: str | None = None
    ) -> str:
        """Copy a file to the local storage directory."""
        source_path = Path(file_path)
        dest_path = self.base_path / object_key

        # Check if source and destination are the same file
        if source_path.resolve() == dest_path.resolve():
            # File is already in the correct location, just return its path
            logger.debug(
                f"File {source_path} is already in correct location, skipping copy"
            )
            return str(dest_path)

        # Ensure destination directory exists
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy the file
        try:
            shutil.copy2(source_path, dest_path)
        except shutil.SameFileError:
            # Handle edge case where files are the same but resolve() didn't catch it
            logger.debug(
                f"File {source_path} is already in correct location (SameFileError)"
            )
            return str(dest_path)

        return str(dest_path)

    def download_file(self, object_key: str, destination_path: str | Path) -> None:
        """Copy a file from local storage to destination."""
        source_path = self.base_path / object_key
        dest_path = Path(destination_path)

        # Ensure destination directory exists
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(source_path, dest_path)

    def get_file_url(self, object_key: str, expires_in: int = 3600) -> str:
        """Get local file path for local storage."""
        # For local storage, return the actual filesystem path
        # This provides direct access to the file for internal use
        return str(self.base_path / object_key)

    def file_exists(self, object_key: str) -> bool:
        """Check if file exists in local storage."""
        return (self.base_path / object_key).exists()

    def delete_file(self, object_key: str) -> None:
        """Delete file from local storage."""
        file_path = self.base_path / object_key
        if file_path.exists():
            file_path.unlink()

    def upload_bytes(
        self, data: bytes, object_key: str, content_type: str | None = None
    ) -> str:
        """Upload bytes to local storage."""
        dest_path = self.base_path / object_key
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        with open(dest_path, "wb") as f:
            f.write(data)
        return str(dest_path)

    def download_bytes(self, object_key: str) -> bytes:
        """Download bytes from local storage."""
        file_path = self.base_path / object_key
        with open(file_path, "rb") as f:
            return f.read()
