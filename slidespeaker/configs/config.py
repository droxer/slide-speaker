"""
Configuration module for SlideSpeaker (configs).
"""

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from slidespeaker.storage import StorageConfig, StorageProvider, create_storage_provider

load_dotenv()


class Config:
    def __init__(self) -> None:
        self._output_dir: Path | None = None
        self._uploads_dir: Path | None = None

        # Watermark
        self.watermark_enabled = (
            os.getenv("WATERMARK_ENABLED", "true").lower() == "true"
        )
        self.watermark_text = os.getenv("WATERMARK_TEXT", "SlideSpeaker AI")
        self.watermark_opacity = float(os.getenv("WATERMARK_OPACITY", "0.95"))
        self.watermark_size = int(os.getenv("WATERMARK_SIZE", "64"))

        # FFmpeg
        self.ffmpeg_fps = int(os.getenv("FFMPEG_FPS", "24"))
        self.ffmpeg_threads = int(os.getenv("FFMPEG_THREADS", "2"))
        self.ffmpeg_preset = os.getenv("FFMPEG_PRESET", "medium")
        self.ffmpeg_bitrate = os.getenv("FFMPEG_BITRATE", "2000k")
        self.ffmpeg_audio_bitrate = os.getenv("FFMPEG_AUDIO_BITRATE", "128k")
        self.ffmpeg_codec = os.getenv("FFMPEG_CODEC", "libx264")
        self.ffmpeg_audio_codec = os.getenv("FFMPEG_AUDIO_CODEC", "aac")
        # Performance optimization flags
        self.ffmpeg_fast_mode = os.getenv("FFMPEG_FAST_MODE", "false").lower() == "true"

        # Logging / runtime
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        self.log_file = os.getenv("LOG_FILE")
        self.log_dir = os.getenv("LOG_DIR", "logs")
        self.port = int(os.getenv("PORT", "8000"))
        self.max_workers = int(os.getenv("MAX_WORKERS", "2"))

        # Redis
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = int(os.getenv("REDIS_PORT", 6379))
        self.redis_db = int(os.getenv("REDIS_DB", 0))
        self.redis_password = os.getenv("REDIS_PASSWORD") or None

        # API keys and providers
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        # Optional base URL for OpenAI-compatible services
        self.openai_base_url = os.getenv("OPENAI_BASE_URL") or os.getenv(
            "OPENAI_API_BASE"
        )
        # OpenAI request tuning
        self.openai_timeout = float(os.getenv("OPENAI_TIMEOUT", "60"))
        self.openai_retries = int(os.getenv("OPENAI_RETRIES", "3"))
        self.openai_backoff = float(os.getenv("OPENAI_BACKOFF", "0.5"))
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        # Google Gemini configuration
        self.google_gemini_api_key = os.getenv("GOOGLE_GEMINI_API_KEY")
        self.google_gemini_model = (
            os.getenv("GOOGLE_GEMINI_MODEL") or "gemini-1.5-flash"
        )

        self.google_gemini_timeout = float(os.getenv("GOOGLE_GEMINI_TIMEOUT", "60"))
        self.google_gemini_retries = int(os.getenv("GOOGLE_GEMINI_RETRIES", "3"))
        self.google_gemini_backoff = float(os.getenv("GOOGLE_GEMINI_BACKOFF", "0.5"))
        self.google_gemini_endpoint = (
            os.getenv("GOOGLE_GEMINI_ENDPOINT")
            or "https://generativelanguage.googleapis.com/v1beta"
        )
        self.google_gemini_vision_model = os.getenv(
            "GOOGLE_GEMINI_VISION_MODEL", self.google_gemini_model
        )
        self.google_image_model = os.getenv(
            "GOOGLE_IMAGE_MODEL", "imagen-4.0-generate-001"
        )
        self.google_tts_voice = os.getenv("GOOGLE_TTS_VOICE", "polyglot-1")

        # Vision providers/models (clamped to OpenAI by default)
        self.openai_vision_model = os.getenv(
            "OPENAI_VISION_MODEL", os.getenv("VISION_MODEL", "gpt-4o-mini")
        )
        self.openai_image_model = os.getenv(
            "OPENAI_IMAGE_MODEL", os.getenv("IMAGE_GENERATION_MODEL", "gpt-image-1")
        )
        self.openai_tts_model = os.getenv("OPENAI_TTS_MODEL", "tts-1")
        self.openai_tts_voice = os.getenv("OPENAI_TTS_VOICE", "alloy")

        self.script_generate_model = os.getenv("SCRIPT_GENERATION_MODEL")
        self.script_review_model = os.getenv("SCRIPT_REVIEW_MODEL")
        self.translation_model = os.getenv("TRANSLATION_MODEL")
        self.pdf_analyzer_model = os.getenv("PDF_ANALYZER_MODEL")
        self.vision_analyzer_model = os.getenv("VISION_ANALYZER_MODEL")
        self.image_generation_model = os.getenv("IMAGE_GENERATION_MODEL")
        self.tts_model = os.getenv("TTS_MODEL")
        self.tts_voice = os.getenv("TTS_VOICE")

        # Feature flags
        self.enable_visual_analysis = (
            os.getenv("ENABLE_VISUAL_ANALYSIS", "true").lower() == "true"
        )

        self.slide_image_provider = os.getenv("SLIDE_IMAGE_PROVIDER", "pil")

        self.storage_provider = os.getenv("STORAGE_PROVIDER", "oss")
        self.proxy_cloud_media = (
            os.getenv("PROXY_CLOUD_MEDIA", "false").lower() == "true"
        )
        # CORS settings
        self.cors_origins = self._parse_cors_origins(
            os.getenv("CORS_ORIGINS", "http://localhost:3000")
        )

    def _parse_cors_origins(self, origins_str: str) -> list[str]:
        """Parse CORS origins from a comma-separated string."""
        if not origins_str:
            return ["http://localhost:3000"]
        return [origin.strip() for origin in origins_str.split(",") if origin.strip()]

    @property
    def output_dir(self) -> Path:
        if self._output_dir is None:
            output_dir_env = os.getenv("OUTPUT_DIR")
            if output_dir_env:
                self._output_dir = Path(output_dir_env).resolve()
            else:
                self._output_dir = Path(__file__).parent.parent.parent / "output"
        return self._output_dir

    @property
    def uploads_dir(self) -> Path:
        if self._uploads_dir is None:
            uploads_dir_env = os.getenv("UPLOADS_DIR")
            if uploads_dir_env:
                self._uploads_dir = Path(uploads_dir_env).resolve()
            else:
                self._uploads_dir = Path(__file__).parent.parent.parent / "uploads"
        return self._uploads_dir

    def ensure_directories_exist(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)

    def _get_storage_config(self) -> dict[str, Any]:
        if self.storage_provider == "local":
            return {"base_path": str(self.output_dir), "base_url": "/"}
        elif self.storage_provider == "s3":
            return {
                "bucket_name": os.getenv("AWS_S3_BUCKET_NAME", ""),
                "region_name": os.getenv("AWS_REGION", "us-east-1"),
                "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID", ""),
                "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY", ""),
                "endpoint_url": os.getenv("AWS_S3_ENDPOINT_URL"),
            }
        elif self.storage_provider == "oss":
            return {
                "bucket_name": os.getenv("OSS_BUCKET_NAME", ""),
                "endpoint": os.getenv("OSS_ENDPOINT", ""),
                "access_key_id": os.getenv("OSS_ACCESS_KEY_ID", ""),
                "access_key_secret": os.getenv("OSS_ACCESS_KEY_SECRET", ""),
                "region": os.getenv("OSS_REGION", ""),
                "is_cname": os.getenv("OSS_IS_CNAME", "false").lower() == "true",
            }
        else:
            raise ValueError(f"Unsupported storage provider: {self.storage_provider}")

    @property
    def storage_config(self) -> dict[str, Any]:
        """Return resolved storage configuration for the active provider."""
        return self._get_storage_config()

    def get_storage_provider(self) -> StorageProvider:
        try:
            storage_config = StorageConfig(
                provider=self.storage_provider, **self._get_storage_config()
            )
            return create_storage_provider(storage_config)
        except ImportError:
            if self.storage_provider != "local":
                raise
            local_config = StorageConfig(
                provider="local", base_path=str(self.output_dir), base_url="/"
            )
            return create_storage_provider(local_config)


config = Config()
_storage_provider_instance = None


def get_storage_provider() -> StorageProvider:
    global _storage_provider_instance
    if _storage_provider_instance is None:
        _storage_provider_instance = config.get_storage_provider()
    return _storage_provider_instance


def get_env(key: str, default: Any | None = None) -> Any:
    return os.getenv(key, default)


config.ensure_directories_exist()
