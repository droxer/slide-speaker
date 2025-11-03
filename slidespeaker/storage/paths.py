"""
Helpers for building storage object keys and URIs.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from slidespeaker.configs.config import config

UPLOADS_PREFIX = "uploads"
OUTPUTS_PREFIX = "outputs"


def _normalize_extension(file_ext: str | None) -> str:
    if not file_ext:
        return ""
    ext = file_ext.lower()
    if not ext.startswith("."):
        ext = f".{ext}"
    return ext


def build_storage_uri(object_key: str) -> str:
    """Convert an object key into a provider-qualified URI."""
    provider = (config.storage_provider or "local").lower()
    if provider == "s3":
        bucket = (config.storage_config or {}).get("bucket_name") or ""
        prefix = f"s3://{bucket}/" if bucket else "s3://"
        return f"{prefix}{object_key}"
    if provider == "oss":
        bucket = (config.storage_config or {}).get("bucket_name") or ""
        prefix = f"oss://{bucket}/" if bucket else "oss://"
        return f"{prefix}{object_key}"
    return f"local://{object_key}"


def object_key_from_uri(uri: str | None) -> str | None:
    """Extract the storage object key from a provider-qualified URI."""
    if not uri:
        return None
    if "://" not in uri:
        return uri.lstrip("/")
    _, remainder = uri.split("://", 1)
    # Strip bucket segment if present (e.g., bucket/key)
    parts = remainder.split("/", 1)
    if len(parts) == 1:
        return ""
    return parts[1]


def upload_object_key(file_id: str, file_ext: str | None) -> str:
    """Return the canonical object key for an uploaded source file."""
    ext = _normalize_extension(file_ext)
    return f"{UPLOADS_PREFIX}/{file_id}{ext}"


def resolve_output_base_id(
    file_id: str,
    *,
    task_id: str | None = None,
    state: Mapping[str, Any] | None = None,
) -> str:
    """Choose the correct base identifier for task outputs."""
    if task_id:
        tid = str(task_id).strip()
        if tid:
            return tid
    if state:
        candidate = state.get("task_id")
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
        task_block = state.get("task")
        if isinstance(task_block, Mapping):
            candidate = task_block.get("task_id")
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
    return str(file_id).strip()


def output_object_key(base_id: str, *segments: str) -> str:
    """Assemble an outputs object key for a given task/file base id."""
    cleaned = [OUTPUTS_PREFIX, base_id]
    cleaned.extend(s.strip("/\\") for s in segments if s and s.strip("/\\"))
    return "/".join(cleaned)


def upload_storage_uri(file_id: str, file_ext: str | None) -> tuple[str, str]:
    """Return (object_key, uri) for an uploaded source file."""
    key = upload_object_key(file_id, file_ext)
    return key, build_storage_uri(key)


def output_storage_uri(
    file_id: str,
    *,
    task_id: str | None = None,
    state: Mapping[str, Any] | None = None,
    segments: tuple[str, ...],
) -> tuple[str, str, str]:
    """Return (base_id, object_key, uri) for a task output artifact."""
    base_id = resolve_output_base_id(file_id, task_id=task_id, state=state)
    object_key = output_object_key(base_id, *segments)
    return base_id, object_key, build_storage_uri(object_key)
