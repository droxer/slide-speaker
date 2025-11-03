"""Password hashing helpers for authentication services."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from typing import Final

try:  # Optional fallback for legacy bcrypt hashes
    from passlib.context import CryptContext  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    _LEGACY_CONTEXT = None
else:  # pragma: no cover - only exercised when passlib available
    _LEGACY_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")


SCHEME: Final[str] = "pbkdf2_sha256"
ITERATIONS: Final[int] = 390_000
SALT_BYTES: Final[int] = 16


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode(value + padding)


def hash_password(password: str) -> str:
    """Return a secure password hash for storage using PBKDF2-HMAC-SHA256."""

    if not isinstance(password, str):  # Defensive: ensure predictable encoding
        raise TypeError("password must be a string")

    salt = os.urandom(SALT_BYTES)
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        ITERATIONS,
    )
    return f"{SCHEME}${ITERATIONS}${_b64encode(salt)}${_b64encode(derived)}"


def verify_password(password: str, hashed: str | None) -> bool:
    """Verify a plaintext password against the stored PBKDF2 hash."""

    if not hashed or not isinstance(password, str):
        return False

    if not hashed.startswith(f"{SCHEME}$"):
        if _LEGACY_CONTEXT is None:
            return False
        try:
            return bool(_LEGACY_CONTEXT.verify(password, hashed))
        except ValueError:
            return False

    try:
        scheme, iter_str, salt_b64, hash_b64 = hashed.split("$", 3)
        if scheme != SCHEME:
            return False
        iterations = int(iter_str)
        salt = _b64decode(salt_b64)
        expected = _b64decode(hash_b64)
        candidate = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations,
        )
    except (ValueError, TypeError):
        return False

    return hmac.compare_digest(candidate, expected)
