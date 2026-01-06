"""
ERP Arabic OCR Microservice - Fusion Engine Unit Tests
======================================================
Tests for the confidence-weighted fusion engine.
"""

import pytest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.services import OCRResult, FusionResult, FusionStrategy, OCREngine
from src.services.fusion_engine import (
    FusionEngine,
    ARABIC_VOCABULARY,
    ARABIC_VOCABULARY_EXTENDED
)


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def fusion_engine():
    """Create a FusionEngine instance."""
    return FusionEngine()


@pytest.fixture
def custom_vocabulary_engine():
    """Create a FusionEngine with custom vocabulary."""
    custom_vocab = {'فاتورة', 'ضريبة', 'مبلغ', 'رقم'}
    return FusionEngine(vocabulary=custom_vocab)


@pytest.fixture
def paddle_result():
    """Create a mock PaddleOCR result."""
    return OCRResult(
        text="الرقم الضريبي 310123456789012",
        confidence=0.95,
        engine=OCREngine.PADDLE,
        blocks=[]
    )


@pytest.fixture
def easyocr_result():
    """Create a mock EasyOCR result."""
    return OCRResult(
        text="الرقم الضريبي 310123456789012",
        confidence=0.92,
        engine=OCREngine.EASYOCR,
        blocks=[]
    )


@pytest.fixture
def tesseract_result():
    """Create a mock Tesseract result."""
    return OCRResult(
        text="الرقم الضريبى 310123456789012",
        confidence=0.78,
        engine=OCREngine.TESSERACT,
        blocks=[]
    )


@pytest.fixture
def divergent_results():
    """Create results with different texts."""
    return [
        OCRResult(
            text="فاتورة رقم 12345",
            confidence=0.90,
            engine=OCREngine.PADDLE,
            blocks=[]
        ),
        OCRResult(
            text="فاتوره رقم 12345",
            confidence=0.85,
            engine=OCREngine.EASYOCR,
            blocks=[]
        ),
        OCRResult(
            text="فاتورة رقم 12346",
            confidence=0.75,
            engine=OCREngine.TESSERACT,
            blocks=[]
        ),
    ]


@pytest.fixture
def bilingual_results():
    """Create bilingual Arabic+English results."""
    return [
        OCRResult(
            text="Invoice رقم الفاتورة Number 12345",
            confidence=0.93,
            engine=OCREngine.PADDLE,
            blocks=[]
        ),
        OCRResult(
            text="Invoice رقم الفاتورة Number 12345",
            confidence=0.91,
            engine=OCREngine.EASYOCR,
            blocks=[]
        ),
    ]


# ==============================================================================
# Initialization Tests
# ==============================================================================

class TestFusionEngineInitialization:
    """Tests for FusionEngine initialization."""

    def test_default_initialization(self):
        """Test default initialization."""
        engine = FusionEngine()

        assert engine.vocabulary == ARABIC_VOCABULARY_EXTENDED
        assert engine.confidence_threshold == 0.7

    def test_custom_vocabulary(self):
        """Test initialization with custom vocabulary."""
        custom_vocab = {'word1', 'word2'}
        engine = FusionEngine(vocabulary=custom_vocab)

        assert engine.vocabulary == custom_vocab

    def test_custom_confidence_threshold(self):
        """Test initialization with custom confidence threshold."""
        engine = FusionEngine(confidence_threshold=0.85)

        assert engine.confidence_threshold == 0.85

    def test_vocabulary_contains_common_terms(self):
        """Test that default vocabulary contains common invoice terms."""
        expected_terms = ['فاتورة', 'الضريبي', 'المبلغ', 'الاجمالي']

        for term in expected_terms:
            assert term in ARABIC_VOCABULARY


# ==============================================================================
# Confidence-Weighted Fusion Tests
# ==============================================================================

class TestConfidenceWeightedFusion:
    """Tests for confidence-weighted fusion strategy."""

    def test_basic_fusion(self, fusion_engine, paddle_result, easyocr_result):
        """Test basic confidence-weighted fusion."""
        results = [paddle_result, easyocr_result]

        fusion_result = fusion_engine.fuse_results(
            results,
            strategy=FusionStrategy.CONFIDENCE_WEIGHTED
        )

        assert fusion_result is not None
        assert isinstance(fusion_result, FusionResult)
        assert "الرقم" in fusion_result.fused_text
        assert "الضريبي" in fusion_result.fused_text
        assert fusion_result.confidence > 0

    def test_fusion_prefers_higher_confidence(self, fusion_engine, divergent_results):
        """Test that fusion prefers higher confidence words."""
        fusion_result = fusion_engine.fuse_results(
            divergent_results,
            strategy=FusionStrategy.CONFIDENCE_WEIGHTED
        )

        # Higher confidence result should contribute more
        assert "فاتورة" in fusion_result.fused_text  # From paddle (0.90)

    def test_fusion_with_vocabulary_bonus(self, fusion_engine):
        """Test that vocabulary words get bonus."""
        # Create results where one has vocabulary word, other doesn't
        results = [
            OCRResult(
                text="فاتورة",  # In vocabulary
                confidence=0.85,
                engine=OCREngine.PADDLE,
                blocks=[]
            ),
            OCRResult(
                text="فاتوره",  # Misspelled, not in vocabulary
                confidence=0.87,
                engine=OCREngine.EASYOCR,
                blocks=[]
            ),
        ]

        fusion_result = fusion_engine.fuse_results(
            results,
            strategy=FusionStrategy.CONFIDENCE_WEIGHTED
        )

        # Should prefer "فاتورة" due to vocabulary bonus
        assert "فاتورة" in fusion_result.fused_text

    def test_fusion_calculates_improvement_score(self, fusion_engine, paddle_result, easyocr_result):
        """Test improvement score calculation."""
        results = [paddle_result, easyocr_result]

        fusion_result = fusion_engine.fuse_results(
            results,
            strategy=FusionStrategy.CONFIDENCE_WEIGHTED
        )

        assert hasattr(fusion_result, 'improvement_score')
        # Improvement score = fused_confidence - max(individual_confidence)

    def test_fusion_tracks_word_sources(self, fusion_engine, paddle_result, easyocr_result):
        """Test that word sources are tracked."""
        results = [paddle_result, easyocr_result]

        fusion_result = fusion_engine.fuse_results(
            results,
            strategy=FusionStrategy.CONFIDENCE_WEIGHTED
        )

        assert hasattr(fusion_result, 'word_sources')
        assert isinstance(fusion_result.word_sources, dict)


# ==============================================================================
# Majority Voting Fusion Tests
# ==============================================================================

class TestMajorityVotingFusion:
    """Tests for majority voting fusion strategy."""

    def test_basic_majority_voting(self, fusion_engine, divergent_results):
        """Test basic majority voting."""
        fusion_result = fusion_engine.fuse_results(
            divergent_results,
            strategy=FusionStrategy.MAJORITY_VOTING
        )

        assert fusion_result is not None
        assert fusion_result.strategy == FusionStrategy.MAJORITY_VOTING

    def test_majority_wins(self, fusion_engine):
        """Test that majority word wins."""
        results = [
            OCRResult(text="فاتورة", confidence=0.90, engine=OCREngine.PADDLE, blocks=[]),
            OCRResult(text="فاتورة", confidence=0.85, engine=OCREngine.EASYOCR, blocks=[]),
            OCRResult(text="فاتوره", confidence=0.95, engine=OCREngine.TESSERACT, blocks=[]),
        ]

        fusion_result = fusion_engine.fuse_results(
            results,
            strategy=FusionStrategy.MAJORITY_VOTING
        )

        # "فاتورة" appears twice, should win despite tesseract having higher confidence
        assert "فاتورة" in fusion_result.fused_text

    def test_confidence_based_on_votes(self, fusion_engine):
        """Test that confidence reflects vote ratio."""
        results = [
            OCRResult(text="فاتورة", confidence=0.90, engine=OCREngine.PADDLE, blocks=[]),
            OCRResult(text="فاتورة", confidence=0.85, engine=OCREngine.EASYOCR, blocks=[]),
            OCRResult(text="فاتورة", confidence=0.80, engine=OCREngine.TESSERACT, blocks=[]),
        ]

        fusion_result = fusion_engine.fuse_results(
            results,
            strategy=FusionStrategy.MAJORITY_VOTING
        )

        # All agree, confidence should be high (3/3 = 1.0)
        assert fusion_result.confidence == 1.0


# ==============================================================================
# Dictionary-Validated Fusion Tests
# ==============================================================================

class TestDictionaryValidatedFusion:
    """Tests for dictionary-validated fusion strategy."""

    def test_basic_dictionary_validation(self, fusion_engine, paddle_result, easyocr_result):
        """Test basic dictionary validation."""
        results = [paddle_result, easyocr_result]

        fusion_result = fusion_engine.fuse_results(
            results,
            strategy=FusionStrategy.DICTIONARY_VALIDATED
        )

        assert fusion_result is not None
        assert fusion_result.strategy == FusionStrategy.DICTIONARY_VALIDATED

    def test_dictionary_words_preferred(self, custom_vocabulary_engine):
        """Test that dictionary words are strongly preferred."""
        results = [
            OCRResult(
                text="فاتورة",  # In custom vocabulary
                confidence=0.75,
                engine=OCREngine.PADDLE,
                blocks=[]
            ),
            OCRResult(
                text="فاتوره",  # Not in vocabulary
                confidence=0.95,
                engine=OCREngine.EASYOCR,
                blocks=[]
            ),
        ]

        fusion_result = custom_vocabulary_engine.fuse_results(
            results,
            strategy=FusionStrategy.DICTIONARY_VALIDATED
        )

        # Dictionary word should win despite lower confidence
        assert "فاتورة" in fusion_result.fused_text

    def test_fallback_when_no_dictionary_match(self, custom_vocabulary_engine):
        """Test fallback to confidence when no dictionary matches."""
        results = [
            OCRResult(
                text="كلمة",  # Not in custom vocabulary
                confidence=0.95,
                engine=OCREngine.PADDLE,
                blocks=[]
            ),
            OCRResult(
                text="كلمه",  # Not in vocabulary
                confidence=0.85,
                engine=OCREngine.EASYOCR,
                blocks=[]
            ),
        ]

        fusion_result = custom_vocabulary_engine.fuse_results(
            results,
            strategy=FusionStrategy.DICTIONARY_VALIDATED
        )

        # Should fall back to highest confidence
        assert fusion_result.fused_text is not None


# ==============================================================================
# Best Confidence Strategy Tests
# ==============================================================================

class TestBestConfidenceStrategy:
    """Tests for best confidence selection strategy."""

    def test_selects_highest_confidence(self, fusion_engine):
        """Test that highest confidence result is selected."""
        results = [
            OCRResult(text="نص أول", confidence=0.85, engine=OCREngine.PADDLE, blocks=[]),
            OCRResult(text="نص ثاني", confidence=0.95, engine=OCREngine.EASYOCR, blocks=[]),
            OCRResult(text="نص ثالث", confidence=0.75, engine=OCREngine.TESSERACT, blocks=[]),
        ]

        fusion_result = fusion_engine.fuse_results(
            results,
            strategy=FusionStrategy.BEST_CONFIDENCE
        )

        assert fusion_result.fused_text == "نص ثاني"
        assert fusion_result.confidence == 0.95


# ==============================================================================
# Arabic Tokenization Tests
# ==============================================================================

class TestArabicTokenization:
    """Tests for Arabic-aware tokenization."""

    def test_basic_tokenization(self, fusion_engine):
        """Test basic Arabic tokenization."""
        text = "الرقم الضريبي"
        tokens = fusion_engine._tokenize_arabic(text)

        assert len(tokens) == 2
        assert tokens[0] == "الرقم"
        assert tokens[1] == "الضريبي"

    def test_mixed_arabic_english(self, fusion_engine):
        """Test tokenization of mixed text."""
        text = "Invoice رقم 12345"
        tokens = fusion_engine._tokenize_arabic(text)

        assert len(tokens) == 3
        assert "Invoice" in tokens
        assert "رقم" in tokens
        assert "12345" in tokens

    def test_punctuation_handling(self, fusion_engine):
        """Test that punctuation is handled correctly."""
        text = "فاتورة، رقم: 12345."
        tokens = fusion_engine._tokenize_arabic(text)

        # Punctuation should be stripped
        assert "فاتورة" in tokens
        assert "رقم" in tokens
        assert "12345" in tokens

    def test_whitespace_normalization(self, fusion_engine):
        """Test whitespace normalization."""
        text = "الرقم    الضريبي\t\nالمبلغ"
        tokens = fusion_engine._tokenize_arabic(text)

        assert len(tokens) == 3
        assert tokens[0] == "الرقم"
        assert tokens[1] == "الضريبي"
        assert tokens[2] == "المبلغ"

    def test_empty_text(self, fusion_engine):
        """Test tokenization of empty text."""
        tokens = fusion_engine._tokenize_arabic("")

        assert tokens == []

    def test_arabic_punctuation(self, fusion_engine):
        """Test handling of Arabic punctuation."""
        text = "فاتورة؛ المبلغ: ١٠٠٠ ريال«»"
        tokens = fusion_engine._tokenize_arabic(text)

        assert len(tokens) >= 3
        assert "فاتورة" in tokens


# ==============================================================================
# Vocabulary Bonus Tests
# ==============================================================================

class TestVocabularyBonus:
    """Tests for vocabulary bonus calculation."""

    def test_exact_match_bonus(self, fusion_engine):
        """Test bonus for exact vocabulary match."""
        bonus = fusion_engine._calculate_vocabulary_bonus("فاتورة")

        assert bonus == 1.5  # Exact match gets highest bonus

    def test_partial_match_bonus(self, fusion_engine):
        """Test bonus for partial match."""
        # "الفاتورة" contains "فاتورة"
        bonus = fusion_engine._calculate_vocabulary_bonus("الفاتورة")

        # Should get at least partial match bonus
        assert bonus >= 1.2

    def test_valid_arabic_bonus(self, fusion_engine):
        """Test bonus for valid Arabic word not in vocabulary."""
        # A valid Arabic word not in the vocabulary
        bonus = fusion_engine._calculate_vocabulary_bonus("كتاب")

        assert bonus >= 1.0

    def test_no_bonus_for_gibberish(self, fusion_engine):
        """Test no bonus for non-Arabic gibberish."""
        bonus = fusion_engine._calculate_vocabulary_bonus("xyz123")

        assert bonus == 1.0  # No bonus


# ==============================================================================
# Word Normalization Tests
# ==============================================================================

class TestWordNormalization:
    """Tests for word normalization."""

    def test_diacritic_removal(self, fusion_engine):
        """Test removal of Arabic diacritics."""
        # Word with diacritics (fatha, damma, kasra)
        word_with_diacritics = "فَاتُورَة"
        normalized = fusion_engine._normalize_for_vocab(word_with_diacritics)

        assert "َ" not in normalized  # Fatha removed
        assert "ُ" not in normalized  # Damma removed

    def test_kashida_removal(self, fusion_engine):
        """Test removal of kashida (tatweel)."""
        word_with_kashida = "فـاتـورة"
        normalized = fusion_engine._normalize_for_vocab(word_with_kashida)

        assert "ـ" not in normalized

    def test_punctuation_stripping(self, fusion_engine):
        """Test stripping of punctuation."""
        word_with_punct = "فاتورة،"
        normalized = fusion_engine._normalize_for_vocab(word_with_punct)

        assert normalized == "فاتورة"


# ==============================================================================
# Word Similarity Tests
# ==============================================================================

class TestWordSimilarity:
    """Tests for word similarity checking."""

    def test_identical_words(self, fusion_engine):
        """Test that identical words are similar."""
        assert fusion_engine._words_similar("فاتورة", "فاتورة") is True

    def test_normalized_similar(self, fusion_engine):
        """Test similarity after normalization."""
        # Same word, one with diacritics
        assert fusion_engine._words_similar("فَاتورة", "فاتورة") is True

    def test_substring_similarity(self, fusion_engine):
        """Test substring similarity."""
        # One word contains the other
        assert fusion_engine._words_similar("فاتورة", "الفاتورة") is True

    def test_dissimilar_words(self, fusion_engine):
        """Test dissimilar words."""
        assert fusion_engine._words_similar("فاتورة", "شركة") is False


# ==============================================================================
# Valid Arabic Word Tests
# ==============================================================================

class TestValidArabicWord:
    """Tests for Arabic word validation."""

    def test_valid_arabic_word(self, fusion_engine):
        """Test valid Arabic word detection."""
        assert fusion_engine._is_valid_arabic_word("فاتورة") is True
        assert fusion_engine._is_valid_arabic_word("الضريبي") is True

    def test_invalid_arabic_word(self, fusion_engine):
        """Test invalid Arabic word detection."""
        assert fusion_engine._is_valid_arabic_word("abc") is False
        assert fusion_engine._is_valid_arabic_word("123") is False

    def test_mixed_word(self, fusion_engine):
        """Test mixed Arabic/English word."""
        # Less than 80% Arabic
        assert fusion_engine._is_valid_arabic_word("abفاc") is False

    def test_empty_word(self, fusion_engine):
        """Test empty word."""
        assert fusion_engine._is_valid_arabic_word("") is False

    def test_single_character(self, fusion_engine):
        """Test single character (too short)."""
        assert fusion_engine._is_valid_arabic_word("ا") is False


# ==============================================================================
# Empty Result Handling Tests
# ==============================================================================

class TestEmptyResultsHandling:
    """Tests for handling empty results."""

    def test_empty_results_list(self, fusion_engine):
        """Test fusion with empty results list."""
        fusion_result = fusion_engine.fuse_results([])

        assert fusion_result.fused_text == ""
        assert fusion_result.confidence == 0.0
        assert fusion_result.individual_results == []

    def test_single_result(self, fusion_engine, paddle_result):
        """Test fusion with single result."""
        fusion_result = fusion_engine.fuse_results([paddle_result])

        assert fusion_result.fused_text == paddle_result.text
        assert fusion_result.confidence == paddle_result.confidence

    def test_results_with_empty_text(self, fusion_engine):
        """Test fusion when some results have empty text."""
        results = [
            OCRResult(text="", confidence=0.0, engine=OCREngine.PADDLE, blocks=[]),
            OCRResult(text="فاتورة", confidence=0.90, engine=OCREngine.EASYOCR, blocks=[]),
        ]

        fusion_result = fusion_engine.fuse_results(results)

        # Should handle gracefully
        assert fusion_result is not None

    def test_all_empty_results(self, fusion_engine):
        """Test fusion when all results have empty text."""
        results = [
            OCRResult(text="", confidence=0.0, engine=OCREngine.PADDLE, blocks=[]),
            OCRResult(text="", confidence=0.0, engine=OCREngine.EASYOCR, blocks=[]),
        ]

        fusion_result = fusion_engine.fuse_results(results)

        assert fusion_result.fused_text == ""
        assert fusion_result.confidence == 0.0


# ==============================================================================
# Conflict Resolution Tests
# ==============================================================================

class TestConflictResolution:
    """Tests for word conflict resolution."""

    def test_resolve_conflict_basic(self, fusion_engine, divergent_results):
        """Test basic conflict resolution."""
        word, confidence, source = fusion_engine.resolve_conflicts(
            divergent_results,
            position=0  # First word
        )

        assert word != ""
        assert confidence > 0
        assert source in ["paddle", "easyocr", "tesseract"]

    def test_resolve_conflict_prefers_agreement(self, fusion_engine):
        """Test that conflict resolution prefers words with agreement."""
        results = [
            OCRResult(text="فاتورة", confidence=0.80, engine=OCREngine.PADDLE, blocks=[]),
            OCRResult(text="فاتورة", confidence=0.85, engine=OCREngine.EASYOCR, blocks=[]),
            OCRResult(text="فاتوره", confidence=0.95, engine=OCREngine.TESSERACT, blocks=[]),
        ]

        word, confidence, source = fusion_engine.resolve_conflicts(results, 0)

        # Should prefer "فاتورة" due to agreement bonus
        assert word == "فاتورة"

    def test_resolve_conflict_invalid_position(self, fusion_engine, divergent_results):
        """Test conflict resolution with invalid position."""
        word, confidence, source = fusion_engine.resolve_conflicts(
            divergent_results,
            position=100  # Out of range
        )

        assert word == ""
        assert confidence == 0.0
        assert source == ""


# ==============================================================================
# Strategy Selection Tests
# ==============================================================================

class TestStrategySelection:
    """Tests for fusion strategy selection."""

    def test_all_strategies_work(self, fusion_engine, paddle_result, easyocr_result):
        """Test that all strategies produce results."""
        results = [paddle_result, easyocr_result]

        for strategy in FusionStrategy:
            fusion_result = fusion_engine.fuse_results(results, strategy=strategy)

            assert fusion_result is not None
            assert fusion_result.strategy == strategy
            assert fusion_result.fused_text != ""

    def test_strategy_stored_in_result(self, fusion_engine, paddle_result, easyocr_result):
        """Test that strategy is stored in result."""
        results = [paddle_result, easyocr_result]

        fusion_result = fusion_engine.fuse_results(
            results,
            strategy=FusionStrategy.MAJORITY_VOTING
        )

        assert fusion_result.strategy == FusionStrategy.MAJORITY_VOTING


# ==============================================================================
# Edge Case Tests
# ==============================================================================

class TestEdgeCases:
    """Tests for edge cases."""

    def test_very_long_text(self, fusion_engine):
        """Test fusion with very long text."""
        long_text = "فاتورة " * 1000
        results = [
            OCRResult(text=long_text, confidence=0.90, engine=OCREngine.PADDLE, blocks=[]),
            OCRResult(text=long_text, confidence=0.85, engine=OCREngine.EASYOCR, blocks=[]),
        ]

        fusion_result = fusion_engine.fuse_results(results)

        assert len(fusion_result.fused_text) > 0

    def test_special_characters(self, fusion_engine):
        """Test fusion with special characters."""
        results = [
            OCRResult(text="100% @ #$%", confidence=0.90, engine=OCREngine.PADDLE, blocks=[]),
            OCRResult(text="100% @ #$%", confidence=0.85, engine=OCREngine.EASYOCR, blocks=[]),
        ]

        fusion_result = fusion_engine.fuse_results(results)

        assert fusion_result is not None

    def test_different_length_results(self, fusion_engine):
        """Test fusion when results have different lengths."""
        results = [
            OCRResult(text="فاتورة رقم", confidence=0.90, engine=OCREngine.PADDLE, blocks=[]),
            OCRResult(text="فاتورة رقم 12345", confidence=0.85, engine=OCREngine.EASYOCR, blocks=[]),
            OCRResult(text="فاتورة", confidence=0.80, engine=OCREngine.TESSERACT, blocks=[]),
        ]

        fusion_result = fusion_engine.fuse_results(results)

        # Should handle different lengths gracefully
        assert "فاتورة" in fusion_result.fused_text

    def test_unicode_numbers(self, fusion_engine):
        """Test fusion with Arabic/Persian numbers."""
        results = [
            OCRResult(text="فاتورة ١٢٣٤٥", confidence=0.90, engine=OCREngine.PADDLE, blocks=[]),
            OCRResult(text="فاتورة 12345", confidence=0.85, engine=OCREngine.EASYOCR, blocks=[]),
        ]

        fusion_result = fusion_engine.fuse_results(results)

        assert "فاتورة" in fusion_result.fused_text


# ==============================================================================
# Performance Tests
# ==============================================================================

class TestFusionPerformance:
    """Basic performance tests for fusion engine."""

    def test_fusion_speed(self, fusion_engine):
        """Test fusion speed."""
        import time

        results = [
            OCRResult(
                text="الرقم الضريبي 310123456789012 " * 10,
                confidence=0.90,
                engine=OCREngine.PADDLE,
                blocks=[]
            ),
            OCRResult(
                text="الرقم الضريبي 310123456789012 " * 10,
                confidence=0.85,
                engine=OCREngine.EASYOCR,
                blocks=[]
            ),
        ]

        start = time.time()
        for _ in range(100):
            fusion_engine.fuse_results(results)
        elapsed = time.time() - start

        # Should complete 100 fusions in under 1 second
        assert elapsed < 1.0

    def test_tokenization_speed(self, fusion_engine):
        """Test tokenization speed."""
        import time

        text = "الرقم الضريبي " * 100

        start = time.time()
        for _ in range(1000):
            fusion_engine._tokenize_arabic(text)
        elapsed = time.time() - start

        # Should tokenize 1000 times in under 1 second
        assert elapsed < 1.0


# ==============================================================================
# Run Tests
# ==============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
