"""
Shared utilities for download routes.

This module provides common functions used across different download route modules
to avoid code duplication and improve maintainability.
"""

from collections.abc import AsyncIterator, Iterator
from contextlib import AsyncExitStack

import httpx
from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

from slidespeaker.configs.config import get_storage_provider
from slidespeaker.storage import StorageProvider
from slidespeaker.storage.paths import output_object_key


def build_headers(
    request: Request,
    *,
    content_type: str,
    content_length: int | None = None,
    disposition: str | None = None,
    cache_control: str = "public, max-age=3600",
    include_cors_headers: bool = True,
) -> dict[str, str]:
    """
    Build standardized HTTP headers for download responses.

    Args:
        request: The FastAPI request object
        content_type: MIME type of the content
        content_length: Size of the content in bytes (optional)
        disposition: Content-Disposition header value (optional)
        cache_control: Cache-Control header value (default: "public, max-age=3600")
        include_cors_headers: Whether to include CORS headers (default: True)

    Returns:
        Dictionary of HTTP headers
    """
    origin = request.headers.get("origin") or request.headers.get("Origin")
    headers: dict[str, str] = {
        "Content-Type": content_type,
        "Cache-Control": cache_control,
    }

    if content_length is not None:
        headers["Content-Length"] = str(content_length)

    if disposition:
        headers["Content-Disposition"] = disposition

    if include_cors_headers:
        headers["Accept-Ranges"] = "bytes"
        if origin:
            headers["Access-Control-Allow-Origin"] = origin
            headers["Access-Control-Allow-Credentials"] = "true"

    return headers


def build_cors_headers() -> dict[str, str]:
    """
    Build standardized CORS headers for preflight responses.

    Returns:
        Dictionary of CORS headers
    """
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
        "Access-Control-Allow-Headers": "Range, Accept, Accept-Encoding, Accept-Language, Content-Type",
    }


def iter_file(
    path: str, offset: int = 0, length: int | None = None, chunk_size: int = 1024 * 256
) -> Iterator[bytes]:
    """
    Generator to stream a file from a specific offset for a specific length.

    Args:
        path: Path to the file
        offset: Starting position in the file (default: 0)
        length: Number of bytes to read (default: entire file from offset)
        chunk_size: Size of chunks to read at a time (default: 256KB)

    Yields:
        Bytes from the file
    """
    with open(path, "rb") as f:
        f.seek(offset)
        remaining = length if length is not None else -1

        while remaining != 0:
            read_size = chunk_size if remaining < 0 else min(chunk_size, remaining)
            data = f.read(read_size)
            if not data:
                break
            yield data
            if remaining > 0:
                remaining -= len(data)


def check_file_exists(object_key: str) -> bool:
    """
    Check if a file exists in storage.

    Args:
        object_key: Storage object key to check

    Returns:
        True if file exists, False otherwise
    """
    sp: StorageProvider = get_storage_provider()
    return sp.file_exists(object_key)


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


def final_audio_object_keys(file_id: str, task_id: str | None = None) -> list[str]:
    """Return possible storage object keys for final audio outputs."""
    keys: list[str] = []
    bases: list[str] = []
    if task_id:
        bases.append(task_id)
    bases.append(file_id)
    for base in bases:
        base = base.strip()
        if base:
            keys.append(output_object_key(base, "audio", "final.mp3"))
    # Legacy fallbacks
    keys.extend(
        [f"{file_id}.mp3", f"{file_id}_final_audio.mp3", f"{file_id}_final.mp3"]
    )
    return keys


async def proxy_cloud_media(
    object_key: str,
    media_type: str,
    range_header: str | None,
    *,
    origin: str | None = None,
) -> StreamingResponse:
    """Proxy a cloud object through the API using signed-URL streaming first.

    This avoids loading the full media into memory. If URL streaming fails,
    fall back to SDK byte download as a last resort.
    """
    sp: StorageProvider = get_storage_provider()

    # Prefer: presigned URL streaming with Range support
    stack = AsyncExitStack()
    try:
        url = sp.get_file_url(object_key, expires_in=300)
        headers: dict[str, str] = {}
        if range_header:
            headers["Range"] = range_header

        client = await stack.enter_async_context(
            httpx.AsyncClient(timeout=None, follow_redirects=True)
        )
        resp = await stack.enter_async_context(
            client.stream("GET", url, headers=headers)
        )

        status = resp.status_code
        if status >= 400:
            if status in {400, 403, 404, 416}:
                raw_detail = await resp.aread()
                detail = raw_detail.decode("utf-8", errors="replace")
                raise HTTPException(status_code=status, detail=detail)
            resp.raise_for_status()

        async def iter_stream(
            chunk_size: int = 1024 * 256,
        ) -> AsyncIterator[bytes]:
            async for chunk in resp.aiter_raw(chunk_size):
                yield chunk

        content_length = resp.headers.get("Content-Length")
        content_range = resp.headers.get("Content-Range")

        out_headers: dict[str, str] = {
            "Content-Type": media_type,
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Accept-Ranges": "bytes",
        }
        if "Content-Encoding" in resp.headers:
            out_headers["Content-Encoding"] = resp.headers["Content-Encoding"]
        if "Content-Disposition" in resp.headers:
            out_headers["Content-Disposition"] = resp.headers["Content-Disposition"]
        if "ETag" in resp.headers:
            out_headers["ETag"] = resp.headers["ETag"]
        if "Last-Modified" in resp.headers:
            out_headers["Last-Modified"] = resp.headers["Last-Modified"]
        if content_range:
            out_headers["Content-Range"] = content_range
        if not content_length and content_range:
            try:
                units, range_part = content_range.split(" ", 1)
                if units.lower() == "bytes":
                    span, total_part = range_part.split("/", 1)
                    if "-" in span:
                        start_s, end_s = span.split("-", 1)
                        if start_s.strip() and end_s.strip():
                            start = int(start_s)
                            end = int(end_s)
                            length = (end - start) + 1
                            if length > 0:
                                out_headers["Content-Length"] = str(length)
                    elif span.strip():
                        # e.g. "12345-" (open ended)
                        start = int(span)
                        if total_part.strip().isdigit():
                            total = int(total_part)
                            if total > start:
                                out_headers["Content-Length"] = str(total - start)
            except Exception:
                pass
        elif content_length:
            out_headers["Content-Length"] = content_length
        if origin:
            out_headers["Access-Control-Allow-Origin"] = origin
            out_headers["Access-Control-Allow-Credentials"] = "true"

        cleanup_stack = stack.pop_all()
        response = StreamingResponse(
            iter_stream(),
            status_code=status,
            headers=out_headers,
            media_type=media_type,
            background=BackgroundTask(cleanup_stack.aclose),
        )
        return response
    except HTTPException as e:
        # Some providers return 4xx for transient or permissioned GETs
        if e.status_code not in (400, 403, 404, 416):
            raise
        # Fall through to SDK download fallback
    except httpx.HTTPError:
        pass
    finally:
        await stack.aclose()

    # Fallback: download bytes via storage SDK
    try:
        blob: bytes = sp.download_bytes(object_key)
        total = len(blob)

        def iter_mem(chunk_size: int = 1024 * 256) -> Iterator[bytes]:
            offset = 0
            while offset < total:
                nxt = min(offset + chunk_size, total)
                yield blob[offset:nxt]
                offset = nxt

        headers = {
            "Content-Type": media_type,
            "Content-Length": str(total),
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-cache, no-store, must-revalidate",
        }
        if origin:
            headers["Access-Control-Allow-Origin"] = origin
            headers["Access-Control-Allow-Credentials"] = "true"

        return StreamingResponse(
            iter_mem(),
            status_code=200,
            headers=headers,
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail="Media not found") from e


async def proxy_cloud_media_with_range(
    object_key: str,
    media_type: str,
    range_header: str | None,
    *,
    origin: str | None = None,
) -> StreamingResponse:
    """
    Proxy a cloud object through the API using signed-URL streaming with range support.

    This avoids loading the full media into memory. If URL streaming fails,
    fall back to SDK byte download as a last resort.

    Args:
        object_key: Storage object key
        media_type: MIME type of the content
        range_header: HTTP Range header value (if any)
        origin: Origin header for CORS (optional)

    Returns:
        StreamingResponse with the media content
    """
    sp: StorageProvider = get_storage_provider()

    # Prefer: presigned URL streaming with Range support
    stack = AsyncExitStack()
    try:
        url = sp.get_file_url(object_key, expires_in=300)
        headers: dict[str, str] = {}
        if range_header:
            headers["Range"] = range_header

        client = await stack.enter_async_context(
            httpx.AsyncClient(timeout=None, follow_redirects=True)
        )
        resp = await stack.enter_async_context(
            client.stream("GET", url, headers=headers)
        )

        status = resp.status_code
        if status >= 400:
            if status in {400, 403, 404, 416}:
                raw_detail = await resp.aread()
                detail = raw_detail.decode("utf-8", errors="replace")
                raise HTTPException(status_code=status, detail=detail)
            resp.raise_for_status()

        async def iter_stream(
            chunk_size: int = 1024 * 256,
        ) -> AsyncIterator[bytes]:
            async for chunk in resp.aiter_raw(chunk_size):
                yield chunk

        content_length = resp.headers.get("Content-Length")
        content_range = resp.headers.get("Content-Range")

        out_headers: dict[str, str] = {
            "Content-Type": media_type,
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Accept-Ranges": "bytes",
        }
        if "Content-Encoding" in resp.headers:
            out_headers["Content-Encoding"] = resp.headers["Content-Encoding"]
        if "Content-Disposition" in resp.headers:
            out_headers["Content-Disposition"] = resp.headers["Content-Disposition"]
        if "ETag" in resp.headers:
            out_headers["ETag"] = resp.headers["ETag"]
        if "Last-Modified" in resp.headers:
            out_headers["Last-Modified"] = resp.headers["Last-Modified"]
        if content_range:
            out_headers["Content-Range"] = content_range
        if not content_length and content_range:
            try:
                units, range_part = content_range.split(" ", 1)
                if units.lower() == "bytes":
                    span, total_part = range_part.split("/", 1)
                    if "-" in span:
                        start_s, end_s = span.split("-", 1)
                        if start_s.strip() and end_s.strip():
                            start = int(start_s)
                            end = int(end_s)
                            length = (end - start) + 1
                            if length > 0:
                                out_headers["Content-Length"] = str(length)
                    elif span.strip():
                        # e.g. "12345-" (open ended)
                        start = int(span)
                        if total_part.strip().isdigit():
                            total = int(total_part)
                            if total > start:
                                out_headers["Content-Length"] = str(total - start)
            except Exception:
                pass
        elif content_length:
            out_headers["Content-Length"] = content_length
        if origin:
            out_headers["Access-Control-Allow-Origin"] = origin
            out_headers["Access-Control-Allow-Credentials"] = "true"

        cleanup_stack = stack.pop_all()
        response = StreamingResponse(
            iter_stream(),
            status_code=status,
            headers=out_headers,
            media_type=media_type,
            background=BackgroundTask(cleanup_stack.aclose),
        )
        return response
    except HTTPException as e:
        # Some providers return 4xx for transient or permissioned GETs
        if e.status_code not in (400, 403, 404, 416):
            raise
        # Fall through to SDK download fallback
    except httpx.HTTPError:
        pass
    finally:
        await stack.aclose()

    # Fallback: download bytes via storage SDK
    try:
        blob: bytes = sp.download_bytes(object_key)
        total = len(blob)

        def iter_mem(chunk_size: int = 1024 * 256) -> Iterator[bytes]:
            offset = 0
            while offset < total:
                nxt = min(offset + chunk_size, total)
                yield blob[offset:nxt]
                offset = nxt

        headers = {
            "Content-Type": media_type,
            "Content-Length": str(total),
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-cache, no-store, must-revalidate",
        }
        if origin:
            headers["Access-Control-Allow-Origin"] = origin
            headers["Access-Control-Allow-Credentials"] = "true"

        return StreamingResponse(
            iter_mem(),
            status_code=200,
            headers=headers,
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail="Media not found") from e
