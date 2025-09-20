"""
Shared utilities for download routes.

This module provides common functions used across different download route modules
to avoid code duplication and improve maintainability.
"""

import urllib.request
from collections.abc import Iterator
from urllib.error import HTTPError

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from slidespeaker.configs.config import get_storage_provider
from slidespeaker.storage import StorageProvider


async def file_id_from_task(task_id: str) -> str:
    """Resolve a file_id from a task_id (DB → task payload).

    Uses the repository first. Legacy Redis mappings are not consulted here
    per project direction to make DB the source of truth for task metadata.
    """
    # 1) DB lookup (preferred)
    try:
        from slidespeaker.repository.task import get_file_id_by_task

        res = await get_file_id_by_task(task_id)
        if res:
            return str(res)
    except Exception:
        # Silently continue to payload fallback
        pass

    # 2) Fallback to the task payload from the queue
    from slidespeaker.core.task_queue import task_queue

    task = await task_queue.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    file_id = (task.get("kwargs") or {}).get("file_id") or task.get("file_id")
    if not file_id or not isinstance(file_id, str):
        raise HTTPException(status_code=404, detail="File not found for task")
    return str(file_id)


async def get_audio_files_from_state(file_id: str) -> list[str]:
    """Helper to read generated audio file paths from state.

    Prefers PDF audio step when present; otherwise falls back to slide audio.
    """
    from slidespeaker.core.state_manager import state_manager as sm

    state = await sm.get_state(file_id)
    if not state or "steps" not in state:
        return []
    steps = state["steps"]
    # Prefer PDF audio when available
    if (
        "generate_pdf_audio" in steps
        and steps["generate_pdf_audio"].get("data") is not None
    ):
        data = steps["generate_pdf_audio"]["data"]
        return (
            data
            if isinstance(data, list)
            else ([data] if isinstance(data, str) else [])
        )
    # Fall back to slide audio
    if "generate_audio" in steps and steps["generate_audio"].get("data") is not None:
        data = steps["generate_audio"]["data"]
        return (
            data
            if isinstance(data, list)
            else ([data] if isinstance(data, str) else [])
        )
    return []


def stream_concatenated_files(
    paths: list[str], chunk_size: int = 1024 * 256
) -> Iterator[bytes]:
    """Generator to stream multiple files sequentially as one stream."""

    def iterator() -> Iterator[bytes]:
        for p in paths:
            with open(p, "rb") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk

    return iterator()


def final_audio_object_keys(file_id: str) -> list[str]:
    # Prefer new non-final naming first; include legacy for backward compatibility
    return [f"{file_id}.mp3", f"{file_id}_final_audio.mp3", f"{file_id}_final.mp3"]


async def proxy_cloud_media(
    object_key: str, media_type: str, range_header: str | None
) -> StreamingResponse:
    """Proxy a cloud object through the API using signed-URL streaming first.

    This avoids loading the full media into memory. If URL streaming fails,
    fall back to SDK byte download as a last resort.
    """
    sp: StorageProvider = get_storage_provider()

    # Prefer: presigned URL streaming with Range support
    try:
        url = sp.get_file_url(object_key, expires_in=300)
        req = urllib.request.Request(url)
        if range_header:
            req.add_header("Range", range_header)
        resp = urllib.request.urlopen(req)  # nosec - controlled URL

        status = resp.getcode() or 200
        headers = resp.info()
        content_length = headers.get("Content-Length")
        content_range = headers.get("Content-Range")

        def iter_stream(chunk_size: int = 1024 * 256) -> Iterator[bytes]:
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                yield chunk

        out_headers = {
            "Content-Type": media_type,
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Access-Control-Allow-Origin": "*",
            "Accept-Ranges": "bytes",
        }
        if content_length:
            out_headers["Content-Length"] = content_length
        if content_range:
            out_headers["Content-Range"] = content_range

        return StreamingResponse(iter_stream(), status_code=status, headers=out_headers)
    except HTTPError as e:
        # Some providers return 400/403/404/416 for transient or permissioned HEAD/GET
        # Try SDK download as a fallback to avoid bubbling 4xx to the client.
        try:
            blob: bytes = sp.download_bytes(object_key)
            total = len(blob)

            def iter_mem(chunk_size: int = 1024 * 256) -> Iterator[bytes]:
                offset = 0
                while offset < total:
                    nxt = min(offset + chunk_size, total)
                    yield blob[offset:nxt]
                    offset = nxt

            return StreamingResponse(
                iter_mem(),
                status_code=200,
                headers={
                    "Content-Type": media_type,
                    "Content-Length": str(total),
                    "Accept-Ranges": "bytes",
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Access-Control-Allow-Origin": "*",
                },
            )
        except Exception:
            raise HTTPException(status_code=e.code, detail=str(e)) from e
    except Exception:
        # Fallback: download all bytes and stream from memory (no Range)
        pass

    try:
        blob2: bytes = sp.download_bytes(object_key)
        total = len(blob2)

        def iter_mem(chunk_size: int = 1024 * 256) -> Iterator[bytes]:
            offset = 0
            while offset < total:
                nxt = min(offset + chunk_size, total)
                yield blob2[offset:nxt]
                offset = nxt

        return StreamingResponse(
            iter_mem(),
            status_code=200,
            headers={
                "Content-Type": media_type,
                "Content-Length": str(total),
                "Accept-Ranges": "bytes",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Access-Control-Allow-Origin": "*",
            },
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail="Media not found") from e
