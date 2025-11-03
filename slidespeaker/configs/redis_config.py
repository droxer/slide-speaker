"""
Centralized Redis configuration for SlideSpeaker (configs).
"""

import os
from typing import Any

import redis.asyncio as redis
from dotenv import load_dotenv

from slidespeaker.configs.config import config

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))


class RedisConfig:
    @classmethod
    def get_redis_client(cls) -> redis.Redis:
        return redis.Redis(
            host=config.redis_host,
            port=config.redis_port,
            db=config.redis_db,
            password=config.redis_password,
            decode_responses=True,
            socket_timeout=5.0,
        )

    @classmethod
    def get_redis_sync_client(cls) -> Any:
        import redis as sync_redis

        return sync_redis.Redis(
            host=config.redis_host,
            port=config.redis_port,
            db=config.redis_db,
            password=config.redis_password,
            decode_responses=True,
            socket_timeout=5.0,
        )

    @classmethod
    def get_connection_info(cls) -> dict[str, Any]:
        """Return non-sensitive Redis connection information for internal use only.

        WARNING: This method should not be exposed via public endpoints as it may
        reveal infrastructure details. For public health checks, only expose
        connectivity status without specific configuration details.

        Returns:
            dict: Connection information (for internal use only)
        """
        return {
            "host": config.redis_host,
            "port": config.redis_port,
            "db": config.redis_db,
            "password_set": bool(config.redis_password),
        }
