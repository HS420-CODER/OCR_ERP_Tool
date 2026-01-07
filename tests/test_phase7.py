"""
Test Phase 7: Performance & Quality modules.

Tests:
- OCR Cache Layer
- Metrics Tracker (CER/WER)
- Batch Processor (import only, actual processing needs images)
"""

import sys
sys.path.insert(0, 'C:/wamp64/www/OCR_2')

import unittest


class TestOCRCache(unittest.TestCase):
    """Test OCR Cache module."""

    def test_cache_import(self):
        """Test cache module imports."""
        from src.utils.ocr_cache import (
            OCRModelCache,
            CacheStats,
            get_ocr_cache,
            clear_ocr_cache,
            get_cache_stats
        )
        self.assertTrue(callable(get_ocr_cache))

    def test_cache_singleton(self):
        """Test singleton pattern."""
        from src.utils.ocr_cache import get_ocr_cache
        cache1 = get_ocr_cache()
        cache2 = get_ocr_cache()
        self.assertIs(cache1, cache2)

    def test_cache_stats(self):
        """Test cache statistics."""
        from src.utils.ocr_cache import CacheStats
        stats = CacheStats()
        stats.record_hit()
        stats.record_miss()
        self.assertEqual(stats.hits, 1)
        self.assertEqual(stats.misses, 1)
        self.assertEqual(stats.total_calls, 2)
        self.assertEqual(stats.hit_rate, 0.5)

    def test_cache_clear(self):
        """Test cache clearing."""
        from src.utils.ocr_cache import get_ocr_cache, clear_ocr_cache
        cache = get_ocr_cache()
        clear_ocr_cache()
        stats = cache.get_all_stats()
        self.assertIn('confusion', stats)
        self.assertIn('ngram', stats)

    def test_utils_exports(self):
        """Test exports from utils __init__."""
        from src.utils import (
            CacheStats,
            OCRModelCache,
            get_ocr_cache,
            clear_ocr_cache,
            get_cache_stats
        )
        self.assertTrue(callable(get_ocr_cache))


class TestMetricsTracker(unittest.TestCase):
    """Test Metrics Tracker module."""

    def test_metrics_import(self):
        """Test metrics module imports."""
        from src.utils.metrics_tracker import (
            MetricsTracker,
            QualityMetrics,
            BenchmarkReport,
            levenshtein_distance,
            calculate_cer,
            calculate_wer
        )
        self.assertTrue(callable(calculate_cer))

    def test_levenshtein_distance(self):
        """Test Levenshtein distance calculation."""
        from src.utils.metrics_tracker import levenshtein_distance

        # Identical strings
        self.assertEqual(levenshtein_distance("hello", "hello"), 0)

        # One substitution
        self.assertEqual(levenshtein_distance("hello", "hallo"), 1)

        # One deletion
        self.assertEqual(levenshtein_distance("hello", "helo"), 1)

        # One insertion
        self.assertEqual(levenshtein_distance("hello", "helllo"), 1)

        # Multiple edits
        self.assertEqual(levenshtein_distance("kitten", "sitting"), 3)

        # Empty strings
        self.assertEqual(levenshtein_distance("", "hello"), 5)
        self.assertEqual(levenshtein_distance("hello", ""), 5)
        self.assertEqual(levenshtein_distance("", ""), 0)

    def test_cer_calculation(self):
        """Test Character Error Rate calculation."""
        from src.utils.metrics_tracker import MetricsTracker
        tracker = MetricsTracker()

        # Perfect match
        cer = tracker.calculate_cer("hello world", "hello world")
        self.assertEqual(cer, 0.0)

        # One error in 11 characters
        cer = tracker.calculate_cer("hello world", "helo world")
        self.assertAlmostEqual(cer, 1/11, places=4)

        # Multiple errors
        cer = tracker.calculate_cer("the quick", "teh quikc")
        self.assertGreater(cer, 0)
        self.assertLess(cer, 1)

    def test_wer_calculation(self):
        """Test Word Error Rate calculation."""
        from src.utils.metrics_tracker import MetricsTracker
        tracker = MetricsTracker()

        # Perfect match
        wer = tracker.calculate_wer("hello world", "hello world")
        self.assertEqual(wer, 0.0)

        # One wrong word in 3 words
        wer = tracker.calculate_wer("the quick fox", "the slow fox")
        self.assertAlmostEqual(wer, 1/3, places=4)

    def test_quality_metrics_dataclass(self):
        """Test QualityMetrics dataclass."""
        from src.utils.metrics_tracker import QualityMetrics
        metrics = QualityMetrics(
            cer=0.05,
            wer=0.10,
            confidence=0.95,
            meets_target=True
        )
        self.assertEqual(metrics.cer, 0.05)
        self.assertEqual(metrics.wer, 0.10)
        self.assertTrue(metrics.meets_target)

        # Test to_dict
        d = metrics.to_dict()
        self.assertIn('cer', d)
        self.assertIn('wer', d)

    def test_benchmark_targets(self):
        """Test benchmark target constants."""
        from src.utils.metrics_tracker import MetricsTracker
        tracker = MetricsTracker()

        # Arabic targets
        self.assertEqual(tracker.TARGETS['ar']['cer'], 0.06)
        self.assertEqual(tracker.TARGETS['ar']['wer'], 0.16)

        # English targets
        self.assertEqual(tracker.TARGETS['en']['cer'], 0.02)
        self.assertEqual(tracker.TARGETS['en']['wer'], 0.04)

        # Mixed targets
        self.assertEqual(tracker.TARGETS['mixed']['cer'], 0.08)
        self.assertEqual(tracker.TARGETS['mixed']['wer'], 0.12)

    def test_calculate_metrics(self):
        """Test full metrics calculation."""
        from src.utils.metrics_tracker import MetricsTracker
        tracker = MetricsTracker()

        metrics = tracker.calculate_metrics(
            hypothesis="hello world",
            reference="hello world",
            language="en",
            confidence=0.95
        )
        self.assertEqual(metrics.cer, 0.0)
        self.assertEqual(metrics.wer, 0.0)
        self.assertTrue(metrics.meets_target)

    def test_generate_report(self):
        """Test report generation."""
        from src.utils.metrics_tracker import MetricsTracker
        tracker = MetricsTracker()

        # Track some results using track_result (calculate_metrics doesn't auto-track)
        tracker.track_result({'full_text': 'hello', 'confidence': 0.9}, "hello", "en")
        tracker.track_result({'full_text': 'world', 'confidence': 0.8}, "world", "en")

        report = tracker.generate_report()
        self.assertEqual(report.total_samples, 2)

    def test_utils_exports(self):
        """Test exports from utils __init__."""
        from src.utils import (
            QualityMetrics,
            BenchmarkReport,
            MetricsTracker,
            get_metrics_tracker,
            calculate_cer,
            calculate_wer,
            levenshtein_distance
        )
        self.assertTrue(callable(calculate_cer))
        self.assertTrue(callable(calculate_wer))


class TestBatchProcessor(unittest.TestCase):
    """Test Batch Processor module (import tests only)."""

    def test_batch_processor_import(self):
        """Test batch processor imports."""
        from src.api.batch_processor import (
            BatchOCRProcessor,
            BatchResult,
            get_batch_processor
        )
        self.assertTrue(callable(get_batch_processor))

    def test_batch_result_dataclass(self):
        """Test BatchResult dataclass."""
        from src.api.batch_processor import BatchResult
        result = BatchResult(
            total_images=10,
            successful=8,
            failed=2,
            total_time_ms=5000.0
        )
        self.assertEqual(result.total_images, 10)
        self.assertEqual(result.success_rate, 0.8)

        d = result.to_dict()
        self.assertIn('total_images', d)
        self.assertIn('success_rate', d)

    def test_api_module_import(self):
        """Test API module __init__ imports."""
        from src.api import (
            BatchResult,
            BatchOCRProcessor,
            get_batch_processor,
            process_batch,
            process_batch_async
        )
        self.assertTrue(callable(process_batch))


class TestArabicMetrics(unittest.TestCase):
    """Test Arabic-specific metrics."""

    def test_arabic_cer(self):
        """Test CER with Arabic text."""
        from src.utils.metrics_tracker import MetricsTracker
        tracker = MetricsTracker()

        # Arabic text
        ref = "مرحبا بالعالم"
        hyp = "مرحبا بالعالم"
        cer = tracker.calculate_cer(ref, hyp)
        self.assertEqual(cer, 0.0)

        # One character error in Arabic
        ref = "فاتورة ضريبية"
        hyp = "فاتوره ضريبية"  # ة vs ه
        cer = tracker.calculate_cer(ref, hyp)
        self.assertGreater(cer, 0)
        self.assertLess(cer, 0.1)

    def test_mixed_language_metrics(self):
        """Test metrics with mixed Arabic-English text."""
        from src.utils.metrics_tracker import MetricsTracker
        tracker = MetricsTracker()

        ref = "Invoice فاتورة Total المجموع"
        hyp = "Invoice فاتورة Total المجموع"
        cer = tracker.calculate_cer(ref, hyp)
        self.assertEqual(cer, 0.0)


if __name__ == '__main__':
    print("=" * 60)
    print("Phase 7: Performance & Quality Module Tests")
    print("=" * 60)
    unittest.main(verbosity=2)
