"""
Logging utilities for Trading Engine
"""

import logging
import sys
from pathlib import Path
from typing import Optional
import structlog
from datetime import datetime


def setup_logger(
    name: str = "trading_engine",
    level: str = "INFO",
    log_file: Optional[str] = None,
    format_type: str = "json"
) -> structlog.BoundLogger:
    """
    Setup structured logger

    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        format_type: Format type (json or console)

    Returns:
        Configured structlog logger
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level
    )

    # Setup file handler if log file specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        logging.root.addHandler(file_handler)

    # Configure structlog processors
    processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if format_type == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger(name)


def get_logger(name: str = "trading_engine") -> structlog.BoundLogger:
    """
    Get configured logger instance

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return structlog.get_logger(name)


class LogContext:
    """Context manager for adding context to logs"""

    def __init__(self, logger: structlog.BoundLogger, **context):
        self.logger = logger
        self.context = context
        self.bound_logger = None

    def __enter__(self):
        self.bound_logger = self.logger.bind(**self.context)
        return self.bound_logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.bound_logger.error(
                "Exception in context",
                exc_type=exc_type.__name__,
                exc_value=str(exc_val)
            )
        return False
