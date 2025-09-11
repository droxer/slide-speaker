"""
Configuration module for SlideSpeaker.
Handles environment-based configuration including output directory settings.

This module manages application configuration through environment variables and
provides centralized access to configuration values with appropriate defaults.
"""

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from slidespeaker.storage import StorageConfig, StorageProvider, create_storage_provider

# Load environment variables once at module import
load_dotenv()


class Config:
    """Configuration class for SlideSpeaker application"""

    def __init__(self) -> None:
        """Initialize configuration with default values and environment overrides"""
        # Output directory configuration
        self._output_dir: Path | None = None
        self._uploads_dir: Path | None = None

        # Watermark configuration
        self.watermark_enabled = (
            os.getenv("WATERMARK_ENABLED", "true").lower() == "true"
        )
        self.watermark_text = os.getenv("WATERMARK_TEXT", "SlideSpeaker AI")
        self.watermark_opacity = float(os.getenv("WATERMARK_OPACITY", "0.95"))
        self.watermark_size = int(os.getenv("WATERMARK_SIZE", "64"))

        # FFmpeg configuration
        self.ffmpeg_fps = int(os.getenv("FFMPEG_FPS", "24"))
        self.ffmpeg_threads = int(os.getenv("FFMPEG_THREADS", "2"))
        self.ffmpeg_preset = os.getenv("FFMPEG_PRESET", "medium")
        self.ffmpeg_bitrate = os.getenv("FFMPEG_BITRATE", "2000k")
        self.ffmpeg_audio_bitrate = os.getenv("FFMPEG_AUDIO_BITRATE", "128k")

        # Storage configuration
        self.storage_provider = os.getenv("STORAGE_PROVIDER", "local")
        self.storage_config = self._get_storage_config()

    @property
    def output_dir(self) -> Path:
        """Get the output directory path, configurable via "
        "OUTPUT_DIR environment variable"""
        if self._output_dir is None:
            output_dir_env = os.getenv("OUTPUT_DIR")
            if output_dir_env:
                self._output_dir = Path(output_dir_env).resolve()
            else:
                # Default to 'output' directory in the api folder (same as before)
                self._output_dir = Path(__file__).parent.parent.parent / "output"
        return self._output_dir

    @property
    def uploads_dir(self) -> Path:
        """Get the uploads directory path, configurable via "
        "UPLOADS_DIR environment variable"""
        if self._uploads_dir is None:
            uploads_dir_env = os.getenv("UPLOADS_DIR")
            if uploads_dir_env:
                self._uploads_dir = Path(uploads_dir_env).resolve()
            else:
                # Default to 'uploads' directory in the api folder (same as before)
                self._uploads_dir = Path(__file__).parent.parent.parent / "uploads"
        return self._uploads_dir

    def ensure_directories_exist(self) -> None:
        """Ensure that the required directories exist"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)

    def _get_storage_config(self) -> dict[str, Any]:
        """Get storage configuration based on provider type."""
        if self.storage_provider == "local":
            return {"base_path": str(self.output_dir), "base_url": "/"}
        elif self.storage_provider == "s3":
            return {
                "bucket_name": os.getenv("AWS_S3_BUCKET_NAME", ""),
                "region_name": os.getenv("AWS_REGION", "us-east-1"),
                "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID", ""),
                "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY", ""),
                "endpoint_url": os.getenv("AWS_S3_ENDPOINT_URL"),  # For testing/minio
            }
        elif self.storage_provider == "oss":
            return {
                "bucket_name": os.getenv("OSS_BUCKET_NAME", ""),
                "endpoint": os.getenv("OSS_ENDPOINT", ""),
                "access_key_id": os.getenv("OSS_ACCESS_KEY_ID", ""),
                "access_key_secret": os.getenv("OSS_ACCESS_KEY_SECRET", ""),
                "region": os.getenv("OSS_REGION", ""),
            }
        else:
            raise ValueError(f"Unsupported storage provider: {self.storage_provider}")

    def get_storage_provider(self) -> StorageProvider:
        """Get a storage provider instance based on configuration."""
        try:
            storage_config = StorageConfig(
                provider=self.storage_provider, **self.storage_config
            )
            return create_storage_provider(storage_config)
        except ImportError:
            # Surface configuration errors explicitly for non-local providers
            if self.storage_provider != "local":
                raise
            # Local provider should still work
            local_config = StorageConfig(
                provider="local", base_path=str(self.output_dir), base_url="/"
            )
            return create_storage_provider(local_config)


# Global configuration instance
config = Config()

# Global storage provider instance (lazy initialization)
_storage_provider_instance = None


def get_storage_provider() -> StorageProvider:
    """Get the global storage provider instance with lazy initialization."""
    global _storage_provider_instance
    if _storage_provider_instance is None:
        _storage_provider_instance = config.get_storage_provider()
    return _storage_provider_instance


# Ensure directories exist on import
config.ensure_directories_exist()
