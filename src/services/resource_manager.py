"""
ERP Arabic OCR Microservice - Resource Manager
===============================================
Manages system resources and concurrent processing limits.
"""

import os
import time
import threading
import logging
from typing import Dict, Any, Optional, Generator
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import contextmanager

import psutil

logger = logging.getLogger(__name__)


@dataclass
class ResourceStats:
    """Resource usage statistics."""
    total_acquired: int = 0
    total_released: int = 0
    total_rejected: int = 0
    total_timeouts: int = 0
    peak_concurrent: int = 0
    current_concurrent: int = 0
    avg_hold_time_ms: float = 0.0
    _hold_times: list = field(default_factory=list)

    def record_hold_time(self, duration_ms: float) -> None:
        """Record processing slot hold time."""
        self._hold_times.append(duration_ms)
        # Keep last 1000 entries
        if len(self._hold_times) > 1000:
            self._hold_times = self._hold_times[-1000:]
        self.avg_hold_time_ms = sum(self._hold_times) / len(self._hold_times)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_acquired": self.total_acquired,
            "total_released": self.total_released,
            "total_rejected": self.total_rejected,
            "total_timeouts": self.total_timeouts,
            "peak_concurrent": self.peak_concurrent,
            "current_concurrent": self.current_concurrent,
            "avg_hold_time_ms": round(self.avg_hold_time_ms, 2)
        }


class ResourceManager:
    """
    Manages system resources for OCR processing.

    Features:
    - Concurrent request limiting via semaphore
    - CPU/memory usage monitoring
    - Automatic backpressure when resources low
    - Processing slot acquisition with timeout
    - Resource usage statistics
    """

    def __init__(
        self,
        max_concurrent_requests: int = 10,
        max_memory_percent: int = 80,
        max_cpu_percent: int = 90,
        check_interval_seconds: float = 1.0
    ):
        """
        Initialize resource manager.

        Args:
            max_concurrent_requests: Maximum concurrent OCR operations
            max_memory_percent: Maximum memory usage percentage
            max_cpu_percent: Maximum CPU usage percentage
            check_interval_seconds: Interval for resource checks
        """
        self.max_concurrent = max_concurrent_requests
        self.max_memory_percent = max_memory_percent
        self.max_cpu_percent = max_cpu_percent
        self.check_interval = check_interval_seconds

        # Semaphore for limiting concurrent requests
        self._semaphore = threading.Semaphore(max_concurrent_requests)
        self._lock = threading.Lock()

        # Statistics
        self._stats = ResourceStats()

        # Slot tracking
        self._active_slots: Dict[int, float] = {}  # thread_id -> start_time
        self._slot_counter = 0

        logger.info(
            f"ResourceManager initialized: max_concurrent={max_concurrent_requests}, "
            f"max_memory={max_memory_percent}%, max_cpu={max_cpu_percent}%"
        )

    def check_resources(self) -> tuple[bool, Dict[str, Any]]:
        """
        Check if system resources are available.

        Returns:
            Tuple of (resources_available, status_dict)
        """
        try:
            # Get current usage
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=0.1)

            status = {
                "memory_percent": memory.percent,
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "cpu_percent": cpu_percent,
                "concurrent_requests": self._stats.current_concurrent,
                "max_concurrent": self.max_concurrent
            }

            # Check limits
            memory_ok = memory.percent < self.max_memory_percent
            cpu_ok = cpu_percent < self.max_cpu_percent
            slots_ok = self._stats.current_concurrent < self.max_concurrent

            available = memory_ok and cpu_ok and slots_ok

            if not available:
                reasons = []
                if not memory_ok:
                    reasons.append(f"memory={memory.percent}% (max {self.max_memory_percent}%)")
                if not cpu_ok:
                    reasons.append(f"cpu={cpu_percent}% (max {self.max_cpu_percent}%)")
                if not slots_ok:
                    reasons.append(f"slots={self._stats.current_concurrent} (max {self.max_concurrent})")
                status["rejection_reasons"] = reasons

            return available, status

        except Exception as e:
            logger.error(f"Resource check failed: {e}")
            return True, {"error": str(e)}

    def acquire(self, timeout: float = 30.0, check_resources: bool = True) -> bool:
        """
        Acquire a processing slot.

        Args:
            timeout: Maximum time to wait for slot (seconds)
            check_resources: Whether to check system resources first

        Returns:
            True if slot acquired, False otherwise
        """
        # Check resources first
        if check_resources:
            available, status = self.check_resources()
            if not available:
                with self._lock:
                    self._stats.total_rejected += 1
                logger.warning(f"Resource acquisition rejected: {status.get('rejection_reasons')}")
                return False

        # Try to acquire semaphore
        acquired = self._semaphore.acquire(timeout=timeout)

        with self._lock:
            if acquired:
                self._stats.total_acquired += 1
                self._stats.current_concurrent += 1

                if self._stats.current_concurrent > self._stats.peak_concurrent:
                    self._stats.peak_concurrent = self._stats.current_concurrent

                # Track slot
                thread_id = threading.current_thread().ident
                self._active_slots[thread_id] = time.time()

                logger.debug(f"Slot acquired: concurrent={self._stats.current_concurrent}")
            else:
                self._stats.total_timeouts += 1
                logger.warning(f"Slot acquisition timed out after {timeout}s")

        return acquired

    def release(self) -> None:
        """Release a processing slot."""
        thread_id = threading.current_thread().ident

        with self._lock:
            # Record hold time
            if thread_id in self._active_slots:
                start_time = self._active_slots.pop(thread_id)
                hold_time_ms = (time.time() - start_time) * 1000
                self._stats.record_hold_time(hold_time_ms)

            self._stats.total_released += 1
            self._stats.current_concurrent = max(0, self._stats.current_concurrent - 1)

        self._semaphore.release()
        logger.debug(f"Slot released: concurrent={self._stats.current_concurrent}")

    @contextmanager
    def processing_slot(
        self,
        timeout: float = 30.0,
        check_resources: bool = True
    ) -> Generator[bool, None, None]:
        """
        Context manager for acquiring and releasing processing slots.

        Args:
            timeout: Maximum time to wait for slot
            check_resources: Whether to check system resources

        Yields:
            True if slot acquired, False otherwise

        Usage:
            with resource_manager.processing_slot() as acquired:
                if acquired:
                    # Do OCR processing
                else:
                    # Handle rejection
        """
        acquired = self.acquire(timeout=timeout, check_resources=check_resources)

        try:
            yield acquired
        finally:
            if acquired:
                self.release()

    def get_status(self) -> Dict[str, Any]:
        """
        Get current resource status.

        Returns:
            Resource status dictionary
        """
        try:
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=0.1)

            # Disk usage for temp directory
            try:
                from config.settings import get_settings
                settings = get_settings()
                temp_dir = settings.resources.temp_dir
            except:
                temp_dir = "/tmp"

            try:
                disk = psutil.disk_usage(temp_dir)
                disk_info = {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "percent_used": disk.percent
                }
            except:
                disk_info = {"error": "unavailable"}

            return {
                "system": {
                    "cpu_percent": cpu_percent,
                    "cpu_count": psutil.cpu_count(),
                    "memory_percent": memory.percent,
                    "memory_total_gb": round(memory.total / (1024**3), 2),
                    "memory_available_gb": round(memory.available / (1024**3), 2),
                    "disk": disk_info
                },
                "limits": {
                    "max_concurrent_requests": self.max_concurrent,
                    "max_memory_percent": self.max_memory_percent,
                    "max_cpu_percent": self.max_cpu_percent
                },
                "current": {
                    "concurrent_requests": self._stats.current_concurrent,
                    "available_slots": self.max_concurrent - self._stats.current_concurrent
                },
                "stats": self._stats.to_dict()
            }

        except Exception as e:
            logger.error(f"Failed to get resource status: {e}")
            return {"error": str(e)}

    def wait_for_resources(
        self,
        timeout: float = 60.0,
        poll_interval: float = 1.0
    ) -> bool:
        """
        Wait for resources to become available.

        Args:
            timeout: Maximum time to wait
            poll_interval: Time between checks

        Returns:
            True if resources available, False if timeout
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            available, _ = self.check_resources()
            if available:
                return True
            time.sleep(poll_interval)

        return False

    def health_check(self) -> Dict[str, Any]:
        """
        Health check for resource manager.

        Returns:
            Health status dictionary
        """
        available, status = self.check_resources()

        return {
            "status": "healthy" if available else "degraded",
            "resources_available": available,
            "current_load": {
                "concurrent": self._stats.current_concurrent,
                "max_concurrent": self.max_concurrent,
                "utilization": f"{(self._stats.current_concurrent / self.max_concurrent) * 100:.1f}%"
            },
            "system": status
        }


# Singleton instance
_resource_manager: Optional[ResourceManager] = None


def get_resource_manager() -> ResourceManager:
    """Get global resource manager instance."""
    global _resource_manager
    if _resource_manager is None:
        try:
            from config.settings import get_settings
            settings = get_settings()
            _resource_manager = ResourceManager(
                max_concurrent_requests=settings.resources.max_concurrent_requests,
                max_memory_percent=settings.resources.max_memory_percent,
                max_cpu_percent=settings.resources.max_cpu_percent
            )
        except:
            _resource_manager = ResourceManager()
    return _resource_manager


# Export
__all__ = [
    "ResourceManager",
    "ResourceStats",
    "get_resource_manager"
]
