"""
Lightweight async Postgres access (optional).

If DATABASE_URL is set (postgresql+asyncpg://...), provides an async
SQLAlchemy engine/session factory. Otherwise, exports `db_enabled = False`.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

DATABASE_URL = os.getenv("DATABASE_URL")

db_enabled: bool = bool(DATABASE_URL)
_engine: AsyncEngine | None = None
_Session: async_sessionmaker[AsyncSession] | None = None


def _ensure_engine() -> None:
    global _engine, _Session
    if not db_enabled:
        return
    if _engine is None:
        assert DATABASE_URL is not None
        _engine = create_async_engine(DATABASE_URL, future=True, echo=False)
        _Session = async_sessionmaker(_engine, expire_on_commit=False)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield an async session if DB is enabled; otherwise raise RuntimeError."""
    if not db_enabled:
        raise RuntimeError("DATABASE_URL not configured")
    _ensure_engine()
    assert _Session is not None
    async with _Session() as session:
        yield session
