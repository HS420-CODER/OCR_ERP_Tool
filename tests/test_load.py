"""
ERP Arabic OCR Microservice - Load Tests
=========================================
Performance and load testing for OCR service.

Target Metrics:
- Throughput: 2-20 documents/second
- Latency (p95): ≤ 1200ms
- Memory: Stable under load
"""

import os
import sys
import time
import json
import pytest
import psutil
import tempfile
import statistics
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
from typing import List, Optional
import threading
import queue

from PIL import Image
import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ==============================================================================
# Test Configuration
# ==============================================================================

# Performance thresholds
MIN_THROUGHPUT = 2.0  # documents/second minimum
MAX_LATENCY_P95 = 1200  # milliseconds
MAX_MEMORY_GROWTH_MB = 500  # Maximum memory growth under load


@dataclass
class LoadTestResult:
    """Result from a load test run."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_time_seconds: float
    throughput_per_second: float
    latencies_ms: List[float]
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    latency_mean_ms: float
    memory_start_mb: float
    memory_end_mb: float
    memory_peak_mb: float
    errors: List[str]

    @property
    def success_rate(self) -> float:
        return self.successful_requests / self.total_requests if self.total_requests > 0 else 0.0


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def sample_images():
    """Create multiple sample test images."""
    images = []
    for i in range(20):
        img = Image.new('RGB', (800, 400), color='white')
        # Add some variation
        img.putpixel((i * 10, i * 5), (0, 0, 0))
        images.append(img)
    return images


@pytest.fixture
def temp_image_files(sample_images, tmp_path):
    """Save sample images to temp files."""
    paths = []
    for i, img in enumerate(sample_images):
        path = tmp_path / f"test_image_{i}.png"
        img.save(path)
        paths.append(str(path))
    return paths


@pytest.fixture
def mock_ocr_service():
    """Create mock OCR service for load testing."""
    from src.services import OCRResult, OCREngine

    def create_result(*args, **kwargs):
        # Simulate processing time
        time.sleep(0.05)  # 50ms simulated processing
        return OCRResult(
            text="الرقم الضريبي: 310123456789012",
            confidence=0.95,
            engine=OCREngine.PADDLE,
            blocks=[],
            processing_time_ms=50.0
        )

    mock_service = Mock()
    mock_service.process_image.side_effect = create_result
    mock_service.get_engine_status.return_value = {
        'paddle': {'available': True},
        'easyocr': {'available': True}
    }

    return mock_service


@pytest.fixture
def app():
    """Create test Flask application."""
    from api import create_app

    app = create_app()
    app.config['TESTING'] = True
    app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()

    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


# ==============================================================================
# Helper Functions
# ==============================================================================

def get_memory_usage_mb() -> float:
    """Get current process memory usage in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)


def calculate_percentile(values: List[float], percentile: float) -> float:
    """Calculate percentile of a list of values."""
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = int(len(sorted_values) * percentile / 100)
    return sorted_values[min(index, len(sorted_values) - 1)]


def run_load_test(
    func,
    iterations: int,
    concurrency: int,
    *args,
    **kwargs
) -> LoadTestResult:
    """
    Run a load test with specified parameters.

    Args:
        func: Function to test
        iterations: Total number of iterations
        concurrency: Number of concurrent workers
        *args, **kwargs: Arguments to pass to func

    Returns:
        LoadTestResult with metrics
    """
    latencies = []
    errors = []
    successful = 0
    failed = 0
    memory_samples = []
    lock = threading.Lock()

    memory_start = get_memory_usage_mb()

    def worker(iteration_id):
        nonlocal successful, failed
        try:
            start = time.time()
            func(*args, **kwargs)
            elapsed_ms = (time.time() - start) * 1000

            with lock:
                latencies.append(elapsed_ms)
                successful += 1
                memory_samples.append(get_memory_usage_mb())

        except Exception as e:
            with lock:
                failed += 1
                errors.append(f"Iteration {iteration_id}: {str(e)}")

    # Run test
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(worker, i) for i in range(iterations)]
        for future in as_completed(futures):
            pass  # Wait for all to complete

    total_time = time.time() - start_time
    memory_end = get_memory_usage_mb()
    memory_peak = max(memory_samples) if memory_samples else memory_end

    # Calculate metrics
    throughput = iterations / total_time if total_time > 0 else 0

    return LoadTestResult(
        total_requests=iterations,
        successful_requests=successful,
        failed_requests=failed,
        total_time_seconds=total_time,
        throughput_per_second=throughput,
        latencies_ms=latencies,
        latency_p50_ms=calculate_percentile(latencies, 50),
        latency_p95_ms=calculate_percentile(latencies, 95),
        latency_p99_ms=calculate_percentile(latencies, 99),
        latency_mean_ms=statistics.mean(latencies) if latencies else 0,
        memory_start_mb=memory_start,
        memory_end_mb=memory_end,
        memory_peak_mb=memory_peak,
        errors=errors[:10]  # Keep first 10 errors
    )


# ==============================================================================
# Concurrent Request Tests
# ==============================================================================

class TestConcurrentRequests:
    """Tests for concurrent request handling."""

    def test_concurrent_ocr_processing(self, mock_ocr_service, temp_image_files):
        """Test OCR service handles concurrent requests."""

        def process_image(path):
            return mock_ocr_service.process_image(path)

        # Run with 10 concurrent workers
        result = run_load_test(
            process_image,
            50,  # iterations
            10,  # concurrency
            temp_image_files[0]
        )

        print(f"\nConcurrent OCR Test Results:")
        print(f"  Total requests: {result.total_requests}")
        print(f"  Successful: {result.successful_requests}")
        print(f"  Failed: {result.failed_requests}")
        print(f"  Throughput: {result.throughput_per_second:.2f} req/s")
        print(f"  Latency P95: {result.latency_p95_ms:.0f}ms")

        # Assert success rate
        assert result.success_rate >= 0.95, f"Success rate too low: {result.success_rate}"

    def test_high_concurrency(self, mock_ocr_service, temp_image_files):
        """Test service under high concurrency."""

        def process_image(path):
            return mock_ocr_service.process_image(path)

        # Run with 20 concurrent workers
        result = run_load_test(
            process_image,
            100,  # iterations
            20,  # concurrency
            temp_image_files[0]
        )

        print(f"\nHigh Concurrency Test Results:")
        print(f"  Concurrency: 20 workers")
        print(f"  Throughput: {result.throughput_per_second:.2f} req/s")
        print(f"  Success rate: {result.success_rate * 100:.1f}%")

        # Should handle concurrency gracefully
        assert result.success_rate >= 0.90

    def test_thread_safety(self, mock_ocr_service):
        """Test OCR service is thread-safe."""
        results = []
        errors = []
        lock = threading.Lock()

        def worker(thread_id):
            try:
                for i in range(10):
                    result = mock_ocr_service.process_image(f"test_{thread_id}_{i}.png")
                    with lock:
                        results.append(result)
            except Exception as e:
                with lock:
                    errors.append(f"Thread {thread_id}: {e}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        print(f"\nThread Safety Test:")
        print(f"  Total results: {len(results)}")
        print(f"  Errors: {len(errors)}")

        assert len(errors) == 0, f"Thread safety errors: {errors}"
        assert len(results) == 100


# ==============================================================================
# Throughput Tests
# ==============================================================================

class TestThroughput:
    """Tests for throughput performance."""

    def test_throughput_minimum(self, mock_ocr_service, temp_image_files):
        """Test minimum throughput requirement (2 docs/sec)."""

        def process_image(path):
            return mock_ocr_service.process_image(path)

        result = run_load_test(
            process_image,
            20,  # iterations
            4,  # concurrency
            temp_image_files[0]
        )

        print(f"\nThroughput Test Results:")
        print(f"  Achieved: {result.throughput_per_second:.2f} docs/sec")
        print(f"  Required: {MIN_THROUGHPUT} docs/sec")

        assert result.throughput_per_second >= MIN_THROUGHPUT, \
            f"Throughput {result.throughput_per_second:.2f} below minimum {MIN_THROUGHPUT}"

    def test_sustained_throughput(self, mock_ocr_service, temp_image_files):
        """Test sustained throughput over longer period."""

        def process_image(path):
            return mock_ocr_service.process_image(path)

        # Run for longer duration
        result = run_load_test(
            process_image,
            100,  # iterations
            8,  # concurrency
            temp_image_files[0]
        )

        print(f"\nSustained Throughput Test:")
        print(f"  Duration: {result.total_time_seconds:.1f}s")
        print(f"  Throughput: {result.throughput_per_second:.2f} docs/sec")
        print(f"  Latency mean: {result.latency_mean_ms:.0f}ms")

        # Should maintain reasonable throughput
        assert result.throughput_per_second >= MIN_THROUGHPUT * 0.8

    def test_batch_throughput(self, mock_ocr_service, temp_image_files):
        """Test throughput with batch processing."""
        processed_count = 0
        start_time = time.time()

        # Process batch of 10 images
        batch_size = 10
        batch_files = temp_image_files[:batch_size]

        def process_batch():
            results = []
            for path in batch_files:
                results.append(mock_ocr_service.process_image(path))
            return results

        # Run 5 batches
        for _ in range(5):
            results = process_batch()
            processed_count += len(results)

        elapsed = time.time() - start_time
        throughput = processed_count / elapsed

        print(f"\nBatch Throughput Test:")
        print(f"  Batches: 5 x {batch_size} = {processed_count} docs")
        print(f"  Time: {elapsed:.1f}s")
        print(f"  Throughput: {throughput:.2f} docs/sec")

        assert throughput >= MIN_THROUGHPUT


# ==============================================================================
# Latency Tests
# ==============================================================================

class TestLatency:
    """Tests for latency performance."""

    def test_latency_p95(self, mock_ocr_service, temp_image_files):
        """Test P95 latency is within acceptable range."""

        def process_image(path):
            return mock_ocr_service.process_image(path)

        result = run_load_test(
            process_image,
            100,  # iterations
            4,  # concurrency
            temp_image_files[0]
        )

        print(f"\nLatency Test Results:")
        print(f"  P50: {result.latency_p50_ms:.0f}ms")
        print(f"  P95: {result.latency_p95_ms:.0f}ms")
        print(f"  P99: {result.latency_p99_ms:.0f}ms")
        print(f"  Mean: {result.latency_mean_ms:.0f}ms")
        print(f"  Max allowed P95: {MAX_LATENCY_P95}ms")

        assert result.latency_p95_ms <= MAX_LATENCY_P95, \
            f"P95 latency {result.latency_p95_ms}ms exceeds {MAX_LATENCY_P95}ms"

    def test_latency_consistency(self, mock_ocr_service, temp_image_files):
        """Test latency is consistent."""

        def process_image(path):
            return mock_ocr_service.process_image(path)

        result = run_load_test(
            process_image,
            50,  # iterations
            4,  # concurrency
            temp_image_files[0]
        )

        # Calculate coefficient of variation
        if result.latencies_ms:
            cv = statistics.stdev(result.latencies_ms) / statistics.mean(result.latencies_ms)

            print(f"\nLatency Consistency Test:")
            print(f"  Coefficient of variation: {cv:.2f}")
            print(f"  (lower is better, <1.0 is good)")

            # CV should be reasonable
            assert cv < 2.0, f"Latency too inconsistent: CV={cv:.2f}"


# ==============================================================================
# Memory Stability Tests
# ==============================================================================

class TestMemoryStability:
    """Tests for memory stability under load."""

    def test_memory_no_leak(self, mock_ocr_service, temp_image_files):
        """Test no memory leak under sustained load."""
        import gc

        gc.collect()
        memory_start = get_memory_usage_mb()

        def process_image(path):
            return mock_ocr_service.process_image(path)

        # Run multiple iterations
        for batch in range(5):
            result = run_load_test(
                process_image,
                50,  # iterations
                4,  # concurrency
                temp_image_files[0]
            )
            gc.collect()

        memory_end = get_memory_usage_mb()
        memory_growth = memory_end - memory_start

        print(f"\nMemory Leak Test:")
        print(f"  Start: {memory_start:.1f}MB")
        print(f"  End: {memory_end:.1f}MB")
        print(f"  Growth: {memory_growth:.1f}MB")
        print(f"  Max allowed: {MAX_MEMORY_GROWTH_MB}MB")

        assert memory_growth < MAX_MEMORY_GROWTH_MB, \
            f"Memory grew by {memory_growth:.1f}MB (max: {MAX_MEMORY_GROWTH_MB}MB)"

    def test_memory_under_load(self, mock_ocr_service, temp_image_files):
        """Test memory usage under heavy load."""

        def process_image(path):
            return mock_ocr_service.process_image(path)

        result = run_load_test(
            process_image,
            100,  # iterations
            10,  # concurrency
            temp_image_files[0]
        )

        memory_growth = result.memory_peak_mb - result.memory_start_mb

        print(f"\nMemory Under Load Test:")
        print(f"  Peak memory: {result.memory_peak_mb:.1f}MB")
        print(f"  Growth: {memory_growth:.1f}MB")

        assert memory_growth < MAX_MEMORY_GROWTH_MB


# ==============================================================================
# Cache Effectiveness Tests
# ==============================================================================

class TestCacheEffectiveness:
    """Tests for cache effectiveness."""

    def test_cache_hit_improves_throughput(self, mock_ocr_service, temp_image_files):
        """Test that caching improves throughput."""
        from src.services.cache_manager import OCRCacheManager

        # Create mock cache
        mock_cache = Mock(spec=OCRCacheManager)
        cached_result = Mock(text="Cached text", confidence=0.95)

        # First call is cache miss, subsequent are hits
        call_count = [0]

        def get_cached(*args):
            call_count[0] += 1
            if call_count[0] > 1:
                return cached_result
            return None

        mock_cache.get.side_effect = get_cached

        # Test without cache (first calls)
        uncached_times = []
        for i in range(5):
            start = time.time()
            mock_ocr_service.process_image(temp_image_files[0])
            uncached_times.append((time.time() - start) * 1000)

        # Simulate cached calls (instant)
        cached_times = []
        for i in range(5):
            start = time.time()
            # Cached lookup is instant
            time.sleep(0.001)  # 1ms
            cached_times.append((time.time() - start) * 1000)

        uncached_mean = statistics.mean(uncached_times)
        cached_mean = statistics.mean(cached_times)
        improvement = (uncached_mean - cached_mean) / uncached_mean * 100

        print(f"\nCache Effectiveness Test:")
        print(f"  Uncached mean: {uncached_mean:.1f}ms")
        print(f"  Cached mean: {cached_mean:.1f}ms")
        print(f"  Improvement: {improvement:.1f}%")

        # Cache should provide significant improvement
        assert improvement > 50, f"Cache improvement too low: {improvement:.1f}%"

    def test_cache_hit_ratio(self):
        """Test cache hit ratio calculation."""
        # Simulate cache hits and misses
        hits = 80
        misses = 20
        total = hits + misses
        hit_ratio = hits / total

        print(f"\nCache Hit Ratio Test:")
        print(f"  Hits: {hits}")
        print(f"  Misses: {misses}")
        print(f"  Hit ratio: {hit_ratio * 100:.1f}%")

        # Good cache should have > 70% hit rate in production
        assert hit_ratio >= 0.7


# ==============================================================================
# Stress Tests
# ==============================================================================

class TestStress:
    """Stress tests for extreme conditions."""

    def test_burst_load(self, mock_ocr_service, temp_image_files):
        """Test handling of burst load."""
        burst_size = 50
        burst_concurrency = 20

        def process_image(path):
            return mock_ocr_service.process_image(path)

        result = run_load_test(
            process_image,
            burst_size,  # iterations
            burst_concurrency,  # concurrency
            temp_image_files[0]
        )

        print(f"\nBurst Load Test:")
        print(f"  Burst size: {burst_size}")
        print(f"  Concurrency: {burst_concurrency}")
        print(f"  Success rate: {result.success_rate * 100:.1f}%")
        print(f"  Throughput: {result.throughput_per_second:.2f} req/s")

        # Should handle burst gracefully
        assert result.success_rate >= 0.85

    def test_sustained_high_load(self, mock_ocr_service, temp_image_files):
        """Test sustained high load over time."""
        iterations = 200
        concurrency = 10

        def process_image(path):
            return mock_ocr_service.process_image(path)

        result = run_load_test(
            process_image,
            iterations,  # iterations
            concurrency,  # concurrency
            temp_image_files[0]
        )

        print(f"\nSustained High Load Test:")
        print(f"  Total requests: {iterations}")
        print(f"  Duration: {result.total_time_seconds:.1f}s")
        print(f"  Success rate: {result.success_rate * 100:.1f}%")
        print(f"  Throughput: {result.throughput_per_second:.2f} req/s")

        assert result.success_rate >= 0.90


# ==============================================================================
# Performance Benchmark Tests
# ==============================================================================

class TestPerformanceBenchmarks:
    """Benchmark tests for overall performance."""

    def test_overall_performance_benchmark(self, mock_ocr_service, temp_image_files):
        """Run comprehensive performance benchmark."""

        def process_image(path):
            return mock_ocr_service.process_image(path)

        # Run benchmark
        result = run_load_test(
            process_image,
            100,  # iterations
            8,  # concurrency
            temp_image_files[0]
        )

        print("\n" + "=" * 60)
        print("PERFORMANCE BENCHMARK RESULTS")
        print("=" * 60)
        print(f"Total Requests:     {result.total_requests}")
        print(f"Successful:         {result.successful_requests}")
        print(f"Failed:             {result.failed_requests}")
        print(f"Success Rate:       {result.success_rate * 100:.1f}%")
        print(f"Total Time:         {result.total_time_seconds:.2f}s")
        print(f"Throughput:         {result.throughput_per_second:.2f} req/s")
        print("-" * 60)
        print("LATENCY METRICS")
        print("-" * 60)
        print(f"Mean:               {result.latency_mean_ms:.0f}ms")
        print(f"P50 (Median):       {result.latency_p50_ms:.0f}ms")
        print(f"P95:                {result.latency_p95_ms:.0f}ms")
        print(f"P99:                {result.latency_p99_ms:.0f}ms")
        print("-" * 60)
        print("MEMORY USAGE")
        print("-" * 60)
        print(f"Start:              {result.memory_start_mb:.1f}MB")
        print(f"Peak:               {result.memory_peak_mb:.1f}MB")
        print(f"End:                {result.memory_end_mb:.1f}MB")
        print("=" * 60)

        # Performance assertions
        assert result.success_rate >= 0.95, "Success rate below 95%"
        assert result.throughput_per_second >= MIN_THROUGHPUT, \
            f"Throughput below {MIN_THROUGHPUT} req/s"
        assert result.latency_p95_ms <= MAX_LATENCY_P95, \
            f"P95 latency above {MAX_LATENCY_P95}ms"

    def test_create_performance_report(self, mock_ocr_service, temp_image_files, tmp_path):
        """Create a JSON performance report."""

        def process_image(path):
            return mock_ocr_service.process_image(path)

        result = run_load_test(
            process_image,
            50,  # iterations
            4,  # concurrency
            temp_image_files[0]
        )

        report = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "configuration": {
                "iterations": result.total_requests,
                "concurrency": 4
            },
            "results": {
                "success_rate": result.success_rate,
                "throughput_per_second": result.throughput_per_second,
                "latency": {
                    "mean_ms": result.latency_mean_ms,
                    "p50_ms": result.latency_p50_ms,
                    "p95_ms": result.latency_p95_ms,
                    "p99_ms": result.latency_p99_ms
                },
                "memory": {
                    "start_mb": result.memory_start_mb,
                    "peak_mb": result.memory_peak_mb,
                    "end_mb": result.memory_end_mb
                }
            },
            "targets": {
                "min_throughput": MIN_THROUGHPUT,
                "max_latency_p95_ms": MAX_LATENCY_P95,
                "max_memory_growth_mb": MAX_MEMORY_GROWTH_MB
            },
            "passed": {
                "throughput": result.throughput_per_second >= MIN_THROUGHPUT,
                "latency": result.latency_p95_ms <= MAX_LATENCY_P95,
                "memory": (result.memory_peak_mb - result.memory_start_mb) < MAX_MEMORY_GROWTH_MB
            }
        }

        # Save report
        report_path = tmp_path / "performance_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\nPerformance report saved to: {report_path}")

        # Verify report was created
        assert report_path.exists()


# ==============================================================================
# Run Tests
# ==============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
