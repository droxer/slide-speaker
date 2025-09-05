"""
Logging configuration module for SlideSpeaker.
Provides centralized logging setup with configurable levels and handlers.

This module configures the application's logging system with support for
both console and file-based logging, customizable formats, and log rotation.
"""

import logging
import logging.config
import os
from typing import Any


def setup_logging(
    log_level: str | None = None,
    log_format: str | None = None,
    enable_file_logging: bool = False,
    log_file: str = "slidespeaker.log",
    log_dir: str = "logs",
) -> None:
    """
    Configure logging for the SlideSpeaker application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Custom log format string
        enable_file_logging: Whether to write logs to file
        log_file: Log file name
        log_dir: Directory for log files
    """
    if log_level is None:
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    if log_format is None:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    config: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {"format": log_format, "datefmt": "%Y-%m-%d %H:%M:%S"},
            "detailed": {
                "format": (
                    "%(asctime)s - %(name)s - %(levelname)s - "
                    "%(module)s - %(funcName)s - %(lineno)d - %(message)s"
                ),
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "level": log_level,
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "stream": "ext://sys.stdout",
            }
        },
        "loggers": {
            "slidespeaker": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False,
            },
            "uvicorn": {"level": "INFO", "handlers": ["console"], "propagate": False},
            "fastapi": {"level": "INFO", "handlers": ["console"], "propagate": False},
        },
        "root": {"level": log_level, "handlers": ["console"]},
    }

    if enable_file_logging:
        # Ensure log directory exists
        os.makedirs(log_dir, exist_ok=True)

        config["handlers"].update(
            {
                "file": {
                    "level": "DEBUG",
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": os.path.join(log_dir, log_file),
                    "maxBytes": 10485760,  # 10MB
                    "backupCount": 5,
                    "formatter": "detailed",
                }
            }
        )

        # Add file handler to loggers
        for logger_name in config["loggers"]:
            config["loggers"][logger_name]["handlers"].append("file")
        config["root"]["handlers"].append("file")

    logging.config.dictConfig(config)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name."""
    return logging.getLogger(f"slidespeaker.{name}")


def set_log_level(level: str, logger_name: str | None = None) -> None:
    """
    Dynamically change the log level for a specific logger or the root logger.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        logger_name: Logger name (None for root logger)
    """

    logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
    logger.setLevel(getattr(logging, level.upper()))
