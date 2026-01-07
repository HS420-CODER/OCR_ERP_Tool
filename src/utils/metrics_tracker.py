"""
Quality Metrics Tracker - CER/WER calculation and benchmark tracking.

Calculates Character Error Rate (CER) and Word Error Rate (WER) using
Levenshtein distance. Tracks metrics over time against research-verified
benchmarks (arXiv:2506.02295).

Part of Phase 7: Performance & Quality implementation.
"""

import json
import logging
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)


def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calculate standard Levenshtein edit distance.

    Uses dynamic programming with O(m*n) time and space complexity.

    Args:
        s1: Reference string
        s2: Hypothesis string

    Returns:
        Edit distance (int)
    """
    m, n = len(s1), len(s2)

    # Handle edge cases
    if m == 0:
        return n
    if n == 0:
        return m

    # Create DP matrix
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    # Initialize first row and column
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j

    # Fill DP matrix
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,      # deletion
                dp[i][j - 1] + 1,      # insertion
                dp[i - 1][j - 1] + cost  # substitution
            )

    return dp[m][n]


def word_levenshtein_distance(words1: List[str], words2: List[str]) -> int:
    """
    Calculate word-level Levenshtein distance.

    Args:
        words1: Reference word list
        words2: Hypothesis word list

    Returns:
        Word-level edit distance (int)
    """
    m, n = len(words1), len(words2)

    if m == 0:
        return n
    if n == 0:
        return m

    dp = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if words1[i - 1] == words2[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,
                dp[i][j - 1] + 1,
                dp[i - 1][j - 1] + cost
            )

    return dp[m][n]


@dataclass
class QualityMetrics:
    """Metrics for a single OCR result."""

    cer: float = 0.0                     # Character Error Rate
    wer: float = 0.0                     # Word Error Rate
    arabic_cer: Optional[float] = None   # Arabic-specific CER
    arabic_wer: Optional[float] = None
    english_cer: Optional[float] = None  # English-specific CER
    english_wer: Optional[float] = None
    confidence: float = 0.0              # OCR engine confidence
    meets_target: bool = False           # Meets benchmark target
    target_gap: Dict[str, float] = field(default_factory=dict)
    processing_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'cer': round(self.cer, 4),
            'wer': round(self.wer, 4),
            'arabic_cer': round(self.arabic_cer, 4) if self.arabic_cer is not None else None,
            'arabic_wer': round(self.arabic_wer, 4) if self.arabic_wer is not None else None,
            'english_cer': round(self.english_cer, 4) if self.english_cer is not None else None,
            'english_wer': round(self.english_wer, 4) if self.english_wer is not None else None,
            'confidence': round(self.confidence, 4),
            'meets_target': self.meets_target,
            'target_gap': {k: round(v, 4) for k, v in self.target_gap.items()},
            'processing_time_ms': round(self.processing_time_ms, 2),
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class BenchmarkReport:
    """Aggregate statistics from multiple samples."""

    total_samples: int = 0
    avg_cer: float = 0.0
    avg_wer: float = 0.0
    cer_std: float = 0.0
    wer_std: float = 0.0
    min_cer: float = 0.0
    max_cer: float = 0.0
    min_wer: float = 0.0
    max_wer: float = 0.0
    target_pass_rate: float = 0.0
    language_breakdown: Dict[str, Dict[str, float]] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'total_samples': self.total_samples,
            'avg_cer': round(self.avg_cer, 4),
            'avg_wer': round(self.avg_wer, 4),
            'cer_std': round(self.cer_std, 4),
            'wer_std': round(self.wer_std, 4),
            'cer_range': [round(self.min_cer, 4), round(self.max_cer, 4)],
            'wer_range': [round(self.min_wer, 4), round(self.max_wer, 4)],
            'target_pass_rate': round(self.target_pass_rate, 4),
            'language_breakdown': self.language_breakdown,
            'generated_at': self.generated_at.isoformat()
        }


class MetricsTracker:
    """
    Track OCR quality with CER/WER against research benchmarks.

    Benchmark targets from arXiv:2506.02295:
    - Arabic: CER <0.06 (6%), WER <0.16 (16%)
    - English: CER <0.02 (2%), WER <0.04 (4%)
    - Mixed: CER <0.08 (8%), WER <0.12 (12%)

    Usage:
        tracker = MetricsTracker()

        # Calculate metrics for single result
        metrics = tracker.calculate_metrics(
            hypothesis="detected text",
            reference="ground truth text",
            language="ar"
        )

        # Track result from BilingualOCRResult
        metrics = tracker.track_result(ocr_result, reference_text)

        # Generate report
        report = tracker.generate_report()
    """

    # Research-verified benchmark targets (arXiv:2506.02295)
    TARGETS = {
        'ar': {'cer': 0.06, 'wer': 0.16},
        'en': {'cer': 0.02, 'wer': 0.04},
        'mixed': {'cer': 0.08, 'wer': 0.12}
    }

    def __init__(
        self,
        output_dir: Optional[str] = None,
        max_history: int = 10000
    ):
        """
        Initialize metrics tracker.

        Args:
            output_dir: Directory for saving reports
            max_history: Maximum samples to keep in memory
        """
        self.output_dir = Path(output_dir) if output_dir else None
        self.max_history = max_history
        self.metrics_history: List[QualityMetrics] = []

        if self.output_dir:
            self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"MetricsTracker initialized with targets: {self.TARGETS}")

    def calculate_cer(
        self,
        reference: str,
        hypothesis: str,
        normalize: bool = True
    ) -> float:
        """
        Calculate Character Error Rate.

        CER = Levenshtein(reference, hypothesis) / len(reference)

        Args:
            reference: Ground truth text
            hypothesis: OCR-detected text
            normalize: Normalize whitespace and case

        Returns:
            CER value (0.0 = perfect, >1.0 = more errors than reference length)
        """
        if normalize:
            reference = ' '.join(reference.split()).strip()
            hypothesis = ' '.join(hypothesis.split()).strip()

        if not reference:
            return 1.0 if hypothesis else 0.0

        distance = levenshtein_distance(reference, hypothesis)
        return distance / len(reference)

    def calculate_wer(
        self,
        reference: str,
        hypothesis: str,
        normalize: bool = True
    ) -> float:
        """
        Calculate Word Error Rate.

        WER = Word-level Levenshtein / word_count(reference)

        Args:
            reference: Ground truth text
            hypothesis: OCR-detected text
            normalize: Normalize whitespace

        Returns:
            WER value (0.0 = perfect, >1.0 = more errors than word count)
        """
        if normalize:
            reference = ' '.join(reference.split()).strip()
            hypothesis = ' '.join(hypothesis.split()).strip()

        ref_words = reference.split()
        hyp_words = hypothesis.split()

        if not ref_words:
            return 1.0 if hyp_words else 0.0

        distance = word_levenshtein_distance(ref_words, hyp_words)
        return distance / len(ref_words)

    def calculate_metrics(
        self,
        hypothesis: str,
        reference: str,
        language: str = 'mixed',
        confidence: float = 0.0,
        processing_time_ms: float = 0.0
    ) -> QualityMetrics:
        """
        Calculate quality metrics for single result.

        Args:
            hypothesis: OCR-detected text
            reference: Ground truth text
            language: Language code ('ar', 'en', 'mixed')
            confidence: OCR engine confidence
            processing_time_ms: Processing time in milliseconds

        Returns:
            QualityMetrics with CER, WER, and target comparison
        """
        cer = self.calculate_cer(reference, hypothesis)
        wer = self.calculate_wer(reference, hypothesis)

        # Get target for language
        lang_key = language.lower()
        if lang_key not in self.TARGETS:
            lang_key = 'mixed'

        targets = self.TARGETS[lang_key]
        meets_target = (cer <= targets['cer']) and (wer <= targets['wer'])

        target_gap = {
            'cer_gap': cer - targets['cer'],
            'wer_gap': wer - targets['wer']
        }

        metrics = QualityMetrics(
            cer=cer,
            wer=wer,
            confidence=confidence,
            meets_target=meets_target,
            target_gap=target_gap,
            processing_time_ms=processing_time_ms
        )

        # Set language-specific metrics
        if lang_key == 'ar':
            metrics.arabic_cer = cer
            metrics.arabic_wer = wer
        elif lang_key == 'en':
            metrics.english_cer = cer
            metrics.english_wer = wer

        return metrics

    def track_result(
        self,
        ocr_result: Any,
        reference_text: Optional[str] = None,
        language: Optional[str] = None
    ) -> QualityMetrics:
        """
        Track metrics from a BilingualOCRResult.

        Args:
            ocr_result: BilingualOCRResult or similar result object
            reference_text: Ground truth (optional for tracking without benchmark)
            language: Language override

        Returns:
            QualityMetrics (stored in history)
        """
        # Extract text and metadata from result
        hypothesis = ''
        confidence = 0.0
        processing_time = 0.0
        detected_language = 'mixed'

        if hasattr(ocr_result, 'full_text'):
            hypothesis = ocr_result.full_text
        elif isinstance(ocr_result, dict):
            hypothesis = ocr_result.get('full_text', '')

        if hasattr(ocr_result, 'overall_confidence'):
            confidence = ocr_result.overall_confidence
        elif isinstance(ocr_result, dict):
            confidence = ocr_result.get('confidence', 0.0)

        if hasattr(ocr_result, 'processing_time_ms'):
            processing_time = ocr_result.processing_time_ms
        elif isinstance(ocr_result, dict):
            processing_time = ocr_result.get('processing_time_ms', 0.0)

        if hasattr(ocr_result, 'primary_language'):
            lang_obj = ocr_result.primary_language
            if hasattr(lang_obj, 'value'):
                detected_language = lang_obj.value
            else:
                detected_language = str(lang_obj)
        elif isinstance(ocr_result, dict):
            detected_language = ocr_result.get('primary_language', 'mixed')

        # Use provided language or detected
        lang = language or detected_language

        # Calculate metrics
        if reference_text:
            metrics = self.calculate_metrics(
                hypothesis=hypothesis,
                reference=reference_text,
                language=lang,
                confidence=confidence,
                processing_time_ms=processing_time
            )
        else:
            # No reference - track confidence only
            metrics = QualityMetrics(
                confidence=confidence,
                processing_time_ms=processing_time
            )

        # Add to history (with size limit)
        self.metrics_history.append(metrics)
        if len(self.metrics_history) > self.max_history:
            self.metrics_history = self.metrics_history[-self.max_history:]

        return metrics

    def generate_report(
        self,
        metrics_list: Optional[List[QualityMetrics]] = None
    ) -> BenchmarkReport:
        """
        Generate aggregate statistics report.

        Args:
            metrics_list: Optional specific metrics to analyze (default: history)

        Returns:
            BenchmarkReport with aggregate statistics
        """
        metrics = metrics_list or self.metrics_history

        if not metrics:
            return BenchmarkReport()

        # Filter metrics with CER/WER (have reference text)
        valid_metrics = [m for m in metrics if m.cer > 0 or m.wer > 0]

        if not valid_metrics:
            return BenchmarkReport(
                total_samples=len(metrics),
                language_breakdown={'note': 'No reference text provided for CER/WER calculation'}
            )

        # Calculate aggregate statistics
        cer_values = [m.cer for m in valid_metrics]
        wer_values = [m.wer for m in valid_metrics]

        avg_cer = statistics.mean(cer_values)
        avg_wer = statistics.mean(wer_values)

        cer_std = statistics.stdev(cer_values) if len(cer_values) > 1 else 0.0
        wer_std = statistics.stdev(wer_values) if len(wer_values) > 1 else 0.0

        # Target pass rate
        passing = sum(1 for m in valid_metrics if m.meets_target)
        pass_rate = passing / len(valid_metrics)

        # Language breakdown
        language_breakdown = {}

        ar_metrics = [m for m in valid_metrics if m.arabic_cer is not None]
        if ar_metrics:
            language_breakdown['arabic'] = {
                'count': len(ar_metrics),
                'avg_cer': round(statistics.mean(m.arabic_cer for m in ar_metrics), 4),
                'avg_wer': round(statistics.mean(m.arabic_wer for m in ar_metrics if m.arabic_wer), 4),
                'target_cer': self.TARGETS['ar']['cer'],
                'target_wer': self.TARGETS['ar']['wer']
            }

        en_metrics = [m for m in valid_metrics if m.english_cer is not None]
        if en_metrics:
            language_breakdown['english'] = {
                'count': len(en_metrics),
                'avg_cer': round(statistics.mean(m.english_cer for m in en_metrics), 4),
                'avg_wer': round(statistics.mean(m.english_wer for m in en_metrics if m.english_wer), 4),
                'target_cer': self.TARGETS['en']['cer'],
                'target_wer': self.TARGETS['en']['wer']
            }

        return BenchmarkReport(
            total_samples=len(metrics),
            avg_cer=avg_cer,
            avg_wer=avg_wer,
            cer_std=cer_std,
            wer_std=wer_std,
            min_cer=min(cer_values),
            max_cer=max(cer_values),
            min_wer=min(wer_values),
            max_wer=max(wer_values),
            target_pass_rate=pass_rate,
            language_breakdown=language_breakdown
        )

    def export_json(self, filepath: Optional[str] = None) -> str:
        """
        Export metrics history to JSON file.

        Args:
            filepath: Output path (default: output_dir/metrics_TIMESTAMP.json)

        Returns:
            Path to exported file
        """
        if filepath:
            output_path = Path(filepath)
        elif self.output_dir:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = self.output_dir / f'metrics_{timestamp}.json'
        else:
            output_path = Path(f'metrics_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')

        report = self.generate_report()

        export_data = {
            'report': report.to_dict(),
            'metrics': [m.to_dict() for m in self.metrics_history],
            'targets': self.TARGETS
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Metrics exported to {output_path}")
        return str(output_path)

    def export_prometheus(self) -> str:
        """
        Export metrics in Prometheus format.

        Returns:
            Prometheus-compatible metrics string
        """
        report = self.generate_report()

        lines = [
            '# HELP ocr_cer_avg Average Character Error Rate',
            '# TYPE ocr_cer_avg gauge',
            f'ocr_cer_avg {report.avg_cer}',
            '',
            '# HELP ocr_wer_avg Average Word Error Rate',
            '# TYPE ocr_wer_avg gauge',
            f'ocr_wer_avg {report.avg_wer}',
            '',
            '# HELP ocr_target_pass_rate Rate of samples meeting benchmark targets',
            '# TYPE ocr_target_pass_rate gauge',
            f'ocr_target_pass_rate {report.target_pass_rate}',
            '',
            '# HELP ocr_samples_total Total samples processed',
            '# TYPE ocr_samples_total counter',
            f'ocr_samples_total {report.total_samples}',
        ]

        # Language-specific metrics
        for lang, data in report.language_breakdown.items():
            if isinstance(data, dict) and 'avg_cer' in data:
                lines.extend([
                    '',
                    f'# HELP ocr_cer_{lang} CER for {lang}',
                    f'# TYPE ocr_cer_{lang} gauge',
                    f'ocr_cer_{lang} {data["avg_cer"]}',
                ])

        return '\n'.join(lines)

    def clear_history(self) -> None:
        """Clear metrics history."""
        self.metrics_history.clear()
        logger.info("Metrics history cleared")

    def get_summary(self) -> Dict[str, Any]:
        """
        Get quick summary of current metrics.

        Returns:
            Dict with summary statistics
        """
        if not self.metrics_history:
            return {'status': 'no_data', 'samples': 0}

        report = self.generate_report()
        return {
            'status': 'ok',
            'samples': report.total_samples,
            'avg_cer': round(report.avg_cer, 4),
            'avg_wer': round(report.avg_wer, 4),
            'target_pass_rate': round(report.target_pass_rate, 2),
            'targets': self.TARGETS
        }


# Module-level singleton
_tracker_instance: Optional[MetricsTracker] = None


def get_metrics_tracker(output_dir: Optional[str] = None) -> MetricsTracker:
    """
    Get singleton metrics tracker instance.

    Args:
        output_dir: Optional output directory for reports

    Returns:
        MetricsTracker instance
    """
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = MetricsTracker(output_dir=output_dir)
    return _tracker_instance


def calculate_cer(reference: str, hypothesis: str) -> float:
    """Convenience function for CER calculation."""
    return get_metrics_tracker().calculate_cer(reference, hypothesis)


def calculate_wer(reference: str, hypothesis: str) -> float:
    """Convenience function for WER calculation."""
    return get_metrics_tracker().calculate_wer(reference, hypothesis)
