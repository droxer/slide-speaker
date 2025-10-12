"""
Database models for SlideSpeaker.

This module contains the SQLAlchemy models used by the application.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, synonym


class Base(DeclarativeBase):
    pass


class TaskRow(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id = synonym("id")  # backward compatibility for legacy attribute name
    file_id: Mapped[str] = mapped_column(String(64), index=True)
    task_type: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), index=True)
    kwargs: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_ext: Mapped[str | None] = mapped_column(String(16), nullable=True)
    owner_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    voice_language: Mapped[str | None] = mapped_column(String(64), nullable=True)
    subtitle_language: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False))


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    picture: Mapped[str | None] = mapped_column(Text, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferred_language: Mapped[str] = mapped_column(String(64), default="english")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.now, onupdate=datetime.now
    )
