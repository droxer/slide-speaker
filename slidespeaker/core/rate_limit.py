"""
Rate limiting configuration for the SlideSpeaker API.
"""

from collections.abc import Awaitable, Callable
from typing import cast

from fastapi import FastAPI, Request
from fastapi.responses import Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# Create a rate limiter instance
limiter = Limiter(key_func=get_remote_address)

_ExceptionHandler = Callable[[Request, Exception], Awaitable[Response]]


def add_rate_limiting(app: FastAPI) -> None:
    """Attach rate limiting to the FastAPI application."""
    app.state.limiter = limiter
    app.add_exception_handler(
        RateLimitExceeded,
        cast(_ExceptionHandler, _rate_limit_exceeded_handler),
    )
