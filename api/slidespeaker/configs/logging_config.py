"""
Logging configuration for SlideSpeaker (configs).
"""

import logging
import logging.config
import sys
from typing import Any

from slidespeaker.configs.config import config


def setup_logging(
    log_level: str | None = None,
    log_format: str | None = None,
    enable_file_logging: bool = False,
    log_file: str = "slidespeaker.log",
    log_dir: str = "logs",
    component: str = "default",
) -> None:
    if log_level is None:
        log_level = config.log_level

    if enable_file_logging and log_file == "slidespeaker.log":
        if component == "api":
            log_file = "api.log"
        elif component == "master_worker":
            log_file = "master_worker.log"
        elif component == "worker":
            log_file = "worker.log"
        else:
            log_file = f"{component}.log"

    if log_format is None:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    logging_dict: dict[str, Any] = {
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
            "uvicorn": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False,
            },
            "fastapi": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False,
            },
        },
        "root": {"level": log_level, "handlers": ["console"]},
    }

    if enable_file_logging:
        import os

        log_dir = log_dir or config.log_dir
        os.makedirs(log_dir, exist_ok=True)

        logging_dict["handlers"].update(
            {
                "file": {
                    "level": "DEBUG",
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": os.path.join(log_dir, log_file),
                    "maxBytes": 10485760,
                    "backupCount": 5,
                    "formatter": "detailed",
                }
            }
        )
        for logger_name in logging_dict["loggers"]:
            logging_dict["loggers"][logger_name]["handlers"].append("file")
        logging_dict["root"]["handlers"].append("file")

    logging.config.dictConfig(logging_dict)

    # Also configure loguru to respect the configured log level/handlers
    try:
        from loguru import logger as loguru_logger

        # Reset existing handlers and add stdout sink
        loguru_logger.remove()
        loguru_logger.add(sys.stdout, level=log_level)

        # Optional file sink aligned with standard logging
        if enable_file_logging:
            import os as _os

            log_dir_fs = log_dir or config.log_dir
            _os.makedirs(log_dir_fs, exist_ok=True)
            log_path = _os.path.join(log_dir_fs, log_file)
            loguru_logger.add(
                log_path,
                level="DEBUG",
                rotation="10 MB",
                retention=5,
                backtrace=False,
                diagnose=False,
            )
    except Exception:
        # If loguru isn't present or something fails, ignore silently
        pass


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"slidespeaker.{name}")


def set_log_level(level: str, logger_name: str | None = None) -> None:
    logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
    logger.setLevel(getattr(logging, level.upper()))
