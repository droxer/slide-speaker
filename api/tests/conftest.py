"""
Configuration file for pytest test suite.
"""

import os
import sys
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

# Add the api directory to the path so we can import the app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from server import app


@pytest.fixture(scope="module")
def test_client() -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI app."""
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="module")
def mock_env(monkeymodule: pytest.MonkeyPatch) -> None:
    """Mock environment variables for testing."""
    monkeymodule.setenv("TESTING", "true")
    monkeymodule.setenv("REDIS_HOST", "localhost")
    monkeymodule.setenv("REDIS_PORT", "6379")
    monkeymodule.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")


@pytest.fixture
def temp_file() -> Generator[str, None, None]:
    """Create a temporary file for testing."""
    import tempfile

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp:
        temp.write(b"Test file content")
        temp.flush()
        path = temp.name
    yield path
    # Cleanup
    os.unlink(path)
