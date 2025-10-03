"""Utilities for validating NextAuth sessions on backend requests."""

from __future__ import annotations

# jose does not provide type hints
import base64
import hashlib
import hmac
import json
import os
from typing import Any, cast

from fastapi import HTTPException, Request, status
from jose import JWTError, jwe, jwt  # type: ignore[import-untyped]
from loguru import logger

SESSION_COOKIE_NAMES = [
    "__Secure-next-auth.session-token",
    "next-auth.session-token",
]

AUTH_HEADER_PREFIX = "Bearer "

ALLOWED_ALGORITHMS = {"HS512", "HS256", "dir"}
HKDF_INFO_BASE = "NextAuth.js Generated Encryption Key"


def _get_nextauth_secret() -> str:
    secret = os.getenv("NEXTAUTH_SECRET")
    if not secret:
        raise RuntimeError("NEXTAUTH_SECRET is not configured")
    return secret


def _extract_session_token(request: Request) -> str | None:
    for cookie_name in SESSION_COOKIE_NAMES:
        token = request.cookies.get(cookie_name)
        if token:
            return token

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith(AUTH_HEADER_PREFIX):
        return auth_header[len(AUTH_HEADER_PREFIX) :].strip()

    return None


def _derive_encryption_key(secret: str | bytes, *, salt: str = "") -> bytes:
    key_material = secret.encode("utf-8") if isinstance(secret, str) else secret

    salt_bytes = salt.encode("utf-8") if salt else b""
    info_suffix = f" ({salt})" if salt else ""
    info_bytes = f"{HKDF_INFO_BASE}{info_suffix}".encode()

    hash_len = hashlib.sha256().digest_size
    if not salt_bytes:
        salt_bytes = b"\x00" * hash_len

    prk = hmac.new(salt_bytes, key_material, hashlib.sha256).digest()

    okm = b""
    previous = b""
    counter = 1
    while len(okm) < 32:
        data = previous + info_bytes + bytes([counter])
        previous = hmac.new(prk, data, hashlib.sha256).digest()
        okm += previous
        counter += 1
    return okm[:32]


def _decode_header(token: str) -> dict[str, Any]:
    try:
        header = jwt.get_unverified_header(token)
        if not isinstance(header, dict):
            raise JWTError("Token header is not a JSON object") from None
        return cast(dict[str, Any], header)
    except JWTError:
        parts = token.split(".")
        if not parts:
            raise
        try:
            padded = parts[0] + "=" * (-len(parts[0]) % 4)
            raw = base64.urlsafe_b64decode(padded.encode("ascii"))
            header = json.loads(raw.decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise JWTError("Unable to parse token header") from exc
        if not isinstance(header, dict):
            raise JWTError("Token header is not a JSON object") from None
        return cast(dict[str, Any], header)


def _decode_nextauth_jwt(token: str) -> dict[str, Any]:
    secret = _get_nextauth_secret()
    try:
        header = _decode_header(token)
    except JWTError as exc:
        preview = f"{token[:8]}..." if len(token) > 8 else token
        logger.warning(
            "Rejecting invalid NextAuth session token (failed to parse header, preview={}): {}",
            preview,
            str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid session",
        ) from exc

    algorithm = header.get("alg") if isinstance(header, dict) else None
    if not isinstance(algorithm, str) or algorithm not in ALLOWED_ALGORITHMS:
        preview = f"{token[:8]}..." if len(token) > 8 else token
        logger.warning(
            "Rejecting NextAuth session token with unsupported algorithm (alg={}, preview={})",
            algorithm,
            preview,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid session",
        )

    if algorithm == "dir":
        encryption_key = _derive_encryption_key(secret)
        try:
            plaintext = jwe.decrypt(token, encryption_key)
        except Exception as exc:  # jose raises JWEError, but catch broadly to log
            preview = f"{token[:8]}..." if len(token) > 8 else token
            logger.warning(
                "NextAuth JWE decrypt failed (preview={}): {}",
                preview,
                str(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid session",
            ) from exc

        try:
            payload = json.loads(plaintext.decode("utf-8"))
        except Exception as exc:
            preview = f"{token[:8]}..." if len(token) > 8 else token
            logger.error(
                "Failed to parse decrypted NextAuth payload as JSON (preview={}): {}",
                preview,
                str(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="server misconfiguration",
            ) from exc
        if not isinstance(payload, dict):
            logger.error(
                "Unexpected NextAuth payload type %s after decryption", type(payload)
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="server misconfiguration",
            )
        return cast(dict[str, Any], payload)

    try:
        decoded = jwt.decode(token, secret, algorithms=[algorithm])
    except JWTError as exc:
        preview = f"{token[:8]}..." if len(token) > 8 else token
        logger.warning(
            "NextAuth JWT decode failed (algorithm={}, preview={}): {}",
            algorithm,
            preview,
            str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid session",
        ) from exc
    if not isinstance(decoded, dict):
        logger.error(
            "Unexpected NextAuth payload type %s after JWT decode", type(decoded)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="server misconfiguration",
        )
    return cast(dict[str, Any], decoded)


async def require_authenticated_user(request: Request) -> dict[str, Any]:
    token = _extract_session_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication required",
        )

    try:
        return _decode_nextauth_jwt(token)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="server misconfiguration",
        ) from exc


def extract_user_id(decoded_token: dict[str, Any] | None) -> str | None:
    """Return the user id embedded in the NextAuth session payload."""
    if not isinstance(decoded_token, dict):
        return None
    user_section = decoded_token.get("user")
    if isinstance(user_section, dict):
        candidate = user_section.get("id") or user_section.get("user_id")
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    sub = decoded_token.get("sub")
    if isinstance(sub, str) and sub.strip():
        return sub.strip()
    return None
