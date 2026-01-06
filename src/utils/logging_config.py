"""
ERP Arabic OCR Microservice - Structured Logging Configuration
===============================================================
JSON-formatted logging with request context.
"""

import os
import sys
import json
import logging
import threading
from datetime import datetime
from typing import Dict, Any, Optional
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler


# Thread-local storage for request context
_context = threading.local()


def set_request_context(
    request_id: Optional[str] = None,
    client_id: Optional[str] = None,
    **extra
) -> None:
    """
    Set request context for logging.

    Args:
        request_id: Unique request identifier
        client_id: Client identifier
        **extra: Additional context fields
    """
    _context.request_id = request_id
    _context.client_id = client_id
    _context.extra = extra


def clear_request_context() -> None:
    """Clear request context."""
    _context.request_id = None
    _context.client_id = None
    _context.extra = {}


def get_request_context() -> Dict[str, Any]:
    """Get current request context."""
    return {
        "request_id": getattr(_context, 'request_id', None),
        "client_id": getattr(_context, 'client_id', None),
        **getattr(_context, 'extra', {})
    }


class JSONFormatter(logging.Formatter):
    """
    JSON log formatter for structured logging.

    Output format:
    {
        "timestamp": "2026-01-06T12:00:00.000Z",
        "level": "INFO",
        "logger": "module.name",
        "message": "Log message",
        "request_id": "abc123",
        "client_id": "client_1",
        "extra": {...}
    }
    """

    def __init__(
        self,
        include_timestamp: bool = True,
        include_level: bool = True,
        include_logger: bool = True,
        include_location: bool = False,
        extra_fields: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize JSON formatter.

        Args:
            include_timestamp: Include timestamp field
            include_level: Include log level field
            include_logger: Include logger name field
            include_location: Include file/line location
            extra_fields: Static extra fields to include
        """
        super().__init__()
        self.include_timestamp = include_timestamp
        self.include_level = include_level
        self.include_logger = include_logger
        self.include_location = include_location
        self.extra_fields = extra_fields or {}

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {}

        # Timestamp
        if self.include_timestamp:
            log_data["timestamp"] = datetime.utcnow().isoformat() + "Z"

        # Level
        if self.include_level:
            log_data["level"] = record.levelname

        # Logger name
        if self.include_logger:
            log_data["logger"] = record.name

        # Message
        log_data["message"] = record.getMessage()

        # Location
        if self.include_location:
            log_data["location"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName
            }

        # Request context
        context = get_request_context()
        if context.get("request_id"):
            log_data["request_id"] = context["request_id"]
        if context.get("client_id"):
            log_data["client_id"] = context["client_id"]

        # Extra context fields
        for key, value in context.items():
            if key not in ("request_id", "client_id") and value is not None:
                log_data[key] = value

        # Static extra fields
        log_data.update(self.extra_fields)

        # Record extra attributes
        if hasattr(record, 'extra_data'):
            log_data.update(record.extra_data)

        # Exception info
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False, default=str)


class TextFormatter(logging.Formatter):
    """
    Human-readable text formatter for development.

    Output format:
    2026-01-06 12:00:00,000 - INFO - [req_id] module.name - Message
    """

    DEFAULT_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    CONTEXT_FORMAT = "%(asctime)s - %(levelname)s - [%(request_id)s] %(name)s - %(message)s"

    def __init__(self, include_context: bool = True):
        """
        Initialize text formatter.

        Args:
            include_context: Include request context in output
        """
        self.include_context = include_context
        super().__init__(self.DEFAULT_FORMAT)

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as text."""
        context = get_request_context()

        if self.include_context and context.get("request_id"):
            # Add context to record
            record.request_id = context["request_id"]
            self._style._fmt = self.CONTEXT_FORMAT
        else:
            record.request_id = "-"
            self._style._fmt = self.DEFAULT_FORMAT

        return super().format(record)


def setup_logging(
    level: str = "INFO",
    log_format: str = "json",
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    service_name: str = "ocr-microservice"
) -> None:
    """
    Configure application logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format type ("json" or "text")
        log_file: Optional log file path
        max_bytes: Max log file size before rotation
        backup_count: Number of backup files to keep
        service_name: Service name for log context
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create formatter
    if log_format.lower() == "json":
        formatter = JSONFormatter(
            include_location=level.upper() == "DEBUG",
            extra_fields={"service": service_name}
        )
    else:
        formatter = TextFormatter(include_context=True)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (if configured)
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Configure third-party loggers
    _configure_third_party_loggers(level)

    logging.info(f"Logging configured: level={level}, format={log_format}")


def _configure_third_party_loggers(level: str) -> None:
    """Configure third-party library loggers to reduce noise."""
    # Set higher levels for noisy libraries
    noisy_loggers = [
        "urllib3",
        "requests",
        "werkzeug",
        "flask",
        "PIL",
        "paddle",
        "paddleocr",
        "ppocr",
        "easyocr",
        "matplotlib",
        "fontTools",
    ]

    min_level = logging.WARNING if level.upper() in ("INFO", "DEBUG") else logging.ERROR

    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(min_level)


class LogContext:
    """
    Context manager for request logging context.

    Usage:
        with LogContext(request_id="abc123", client_id="client_1"):
            logger.info("Processing request")
    """

    def __init__(
        self,
        request_id: Optional[str] = None,
        client_id: Optional[str] = None,
        **extra
    ):
        """
        Initialize log context.

        Args:
            request_id: Request identifier
            client_id: Client identifier
            **extra: Additional context fields
        """
        self.request_id = request_id
        self.client_id = client_id
        self.extra = extra
        self._previous_context = None

    def __enter__(self):
        """Enter context."""
        self._previous_context = get_request_context()
        set_request_context(
            request_id=self.request_id,
            client_id=self.client_id,
            **self.extra
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and restore previous."""
        if self._previous_context:
            set_request_context(**self._previous_context)
        else:
            clear_request_context()
        return False


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    **extra
) -> None:
    """
    Log message with additional context.

    Args:
        logger: Logger instance
        level: Log level
        message: Log message
        **extra: Additional context fields
    """
    record = logger.makeRecord(
        logger.name,
        level,
        "",
        0,
        message,
        (),
        None
    )
    record.extra_data = extra
    logger.handle(record)


# Convenience functions
def log_request_start(
    logger: logging.Logger,
    request_id: str,
    method: str,
    path: str,
    client_id: Optional[str] = None
) -> None:
    """Log request start."""
    set_request_context(request_id=request_id, client_id=client_id)
    logger.info(f"Request started: {method} {path}")


def log_request_end(
    logger: logging.Logger,
    status_code: int,
    duration_ms: float
) -> None:
    """Log request completion."""
    logger.info(
        f"Request completed: status={status_code}, duration={duration_ms:.0f}ms"
    )
    clear_request_context()


# Export
__all__ = [
    "JSONFormatter",
    "TextFormatter",
    "LogContext",
    "setup_logging",
    "set_request_context",
    "clear_request_context",
    "get_request_context",
    "log_with_context",
    "log_request_start",
    "log_request_end"
]
