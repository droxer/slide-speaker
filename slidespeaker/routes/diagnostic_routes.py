"""
Diagnostic routes for configuration introspection.

Exposes resolved providers/models with secrets redacted to help validate
runtime configuration. Intended for development/ops diagnostics.
"""

import time

from fastapi import APIRouter, Depends

from slidespeaker.auth import require_authenticated_user
from slidespeaker.configs.config import config

router = APIRouter(
    prefix="/api/diagnostic",
    tags=["diagnostic"],
    dependencies=[Depends(require_authenticated_user)],
)


_CONFIG_CACHE: dict[str, object] | None = None
_CONFIG_CACHE_TS: float = 0.0
_CONFIG_TTL = 10.0  # seconds


@router.get("/config")
async def get_config_diagnostic() -> dict[str, object]:
    global _CONFIG_CACHE, _CONFIG_CACHE_TS
    now = time.time()
    if _CONFIG_CACHE and (now - _CONFIG_CACHE_TS) < _CONFIG_TTL:
        return _CONFIG_CACHE

    def _oss_is_cname() -> bool:
        try:
            sc = getattr(config, "storage_config", {})
            if isinstance(sc, dict):
                return bool(sc.get("is_cname", False))
        except Exception:
            pass
        return False

    payload = {
        "providers": {
            "script": config.script_provider,
            "translation": config.translation_provider,
            "review": config.review_provider,
            "vision": config.vision_provider,
            "image": getattr(config, "image_provider", "openai"),
            "pdf_analyzer": getattr(config, "pdf_analyzer_provider", "openai"),
            "tts": config.tts_service,
            "storage": config.storage_provider,
        },
        "models": {
            "script": {
                "provider": config.script_provider,
                "model": config.script_model,
                "raw": getattr(config, "script_model_name", None),
            },
            "translation": {
                "provider": config.translation_provider,
                "model": config.translation_model,
                "raw": getattr(config, "translation_model_name", None),
            },
            "review": {
                "provider": config.review_provider,
                "model": config.review_model,
                "raw": getattr(config, "review_model_name", None),
            },
            "vision": {
                "provider": config.vision_provider,
                "model": config.vision_model,
                "raw": getattr(config, "vision_model_name", None),
            },
            "image": {
                "provider": getattr(config, "image_provider", "openai"),
                "model": getattr(config, "image_generation_model", None),
                "raw": getattr(config, "image_model_name", None),
            },
            "pdf_analyzer": {
                "provider": getattr(config, "pdf_analyzer_provider", "openai"),
                "model": getattr(config, "pdf_analyzer_model", None),
                "raw": getattr(config, "pdf_analyzer_model_name", None),
            },
            "tts": {
                "provider": config.tts_service,
                "model": getattr(config, "tts_model", None),
                "raw": getattr(config, "tts_model_name", None),
                "voice": getattr(config, "tts_voice", None),
                "openai": {
                    "model": getattr(config, "openai_tts_model", None),
                    "voice": getattr(config, "openai_tts_voice", None),
                },
                "elevenlabs": {
                    "voice_id": getattr(config, "elevenlabs_voice_id", None) or "unset",
                },
            },
        },
        "flags": {
            "proxy_cloud_media": getattr(config, "proxy_cloud_media", False),
            "oss_is_cname": _oss_is_cname(),
            "enable_visual_analysis": getattr(config, "enable_visual_analysis", True),
        },
        "keys_present": {
            "openai": bool(getattr(config, "openai_api_key", None)),
            "elevenlabs": bool(getattr(config, "elevenlabs_api_key", None)),
            "heygen": bool(getattr(config, "heygen_api_key", None)),
        },
    }
    _CONFIG_CACHE = payload
    _CONFIG_CACHE_TS = now
    return payload
