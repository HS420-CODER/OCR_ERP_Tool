"""
ERP Arabic OCR Microservice - Prometheus Metrics
=================================================
Exposes application metrics in Prometheus format.
"""

import time
import threading
import functools
import logging
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
from enum import Enum

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Prometheus metric types."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricValue:
    """Container for metric values with labels."""
    value: float = 0.0
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: Optional[datetime] = None

    def label_key(self) -> str:
        """Generate label key for grouping."""
        if not self.labels:
            return ""
        return ",".join(f'{k}="{v}"' for k, v in sorted(self.labels.items()))


class Counter:
    """
    Prometheus-style counter metric.

    Counters only increase (or reset to zero on restart).
    """

    def __init__(self, name: str, description: str, labels: List[str] = None):
        """
        Initialize counter.

        Args:
            name: Metric name (e.g., 'ocr_requests_total')
            description: Human-readable description
            labels: List of label names
        """
        self.name = name
        self.description = description
        self.label_names = labels or []
        self._values: Dict[str, float] = defaultdict(float)
        self._lock = threading.Lock()

    def inc(self, value: float = 1.0, **labels) -> None:
        """
        Increment counter.

        Args:
            value: Amount to increment (default 1.0)
            **labels: Label values
        """
        key = self._make_key(labels)
        with self._lock:
            self._values[key] += value

    def _make_key(self, labels: Dict[str, str]) -> str:
        """Create key from labels."""
        if not labels:
            return ""
        return ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))

    def get_values(self) -> Dict[str, float]:
        """Get all counter values."""
        with self._lock:
            return dict(self._values)

    def to_prometheus(self) -> str:
        """Format as Prometheus metric."""
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} counter"
        ]
        with self._lock:
            if not self._values:
                lines.append(f"{self.name} 0")
            else:
                for key, value in self._values.items():
                    if key:
                        lines.append(f"{self.name}{{{key}}} {value}")
                    else:
                        lines.append(f"{self.name} {value}")
        return "\n".join(lines)


class Gauge:
    """
    Prometheus-style gauge metric.

    Gauges can increase or decrease.
    """

    def __init__(self, name: str, description: str, labels: List[str] = None):
        """
        Initialize gauge.

        Args:
            name: Metric name
            description: Human-readable description
            labels: List of label names
        """
        self.name = name
        self.description = description
        self.label_names = labels or []
        self._values: Dict[str, float] = defaultdict(float)
        self._lock = threading.Lock()

    def set(self, value: float, **labels) -> None:
        """Set gauge value."""
        key = self._make_key(labels)
        with self._lock:
            self._values[key] = value

    def inc(self, value: float = 1.0, **labels) -> None:
        """Increment gauge."""
        key = self._make_key(labels)
        with self._lock:
            self._values[key] += value

    def dec(self, value: float = 1.0, **labels) -> None:
        """Decrement gauge."""
        key = self._make_key(labels)
        with self._lock:
            self._values[key] -= value

    def _make_key(self, labels: Dict[str, str]) -> str:
        """Create key from labels."""
        if not labels:
            return ""
        return ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))

    def get_values(self) -> Dict[str, float]:
        """Get all gauge values."""
        with self._lock:
            return dict(self._values)

    def to_prometheus(self) -> str:
        """Format as Prometheus metric."""
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} gauge"
        ]
        with self._lock:
            if not self._values:
                lines.append(f"{self.name} 0")
            else:
                for key, value in self._values.items():
                    if key:
                        lines.append(f"{self.name}{{{key}}} {value}")
                    else:
                        lines.append(f"{self.name} {value}")
        return "\n".join(lines)


class Histogram:
    """
    Prometheus-style histogram metric.

    Tracks distribution of values across buckets.
    """

    # Default buckets for latency (in seconds)
    DEFAULT_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5,
                       0.75, 1.0, 2.5, 5.0, 7.5, 10.0, float("inf"))

    def __init__(
        self,
        name: str,
        description: str,
        labels: List[str] = None,
        buckets: tuple = None
    ):
        """
        Initialize histogram.

        Args:
            name: Metric name
            description: Human-readable description
            labels: List of label names
            buckets: Bucket boundaries
        """
        self.name = name
        self.description = description
        self.label_names = labels or []
        self.buckets = buckets or self.DEFAULT_BUCKETS
        self._lock = threading.Lock()

        # Store per-label-set: {label_key: {bucket: count, _sum: total, _count: n}}
        self._data: Dict[str, Dict] = defaultdict(
            lambda: {b: 0 for b in self.buckets} | {"_sum": 0.0, "_count": 0}
        )

    def observe(self, value: float, **labels) -> None:
        """
        Record a value observation.

        Args:
            value: Observed value
            **labels: Label values
        """
        key = self._make_key(labels)
        with self._lock:
            data = self._data[key]
            data["_sum"] += value
            data["_count"] += 1
            for bucket in self.buckets:
                if value <= bucket:
                    data[bucket] += 1

    def _make_key(self, labels: Dict[str, str]) -> str:
        """Create key from labels."""
        if not labels:
            return ""
        return ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))

    def get_data(self) -> Dict[str, Dict]:
        """Get histogram data."""
        with self._lock:
            return dict(self._data)

    def to_prometheus(self) -> str:
        """Format as Prometheus metric."""
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} histogram"
        ]

        with self._lock:
            for label_key, data in self._data.items():
                label_prefix = f"{{{label_key}," if label_key else "{"
                label_suffix = "}" if label_key else ""

                # Buckets (cumulative)
                cumulative = 0
                for bucket in self.buckets:
                    if bucket == float("inf"):
                        bucket_str = "+Inf"
                    else:
                        bucket_str = str(bucket)

                    cumulative += data.get(bucket, 0)

                    if label_key:
                        lines.append(
                            f'{self.name}_bucket{{{label_key},le="{bucket_str}"}} {cumulative}'
                        )
                    else:
                        lines.append(
                            f'{self.name}_bucket{{le="{bucket_str}"}} {cumulative}'
                        )

                # Sum and count
                if label_key:
                    lines.append(f"{self.name}_sum{{{label_key}}} {data['_sum']}")
                    lines.append(f"{self.name}_count{{{label_key}}} {data['_count']}")
                else:
                    lines.append(f"{self.name}_sum {data['_sum']}")
                    lines.append(f"{self.name}_count {data['_count']}")

        return "\n".join(lines)

    def time(self, **labels):
        """
        Context manager for timing operations.

        Usage:
            with histogram.time(engine="paddle"):
                # do work
        """
        return _HistogramTimer(self, labels)


class _HistogramTimer:
    """Timer context manager for histogram observations."""

    def __init__(self, histogram: Histogram, labels: Dict[str, str]):
        self.histogram = histogram
        self.labels = labels
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        self.histogram.observe(duration, **self.labels)
        return False


class MetricsRegistry:
    """
    Registry for all application metrics.

    Singleton pattern for global access.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._metrics: Dict[str, Any] = {}
        self._start_time = datetime.utcnow()
        self._initialized = True

        # Initialize default OCR metrics
        self._init_default_metrics()

    def _init_default_metrics(self) -> None:
        """Initialize default OCR-related metrics."""
        # Counters
        self.register(Counter(
            "ocr_requests_total",
            "Total number of OCR requests",
            labels=["endpoint", "status"]
        ))

        self.register(Counter(
            "ocr_documents_processed_total",
            "Total number of documents processed",
            labels=["engine", "document_type"]
        ))

        self.register(Counter(
            "ocr_errors_total",
            "Total number of OCR errors",
            labels=["error_type", "engine"]
        ))

        self.register(Counter(
            "ocr_cache_operations_total",
            "Total cache operations",
            labels=["operation", "result"]
        ))

        # Gauges
        self.register(Gauge(
            "ocr_active_requests",
            "Number of currently active OCR requests",
            labels=["endpoint"]
        ))

        self.register(Gauge(
            "ocr_engine_available",
            "OCR engine availability (1=available, 0=unavailable)",
            labels=["engine"]
        ))

        self.register(Gauge(
            "ocr_queue_size",
            "Number of requests waiting in queue",
            labels=[]
        ))

        # Histograms
        self.register(Histogram(
            "ocr_request_latency_seconds",
            "OCR request latency in seconds",
            labels=["endpoint", "engine"],
            buckets=(0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, float("inf"))
        ))

        self.register(Histogram(
            "ocr_confidence_score",
            "OCR confidence scores",
            labels=["engine"],
            buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0, float("inf"))
        ))

        self.register(Histogram(
            "ocr_document_size_bytes",
            "Document size in bytes",
            labels=["document_type"],
            buckets=(1024, 10240, 102400, 1048576, 10485760, 52428800, float("inf"))
        ))

        self.register(Histogram(
            "ocr_text_length_chars",
            "Extracted text length in characters",
            labels=["engine"],
            buckets=(10, 100, 500, 1000, 5000, 10000, 50000, float("inf"))
        ))

        logger.info("Default OCR metrics initialized")

    def register(self, metric: Any) -> None:
        """Register a metric."""
        self._metrics[metric.name] = metric

    def get(self, name: str) -> Optional[Any]:
        """Get metric by name."""
        return self._metrics.get(name)

    def get_all(self) -> Dict[str, Any]:
        """Get all metrics."""
        return dict(self._metrics)

    def to_prometheus(self) -> str:
        """
        Generate Prometheus-format output for all metrics.

        Returns:
            Prometheus text format string
        """
        lines = []

        # Add process info
        lines.append(f"# HELP process_start_time_seconds Start time of the process")
        lines.append(f"# TYPE process_start_time_seconds gauge")
        lines.append(f"process_start_time_seconds {self._start_time.timestamp()}")
        lines.append("")

        # Add uptime
        uptime = (datetime.utcnow() - self._start_time).total_seconds()
        lines.append(f"# HELP process_uptime_seconds Process uptime in seconds")
        lines.append(f"# TYPE process_uptime_seconds gauge")
        lines.append(f"process_uptime_seconds {uptime}")
        lines.append("")

        # Add all registered metrics
        for name, metric in sorted(self._metrics.items()):
            lines.append(metric.to_prometheus())
            lines.append("")

        return "\n".join(lines)

    def reset(self) -> None:
        """Reset all metrics (for testing)."""
        self._metrics.clear()
        self._init_default_metrics()


# Global registry instance
_registry: Optional[MetricsRegistry] = None


def get_metrics_registry() -> MetricsRegistry:
    """Get global metrics registry."""
    global _registry
    if _registry is None:
        _registry = MetricsRegistry()
    return _registry


def get_metrics() -> str:
    """
    Get Prometheus-format metrics output.

    Returns:
        Prometheus text format string
    """
    return get_metrics_registry().to_prometheus()


# Convenience accessors for common metrics
def get_counter(name: str) -> Optional[Counter]:
    """Get counter by name."""
    return get_metrics_registry().get(name)


def get_gauge(name: str) -> Optional[Gauge]:
    """Get gauge by name."""
    return get_metrics_registry().get(name)


def get_histogram(name: str) -> Optional[Histogram]:
    """Get histogram by name."""
    return get_metrics_registry().get(name)


def track_request(endpoint: str, engine: str = "unknown") -> Callable:
    """
    Decorator for tracking request metrics.

    Args:
        endpoint: API endpoint name
        engine: OCR engine name

    Returns:
        Decorator function

    Usage:
        @track_request("invoice", "paddle")
        def process_invoice(image):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            registry = get_metrics_registry()

            # Get metrics
            requests_counter = registry.get("ocr_requests_total")
            active_gauge = registry.get("ocr_active_requests")
            latency_hist = registry.get("ocr_request_latency_seconds")
            errors_counter = registry.get("ocr_errors_total")

            # Increment active requests
            if active_gauge:
                active_gauge.inc(endpoint=endpoint)

            start_time = time.time()
            status = "success"

            try:
                result = func(*args, **kwargs)
                return result

            except Exception as e:
                status = "error"
                if errors_counter:
                    error_type = type(e).__name__
                    errors_counter.inc(error_type=error_type, engine=engine)
                raise

            finally:
                # Record latency
                duration = time.time() - start_time
                if latency_hist:
                    latency_hist.observe(duration, endpoint=endpoint, engine=engine)

                # Decrement active requests
                if active_gauge:
                    active_gauge.dec(endpoint=endpoint)

                # Increment request counter
                if requests_counter:
                    requests_counter.inc(endpoint=endpoint, status=status)

        return wrapper
    return decorator


def record_document_processed(
    engine: str,
    document_type: str,
    confidence: float,
    text_length: int,
    size_bytes: int
) -> None:
    """
    Record document processing metrics.

    Args:
        engine: OCR engine used
        document_type: Type of document (invoice, document)
        confidence: OCR confidence score
        text_length: Extracted text length
        size_bytes: Document size in bytes
    """
    registry = get_metrics_registry()

    # Documents processed
    docs_counter = registry.get("ocr_documents_processed_total")
    if docs_counter:
        docs_counter.inc(engine=engine, document_type=document_type)

    # Confidence score
    confidence_hist = registry.get("ocr_confidence_score")
    if confidence_hist:
        confidence_hist.observe(confidence, engine=engine)

    # Text length
    text_hist = registry.get("ocr_text_length_chars")
    if text_hist:
        text_hist.observe(text_length, engine=engine)

    # Document size
    size_hist = registry.get("ocr_document_size_bytes")
    if size_hist:
        size_hist.observe(size_bytes, document_type=document_type)


def record_cache_operation(operation: str, hit: bool) -> None:
    """
    Record cache operation.

    Args:
        operation: Operation type (get, set, invalidate)
        hit: Whether operation was successful/hit
    """
    cache_counter = get_metrics_registry().get("ocr_cache_operations_total")
    if cache_counter:
        result = "hit" if hit else "miss"
        cache_counter.inc(operation=operation, result=result)


def set_engine_availability(engine: str, available: bool) -> None:
    """
    Set engine availability.

    Args:
        engine: Engine name
        available: Whether engine is available
    """
    gauge = get_metrics_registry().get("ocr_engine_available")
    if gauge:
        gauge.set(1.0 if available else 0.0, engine=engine)


def set_queue_size(size: int) -> None:
    """
    Set queue size.

    Args:
        size: Number of requests in queue
    """
    gauge = get_metrics_registry().get("ocr_queue_size")
    if gauge:
        gauge.set(float(size))


# Export
__all__ = [
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
