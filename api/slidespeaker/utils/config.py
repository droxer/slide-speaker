"""
Configuration module for SlideSpeaker.
Handles environment-based configuration including output directory settings.

This module manages application configuration through environment variables and
provides centralized access to configuration values with appropriate defaults.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

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


# Global configuration instance
config = Config()

# Ensure directories exist on import
config.ensure_directories_exist()
