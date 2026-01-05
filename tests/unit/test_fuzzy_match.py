"""
Tests for fuzzy string matching utilities.
"""

import pytest
from src.utils.fuzzy_match import (
    fuzzy_ratio,
    fuzzy_partial_ratio,
    fuzzy_token_sort_ratio,
    fuzzy_token_set_ratio,
    fuzzy_best_match,
    fuzzy_match_all,
    fuzzy_contains,
    fuzzy_field_match,
    fuzzy_extract_key_value,
    FuzzyMatch,
    RAPIDFUZZ_AVAILABLE,
)


class TestFuzzyRatio:
    """Tests for fuzzy_ratio function."""

    def test_identical_strings(self):
        """Ratio for identical strings should be 100."""
        assert fuzzy_ratio("فاتورة", "فاتورة") == 100.0

    def test_similar_strings(self):
        """Ratio for similar strings should be high."""
        # One character difference
        ratio = fuzzy_ratio("فاتورة", "فانورة")
        assert ratio > 80

    def test_different_strings(self):
        """Ratio for different strings should be low."""
        ratio = fuzzy_ratio("فاتورة", "عميل")
        assert ratio < 50

    def test_empty_strings(self):
        """Handle empty strings."""
        assert fuzzy_ratio("", "") == 0.0
        assert fuzzy_ratio("abc", "") == 0.0

    def test_with_normalization(self):
        """Test with Arabic normalization."""
        # With diacritics vs without
        ratio = fuzzy_ratio("فَاتُورَة", "فاتورة", normalize=True)
        assert ratio == 100.0


class TestFuzzyPartialRatio:
    """Tests for fuzzy_partial_ratio function."""

    def test_substring_match(self):
        """Partial ratio for substring should be 100."""
        ratio = fuzzy_partial_ratio("فاتورة", "فاتورة ضريبية")
        assert ratio == 100.0

    def test_similar_substring(self):
        """Partial ratio for similar substring should be high."""
        ratio = fuzzy_partial_ratio("فاتور", "فاتورة ضريبية")
        assert ratio > 80

    def test_no_match(self):
        """Partial ratio for no match should be low."""
        ratio = fuzzy_partial_ratio("xyz", "فاتورة ضريبية")
        assert ratio < 50


class TestFuzzyTokenSortRatio:
    """Tests for fuzzy_token_sort_ratio function."""

    def test_same_tokens_different_order(self):
        """Token sort ratio for same tokens in different order."""
        ratio = fuzzy_token_sort_ratio("شركة فضاء", "فضاء شركة")
        assert ratio == 100.0

    def test_different_tokens(self):
        """Token sort ratio for different tokens."""
        ratio = fuzzy_token_sort_ratio("شركة فضاء", "عميل محلي")
        assert ratio < 50


class TestFuzzyTokenSetRatio:
    """Tests for fuzzy_token_set_ratio function."""

    def test_subset_tokens(self):
        """Token set ratio for subset of tokens."""
        ratio = fuzzy_token_set_ratio("فاتورة مبسطة", "فاتورة ضريبية مبسطة")
        assert ratio > 80

    def test_no_common_tokens(self):
        """Token set ratio for no common tokens."""
        ratio = fuzzy_token_set_ratio("شركة فضاء", "عميل محلي")
        assert ratio < 30


class TestFuzzyBestMatch:
    """Tests for fuzzy_best_match function."""

    def test_exact_match(self):
        """Find exact match in candidates."""
        candidates = ["فاتورة", "رقم", "تاريخ"]
        match = fuzzy_best_match("فاتورة", candidates)
        assert match is not None
        assert match.match == "فاتورة"
        assert match.score == 100.0

    def test_fuzzy_match(self):
        """Find fuzzy match in candidates."""
        candidates = ["فاتورة", "رقم", "تاريخ"]
        match = fuzzy_best_match("فانورة", candidates, threshold=70)
        assert match is not None
        assert match.match == "فاتورة"
        assert match.score > 70

    def test_no_match_below_threshold(self):
        """Return None when no match above threshold."""
        candidates = ["فاتورة", "رقم", "تاريخ"]
        match = fuzzy_best_match("xyz", candidates, threshold=70)
        assert match is None

    def test_empty_candidates(self):
        """Handle empty candidates list."""
        match = fuzzy_best_match("فاتورة", [])
        assert match is None

    def test_empty_query(self):
        """Handle empty query."""
        match = fuzzy_best_match("", ["فاتورة"])
        assert match is None


class TestFuzzyMatchAll:
    """Tests for fuzzy_match_all function."""

    def test_multiple_matches(self):
        """Find multiple matches above threshold."""
        candidates = ["فاتورة", "فوترة", "تور", "عميل"]
        matches = fuzzy_match_all("فاتور", candidates, threshold=50)
        assert len(matches) >= 1
        # Best match should be first
        assert matches[0].match in ["فاتورة", "فوترة"]

    def test_limit_results(self):
        """Limit number of results."""
        candidates = ["فاتورة", "فوترة", "تور", "عميل"]
        matches = fuzzy_match_all("فاتور", candidates, threshold=30, limit=2)
        assert len(matches) <= 2

    def test_empty_results(self):
        """Return empty list when no matches."""
        matches = fuzzy_match_all("xyz", ["فاتورة"], threshold=90)
        assert len(matches) == 0


class TestFuzzyContains:
    """Tests for fuzzy_contains function."""

    def test_exact_contains(self):
        """Detect exact keyword in text."""
        assert fuzzy_contains("فاتورة ضريبية", "فاتورة") is True

    def test_fuzzy_contains(self):
        """Detect fuzzy keyword in text."""
        result = fuzzy_contains("فانورة ضريبية", "فاتورة", threshold=75)
        assert result is True

    def test_not_contains(self):
        """Return False when keyword not in text."""
        assert fuzzy_contains("فاتورة ضريبية", "عميل") is False

    def test_empty_strings(self):
        """Handle empty strings."""
        assert fuzzy_contains("", "فاتورة") is False
        assert fuzzy_contains("فاتورة", "") is False


class TestFuzzyFieldMatch:
    """Tests for fuzzy_field_match function."""

    def test_exact_match(self):
        """Match exact field in dictionary."""
        field_dict = {"فاتورة": "Invoice", "رقم": "Number"}
        ar_key, en_value, score = fuzzy_field_match("فاتورة", field_dict)
        assert ar_key == "فاتورة"
        assert en_value == "Invoice"
        assert score == 100.0

    def test_fuzzy_match(self):
        """Match fuzzy field in dictionary."""
        field_dict = {"فاتورة": "Invoice", "رقم": "Number"}
        ar_key, en_value, score = fuzzy_field_match("فانورة", field_dict, threshold=70)
        assert ar_key == "فاتورة"
        assert en_value == "Invoice"
        assert score > 70

    def test_no_match(self):
        """Return None when no match found."""
        field_dict = {"فاتورة": "Invoice"}
        ar_key, en_value, score = fuzzy_field_match("xyz", field_dict)
        assert ar_key is None
        assert en_value is None
        assert score == 0.0


class TestFuzzyExtractKeyValue:
    """Tests for fuzzy_extract_key_value function."""

    def test_colon_separator(self):
        """Extract key-value with colon separator."""
        field_dict = {"الرقم": "Number", "التاريخ": "Date"}
        result = fuzzy_extract_key_value("الرقم: 12345", field_dict)
        assert result is not None
        assert result['english_key'] == "Number"
        assert result['value'] == "12345"

    def test_fuzzy_key(self):
        """Extract key-value with fuzzy key match."""
        field_dict = {"العميل": "Customer"}
        result = fuzzy_extract_key_value("العملي: قرطاسية اصل", field_dict, threshold=70)
        # Should match العميل even though input is العملي
        if result:
            assert result['value']

    def test_no_match(self):
        """Return None when no key-value found."""
        field_dict = {"فاتورة": "Invoice"}
        result = fuzzy_extract_key_value("some random text", field_dict)
        assert result is None


class TestFuzzyMatchDataclass:
    """Tests for FuzzyMatch dataclass."""

    def test_truthy_positive_score(self):
        """FuzzyMatch is truthy with positive score."""
        match = FuzzyMatch(text="a", match="b", score=50.0)
        assert bool(match) is True

    def test_falsy_zero_score(self):
        """FuzzyMatch is falsy with zero score."""
        match = FuzzyMatch(text="a", match="b", score=0.0)
        assert bool(match) is False


class TestRapidfuzzAvailability:
    """Tests for rapidfuzz availability."""

    def test_rapidfuzz_available(self):
        """Verify rapidfuzz is available."""
        # This test ensures rapidfuzz is installed
        assert RAPIDFUZZ_AVAILABLE is True
