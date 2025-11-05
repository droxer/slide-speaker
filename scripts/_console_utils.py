"""
Shared Rich console helpers for CLI scripts.
"""

from __future__ import annotations

from functools import lru_cache

from rich.console import Console
from rich.text import Text


@lru_cache(maxsize=1)
def get_console() -> Console:
    """Return a shared stdout console instance."""
    return Console()


@lru_cache(maxsize=1)
def get_err_console() -> Console:
    """Return a shared stderr console instance."""
    return Console(stderr=True)


def status_label(label: str, style: str) -> Text:
    """Create a styled status label wrapped in brackets."""
    text = Text(f"[{label}]")
    text.stylize(style)
    return text
