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

        # Ensure destination directory exists
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if source and destination are the same file
        try:
            if source_path.resolve() == dest_path.resolve():
                # File is already in the correct location, just return its path
                logger.debug(
                    f"File {source_path} is already in correct location, skipping copy"
                )
                return str(dest_path)
        except (OSError, ValueError) as e:
            # Handle cases where resolve() might fail (e.g., broken symlinks)
            logger.debug(f"Could not resolve paths for comparison: {e}")

        # Copy the file
        try:
            shutil.copy2(source_path, dest_path)
        except shutil.SameFileError:
            # Handle edge case where files are the same but resolve() didn't catch it
            logger.debug(
                f"File {source_path} is already in correct location (SameFileError)"
            )
            return str(dest_path)
        except FileNotFoundError:
            logger.error(f"Source file not found: {source_path}")
            raise
        except PermissionError:
            logger.error(f"Permission denied when copying file: {source_path}")
            raise

        return str(dest_path)

    def download_file(self, object_key: str, destination_path: str | Path) -> None:
        """Copy a file from local storage to destination."""
        source_path = self.base_path / object_key
        dest_path = Path(destination_path)

        # Ensure destination directory exists
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if source file exists
        if not source_path.exists():
            logger.error(f"Source file not found in storage: {source_path}")
            raise FileNotFoundError(f"File not found in storage: {object_key}")

        try:
            shutil.copy2(source_path, dest_path)
        except PermissionError:
            logger.error(f"Permission denied when copying file: {source_path}")
            raise
        except Exception as e:
            logger.error(f"Error downloading file {object_key}: {e}")
            raise

    def get_file_url(self, object_key: str, expires_in: int = 3600) -> str:
        """Get local file URL for local storage."""
        # For local storage, return a file URL that can be accessed via HTTP
        # when served by the web server
        return f"/files/{object_key}"

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

        try:
            with open(dest_path, "wb") as f:
                f.write(data)
            logger.debug(f"Uploaded {len(data)} bytes to {dest_path}")
        except PermissionError:
            logger.error(f"Permission denied when writing file: {dest_path}")
            raise
        except Exception as e:
            logger.error(f"Error uploading bytes to {dest_path}: {e}")
            raise

        return str(dest_path)

    def download_bytes(self, object_key: str) -> bytes:
        """Download bytes from local storage."""
        file_path = self.base_path / object_key

        # Check if file exists
        if not file_path.exists():
            logger.error(f"File not found in storage: {file_path}")
            raise FileNotFoundError(f"File not found in storage: {object_key}")

        try:
            with open(file_path, "rb") as f:
                data = f.read()
            logger.debug(f"Downloaded {len(data)} bytes from {file_path}")
            return data
        except PermissionError:
            logger.error(f"Permission denied when reading file: {file_path}")
            raise
        except Exception as e:
            logger.error(f"Error downloading bytes from {file_path}: {e}")
            raise
