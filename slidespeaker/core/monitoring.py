"""
Monitoring and metrics collection for the SlideSpeaker API.
"""

import time
from collections.abc import Callable
from functools import wraps
from typing import Any

from fastapi import HTTPException
from loguru import logger


class APIMetrics:
    """Simple API metrics collector."""

    def __init__(self) -> None:
        self.request_counts: dict[str, int] = {}
        self.response_times: dict[str, list[float]] = {}
        self.error_counts: dict[str, int] = {}

    def record_request(self, endpoint: str) -> None:
        """Record an incoming request to an endpoint."""
        self.request_counts[endpoint] = self.request_counts.get(endpoint, 0) + 1

    def record_response_time(self, endpoint: str, duration: float) -> None:
        """Record response time for an endpoint."""
        if endpoint not in self.response_times:
            self.response_times[endpoint] = []
        self.response_times[endpoint].append(duration)

    def record_error(self, endpoint: str) -> None:
        """Record an error for an endpoint."""
        self.error_counts[endpoint] = self.error_counts.get(endpoint, 0) + 1

    def get_metrics(self) -> dict[str, Any]:
        """Get current metrics."""
        metrics = {}
        for endpoint in self.request_counts:
            metrics[endpoint] = {
                "requests": self.request_counts[endpoint],
                "errors": self.error_counts.get(endpoint, 0),
                "avg_response_time": (
                    sum(self.response_times.get(endpoint, []))
                    / len(self.response_times.get(endpoint, [1]))
                )
                if self.response_times.get(endpoint)
                else 0,
            }
        return metrics


# Global metrics instance
metrics = APIMetrics()


def monitor_endpoint(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to monitor endpoint performance and errors."""

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        endpoint = func.__name__
        start_time = time.time()

        metrics.record_request(endpoint)
        try:
            result = await func(*args, **kwargs)
        except HTTPException as http_exc:
            duration = time.time() - start_time
            metrics.record_response_time(endpoint, duration)
            if http_exc.status_code >= 500:
                metrics.record_error(endpoint)
                logger.error(
                    "HTTP %s error in endpoint %s: %s",
                    http_exc.status_code,
                    endpoint,
                    http_exc.detail,
                )
            else:
                logger.info(
                    "HTTP %s response from endpoint %s: %s",
                    http_exc.status_code,
                    endpoint,
                    http_exc.detail,
                )
            raise
        except Exception as exc:
            duration = time.time() - start_time
            metrics.record_response_time(endpoint, duration)
            metrics.record_error(endpoint)
            logger.exception(f"Unhandled error in endpoint {endpoint}: {exc}")
            raise
        else:
            duration = time.time() - start_time
            metrics.record_response_time(endpoint, duration)
            return result

    return wrapper


def get_current_metrics() -> dict[str, Any]:
    """Get current API metrics."""
    return metrics.get_metrics()
