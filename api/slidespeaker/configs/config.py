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
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        # Vision providers/models
        self.vision_provider = os.getenv("VISION_PROVIDER", "openai").lower()
        self.openai_vision_model = os.getenv(
            "OPENAI_VISION_MODEL", os.getenv("VISION_MODEL", "gpt-4o-mini")
        )
        self.vision_model = self.openai_vision_model

        # Reviewer
        self.review_provider = os.getenv("REVIEW_PROVIDER", "openai").lower()
        self.openai_reviewer_model = os.getenv(
            "OPENAI_REVIEW_MODEL", os.getenv("SCRIPT_REVIEWER_MODEL", "gpt-4o-mini")
        )
        self.script_reviewer_model = self.openai_reviewer_model

        # Script generation
        self.script_provider = os.getenv("SCRIPT_PROVIDER", "openai").lower()
        self.openai_script_model = os.getenv(
            "OPENAI_SCRIPT_MODEL", os.getenv("SCRIPT_GENERATOR_MODEL", "gpt-4o-mini")
        )
        self.script_generator_model = self.openai_script_model

        # PDF analyzer
        self.pdf_analyzer_provider = os.getenv(
            "PDF_ANALYZER_PROVIDER", "openai"
        ).lower()
        self.openai_pdf_analyzer_model = os.getenv(
            "OPENAI_PDF_ANALYZER_MODEL", "gpt-4o-mini"
        )
        self.pdf_analyzer_model = self.openai_pdf_analyzer_model

        # Translation
        self.translation_provider = os.getenv("TRANSLATION_PROVIDER", "openai").lower()
        self.openai_translation_model = os.getenv(
            "OPENAI_TRANSLATION_MODEL", "gpt-4o-mini"
        )
        self.translation_model = self.openai_translation_model

        # Qwen models/keys (kept for features still supported elsewhere)
        self.qwen_api_key = os.getenv("QWEN_API_KEY")
        self.qwen_script_model = os.getenv("QWEN_SCRIPT_MODEL", "qwen-turbo")
        self.qwen_reviewer_model = os.getenv("QWEN_REVIEWER_MODEL", "qwen-turbo")

        # TTS
        self.tts_service = os.getenv("TTS_SERVICE", "openai").lower()
        self.openai_tts_model = os.getenv("OPENAI_TTS_MODEL", "tts-1")
        self.openai_tts_voice = os.getenv("OPENAI_TTS_VOICE", "alloy")
        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        self.elevenlabs_voice_id = os.getenv("ELEVENLABS_VOICE_ID")

        # Images
        self.avatar_service = os.getenv("AVATAR_SERVICE", "heygen").lower()
        self.heygen_api_key = os.getenv("HEYGEN_API_KEY")
        self.image_provider = os.getenv("IMAGE_PROVIDER", "openai").lower()
        self.openai_image_model = os.getenv(
            "OPENAI_IMAGE_MODEL", os.getenv("IMAGE_GENERATION_MODEL", "gpt-image-1")
        )
        self.qwen_image_model = os.getenv("QWEN_IMAGE_MODEL", "wanx-v1")
        self.image_generation_model = self.openai_image_model
        self.slide_image_provider = os.getenv("SLIDE_IMAGE_PROVIDER", "PIL")

        # Storage
        self.storage_provider = os.getenv("STORAGE_PROVIDER", "local")
        self.storage_config = self._get_storage_config()
        self.proxy_cloud_media = (
            os.getenv("PROXY_CLOUD_MEDIA", "false").lower() == "true"
        )

        # Pipeline feature flags
        self.enable_visual_analysis = (
            os.getenv("ENABLE_VISUAL_ANALYSIS", "true").lower() == "true"
        )

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

    def get_storage_provider(self) -> StorageProvider:
        try:
            storage_config = StorageConfig(
                provider=self.storage_provider, **self.storage_config
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
