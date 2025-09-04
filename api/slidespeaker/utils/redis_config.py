"""
Centralized Redis configuration for SlideSpeaker.
Ensures consistent Redis configuration across all modules.
"""

import os
from typing import Any

import redis.asyncio as redis
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))


class RedisConfig:
    """Centralized Redis configuration management"""

    @classmethod
    def get_redis_client(cls) -> redis.Redis:
        """Get a Redis client with consistent configuration"""
        return redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=int(os.getenv("REDIS_DB", 7)),
            password=os.getenv("REDIS_PASSWORD", None),
            decode_responses=True,
            socket_timeout=5.0,
        )

    @classmethod
    def get_redis_sync_client(cls) -> Any:
        """Get a synchronous Redis client for compatibility"""
        import redis as sync_redis

        return sync_redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=int(os.getenv("REDIS_DB", 7)),
            password=os.getenv("REDIS_PASSWORD", None) or None,
            decode_responses=True,
            socket_timeout=5.0,
        )

    @classmethod
    def get_connection_info(cls) -> dict[str, Any]:
        """Get Redis connection information for debugging"""
        return {
            "host": os.getenv("REDIS_HOST", "localhost"),
            "port": int(os.getenv("REDIS_PORT", 6379)),
            "db": int(os.getenv("REDIS_DB", 0)),
            "password_set": bool(os.getenv("REDIS_PASSWORD")),
        }
