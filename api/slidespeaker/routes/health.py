"""
Health and readiness endpoints.

Reports Redis connectivity so the UI can show a queue availability banner
instead of failing requests when Redis is down.
"""

from __future__ import annotations

import time
from time import perf_counter
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text

from slidespeaker.auth import require_authenticated_user
from slidespeaker.configs.db import get_session
from slidespeaker.configs.redis_config import RedisConfig

router = APIRouter(
    prefix="/api",
    tags=["health"],
    dependencies=[Depends(require_authenticated_user)],
)


@router.get("/health")
async def health() -> dict[str, Any]:
    """Return basic health info for Redis and DB connectivity."""
    # Redis check
    redis_ok = False
    redis_latency_ms: float | None = None
    redis_error: str | None = None
    try:
        redis = RedisConfig.get_redis_client()
        t0 = time.perf_counter()
        pong = await redis.ping()
        t1 = time.perf_counter()
        redis_ok = bool(pong)
        redis_latency_ms = (t1 - t0) * 1000.0
    except Exception as e:  # noqa: BLE001 - intentionally broad for health check
        redis_error = str(e)

    # DB check
    db_ok = False
    db_latency_ms: float | None = None
    db_error: str | None = None
    try:
        t0 = perf_counter()
        async with get_session() as s:
            await s.execute(text("SELECT 1"))
        t1 = perf_counter()
        db_ok = True
        db_latency_ms = (t1 - t0) * 1000.0
    except Exception as e:  # noqa: BLE001 - broad for health
        db_error = str(e)

    # Overall status
    status = (
        "ok"
        if (redis_ok and db_ok)
        else ("degraded" if (redis_ok or db_ok) else "down")
    )

    info: dict[str, Any] = {
        "status": status,
        "redis": {"ok": redis_ok},
        "db": {"ok": db_ok},
    }
    if redis_latency_ms is not None:
        info["redis"]["latency_ms"] = round(redis_latency_ms, 2)
    if redis_error:
        info["redis"]["error"] = redis_error
    if db_latency_ms is not None:
        info["db"]["latency_ms"] = round(db_latency_ms, 2)
    if db_error:
        info["db"]["error"] = db_error

    return info
