"""
Health and readiness endpoints.

Reports Redis connectivity so the UI can show a queue availability banner
instead of failing requests when Redis is down.
"""

from __future__ import annotations

import time
from contextlib import suppress
from typing import Any

from fastapi import APIRouter

from slidespeaker.configs.redis_config import RedisConfig

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health() -> dict[str, Any]:
    """Return basic health info, including Redis connectivity status."""
    redis_ok = False
    latency_ms: float | None = None
    error: str | None = None

    try:
        redis = RedisConfig.get_redis_client()
        t0 = time.perf_counter()
        pong = await redis.ping()
        t1 = time.perf_counter()
        redis_ok = bool(pong)
        latency_ms = (t1 - t0) * 1000.0
    except Exception as e:  # noqa: BLE001 - intentionally broad for health check
        error = str(e)

    status = "ok" if redis_ok else "degraded"
    info: dict[str, Any] = {
        "status": status,
        "redis": {"ok": redis_ok},
    }
    if latency_ms is not None:
        info["redis"]["latency_ms"] = round(latency_ms, 2)
    if error:
        info["redis"]["error"] = error

    # Also include non-sensitive connection info for visibility
    with suppress(Exception):
        info["redis"]["connection"] = RedisConfig.get_connection_info()

    return info
