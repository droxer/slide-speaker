"""
pytest configuration for SlideSpeaker API tests.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing."""
    return AsyncMock()


@pytest.fixture
def mock_storage_provider():
    """Mock storage provider for testing."""
    return MagicMock()


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    config = MagicMock()
    config.output_dir = "/tmp/test_output"
    config.storage_provider = "local"
    return config
