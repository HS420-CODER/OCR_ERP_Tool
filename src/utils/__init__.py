"""
Utility functions and helpers.

Modules:
- file_utils: File type detection, path validation
- image_utils: Image preprocessing, encoding
- logging_config: Structured JSON logging
- metrics: Prometheus metrics
"""

from .logging_config import (
    JSONFormatter,
    TextFormatter,
    LogContext,
    setup_logging,
    set_request_context,
    clear_request_context,
    get_request_context,
    log_with_context,
    log_request_start,
    log_request_end
)

from .metrics import (
    Counter,
    Gauge,
    Histogram,
    MetricsRegistry,
    get_metrics_registry,
    get_metrics,
    get_counter,
    get_gauge,
    get_histogram,
    track_request,
    record_document_processed,
    record_cache_operation,
    set_engine_availability,
    set_queue_size
)

__all__ = [
    # Logging
    "JSONFormatter",
    "TextFormatter",
    "LogContext",
    "setup_logging",
    "set_request_context",
    "clear_request_context",
    "get_request_context",
    "log_with_context",
    "log_request_start",
    "log_request_end",
    # Metrics
    "Counter",
    "Gauge",
    "Histogram",
    "MetricsRegistry",
    "get_metrics_registry",
    "get_metrics",
    "get_counter",
    "get_gauge",
    "get_histogram",
    "track_request",
    "record_document_processed",
    "record_cache_operation",
    "set_engine_availability",
    "set_queue_size"
]
