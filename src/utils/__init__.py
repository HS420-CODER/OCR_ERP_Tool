"""
Utility functions and helpers.

Modules:
- file_utils: File type detection, path validation
- image_utils: Image preprocessing, encoding
- logging_config: Structured JSON logging
- metrics: Prometheus metrics
- word_level_detector: Word-level language detection (Phase 4)
- arabizi_transliterator: Arabizi to Arabic conversion (Phase 4)
- bidirectional_text: RTL/LTR text handling (Phase 4)
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

# Phase 4: Language Processing
from .word_level_detector import (
    Language,
    ScriptType,
    WordAnalysis,
    LineAnalysis,
    WordLevelDetector,
    get_language_detector,
    detect_language,
    is_arabic,
    is_english,
    is_bilingual,
)

from .arabizi_transliterator import (
    TransliterationMode,
    TransliterationResult,
    ArabiziTransliterator,
    ArabicToArabiziConverter,
    get_arabizi_transliterator,
    transliterate_arabizi,
    is_arabizi,
    get_arabizi_confidence,
)

from .bidirectional_text import (
    BidiClass,
    Direction,
    BidiRun,
    BidiParagraph,
    BidirectionalTextHandler,
    get_bidi_handler,
    resolve_bidi,
    get_visual_text,
    detect_direction,
    is_rtl,
    is_ltr,
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
    "set_queue_size",
    # Phase 4: Word-Level Language Detection
    "Language",
    "ScriptType",
    "WordAnalysis",
    "LineAnalysis",
    "WordLevelDetector",
    "get_language_detector",
    "detect_language",
    "is_arabic",
    "is_english",
    "is_bilingual",
    # Phase 4: Arabizi Transliterator
    "TransliterationMode",
    "TransliterationResult",
    "ArabiziTransliterator",
    "ArabicToArabiziConverter",
    "get_arabizi_transliterator",
    "transliterate_arabizi",
    "is_arabizi",
    "get_arabizi_confidence",
    # Phase 4: Bidirectional Text
    "BidiClass",
    "Direction",
    "BidiRun",
    "BidiParagraph",
    "BidirectionalTextHandler",
    "get_bidi_handler",
    "resolve_bidi",
    "get_visual_text",
    "detect_direction",
    "is_rtl",
    "is_ltr",
]
