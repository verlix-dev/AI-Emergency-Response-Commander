"""Centralized JSON logging configuration."""

import json
import logging
from datetime import datetime, timezone

from app.core.config import get_settings


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(), "level": record.levelname, "logger": record.name, "message": record.getMessage()})


def configure_logging() -> None:
    """Configure the shared structured logger once per process."""
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(get_settings().log_level.upper())


def get_logger(name: str) -> logging.Logger:
    """Retrieve an application logger from the central configuration."""
    return logging.getLogger(name)
