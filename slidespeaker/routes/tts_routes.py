"""
TTS and LLM routes for listing provider catalogs.
"""

import httpx
from fastapi import APIRouter, Depends, HTTPException

from slidespeaker.audio.tts_factory import TTSFactory
from slidespeaker.auth import require_authenticated_user
from slidespeaker.configs.config import config

router = APIRouter(
    prefix="/api",
    tags=["tts"],
    dependencies=[Depends(require_authenticated_user)],
)


@router.get("/tts/voices")
async def list_tts_voices(
    language: str = "english", provider: str | None = None
) -> dict[str, object]:
    """List supported TTS voices for the given language.

    Args:
        language: Normalized language key (e.g., 'english', 'simplified_chinese')
        provider: Optional provider override (openai|elevenlabs). Defaults to config.
    """
    try:
        service = TTSFactory.create_service(config.tts_model)
        voices = service.get_supported_voices(language)
        # Extract model name instead of returning the service instance
        model_name = (
            config.tts_model.split("/")[0]
            if "/" in config.tts_model
            else config.tts_model
        )
        return {"model": model_name, "voices": voices}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"TTS voices unavailable: {e}"
        ) from e


@router.get("/tts/catalog")
async def tts_catalog(provider: str | None = None) -> dict[str, object]:
    """Return a richer voice catalog for a provider (IDs, names, languages).

    Provider-specific behavior:
    - elevenlabs: calls list-voices API when possible.
    - openai: returns static set with common voices and language hints.
    """
    p = (provider or config.tts_service).lower()
    catalog: dict[str, object] = {"provider": p, "voices": []}
    try:
        if p == "elevenlabs":
            api_key = config.elevenlabs_api_key
            if not api_key:
                raise RuntimeError("ELEVENLABS_API_KEY not configured")
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    "https://api.elevenlabs.io/v1/voices",
                    headers={"xi-api-key": api_key},
                )
                resp.raise_for_status()
                data = resp.json()
            voices = []
            for v in data.get("voices") or []:
                voices.append(
                    {
                        "id": v.get("voice_id"),
                        "name": v.get("name"),
                        "labels": v.get("labels", {}),
                        "category": v.get("category"),
                    }
                )
            catalog["voices"] = voices
            return catalog
        elif p == "openai":
            # Static catalog; OpenAI doesn't provide a voice list endpoint
            base = [
                {"id": "alloy", "name": "Alloy"},
                {"id": "echo", "name": "Echo"},
                {"id": "fable", "name": "Fable"},
                {"id": "onyx", "name": "Onyx"},
                {"id": "nova", "name": "Nova"},
                {"id": "shimmer", "name": "Shimmer"},
            ]
            catalog["voices"] = base
            catalog["notes"] = "Static OpenAI voice set; no official list-voices API"
            return catalog
        else:
            raise RuntimeError(f"Unknown provider: {p}")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Catalog error: {e}") from e


@router.get("/llm/models")
async def llm_models() -> dict[str, object]:
    """Expose configured providers/models and supported language keys.

    Qwen support is removed for transcript generation/review and TTS; this
    endpoint reflects OpenAI for script models.
    """
    from slidespeaker.translation.openai_translator import LANGUAGE_CODES

    return {
        "script": {
            "provider": config.script_provider,
            "model": config.script_model,
        },
        "translation": {
            "provider": config.translation_provider,
            "model": config.translation_model,
        },
        "languages": sorted(LANGUAGE_CODES.keys()),
    }
