"""Logging configuration for FarmShield AI Backend."""

import logging
import sys
from typing import Any
from app.core.config import settings


class SensitiveDataFilter(logging.Filter):
    """Filter to prevent accidental logging of credentials and secrets."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        # Redact JWT secret if present
        if settings.JWT_SECRET_KEY and settings.JWT_SECRET_KEY in message:
            record.msg = message.replace(settings.JWT_SECRET_KEY, "[REDACTED_SECRET]")
            record.args = ()
        return True


def setup_logging() -> logging.Logger:
    """Configure structured console logging for the application."""
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    handler.setFormatter(formatter)
    handler.addFilter(SensitiveDataFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Avoid adding duplicate handlers on reload
    if not root_logger.handlers:
        root_logger.addHandler(handler)
    else:
        root_logger.handlers = [handler]

    # Tone down noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DEBUG else logging.WARNING
    )

    logger = logging.getLogger("farmshield")
    logger.setLevel(log_level)
    return logger


logger = setup_logging()
