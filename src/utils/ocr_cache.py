"""
OCR Model Cache Layer - LRU caching for model-level lookups.

Provides 10x+ speedup potential by caching:
- Confusion matrix lookups (char, position) -> candidates
- N-gram word scores -> float
- Morphology analysis results -> dict
- English validation results -> tuple

Part of Phase 7: Performance & Quality implementation.
"""

from functools import lru_cache
from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
import threading
import logging

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """Statistics for cache performance monitoring."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_calls: int = 0
    last_reset: datetime = field(default_factory=datetime.now)

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        if self.total_calls == 0:
            return 0.0
        return self.hits / self.total_calls

    def record_hit(self) -> None:
        """Record a cache hit."""
        self.hits += 1
        self.total_calls += 1

    def record_miss(self) -> None:
        """Record a cache miss."""
        self.misses += 1
        self.total_calls += 1

    def reset(self) -> None:
        """Reset statistics."""
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.total_calls = 0
        self.last_reset = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            'hits': self.hits,
            'misses': self.misses,
            'evictions': self.evictions,
            'total_calls': self.total_calls,
            'hit_rate': round(self.hit_rate, 4),
            'last_reset': self.last_reset.isoformat()
        }


class OCRModelCache:
    """
    LRU cache layer for OCR model lookups.

    Caches expensive computations:
    - Confusion matrix: ~112 entries (28 chars x 4 positions)
    - N-gram word scores: common words repeated across documents
    - Morphology analysis: expensive pattern matching
    - English validation: dictionary lookups

    Thread-safe with per-cache statistics tracking.

    Usage:
        cache = OCRModelCache()

        # Wrap confusion matrix
        confusions = cache.get_confusions('ب', 'initial')

        # Wrap n-gram scoring
        score = cache.score_word('فاتورة')

        # Get statistics
        stats = cache.get_all_stats()
    """

    # Cache size configurations
    CONFUSION_CACHE_SIZE = 256      # 28 chars x 4 positions + buffer
    NGRAM_CACHE_SIZE = 2000         # Common words repeated
    MORPHOLOGY_CACHE_SIZE = 1000    # Expensive analysis
    ENGLISH_CACHE_SIZE = 1000       # Dictionary lookups
    TRIGRAM_CACHE_SIZE = 500        # English trigram scores

    _instance: Optional['OCRModelCache'] = None
    _lock = threading.Lock()

    def __new__(cls) -> 'OCRModelCache':
        """Singleton pattern for global cache instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize cache with statistics tracking."""
        if self._initialized:
            return

        self._initialized = True

        # Statistics per cache type
        self._stats: Dict[str, CacheStats] = {
            'confusion': CacheStats(),
            'ngram': CacheStats(),
            'morphology': CacheStats(),
            'english': CacheStats(),
            'trigram': CacheStats()
        }

        # Underlying model references (lazy loaded)
        self._confusion_matrix = None
        self._ngram_model = None
        self._morphology_analyzer = None
        self._english_validator = None

        # Create cached methods
        self._setup_caches()

        logger.info("OCRModelCache initialized with sizes: "
                   f"confusion={self.CONFUSION_CACHE_SIZE}, "
                   f"ngram={self.NGRAM_CACHE_SIZE}, "
                   f"morphology={self.MORPHOLOGY_CACHE_SIZE}, "
                   f"english={self.ENGLISH_CACHE_SIZE}")

    def _setup_caches(self) -> None:
        """Set up LRU cached methods."""
        # These are instance-level caches that wrap the actual model methods
        self._confusion_cache = lru_cache(maxsize=self.CONFUSION_CACHE_SIZE)(
            self._get_confusions_impl
        )
        self._ngram_cache = lru_cache(maxsize=self.NGRAM_CACHE_SIZE)(
            self._score_word_impl
        )
        self._morphology_cache = lru_cache(maxsize=self.MORPHOLOGY_CACHE_SIZE)(
            self._analyze_word_impl
        )
        self._english_cache = lru_cache(maxsize=self.ENGLISH_CACHE_SIZE)(
            self._validate_english_impl
        )
        self._trigram_cache = lru_cache(maxsize=self.TRIGRAM_CACHE_SIZE)(
            self._score_trigrams_impl
        )

    # =========================================================================
    # Confusion Matrix Cache
    # =========================================================================

    def get_confusions(
        self,
        char: str,
        position: str = 'isolated'
    ) -> Tuple[Tuple[str, float], ...]:
        """
        Get confusion candidates for Arabic character at position.

        Args:
            char: Arabic character
            position: 'isolated', 'initial', 'medial', 'final'

        Returns:
            Tuple of (candidate_char, probability) pairs
        """
        # Track statistics
        cache_info = self._confusion_cache.cache_info()
        result = self._confusion_cache(char, position)
        new_cache_info = self._confusion_cache.cache_info()

        if new_cache_info.hits > cache_info.hits:
            self._stats['confusion'].record_hit()
        else:
            self._stats['confusion'].record_miss()

        return result

    def _get_confusions_impl(
        self,
        char: str,
        position: str
    ) -> Tuple[Tuple[str, float], ...]:
        """Actual implementation - calls confusion matrix model."""
        if self._confusion_matrix is None:
            self._load_confusion_matrix()

        if self._confusion_matrix is None:
            return ()

        try:
            candidates = self._confusion_matrix.get_confusions(char, position)
            # Convert to tuple for hashability
            return tuple((c, p) for c, p in candidates)
        except Exception as e:
            logger.warning(f"Confusion matrix lookup failed: {e}")
            return ()

    def _load_confusion_matrix(self) -> None:
        """Lazy load confusion matrix model."""
        try:
            from ..ml.arabic_confusion_matrix import get_confusion_matrix
            self._confusion_matrix = get_confusion_matrix()
        except ImportError:
            logger.warning("Arabic confusion matrix not available")

    # =========================================================================
    # N-gram Score Cache
    # =========================================================================

    def score_word(self, word: str) -> float:
        """
        Get n-gram score for Arabic word.

        Args:
            word: Arabic word to score

        Returns:
            Score from 0.0 to 1.0 (higher = more likely valid)
        """
        cache_info = self._ngram_cache.cache_info()
        result = self._ngram_cache(word)
        new_cache_info = self._ngram_cache.cache_info()

        if new_cache_info.hits > cache_info.hits:
            self._stats['ngram'].record_hit()
        else:
            self._stats['ngram'].record_miss()

        return result

    def _score_word_impl(self, word: str) -> float:
        """Actual implementation - calls n-gram model."""
        if self._ngram_model is None:
            self._load_ngram_model()

        if self._ngram_model is None:
            return 0.5  # Neutral score

        try:
            return self._ngram_model.score_word(word)
        except Exception as e:
            logger.warning(f"N-gram scoring failed: {e}")
            return 0.5

    def _load_ngram_model(self) -> None:
        """Lazy load n-gram model."""
        try:
            from ..ml.arabic_ngram_model import get_ngram_model
            self._ngram_model = get_ngram_model()
        except ImportError:
            logger.warning("Arabic n-gram model not available")

    # =========================================================================
    # Morphology Analysis Cache
    # =========================================================================

    def analyze_word(self, word: str) -> Dict[str, Any]:
        """
        Get morphological analysis for Arabic word.

        Args:
            word: Arabic word to analyze

        Returns:
            Dict with 'root', 'pattern', 'prefixes', 'suffixes', 'pos'
        """
        cache_info = self._morphology_cache.cache_info()
        result = self._morphology_cache(word)
        new_cache_info = self._morphology_cache.cache_info()

        if new_cache_info.hits > cache_info.hits:
            self._stats['morphology'].record_hit()
        else:
            self._stats['morphology'].record_miss()

        return result

    def _analyze_word_impl(self, word: str) -> Dict[str, Any]:
        """Actual implementation - calls morphology analyzer."""
        if self._morphology_analyzer is None:
            self._load_morphology_analyzer()

        if self._morphology_analyzer is None:
            return {'word': word, 'analyzed': False}

        try:
            result = self._morphology_analyzer.analyze(word)
            # Convert to dict for caching
            if hasattr(result, '__dict__'):
                return {
                    'word': word,
                    'root': getattr(result, 'root', ''),
                    'pattern': getattr(result, 'pattern', ''),
                    'prefixes': getattr(result, 'prefixes', []),
                    'suffixes': getattr(result, 'suffixes', []),
                    'pos': getattr(result, 'pos', ''),
                    'analyzed': True
                }
            return {'word': word, 'analyzed': False}
        except Exception as e:
            logger.warning(f"Morphology analysis failed: {e}")
            return {'word': word, 'analyzed': False}

    def _load_morphology_analyzer(self) -> None:
        """Lazy load morphology analyzer."""
        try:
            from ..utils.arabic_morphology import get_morphology_analyzer
            self._morphology_analyzer = get_morphology_analyzer()
        except ImportError:
            logger.warning("Arabic morphology analyzer not available")

    # =========================================================================
    # English Validation Cache
    # =========================================================================

    def validate_english(self, word: str) -> Tuple[str, float, bool]:
        """
        Validate English word.

        Args:
            word: English word to validate

        Returns:
            Tuple of (corrected_word, confidence, is_valid)
        """
        cache_info = self._english_cache.cache_info()
        result = self._english_cache(word.lower())  # Normalize for caching
        new_cache_info = self._english_cache.cache_info()

        if new_cache_info.hits > cache_info.hits:
            self._stats['english'].record_hit()
        else:
            self._stats['english'].record_miss()

        return result

    def _validate_english_impl(self, word: str) -> Tuple[str, float, bool]:
        """Actual implementation - calls English validator."""
        if self._english_validator is None:
            self._load_english_validator()

        if self._english_validator is None:
            return (word, 0.5, True)  # Assume valid if no validator

        try:
            corrected, confidence = self._english_validator.validate_word(word)
            is_valid = confidence > 0.7
            return (corrected, confidence, is_valid)
        except Exception as e:
            logger.warning(f"English validation failed: {e}")
            return (word, 0.5, True)

    def _load_english_validator(self) -> None:
        """Lazy load English validator."""
        try:
            from ..validators.english_validator import get_english_validator
            self._english_validator = get_english_validator()
        except ImportError:
            logger.warning("English validator not available")

    # =========================================================================
    # English Trigram Score Cache
    # =========================================================================

    def score_trigrams(self, text: str) -> Tuple[float, bool, int]:
        """
        Score English text using trigrams.

        Args:
            text: English text to score

        Returns:
            Tuple of (score, is_common, trigram_hits)
        """
        # Normalize text for consistent caching
        normalized = text.lower().strip()
        if len(normalized) < 3:
            return (0.5, False, 0)

        cache_info = self._trigram_cache.cache_info()
        result = self._trigram_cache(normalized)
        new_cache_info = self._trigram_cache.cache_info()

        if new_cache_info.hits > cache_info.hits:
            self._stats['trigram'].record_hit()
        else:
            self._stats['trigram'].record_miss()

        return result

    def _score_trigrams_impl(self, text: str) -> Tuple[float, bool, int]:
        """Actual implementation - calls English validator trigram scoring."""
        if self._english_validator is None:
            self._load_english_validator()

        if self._english_validator is None:
            return (0.5, False, 0)

        try:
            result = self._english_validator.score_trigrams(text)
            return (result.score, result.is_common, result.trigram_hits)
        except Exception as e:
            logger.warning(f"Trigram scoring failed: {e}")
            return (0.5, False, 0)

    # =========================================================================
    # Statistics and Management
    # =========================================================================

    def get_stats(self, cache_type: str) -> CacheStats:
        """Get statistics for specific cache."""
        return self._stats.get(cache_type, CacheStats())

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all caches."""
        stats = {}
        for name, cache_stats in self._stats.items():
            stats[name] = cache_stats.to_dict()

            # Add cache info from lru_cache
            cache_method = getattr(self, f'_{name}_cache', None)
            if cache_method and hasattr(cache_method, 'cache_info'):
                info = cache_method.cache_info()
                stats[name]['lru_hits'] = info.hits
                stats[name]['lru_misses'] = info.misses
                stats[name]['lru_maxsize'] = info.maxsize
                stats[name]['lru_currsize'] = info.currsize

        return stats

    def clear_cache(self, cache_type: Optional[str] = None) -> None:
        """
        Clear cache(s).

        Args:
            cache_type: Specific cache to clear, or None for all
        """
        if cache_type is None:
            # Clear all caches
            self._confusion_cache.cache_clear()
            self._ngram_cache.cache_clear()
            self._morphology_cache.cache_clear()
            self._english_cache.cache_clear()
            self._trigram_cache.cache_clear()

            for stats in self._stats.values():
                stats.reset()

            logger.info("All OCR caches cleared")
        else:
            cache_method = getattr(self, f'_{cache_type}_cache', None)
            if cache_method and hasattr(cache_method, 'cache_clear'):
                cache_method.cache_clear()
                if cache_type in self._stats:
                    self._stats[cache_type].reset()
                logger.info(f"OCR cache '{cache_type}' cleared")

    def get_cache_info(self) -> Dict[str, Dict[str, int]]:
        """Get LRU cache info for all caches."""
        info = {}
        for name in ['confusion', 'ngram', 'morphology', 'english', 'trigram']:
            cache_method = getattr(self, f'_{name}_cache', None)
            if cache_method and hasattr(cache_method, 'cache_info'):
                ci = cache_method.cache_info()
                info[name] = {
                    'hits': ci.hits,
                    'misses': ci.misses,
                    'maxsize': ci.maxsize,
                    'currsize': ci.currsize
                }
        return info


# Module-level singleton accessor
_cache_instance: Optional[OCRModelCache] = None


def get_ocr_cache() -> OCRModelCache:
    """
    Get the singleton OCR cache instance.

    Returns:
        OCRModelCache instance
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = OCRModelCache()
    return _cache_instance


def clear_ocr_cache() -> None:
    """Clear all OCR caches."""
    cache = get_ocr_cache()
    cache.clear_cache()


def get_cache_stats() -> Dict[str, Dict[str, Any]]:
    """Get statistics for all OCR caches."""
    cache = get_ocr_cache()
    return cache.get_all_stats()


# Convenience functions for direct access
def cached_confusions(char: str, position: str = 'isolated') -> Tuple[Tuple[str, float], ...]:
    """Get cached confusion candidates for Arabic character."""
    return get_ocr_cache().get_confusions(char, position)


def cached_ngram_score(word: str) -> float:
    """Get cached n-gram score for Arabic word."""
    return get_ocr_cache().score_word(word)


def cached_morphology(word: str) -> Dict[str, Any]:
    """Get cached morphology analysis for Arabic word."""
    return get_ocr_cache().analyze_word(word)


def cached_english_validation(word: str) -> Tuple[str, float, bool]:
    """Get cached English word validation."""
    return get_ocr_cache().validate_english(word)


def cached_trigram_score(text: str) -> Tuple[float, bool, int]:
    """Get cached English trigram score."""
    return get_ocr_cache().score_trigrams(text)
