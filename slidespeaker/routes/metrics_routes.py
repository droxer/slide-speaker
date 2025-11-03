"""
Metrics endpoints for monitoring API performance.
"""

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from slidespeaker.auth import require_authenticated_user
from slidespeaker.core.monitoring import get_current_metrics

router = APIRouter(
    prefix="/api/metrics",
    tags=["metrics"],
)

# Separate router for authenticated endpoints
protected_router = APIRouter(
    prefix="/api/metrics",
    tags=["metrics"],
    dependencies=[Depends(require_authenticated_user)],
)


@router.get("/health")
async def metrics_health_check() -> dict[str, str]:
    """Basic health check for the metrics endpoint."""
    return {"status": "healthy", "service": "metrics"}


@protected_router.get("/performance")
async def get_performance_metrics() -> dict[str, Any]:
    """Get current API performance metrics."""
    metrics = get_current_metrics()
    return {"metrics": metrics, "status": "success"}


@protected_router.get("/prometheus")
async def prometheus_metrics() -> JSONResponse:
    """Export metrics in Prometheus format."""
    metrics = get_current_metrics()

    # Format metrics for Prometheus
    prometheus_output = []
    prometheus_output.append(
        "# HELP slidespeaker_api_requests_total Total number of requests"
    )
    prometheus_output.append("# TYPE slidespeaker_api_requests_total counter")

    prometheus_output.append(
        "# HELP slidespeaker_api_errors_total Total number of errors"
    )
    prometheus_output.append("# TYPE slidespeaker_api_errors_total counter")

    prometheus_output.append(
        "# HELP slidespeaker_api_response_time_seconds Average response time"
    )
    prometheus_output.append("# TYPE slidespeaker_api_response_time_seconds gauge")

    for endpoint, data in metrics.items():
        # Sanitize endpoint name for Prometheus
        sanitized_endpoint = (
            endpoint.replace("-", "_").replace("/", "_").replace(".", "_")
        )

        prometheus_output.append(
            f'slidespeaker_api_requests_total{{endpoint="{sanitized_endpoint}"}} {data["requests"]}'
        )
        prometheus_output.append(
            f'slidespeaker_api_errors_total{{endpoint="{sanitized_endpoint}"}} {data["errors"]}'
        )
        prometheus_output.append(
            f'slidespeaker_api_response_time_seconds{{endpoint="{sanitized_endpoint}"}} {data["avg_response_time"]}'
        )

    return JSONResponse(
        content="\n".join(prometheus_output),
        headers={"Content-Type": "text/plain; charset=utf-8"},
    )
