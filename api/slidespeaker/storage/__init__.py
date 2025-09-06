"""
Storage module for SlideSpeaker.

Provides abstract storage interface and implementations for different cloud providers.
Designed to be extensible for multiple storage backends (AWS S3, Google Cloud Storage, etc.).
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, BinaryIO, Optional, Union


class StorageProvider(ABC):
    """Abstract base class for storage providers."""

    @abstractmethod
    def upload_file(
        self, file_path: str | Path, object_key: str, content_type: str | None = None
    ) -> str:
        """Upload a file to storage.

        Args:
            file_path: Path to the local file to upload
            object_key: Key/name for the object in storage
            content_type: MIME type of the file content

        Returns:
            URL or identifier for the uploaded file
        """
        pass

    @abstractmethod
    def download_file(self, object_key: str, destination_path: str | Path) -> None:
        """Download a file from storage.

        Args:
            object_key: Key/name of the object in storage
            destination_path: Local path to save the downloaded file
        """
        pass

    @abstractmethod
    def get_file_url(self, object_key: str, expires_in: int = 3600) -> str:
        """Get a presigned URL for accessing a file.

        Args:
            object_key: Key/name of the object in storage
            expires_in: URL expiration time in seconds

        Returns:
            Presigned URL for accessing the file
        """
        pass

    @abstractmethod
    def file_exists(self, object_key: str) -> bool:
        """Check if a file exists in storage.

        Args:
            object_key: Key/name of the object in storage

        Returns:
            True if file exists, False otherwise
        """
        pass

    @abstractmethod
    def delete_file(self, object_key: str) -> None:
        """Delete a file from storage.

        Args:
            object_key: Key/name of the object in storage
        """
        pass

    @abstractmethod
    def upload_bytes(
        self, data: bytes, object_key: str, content_type: str | None = None
    ) -> str:
        """Upload bytes data to storage.

        Args:
            data: Bytes data to upload
            object_key: Key/name for the object in storage
            content_type: MIME type of the content

        Returns:
            URL or identifier for the uploaded data
        """
        pass

    @abstractmethod
    def download_bytes(self, object_key: str) -> bytes:
        """Download bytes data from storage.

        Args:
            object_key: Key/name of the object in storage

        Returns:
            Bytes data from the file
        """
        pass


class StorageConfig:
    """Configuration for storage providers."""

    def __init__(self, provider: str = "local", **kwargs: Any) -> None:
        """Initialize storage configuration.

        Args:
            provider: Storage provider type ('local', 's3', 'gcs')
            **kwargs: Provider-specific configuration
        """
        self.provider = provider
        self.config = kwargs


# Factory function to create storage providers
def create_storage_provider(config: StorageConfig) -> StorageProvider:
    """Create a storage provider based on configuration.

    Args:
        config: Storage configuration

    Returns:
        StorageProvider instance

    Raises:
        ValueError: If provider type is not supported
    """
    if config.provider == "local":
        from .local_storage import LocalStorage

        return LocalStorage(**config.config)
    elif config.provider == "s3":
        from .s3_storage import S3Storage

        return S3Storage(**config.config)
    elif config.provider == "oss":
        from .oss_storage import OSSStorage

        return OSSStorage(**config.config)
    else:
        raise ValueError(f"Unsupported storage provider: {config.provider}")
