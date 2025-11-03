"""
Test suite for metrics endpoints.
"""

from fastapi.testclient import TestClient


class TestMetricsEndpoints:
    """Test cases for metrics endpoints."""

    def test_metrics_health_check(self, test_client: TestClient) -> None:
        """Test the metrics health check endpoint."""
        response = test_client.get("/api/metrics/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "service" in data
        assert data["service"] == "metrics"

    def test_performance_metrics_unauthorized(self, test_client: TestClient) -> None:
        """Test that performance metrics require authentication."""
        response = test_client.get("/api/metrics/performance")
        # Should require authentication
        assert response.status_code == 401

    def test_prometheus_metrics_unauthorized(self, test_client: TestClient) -> None:
        """Test that Prometheus metrics require authentication."""
        response = test_client.get("/api/metrics/prometheus")
        # Should require authentication
        assert response.status_code == 401
