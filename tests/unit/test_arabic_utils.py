"""
Tests for Arabic text utilities.
"""

import pytest
from src.utils.arabic_utils import (
    remove_diacritics,
    remove_kashida,
    normalize_alef,
    normalize_yaa,
    normalize_taa_marbuta,
    normalize_arabic,
    is_arabic,
    arabic_ratio,
    extract_arabic_words,
    extract_non_arabic_words,
    levenshtein_distance,
    similarity_ratio,
)


class TestRemoveDiacritics:
    """Tests for diacritics removal."""

    def test_remove_fatha(self):
        """Remove fatha diacritic."""
        assert remove_diacritics("مَحَمَّد") == "محمد"

    def test_remove_damma(self):
        """Remove damma diacritic."""
        assert remove_diacritics("مُحَمَّد") == "محمد"

    def test_remove_kasra(self):
        """Remove kasra diacritic."""
        assert remove_diacritics("بِسْمِ") == "بسم"

    def test_remove_shadda(self):
        """Remove shadda diacritic."""
        assert remove_diacritics("محمّد") == "محمد"

    def test_remove_sukun(self):
        """Remove sukun diacritic."""
        assert remove_diacritics("بْسم") == "بسم"

    def test_empty_string(self):
        """Handle empty string."""
        assert remove_diacritics("") == ""

    def test_no_diacritics(self):
        """Handle text without diacritics."""
        assert remove_diacritics("محمد") == "محمد"

    def test_mixed_text(self):
        """Handle mixed Arabic and English."""
        assert remove_diacritics("Hello مَرْحَبًا") == "Hello مرحبا"


class TestRemoveKashida:
    """Tests for kashida removal."""

    def test_remove_kashida(self):
        """Remove kashida character."""
        assert remove_kashida("الـــعربيـــة") == "العربية"

    def test_single_kashida(self):
        """Remove single kashida."""
        assert remove_kashida("العـربية") == "العربية"

    def test_no_kashida(self):
        """Handle text without kashida."""
        assert remove_kashida("العربية") == "العربية"

    def test_empty_string(self):
        """Handle empty string."""
        assert remove_kashida("") == ""


class TestNormalizeAlef:
    """Tests for Alef normalization."""

    def test_alef_with_hamza_above(self):
        """Normalize Alef with Hamza above."""
        assert normalize_alef("أحمد") == "احمد"

    def test_alef_with_hamza_below(self):
        """Normalize Alef with Hamza below."""
        assert normalize_alef("إبراهيم") == "ابراهيم"

    def test_alef_with_madda(self):
        """Normalize Alef with Madda."""
        assert normalize_alef("آمن") == "امن"

    def test_multiple_alef_variants(self):
        """Normalize multiple Alef variants."""
        assert normalize_alef("أحمد إبراهيم آمن") == "احمد ابراهيم امن"

    def test_no_alef_variants(self):
        """Handle text without Alef variants."""
        assert normalize_alef("محمد") == "محمد"

    def test_empty_string(self):
        """Handle empty string."""
        assert normalize_alef("") == ""


class TestNormalizeYaa:
    """Tests for Yaa normalization."""

    def test_alef_maksura(self):
        """Normalize Alef Maksura to Yaa."""
        assert normalize_yaa("على") == "علي"

    def test_multiple_alef_maksura(self):
        """Normalize multiple Alef Maksura."""
        assert normalize_yaa("موسى على") == "موسي علي"

    def test_no_alef_maksura(self):
        """Handle text without Alef Maksura."""
        assert normalize_yaa("محمد") == "محمد"

    def test_empty_string(self):
        """Handle empty string."""
        assert normalize_yaa("") == ""


class TestNormalizeTaaMarbuta:
    """Tests for Taa Marbuta normalization."""

    def test_taa_marbuta_to_haa_disabled(self):
        """Keep Taa Marbuta when disabled."""
        assert normalize_taa_marbuta("فاتورة") == "فاتورة"

    def test_taa_marbuta_to_haa_enabled(self):
        """Convert Taa Marbuta to Haa when enabled."""
        assert normalize_taa_marbuta("فاتورة", to_haa=True) == "فاتوره"

    def test_empty_string(self):
        """Handle empty string."""
        assert normalize_taa_marbuta("") == ""


class TestNormalizeArabic:
    """Tests for full Arabic normalization pipeline."""

    def test_full_normalization(self):
        """Apply all normalizations."""
        text = "فَاتُورَة ضَرِيبِيَّة"
        result = normalize_arabic(text)
        # Should remove diacritics
        assert "فاتورة" in result or "فاتوره" in result

    def test_selective_normalization(self):
        """Apply selective normalizations."""
        text = "أحمد"
        # Only normalize alef
        result = normalize_arabic(
            text,
            remove_tashkeel=False,
            normalize_alef_chars=True,
            normalize_yaa_chars=False
        )
        assert result == "احمد"

    def test_empty_string(self):
        """Handle empty string."""
        assert normalize_arabic("") == ""

    def test_whitespace_normalization(self):
        """Normalize whitespace."""
        assert normalize_arabic("hello   world") == "hello world"


class TestIsArabic:
    """Tests for Arabic detection."""

    def test_arabic_text(self):
        """Detect Arabic text."""
        assert is_arabic("مرحبا") is True

    def test_english_text(self):
        """Detect English text."""
        assert is_arabic("Hello") is False

    def test_mixed_text(self):
        """Detect mixed text."""
        assert is_arabic("Hello مرحبا") is True

    def test_empty_string(self):
        """Handle empty string."""
        assert is_arabic("") is False

    def test_numbers_only(self):
        """Handle numbers only."""
        assert is_arabic("12345") is False


class TestArabicRatio:
    """Tests for Arabic ratio calculation."""

    def test_all_arabic(self):
        """Calculate ratio for all Arabic."""
        ratio = arabic_ratio("مرحبا")
        assert ratio == 1.0

    def test_all_english(self):
        """Calculate ratio for all English."""
        ratio = arabic_ratio("Hello")
        assert ratio == 0.0

    def test_mixed_text(self):
        """Calculate ratio for mixed text."""
        ratio = arabic_ratio("مرحبا Hello")
        assert 0.3 < ratio < 0.7

    def test_empty_string(self):
        """Handle empty string."""
        assert arabic_ratio("") == 0.0


class TestExtractWords:
    """Tests for word extraction."""

    def test_extract_arabic_words(self):
        """Extract Arabic words from mixed text."""
        words = extract_arabic_words("Invoice فاتورة Number رقم")
        assert "فاتورة" in words
        assert "رقم" in words
        assert "Invoice" not in words

    def test_extract_non_arabic_words(self):
        """Extract non-Arabic words from mixed text."""
        words = extract_non_arabic_words("Invoice فاتورة Number رقم")
        assert "Invoice" in words
        assert "Number" in words
        assert "فاتورة" not in words

    def test_empty_string(self):
        """Handle empty string."""
        assert extract_arabic_words("") == []
        assert extract_non_arabic_words("") == []


class TestLevenshteinDistance:
    """Tests for Levenshtein distance calculation."""

    def test_identical_strings(self):
        """Distance for identical strings."""
        assert levenshtein_distance("فاتورة", "فاتورة") == 0

    def test_one_char_difference(self):
        """Distance for one character difference."""
        distance = levenshtein_distance("فاتورة", "فانورة")
        assert distance == 1

    def test_empty_strings(self):
        """Handle empty strings."""
        assert levenshtein_distance("", "") == 0
        assert levenshtein_distance("abc", "") == 3
        assert levenshtein_distance("", "abc") == 3

    def test_completely_different(self):
        """Distance for completely different strings."""
        distance = levenshtein_distance("abc", "xyz")
        assert distance == 3


class TestSimilarityRatio:
    """Tests for similarity ratio calculation."""

    def test_identical_strings(self):
        """Ratio for identical strings."""
        assert similarity_ratio("فاتورة", "فاتورة") == 1.0

    def test_one_char_difference(self):
        """Ratio for one character difference."""
        ratio = similarity_ratio("فاتورة", "فانورة")
        assert 0.8 < ratio < 1.0

    def test_empty_strings(self):
        """Handle empty strings."""
        assert similarity_ratio("", "") == 1.0
        assert similarity_ratio("abc", "") == 0.0

    def test_completely_different(self):
        """Ratio for completely different strings."""
        ratio = similarity_ratio("abc", "xyz")
        assert ratio == 0.0
